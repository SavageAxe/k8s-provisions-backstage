import json

import httpx
from fastapi.responses import JSONResponse
from app.general.database import BaseAPI
from loguru import logger
from ..errors.external_service import ExternalServiceError

class ArgoCDError(ExternalServiceError):
    def __init__(self, status_code, detail, *args, **kwargs):
        # Always set service_name to "ArgoCD"
        self.service_name = "ArgoCD"
        super().__init__(service_name="ArgoCD", status_code=status_code, detail=detail, *args, **kwargs)


def handle_response(response: httpx.Response):

    message = response.json().get('message')

    if response.status_code == 307:
        raise ArgoCDError(status_code=response.status_code, detail="ArgoCD endpoint is redirecting. "
                                                    f"ArgoCD message: {message}")

    if response.status_code == 403:
        raise ArgoCDError(status_code=response.status_code, detail="Don't have permission to access this resource, or this resource dosen't exist. "
                                                    f"ArgoCD message: {message}")

    if not response.is_success:
        raise ArgoCDError(status_code=response.status_code, detail=f"ArgoCD status code: {response.status_code}. "
                                                    f"ArgoCD message: {message}")


class ArgoCDAPI:
    def __init__(self, base_url, api_key):
        headers =  {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self.api = BaseAPI(base_url.rstrip('/'), headers=headers)

    async def sync_app(self, app_name):

        uri = f"/api/v1/applications/{app_name}/sync"

        try:
            response = await self.api.post(endpoint=uri, data={})
            handle_response(response)

        except httpx.RequestError as e:
            raise ArgoCDError(status_code=500, detail=f"Request error: {str(e)}")


    async def get_app(self, app_name):

        uri = f"/api/v1/applications/{app_name}"

        try:
            response = await self.api.get(endpoint=uri)
            handle_response(response)

        except httpx.RequestError as e:
            raise ArgoCDError(status_code=500, detail=f"Request error: {str(e)}")


        return JSONResponse(status_code=response.status_code,
                        content=response.json(),
                        headers=response.headers)


    async def patch_app(self, app_definition, app_name, namespace, project):
        uri = f"/api/v1/applications/{app_name}"

        data = {
            "appNamespace": namespace,
            "name": app_name,
            "patch": json.dumps(app_definition),
            "patchType": "merge",
            "project": project
        }

        data = json.dumps(data)

        try:
            response = await self.api.patch(endpoint=uri, data=data)
            print()
            handle_response(response)

        except httpx.RequestError as e:
            raise ArgoCDError(status_code=500, detail=f"Request error: {str(e)}")
