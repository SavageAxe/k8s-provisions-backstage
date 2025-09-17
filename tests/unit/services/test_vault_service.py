import pytest

from app.src.services.vault import Vault


class FakeVaultAPI:
    def __init__(self):
        self.calls = {"read": 0, "write": 0, "delete": 0}
        self.read_side_effects = []  # list of values or exceptions
        self.write_side_effects = []
        self.delete_side_effects = []

    async def read_secret(self, path: str):
        self.calls["read"] += 1
        if self.read_side_effects:
            effect = self.read_side_effects.pop(0)
            if isinstance(effect, Exception):
                raise effect
            return effect
        return {"data": {"default": True}}

    async def write_secret(self, path: str, data: dict):
        self.calls["write"] += 1
        if self.write_side_effects:
            effect = self.write_side_effects.pop(0)
            if isinstance(effect, Exception):
                raise effect

    async def delete_secret(self, path: str):
        self.calls["delete"] += 1
        if self.delete_side_effects:
            effect = self.delete_side_effects.pop(0)
            if isinstance(effect, Exception):
                raise effect


@pytest.mark.asyncio
async def test_read_secret_returns_data(monkeypatch):
    fake_api = FakeVaultAPI()
    fake_api.read_side_effects = [{"data": {"a": 1}}]

    v = Vault(base_url="http://vault", token="tkn")
    # Patch the retry in this module to call once without sleeping
    async def fast_retry(coro_factory, *args, **kwargs):
        return await coro_factory()
    monkeypatch.setattr("app.src.services.vault.retry", fast_retry)

    # Inject fake API
    v.api = fake_api

    data = await v.read_secret("/kv/app/secret")
    assert data == {"a": 1}
    assert fake_api.calls["read"] == 1


@pytest.mark.asyncio
async def test_write_and_delete_secret_call_underlying_api(monkeypatch):
    fake_api = FakeVaultAPI()
    v = Vault(base_url="http://vault", token="tkn")

    async def fast_retry(coro_factory, *args, **kwargs):
        return await coro_factory()
    monkeypatch.setattr("app.src.services.vault.retry", fast_retry)

    v.api = fake_api

    await v.write_secret("/kv/app/secret", {"k": "v"})
    await v.delete_secret("/kv/app/secret")

    assert fake_api.calls["write"] == 1
    assert fake_api.calls["delete"] == 1


@pytest.mark.asyncio
async def test_retry_on_transient_failure_then_success(monkeypatch):
    fake_api = FakeVaultAPI()
    # First call raises, second succeeds
    fake_api.read_side_effects = [RuntimeError("boom"), {"data": {"ok": True}}]

    v = Vault(base_url="http://vault", token="tkn")

    attempts = {"count": 0}

    async def controlled_retry(coro_factory, attempts: int = 4, **kwargs):
        # Custom retry that loops without sleeping
        last_exc = None
        for _ in range(attempts):
            try:
                attempts["count"] += 1
                return await coro_factory()
            except Exception as e:  # noqa: BLE001
                last_exc = e
                continue
        raise last_exc  # type: ignore[misc]

    monkeypatch.setattr("app.src.services.vault.retry", controlled_retry)
    v.api = fake_api

    data = await v.read_secret("/kv/app/secret")
    assert data == {"ok": True}
    # Should have attempted twice
    assert fake_api.calls["read"] == 2
    assert attempts["count"] >= 2


@pytest.mark.asyncio
async def test_retry_exhaustion_raises(monkeypatch):
    fake_api = FakeVaultAPI()
    # All attempts raise
    fake_api.read_side_effects = [RuntimeError("boom") for _ in range(5)]

    v = Vault(base_url="http://vault", token="tkn")

    async def controlled_retry(coro_factory, attempts: int = 3, **kwargs):
        last_exc = None
        for _ in range(attempts):
            try:
                return await coro_factory()
            except Exception as e:  # noqa: BLE001
                last_exc = e
                continue
        raise last_exc  # type: ignore[misc]

    monkeypatch.setattr("app.src.services.vault.retry", controlled_retry)
    v.api = fake_api

    with pytest.raises(RuntimeError):
        await v.read_secret("/kv/app/secret")

