from contextlib import asynccontextmanager
from pathlib import Path

import aioftp
from io import BytesIO
from typing import Optional, AsyncGenerator


class AsyncFTPClient:
    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        port: int = 21,
        base_dir: str = ".",
        override: bool = True,
    ) -> None:
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.base_dir = base_dir
        self.override = override

    @classmethod
    async def create(
        cls,
        host: str,
        user: str,
        password: str,
        port: int = 21,
        base_dir: str = ".",
        override: bool = True,
    ) -> "AsyncFTPClient":
        instance = cls(host, user, password, port, base_dir, override)
        return instance

    @asynccontextmanager
    async def _get_client(self) -> AsyncGenerator[aioftp.Client, None]:
        client = aioftp.Client()
        try:
            await client.connect(self.host, self.port)
            await client.login(self.user, self.password)
            await client.change_directory(self.base_dir)
            yield client
        finally:
            await client.quit()

    async def pwd(self) -> str:
        async with self._get_client() as client:
            client: aioftp.Client = client
            return str(await client.get_current_directory())

    async def cd(self, path: str) -> None:
        async with self._get_client() as client:
            client: aioftp.Client = client
            await client.change_directory(path)

    async def list(self) -> list[str]:
        async with self._get_client() as client:
            client: aioftp.Client = client
            entry_list = await client.list()
            return [entry[0].name for entry in entry_list]

    async def rename(self, name: str, new_name: str) -> None:
        async with self._get_client() as client:
            client: aioftp.Client = client
            if not await self.file_exists(name):
                raise FileNotFoundError(f"File '{name}' does not exist.")
            if await self.file_exists(new_name):
                if not self.override:
                    raise FileExistsError(f"File '{new_name}' already exists.")
                await self.delete(new_name)

            await client.rename(name, new_name)

    async def download(self, filename: str) -> bytes:
        async with self._get_client() as client:
            client: aioftp.Client = client
            data_stream = BytesIO()

            async with client.download_stream(filename) as stream:
                data_stream.write(await stream.read())

            data_stream.seek(0)
            return data_stream.read()

    async def upload(self, filename: str, content: bytes) -> None:
        async with self._get_client() as client:
            client: aioftp.Client = client
            data_stream = BytesIO(content)
            temp_name = f"{filename}.tmp"

            async with client.upload_stream(temp_name) as stream:
                await stream.write(data_stream.read())

            await self.rename(temp_name, filename)

    async def upload_from_file(self, local_path: str, remote_name: Optional[str] = None) -> None:
        remote_name = remote_name or Path(local_path).name
        async with self._get_client() as client:
            client: aioftp.Client = client
            temp_name = f"{remote_name}.tmp"
            async with aioftp.PathIO() as aio:
                async with aio.open(local_path, "rb") as f:
                    await client.upload(f, temp_name)

            await self.rename(temp_name, remote_name)

    async def download_to_file(self, remote_name: str, local_path: str) -> None:
        async with self._get_client() as client:
            client: aioftp.Client = client
            async with aioftp.PathIO() as aio:
                async with aio.open(local_path, "wb") as f:
                    await client.download(remote_name, f)

    async def delete(self, filename: str) -> None:
        async with self._get_client() as client:
            client: aioftp.Client = client
            await client.remove_file(filename)

    async def file_exists(self, filename: str) -> bool:
        files = await self.list()
        return filename in files