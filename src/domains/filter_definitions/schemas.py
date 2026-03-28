import datetime
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import FilterType

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*$")


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
        if not _SLUG_RE.match(v):
            raise ValueError(
                "slug must start with a lowercase letter and contain only lowercase letters, digits, and underscores"
            )

        return v

    @model_validator(mode="after")
    def validate_options(self) -> "FilterDefinitionRequest":
        if self.filter_type == FilterType.SELECT:
            values = (self.options or {}).get("values")
            if not values or not isinstance(values, list):
                raise ValueError(
                    "options.values must be a non-empty list for SELECT filter type"
                )

        return self


class FilterDefinitionUpdateRequest(BaseModel):
    slug: str | None = Field(default=None, max_length=100)
    label: str | None = Field(default=None, max_length=255)
    filter_type: FilterType | None = None
    options: dict | None = None
    is_required: bool | None = None
    display_order: int | None = Field(default=None, ge=0)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str | None) -> str | None:
        if v is not None and not _SLUG_RE.match(v):
            raise ValueError(
                "slug must start with a lowercase letter and contain only lowercase letters, digits, and underscores"
            )

        return v


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
