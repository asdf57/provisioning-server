from pydantic import BaseModel, IPvAnyAddress, ConfigDict
from typing import Literal, Annotated
from functools import partial


class SystemModel(BaseModel):
    os: Literal["arch", "debian"]
