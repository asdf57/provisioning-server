from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Annotated
from typing import List, Literal, Optional, Union
from models.optional_model import OptionalModel

VALID_PARTITION_TYPE = Literal["primary", "logical", "extended"]
VALID_FS_TYPES = Literal[
    "ext4", "ext3", "ext2", "xfs", "btrfs", "fat32", 
    "ntfs", "swap", "zfs", "jfs", "reiserfs", "f2fs",
    "swap", "efi"
]
VALID_FLAGS = Literal["boot", "esp", "swap", "raid", "lvm", "noauto", "hidden"]

VALID_ALLOCATORS = Literal[
    "percentage", "size"
]

class PartitionModel(BaseModel):
    partition_type: VALID_PARTITION_TYPE = Field(
        description="Type of partition (primary, logical, or extended)"
    )
    alloc_type: VALID_ALLOCATORS = Field(
        description="Type of allocator for the partition size (percentage, size)"
    )
    size: int = Field(
        description="Size of the partition (percentage or size in MiB)"
    )
    fs_type: Optional[VALID_FS_TYPES] = Field(
        default=None,
        description="Filesystem type for the partition"
    )
    flags: List[VALID_FLAGS] = Field(
        default_factory=list,
        description="Flags for the partition"
    )
    
    @field_validator("fs_type")
    @classmethod
    def validate_fs_type(cls, v, info):
        partition_type = info.data.get("partition_type")

        if partition_type == 'extended' and v is not None:
            raise ValueError("Extended partitions cannot have a filesystem")
        if partition_type != 'extended' and v is None:
            raise ValueError(f"{partition_type} partitions must have a filesystem")

        return v
    
    @field_validator("size")
    @classmethod
    def validate_size(cls, v, info):
        alloc_type = info.data.get("alloc_type")

        if alloc_type == "percentage" and not (0 <= v <= 100):
            raise ValueError("Percentage size must be between 0 and 100")
        elif alloc_type == "size" and v <= 0:
            raise ValueError("Size must be greater than 0 for size allocation")

        return v

class StorageModel(BaseModel):
    disk_name: str
    partitions: List[PartitionModel] = Field(
        default_factory=list,
        description="List of partitions to create on the disk"
    )

    @model_validator(mode="after")
    def validate_partitions(self):
        if not self.partitions:
            raise ValueError("At least one partition must be defined")

        percentage_sum = 0

        for partition in self.partitions:
            if partition.alloc_type == "percentage":
                percentage_sum += partition.size

        if percentage_sum > 100:
            raise ValueError(f"Total percentage of partition(s) exceeds 100%: {percentage_sum}")

        return self

class PartialStorageModel(StorageModel, OptionalModel):
    pass