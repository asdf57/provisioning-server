import yaml
from decimal import ROUND_DOWN, Decimal, InvalidOperation
from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Annotated
from typing import List, Literal, Optional
from models.optional_model import OptionalModel

VALID_PARTITION_TYPE = Literal["primary", "logical", "extended"]
VALID_FS_TYPES = Literal[
    "ext4", "ext3", "ext2", "xfs", "btrfs", "fat32", 
    "ntfs", "swap", "zfs", "jfs", "reiserfs", "f2fs",
    "swap", "efi"
]
VALID_FLAGS = Literal["boot", "esp", "swap", "raid", "lvm", "noauto", "hidden"]

PartitionPercentage = Annotated[
    float,
    Field(
        gt=0.0,
        le=100.0,
        description="Percentage of disk space to allocate to the partition (precision of 2 decimal places)"
    )
]

class PartitionModel(BaseModel):
    partition_type: VALID_PARTITION_TYPE = Field(
        description="Type of partition (primary, logical, or extended)"
    )
    percentage: PartitionPercentage = Field(
        description="Percentage of disk space to allocate to the partition (precision of 2 decimal places)"
    )
    fs_type: Optional[VALID_FS_TYPES] = Field(
        default=None,
        description="Filesystem type for the partition"
    )
    flags: List[VALID_FLAGS] = Field(
        default_factory=list,
        description="Flags for the partition"
    )

    @field_validator("percentage")
    @classmethod
    def validate_percentage(cls, v):
        # Convert to string to analyze the decimal part
        str_value = str(v)

        # Check if there's a decimal point in the string
        if '.' not in str_value:
            raise ValueError("Percentage must have exactly two decimal places")

        # Split by decimal point and check the length of the decimal part
        integer_part, decimal_part = str_value.split('.')

        # Validate that there are exactly 2 decimal places
        if len(decimal_part) > 2:
            raise ValueError("Percentage must have exactly two decimal places or less")

        # Return the float value (which is already properly formatted)
        return float(str_value)
    
    @field_validator("fs_type")
    @classmethod
    def validate_fs_type(cls, v, info):
        partition_type = info.data.get("partition_type")
        if partition_type == 'extended' and v is not None:
            raise ValueError("Extended partitions cannot have a filesystem")
        if partition_type != 'extended' and v is None:
            raise ValueError(f"{partition_type} partitions must have a filesystem")
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
        # Ensure total percentage does not exceed 100%
        total_percentage = sum([partition.percentage for partition in self.partitions])
        if total_percentage > 100:
            raise ValueError(f"Total percentage of partitions exceeds 100%: {total_percentage}")
        return self

class PartialStorageModel(StorageModel, OptionalModel):
    pass