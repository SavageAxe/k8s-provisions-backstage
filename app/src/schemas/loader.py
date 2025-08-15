import os
import tempfile
import json
import shutil
import re
import subprocess
from typing import Dict, Any

from loguru import logger
from .resolver import SchemaResolver


def is_version(string: str) -> bool:
    return (
        string.startswith("schema-")
        and string.endswith(".json")
        and re.fullmatch(r"\d+\.\d+\.\d+", string.split("-")[1].rstrip(".json")) is not None
    )


class SchemaLoader:
    def __init__(self, repo_url, resource, private_key_path):
        self.repo_url = repo_url
        self.private_key_path = private_key_path
        self.resource = resource
        self.schemas: Dict[str, Dict[str, Dict[str, Any]]] = {}   # {resource: {version: schema_dict}}
        self.resolved_schemas: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def load_all_schemas(self):
        self._load_resource_schemas(self.resource)
        self.resolve_schemas()
        return self.resolved_schemas

    def resolve_schemas(self):
        schema_store = self.schemas
        resolver = SchemaResolver(schema_store)
        for version, schema in schema_store.items():
            self.resolved_schemas[version] = resolver.resolve_refs(version, schema, schema_store)

    def _load_resource_schemas(self, resource: str):

        temp_dir = tempfile.mkdtemp(prefix=f"{resource}_schemas_")

        try:
            git_ssh_cmd = f"ssh -i {self.private_key_path} -o StrictHostKeyChecking=no"
            env = os.environ.copy()
            env["GIT_SSH_COMMAND"] = git_ssh_cmd

            subprocess.run(
                ["git", "clone", "--verbose", "--", self.repo_url, temp_dir],
                check=True,
                env=env,
                text=True,
                capture_output=True,
            )

            schemas_dir = os.path.join(temp_dir, "schemas")
            scan_dir = schemas_dir if os.path.isdir(schemas_dir) else temp_dir

            for fname in os.listdir(scan_dir):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(scan_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        schema = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to parse {fname} for {resource}: {e}")
                    continue

                if is_version(fname):
                    version = fname.split("-")[1].rstrip(".json")
                    self.schemas[version] = schema
                    logger.info(f"Loaded schema for {resource} version {version}")
                else:
                    self.schemas[fname] = schema
                    logger.info(f"Loaded {fname} for {resource}")

        except subprocess.CalledProcessError as e:
            logger.error(f"Git clone failed for {resource}: {e.stderr or e}")
        except Exception as e:
            logger.error(f"Failed to load schemas for {resource}: {e}")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def get_schema(self, version: str):
        return self.schemas.get(version)