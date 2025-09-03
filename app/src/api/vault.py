import httpx
from fastapi.responses import JSONResponse

from ...general.database.basic_api import BaseAPI
from ..errors.external_service import ExternalServiceError


class VaultError(ExternalServiceError):
    """Error raised when Vault responds with an error."""

    def __init__(self, status_code, detail, *args, **kwargs):
        # Always set service_name to "Vault"
        self.service_name = "Vault"
        super().__init__(
            service_name="Vault",
            status_code=status_code,
            detail=detail,
            *args,
            **kwargs,
        )


def handle_response(response: httpx.Response) -> None:
    """Raise a VaultError if the response indicates failure."""
    if response.status_code // 100 != 2:
        errors = response.json().get("errors")
        if not response.is_success:
            raise VaultError(
                status_code=response.status_code,
                detail=f"Vault message: {errors}",
            )


def generate_secret_path(path: str) -> str:
    return f"{path.lstrip('/').split('/')[0]}/data/{'/'.join(path.lstrip('/').split('/')[1:])}"


def generate_metadata_path(path: str) -> str:
    return f"{path.lstrip('/').split('/')[0]}/metadata/{'/'.join(path.lstrip('/').split('/')[1:])}"


class VaultAPI:
    def __init__(self, base_url: str, token: str):
        headers = {"X-Vault-Token": token, "Content-Type": "application/json"}
        self.api = BaseAPI(base_url.rstrip("/"), headers=headers)

    async def read_secret(self, path: str) -> JSONResponse:
        try:
            secret_path = generate_secret_path(path)
            response = await self.api.get(f"/v1/{secret_path}")
            handle_response(response)
        except httpx.RequestError as e:
            raise VaultError(status_code=500, detail=f"Vault request failed: {e}")

        return response.json()

    async def write_secret(self, path: str, data: dict) -> JSONResponse:
        try:
            secret_path = generate_secret_path(path)
            response = await self.api.post(f"/v1/{secret_path}", json={"data": data})
            handle_response(response)
        except httpx.RequestError as e:
            raise VaultError(status_code=500, detail=f"Vault request failed: {e}")

    async def delete_secret(self, path: str) -> JSONResponse:
        try:
            # For KV v2, deleting a secret entirely uses the metadata endpoint
            metadata_path = generate_metadata_path(path)
            response = await self.api.delete(f"/v1/{metadata_path}")
            handle_response(response)
        except httpx.RequestError as e:
            raise VaultError(status_code=500, detail=f"Vault request failed: {e}")
