from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional


class RemoveCheckRequest(BaseModel):
    schemas: List[str] = Field(
        ...,
        description="List of schema names to check if they can be safely removed"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "schemas": ["base-schema.json", "0.1.0"]
            }
        }
    )


class RemoveCheckResponse(BaseModel):
    schema_name: str = Field(
        ...,
        alias="schema",
        description="The schema being checked"
    )
    can_remove: bool = Field(
        ...,
        description="Whether this schema can be safely removed"
    )
    reason: Optional[str] = Field(
        None,
        description="If removal is not allowed, explains why"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "schema": "0.1.0",
                "can_remove": False,
                "reason": "still referred in: ['schema-0.1.0.json']"
            }
        }
    )
