from enum import StrEnum, auto


class CurrencyEnum(StrEnum):
    USD = auto()
    EUR = auto()
    CZK = auto()
    UAH = auto()


class ListingStatus(StrEnum):
    DRAFT = auto()  # Listing created but not yet submitted (visible only to owner)
    PLANNED = auto()  # Submitted, scheduled for future publication
    ACTIVE = auto()  # Live and visible to buyers
    INACTIVE = auto()  # Temporarily hidden by owner (can be reactivated)
    SOLD = auto()  # Marked as sold by owner (can be archived or reactivated)

    # Lifecycle:
    # DRAFT -> PLANNED, ACTIVE
    # PLANNED -> DRAFT, ACTIVE, SOLD
    # ACTIVE -> PLANNED, INACTIVE, SOLD
    # INACTIVE -> PLANNED, ACTIVE, SOLD
    # SOLD -> DRAFT
