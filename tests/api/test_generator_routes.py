import pytest
from fastapi import FastAPI
import httpx
from httpx import ASGITransport

from app.src.routers.generator import RouterGenerator


class FakeArgocd:
    async def get_app_status(self, app_name: str):
        return {"status": "Synced", "revision": "abc123"}

    async def sync(self, app_name: str):
        return None

    async def get_app_values(self, name: str):
        return "{}"

    async def modify_values(self, values, app, ns, proj):
        return None


class FakeGit:
    def __init__(self):
        self.deleted = []
        self.modified = []
        self.files = {}

    async def get_file_content(self, path: str):
        return self.files.get(path, "key: value\n")

    async def delete_file(self, path: str, commit_message: str):
        self.deleted.append((path, commit_message))

    async def modify_file(self, path: str, commit_message: str, content: str):
        self.modified.append((path, commit_message, content))
        self.files[path] = content


class FakeSchemaManager:
    def __init__(self):
        # Use a single non-semver version to only register general routes
        self.resolved_schemas = {"latest": {"schema": {}}}

    async def load_all_schemas(self):
        return None


class FakeVault:
    def __init__(self):
        self.deleted = []
        self.written = []

    async def write_secret(self, path: str, data: dict):
        self.written.append((path, data))

    async def delete_secret(self, path: str):
        self.deleted.append(path)


@pytest.mark.asyncio
async def test_status_and_get_config_routes():
    app = FastAPI()
    fake_git = FakeGit()
    generator = RouterGenerator(
        app=app,
        resource="service",
        git=fake_git,
        schema_manager=FakeSchemaManager(),
        argocd=FakeArgocd(),
        vault=FakeVault(),
        team_name="team",
    )

    await generator.generate_routes()

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # status route
        r = await client.get(
            "/v1/service/status",
            params={"cluster": "eu", "namespace": "ns", "name": "app"},
        )
        assert r.status_code == 200
        assert r.json() == {"status": "Synced", "version": "abc123"}

        # get configuration route returns raw text (YAML)
        r2 = await client.get(
            "/v1/service/",
            params={"cluster": "eu", "namespace": "ns", "name": "app"},
        )
        assert r2.status_code == 200
        assert r2.text.startswith("key: value")


@pytest.mark.asyncio
async def test_delete_route_invokes_git_and_vault():
    app = FastAPI()
    fake_git = FakeGit()
    fake_vault = FakeVault()
    generator = RouterGenerator(
        app=app,
        resource="service",
        git=fake_git,
        schema_manager=FakeSchemaManager(),
        argocd=FakeArgocd(),
        vault=fake_vault,
        team_name="team",
    )

    await generator.generate_routes()

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.request(
            method="DELETE",
            url="/v1/service/",
            params={"cluster": "eu", "namespace": "ns", "name": "app"},
        )
        # No content returned, but should be 200 by default
        assert r.status_code in (200, 204)

    # Verify underlying services were called
    assert any(p[0].endswith("/eu/ns/app.yaml") for p in fake_git.deleted)
    # Verify new secret path format: /{resource}/{cluster}/{namespace}/{application_name}
    assert f"/service/eu/ns/app" in fake_vault.deleted
