from src.core.exceptions import BadRequestError


class InsufficientBalanceError(BadRequestError):
    detail = "Insufficient balance"


class InvalidTopUpAmountError(BadRequestError):
    detail = "Top-up amount must be greater than zero"
