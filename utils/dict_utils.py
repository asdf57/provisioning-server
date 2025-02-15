from enum import Enum


class ReplacementType(Enum):
    IN_PLACE = "in_place"
    OVERRIDE = "override"

def deep_merge(d1: dict, d2: dict):
    for k, v in d2.items():
        if isinstance(v, dict):
            if not isinstance(d1.get(k), dict):
                d1[k] = {}

            deep_merge(d1[k], v)
        else:
            d1[k] = v

    return d1
