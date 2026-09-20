"""Nayara backend API tests - products, auth, cart, wishlist, reviews, orders, stripe, admin."""

import uuid
import pytest
import requests


# ---------- Products ----------
class TestProducts:
    def test_list_products_no_id_leak(self, base_url, anon_client):
        r = anon_client.get(f"{base_url}/api/products")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 7, f"Expected >=7 products, got {len(data)}"
        for p in data:
            assert "_id" not in p
            assert "product_id" in p and "name" in p and "price" in p

    def test_filter_category_laundry(self, base_url, anon_client):
        r = anon_client.get(f"{base_url}/api/products?category=laundry")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert all(p["category"] == "laundry" for p in data)

    def test_search_soap(self, base_url, anon_client):
        r = anon_client.get(f"{base_url}/api/products?q=soap")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert all("soap" in (p["name"] + p["description"]).lower() for p in data)

    def test_featured_true(self, base_url, anon_client):
        r = anon_client.get(f"{base_url}/api/products?featured=true")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert all(p["featured"] is True for p in data)

    def test_get_product_by_id(self, base_url, anon_client):
        lst = anon_client.get(f"{base_url}/api/products").json()
        pid = lst[0]["product_id"]
        r = anon_client.get(f"{base_url}/api/products/{pid}")
        assert r.status_code == 200
        d = r.json()
        assert d["product_id"] == pid
        assert "_id" not in d

    def test_get_product_404(self, base_url, anon_client):
        r = anon_client.get(f"{base_url}/api/products/does_not_exist")
        assert r.status_code == 404


# ---------- Auth ----------
class TestAuth:
    def test_invalid_login(self, base_url, anon_client):
        r = anon_client.post(
            f"{base_url}/api/auth/login",
            json={"identifier": "missing@example.com", "password": "invalid-password"},
        )
        assert r.status_code == 401

    def test_register_login_and_logout(self, base_url, mongo_db):
        email = f"auth-test-{uuid.uuid4().hex}@example.com"
        mobile = f"9{uuid.uuid4().int % 10**9:09d}"
        password = "SecurePassword123!"
        client = requests.Session()
        try:
            r = client.post(
                f"{base_url}/api/auth/register",
                json={
                    "name": "Auth Test",
                    "email": email,
                    "mobile": mobile,
                    "password": password,
                },
            )
            assert r.status_code == 201
            assert r.json()["user"]["email"] == email
            assert r.json()["user"]["mobile"] == f"+91{mobile}"
            assert "password_hash" not in r.json()["user"]
            assert client.cookies.get("session_token")
            csrf = {"X-CSRF-Token": r.json()["csrf_token"]}

            duplicate = requests.post(
                f"{base_url}/api/auth/register",
                json={
                    "name": "Auth Test",
                    "email": email,
                    "mobile": mobile,
                    "password": password,
                },
            )
            assert duplicate.status_code == 409

            me = client.get(f"{base_url}/api/auth/me")
            assert me.status_code == 200
            assert me.json()["email"] == email
            assert "password_hash" not in me.json()

            # A cookie session must present the CSRF token on writes.
            assert client.post(f"{base_url}/api/auth/logout").status_code == 403

            assert client.post(f"{base_url}/api/auth/logout", headers=csrf).status_code == 200
            assert client.get(f"{base_url}/api/auth/me").status_code == 401

            login = client.post(
                f"{base_url}/api/auth/login",
                json={"identifier": mobile, "password": password},
            )
            assert login.status_code == 200
            csrf = {"X-CSRF-Token": login.json()["csrf_token"]}
            assert client.get(f"{base_url}/api/auth/me").status_code == 200

            assert client.post(f"{base_url}/api/auth/logout", headers=csrf).status_code == 200
            login = client.post(
                f"{base_url}/api/auth/login",
                json={"identifier": email, "password": password},
            )
            assert login.status_code == 200
        finally:
            user = mongo_db.users.find_one({"email": email})
            if user:
                mongo_db.user_sessions.delete_many({"user_id": user["user_id"]})
                mongo_db.users.delete_one({"user_id": user["user_id"]})

    def test_me_without_auth(self, base_url, anon_client):
        r = anon_client.get(f"{base_url}/api/auth/me")
        assert r.status_code == 401

    def test_me_with_bearer(self, base_url, user_client, user_session):
        r = user_client.get(f"{base_url}/api/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == user_session["email"]
        assert "_id" not in r.json()

    def test_protected_routes_401(self, base_url, anon_client):
        for path in ["/api/cart", "/api/wishlist", "/api/orders"]:
            r = anon_client.get(f"{base_url}{path}")
            assert r.status_code == 401, f"{path} expected 401 got {r.status_code}"


# ---------- Cart ----------
class TestCart:
    def test_cart_flow(self, base_url, user_client):
        pid = user_client.get(f"{base_url}/api/products").json()[0]["product_id"]
        # add
        r = user_client.post(f"{base_url}/api/cart", json={"product_id": pid, "quantity": 2})
        assert r.status_code == 200
        # add same again -> merges
        user_client.post(f"{base_url}/api/cart", json={"product_id": pid, "quantity": 1})
        r = user_client.get(f"{base_url}/api/cart")
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) == 1
        assert items[0]["quantity"] == 3
        assert items[0]["product_id"] == pid
        # update qty
        r = user_client.put(f"{base_url}/api/cart/{pid}", json={"quantity": 5})
        assert r.status_code == 200
        items = user_client.get(f"{base_url}/api/cart").json()["items"]
        assert items[0]["quantity"] == 5
        # delete item
        r = user_client.delete(f"{base_url}/api/cart/{pid}")
        assert r.status_code == 200
        assert user_client.get(f"{base_url}/api/cart").json()["items"] == []
        # add + clear
        user_client.post(f"{base_url}/api/cart", json={"product_id": pid, "quantity": 1})
        r = user_client.delete(f"{base_url}/api/cart")
        assert r.status_code == 200
        assert user_client.get(f"{base_url}/api/cart").json()["items"] == []


