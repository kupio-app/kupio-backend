from pydantic import BaseModel, ConfigDict


class CategorySlim(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    depth: int


class CategoryResponse(CategorySlim):
    parent: CategorySlim | None
