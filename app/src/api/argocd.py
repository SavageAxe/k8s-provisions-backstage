import httpx
from fastapi.responses import JSONResponse
from app.general.database import BaseAPI
from fastapi import HTTPException

def handle_response(response: httpx.Response):

    if response.status_code == 307:
        raise HTTPException(status_code=502, detail="ArgoCD endpoint is redirecting."
                                                    f"ArgoCD message: {response.text}")

    if response.status_code == 403:
        raise HTTPException(status_code=502, detail="Dont have permission to access this application, or this application dosen't exist"
                                                    f"ArgoCD message: {response.text}")

    if response.status_code != httpx.codes.OK:
        raise HTTPException(status_code=502, detail=f"ArgoCD status code: {response.status_code}"
                                                    f"ArgoCD message: {response.text}")


class ArgoCDAPI:
    def __init__(self, base_url, api_key):
        headers =  {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self.api = BaseAPI(base_url.rstrip('/'), headers=headers)

    async def sync_app(self, app_name):

        uri = f"/api/v1/applications/{app_name}/sync"

        try:
            response = await self.api.post(endpoint=uri, data={})

        except httpx.RequestError as e:
            raise e

        handle_response(response)


    async def get_app(self, app_name):

        uri = f"/api/v1/applications/{app_name}"

        try:
            response = await self.api.get(endpoint=uri)

        except httpx.RequestError as e:
            raise e

        handle_response(response)

        return JSONResponse(status_code=response.status_code,
                        content=response.json(),
                        headers=response.headers)