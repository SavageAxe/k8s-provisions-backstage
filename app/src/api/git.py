import asyncio
import base64

import httpx
from fastapi.responses import JSONResponse
from ...general.database.basic_api import BaseAPI
from ..errors.external_service import ExternalServiceError
from loguru import logger

class GitError(ExternalServiceError):
    def __init__(self, status_code, detail, *args, **kwargs):
        # Always set service_name to "Git"
        self.service_name = "Git"
        super().__init__(service_name="Git", status_code=status_code, detail=detail, *args, **kwargs)


def handle_response(response: httpx.Response):

    if not 'message' in response.json():
        return

    message = response.json().get('message')

    if response.status_code == 401:
        raise GitError(status_code=response.status_code, detail="Git token is invalid or revoked."
                                                    f"Git message: {message}")

    if response.status_code == 404:
        raise GitError(status_code=404, detail="Git path (repo or file) not found."
                       f"Git message: {message}")

    if response.status_code == 422:
        if "sha" in response.json().get('message'):
            raise GitError(status_code=422, detail="Git path (repo or file) already exists.")
        raise GitError(status_code=422, detail="Invalid request."
                       f"Git message: {message}")


    if not response.is_success:
        raise GitError(status_code=response.status_code, detail=f"Git status code: {response.status_code}."
                                                    f"Git message: {message}")




class GitAPI:
    def __init__(self, base_url, token):
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        self.base_url = base_url
        self.token = token
        self.api = BaseAPI(base_url.rstrip('/'), headers=headers)

    async def get_file(self, path: str):
        try:
            response = await self.api.get(f"/contents/{path.lstrip('/')}")
            handle_response(response)

        except httpx.RequestError as e:
            raise GitError(status_code=500, detail=f"Git request failed: {e}")

        return response.json()

    async def delete_file(self, path: str, commit_message: str):
        data = await self.get_file(path)
        sha = data["sha"]

        payload = {
            "sha": sha,
            "message": commit_message,
            "branch": "main"
        }

        try:
            response = await self.api.delete(f"/contents/{path.lstrip('/')}", json=payload)
            handle_response(response)

        except httpx.RequestError as e:
            raise GitError(status_code=500, detail=f"Git request failed: {e}")


    async def modify_file_content(self, path, commit_message, content):

        try:
            file = await self.get_file(path)
            sha = file["sha"]

        except GitError as e:
            logger.debug(f"Failed to get file sha: {path}")
            raise e


        encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')

        payload = {
            "sha": sha,
            "content": encoded_content,
            "message": commit_message
        }

        try:
            response = await self.api.put(f"/contents/{path.lstrip('/')}", json=payload)
            handle_response(response)

        except httpx.RequestError as e:
            raise GitError(status_code=500, detail=f"Git request failed: {e}")


    async def list_dir(self, path: str) -> list[str]:
        try:
            response = await self.api.get(f"/contents/{path.lstrip('/')}")
            handle_response(response)

        except httpx.RequestError as e:
            raise GitError(status_code=500, detail=f"Git request failed: {e}")

        return response.json()


    async def create_new_file(self, path: str, commit_message: str,content: str):

        encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')

        payload = {
            "content": encoded_content,
            "message": commit_message
        }

        try:
            response = await self.api.put(f"/contents/{path.lstrip('/')}", json=payload)
            handle_response(response)

        except httpx.RequestError as e:
            raise GitError(status_code=500, detail=f"Git request failed: {e}")


    async def commits_per_path(self, path, since, until):

        params = {"path": path, "since": since, "until": until}

        try:
            response = await self.api.get("/commits", params=params)
            handle_response(response)

        except httpx.RequestError as e:
            raise GitError(status_code=500, detail=f"Git request failed: {e}")

        return response.json()

    async def compare_commits(self, base: str, head: str):
        path = f"/compare/{base}...{head}"

        try:
            response = await self.api.get(path)
            handle_response(response)

        except httpx.RequestError as e:
            raise GitError(status_code=500, detail=f"Git request failed: {e}")

        return response.json()

    async def get_last_commit(self):
        try:
            response = await self.api.get("/commits/main")
            handle_response(response)

        except httpx.RequestError as e:
            raise GitError(status_code=500, detail=f"Git request failed: {e}")

        return response.json()


    async def get_commit(self, sha: str):

        try:
            response = await self.api.get(f"/commits/{sha}")
            handle_response(response)

        except httpx.RequestError as e:
            raise GitError(status_code=500, detail=f"Git request failed: {e}")

        return response.json()