from pydantic import BaseModel, Field
from enum import Enum
import re

class AllowedRegions(str, Enum):
    SHEKER1 = "sheker1"
    SHEKER2 = "sheker2"
    SHEKER3 = "sheker3"

class ResourceMetadata(BaseModel):
    region: AllowedRegions
    namespace: str = Field(..., pattern=r"^[a-zA-Z0-9-]{2,20}$")
    name: str = Field(..., pattern=r"^[a-zA-Z0-9-]{2,20}$")