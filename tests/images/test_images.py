from uuid import UUID

from sqlalchemy import select

from src.domains.categories.models import Category
from src.domains.images.models import ListingImage
from tests.helpers.auth import auth_header, register_user
from tests.helpers.listings import create_category, listing_payload


def _auth_header(token: str) -> dict[str, str]:
    return auth_header(token)


async def _register(
    client, *, email: str, username: str, device_id: str = "device"
) -> str:
    data = await register_user(
        client, email=email, username=username, device_id=device_id
    )
    return data["access_token"]


async def _create_category(session_factory, *, name: str) -> Category:
    return await create_category(session_factory, name=name, depth=0)


def _listing_payload(*, category_id: int) -> dict:
    return listing_payload(category_id=category_id)


async def _create_listing(client, *, token: str, category_id: int) -> dict:
    resp = await client.post(
        "/api/listings",
        headers=_auth_header(token),
        json=_listing_payload(category_id=category_id),
    )
    assert resp.status_code == 200
    return resp.json()


async def _set_listing_status(
    client, *, token: str, listing_id: str, status: str
) -> None:
    resp = await client.put(
        f"/api/listings/{listing_id}/status",
        headers=_auth_header(token),
        json={"status": status},
    )
    assert resp.status_code == 200


def _image_file(name: str, content: bytes = b"fake-image-bytes"):
    return name, content, "image/jpeg"


async def test_upload_listing_images_and_get_listing_includes_them(
    client, session_factory
):
    category = await _create_category(session_factory, name="Electronics")
    token = await _register(client, email="img1@example.com", username="img1")
    listing = await _create_listing(client, token=token, category_id=category.id)

    upload = await client.post(
        f"/api/listings/{listing['id']}/images",
        headers=_auth_header(token),
        files=[
            ("files", _image_file("first.jpg", b"first")),
            ("files", _image_file("second.jpg", b"second")),
        ],
    )

    assert upload.status_code == 201
    body = upload.json()
    assert [image["sort_order"] for image in body] == [0, 1]
    assert all(
        image["url"].startswith("https://test-bucket.s3.test-region.amazonaws.com/")
        for image in body
    )

    listing_resp = await client.get(f"/api/listings/{listing['id']}")
    assert listing_resp.status_code == 200

    images = listing_resp.json()["images"]
    assert [image["id"] for image in images] == [image["id"] for image in body]
    assert [image["sort_order"] for image in images] == [0, 1]

    async with session_factory() as session:
        listing_image_rows = (
            await session.scalars(
                select(ListingImage).where(
                    ListingImage.listing_id == UUID(listing["id"])
                )
            )
        ).all()

    assert {image["id"] for image in images} == {
        str(listing_image.image_id) for listing_image in listing_image_rows
    }
    assert {image["id"] for image in images}.isdisjoint(
        {str(listing_image.id) for listing_image in listing_image_rows}
    )


async def test_download_listing_image_returns_binary_content(client, session_factory):
    category = await _create_category(session_factory, name="Cameras")
    token = await _register(
        client, email="img-download@example.com", username="imgdownload"
    )
    listing = await _create_listing(client, token=token, category_id=category.id)

    upload = await client.post(
        f"/api/listings/{listing['id']}/images",
        headers=_auth_header(token),
        files=[("files", _image_file("photo.jpg", b"photo-bytes"))],
    )
    assert upload.status_code == 201
    image_id = upload.json()[0]["id"]

    download = await client.get(
        f"/api/listings/{listing['id']}/images/{image_id}/download"
    )
    assert download.status_code == 200
    assert download.content == b"photo-bytes"
    assert download.headers["content-type"] == "image/jpeg"


async def test_download_listing_image_returns_404_for_wrong_listing(
    client, session_factory
):
    category = await _create_category(session_factory, name="Consoles")
    token = await _register(client, email="img-wrong@example.com", username="imgwrong")
    listing_a = await _create_listing(client, token=token, category_id=category.id)
    listing_b = await _create_listing(client, token=token, category_id=category.id)

    upload = await client.post(
        f"/api/listings/{listing_a['id']}/images",
        headers=_auth_header(token),
        files=[("files", _image_file("photo.jpg", b"photo-bytes"))],
    )
    assert upload.status_code == 201
    image_id = upload.json()[0]["id"]

    download = await client.get(
        f"/api/listings/{listing_b['id']}/images/{image_id}/download"
    )
    assert download.status_code == 404
    assert download.json()["detail"] == "Listing image not found"


async def test_reorder_listing_images_updates_listing_response(client, session_factory):
    category = await _create_category(session_factory, name="Phones")
    token = await _register(client, email="img2@example.com", username="img2")
    listing = await _create_listing(client, token=token, category_id=category.id)

    upload = await client.post(
        f"/api/listings/{listing['id']}/images",
        headers=_auth_header(token),
        files=[
            ("files", _image_file("first.jpg", b"first")),
            ("files", _image_file("second.jpg", b"second")),
        ],
    )
    assert upload.status_code == 201
    uploaded_images = upload.json()

    reorder = await client.put(
        f"/api/listings/{listing['id']}/images/order",
        headers=_auth_header(token),
        json={"image_ids": [uploaded_images[1]["id"], uploaded_images[0]["id"]]},
    )
    assert reorder.status_code == 204

    listing_resp = await client.get(f"/api/listings/{listing['id']}")
    assert listing_resp.status_code == 200
    images = listing_resp.json()["images"]
    assert [image["id"] for image in images] == [
        uploaded_images[1]["id"],
        uploaded_images[0]["id"],
    ]
    assert [image["sort_order"] for image in images] == [0, 1]


