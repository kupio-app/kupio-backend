from src.core.exceptions import NotFoundError, ForbiddenError, BadRequestError


class ConversationNotFoundError(NotFoundError):
    detail = "Conversation not found"


class MessageNotFoundError(NotFoundError):
    detail = "Message not found"


class NotConversationParticipantError(ForbiddenError):
    detail = "You are not a participant in this conversation"


class CannotMessageOwnListingError(BadRequestError):
    detail = "You cannot start a conversation on your own listing"


class MessageNotOwnedError(ForbiddenError):
    detail = "You can only delete your own messages"
