from pydantic import BaseModel, Field, IPvAnyAddress
from typing import Literal
from models.state_model import *
from models.storage_model import *
from models.system_model import SystemModel

class HostvarsModel(BaseModel):
    system: SystemModel
    state: StateModel
    storage: StorageModel
