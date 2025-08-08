import httpx
from typing import Optional, Dict, Any, Union, List, Tuple


class BaseAPI:
    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = 10.0,
        verify: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}
        self.timeout = timeout
        self.verify = verify

    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], str]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        files: Optional[List[Tuple[str, Tuple[str, bytes, str]]]] = None,
    ) -> httpx.Response:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        merged_headers = {**self.headers, **(headers or {})}

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout,
                verify=self.verify,
            ) as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    data=data,
                    json=json,
                    headers=merged_headers,
                    files=files,
                )
                return response  # Always return response, caller decides what to do with status code
        except httpx.RequestError as e:
            raise RuntimeError(f"Request failed: {str(e)}") from e

    async def get(self, endpoint: str, **kwargs) -> httpx.Response:
        return await self.request("GET", endpoint, **kwargs)

    async def post(self, endpoint: str, **kwargs) -> httpx.Response:
        return await self.request("POST", endpoint, **kwargs)

    async def put(self, endpoint: str, **kwargs) -> httpx.Response:
        return await self.request("PUT", endpoint, **kwargs)

    async def patch(self, endpoint: str, **kwargs) -> httpx.Response:
        return await self.request("PATCH", endpoint, **kwargs)

    async def delete(self, endpoint: str, **kwargs) -> httpx.Response:
        return await self.request("DELETE", endpoint, **kwargs)

    async def upload_file_bytes(
        self,
        endpoint: str,
        field_name: str,
        filename: str,
        file_bytes: bytes,
        content_type: str = "application/octet-stream",
        extra_fields: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        files = [
            (field_name, (filename, file_bytes, content_type))
        ]
        if extra_fields:
            for key, value in extra_fields.items():
                files.append((key, (None, value)))
        return await self.post(endpoint, files=files)

    async def download_file_bytes(
        self,
        endpoint: str,
    ) -> bytes:
        response = await self.get(endpoint)
        return response.content

    async def close(self):
        await self.client.aclose()
