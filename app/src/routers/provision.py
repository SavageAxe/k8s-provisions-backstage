from fastapi import APIRouter, Request, HTTPException
from ..utils import config
from app.src.schemas.validator import SchemaValidator
from app.src.gitops.values_writer import GitValuesWriter
from app.src.argocd.sync import ArgoCDSyncer
from ..utils import resources_config
from loguru import logger

class ProvisionRouter:
    def __init__(self, schemas_cache):
        self.router = APIRouter()
        self.config = config.get_instance()
        self.git_writer = GitValuesWriter(logger)
        self.argocd = ArgoCDSyncer(logger)
        self.schemas_cache = schemas_cache
        self._register_dynamic_routes()

    def _register_dynamic_routes(self):
        for resource, versions in self.schemas_cache.items():
            for version in versions:
                if version != "base":
                    path = f"/{resource}/{version}"
                    self.router.add_api_route(
                        path,
                        self._make_handler(resource, version),
                        methods=["POST"],
                        name=f"provision_{resource}_{version}",
                        tags=[f"{resource} v{version}"]
                    )

    def _make_handler(self, resource, version):
        async def handler(request: Request):
            payload = await request.json()
            schema = self.schemas_cache.get(resource, {}).get(version)
            if not schema:
                raise HTTPException(status_code=404, detail=f"Schema for {resource} version {version} not found")
            try:
                SchemaValidator(schema, self.schemas_cache).validate(payload)
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e))
            resource_config = resources_config.get(resource, {})
            repo_url = resource_config['VALUES_REPO_URL']
            private_key_path = resource_config['VALUES_REPO_PRIVATE_KEY']
            if not repo_url or not private_key_path:
                raise HTTPException(status_code=500, detail="Missing Git repo config for resource")
            # Write YAML to Git
            try:
                namespace = payload['namespace']
                app_name = payload['applicationName']
                region = payload['region']
                yaml_data = payload
                rel_path = self.git_writer.write_and_commit(region, namespace, app_name, yaml_data, repo_url, private_key_path)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"GitOps error: {e}")
            # Trigger ArgoCD sync
            try:
                sync_result = self.argocd.sync(region, namespace, resource, app_name, config.ARGOCD_URL, config.ARGOCD_TOKEN)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"ArgoCD sync error: {e}")
            return {"status": "success", "git": rel_path, "argocd": sync_result}
        return handler
