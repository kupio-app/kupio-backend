import stripe
from fastapi import FastAPI

from src.core.config import AppConfig


def init_stripe(app: FastAPI, config: AppConfig) -> stripe.StripeClient:
    """Initialize Stripe client and place it in application state for later use."""
    client = stripe.StripeClient(config.stripe.secret_key.get_secret_value())
    app.state.stripe_client = client
    return client
