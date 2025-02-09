from pydantic import BaseModel, Field, IPvAnyAddress
from typing import Literal
from models.state_model import *
from models.storage_model import *

class HostvarsModel(BaseModel):
    state: StateModel
    storage: StorageModel