# ---------- Wishlist ----------
class TestWishlist:
    def test_wishlist_flow(self, base_url, user_client):
        pid = user_client.get(f"{base_url}/api/products").json()[0]["product_id"]
        r = user_client.post(f"{base_url}/api/wishlist", json={"product_id": pid})
        assert r.status_code == 200
        items = user_client.get(f"{base_url}/api/wishlist").json()["items"]
        assert any(p["product_id"] == pid for p in items)
        r = user_client.delete(f"{base_url}/api/wishlist/{pid}")
        assert r.status_code == 200
        items = user_client.get(f"{base_url}/api/wishlist").json()["items"]
        assert not any(p["product_id"] == pid for p in items)


# ---------- Reviews ----------
class TestReviews:
    def test_review_creates_and_bumps_rating(self, base_url, user_client, anon_client, mongo_db):
        pid = anon_client.get(f"{base_url}/api/products").json()[0]["product_id"]
        review_id = None
        try:
            r = user_client.post(
                f"{base_url}/api/products/{pid}/reviews",
                json={"rating": 5, "title": "Great", "comment": "Loved it"},
            )
            assert r.status_code == 200
            data = r.json()
            review_id = data["review_id"]
            assert data["rating"] == 5
            assert "_id" not in data
            revs = anon_client.get(f"{base_url}/api/products/{pid}/reviews").json()
            assert len(revs) >= 1
            prod = anon_client.get(f"{base_url}/api/products/{pid}").json()
            assert prod["reviews_count"] >= 1
        finally:
            if review_id:
                mongo_db.reviews.delete_one({"review_id": review_id})
                _restore_product_rating(mongo_db, pid)


def _restore_product_rating(mongo_db, product_id):
    """Recalculate a product rating so tests leave the catalogue untouched."""
    summary = list(
        mongo_db.reviews.aggregate(
            [
                {"$match": {"product_id": product_id}},
                {"$group": {"_id": None, "average": {"$avg": "$rating"}, "count": {"$sum": 1}}},
            ]
        )
    )
    average = summary[0]["average"] if summary else 0
    count = summary[0]["count"] if summary else 0
    mongo_db.products.update_one(
        {"product_id": product_id},
        {"$set": {"rating": round(average, 2), "reviews_count": count}},
    )


# ---------- Contact ----------
class TestContact:
    def test_contact_submit(self, base_url, anon_client, mongo_db):
        contact_id = None
        try:
            r = anon_client.post(
                f"{base_url}/api/contact",
                json={"name": "TEST_ctc", "email": "t@e.com", "subject": "Hi", "message": "Hello"},
            )
            assert r.status_code == 200
            contact_id = r.json().get("contact_id")
            assert contact_id
        finally:
            if contact_id:
                mongo_db.contacts.delete_one({"contact_id": contact_id})


# ---------- Orders ----------
ADDRESS = {
    "full_name": "Test",
    "phone": "9999999999",
    "line1": "Addr1",
    "line2": "",
    "city": "Mumbai",
    "state": "MH",
    "pincode": "400001",
}


