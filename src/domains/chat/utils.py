from .models import Message


def generate_message_preview(message: Message) -> str:
    return message.body[:100] if message.body else ""
