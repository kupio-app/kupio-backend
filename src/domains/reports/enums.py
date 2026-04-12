from enum import StrEnum, auto


class ReportStatus(StrEnum):
    PENDING = auto()
    DECLINED = auto()
    LISTING_REMOVED = auto()
    USER_BANNED = auto()


class ReportSeenFilter(StrEnum):
    ALL = auto()
    SEEN = auto()
    UNSEEN = auto()


class ReportDecisionAction(StrEnum):
    DECLINE = auto()
    REMOVE_LISTING = auto()
    BAN_USER = auto()
