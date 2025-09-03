import asyncio

from app.src.api.vault import VaultAPI, VaultError


class Vault:
    def __init__(self, base_url: str, token: str):
        self.api = VaultAPI(base_url, token)

    async def read_secret(self, path: str):
        response = await self.api.read_secret(path)
        return response.get("data")

    async def write_secret(self, path: str, data: dict):
        await self.api.write_secret(path, data)

    async def delete_secret(self, path: str):
        await self.api.delete_secret(path)