import pytest

from src.core.utils.pydantic import (
    normalize_optional_string,
    validate_optional_slug,
    validate_slug,
)


def test_validate_slug_accepts_valid():
    assert validate_slug("valid_slug1") == "valid_slug1"


def test_validate_slug_rejects_invalid():
    with pytest.raises(ValueError):
        validate_slug("Invalid-Slug")


def test_validate_optional_slug_none_is_allowed():
    assert validate_optional_slug(None) is None


def test_normalize_optional_string_trims():
    assert normalize_optional_string("  text  ") == "text"


def test_normalize_optional_string_empty_to_none():
    assert normalize_optional_string("   ") is None
