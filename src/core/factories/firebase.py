import firebase_admin
from firebase_admin import credentials
from fastapi import FastAPI

from src.core.config import AppConfig


def init_firebase(app: FastAPI, config: AppConfig) -> firebase_admin.App | None:
    cred = credentials.Certificate(config.firebase.credentials_path)
    fb_app = firebase_admin.initialize_app(
        cred, {"projectId": config.firebase.project_id}
    )
    app.state.firebase_app = fb_app
    return fb_app


def shutdown_firebase(app: FastAPI) -> None:
    firebase_admin.delete_app(app.state.firebase_app)
