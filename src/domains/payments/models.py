import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped as M, mapped_column as mc, relationship

from src.core.database.base_model import Base, UUID, Int64
from src.domains.payments.enums import PaymentSessionStatus, TransactionType

if TYPE_CHECKING:
    from src.domains.users.models import User


class BalanceTransaction(Base):
    __tablename__ = "balance_transactions"

    id: M[UUID] = mc(primary_key=True, default=uuid.uuid4)
    user_id: M[UUID] = mc(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user: M["User"] = relationship("User", lazy="joined")
    amount: M[Int64]  # negative = deduction, positive = credit
    type: M[TransactionType] = mc(Enum(TransactionType))


class PaymentSession(Base):
    __tablename__ = "payments_sessions"

    id: M[UUID] = mc(primary_key=True, default=uuid.uuid4)
    user_id: M[UUID] = mc(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user: M["User"] = relationship("User", lazy="joined")
    stripe_session_id: M[str | None] = mc(
        String(255), unique=True, index=True, nullable=True
    )
    stripe_payment_intent_id: M[str | None] = mc(String(255), nullable=True)
    amount: M[Int64]
    status: M[PaymentSessionStatus] = mc(
        Enum(PaymentSessionStatus), default=PaymentSessionStatus.CREATED
    )
