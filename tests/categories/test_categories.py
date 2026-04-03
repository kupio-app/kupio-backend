from src.domains.categories.models import Category


# ── helpers ───────────────────────────────────────────────────────────────────


async def _create_category(
    session_factory,
    *,
    name: str,
    depth: int = 0,
    parent_id: int | None = None,
) -> Category:
    async with session_factory() as session:
        category = Category(name=name, depth=depth, parent_id=parent_id)
        session.add(category)
        await session.commit()
        await session.refresh(category)
        return category


# ── GET /api/categories ───────────────────────────────────────────────────────


async def test_get_categories_returns_all(client, session_factory):
    root = await _create_category(session_factory, name="Electronics", depth=0)
    child = await _create_category(
        session_factory, name="Phones", depth=1, parent_id=root.id
    )

    resp = await client.get("/api/categories")

    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert root.id in ids
    assert child.id in ids


async def test_get_categories_filter_by_depth(client, session_factory):
    root = await _create_category(session_factory, name="Vehicles", depth=0)
    child = await _create_category(
        session_factory, name="Cars", depth=1, parent_id=root.id
    )

    resp = await client.get("/api/categories?depth=0")

    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert root.id in ids
    assert child.id not in ids


async def test_get_categories_returns_empty_list_when_none_exist(client):
    resp = await client.get("/api/categories")

    assert resp.status_code == 200
    assert resp.json() == []


# ── GET /api/categories/{id} ──────────────────────────────────────────────────


async def test_get_category_by_id(client, session_factory):
    category = await _create_category(session_factory, name="Furniture", depth=0)

    resp = await client.get(f"/api/categories/{category.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == category.id
    assert body["name"] == "Furniture"
    assert body["depth"] == 0
    assert body["parent"] is None


async def test_get_category_includes_nested_parent(client, session_factory):
    root = await _create_category(session_factory, name="Sports", depth=0)
    child = await _create_category(
        session_factory, name="Football", depth=1, parent_id=root.id
    )

    resp = await client.get(f"/api/categories/{child.id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == child.id
    assert body["parent"]["id"] == root.id
    assert body["parent"]["name"] == "Sports"


async def test_get_category_not_found_returns_404(client):
    resp = await client.get("/api/categories/999999")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Category not found"


# ── GET /api/categories/{id}/subcategories ────────────────────────────────────


async def test_get_subcategories_returns_direct_children(client, session_factory):
    root = await _create_category(session_factory, name="Clothing", depth=0)
    child_a = await _create_category(
        session_factory, name="Men", depth=1, parent_id=root.id
    )
    child_b = await _create_category(
        session_factory, name="Women", depth=1, parent_id=root.id
    )
    grandchild = await _create_category(
        session_factory, name="T-Shirts", depth=2, parent_id=child_a.id
    )

    resp = await client.get(f"/api/categories/{root.id}/subcategories")

    assert resp.status_code == 200
    ids = [c["id"] for c in resp.json()]
    assert child_a.id in ids
    assert child_b.id in ids
    assert grandchild.id not in ids  # only direct children, not grandchildren


async def test_get_subcategories_returns_empty_for_leaf(client, session_factory):
    category = await _create_category(session_factory, name="Books", depth=0)

    resp = await client.get(f"/api/categories/{category.id}/subcategories")

    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_subcategories_not_found_returns_404(client):
    resp = await client.get("/api/categories/999999/subcategories")

    assert resp.status_code == 404


# ── GET /api/categories/{id}/breadcrumbs ─────────────────────────────────────


async def test_get_breadcrumbs_for_root_category(client, session_factory):
    root = await _create_category(session_factory, name="Root", depth=0)

    resp = await client.get(f"/api/categories/{root.id}/breadcrumbs")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["id"] == root.id


async def test_get_breadcrumbs_returns_full_chain_root_to_current(
    client, session_factory
):
    root = await _create_category(session_factory, name="Home", depth=0)
    mid = await _create_category(
        session_factory, name="Kitchen", depth=1, parent_id=root.id
    )
    leaf = await _create_category(
        session_factory, name="Cookware", depth=2, parent_id=mid.id
    )

    resp = await client.get(f"/api/categories/{leaf.id}/breadcrumbs")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 3
    assert [c["id"] for c in body] == [root.id, mid.id, leaf.id]


async def test_get_breadcrumbs_not_found_returns_404(client):
    resp = await client.get("/api/categories/999999/breadcrumbs")

    assert resp.status_code == 404
