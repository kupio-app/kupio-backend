import datetime
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, and_, case, func, or_, select, update
from sqlalchemy.orm import joinedload

from src.core.database.base_repository import BaseRepository
from src.domains.images.models import ListingImage
from src.domains.listings.models import Listing

from .enums import ReportStatus
from .models import ListingReport, ReportReason


@dataclass(slots=True)
class ReportsDashboardStatsData:
    new_today: int
    no_action: int
    unseen: int


class ReportReasonsRepository(BaseRepository):
    async def get_by_id(self, reason_id: int) -> ReportReason | None:
        return await self._get(ReportReason, ReportReason.id == reason_id)

    async def get_by_slug(self, slug: str) -> ReportReason | None:
        return await self._get(ReportReason, ReportReason.slug == slug)

    async def list_all(self, *, include_inactive: bool = False) -> list[ReportReason]:
        conditions: list[ColumnElement[Any]] = []
        if not include_inactive:
            conditions.append(ReportReason.is_active.is_(True))

        return await self._get_many(
            ReportReason,
            *conditions,
            order_by=(
                ReportReason.display_order.asc(),
                ReportReason.id.asc(),
            ),
        )

    async def create(
        self,
        *,
        slug: str,
        title: str,
        description: str | None,
        display_order: int,
        is_active: bool,
    ) -> ReportReason:
        return await self._add(
            ReportReason,
            slug=slug,
            title=title,
            description=description,
            display_order=display_order,
            is_active=is_active,
        )

    async def update_by_id(self, reason_id: int, **kwargs: Any) -> ReportReason | None:
        return await self._update(
            ReportReason, [ReportReason.id == reason_id], **kwargs
        )


