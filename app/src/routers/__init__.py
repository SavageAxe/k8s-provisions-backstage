import asyncio

from fastapi import FastAPI

from .generator import RouterGenerator
from ..utils import resources_config
from ..schemas.loader import SchemaLoader
from ..services.git import Git
from ..services.argocd import ArgoCD
from ..utils import config as cfg

async def generate_router(app):
    argocd_url, argocd_token, application_set_timeout = cfg.ARGOCD_URL, cfg.ARGOCD_TOKEN, cfg.APPLICATION_SET_TIMEOUT
    for resource in resources_config:
        config = resources_config[resource]
        schemas_git = Git(config["SCHEMAS_REPO_URL"], config["SCHEMAS_ACCESS_TOKEN"])
        schema_manager = SchemaLoader(resource, schemas_git)
        values_git = Git(config["VALUES_REPO_URL"], config["VALUES_ACCESS_TOKEN"])
        argocd = ArgoCD(argocd_url, argocd_token, application_set_timeout)
        router_generator = RouterGenerator(app, resource, values_git, schema_manager, argocd)
        await router_generator.schema_manager.load_all_schemas()
        await router_generator.generate_routes()
        app.include_router(router_generator.router, prefix=f"/v1/{resource}")

    return app