from enum import StrEnum, auto


class UserRole(StrEnum):
    MODERATOR = auto()
    USER = auto()


class DevicePlatform(StrEnum):
    IOS = auto()
    ANDROID = auto()
