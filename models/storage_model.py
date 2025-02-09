from pydantic import BaseModel, Field, IPvAnyAddress, create_model
from typing import Literal


class PartitionModel(BaseModel):
    partition_type: str
    start: str
    end: str
    number: str
    unit: str
    fs_type: str
    mount_point: str
    flags: list[str]

class StorageModel(BaseModel):
    disk_name: str
    disk_size: int
    partitions: list[PartitionModel]

