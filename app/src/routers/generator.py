import asyncio
import yaml
from fastapi import HTTPException, Depends
from typing import List
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from starlette.responses import JSONResponse
from ..models.remove_check import RemoveCheckRequest, RemoveCheckResponse
from ..schemas import schema_to_model
import re
from loguru import logger
from app.src.models.resource_metadata import ResourceMetadata
from ..services.argocd import build_app_name
from ..utils import config as cfg
from app.general.utils import basicSettings
import inspect
from app.hooks import HOOK_REGISTRY


def _normalize(data):
    if isinstance(data, dict):
        return {k: _normalize(v) for k, v in sorted(data.items())}
    if isinstance(data, list):
        return sorted((_normalize(i) for i in data), key=lambda x: str(x))
    return data


def yaml_data_equals(yaml_data_1, yaml_data_2):
    if isinstance(yaml_data_1, str):
        yaml_data_1 = yaml.safe_load(yaml_data_1)
    if isinstance(yaml_data_2, str):
        yaml_data_2 = yaml.safe_load(yaml_data_2)

    return _normalize(yaml_data_1) == _normalize(yaml_data_2)


def parse_payload(payload):
    data = payload.model_dump(mode="json")

    # Extract routing metadata
    namespace = data.pop("namespace")
    app_name = data.pop("applicationName")
    cluster = data.pop("cluster")

    # Extract values and secrets (support both top-level and values.secrets)
    values = dict(data.get("values") or {})
    secrets = data.get("secrets") or values.get("secrets") or {}

    # Sanitize values for Git by removing any secrets
    if "secrets" in values:
        values.pop("secrets", None)

    yaml_data = yaml.safe_dump(values, sort_keys=False)
    path = f'/{cluster}/{namespace}/{app_name}.yaml'

    return path, yaml_data, cluster, namespace, app_name, secrets


# --- Namespace helpers ---
def _namespaces_to_list(raw):
    """Coerce a namespaces value (string/list/None) into a clean list of strings."""
    if raw is None:
        return []
    if isinstance(raw, str):
        return [ns.strip() for ns in raw.split(",") if ns and ns.strip()]
    if isinstance(raw, list):
        return [str(ns).strip() for ns in raw if str(ns).strip()]
    return []


def _serialize_namespaces(namespaces, original_value):
    """Serialize a list of namespaces back to the original type (list or comma string).

    If the original was a list, keep it a list; otherwise, use a comma-separated string
    to maintain backward compatibility with existing values.
    """
    clean = [str(ns).strip() for ns in namespaces if str(ns).strip()]
    if isinstance(original_value, list):
        return clean
    return ", ".join(clean)


from typing import Optional, Dict


