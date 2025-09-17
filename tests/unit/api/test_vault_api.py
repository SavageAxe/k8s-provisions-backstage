import json
import pytest
import httpx

from app.src.api.vault import (
    handle_response,
    generate_secret_path,
    generate_metadata_path,
    VaultError,
)


def _make_json_response(status_code: int, payload: dict) -> httpx.Response:
    req = httpx.Request("GET", "http://vault.local/v1/test")
    content = json.dumps(payload).encode()
    return httpx.Response(
        status_code,
        request=req,
        content=content,
        headers={"Content-Type": "application/json"},
    )


def test_generate_secret_path():
    assert generate_secret_path("/secret/app/foo") == "secret/data/app/foo"
    assert generate_secret_path("secret/app/foo") == "secret/data/app/foo"
    assert generate_secret_path("/kv/app") == "kv/data/app"


def test_generate_metadata_path():
    assert generate_metadata_path("/secret/app/foo") == "secret/metadata/app/foo"
    assert generate_metadata_path("secret/app/foo") == "secret/metadata/app/foo"
    assert generate_metadata_path("/kv/app") == "kv/metadata/app"


def test_handle_response_success_noop():
    # 200 OK
    resp_ok = _make_json_response(200, {"data": {}})
    handle_response(resp_ok)  # should not raise

    # 204 No Content
    req = httpx.Request("DELETE", "http://vault.local/v1/test")
    resp_no_content = httpx.Response(204, request=req)
    handle_response(resp_no_content)  # should not raise


def test_handle_response_raises_vault_error():
    resp_err = _make_json_response(400, {"errors": ["some error"]})
    with pytest.raises(VaultError) as ei:
        handle_response(resp_err)
    assert ei.value.status_code == 400
    assert "Vault message" in str(ei.value.detail)

