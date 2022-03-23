from enum import Enum


class Labels(Enum):
    QUANTUM = 1
    CLASSICAL = 2
    NO_CODE = 3
    IMPORTS = 4
    FORCE_SPLIT = 5
    START_PREVENT_SPLIT = 6
    END_PREVENT_SPLIT = 7
    IF_ELSE_BLOCK = 8
    LOOP = 9
