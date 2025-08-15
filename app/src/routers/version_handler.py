from ..models.schema_to_model import schema_to_model

def make_get_definition_handler(schema: dict):
    def handler():
        return JSONResponse(content=json_safe(schema))
    return handler

def make_delete_definition_handler(app, resource: str, version: str, remove_callback):
    def handler():
        remove_callback(resource, version)
        update_openapi_schema(app)
        return JSONResponse(content={"status": "ok"})
    return handler

def make_patch_definition_handler(app, resource: str, version: str,
                                  schema_manager, models_store: dict,
                                  remove_callback, register_callback):
    async def handler(request: dict):
        schema_manager.schemas[resource][version] = request
        schema_manager.resolve_schemas(resource)

        model_name = f"{resource}_{version}_Model"
        models_store[model_name] = schema_to_model(model_name, schema_manager.resolved_schemas[resource][version])

        remove_callback(resource, version)
        register_callback(resource, version)
        update_openapi_schema(app)

        return JSONResponse(content={"message": f"Schema reloaded for {resource} {version}"})
    return handler

def json_safe(obj):
    # tiny helper if you ever inject non JSON serializable values
    return obj
from starlette.responses import JSONResponse
from ..utils.openapi import update_openapi_schema
from ..schemas import schema_to_model

def make_get_definition_handler(schema: dict):
    def handler():
        return JSONResponse(content=json_safe(schema))
    return handler

def make_delete_definition_handler(app, resource: str, version: str, remove_callback):
    def handler():
        remove_callback(resource, version)
        update_openapi_schema(app, "Dynamic Router", "Provision k8s instances")
        return JSONResponse(content={"status": "ok"})
    return handler

def make_patch_definition_handler(app, resource: str, version: str,
                                  schema_manager, models_store: dict,
                                  remove_callback, register_callback):
    async def handler(request: dict):
        schema_manager.schemas[resource][version] = request
        schema_manager.resolve_schemas(resource)

        model_name = f"{resource}_{version}_Model"
        models_store[model_name] = schema_to_model(model_name, schema_manager.resolved_schemas[resource][version])

        remove_callback(resource, version)
        register_callback(resource, version)
        update_openapi_schema(app, "Dynamic Router", "Provision k8s instances")

        return JSONResponse(content={"message": f"Schema reloaded for {resource} {version}"})
    return handler

def json_safe(obj):
    return obj