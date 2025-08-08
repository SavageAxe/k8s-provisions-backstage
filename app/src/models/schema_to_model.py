from pydantic import BaseModel, create_model, Field, HttpUrl
from typing import Any, Dict, List, Union, Optional, Literal, get_args

def schema_to_model(
    name: str,
    schema: Dict[str, Any],
    required: Optional[List[str]] = None
) -> type[BaseModel]:
    required = set(required or schema.get("required", []))
    properties = schema.get("properties", {})
    fields = {}

    for prop_name, prop_schema in properties.items():
        field_type = Any
        field_args = {}

        if "description" in prop_schema:
            field_args["description"] = prop_schema["description"]
        if "example" in prop_schema:
            field_args["example"] = prop_schema["example"]

        if "enum" in prop_schema:
            field_type = Literal[tuple(prop_schema["enum"])]

        elif prop_schema.get("type") == "string":
            if "pattern" in prop_schema and prop_schema["pattern"].startswith("^https?://"):
                field_type = HttpUrl
            else:
                field_type = str

        elif prop_schema.get("type") == "integer":
            field_type = int
        elif prop_schema.get("type") == "boolean":
            field_type = bool
        elif prop_schema.get("type") == "array":
            item_type = schema_to_type(prop_schema["items"])
            field_type = List[item_type]
        elif prop_schema.get("type") == "object":
            sub_model_name = f"{name}_{prop_name.capitalize()}"
            field_type = schema_to_model(sub_model_name, prop_schema)

        fields[prop_name] = (
            field_type,
            Field(... if prop_name in required else None, **field_args)
        )

    return create_model(name, **fields)

def schema_to_type(prop_schema: dict) -> type:
    if "enum" in prop_schema:
        return Literal[tuple(prop_schema["enum"])]
    if prop_schema.get("type") == "string":
        return str
    if prop_schema.get("type") == "integer":
        return int
    if prop_schema.get("type") == "boolean":
        return bool
    if prop_schema.get("type") == "array":
        return List[schema_to_type(prop_schema["items"])]
    return Any
