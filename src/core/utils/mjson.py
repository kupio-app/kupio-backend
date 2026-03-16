import msgspec

from pydantic import BaseModel
from typing import Any, Callable, Final
from msgspec.json import Decoder, Encoder

decode: Final[Callable[..., Any]] = Decoder[dict[str, Any]]().decode
encode_bytes: Final[Callable[..., bytes]] = Encoder().encode


def encode(obj: Any) -> str:
    return encode_bytes(obj).decode()


def _enc_hook(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    else:
        # Raise a NotImplementedError for other types
        raise NotImplementedError(f"Objects of type {type(obj)} are not supported")


custom_encoder = Encoder(enc_hook=_enc_hook)


def database_json_serializer(obj: Any) -> str:
    return msgspec.json.format(custom_encoder.encode(obj), indent=2).decode()
