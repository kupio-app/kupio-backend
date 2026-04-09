from enum import StrEnum, auto


class PromotionType(StrEnum):
    TOP = auto()  # Listing appears at the top of search results
    HIGHLIGHT = auto()  # Listing is visually highlighted in results
    URGENT = auto()  # Listing is marked as urgent
    VIP = auto()  # Listing receives maximum visibility (top + highlight)


class PromotionStatus(StrEnum):
    PENDING = auto()  # Purchased but listing not yet active
    ACTIVE = auto()  # Live and boosting the listing
    EXPIRED = auto()  # Duration elapsed, deactivated by worker
    CANCELLED = auto()  # Manually cancelled, triggers refund
