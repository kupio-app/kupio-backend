from src.core.database.repositories import Repositories
from src.core.database.uow import UoW
from src.domains.users.models import User
from .models import BalanceTransaction


class PaymentsService:
    def __init__(self, repos: Repositories, uow: UoW) -> None:
        self.repos = repos
        self.uow = uow

    async def list_transactions(
        self,
        current_user: User,
        *,
        limit: int,
        offset: int = 0,
    ) -> list[BalanceTransaction]:
        return await self.repos.balance_transactions.get_by_user(
            current_user.id,
            limit=limit,
            offset=offset,
        )
