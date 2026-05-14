import json

import pytest
from pydantic import BaseModel

from src.core.utils import mjson


class DummyModel(BaseModel):
    name: str


def test_encode_returns_json_string():
    encoded = mjson.encode({"a": 1})
    assert json.loads(encoded) == {"a": 1}


def test_database_json_serializer_handles_basemodel():
    encoded = mjson.database_json_serializer(DummyModel(name="kupio"))
    assert json.loads(encoded) == {"name": "kupio"}


def test_database_json_serializer_raises_for_unknown_type():
    with pytest.raises(NotImplementedError):
        mjson.database_json_serializer(object())
