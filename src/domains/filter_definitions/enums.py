from enum import StrEnum, auto


class FilterType(StrEnum):
    TEXT = auto()  # free-form string
    NUMBER = auto()  # int or float
    BOOLEAN = auto()  # true / false
    SELECT = auto()  # one of predefined options list
    RANGE = auto()  # number within min/max bounds
