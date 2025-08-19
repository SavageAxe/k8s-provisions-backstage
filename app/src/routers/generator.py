import yaml
from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List
from starlette.responses import JSONResponse
from ..models.remove_check import RemoveCheckRequest, RemoveCheckResponse
from ..schemas import schema_to_model
import re
from app.src.models.resource_metadata import ResourceMetadata



class RouterGenerator:
    def __init__(self, app, resource, git, schema_manager, argocd):
        self.app = app
        self.resource = resource
        self.router = APIRouter()
        self.argocd = argocd
        self.git = git
        self.schema_manager = schema_manager
        self.models = {}


    async def generate_routes(self):

        for version, schema in self.schema_manager.resolved_schemas.items():

            self.router.add_api_route(
                "/status",
                self._make_resource_handler(),
                methods=["GET"],
                name=f"get apps statuses for {self.resource}",
                tags=["get status"],
            )

            self.router.add_api_route(
                "/schemas/can-remove",
                self._create_can_remove_handler(),
                methods=["POST"],
                name=f"can-remove schemas for {self.resource}",
                tags=["can-remove"],
                description="Given a list of schema names, validates if each can be safely removed",
                response_model=List[RemoveCheckResponse]
            )

            if re.fullmatch(r"\d+\.\d+\.\d+", version):
                self._register_resource_version_routes(version)


    def _create_can_remove_handler(self):

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

        self.app.include_router(self.router, prefix=f'/v1/{self.resource}')

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


    def _make_version_handler(self, version):

        schema = self.schema_manager.resolved_schemas.get(version)["schema"]
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
            path = f'/{region}/{namespace}/{app_name}.yaml'
            await self.git.add_files(path, yaml_data)

            # Trigger ArgoCD sync
            await self.argocd.sync(region, namespace, app_name, self.resource)

            return JSONResponse(status_code=201, content={"message": f"Successfully provisioned {self.resource} for app: {app_name} at Region: {region}, in Namespace: {namespace}"})

        return handler
