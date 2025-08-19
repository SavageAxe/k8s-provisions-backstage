import re
from typing import Dict, Any, Set, List, Optional, Tuple
from loguru import logger
import asyncio
import json
from datetime import datetime, timezone
from ..utils.openapi import update_openapi_schema
from .resolver import SchemaResolver


def is_version(string: str) -> bool:
    return (
        string.startswith("schema-")
        and string.endswith(".json")
        and re.fullmatch(r"\d+\.\d+\.\d+", string.split("-")[1].rstrip(".json")) is not None
    )


def _normalize_name(filename: str) -> str:
    """schemas/base-schema.json -> base-schema.json, schema-0.1.0.json -> 0.1.0"""
    name = filename.split("/")[-1]
    if is_version(name):
        return name.split("-")[1].rstrip(".json")
    return name


def _collect_refs(schema: dict) -> Set[str]:
    """Collect file level $ref names, keep only file names"""
    refs: Set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            if "$ref" in node:
                part = node["$ref"].split("/")[-1]
                if part.endswith(".json"):
                    refs.add(part)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(schema)
    return refs


def _dependents_closure(resolved_sets: dict, root: str) -> Set[str]:
    """All schemas that directly or transitively refer to root, including root"""
    seen: Set[str] = set()
    stack: List[str] = [root]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        entry = resolved_sets.get(cur)
        if not entry:
            continue
        for parent in entry["referred_in"]:
            if parent not in seen:
                stack.append(parent)
    return seen


