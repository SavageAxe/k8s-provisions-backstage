import asyncio
import json
import re
from typing import Dict, Any
from ..services.git import Git
from .resolver import SchemaResolver
from loguru import logger


def is_version(string: str) -> bool:
    return (
        string.startswith("schema-")
        and string.endswith(".json")
        and re.fullmatch(r"\d+\.\d+\.\d+", string.split("-")[1].rstrip(".json")) is not None
    )


class SchemaLoader:
    def __init__(self, resource, git):
        self.git = git
        self.resource = resource
        self.schemas: Dict[str, Dict[str, Dict[str, Any]]] = {}   # {resource: {version: schema_dict}}
        self.resolved_schemas: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self.resolver = SchemaResolver()

    async def load_all_schemas(self):
        await self._load_resource_schemas(self.resource)
        resolved_schemas = await self.resolve_schemas()
        return resolved_schemas

    async def resolve_schemas(self):
        schema_store = self.schemas
        for version, schema in schema_store.items():
            self.resolved_schemas[version] = self.resolver.resolve_refs(version, schema, schema_store)
        return self.resolved_schemas

    async def _load_resource_schemas(self, resource: str):

        schemas = await self.git.list_dir("/schemas")
        for name, path in schemas:
            content = await self.git.get_file_content(path)
            schema = json.loads(content)
            if is_version(name):
                name = name.split("-")[1].rstrip(".json")
                self.schemas[name] = schema
            else:
                self.schemas[name] = schema

            logger.info(f"Loaded schema for {resource} version {name}")




    def get_schema(self, version: str):
        return self.schemas.get(version)


    async def sync_schemas(self):

        changed_files = self.git.get_changed_files()

        for schema_path in changed_files:

            current_schema = self.git.get_file_content(schema_path)

            version = schema_path.split("/")[-1]
            if is_version(version):
                version = version.split("-")[1].rstrip(".json")
                schema = self.schemas[version]

            else:
                schema = self.schemas[version]

            if not current_schema == schema:

                self.schemas[version] = current_schema
                self.resolved_schemas[version] = self.resolver.resolve_refs(version, current_schema, self.schemas)