async def test_delete_listing_image_compacts_sort_order(client, session_factory):
    category = await _create_category(session_factory, name="Monitors")
    token = await _register(client, email="img3@example.com", username="img3")
    listing = await _create_listing(client, token=token, category_id=category.id)

    upload = await client.post(
        f"/api/listings/{listing['id']}/images",
        headers=_auth_header(token),
        files=[
            ("files", _image_file("first.jpg", b"first")),
            ("files", _image_file("second.jpg", b"second")),
        ],
    )
    assert upload.status_code == 201
    uploaded_images = upload.json()

    delete = await client.delete(
        f"/api/listings/{listing['id']}/images/{uploaded_images[0]['id']}",
        headers=_auth_header(token),
    )
    assert delete.status_code == 204

    listing_resp = await client.get(f"/api/listings/{listing['id']}")
    assert listing_resp.status_code == 200
    images = listing_resp.json()["images"]
    assert len(images) == 1
    assert images[0]["id"] == uploaded_images[1]["id"]
    assert images[0]["sort_order"] == 0


async def test_active_listing_list_includes_uploaded_images(client, session_factory):
    category = await _create_category(session_factory, name="Tablets")
    token = await _register(client, email="img4@example.com", username="img4")
    listing = await _create_listing(client, token=token, category_id=category.id)

    upload = await client.post(
        f"/api/listings/{listing['id']}/images",
        headers=_auth_header(token),
        files=[("files", _image_file("cover.jpg", b"cover"))],
    )
    assert upload.status_code == 201
    await _set_listing_status(
        client, token=token, listing_id=listing["id"], status="active"
    )

    resp = await client.get("/api/listings")
    assert resp.status_code == 200

    returned_listing = next(
        item for item in resp.json()["listings"] if item["id"] == listing["id"]
    )
    assert len(returned_listing["images"]) == 1
    assert returned_listing["images"][0]["sort_order"] == 0


async def test_set_avatar_returns_avatar_url_and_user_endpoints_expose_it(client):
    token = await _register(client, email="avatar1@example.com", username="avatar1")

    set_avatar = await client.put(
        "/api/users/me/avatar",
        headers=_auth_header(token),
        files={"file": _image_file("avatar.jpg", b"avatar")},
    )
    assert set_avatar.status_code == 200
    avatar_url = set_avatar.json()["avatar_url"]
    assert avatar_url is not None
    assert avatar_url.startswith("https://test-bucket.s3.test-region.amazonaws.com/")

    me = await client.get("/api/users/me", headers=_auth_header(token))
    assert me.status_code == 200
    assert me.json()["avatar_url"] == avatar_url

    public_user = await client.get("/api/users/avatar1")
    assert public_user.status_code == 200
    assert public_user.json()["avatar_url"] == avatar_url


async def test_download_user_avatar_returns_binary_content(client):
    token = await _register(
        client, email="avatar-download@example.com", username="avatardownload"
    )

    set_avatar = await client.put(
        "/api/users/me/avatar",
        headers=_auth_header(token),
        files={"file": _image_file("avatar.jpg", b"avatar-bytes")},
    )
    assert set_avatar.status_code == 200

    download = await client.get("/api/users/avatardownload/avatar/download")
    assert download.status_code == 200
    assert download.content == b"avatar-bytes"
    assert download.headers["content-type"] == "image/jpeg"


async def test_delete_avatar_clears_avatar_url(client):
    token = await _register(client, email="avatar2@example.com", username="avatar2")

    set_avatar = await client.put(
        "/api/users/me/avatar",
        headers=_auth_header(token),
        files={"file": _image_file("avatar.jpg", b"avatar")},
    )
    assert set_avatar.status_code == 200
    assert set_avatar.json()["avatar_url"] is not None

    delete_avatar = await client.delete(
        "/api/users/me/avatar",
        headers=_auth_header(token),
    )
    assert delete_avatar.status_code == 204

    me = await client.get("/api/users/me", headers=_auth_header(token))
    assert me.status_code == 200
    assert me.json()["avatar_url"] is None


async def test_delete_avatar_without_existing_avatar_returns_404(client):
    token = await _register(client, email="avatar3@example.com", username="avatar3")

    resp = await client.delete(
        "/api/users/me/avatar",
        headers=_auth_header(token),
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "User avatar not found"


async def test_download_avatar_without_existing_avatar_returns_404(client):
    await _register(client, email="avatar4@example.com", username="avatar4")

    resp = await client.get("/api/users/avatar4/avatar/download")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "User avatar not found"
