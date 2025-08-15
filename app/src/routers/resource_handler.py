from fastapi import Depends
from starlette.responses import JSONResponse
from app.src.models.resource_metadata import ResourceMetadata

def make_add_version_handler(resource: str, schema_manager, register_callback):
    async def handler(request: dict):
        version = request["version"]
        schema = request["schema"]

        schema_manager.schemas.setdefault(resource, {})[version] = schema
        schema_manager.resolve_schemas(resource)

        register_callback(resource, version)
        return JSONResponse(status_code=200, content=schema_manager.resolved_schemas[resource][version])
    return handler


def make_resource_status_handler(resource: str, argocd):
    async def handler(params: ResourceMetadata = Depends()):
        region, namespace, name = params.region, params.namespace, params.name
        sync_status = await argocd.get_app_status(region, namespace, name, resource)
        return JSONResponse({"status": sync_status["status"], "version": sync_status["revision"]})
    return handler
