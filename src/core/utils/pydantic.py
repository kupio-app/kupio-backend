import re
from typing import Annotated

from pydantic import BeforeValidator


SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def validate_slug(value: str) -> str:
    if not SLUG_RE.match(value):
        raise ValueError(
            "slug must start with a lowercase letter and contain only lowercase letters, digits, and underscores"
        )

    return value


def normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip()
    return value or None


NormalizedOptionalString = Annotated[
    str | None,
    BeforeValidator(normalize_optional_string),
]
