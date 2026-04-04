from fastapi import APIRouter, Depends, status

from src.core.dependencies import require_roles
from src.domains.promotions.models import PromotionPacket
from src.domains.users.enums import UserRole

from src.domains.promotions.dependencies import get_promotions_service, get_packet_by_id
from src.domains.promotions.schemas import (
    PromotionPacketCreateRequest,
    PromotionPacketResponse,
    PromotionPacketUpdateRequest,
)
from src.domains.promotions.service import PromotionsService

router = APIRouter()


@router.get("", response_model=list[PromotionPacketResponse])
async def list_packets(service: PromotionsService = Depends(get_promotions_service)):
    return await service.list_packets()


@router.get("/{packet_id}", response_model=PromotionPacketResponse)
async def get_packet(packet: PromotionPacket = Depends(get_packet_by_id)):
    return packet


@router.post(
    "", response_model=PromotionPacketResponse, status_code=status.HTTP_201_CREATED
)
async def create_packet(
    packet_data: PromotionPacketCreateRequest,
    service: PromotionsService = Depends(get_promotions_service),
    _=Depends(require_roles(UserRole.MODERATOR)),
):
    return await service.create_packet(packet_data)


@router.patch("/{packet_id}", response_model=PromotionPacketResponse)
async def update_packet(
    packet_data: PromotionPacketUpdateRequest,
    packet: PromotionPacket = Depends(get_packet_by_id),
    service: PromotionsService = Depends(get_promotions_service),
    _=Depends(require_roles(UserRole.MODERATOR)),
):
    return await service.update_packet(packet.id, packet_data)
