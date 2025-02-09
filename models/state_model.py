from pydantic import BaseModel, IPvAnyAddress, ConfigDict
from typing import Literal, Annotated
from functools import partial


class StateModel(BaseModel):
    is_provisioned: bool = False
