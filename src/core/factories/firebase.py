import firebase_admin
from firebase_admin import credentials
from fastapi import FastAPI

from src.core.config import AppConfig


def create_firebase_app(config: AppConfig) -> firebase_admin.App | None:
    if not config.firebase.credentials_path or not config.firebase.project_id:
        return None

    cred = credentials.Certificate(config.firebase.credentials_path)
    return firebase_admin.initialize_app(
        cred, {"projectId": config.firebase.project_id}
    )


def init_firebase(app: FastAPI, config: AppConfig) -> firebase_admin.App | None:
    fb_app = create_firebase_app(config)
    app.state.firebase_app = fb_app
    return fb_app


def shutdown_firebase(app: FastAPI) -> None:
    if fb_app := app.state.firebase_app:
        firebase_admin.delete_app(fb_app)
