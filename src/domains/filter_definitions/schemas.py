import datetime
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import FilterType
from .utils import validate_select_options

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _validate_slug(v: str) -> str:
    if not _SLUG_RE.match(v):
        raise ValueError(
            "slug must start with a lowercase letter and contain only lowercase letters, digits, and underscores"
        )

    return v


class FilterDefinitionRequest(BaseModel):
    slug: str = Field(max_length=100)
    label: str = Field(max_length=255)
    filter_type: FilterType
    options: dict | None = None
    is_required: bool = False
    display_order: int = Field(default=0, ge=0)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        return _validate_slug(v)

    @model_validator(mode="after")
    def validate_options(self) -> "FilterDefinitionRequest":
        if self.filter_type == FilterType.SELECT:
            validate_select_options(self.options)

        return self


class FilterDefinitionUpdateRequest(BaseModel):
    slug: str = Field(None, max_length=100)
    label: str = Field(None, max_length=255)
    filter_type: FilterType = None
    options: dict | None = None
    is_required: bool = None
    display_order: int = Field(None, ge=0)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str | None) -> str | None:
        if v is not None:
            return _validate_slug(v)

        return v

    @model_validator(mode="after")
    def validate_options(self) -> "FilterDefinitionUpdateRequest":
        # Validate only when both fields are provided together in the same request.
        # If only one is changed, the service must verify compatibility against the DB state.
        if self.filter_type == FilterType.SELECT and self.options is not None:
            validate_select_options(self.options)

        return self


class FilterDefinitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    slug: str
    label: str
    filter_type: FilterType
    options: dict | None
    is_required: bool
    display_order: int
    created_at: datetime.datetime
    updated_at: datetime.datetime | None
