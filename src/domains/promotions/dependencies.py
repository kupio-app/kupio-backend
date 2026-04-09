from fastapi import Depends

from src.core.database.uow import UoW
from src.core.dependencies import RepositoriesDeps, get_uow

from .service import PromotionsService
from .models import PromotionPacket


def get_promotions_service(
    repos: RepositoriesDeps,
    uow: UoW = Depends(get_uow),
) -> PromotionsService:
    return PromotionsService(repos=repos, uow=uow)


async def get_packet_by_id(
    packet_id: int,
    service: PromotionsService = Depends(get_promotions_service),
) -> PromotionPacket:
    return await service.get_packet(packet_id)
