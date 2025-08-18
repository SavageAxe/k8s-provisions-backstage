import asyncio
import json
import re
from asyncio import sleep
from datetime import datetime
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
        await self.resolve_schemas()

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


    async def sync_schemas(self, last_sync, now):
        changed_files = await self.git.get_changed_files("/schemas", last_sync, now)
        logger.info("Looking for changed files")

        for schema_path in changed_files:

            current_schema = await self.git.get_file_content(schema_path)
            schema_name = schema_path.split("/")[-1]

            logger.info(f"Reloads {schema_name} for {self.resource}")

            if is_version(schema_name):
                schema_name = schema_name.split("-")[1].rstrip(".json")

            self._remove_relevant_refs_resolved_schemas(schema_name)
            self.schemas[schema_name] = current_schema
            await self.resolve_schemas()

            logger.info(f"{schema_name} for {self.resource} reloaded successfully!")

        await asyncio.sleep("10")



    def _remove_relevant_refs_resolved_schemas(self, schema_name: str):
        if self.resolved_schemas[schema_name]["referred_in"] is []:
            del self.resolved_schemas[schema_name]["schema"]
        else:
            for schema in self.resolved_schemas[schema_name]["referred_in"]:
                self.remove_relevant_refs(schema)
                self.resolved_schemas[schema_name]["referred_in"].pop(schema)
            del self.resolved_schemas[schema_name]["schema"]
