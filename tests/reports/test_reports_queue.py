import datetime

from sqlalchemy import select, update

from src.domains.categories.models import Category
from src.domains.reports.models import ListingReport, ReportReason
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


def _image_file(name: str, content: bytes = b"fake-image-bytes"):
    return name, content, "image/jpeg"


async def _upload_listing_image(client, *, token: str, listing_id: str) -> list[dict]:
    resp = await client.post(
        f"/api/listings/{listing_id}/images",
        headers=_auth_header(token),
        files=[("files", _image_file("cover.jpg", b"cover"))],
    )
    assert resp.status_code == 201
    return resp.json()


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


async def test_create_listing_report_success(client, session_factory):
    category = await _create_category(session_factory)
    seller_token = await _register(
        client, email="seller@example.com", username="seller"
    )
    buyer_token = await _register(client, email="buyer@example.com", username="buyer")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    reason = await _create_reason(
        session_factory,
        slug="fraud",
        title="Fraud",
        description="Scam or deceptive listing",
    )

    resp = await client.post(
        f"/api/listings/{listing['id']}/reports",
        headers=_auth_header(buyer_token),
        json={"reason_id": reason.id, "additional_info": "Looks suspicious"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["listing_id"] == listing["id"]
    assert body["reason"]["slug"] == "fraud"
    assert body["additional_info"] == "Looks suspicious"
    assert body["status"] == "pending"


async def test_create_listing_report_requires_additional_info_for_other(
    client,
    session_factory,
):
    category = await _create_category(session_factory)
    seller_token = await _register(
        client, email="seller2@example.com", username="seller2"
    )
    buyer_token = await _register(client, email="buyer2@example.com", username="buyer2")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    reason = await _create_reason(
        session_factory,
        slug="other",
        title="Other",
        description="Other reason",
    )

    resp = await client.post(
        f"/api/listings/{listing['id']}/reports",
        headers=_auth_header(buyer_token),
        json={"reason_id": reason.id},
    )

    assert resp.status_code == 400
    assert (
        resp.json()["detail"]
        == "Additional information is required for the 'other' reason"
    )


async def test_create_listing_report_blocks_duplicate_pending(client, session_factory):
    category = await _create_category(session_factory)
    seller_token = await _register(
        client, email="seller3@example.com", username="seller3"
    )
    buyer_token = await _register(client, email="buyer3@example.com", username="buyer3")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    reason = await _create_reason(
        session_factory,
        slug="fraud",
        title="Fraud",
        description="Scam or deceptive listing",
    )

    first = await client.post(
        f"/api/listings/{listing['id']}/reports",
        headers=_auth_header(buyer_token),
        json={"reason_id": reason.id},
    )
    assert first.status_code == 201

    second = await client.post(
        f"/api/listings/{listing['id']}/reports",
        headers=_auth_header(buyer_token),
        json={"reason_id": reason.id},
    )

    assert second.status_code == 409
    assert (
        second.json()["detail"] == "You already have a pending report for this listing"
    )


async def test_create_listing_report_blocks_own_listing(client, session_factory):
    category = await _create_category(session_factory)
    seller_token = await _register(
        client, email="seller4@example.com", username="seller4"
    )
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    reason = await _create_reason(
        session_factory,
        slug="fraud",
        title="Fraud",
        description="Scam or deceptive listing",
    )

    resp = await client.post(
        f"/api/listings/{listing['id']}/reports",
        headers=_auth_header(seller_token),
        json={"reason_id": reason.id},
    )

    assert resp.status_code == 403
    assert resp.json()["detail"] == "You cannot report your own listing"


async def test_create_listing_report_rejects_inactive_reason(client, session_factory):
    category = await _create_category(session_factory)
    seller_token = await _register(
        client, email="seller5@example.com", username="seller5"
    )
    buyer_token = await _register(client, email="buyer5@example.com", username="buyer5")
    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    reason = await _create_reason(
        session_factory,
        slug="fraud",
        title="Fraud",
        description="Scam or deceptive listing",
        is_active=False,
    )

    resp = await client.post(
        f"/api/listings/{listing['id']}/reports",
        headers=_auth_header(buyer_token),
        json={"reason_id": reason.id},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Report reason is not available"


async def test_get_reports_returns_stats_and_filters(client, session_factory):
    category = await _create_category(session_factory)
    seller_token = await _register(
        client, email="seller6@example.com", username="seller6"
    )
    buyer_token = await _register(client, email="buyer6@example.com", username="buyer6")
    moderator_token = await _register(
        client, email="moderator@example.com", username="moderator"
    )
    await _make_moderator(session_factory, username="moderator")

    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    uploaded_images = await _upload_listing_image(
        client,
        token=seller_token,
        listing_id=listing["id"],
    )
    await _activate_listing(client, token=seller_token, listing_id=listing["id"])
    reason = await _create_reason(
        session_factory,
        slug="fraud",
        title="Fraud",
        description="Scam or deceptive listing",
    )

    create_resp = await client.post(
        f"/api/listings/{listing['id']}/reports",
        headers=_auth_header(buyer_token),
        json={"reason_id": reason.id, "additional_info": "A" * 150},
    )
    assert create_resp.status_code == 201

    list_resp = await client.get("/api/reports", headers=_auth_header(moderator_token))

    assert list_resp.status_code == 200
    body = list_resp.json()
    assert body["stats"] == {"new_today": 1, "no_action": 0, "unseen": 1}
    assert len(body["reports"]) == 1
    report = body["reports"][0]
    assert report["reason"]["slug"] == "fraud"
    assert report["seen"] is False
    assert report["listing"]["primary_image_url"] == uploaded_images[0]["url"]
    assert report["seller"]["username"] == "seller6"
    assert report["additional_info_preview"].endswith("...")

    unseen_resp = await client.get(
        "/api/reports?seen=unseen",
        headers=_auth_header(moderator_token),
    )
    assert unseen_resp.status_code == 200
    assert len(unseen_resp.json()["reports"]) == 1


async def test_get_report_detail_marks_seen_once_for_all_moderators(
    client,
    session_factory,
):
    category = await _create_category(session_factory)
    seller_token = await _register(
        client, email="seller7@example.com", username="seller7"
    )
    buyer_token = await _register(client, email="buyer7@example.com", username="buyer7")
    moderator_a_token = await _register(
        client, email="moda@example.com", username="moda"
    )
    moderator_b_token = await _register(
        client, email="modb@example.com", username="modb", device_id="device-b"
    )
    await _make_moderator(session_factory, username="moda")
    await _make_moderator(session_factory, username="modb")

    listing = await _create_listing(client, token=seller_token, category_id=category.id)
    await _activate_listing(client, token=seller_token, listing_id=listing["id"])
    reason = await _create_reason(
        session_factory,
        slug="fraud",
        title="Fraud",
        description="Scam or deceptive listing",
    )

    create_resp = await client.post(
        f"/api/listings/{listing['id']}/reports",
        headers=_auth_header(buyer_token),
        json={"reason_id": reason.id, "additional_info": "Looks suspicious"},
    )
    report_id = create_resp.json()["id"]

    first_detail = await client.get(
        f"/api/reports/{report_id}",
        headers=_auth_header(moderator_a_token),
    )

    assert first_detail.status_code == 200
    first_body = first_detail.json()
    assert first_body["seen_at"] is not None
    assert (
        first_body["listing"]["description"]
        == _listing_payload(category_id=category.id)["description"]
    )

    moderator_a_id = None
    async with session_factory() as session:
        moderator_a_id = await session.scalar(
            select(Moderator.id)
            .join(User, Moderator.user_id == User.id)
            .where(User.username == "moda")
        )

    assert first_body["seen_by_moderator_id"] == str(moderator_a_id)

    second_detail = await client.get(
        f"/api/reports/{report_id}",
        headers=_auth_header(moderator_b_token),
    )

    assert second_detail.status_code == 200
    second_body = second_detail.json()
    assert second_body["seen_at"] == first_body["seen_at"]
    assert second_body["seen_by_moderator_id"] == first_body["seen_by_moderator_id"]

    seen_list = await client.get(
        "/api/reports?seen=seen",
        headers=_auth_header(moderator_b_token),
    )
    assert seen_list.status_code == 200
    assert len(seen_list.json()["reports"]) == 1
    assert seen_list.json()["stats"]["unseen"] == 0


async def test_get_reports_paginates_with_cursor(client, session_factory):
    category = await _create_category(session_factory)
    seller_token = await _register(
        client, email="seller8@example.com", username="seller8"
    )
    moderator_token = await _register(
        client, email="moderator8@example.com", username="moderator8"
    )
    await _make_moderator(session_factory, username="moderator8")
    buyer_a_token = await _register(
        client, email="buyera@example.com", username="buyera"
    )
    buyer_b_token = await _register(
        client, email="buyerb@example.com", username="buyerb", device_id="device-b"
    )
    reason = await _create_reason(
        session_factory,
        slug="fraud",
        title="Fraud",
        description="Scam or deceptive listing",
    )

    listing_a = await _create_listing(
        client, token=seller_token, category_id=category.id
    )
    await _activate_listing(client, token=seller_token, listing_id=listing_a["id"])
    listing_b = await _create_listing(
        client, token=seller_token, category_id=category.id
    )
    await _activate_listing(client, token=seller_token, listing_id=listing_b["id"])

    first_create = await client.post(
        f"/api/listings/{listing_a['id']}/reports",
        headers=_auth_header(buyer_a_token),
        json={"reason_id": reason.id},
    )
    assert first_create.status_code == 201
    second_create = await client.post(
        f"/api/listings/{listing_b['id']}/reports",
        headers=_auth_header(buyer_b_token),
        json={"reason_id": reason.id},
    )
    assert second_create.status_code == 201
    first_report_id = first_create.json()["id"]
    second_report_id = second_create.json()["id"]

    async with session_factory() as session:
        await session.execute(
            update(ListingReport)
            .where(ListingReport.id == first_report_id)
            .values(
                created_at=datetime.datetime.now(datetime.UTC)
                + datetime.timedelta(days=1)
            )
        )
        await session.commit()

    first_page = await client.get(
        "/api/reports?limit=1",
        headers=_auth_header(moderator_token),
    )
    assert first_page.status_code == 200
    first_body = first_page.json()
    assert len(first_body["reports"]) == 1
    assert first_body["next_cursor"] is not None

    second_page = await client.get(
        f"/api/reports?limit=1&cursor={first_body['next_cursor']}",
        headers=_auth_header(moderator_token),
    )
    assert second_page.status_code == 200
    second_body = second_page.json()
    assert len(second_body["reports"]) == 1
    assert first_body["reports"][0]["id"] == first_report_id
    assert second_body["reports"][0]["id"] == second_report_id
