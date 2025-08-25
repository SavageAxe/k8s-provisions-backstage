from pydantic import BaseModel, Field
from enum import Enum
from ..utils import config

class AllowedRegions(str, Enum):
    pass

for region in config.REGIONS:
    setattr(AllowedRegions, region.upper(), region)

class ResourceMetadata(BaseModel):
    region: AllowedRegions
    namespace: str = Field(..., pattern=r"^[a-zA-Z0-9-]{2,20}$")
    name: str = Field(..., pattern=r"^[a-zA-Z0-9-]{2,20}$")