import asyncio
import yaml
from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from starlette.responses import JSONResponse
from ..models.remove_check import RemoveCheckRequest, RemoveCheckResponse
from ..schemas import schema_to_model
import re
from app.src.models.resource_metadata import ResourceMetadata
from ..schemas.loader import normalize_name
from ..utils import config as cfg
from app.general.utils import basicSettings

def parse_payload(payload):
    data = payload.model_dump(mode="json")

    # Write YAML to Git
    namespace = data.pop("namespace")
    app_name = data.pop("applicationName")
    region = data.pop("region")
    yaml_data = yaml.safe_dump(data, sort_keys=False)
    path = f'/{region}/{namespace}/{app_name}.yaml'

    return path, yaml_data, region, namespace, app_name



class RouterGenerator:
    def __init__(self, app, resource, git, schema_manager, argocd):
        self.app = app
        self.resource = resource
        self.argocd = argocd
        self.git = git
        self.schema_manager = schema_manager
        self.models = {}


    async def generate_routes(self):

        for version, schema in self.schema_manager.resolved_schemas.items():

            self._register_resource_general_routes()


            if re.fullmatch(r"\d+\.\d+\.\d+", version):
                self._register_resource_version_routes(version)


    def _register_resource_general_routes(self):

        self._safe_add_api_route(
            "/status",
            self._make_resource_handler(),
            methods=["GET"],
            name=f"get apps statuses for {self.resource}",
            description=f"Given region, namesapace, applicationName as params. Returns app status.",
            tags=["get status"]
        )

        self._safe_add_api_route(
            "/schemas/can-remove",
            self._make_can_remove_handler(),
            methods=["POST"],
            name=f"can-remove schemas for {self.resource}",
            description="Given a list of schema names, validates if each can be safely removed",
            tags=["can-remove"]
        )

        self._safe_add_api_route(
            "/",
            self._make_delete_resource_handler(),
            methods=["DELETE"],
            name=f"Uninstall specific {self.resource}",
            description=f"Given a region, a namespace and an app name. Deleting related {self.resource}.",
            tags=[f"delete {self.resource}"]
        )

        self._safe_add_api_route(
            "/",
            self._make_get_resource_configuration_handler(),
            methods=["GET"],
            name=f"Get specific {self.resource} configuration.",
            tags=["provision"],
            description=f"Given a region, a namespace and an app name. Returns related {self.resource} configuration."
        )


    def _make_delete_resource_handler(self):

        async def handler(params: ResourceMetadata = Depends()):

            region, namespace, name = params.region, params.namespace, params.name
            path = f'/{region}/{namespace}/{name}.yaml'

            await self.git.delete_file(path)

            try:
                self.argocd.sync(region, namespace, name, self.resource)

            except Exception as e:

                # return to previous commit

                raise e

        return handler


    def _make_get_resource_configuration_handler(self):

        async def handler(params: ResourceMetadata = Depends()):

            region, namespace, name = params.region, params.namespace, params.name
            path = f'/{region}/{namespace}/{name}.yaml'

            cfg = await self.git.get_file_content(path)

            return cfg

        return handler


    def _make_update_resource_handler(self, version):

        model = self.get_model(version)

        async def handler(payload: model):

            path, yaml_data, region, namespace, app_name = parse_payload(payload)
            await self.git.modify_file(path, yaml_data)

            # Trigger ArgoCD sync
            await self.argocd.sync(region, namespace, app_name, self.resource)

            return JSONResponse(
                status_code=202,
                content={
                    "message": (
                        f"Update request accepted for {self.resource} "
                        f"app={app_name}, region={region}, namespace={namespace}"
                    )
                }
            )


        return handler


    def _register_resource_version_routes(self, version):

        path = f"/{version}"
        definition_path = f"{path}/definition"

        self._safe_add_api_route(
            path,
            self._make_create_resource_handler(version),
            methods=["POST"],
            name=f"provision_{self.resource}_{version}",
            description=f"Given values in request body. Provisions {self.resource}.",
            tags=["provision"]
        )

        self._safe_add_api_route(
            definition_path,
            self._get_version(version),
            methods=["GET"],
            name=f"get {self.resource} {version}'s schema",
            description="Returns the version's schema",
            tags=["get version schema"]
        )

        self._safe_add_api_route(
            path,
            self._make_update_resource_handler(version),
            methods=["PATCH"],
            name=f"Modify specific {self.resource}",
            tags=["provision"],
            description=f"Given a region, a namespace and an app name. Updating related {self.resource} configuration."
        )


    def _get_version(self, version):

        def handler():
            return JSONResponse(content=self.schema_manager.resolved_schemas[version]["schema"])

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


    def _make_create_resource_handler(self, version):
        
        model = self.get_model(version)
        
        async def handler(payload: model):

            path, yaml_data, region, namespace, app_name = parse_payload(payload)
            await self.git.add_file(path, yaml_data)

            # Trigger ArgoCD sync
            await self.argocd.sync(region, namespace, app_name, self.resource)

            return JSONResponse(
                status_code=202,
                content={
                    "message": (
                        f"Create request accepted for {self.resource} "
                        f"app={app_name}, region={region}, namespace={namespace}"
                    )
                }
            )

        return handler


    def _make_can_remove_handler(self):

        async def handler(body: RemoveCheckRequest) -> List[RemoveCheckResponse]:

            results = []
            for schema_name in body.schemas:
                can_remove, reason = self.schema_manager.can_remove_schema(schema_name, body.schemas)
                results.append({
                    "schema_name": schema_name,
                    "can_remove": can_remove,
                    "reason": reason,
                })

            return results

        return handler


    def get_model(self, version):
        schema = self.schema_manager.resolved_schemas.get(version)["schema"]
        if not schema:
            raise HTTPException(status_code=404, detail=f"Schema for {self.resource} version {version} not found")

        model_name = f"{self.resource}_{version}_Model"
        if not model_name in self.models:
            self.models[model_name] = schema_to_model(f"{self.resource}_{version}_Model", schema)
        return self.models[model_name]


    async def sync_schemas(self):
        schema_poller_interval = cfg.SCHEMA_POLLER_INTERVAL
        while True:
            changed_versions = await self.schema_manager.sync_schemas(schema_poller_interval)
            await asyncio.sleep(0)

            for version in changed_versions:

                path = f"/{version}"
                definition_path = f"{path}/definition"

                self.app.router.routes = [
                    r for r in self.app.router.routes
                    if not (isinstance(r, APIRoute) and r.path in {f"/v1/{self.resource}/{path.lstrip('/')}", f"/v1/{self.resource}/{definition_path.lstrip('/')}"})
                ]

                model_name = f"{self.resource}_{version}_Model"
                if model_name in self.models:
                    del self.models[model_name]

            await self.generate_routes()

            self.update_openapi_schema()



    def _safe_add_api_route(
            self,
            path: str,
            handler_maker: callable,
            methods: list[str],
            description: str,
            name: str,
            tags: list[str]
    ):
        actual_path = f"/v1/{self.resource}/{path.lstrip('/')}"

        # Collect existing (path, frozenset(methods)) pairs
        existing = {
            (r.path, frozenset(r.methods))
            for r in list(self.app.router.routes)
            if isinstance(r, APIRoute)
        }

        # Allow same path if methods differ
        if (actual_path, frozenset(methods)) not in existing \
                and (f"/v1/{self.resource}{actual_path}", frozenset(methods)) not in existing:

            self.app.add_api_route(
                actual_path,
                handler_maker,
                methods=methods,
                name=name,
                description=description,
                tags=tags,
            )


    def update_openapi_schema(self):
        def custom_openapi():
            return get_openapi(
                title="Your API",
                version=basicSettings.OPENAPI_VERSION,
                description="Dynamic API example",
                routes=self.app.router.routes,
            )

        # Clear cache and assign
        self.app.openapi_schema = None
        self.app.openapi = custom_openapi