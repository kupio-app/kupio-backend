from typing import Final

WS_AUTH_TIMEOUT: Final[int] = 10  # seconds until unauthenticated connection is closed
PRESENCE_TTL: Final[int] = 30  # seconds; refreshed every PRESENCE_TTL // 2 seconds
