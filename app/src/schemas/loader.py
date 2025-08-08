import os
import tempfile
import json
import shutil
import re
from app.src.utils.config import Config
from loguru import logger
from ..utils import resources_config
from jsonschema import RefResolver
from copy import deepcopy


def deep_merge_props(target: dict, source: dict):
    for key, value in source.items():
        if (
                key in target and
                isinstance(target[key], dict) and
                isinstance(value, dict)
        ):
            deep_merge_props(target[key], value)  # recursively merge nested fields
        else:
            target[key] = value


def is_version(string):
    return string.startswith('schema-') and string.endswith('.json') and re.fullmatch(r"\d+\.\d+\.\d+", string.split('-')[1].rstrip(".json"))


class SchemaLoader:
    def __init__(self):
        self.config = Config.get_instance()
        self.schemas = {}  # {resource: {version: schema_dict}}
        self.resolved_schemas = {}

    def load_all_schemas(self):
        # Find all resources by env var pattern *_SCHEMAS_REPO_URL
        for key, value in os.environ.items():
            if key.endswith('_SCHEMAS_REPO_URL') and value:
                resource = key[:-len('_SCHEMAS_REPO_URL')].lower()
                self._load_resource_schemas(resource)
                self.resolve_schemas(resource)
        return self.resolved_schemas

    def _load_resource_schemas(self, resource):
        config = resources_config.get(resource, {})

        # REFACTOR THIS with some of tyk orc git logic
        repo_url = config['SCHEMAS_REPO_URL']
        private_key_path = config['SCHEMAS_REPO_PRIVATE_KEY']
        if not repo_url or not private_key_path:
            logger.warning(f"Missing schema repo config for {resource}")
            return
        temp_dir = tempfile.mkdtemp()
        try:
            # Set up SSH key for git
            git_ssh_cmd = f'ssh -i ~/.ssh/new_key -o StrictHostKeyChecking=no'
            os.system(f"GIT_SSH_COMMAND='{git_ssh_cmd}' git clone -v -- {repo_url} {temp_dir}")
            # Look for schema files: schema-<version>.json or .yaml
            temp_dir = f"{temp_dir}/schemas"
            for fname in os.listdir(temp_dir):
                fpath = os.path.join(temp_dir, fname)
                if is_version(fname):
                    version = fname.split('-')[1].rstrip(".json")
                    with open(fpath, 'r') as f:
                        schema = json.load(f)
                    self.schemas.setdefault(resource, {})[version] = schema
                    logger.info(f"Loaded schema for {resource} version {version}")
                else:
                    with open(fpath, 'r') as f:
                        schema = json.load(f)
                    self.schemas.setdefault(resource, {})[fname] = schema
                    logger.info(f"Loaded {fname}")
        except Exception as e:
            logger.error(f"Failed to load schemas for {resource}: {e}")
        finally:
            shutil.rmtree(temp_dir)

    def resolve_schemas(self, resource):
        for version, schema in self.schemas[resource].items():
            self.resolve_refs(version, schema, self.schemas[resource], resource)


    def get_schema(self, resource, version):
        return self.schemas.get(resource, {}).get(version)


    def resolve_refs(self, version: str, schema: dict, schema_store: dict, resource: str) -> dict:
        """
        Recursively resolve all $ref in a schema using jsonschema.
        If you have external schemas, pass them via schema_store.
        """
        if not isinstance(schema, dict):
            raise TypeError(f"Expected schema to be dict, got {type(schema)}: {schema}")

        resolver = RefResolver.from_schema(schema, store=schema_store or {})

        def _resolve(node):

            if isinstance(node, dict):
                if "$ref" in node:

                    ref = node["$ref"]
                    if ref in self.resolved_schemas.get(resource, {}):
                        return self.resolved_schemas[resource][ref]

                    with resolver.resolving(ref) as resolved:
                        resolved_schema = _resolve(resolved)
                        self.resolved_schemas.setdefault(resource, {})[ref] = resolved_schema
                        return resolved_schema

                if "allOf" in node:
                    merged = {}
                    for subschema in node["allOf"]:

                        resolved = _resolve(subschema)
                        if "required" in resolved:
                            merged.setdefault("required", []).extend(resolved["required"])

                        if "properties" in resolved:
                            merged.setdefault("properties", {})
                            deep_merge_props(merged["properties"], resolved["properties"])

                        for k, v in resolved.items():
                            if k not in {"required", "properties"}:
                                merged[k] = v
                    return merged

                return {k: _resolve(v) for k, v in node.items()}
            elif isinstance(node, list):
                return [_resolve(i) for i in node]

            return node
        self.resolved_schemas.setdefault(resource, {})[version] = _resolve(schema)