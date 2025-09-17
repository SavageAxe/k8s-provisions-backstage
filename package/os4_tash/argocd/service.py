"""High level helpers for interacting with Argo CD."""

from __future__ import annotations

import asyncio
from typing import Any, Dict

import yaml
from loguru import logger

from ..errors import ArgoCDError
from .api import ArgoCDAPI

__all__ = ["ArgoCD", "build_app_name", "logger"]


def build_app_name(region: str, namespace: str, name: str, resource: str) -> str:
    """Build the conventional Argo CD application name used by the platform."""

    return f"{region}-{namespace}-{resource}-{name}"


class ArgoCD:
    """Convenience wrapper that offers higher level Argo CD interactions."""

    def __init__(self, base_url: str, api_key: str, application_set_timeout: int) -> None:
        self.api = ArgoCDAPI(base_url, api_key)
        self.application_set_timeout = application_set_timeout
        self.logger = logger

    @staticmethod
    def get_logger():
        """Return the shared loguru logger used by the service."""

        return logger

    async def wait_for_app_creation(self, app_name: str) -> None:
        timeout = 0
        while timeout < self.application_set_timeout:
            self.logger.info("Waiting for {} to be created...", app_name)
            try:
                await self.api.get_app(app_name)
                return None
            except ArgoCDError as exc:
                if exc.status_code != 403:
                    raise
                await asyncio.sleep(1)
                timeout += 1

        raise TimeoutError(f"Timed out waiting for {app_name}")

    async def sync(self, app_name: str) -> None:
        await self.wait_for_app_creation(app_name)
        await self.api.sync_app(app_name)

    async def get_app_status(self, app_name: str) -> Dict[str, Any]:
        response = await self.api.get_app(app_name)
        return response.get("status", {}).get("sync", {})

    async def get_app_values(self, app_name: str) -> str:
        self.logger.info("Getting ArgoCD app values for {}", app_name)
        response = await self.api.get_app(app_name)
        return response.get("spec", {}).get("source", {}).get("helm", {}).get("values", "")

    async def modify_values(self, values: Dict[str, Any], app_name: str, namespace: str, project: str) -> None:
        values_yaml = yaml.safe_dump(values)
        data = {
            "spec": {
                "source": {
                    "helm": {
                        "values": values_yaml,
                    }
                }
            }
        }

        await self.api.patch_app(data, app_name, namespace, project)
