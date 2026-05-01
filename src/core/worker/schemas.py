from pydantic import BaseModel


class FcmPushPayload(BaseModel):
    title: str
    body: str
    type: str
    data: dict[str, str] = {}
