from enum import StrEnum, auto


class CurrencyEnum(StrEnum):
    USD = auto()
    EUR = auto()
    CZK = auto()
    UAH = auto()


class ListingStatus(StrEnum):
    ACTIVE = auto()
    INACTIVE = auto()
    SOLD = auto()
    DRAFT = auto()
    PLANNED = auto()
