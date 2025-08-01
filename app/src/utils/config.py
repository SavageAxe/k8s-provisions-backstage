import os
from pydantic_settings import SettingsConfigDict
from pydantic import Field
from ...general.utils.config import BasicSettings



class Config(BasicSettings):
    _instance = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8",extra="allow")

    ARGOCD_URL: str = Field(
        description="The service owner's ArgoCD URL.",
        examples=["http://localhost:8080", "https://my.argo.cd.fqdn"],
    )

    ARGOCD_TOKEN: str = Field(
        description="The service owner's ArgoCD token.",
        examples=["eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJPbmxpbmUgSldUIEJ1aWxkZXIiLCJpYXQiOjE3NTM2MzkyMzQsImV4cCI6MTc4NTE3NTIzNCwiYXVkIjoid3d3LmV4YW1wbGUuY29tIiwic3ViIjoianJvY2tldEBleGFtcGxlLmNvbSIsIkdpdmVuTmFtZSI6IkpvaG5ueSIsIlN1cm5hbWUiOiJUaGUgR09BVCIsIkVtYWlsIjoiam9oblRoZUdvYXRAc2hla2VyLmNvbSIsIlJvbGUiOlsiS2luZyIsIkdvYXQiXX0.80uewOWbkWMT8XeLfTXGr8ohiOQt98neFgH8P6lX6bw"]
    )

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_resource_config(self, resource: str):
        return {
            'VALUES_REPO_URL': os.getenv(f'{resource.upper()}_VALUES_REPO_URL'),
            'VALUES_REPO_PRIVATE_KEY': os.getenv(f'{resource.upper()}_VALUES_REPO_PRIVATE_KEY'),
            'SCHEMAS_REPO_URL': os.getenv(f'{resource.upper()}_SCHEMAS_REPO_URL'),
            'SCHEMAS_REPO_PRIVATE_KEY': os.getenv(f'{resource.upper()}_SCHEMAS_REPO_PRIVATE_KEY'),
        }