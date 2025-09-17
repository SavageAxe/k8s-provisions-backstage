import os
from typing import Optional

from pydantic_settings import SettingsConfigDict
from pydantic import Field
from ...general.utils.config import BasicSettings
from ..models.hooks import ResourceHookMapping
import json


class Config(BasicSettings):
    _instance = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8",extra="allow")

    SCHEMA_POLLER_INTERVAL: int = Field(
        description="Interval in seconds between polling for configuration changes.",
        default=10,
        examples=[10, 60]
    )

    ARGOCD_URL: str = Field(
        description="The service owner's ArgoCD URL.",
        examples=["http://localhost:8080", "https://my.argo.cd.fqdn"],
    )

    ARGOCD_TOKEN: str = Field(
        description="The service owner's ArgoCD token.",
        examples=["eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJPbmxpbmUgSldUIEJ1aWxkZXIiLCJpYXQiOjE3NTM2MzkyMzQsImV4cCI6MTc4NTE3NTIzNCwiYXVkIjoid3d3LmV4YW1wbGUuY29tIiwic3ViIjoianJvY2tldEBleGFtcGxlLmNvbSIsIkdpdmVuTmFtZSI6IkpvaG5ueSIsIlN1cm5hbWUiOiJUaGUgR09BVCIsIkVtYWlsIjoiam9oblRoZUdvYXRAc2hla2VyLmNvbSIsIlJvbGUiOlsiS2luZyIsIkdvYXQiXX0.80uewOWbkWMT8XeLfTXGr8ohiOQt98neFgH8P6lX6bw"]
    )

    APPLICATION_SET_TIMEOUT: int = Field(
        default=60,
        description="The time in seconds to wait for an application set create application.",
        examples=[10, 15],
    )


    CLUSTERS: list[str] = Field(
        description="A list of clusters where resources could be created.",
        examples=[["dev", "test"],["qa", "int"]]
    )

    VAULT_URL: str = Field(
        description="Base URL for HashiCorp Vault (e.g., https://vault.company.com)",
        examples=["http://localhost:8200", "https://vault.example.com"]
    )

    VAULT_TOKEN: str = Field(
        description="Token used to authenticate to Vault.",
        examples=["hvs.CAESIJ...", "s.xxxxxx"]
    )

    TEAM_NAME: str = Field(
        description="Team name used as Vault mount path prefix.",
        examples=["perimeter", "platform"],
    )

    REPO_URL: Optional[str] = None

    ACCESS_TOKEN: Optional[str] = None


    def model_post_init(self, __context):

        for k, v in os.environ.items():

            if k.endswith("_REPO_URL"):
                if not v.startswith("https://"):
                    raise ValueError(f"Invalid repo url {v!r} from {k}. Must start with 'https://'")
                object.__setattr__(self, "REPO_URL", v)

            if k.endswith("_ACCESS_TOKEN"):
                object.__setattr__(self, "ACCESS_TOKEN", v)


    def get_resource_config(self, resource: str):
        hooks_raw = os.getenv(f'{resource.upper()}_HOOKS')
        # Expect a JSON object: {"pre_create_hook": "create_org", ...}
        if hooks_raw:
            try:
                loaded = json.loads(hooks_raw)
                if not isinstance(loaded, dict):
                    loaded = {}
            except Exception:
                loaded = {}
            validated = ResourceHookMapping(hooks=loaded).hooks
        else:
            validated = {}

        return {
            'VALUES_REPO_URL': os.getenv(f'{resource.upper()}_VALUES_REPO_URL'),
            'SCHEMAS_REPO_URL': os.getenv(f'{resource.upper()}_SCHEMAS_REPO_URL'),
            'VALUES_ACCESS_TOKEN': os.getenv(f'{resource.upper()}_VALUES_ACCESS_TOKEN'),
            'SCHEMAS_ACCESS_TOKEN': os.getenv(f'{resource.upper()}_SCHEMAS_ACCESS_TOKEN'),
            # Validated mapping of event -> function name
            'HOOKS': validated,
        }
