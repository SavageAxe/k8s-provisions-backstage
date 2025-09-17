"""High level helpers wrapping the Vault API client."""

from __future__ import annotations

from typing import Dict

from loguru import logger

from .api import VaultAPI

__all__ = ["Vault", "logger"]


class Vault:
    """Higher level wrapper around :class:`VaultAPI`."""

    def __init__(self, base_url: str, token: str) -> None:
        self.api = VaultAPI(base_url, token)
        self.logger = logger

    @staticmethod
    def get_logger():
        """Return the shared loguru logger used by the service."""

        return logger

    async def read_secret(self, path: str) -> Dict:
        self.logger.debug("Reading Vault secret at {}", path)
        response = await self.api.read_secret(path)
        return response.get("data", {})

    async def write_secret(self, path: str, data: Dict) -> None:
        self.logger.debug("Writing Vault secret at {}", path)
        await self.api.write_secret(path, data)

    async def delete_secret(self, path: str) -> None:
        self.logger.debug("Deleting Vault secret at {}", path)
        await self.api.delete_secret(path)
