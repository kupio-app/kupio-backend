from sqlalchemy import update

from src.domains.categories.models import Category
from src.domains.reports.models import ReportReason
from src.domains.users.enums import UserRole
from src.domains.users.models import User


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
        await session.execute(
            update(User)
            .where(User.username == username)
            .values(role=UserRole.MODERATOR)
        )
        await session.commit()


async def _create_category(session_factory, *, name: str = "Electronics") -> Category:
    async with session_factory() as session:
        category = Category(name=name, depth=0)
        session.add(category)
        await session.commit()
        await session.refresh(category)
        return category


def _listing_payload(*, category_id: int) -> dict:
    return {
        "title": "Gaming laptop 2026",
        "description": "Powerful gaming laptop with RTX graphics card, clean condition, and full accessories included.",
        "price": 2200,
        "is_free": False,
        "is_tradable": False,
        "currency": "usd",
        "category_id": category_id,
    }


async def _create_listing(client, *, token: str, category_id: int) -> dict:
    resp = await client.post(
        "/api/listings",
        headers=_auth_header(token),
        json=_listing_payload(category_id=category_id),
    )
    assert resp.status_code == 200
    return resp.json()


async def _activate_listing(client, *, token: str, listing_id: str) -> None:
    resp = await client.put(
        f"/api/listings/{listing_id}/status",
        headers=_auth_header(token),
        json={"status": "active"},
    )
    assert resp.status_code == 200


async def _create_reason(
    session_factory,
    *,
    slug: str = "fraud",
    title: str = "Fraud",
    description: str = "Scam or deceptive listing",
) -> ReportReason:
    async with session_factory() as session:
        reason = ReportReason(
            slug=slug,
            title=title,
            description=description,
            display_order=0,
            is_active=True,
        )
        session.add(reason)
        await session.commit()
        await session.refresh(reason)
        return reason


async def _create_report(
    client,
    *,
    listing_id: str,
    token: str,
    reason_id: int,
    additional_info: str | None = None,
) -> dict:
    resp = await client.post(
        f"/api/listings/{listing_id}/reports",
        headers=_auth_header(token),
        json={
            "reason_id": reason_id,
            "additional_info": additional_info,
        },
    )
    assert resp.status_code == 201
    return resp.json()


