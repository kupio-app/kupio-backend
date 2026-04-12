from typing import Annotated

from pydantic import BeforeValidator


def normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip()
    return value or None


NormalizedOptionalString = Annotated[
    str | None,
    BeforeValidator(normalize_optional_string),
]
