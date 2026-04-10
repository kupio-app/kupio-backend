from enum import StrEnum, auto


class TransactionType(StrEnum):
    TOP_UP = auto()  # Balance credited
    DEBIT = auto()  # Balance deducted
    REFUND = auto()  # Balance returned


class PaymentSessionStatus(StrEnum):
    CREATED = auto()  # row created, Stripe session not yet requested
    PENDING = auto()  # Stripe session created, awaiting payment
    COMPLETED = auto()
    EXPIRED = auto()
