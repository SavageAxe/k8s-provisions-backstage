import json

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from starlette.responses import JSONResponse

from app.src.schemas.loader import SchemaLoader
from ..utils import config, resources_config
from ..schemas import schema_to_model
from app.src.gitops.values_writer import GitValuesWriter
from loguru import logger
import re
from app.src.services.argocd import ArgoCD
from app.src.models.resource_metadata import ResourceMetadata
from ...general.utils import basicSettings


class ProvisionRouter:
    def __init__(self, app):
        self.app = app
        self.router = APIRouter()
        self.config = config.get_instance()
        self.git_writer = GitValuesWriter(logger)
        self.argocd = ArgoCD(config.ARGOCD_URL, config.ARGOCD_TOKEN, config.APPLICATION_SET_TIMEOUT)
        self.schemas = SchemaLoader()
        self.models = {}
        self.schemas.load_all_schemas()
        self._register_dynamic_routes()


    def _register_dynamic_routes(self):

        for resource, versions in self.schemas.resolved_schemas.items():


            self.router.add_api_route(
                f"/{resource}",
                self._add_version(resource),
                methods=["POST"],
                name=f"add version to {resource}",
                tags=["add version"],
            )

            self.router.add_api_route(
                f"/{resource}/status",
                self._make_resource_handler(resource),
                methods=["GET"],
                name=f"get apps statuses for {resource}",
                tags=["get status"],
            )

            for version in versions:
                if re.fullmatch(r"\d+\.\d+\.\d+", version):

                    self._register_resource_version_routes(resource, version)


    def _remove_resource_version_routes(self, resource, version):
        path = f"/v1/{resource}/{version}"
        definition_path = f"{path}/definition"

        self.app.router.routes = [
            r for r in self.app.router.routes
            if not (isinstance(r, APIRoute) and r.path in {path, definition_path})
        ]

        self.update_openapi_schema()


    def _add_version(self, resource):

        async def handler(request: dict):

            version = request["version"]
            schema = request["schema"]

            self.schemas.schemas[resource][version] = schema
            self.schemas.resolve_schemas(resource)

            self._register_resource_version_routes(resource, version)

            return JSONResponse(status_code=200, content=self.schemas.resolved_schemas[resource][version])


        return handler

    def _register_resource_version_routes(self, resource, version):

        path = f"/{resource}/{version}"
        definition_path = f"{path}/definition"

        self.router.add_api_route(
            path,
            self._make_version_handler(resource, version),
            methods=["POST"],
            name=f"provision_{resource}_{version}",
            tags=["provision"],
        )

        self.router.add_api_route(
            definition_path,
            self._get_version(resource, version),
            methods=["GET"],
            name=f"get {resource} {version}'s schema",
            tags=["get version schema"],
        )

        self.router.add_api_route(
            definition_path,
            self._modify_version(resource, version),
            methods=["PATCH"],
            name=f"reload {resource} {version}'s schema",
            tags=["reload version"],
        )

        self.router.add_api_route(
            definition_path,
            self._delete_version(resource, version),
            methods=["DELETE"],
            name=f"delete {resource} {version}'s schema",
            tags=["delete version"],
        )

        self.app.include_router(self.router, prefix='/v1')
        self.update_openapi_schema()

    def _get_version(self, resource, version):

        schema = self.schemas.resolved_schemas[resource][version]

        def handler():

            return JSONResponse(content=schema)

        return handler

    def _delete_version(self, resource, version):

        def handler():

            self._remove_resource_version_routes(resource, version)

            return JSONResponse(content={"status": "ok"})

        return handler

    def _modify_version(self, resource, version):

        async def handler(request: dict):
            self.schemas.schemas[resource][version] = request
            self.schemas.resolve_schemas(resource)

            model_name = f"{resource}_{version}_Model"
            self.models[model_name] = schema_to_model(model_name, self.schemas.resolved_schemas[resource][version])

            self._remove_resource_version_routes(resource, version)
            self._register_resource_version_routes(resource, version)

            return JSONResponse(content={"message": f"Schema reloaded for {resource} {version}"})

        return handler


    def _make_resource_handler(self, resource):

        async def handler(params: ResourceMetadata = Depends()):

            region, namespace, name = params.region, params.namespace, params.name

            sync_status = await self.argocd.get_app_status(region, namespace, name, resource)

            return JSONResponse({
                "status": sync_status["status"],
                "version": sync_status["revision"]
                })

        return handler


    def _make_version_handler(self, resource, version):

        schema = self.schemas.resolved_schemas.get(resource, {}).get(version)
        if not schema:
            raise HTTPException(status_code=404, detail=f"Schema for {resource} version {version} not found")

        model_name = f"{resource}_{version}_Model"
        if not model_name in self.models:
            self.models[model_name] = schema_to_model(f"{resource}_{version}_Model", schema)
        model = self.models[model_name]

        async def handler(payload: model):
            payload = payload.dict()

            # REFACTOR THIS with some of tyk orc git logic
            resource_config = resources_config.get(resource, {})
            repo_url = resource_config['VALUES_REPO_URL']
            private_key_path = resource_config['VALUES_REPO_PRIVATE_KEY']

            if not repo_url or not private_key_path:
                raise RuntimeError(f"no repo url or private key. For {resource}.")

            # Write YAML to Git
            namespace = payload.pop('namespace')
            app_name = payload.pop('applicationName')
            region = payload.pop('region')
            yaml_data = payload
            self.git_writer.write_and_commit(region, namespace, app_name, yaml_data, repo_url, private_key_path)

            # Trigger ArgoCD sync
            await self.argocd.sync(region, namespace, app_name, resource)

            return JSONResponse(status_code=201, content={"message": f"Successfully provisioned {resource} for app: {app_name} at Region: {region}, in Namespace: {namespace}"})

        return handler

    def update_openapi_schema(self):
        # Manually regenerate the OpenAPI schema
        self.app.openapi_schema = get_openapi(
            title="Your API",
            version=basicSettings.OPENAPI_VERSION,
            description="Dynamic API example",
            routes=self.app.routes
        )