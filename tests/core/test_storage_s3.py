from io import BytesIO

from src.core.storage.s3 import S3StorageService
from tests.helpers.fakes import FakeS3Config


class FakeBody:
    def __init__(self, data: bytes) -> None:
        self._data = data
        self.closed = False

    def read(self) -> bytes:
        return self._data

    def close(self) -> None:
        self.closed = True


class FakeClient:
    def __init__(self) -> None:
        self.calls = []
        self.body = FakeBody(b"payload")

    def upload_fileobj(self, fileobj, bucket, key, ExtraArgs):
        self.calls.append(("upload", bucket, key, ExtraArgs, fileobj.read()))

    def delete_object(self, Bucket, Key):
        self.calls.append(("delete", Bucket, Key))

    def get_object(self, Bucket, Key):
        self.calls.append(("get", Bucket, Key))
        return {"Body": self.body}

    def close(self):
        self.calls.append(("close",))


def test_s3_storage_service_roundtrip(monkeypatch):
    fake_client = FakeClient()
    monkeypatch.setattr(
        "src.core.storage.s3.boto3.client", lambda *args, **kwargs: fake_client
    )

    service = S3StorageService(FakeS3Config())

    service.upload_file(BytesIO(b"file"), "key", "text/plain")
    service.delete_object("key")
    data = service.download_object("key")
    service.close()

    assert data == b"payload"
    assert fake_client.body.closed is True
    assert (
        "upload",
        "bucket",
        "key",
        {"ContentType": "text/plain"},
        b"file",
    ) in fake_client.calls
    assert ("delete", "bucket", "key") in fake_client.calls
    assert ("get", "bucket", "key") in fake_client.calls
    assert ("close",) in fake_client.calls
