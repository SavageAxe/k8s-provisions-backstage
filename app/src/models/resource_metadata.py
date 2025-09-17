from pydantic import BaseModel, Field
from enum import Enum
from ..utils import config

class AllowedRegions(str, Enum):
    pass

for cluster in config.CLUSTERS:
    setattr(AllowedRegions, cluster.upper(), cluster)

class ResourceMetadata(BaseModel):
    cluster: AllowedRegions
    namespace: str = Field(..., pattern=r"^[a-zA-Z0-9-]{2,20}$")
    name: str = Field(..., pattern=r"^[a-zA-Z0-9-]{2,20}$")