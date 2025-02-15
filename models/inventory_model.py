from pydantic import BaseModel, Field, IPvAnyAddress
from typing import Literal


class InventoryModel(BaseModel):
    host: str
    ip: IPvAnyAddress
    mac: str
    os: Literal["arch", "debian"]
    node_type: Literal["coords", "infras", "workers"]
    family: Literal["server", "router"]
    groups: list[str] = []
    port: int = Field(..., ge=1, le=65535)
    ansible_user: str = "root"

class DeleteInventoryModel(BaseModel):
    host: str
