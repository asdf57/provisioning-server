from pydantic import BaseModel, IPvAnyAddress, ConfigDict
from typing import Literal, Annotated
from functools import partial

from models.optional_model import OptionalModel


class SystemModel(BaseModel):
    os: Literal["arch", "debian"]

class PartialSystemModel(SystemModel, OptionalModel):
    pass