async def test_decline_report_updates_only_selected_report(client, session_factory):
    category = await _create_category(session_factory)
    seller_token = await _register(
        client, email="seller9@example.com", username="seller9"
    )
    buyer_token = await _register(client, email="buyer9@example.com", username="buyer9")
    moderator_token = await _register(
        client, email="mod9@example.com", username="mod9"
    )
    await _make_moderator(session_factory, username="mod9")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    await _activate_listing(client, token=seller_token, listing_id=listing["id"])
    reason = await _create_reason(session_factory)
    report = await _create_report(
        client,
        listing_id=listing["id"],
        token=buyer_token,
        reason_id=reason.id,
        additional_info="Looks suspicious",
    )

    resp = await client.post(
        f"/api/reports/{report['id']}/decision",
        headers=_auth_header(moderator_token),
        json={"action": "decline", "comment": "No violation found"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "declined"
    assert body["moderator_comment"] == "No violation found"
    assert body["seen_at"] is not None
    assert body["moderated_at"] is not None

    listing_resp = await client.get(f"/api/listings/{listing['id']}")
    assert listing_resp.status_code == 200


async def test_remove_listing_hides_listing_and_resolves_sibling_reports(
    client,
    session_factory,
):
    category = await _create_category(session_factory)
    seller_token = await _register(
        client, email="seller10@example.com", username="seller10"
    )
    buyer_a_token = await _register(
        client, email="buyer10a@example.com", username="buyer10a"
    )
    buyer_b_token = await _register(
        client,
        email="buyer10b@example.com",
        username="buyer10b",
        device_id="device-b",
    )
    moderator_token = await _register(
        client, email="mod10@example.com", username="mod10"
    )
    await _make_moderator(session_factory, username="mod10")

    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    await _activate_listing(client, token=seller_token, listing_id=listing["id"])
    reason = await _create_reason(session_factory)

    first_report = await _create_report(
        client,
        listing_id=listing["id"],
        token=buyer_a_token,
        reason_id=reason.id,
        additional_info="Bad listing",
    )
    second_report = await _create_report(
        client,
        listing_id=listing["id"],
        token=buyer_b_token,
        reason_id=reason.id,
        additional_info="Also bad",
    )

    decision = await client.post(
        f"/api/reports/{first_report['id']}/decision",
        headers=_auth_header(moderator_token),
        json={"action": "remove_listing", "comment": "Removed after review"},
    )

    assert decision.status_code == 200
    assert decision.json()["status"] == "listing_removed"

    public_listing = await client.get(f"/api/listings/{listing['id']}")
    assert public_listing.status_code == 404

    public_list = await client.get("/api/listings")
    assert public_list.status_code == 200
    assert not any(
        listing_item["id"] == listing["id"]
        for listing_item in public_list.json()["listings"]
    )

    sibling_detail = await client.get(
        f"/api/reports/{second_report['id']}",
        headers=_auth_header(moderator_token),
    )
    assert sibling_detail.status_code == 200
    sibling_body = sibling_detail.json()
    assert sibling_body["status"] == "listing_removed"
    assert sibling_body["moderator_comment"] == "Removed after review"
    assert sibling_body["seen_at"] is not None
    assert sibling_body["moderated_at"] is not None


async def test_ban_user_soft_deletes_seller_and_resolves_related_reports(
    client,
    session_factory,
):
    category = await _create_category(session_factory)
    seller_token = await _register(
        client, email="seller11@example.com", username="seller11"
    )
    buyer_a_token = await _register(
        client, email="buyer11a@example.com", username="buyer11a"
    )
    buyer_b_token = await _register(
        client,
        email="buyer11b@example.com",
        username="buyer11b",
        device_id="device-b",
    )
    moderator_token = await _register(
        client, email="mod11@example.com", username="mod11"
    )
    await _make_moderator(session_factory, username="mod11")

    listing_a = await _create_listing(
        client, token=seller_token, category_id=category.id
    )
    listing_b = await _create_listing(
        client, token=seller_token, category_id=category.id
    )
    await _activate_listing(client, token=seller_token, listing_id=listing_a["id"])
    await _activate_listing(client, token=seller_token, listing_id=listing_b["id"])
    reason = await _create_reason(session_factory)

    report_a = await _create_report(
        client,
        listing_id=listing_a["id"],
        token=buyer_a_token,
        reason_id=reason.id,
        additional_info="Fraud",
    )
    report_b = await _create_report(
        client,
        listing_id=listing_b["id"],
        token=buyer_b_token,
        reason_id=reason.id,
        additional_info="Spam",
    )

    decision = await client.post(
        f"/api/reports/{report_a['id']}/decision",
        headers=_auth_header(moderator_token),
        json={"action": "ban_user", "comment": "Banned seller"},
    )

    assert decision.status_code == 200
    assert decision.json()["status"] == "user_banned"

    me_resp = await client.get("/api/users/me", headers=_auth_header(seller_token))
    assert me_resp.status_code == 401

    public_list = await client.get("/api/listings")
    assert public_list.status_code == 200
    listing_ids = {listing_item["id"] for listing_item in public_list.json()["listings"]}
    assert listing_a["id"] not in listing_ids
    assert listing_b["id"] not in listing_ids

    related_detail = await client.get(
        f"/api/reports/{report_b['id']}",
        headers=_auth_header(moderator_token),
    )
    assert related_detail.status_code == 200
    related_body = related_detail.json()
    assert related_body["status"] == "user_banned"
    assert related_body["moderator_comment"] == "Banned seller"
    assert related_body["seen_at"] is not None


async def test_second_moderation_attempt_returns_409(client, session_factory):
    category = await _create_category(session_factory)
    seller_token = await _register(
        client, email="seller12@example.com", username="seller12"
    )
    buyer_token = await _register(
        client, email="buyer12@example.com", username="buyer12"
    )
    moderator_token = await _register(
        client, email="mod12@example.com", username="mod12"
    )
    await _make_moderator(session_factory, username="mod12")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    await _activate_listing(client, token=seller_token, listing_id=listing["id"])
    reason = await _create_reason(session_factory)
    report = await _create_report(
        client,
        listing_id=listing["id"],
        token=buyer_token,
        reason_id=reason.id,
    )

    first = await client.post(
        f"/api/reports/{report['id']}/decision",
        headers=_auth_header(moderator_token),
        json={"action": "decline"},
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/reports/{report['id']}/decision",
        headers=_auth_header(moderator_token),
        json={"action": "remove_listing"},
    )

    assert second.status_code == 409
    assert second.json()["detail"] == "Report has already been resolved"
