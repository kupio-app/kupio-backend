from pydantic import BaseModel, ConfigDict, Field


class CategorySlim(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    depth: int
    icon: str | None


class CategoryResponse(CategorySlim):
    parent: CategorySlim | None


class CategoryRequestCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    icon: str | None = Field(min_length=1, max_length=255)
    parent_id: int | None


class CategoryRequestUpdate(BaseModel):
    name: str = Field(None, min_length=1, max_length=255)
    icon: str | None = Field(None, min_length=1, max_length=255)
    parent_id: int | None = None
