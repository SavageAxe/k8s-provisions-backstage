import yaml
from fastapi import APIRouter, HTTPException, Depends
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from starlette.responses import JSONResponse
from ..schemas import schema_to_model
import re
from app.src.models.resource_metadata import ResourceMetadata
from ...general.utils import basicSettings


class RouterGenerator:
    def __init__(self, app, resource, git, schema_manager, argocd):
        self.app = app
        self.resource = resource
        self.router = APIRouter()
        self.argocd = argocd
        self.git = git
        self.schema_manager = schema_manager
        self.models = {}
        self.schema_manager.load_all_schemas()
        self._generate_routes()


    def _generate_routes(self):

        for version, schema in self.schema_manager.resolved_schemas.items():

            self.router.add_api_route(
                "/",
                self._add_version(),
                methods=["POST"],
                name=f"add version to {self.resource}",
                tags=["add version"],
            )

            self.router.add_api_route(
                "/status",
                self._make_resource_handler(),
                methods=["GET"],
                name=f"get apps statuses for {self.resource}",
                tags=["get status"],
            )

            if re.fullmatch(r"\d+\.\d+\.\d+", version):
                self._register_resource_version_routes(version)


    def _remove_resource_version_routes(self, version):
        path = f"/v1/{self.resource}/{version}"
        definition_path = f"{path}/definition"

        self.app.router.routes = [
            r for r in self.app.router.routes
            if not (isinstance(r, APIRoute) and r.path in {path, definition_path})
        ]

        self.update_openapi_schema()


    def _add_version(self):

        async def handler(request: dict):

            version = request["version"]
            schema = request["schema"]

            self.schema_manager.schemas[version] = schema
            self.schema_manager.resolve_schemas()

            self._register_resource_version_routes(version)

            return JSONResponse(status_code=200, content=self.schema_manager.resolved_schemas[version])

        return handler

    def _register_resource_version_routes(self, version):

        path = f"/{version}"
        definition_path = f"{path}/definition"

        self.router.add_api_route(
            path,
            self._make_version_handler(version),
            methods=["POST"],
            name=f"provision_{self.resource}_{version}",
            tags=["provision"],
        )

        self.router.add_api_route(
            definition_path,
            self._get_version(version),
            methods=["GET"],
            name=f"get {self.resource} {version}'s schema",
            tags=["get version schema"],
        )

        self.router.add_api_route(
            definition_path,
            self._modify_version(version),
            methods=["PATCH"],
            name=f"reload {self.resource} {version}'s schema",
            tags=["reload version"],
        )

        self.router.add_api_route(
            definition_path,
            self._delete_version(version),
            methods=["DELETE"],
            name=f"delete {self.resource} {version}'s schema",
            tags=["delete version"],
        )

        self.app.include_router(self.router, prefix='/v1')
        self.update_openapi_schema()

    def _get_version(self, version):

        def handler():
            return JSONResponse(content=self.schema_manager.resolved_schemas[version])

        return handler

    def _delete_version(self, version):

        def handler():

            self._remove_resource_version_routes(version)

            return JSONResponse(content={"status": "ok"})

        return handler

    def _modify_version(self, version):

        async def handler(request: dict):

            self.schema_manager.schemas[version] = request
            self.schema_manager.resolve_schemas()

            model_name = f"{self.resource}_{version}_Model"
            self.models[model_name] = schema_to_model(model_name, self.schema_manager.resolved_schemas[version])

            self._remove_resource_version_routes(version)
            self._register_resource_version_routes(version)

            return JSONResponse(content={"message": f"Schema reloaded for {self.resource} {version}"})

        return handler


    def _make_resource_handler(self):

        async def handler(params: ResourceMetadata = Depends()):

            region, namespace, name = params.region, params.namespace, params.name

            sync_status = await self.argocd.get_app_status(region, namespace, name, self.resource)

            return JSONResponse({
                "status": sync_status["status"],
                "version": sync_status["revision"]
                })

        return handler


    def _make_version_handler(self, version):

        schema = self.schema_manager.resolved_schemas.get(version)
        if not schema:
            raise HTTPException(status_code=404, detail=f"Schema for {self.resource} version {version} not found")

        model_name = f"{self.resource}_{version}_Model"
        if not model_name in self.models:
            self.models[model_name] = schema_to_model(f"{self.resource}_{version}_Model", schema)
        model = self.models[model_name]

        async def handler(payload: model):
            data = payload.model_dump(mode="json")

            # Write YAML to Git
            namespace = data.pop("namespace")
            app_name = data.pop("applicationName")
            region = data.pop("region")
            yaml_data = yaml.safe_dump(data, sort_keys=False)

            await self.git.add_values(region, namespace, app_name, self.resource, yaml_data)

            # Trigger ArgoCD sync
            await self.argocd.sync(region, namespace, app_name, self.resource)

            return JSONResponse(status_code=201, content={"message": f"Successfully provisioned {self.resource} for app: {app_name} at Region: {region}, in Namespace: {namespace}"})

        return handler

    def update_openapi_schema(self):
        # Manually regenerate the OpenAPI schema
        self.app.openapi_schema = get_openapi(
            title="Your API",
            version=basicSettings.OPENAPI_VERSION,
            description="Dynamic API example",
            routes=self.app.routes
        )