class ReportsRepository(BaseRepository):
    @staticmethod
    def _listing_read_options():
        return (
            joinedload(ListingReport.reason),
            joinedload(ListingReport.listing).joinedload(Listing.user),
            joinedload(ListingReport.listing)
            .selectinload(Listing.images)
            .joinedload(ListingImage.image),
        )

    async def get_by_id(self, report_id: int) -> ListingReport | None:
        return await self._get(
            ListingReport,
            ListingReport.id == report_id,
            options=self._listing_read_options(),
        )

    async def create(
        self,
        *,
        listing_id: UUID,
        reporter_id: UUID,
        reason_id: int,
        additional_info: str | None,
        status: ReportStatus,
    ) -> ListingReport:
        report = await self._add(
            ListingReport,
            listing_id=listing_id,
            reporter_id=reporter_id,
            reason_id=reason_id,
            additional_info=additional_info,
            status=status,
        )
        await self.session.refresh(report, attribute_names=["reason", "listing"])
        return await self.get_by_id(report.id)

    async def exists_pending_for_listing_and_reporter(
        self,
        *,
        listing_id: UUID,
        reporter_id: UUID,
    ) -> bool:
        existing = await self._get(
            ListingReport,
            ListingReport.listing_id == listing_id,
            ListingReport.reporter_id == reporter_id,
            ListingReport.status == ReportStatus.PENDING,
        )
        return existing is not None

    async def list_reports(
        self,
        *,
        limit: int,
        status: ReportStatus | None = None,
        seen: bool | None = None,
        cursor_created_at: datetime.datetime | None = None,
        cursor_id: int | None = None,
    ) -> list[ListingReport]:
        conditions: list[ColumnElement[Any]] = []

        if status is not None:
            conditions.append(ListingReport.status == status)

        if seen is True:
            conditions.append(ListingReport.seen_at.is_not(None))
        elif seen is False:
            conditions.append(ListingReport.seen_at.is_(None))

        if cursor_created_at is not None and cursor_id is not None:
            conditions.append(
                or_(
                    ListingReport.created_at < cursor_created_at,
                    and_(
                        ListingReport.created_at == cursor_created_at,
                        ListingReport.id < cursor_id,
                    ),
                )
            )

        stmt = (
            select(ListingReport)
            .options(*self._listing_read_options())
            .where(*conditions)
            .order_by(ListingReport.created_at.desc(), ListingReport.id.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).unique())

    async def get_dashboard_stats(self) -> ReportsDashboardStatsData:
        today = datetime.datetime.now(datetime.UTC).date()

        stmt = select(
            func.coalesce(
                func.sum(
                    case((func.date(ListingReport.created_at) == today, 1), else_=0)
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case((ListingReport.status == ReportStatus.DECLINED, 1), else_=0)
                ),
                0,
            ),
            func.coalesce(
                func.sum(case((ListingReport.seen_at.is_(None), 1), else_=0)),
                0,
            ),
        )
        new_today, no_action, unseen = (await self.session.execute(stmt)).one()
        return ReportsDashboardStatsData(
            new_today=int(new_today),
            no_action=int(no_action),
            unseen=int(unseen),
        )

    async def mark_seen(
        self,
        *,
        report_id: int,
        moderator_id: UUID,
        seen_at: datetime.datetime,
    ) -> bool:
        result = await self.session.execute(
            update(ListingReport)
            .where(
                ListingReport.id == report_id,
                ListingReport.seen_at.is_(None),
            )
            .values(
                seen_at=seen_at,
                seen_by_moderator_id=moderator_id,
            )
        )
        await self.session.flush()
        return bool(getattr(result, "rowcount", 0) > 0)

    async def resolve_pending_by_id(
        self,
        *,
        report_id: int,
        status: ReportStatus,
        moderator_id: UUID,
        moderated_at: datetime.datetime,
        moderator_comment: str | None,
    ) -> bool:
        result = await self.session.execute(
            update(ListingReport)
            .where(
                ListingReport.id == report_id,
                ListingReport.status == ReportStatus.PENDING,
            )
            .values(
                status=status,
                moderated_at=moderated_at,
                moderator_id=moderator_id,
                moderator_comment=moderator_comment,
                seen_at=case(
                    (ListingReport.seen_at.is_(None), moderated_at),
                    else_=ListingReport.seen_at,
                ),
                seen_by_moderator_id=case(
                    (ListingReport.seen_at.is_(None), moderator_id),
                    else_=ListingReport.seen_by_moderator_id,
                ),
            )
        )
        await self.session.flush()
        return bool(getattr(result, "rowcount", 0) > 0)

    async def resolve_pending_for_listing(
        self,
        *,
        listing_id: UUID,
        status: ReportStatus,
        moderator_id: UUID,
        moderated_at: datetime.datetime,
        moderator_comment: str | None,
        exclude_report_id: int | None = None,
    ) -> int:
        conditions: list[ColumnElement[Any]] = [
            ListingReport.listing_id == listing_id,
            ListingReport.status == ReportStatus.PENDING,
        ]
        if exclude_report_id is not None:
            conditions.append(ListingReport.id != exclude_report_id)

        result = await self.session.execute(
            update(ListingReport)
            .where(*conditions)
            .values(
                status=status,
                moderated_at=moderated_at,
                moderator_id=moderator_id,
                moderator_comment=moderator_comment,
                seen_at=case(
                    (ListingReport.seen_at.is_(None), moderated_at),
                    else_=ListingReport.seen_at,
                ),
                seen_by_moderator_id=case(
                    (ListingReport.seen_at.is_(None), moderator_id),
                    else_=ListingReport.seen_by_moderator_id,
                ),
            )
        )
        await self.session.flush()
        return int(getattr(result, "rowcount", 0))

    async def resolve_pending_for_user_listings(
        self,
        *,
        user_id: UUID,
        status: ReportStatus,
        moderator_id: UUID,
        moderated_at: datetime.datetime,
        moderator_comment: str | None,
        exclude_report_id: int | None = None,
    ) -> int:
        conditions: list[ColumnElement[Any]] = [
            ListingReport.listing_id.in_(
                select(Listing.id).where(Listing.user_id == user_id)
            ),
            ListingReport.status == ReportStatus.PENDING,
        ]
        if exclude_report_id is not None:
            conditions.append(ListingReport.id != exclude_report_id)

        result = await self.session.execute(
            update(ListingReport)
            .where(*conditions)
            .values(
                status=status,
                moderated_at=moderated_at,
                moderator_id=moderator_id,
                moderator_comment=moderator_comment,
                seen_at=case(
                    (ListingReport.seen_at.is_(None), moderated_at),
                    else_=ListingReport.seen_at,
                ),
                seen_by_moderator_id=case(
                    (ListingReport.seen_at.is_(None), moderator_id),
                    else_=ListingReport.seen_by_moderator_id,
                ),
            )
        )
        await self.session.flush()
        return int(getattr(result, "rowcount", 0))
