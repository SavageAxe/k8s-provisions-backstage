import asyncio

import yaml

from app.src.api.argocd import ArgoCDAPI
from . import retry
from loguru import logger
import json
from time import sleep

from app.src.errors.external_service import ExternalServiceError


def build_app_name(cluster, namespace, name, resource) -> str:
    return f"{cluster}-{namespace}-{resource}-{name}"

class ArgoCD:
    def __init__(self, base_url, api_key, application_set_timeout: int):
        self.api = ArgoCDAPI(base_url, api_key)
        self.applicationSetTimeout = application_set_timeout
        # self.up = None


    async def sync(self, app_name):
        await retry(lambda: self.api.sync_app(app_name), base_delay=1.0)

    async def wait_for_app_deletion(self, app_name):
        """Wait until an app is no longer accessible (treated as deleted).

        Polls get_app and returns when ArgoCD responds with 403.
        Uses the same timeout window as applicationSetTimeout.
        """
        timeout = 0
        while timeout < self.applicationSetTimeout:
            try:
                await self.api.get_app(app_name)
                # Still exists; wait and retry
                await asyncio.sleep(1)
                timeout += 1
            except ExternalServiceError as e:
                if e.status_code == 403:
                    # Considered deleted/not accessible
                    return None
                # Other errors should bubble up
                raise e

        raise Exception(f"Timed out waiting for {app_name} deletion")


    async def get_app_status(self, app_name):
        response = await retry(lambda: self.api.get_app(app_name), base_delay=1.0)
        response = json.loads(response.body)

        return response["status"]["sync"]

    async def get_app_values(self, app_name):
        logger.info(f"Getting ArgoCD app values for {app_name}")
        response = await retry(lambda: self.api.get_app(app_name), base_delay=1.0)
        response = json.loads(response.body)

        return response["spec"]["source"]["helm"]["values"]


    async def modify_values(self, values, app_name, namespace, project):

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

        await retry(lambda: self.api.patch_app(data, app_name, namespace, project), base_delay=1.0)

    async def wait_for_app_deletion(self, app_name):
        # Delegate to API which handles exceptions/logging and status checks
        await self.api.wait_for_app_deletion(app_name, timeout=self.applicationSetTimeout)
