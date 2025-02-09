from enum import Enum
from typing import Optional, Type
from pydantic import BaseModel, create_model

class ValidationMode(Enum):
    PARTIAL = 1
    FULL = 2

def validate_model(model: Type[BaseModel], data: dict, validation_mode: ValidationMode) -> BaseModel:
    if validation_mode == ValidationMode.PARTIAL:
        partial_model = create_partial_model(model)
        return partial_model(**data)
    elif validation_mode == ValidationMode.FULL:
        return model(**data)
    else:
        raise ValueError("Invalid validation mode")


def create_partial_model(model: Type[BaseModel]) -> Type[BaseModel]:
    partial_fields = {
        name: (Optional[field.annotation], None)
        for name, field in model.model_fields.items()
    }
    return create_model(f"Partial{model.__name__}", **partial_fields)
