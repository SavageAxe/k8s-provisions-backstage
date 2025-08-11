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


def handle_response(response: httpx.Response) -> JSONResponse:

    if response.status_code == 401:
        raise GitError(status_code=response.status_code, detail="Git token is invalid or revoked."
                                                    f"Git message: {response.text}")

    if response.status_code == 404:
        raise GitError(status_code=404, detail="Git path (repo or file) not found."
                       f"Git message: {response.text}")

    if response.status_code != httpx.codes.OK:
        raise GitError(status_code=response.status_code, detail=f"Git status code: {response.status_code}."
                                                    f"Git message: {response.text}")


class GitAPI:
    def __init__(self, base_url, token):
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        self.api = BaseAPI(base_url.rstrip('/'), headers=headers)

    async def get_file_sha(self, path: str) -> str:

        try:
            file_sha = await self.api.get(path)
            handle_response(file_sha)

        except httpx.RequestError as e:
            raise GitError(status_code=500, detail=f"Git request failed: {e}")

        return file_sha.json()["sha"]

    async def get_file_content(self, path: str) -> str:
        # Fetch the file details from GitHub (including the base64-encoded content)
        try:
            response = await self.api.get(path)
            handle_response(response)

        except httpx.RequestError as e:
            raise GitError(status_code=500, detail=f"Git request failed: {e}")

        # GitHub returns the content in base64, so we need to decode it
        content = response.json().get("content")

        decoded_content = base64.b64decode(content).decode('utf-8')
        return decoded_content

    async def modify_file_content(self, path, commit_message, content):

        try:
            sha = await self.get_file_sha(path)

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
            response = await self.api.put(path, json=payload)
            handle_response(response)

        except httpx.RequestError as e:
            raise GitError(status_code=500, detail=f"Git request failed: {e}")


    async def list_dir(self, path: str) -> list[str]:
        try:
            response = await self.api.get(path)
            handle_response(response)

        except httpx.RequestError as e:
            raise GitError(status_code=500, detail=f"Git request failed: {e}")

        files = []
        for file in response.json():
            files.append((file["name"], file["path"]))

        return files


    async def create_new_file(self, path: str, commit_message: str,content: str):

        encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')

        payload = {
            "content": encoded_content,
            "message": commit_message
        }

        try:
            response = await self.api.put(path, json=payload)
            handle_response(response)

        except httpx.RequestError as e:
            raise GitError(status_code=500, detail=f"Git request failed: {e}")