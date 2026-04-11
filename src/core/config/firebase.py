from .base import EnvSettings


class FirebaseConfig(EnvSettings, env_prefix="FIREBASE__"):
    credentials_path: str = ""
    project_id: str = ""
