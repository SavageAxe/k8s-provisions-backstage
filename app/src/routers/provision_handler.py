import yaml
from fastapi import HTTPException
from starlette.responses import JSONResponse
from ..services.git import Git
from ..schemas import schema_to_model
from ..utils import resources_config

def make_provision_handler(resource: str, version: str,
                           schema_manager, models_store: dict,
                           argocd, git_writer=None):
    schema = schema_manager.resolved_schemas.get(resource, {}).get(version)
    if not schema:
        raise HTTPException(status_code=404, detail=f"Schema for {resource} version {version} not found")

    model_name = f"{resource}_{version}_Model"
    if model_name not in models_store:
        models_store[model_name] = schema_to_model(model_name, schema)
    model = models_store[model_name]

    async def handler(payload: model):
        data = payload.model_dump(mode="json")

        cfg = resources_config.get(resource, {})
        repo_url = cfg.get("VALUES_REPO_URL")
        # private_key_path = cfg.get("VALUES_REPO_PRIVATE_KEY")
        # if not repo_url or not private_key_path:
        #     raise RuntimeError(f"no repo url or private key for {resource}")
        access_token = cfg.get("VALUES_ACCESS_TOKEN")
        if not repo_url or not access_token:
            raise RuntimeError(f"no repo url or access token for {resource}")

        git = Git(repo_url, access_token)

        namespace = data.pop("namespace")
        app_name = data.pop("applicationName")
        region = data.pop("region")
        yaml_data = yaml.safe_dump(data, sort_keys=False)

        await git.add_values(region, namespace, app_name, resource, yaml_data)

        # git_writer.write_and_commit(region, namespace, app_name, yaml_data, repo_url, private_key_path)

        await argocd.sync(region, namespace, app_name, resource)

        return JSONResponse(
            status_code=201,
            content={"message": f"Successfully provisioned {resource} for app: {app_name} at Region: {region}, in Namespace: {namespace}"},
        )

    return handler
