from typing import Any

from src.domains.categories.models import Category


def listing_payload(
    *,
    category_id: int,
    title: str = "Gaming laptop 2026",
    description: str = "Powerful gaming laptop with RTX graphics card, clean condition, and full accessories included.",
    price: int = 2200,
    is_free: bool = False,
    is_tradable: bool = False,
    custom_filters: dict | None = None,
) -> dict[str, Any]:
    payload = {
        "title": title,
        "description": description,
        "price": price,
        "is_free": is_free,
        "is_tradable": is_tradable,
        "currency": "usd",
        "category_id": category_id,
    }
    if custom_filters is not None:
        payload["custom_filters"] = custom_filters

    return payload


async def create_listing(
    client, *, token: str, category_id: int, **kwargs
) -> dict[str, Any]:
    resp = await client.post(
        "/api/listings",
        headers={"Authorization": f"Bearer {token}"},
        json=listing_payload(category_id=category_id, **kwargs),
    )
    assert resp.status_code == 200
    return resp.json()


async def activate_listing(client, *, token: str, listing_id: str) -> dict[str, Any]:
    resp = await client.put(
        f"/api/listings/{listing_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "active"},
    )
    assert resp.status_code == 200
    return resp.json()


async def create_category(
    session_factory,
    *,
    name: str,
    depth: int = 0,
    category_id: int | None = None,
) -> Category:
    async with session_factory() as session:
        category = Category(id=category_id, name=name, depth=depth)
        session.add(category)
        await session.commit()
        await session.refresh(category)
        return category
