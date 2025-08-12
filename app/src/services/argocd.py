from app.src.api.argocd import ArgoCDAPI
from loguru import logger
import json
from time import sleep

from app.src.errors.external_service import ExternalServiceError


def build_app_name(region, namespace, name, resource) -> str:
    return f"{region}-{namespace}-{resource}-{name}"

class ArgoCD:
    def __init__(self, base_url, api_key, application_set_timeout: int):
        self.api = ArgoCDAPI(base_url, api_key)
        self.applicationSetTimeout = application_set_timeout
        # self.up = None

    async def wait_for_app_creation(self, app_name):
        timeout = 0
        while timeout < self.applicationSetTimeout:
            logger.info(f"Waiting for {app_name} to be created...")
            try:
                await self.api.get_app(app_name)
                return None

            except ExternalServiceError as e:
                if e.status_code != 403:
                    raise e
                sleep(1)
                timeout += 1

        raise Exception(f"Timed out waiting for {app_name}")


    async def sync(self, region, namespace, name, resource):

        logger.info(f"Triggered ArgoCD sync for {name}'s {resource} at region: {region} in namespace: {namespace}")
        app_name = build_app_name(region, namespace, name, resource)

        await self.wait_for_app_creation(app_name)

        try:
            await self.api.sync_app(app_name)

        except ExternalServiceError as e:
            logger.error(f"Failed to sync {app_name}")
            raise e


    async def get_app_status(self, region, namespace, name, resource):

        logger.info(f"Getting ArgoCD app status for {name}'s {resource} at region: {region} in namespace: {namespace}")

        app_name = build_app_name(region, namespace, name, resource)

        try:
            response = await self.api.get_app(app_name)
            response = json.loads(response.body)

        except ExternalServiceError as e:
            logger.error(f"Failed to get app status for {app_name}")
            raise e

        return response["status"]["sync"]