class RouterGenerator:
    def __init__(self, app, resource, git, schema_manager, argocd, vault, team_name, hooks_mapping: Optional[Dict[str, str]] = None):
        self.app = app
        self.resource = resource
        self.argocd = argocd
        self.git = git
        self.schema_manager = schema_manager
        self.models = {}
        self.vault = vault
        # Initialize team name once (provided by caller)
        self.team_name = team_name
        self.namespaces_clusters_map = dict()
        # Mapping of event -> function name and resolved callables via registry
        self.hooks_map = hooks_mapping or {}
        self.hooks_funcs = {evt: HOOK_REGISTRY.get(fn_name) for evt, fn_name in self.hooks_map.items()}

        # Validate all mapped functions exist in app/hooks (registry-backed)
        missing = [evt for evt, fn_name in self.hooks_map.items() if self.hooks_funcs.get(evt) is None]
        if missing:
            raise ValueError(f"Hook function(s) not found for events: {', '.join(missing)}. Ensure functions exist under app/hooks and are imported.")

    async def run(self):
        await self.create_namespaces_clusters_map()
        await self.schema_manager.load_all_schemas()
        await self.generate_routes()

    async def _run_hook(self, event: str, context: dict) -> dict:
        """Run hook by event name and merge returned updates into context.
        Returns the possibly updated context.
        """
        fn = getattr(self, 'hooks_funcs', {}).get(event)
        if not fn:
            return context
        if inspect.iscoroutinefunction(fn):
            result = await fn(**context)
        else:
            result = fn(**context)
        if isinstance(result, dict):
            context = {**context, **result}
        return context

    async def create_namespaces_clusters_map(self):
        clusters_map = {}
        for cluster in cfg.CLUSTERS:
            cluster_secret_values = yaml.safe_load(
                await self.argocd.get_app_values(f"{cluster}-cluster-secret")
            ) or {}
            raw_namespaces = cluster_secret_values.get("namespaces")
            namespaces = _namespaces_to_list(raw_namespaces)
            clusters_map[cluster] = namespaces
        self.namespaces_clusters_map = clusters_map


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
            description=f"Given cluster, namesapace, applicationName as params. Returns app status.",
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
            description=f"Given a cluster, a namespace and an app name. Deleting related {self.resource}.",
            tags=[f"delete {self.resource}"]
        )

        self._safe_add_api_route(
            "/",
            self._make_get_resource_configuration_handler(),
            methods=["GET"],
            name=f"Get specific {self.resource} configuration.",
            tags=["provision"],
            description=f"Given a cluster, a namespace and an app name. Returns related {self.resource} configuration."
        )


    def _make_delete_resource_handler(self):

        async def handler(params: ResourceMetadata = Depends()):

            cluster, namespace, name = params.cluster, params.namespace, params.name
            ctx = {
                "resource": self.resource,
                "operation": "delete",
                "cluster": cluster,
                "namespace": namespace,
                "name": name,
            }
            ctx["path"] = f'/{ctx["cluster"]}/{ctx["namespace"]}/{ctx["name"]}.yaml'
            ctx["app_name"] = build_app_name(ctx["cluster"], ctx["namespace"], ctx["name"], self.resource)

            ctx = await self._run_hook("pre_delete_hook", ctx)
            cluster = ctx.get("cluster", cluster)
            namespace = ctx.get("namespace", namespace)
            name = ctx.get("name", name)
            path = ctx.get("path") or f'/{cluster}/{namespace}/{name}.yaml'
            app_name = ctx.get("app_name") or build_app_name(cluster, namespace, name, self.resource)

            # 1) Delete file from git
            await self.git.delete_file(path, commit_message=f"delete {self.resource} {name} in {cluster}/{namespace}")

            # 2) Sync application
            logger.info(
                f"Triggered ArgoCD sync for {name}'s {self.resource} at cluster: {cluster} in namespace: {namespace}")
            await self.argocd.sync(app_name)

            # 3) Wait for app deletion (no longer accessible)
            await self.argocd.wait_for_app_deletion(app_name)

            # 4) Delete secrets only after deletion confirmed
            # Secret path format: /{resource}/{cluster}/{namespace}/{application_name}
            secret_path = f'/{self.resource}/{cluster}/{namespace}/{name}'
            await self.vault.delete_secret(secret_path)

            ctx.update({"secret_path": secret_path})
            await self._run_hook("post_delete_hook", ctx)

        return handler


    def _make_get_resource_configuration_handler(self):

        async def handler(params: ResourceMetadata = Depends()):

            cluster, namespace, name = params.cluster, params.namespace, params.name
            ctx = {
                "resource": self.resource,
                "operation": "read",
                "cluster": cluster,
                "namespace": namespace,
                "name": name,
            }
            ctx["path"] = f'/{ctx["cluster"]}/{ctx["namespace"]}/{ctx["name"]}.yaml'
            ctx = await self._run_hook("pre_read_hook", ctx)
            cluster = ctx.get("cluster", cluster)
            namespace = ctx.get("namespace", namespace)
            name = ctx.get("name", name)
            path = ctx.get("path") or f'/{cluster}/{namespace}/{name}.yaml'

            cfg = await self.git.get_file_content(path)

            ctx.update({"config": cfg})
            ctx = await self._run_hook("post_read_hook", ctx)
            return ctx.get("config", cfg)

        return handler


    def _make_update_resource_handler(self, version):

        model = self.get_model(version)

        async def handler(payload: model):

            path, yaml_data, cluster, namespace, app_name, secrets = parse_payload(payload)

            ctx = {
                "resource": self.resource,
                "operation": "update",
                "cluster": cluster,
                "namespace": namespace,
                "name": app_name,
                "path": path,
                "yaml_data": yaml_data,
                "secrets": secrets,
                "payload": payload.model_dump(mode="json"),
                "version": version,
            }
            ctx = await self._run_hook("pre_update_hook", ctx)
            cluster = ctx.get("cluster", cluster)
            namespace = ctx.get("namespace", namespace)
            app_name = ctx.get("name", app_name)
            path = ctx.get("path", path)
            yaml_data = ctx.get("yaml_data", yaml_data)
            secrets = ctx.get("secrets", secrets)

            current_data = await self.git.get_file_content(path)

            if yaml_data_equals(current_data, yaml_data):
                return JSONResponse(
                    status_code=200,
                    content={"message": "Resource already up to date", "values": current_data}
                )

            commit_message = f"modify {self.resource} for {app_name} in {cluster} on {namespace}"
            await self.git.modify_file(path, commit_message ,yaml_data)

            # Also write provided secrets to Vault
            if secrets:
                for key, value in secrets.items():
                    # Secret path format: /{resource}/{cluster}/{namespace}/{application_name}
                    secret_path = f"/{self.resource}/{cluster}/{namespace}/{app_name}"
                    await self.vault.write_secret(secret_path, {key: value})

            # Trigger ArgoCD sync (API handles errors/logging)
            await self.argocd.sync(app_name)

            # Update context in case local variables changed before post hook
            ctx.update({
                "cluster": cluster,
                "namespace": namespace,
                "name": app_name,
                "path": path,
                "yaml_data": yaml_data,
                "secrets": secrets,
            })
            await self._run_hook("post_update_hook", ctx)

            return JSONResponse(
                status_code=202,
                content={
                    "message": (
                        f"Update request accepted for {self.resource} "
                        f"app={app_name}, cluster={cluster}, namespace={namespace}"
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
            description=f"Given a cluster, a namespace and an app name. Updating related {self.resource} configuration."
        )


    def _get_version(self, version):

        def handler():
            return JSONResponse(content=self.schema_manager.resolved_schemas[version]["schema"])

        return handler


    def _make_resource_handler(self):

        async def handler(params: ResourceMetadata = Depends()):

            cluster, namespace, name = params.cluster, params.namespace, params.name

            app_name = build_app_name(cluster, namespace, name, self.resource)

            logger.info(
                f"Getting ArgoCD app status for {name}'s {self.resource} at cluster: {cluster} in namespace: {namespace}")

            sync_status = await self.argocd.get_app_status(app_name)

            return JSONResponse({
                "status": sync_status["status"],
                "version": sync_status["revision"]
                })

        return handler


    def _make_create_resource_handler(self, version):
        
        model = self.get_model(version)
        
        async def handler(payload: model):

            path, yaml_data, cluster, namespace, name, secrets = parse_payload(payload)
            namespaces = self.namespaces_clusters_map.get(cluster, [])

            ctx = {
                "resource": self.resource,
                "operation": "create",
                "cluster": cluster,
                "namespace": namespace,
                "name": name,
                "path": path,
                "yaml_data": yaml_data,
                "secrets": secrets,
                "payload": payload.model_dump(mode="json"),
                "version": version,
            }
            ctx = await self._run_hook("pre_create_hook", ctx)
            cluster = ctx.get("cluster", cluster)
            namespace = ctx.get("namespace", namespace)
            name = ctx.get("name", name)
            path = ctx.get("path", path)
            yaml_data = ctx.get("yaml_data", yaml_data)
            secrets = ctx.get("secrets", secrets)

            if namespace not in namespaces:
                updated_namespaces = [*namespaces, namespace]
                values = yaml.safe_load(
                    await self.argocd.get_app_values(f"{cluster}-cluster-secret")
                ) or {}
                original = values.get("namespaces")
                values["namespaces"] = _serialize_namespaces(updated_namespaces, original)

                await self.argocd.modify_values(values, f"{cluster}-cluster-secret", "argocd", "default")
                await self.argocd.sync(f"{cluster}-cluster-secret")

                self.namespaces_clusters_map[cluster] = updated_namespaces

            app_name = build_app_name(cluster, namespace, name, self.resource)

            await self.git.add_file(path, f"Create {self.resource} in {cluster=} on {namespace=} for {app_name=}" ,yaml_data)

            # Also write provided secrets to Vault
            if secrets:
                for key, value in secrets.items():
                    # Secret path format: /{resource}/{cluster}/{namespace}/{application_name}
                    secret_path = f"/{self.resource}/{cluster}/{namespace}/{name}"
                    await self.vault.write_secret(secret_path, {key: value})

            # Trigger ArgoCD sync
            logger.info(
                f"Triggered ArgoCD sync for {name}'s {self.resource} at cluster: {cluster} in namespace: {namespace}")
            await self.argocd.sync(app_name)

            # Refresh context and run post hook
            ctx.update({
                "cluster": cluster,
                "namespace": namespace,
                "name": name,
                "path": path,
                "yaml_data": yaml_data,
                "secrets": secrets,
            })
            await self._run_hook("post_create_hook", ctx)

            return JSONResponse(
                status_code=202,
                content={
                    "message": (
                        f"Create request accepted for {self.resource} "
                        f"app={app_name}, cluster={cluster}, namespace={namespace}"
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
            try:
                changed_versions = await self.schema_manager.sync_schemas(schema_poller_interval)
                await asyncio.sleep(0)

                for version in changed_versions:

                    path = f"/{version}"
                    definition_path = f"{path}/definition"

                    self.app.router.routes = [
                        r for r in self.app.router.routes
                        if not (
                            isinstance(r, APIRoute)
                            and r.path in {
                                f"/v1/{self.resource}/{path.lstrip('/')}",
                                f"/v1/{self.resource}/{definition_path.lstrip('/')}"
                            }
                        )
                    ]

                    model_name = f"{self.resource}_{version}_Model"
                    if model_name in self.models:
                        del self.models[model_name]

                await self.generate_routes()

                self.update_openapi_schema()

            except asyncio.CancelledError:
                logger.info(f"Schema syncer for {self.resource} cancelled. Exiting loop.")
                raise
            except Exception as e:
                logger.error(f"Schema syncer error for {self.resource}: {e}")
                # Back off before retrying to avoid tight error loops
                await asyncio.sleep(schema_poller_interval) 


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
            schema = get_openapi(
                title="Your API",
                version=basicSettings.OPENAPI_VERSION,
                description="Dynamic API example",
                routes=self.app.router.routes,
            )
            root_path = self.app.root_path or ""
            if root_path:
                schema["servers"] = [{"url": root_path}]
            return schema

        # Clear cache and assign
        self.app.openapi_schema = None
        self.app.openapi = custom_openapi