class SchemaLoader:
    def __init__(self, resource, git, app):
        self.git = git
        self.resource = resource
        self.app = app
        self.schemas: Dict[str, Dict[str, Any]] = {}          # version -> schema dict
        self.resolved_schemas: Dict[str, Dict[str, Any]] = {} # name -> {referred_in, referred_to, schema}
        self.resolver = SchemaResolver()

    async def load_all_schemas(self):
        await self._load_resource_schemas(self.resource)
        await self.resolve_schemas()

    async def resolve_schemas(self):
        # rebuild resolver graph from scratch for consistency
        self.resolver.resolved_schemas.clear()
        schema_store = self.schemas
        for version, schema in schema_store.items():
            self.resolver.resolve_refs(version, schema, schema_store)

        # snapshot resolver internal sets to lists
        self.resolved_schemas = {
            name: {
                "referred_in": list(entry["referred_in"]),
                "referred_to": list(entry["referred_to"]),
                "schema": entry["schema"],
            }
            for name, entry in self.resolver.resolved_schemas.items()
        }
        return self.resolved_schemas

    async def _load_resource_schemas(self, resource: str):
        schemas = await self.git.list_dir("/schemas")
        for name, path in schemas:
            content = await self.git.get_file_content(path)
            schema = json.loads(content)
            if is_version(name):
                version = name.split("-")[1].rstrip(".json")
                self.schemas[version] = schema
            else:
                self.schemas[name] = schema
            logger.info(f"Loaded schema for {resource} version {name}")

    def get_schema(self, version: str):
        return self.schemas.get(version)

    async def _rebuild_impacted(self, impacted: Set[str]) -> None:
        # resolve impacted, or simply snapshot if none provided
        for ver in impacted:
            schema = self.schemas.get(ver)
            if schema is not None:
                self.resolver.resolve_refs(ver, schema, self.schemas)

        self.resolved_schemas = {
            name: {
                "referred_in": list(entry["referred_in"]),
                "referred_to": list(entry["referred_to"]),
                "schema": entry["schema"],
            }
            for name, entry in self.resolver.resolved_schemas.items()
        }

    from typing import List, Tuple, Optional

    def can_remove_schema(self, schema_name: str, changed_schemas: List) -> Tuple[bool, Optional[str]]:
        """
        Validate if schema_name can be removed:
        - It exists in resolver
        - All schemas that depend on it are also removed in this batch
        Returns: (can_remove, reason)
        """
        entry = self.resolver.resolved_schemas.get(schema_name)
        if not entry:
            # Already gone from resolver, nothing to validate
            return True, None

        dependents = set(entry["referred_in"])
        missing = []

        for d in dependents:
            found = False
            for cs in changed_schemas:
                # Case 1: structured dict {filename, status}
                if isinstance(cs, dict):
                    if _normalize_name(cs.get("filename", "")) == d and cs.get("status") == "removed":
                        found = True
                        break
                # Case 2: plain string schema name
                elif isinstance(cs, str):
                    if _normalize_name(cs) == d:
                        found = True
                        break
            if not found:
                missing.append(d)

        if missing:
            reason = f"Schema {schema_name} is still referred in by: {sorted(missing)}"
            logger.error(f"ERROR: {reason}")
            return False, reason

        return True, None


    async def _remove_schema(self, schema_name: str, changed_schemas: list) -> None:
        """
        Remove schema from resolver + store after validating with can_remove_schema
        """
        can_remove, reason = self.can_remove_schema(schema_name, changed_schemas)
        if not can_remove:
            logger.error(f"Skip removing {schema_name}: {reason}")
            return

        entry = self.resolver.resolved_schemas.get(schema_name)
        if not entry:
            # Already gone, just drop from store if present
            self.schemas.pop(schema_name, None)
            return

        # unlink references
        for ref in set(entry["referred_to"]):
            peer = self.resolver.resolved_schemas.get(ref)
            if peer:
                peer["referred_in"].discard(schema_name)

        for parent in set(entry["referred_in"]):
            peer = self.resolver.resolved_schemas.get(parent)
            if peer:
                peer["referred_to"].discard(schema_name)

        # drop schema
        self.resolver.resolved_schemas.pop(schema_name, None)
        self.schemas.pop(schema_name, None)

        # rebuild impacted (empty set here means just refresh snapshot)
        await self._rebuild_impacted(set())

    async def _update_schema(self, schema_name: str, filename: str) -> None:
        try:
            raw = await self.git.get_file_content(filename)
            self.schemas[schema_name] = json.loads(raw)
        except Exception as e:
            logger.error(f"Failed to update schema {schema_name}: {e}")
            return

        impacted = _dependents_closure(self.resolver.resolved_schemas, schema_name)
        await self._rebuild_impacted(impacted)

    async def _add_schema(self, schema_name: str, filename: str, changed_schemas: list) -> None:
        try:
            raw = await self.git.get_file_content(filename)
            new_schema = json.loads(raw)

        except Exception as e:
            logger.error(f"Failed to add schema {schema_name}: {e}")
            return

        refs = _collect_refs(new_schema)
        missing = [
            r for r in refs
            if _normalize_name(r) not in self.schemas
            and not any(_normalize_name(cs["filename"]) == _normalize_name(r) and cs["status"] == "added"
                        for cs in changed_schemas)
        ]
        if missing:
            logger.error(f"ERROR: Cannot add {schema_name}, missing refs: {sorted(missing)}")
            return

        self.schemas[schema_name] = new_schema
        impacted = _dependents_closure(self.resolver.resolved_schemas, schema_name)
        await self._rebuild_impacted(impacted)

    async def sync_schemas(self):
        last_sync = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        while True:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            changed_schemas = await self.git.get_changed_files("/schemas", last_sync, now) or []
            logger.info(f"Looking for changed schemas for {self.resource}")

            for item in changed_schemas:

                filename = item["filename"]
                logger.info(f"Processing {filename}")
                status = item["status"]
                schema_name = _normalize_name(filename)

                if status == "removed":
                    logger.info(f"Removing {schema_name}")
                    await self._remove_schema(schema_name, changed_schemas)

                elif status == "modified":
                    logger.info(f"Modifying {schema_name}")
                    await self._update_schema(schema_name, filename)

                elif status == "added":
                    logger.info(f"Adding {schema_name}")
                    await self._add_schema(schema_name, filename, changed_schemas)

                update_openapi_schema(self.app, f"{self.resource}'s API", f"An api for {self.resource} provisioning.")

            last_sync = now
            await asyncio.sleep(10)
