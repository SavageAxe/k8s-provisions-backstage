import re
from fastapi import APIRouter
from fastapi.routing import APIRoute
from loguru import logger

from app.src.schemas.loader import SchemaLoader
from app.src.gitops.values_writer import GitValuesWriter
from app.src.services.argocd import ArgoCD
from ..utils import config
from ..utils.openapi import update_openapi_schema
from .resource_handler import make_add_version_handler, make_resource_status_handler
from .version_handler import make_get_definition_handler, make_delete_definition_handler, make_patch_definition_handler
from .provision_handler import make_provision_handler

class RouterGenerator:
    def __init__(self, app):
        self.app = app
        self.router = APIRouter()
        self.git_writer = GitValuesWriter(logger)
        self.argocd = ArgoCD(config.ARGOCD_URL, config.ARGOCD_TOKEN, config.APPLICATION_SET_TIMEOUT)

        self.schema_manager = SchemaLoader()
        self.models = {}

        self.schema_manager.load_all_schemas()
        self._generate_routes()

        self.app.include_router(self.router, prefix="/v1")
        update_openapi_schema(self.app, "Dynamic Router", "Provision k8s instances")

    def register_version_routes(self, resource: str, version: str) -> None:
        self._register_resource_version_routes(resource, version)

    def remove_version_routes(self, resource: str, version: str) -> None:
        path = f"/v1/{resource}/{version}"
        definition_path = f"{path}/definition"
        self.app.router.routes = [
            r for r in self.app.router.routes
            if not (isinstance(r, APIRoute) and r.path in {path, definition_path})
        ]

    def _generate_routes(self) -> None:
        for resource, versions in self.schema_manager.resolved_schemas.items():
            self.router.add_api_route(
                f"/{resource}",
                make_add_version_handler(resource, self.schema_manager, self.register_version_routes),
                methods=["POST"],
                name=f"add version to {resource}",
                tags=["add version"],
            )
            self.router.add_api_route(
                f"/{resource}/status",
                make_resource_status_handler(resource, self.argocd),
                methods=["GET"],
                name=f"get apps statuses for {resource}",
                tags=["get status"],
            )
            for version in versions:
                if re.fullmatch(r"\d+\.\d+\.\d+", version):
                    self._register_resource_version_routes(resource, version)

    def _register_resource_version_routes(self, resource: str, version: str) -> None:
        path = f"/{resource}/{version}"
        definition_path = f"{path}/definition"

        self.router.add_api_route(
            path,
            make_provision_handler(resource, version, self.schema_manager, self.models, self.argocd, self.git_writer),
            methods=["POST"],
            name=f"provision_{resource}_{version}",
            tags=["provision"],
        )

        schema = self.schema_manager.resolved_schemas[resource][version]
        self.router.add_api_route(
            definition_path,
            make_get_definition_handler(schema),
            methods=["GET"],
            name=f"get {resource} {version}'s schema",
            tags=["get version schema"],
        )
        self.router.add_api_route(
            definition_path,
            make_patch_definition_handler(self.app, resource, version,
                                          self.schema_manager, self.models,
                                          self.remove_version_routes, self.register_version_routes),
            methods=["PATCH"],
            name=f"reload {resource} {version}'s schema",
            tags=["reload version"],
        )
        self.router.add_api_route(
            definition_path,
            make_delete_definition_handler(self.app, resource, version, self.remove_version_routes),
            methods=["DELETE"],
            name=f"delete {resource} {version}'s schema",
            tags=["delete version"],
        )
