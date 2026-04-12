from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.domains.reports.exceptions import DuplicateReportReasonSlugError
from src.domains.reports.models import ReportReason
from src.domains.reports.schemas import ReportReasonCreateRequest
from src.domains.reports.service import ReportsService
from src.domains.users.enums import UserRole
from src.domains.users.models import Moderator, User


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _register(
    client,
    *,
    email: str,
    username: str,
    device_id: str = "device",
) -> str:
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "username": username,
            "password": "strong-password",
            "device_id": device_id,
        },
    )
    assert resp.status_code == 201
    return resp.json()["access_token"]


async def _make_moderator(session_factory, *, username: str) -> None:
    async with session_factory() as session:
        user = await session.scalar(select(User).where(User.username == username))
        assert user is not None
        user.role = UserRole.MODERATOR
        if (
            await session.scalar(select(Moderator).where(Moderator.user_id == user.id))
            is None
        ):
            session.add(Moderator(user_id=user.id))
        await session.commit()


async def _create_reason(
    session_factory,
    *,
    slug: str,
    title: str,
    description: str | None = None,
    display_order: int = 0,
    is_active: bool = True,
) -> ReportReason:
    async with session_factory() as session:
        reason = ReportReason(
            slug=slug,
            title=title,
            description=description,
            display_order=display_order,
            is_active=is_active,
        )
        session.add(reason)
        await session.commit()
        await session.refresh(reason)
        return reason


class _DummyUoW:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


async def test_list_report_reasons_returns_only_active(client, session_factory):
    await _create_reason(
        session_factory,
        slug="fraud",
        title="Fraud",
        display_order=1,
        is_active=True,
    )
    await _create_reason(
        session_factory,
        slug="spam",
        title="Spam",
        display_order=0,
        is_active=False,
    )
    await _create_reason(
        session_factory,
        slug="other",
        title="Other",
        display_order=2,
        is_active=True,
    )

    resp = await client.get("/api/reports/reasons")

    assert resp.status_code == 200
    assert [item["slug"] for item in resp.json()] == ["fraud", "other"]


async def test_list_all_report_reasons_requires_moderator(client, session_factory):
    token = await _register(client, email="user@example.com", username="user")
    await _create_reason(
        session_factory,
        slug="other",
        title="Other",
        display_order=0,
        is_active=True,
    )

    resp = await client.get("/api/reports/reasons/all", headers=_auth_header(token))

    assert resp.status_code == 403


async def test_list_all_report_reasons_includes_inactive(client, session_factory):
    token = await _register(client, email="mod@example.com", username="mod")
    await _make_moderator(session_factory, username="mod")
    await _create_reason(
        session_factory,
        slug="fraud",
        title="Fraud",
        display_order=1,
        is_active=True,
    )
    await _create_reason(
        session_factory,
        slug="spam",
        title="Spam",
        display_order=0,
        is_active=False,
    )

    resp = await client.get("/api/reports/reasons/all", headers=_auth_header(token))

    assert resp.status_code == 200
    assert [item["slug"] for item in resp.json()] == ["spam", "fraud"]


async def test_create_report_reason_as_moderator(client, session_factory):
    token = await _register(client, email="mod2@example.com", username="mod2")
    await _make_moderator(session_factory, username="mod2")

    resp = await client.post(
        "/api/reports/reasons",
        headers=_auth_header(token),
        json={
            "slug": "fraud",
            "title": "Fraud",
            "description": "Scam or deceptive listing",
            "display_order": 1,
        },
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["slug"] == "fraud"
    assert body["title"] == "Fraud"
    assert body["is_active"] is True


async def test_create_report_reason_duplicate_slug_returns_409(client, session_factory):
    token = await _register(client, email="mod3@example.com", username="mod3")
    await _make_moderator(session_factory, username="mod3")
    await _create_reason(
        session_factory,
        slug="fraud",
        title="Fraud",
        display_order=0,
        is_active=True,
    )

    resp = await client.post(
        "/api/reports/reasons",
        headers=_auth_header(token),
        json={"slug": "fraud", "title": "Fraud", "display_order": 1},
    )

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Report reason slug already exists"


async def test_create_report_reason_translates_integrity_error_to_conflict():
    get_by_slug = AsyncMock(side_effect=[None, object()])
    report_reasons_repo = SimpleNamespace(
        get_by_slug=get_by_slug,
        create=AsyncMock(
            side_effect=IntegrityError(
                "INSERT INTO report_reasons ...",
                params=None,
                orig=Exception("duplicate key value violates unique constraint"),
            )
        ),
    )
    repos = SimpleNamespace(report_reasons=report_reasons_repo, reports=None)
    service = ReportsService(repos=repos, uow=_DummyUoW())
    payload = ReportReasonCreateRequest(
        slug="fraud",
        title="Fraud",
        description="Scam or deceptive listing",
        display_order=1,
    )

    with pytest.raises(DuplicateReportReasonSlugError):
        await service.create_reason(payload)

    report_reasons_repo.create.assert_awaited_once_with(**payload.model_dump())
    assert report_reasons_repo.get_by_slug.await_count == 2


async def test_create_report_reason_rejects_reserved_other_slug(
    client,
    session_factory,
):
    token = await _register(client, email="mod4@example.com", username="mod4")
    await _make_moderator(session_factory, username="mod4")

    resp = await client.post(
        "/api/reports/reasons",
        headers=_auth_header(token),
        json={"slug": "other", "title": "Other", "display_order": 0},
    )

    assert resp.status_code == 409
    assert resp.json()["detail"] == "The 'other' report reason is reserved"


async def test_create_report_reason_requires_moderator(client):
    token = await _register(client, email="user2@example.com", username="user2")

    resp = await client.post(
        "/api/reports/reasons",
        headers=_auth_header(token),
        json={"slug": "fraud", "title": "Fraud", "display_order": 0},
    )

    assert resp.status_code == 403


async def test_update_report_reason_changes_display_order_and_is_active(
    client,
    session_factory,
):
    token = await _register(client, email="mod5@example.com", username="mod5")
    await _make_moderator(session_factory, username="mod5")
    reason = await _create_reason(
        session_factory,
        slug="fraud",
        title="Fraud",
        display_order=4,
        is_active=True,
    )

    resp = await client.put(
        f"/api/reports/reasons/{reason.id}",
        headers=_auth_header(token),
        json={"display_order": 1, "is_active": False},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["display_order"] == 1
    assert body["is_active"] is False


async def test_update_report_reason_rejects_deactivating_other(client, session_factory):
    token = await _register(client, email="mod6@example.com", username="mod6")
    await _make_moderator(session_factory, username="mod6")
    reason = await _create_reason(
        session_factory,
        slug="other",
        title="Other",
        display_order=0,
        is_active=True,
    )

    resp = await client.put(
        f"/api/reports/reasons/{reason.id}",
        headers=_auth_header(token),
        json={"is_active": False},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "The 'other' report reason cannot be deactivated"
