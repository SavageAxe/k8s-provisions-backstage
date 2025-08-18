from typing import Dict, Any, Optional
from jsonschema import RefResolver


def deep_merge_props(target: dict, source: dict):
    for key, value in source.items():
        if (
            key in target
            and isinstance(target[key], dict)
            and isinstance(value, dict)
        ):
            deep_merge_props(target[key], value)
        else:
            target[key] = value


class SchemaResolver:
    """
    Resolve $ref and allOf in JSON Schemas for a given resource.
    Expects schemas shaped like: {resource: {version: <schema dict>, ...}, ...}
    """

    def __init__(self) -> None:
        self.resolved_schemas: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def resolve_refs(self, version: str, schema: dict, schema_store: dict) -> dict:
        """
        Recursively resolve all $ref in a schema using jsonschema.
        If you have external schemas, pass them via schema_store.
        resolved_schemas structure:
        {
          "schema_name": {
            "referred_in": [list of schemas where it was referenced],
            "schema": resolved_schema_dict
          }
        }
        """
        if not isinstance(schema, dict):
            raise TypeError(f"Expected schema to be dict, got {type(schema)}: {schema}")

        resolver = RefResolver.from_schema(schema, store=schema_store or {})

        def _resolve(node, name):
            if isinstance(node, dict):
                if "$ref" in node:
                    ref = node["$ref"]

                    # ensure entry exists
                    self.resolved_schemas.setdefault(ref, {"referred_in": [], "schema": None})
                    self.resolved_schemas[ref]["referred_in"].append(name)

                    if self.resolved_schemas[ref]["schema"] is not None:
                        return self.resolved_schemas[ref]["schema"]

                    with resolver.resolving(ref) as resolved:
                        resolved_schema = _resolve(resolved, ref)
                        self.resolved_schemas[ref]["schema"] = resolved_schema
                        return resolved_schema

                if "allOf" in node:
                    merged = {}
                    for subschema in node["allOf"]:
                        resolved = _resolve(subschema, name)
                        if "required" in resolved:
                            merged.setdefault("required", []).extend(resolved["required"])
                        if "properties" in resolved:
                            merged.setdefault("properties", {})
                            deep_merge_props(merged["properties"], resolved["properties"])
                        for k, v in resolved.items():
                            if k not in {"required", "properties"}:
                                merged[k] = v
                    return merged

                return {k: _resolve(v, name) for k, v in node.items()}

            elif isinstance(node, list):
                return [_resolve(i, name) for i in node]

            return node

        self.resolved_schemas.setdefault(version, {"referred_in": [], "schema": None})
        self.resolved_schemas[version]["schema"] = _resolve(schema, version)
        return self.resolved_schemas[version]