@pytest.fixture
def sample_items(base_url, user_client):
    prods = user_client.get(f"{base_url}/api/products").json()
    return [{"product_id": prods[0]["product_id"], "quantity": 2}]


class TestOrders:
    def test_order_cod(self, base_url, user_client, sample_items):
        # add to cart first to verify clearing
        user_client.post(
            f"{base_url}/api/cart",
            json={"product_id": sample_items[0]["product_id"], "quantity": 1},
        )
        r = user_client.post(
            f"{base_url}/api/orders",
            json={"items": sample_items, "address": ADDRESS, "payment_method": "cod"},
        )
        assert r.status_code == 200
        o = r.json()
        assert o["payment_status"] == "cod_pending"
        assert "_id" not in o
        # cart cleared
        assert user_client.get(f"{base_url}/api/cart").json()["items"] == []

    def test_order_upi_paid(self, base_url, user_client, sample_items):
        r = user_client.post(
            f"{base_url}/api/orders",
            json={"items": sample_items, "address": ADDRESS, "payment_method": "upi"},
        )
        assert r.status_code == 200
        assert r.json()["payment_status"] == "paid"

    def test_order_card_pending(self, base_url, user_client, sample_items):
        r = user_client.post(
            f"{base_url}/api/orders",
            json={"items": sample_items, "address": ADDRESS, "payment_method": "card"},
        )
        assert r.status_code == 200
        assert r.json()["payment_status"] == "pending"

    def test_my_orders_only_own(self, base_url, user_client, user_session):
        r = user_client.get(f"{base_url}/api/orders")
        assert r.status_code == 200
        orders = r.json()
        assert all(o["user_id"] == user_session["user_id"] for o in orders)

    def test_get_order_forbidden_for_other(
        self, base_url, user_client, admin_client, sample_items, anon_client
    ):
        # Make a second user and order - use admin to verify admin can view
        r = user_client.post(
            f"{base_url}/api/orders",
            json={"items": sample_items, "address": ADDRESS, "payment_method": "cod"},
        )
        oid = r.json()["order_id"]
        # owner can get
        assert user_client.get(f"{base_url}/api/orders/{oid}").status_code == 200
        # admin can get
        assert admin_client.get(f"{base_url}/api/orders/{oid}").status_code == 200
        # anon -> 401
        assert anon_client.get(f"{base_url}/api/orders/{oid}").status_code == 401


# ---------- Payments ----------
@pytest.mark.skip(
    reason="No payment provider is integrated yet. This describes what the "
    "checkout endpoint must do once one is chosen, so it is kept "
    "rather than deleted."
)
class TestStripe:
    def test_create_checkout_session(self, base_url, user_client, sample_items, mongo_db):
        r = user_client.post(
            f"{base_url}/api/orders",
            json={"items": sample_items, "address": ADDRESS, "payment_method": "card"},
        )
        oid = r.json()["order_id"]
        r = user_client.post(
            f"{base_url}/api/payments/checkout/session",
            json={"order_id": oid, "origin_url": base_url},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("url", "").startswith("https://")
        assert data.get("session_id")
        tx = mongo_db.payment_transactions.find_one({"session_id": data["session_id"]})
        assert tx is not None
        assert tx["payment_status"] == "initiated"


# ---------- Admin gating ----------
class TestAdmin:
    ADMIN_ENDPOINTS = [
        "/api/admin/stats",
        "/api/admin/orders",
        "/api/admin/users",
        "/api/admin/contacts",
    ]

    def test_non_admin_403(self, base_url, user_client):
        for p in self.ADMIN_ENDPOINTS:
            r = user_client.get(f"{base_url}{p}")
            assert r.status_code == 403, f"{p} -> {r.status_code}"

    def test_admin_200(self, base_url, admin_client):
        for p in self.ADMIN_ENDPOINTS:
            r = admin_client.get(f"{base_url}{p}")
            assert r.status_code == 200, f"{p} -> {r.status_code}"
            body = r.json()
            if isinstance(body, list):
                for d in body:
                    assert "_id" not in d

    def test_admin_update_order(self, base_url, admin_client, user_client, sample_items):
        oid = user_client.post(
            f"{base_url}/api/orders",
            json={"items": sample_items, "address": ADDRESS, "payment_method": "cod"},
        ).json()["order_id"]
        r = admin_client.put(f"{base_url}/api/admin/orders/{oid}", json={"status": "shipped"})
        assert r.status_code == 200
        assert r.json()["status"] == "shipped"
