from pydantic import BaseModel, create_model, Field, HttpUrl
from typing import Any, Dict, List, Optional, Literal, Union


def schema_to_model(
    name: str,
    schema: Dict[str, Any],
    required: Optional[List[str]] = None
) -> type[BaseModel]:
    """
    Convert a JSON Schema dict into a dynamic Pydantic model class.
    """
    required = set(required or schema.get("required", []))
    properties = schema.get("properties", {})
    fields: Dict[str, tuple] = {}

    for prop_name, prop_schema in properties.items():
        field_type = schema_to_type(prop_schema, name=name, prop_name=prop_name)
        field_args: Dict[str, Any] = {}

        # Metadata for Swagger/OpenAPI
        if "title" in prop_schema:
            field_args["title"] = prop_schema["title"]
        if "description" in prop_schema:
            field_args["description"] = prop_schema["description"]

        if "examples" in prop_schema:
            field_args["examples"] = prop_schema["examples"]
        elif "example" in prop_schema:
            field_args["examples"] = [prop_schema["example"]]

        fields[prop_name] = (
            field_type,
            Field(... if prop_name in required else None, **field_args)
        )

    return create_model(name, **fields)


def schema_to_type(prop_schema: dict, name: str = "", prop_name: str = "") -> type:
    """
    Map JSON Schema type definitions to Python/Pydantic types.
    """
    # Nullable types e.g. {"type": ["string", "null"]}
    prop_type = prop_schema.get("type")
    if isinstance(prop_type, list):
        if "null" in prop_type:
            base_type = next((t for t in prop_type if t != "null"), "string")
            return Optional[schema_to_type({"type": base_type})]
        # fallback: treat as Any if multiple types
        return Any

    # Enum
    if "enum" in prop_schema:
        return Literal[tuple(prop_schema["enum"])]

    # String with pattern for URL
    if prop_type == "string":
        if "pattern" in prop_schema and prop_schema["pattern"].startswith("^https?://"):
            return HttpUrl
        return str

    if prop_type == "integer":
        return int
    if prop_type == "boolean":
        return bool
    if prop_type == "number":
        return float

    if prop_type == "array":
        item_schema = prop_schema.get("items", {"type": "string"})
        return List[schema_to_type(item_schema)]

    if prop_type == "object":
        if "properties" in prop_schema:
            sub_model_name = f"{name}_{prop_name.capitalize()}"
            return schema_to_model(sub_model_name, prop_schema)
        return Dict[str, Any]

    return Any