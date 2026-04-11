from enum import StrEnum, auto


class DevicePlatform(StrEnum):
    IOS = auto()
    ANDROID = auto()


class ConversationRole(StrEnum):
    BUYER = auto()
    SELLER = auto()
