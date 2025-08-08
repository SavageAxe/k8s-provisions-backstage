import httpx
from fastapi import HTTPException
from app.src.api.argocd import ArgoCDAPI
from loguru import logger
import json
from time import sleep

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

            except HTTPException as e:

                if e.status_code != 403:
                    raise e

                else:
                    sleep(1)
                    timeout += 1

            except httpx.RequestError as e:
                logger.error(f"Request failed: {e}")
                raise e

        raise Exception(f"Timed out waiting for {app_name}")


    async def sync(self, region, namespace, name, resource):

        logger.info(f"Triggered ArgoCD sync for {name}'s {resource} at region: {region} in namespace: {namespace}")

        app_name = build_app_name(region, namespace, name, resource)

        try:
            await self.wait_for_app_creation(app_name)

        except Exception as e:
            logger.error(f"{app_name} don't exist")
            raise e

        try:
            await self.api.sync_app(app_name)

        except httpx.RequestError as e:
            logger.error(f"Request failed: {e}")
            raise e

        except HTTPException as e:
            logger.error(f"Failed to sync {name}'s {resource} at region: {region} in namespace: {namespace}"
                         f"unexpected response from ArgoCD API: response code: {e.status_code}, detail: {e.detail}")
            raise e


    async def get_app_status(self, region, namespace, name, resource):

        logger.info(f"Getting ArgoCD app status for {name}'s {resource} at region: {region} in namespace: {namespace}")

        app_name = build_app_name(region, namespace, name, resource)

        try:
            response = await self.api.get_app(app_name)

        except Exception as e:
            raise e

        response = json.loads(response.body)

        return response["status"]["sync"]



