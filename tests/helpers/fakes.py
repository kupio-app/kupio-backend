class FakeSecret:
    def __init__(self, value: str) -> None:
        self._value = value

    def get_secret_value(self) -> str:
        return self._value


class FakeS3Config:
    bucket = "bucket"
    region = "region"
    access_key_id = "access"
    secret_access_key = FakeSecret("secret")
