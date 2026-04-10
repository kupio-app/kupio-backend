from enum import StrEnum, auto


class TransactionType(StrEnum):
    TOP_UP = auto()  # Balance credited
    DEBIT = auto()  # Balance deducted
    REFUND = auto()  # Balance returned


class PaymentSessionStatus(StrEnum):
    PENDING = auto()
    COMPLETED = auto()
    EXPIRED = auto()
