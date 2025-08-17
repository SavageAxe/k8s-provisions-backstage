from .generator import RouterGenerator
from ..utils import resources_config
from ..schemas.loader import SchemaLoader
from ..services.git import Git
from ..services.argocd import ArgoCD
from ..utils import config as cfg

def generate_router(app):
    argocd_url, argocd_token, application_set_timeout = cfg.ARGOCD_URL, cfg.ARGOCD_TOKEN, cfg.APPLICATION_SET_TIMEOUT
    for resource in resources_config:
        config = resources_config[resource]
        schema_manager = SchemaLoader(config["SCHEMAS_REPO_URL"], resource, config["SCHEMAS_REPO_PRIVATE_KEY"])
        git = Git(config["VALUES_REPO_URL"], config["VALUES_ACCESS_TOKEN"])
        argocd = ArgoCD(argocd_url, argocd_token, application_set_timeout)
        router_generator = RouterGenerator(app, resource, git, schema_manager, argocd)
        app.include_router(router_generator.router, prefix=f"/v1/{resource}")

    return app