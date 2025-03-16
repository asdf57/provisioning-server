from pydantic import BaseModel, Field, IPvAnyAddress
from typing import Literal

from models.inventory_model import *
from models.storage_model import *
from models.system_model import SystemModel

class EntryModel(BaseModel):
    inventory: InventoryModel
    storage: StorageModel
    system: SystemModel
