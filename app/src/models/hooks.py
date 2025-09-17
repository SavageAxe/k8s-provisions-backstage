from typing import Literal, Dict
from pydantic import BaseModel

# Allowed hook event keys
AllowedEventName = Literal[
    "pre_create_hook",
    "post_create_hook",
    "pre_read_hook",
    "post_read_hook",
    "pre_update_hook",
    "post_update_hook",
    "pre_delete_hook",
    "post_delete_hook",
]


class ResourceHookMapping(BaseModel):
    hooks: Dict[AllowedEventName, str] = {}
