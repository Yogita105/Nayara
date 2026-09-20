"""Stock reservation, idempotent submission, and cancellation."""

import uuid

import pytest

ADDRESS = {
    "full_name": "Stock Tester",
    "phone": "9999900001",
    "line1": "12 Market Road",
    "line2": "",
    "city": "Mumbai",
    "state": "MH",
    "pincode": "400001",
}


@pytest.fixture
def stocked_product(mongo_db):
    """A product with a known stock level, removed afterwards."""

    def _create(stock):
        suffix = uuid.uuid4().hex[:8]
        product = {
            "product_id": f"prod_test_{suffix}",
            "name": f"Stock Test {suffix}",
            "slug": f"stock-test-{suffix}",
            "category": "home-care",
            "description": "Temporary product used by the inventory tests.",
            "short_description": "Temporary product.",
            "price": 100.0,
            "mrp": 120.0,
            "image": "",
            "images": [],
            "stock": stock,
            "rating": 4.5,
            "reviews_count": 0,
            "badges": [],
            "featured": False,
            "created_at": "2026-01-01T00:00:00+00:00",
        }
        mongo_db.products.insert_one(dict(product))
        created.append(product["product_id"])
        return product

    created = []
    yield _create
    mongo_db.products.delete_many({"product_id": {"$in": created}})


def stock_of(mongo_db, product_id):
    return mongo_db.products.find_one({"product_id": product_id})["stock"]


def place_order(client, base_url, items, key=None):
    headers = {"Idempotency-Key": key} if key else {}
    return client.post(
        f"{base_url}/api/orders",
        json={"items": items, "address": ADDRESS, "payment_method": "cod"},
        headers=headers,
    )


class TestStockReservation:
    def test_placing_an_order_reduces_stock(self, base_url, user_client, stocked_product, mongo_db):
        product = stocked_product(10)

        response = place_order(
            user_client, base_url, [{"product_id": product["product_id"], "quantity": 3}]
        )

        assert response.status_code == 200
        assert stock_of(mongo_db, product["product_id"]) == 7

    def test_ordering_more_than_available_is_refused(
        self, base_url, user_client, stocked_product, mongo_db
    ):
        product = stocked_product(2)

        response = place_order(
            user_client, base_url, [{"product_id": product["product_id"], "quantity": 5}]
        )

        assert response.status_code == 409
        assert "Only 2 left" in response.json()["detail"]
        assert stock_of(mongo_db, product["product_id"]) == 2

    def test_stock_can_be_taken_down_to_zero(
        self, base_url, user_client, stocked_product, mongo_db
    ):
        product = stocked_product(4)

        assert (
            place_order(
                user_client, base_url, [{"product_id": product["product_id"], "quantity": 4}]
            ).status_code
            == 200
        )
        assert stock_of(mongo_db, product["product_id"]) == 0

        assert (
            place_order(
                user_client, base_url, [{"product_id": product["product_id"], "quantity": 1}]
            ).status_code
            == 409
        )

    def test_a_rejected_line_rolls_back_the_earlier_ones(
        self, base_url, user_client, stocked_product, mongo_db
    ):
        plenty = stocked_product(10)
        scarce = stocked_product(1)

        response = place_order(
            user_client,
            base_url,
            [
                {"product_id": plenty["product_id"], "quantity": 2},
                {"product_id": scarce["product_id"], "quantity": 5},
            ],
        )

        assert response.status_code == 409
        assert stock_of(mongo_db, plenty["product_id"]) == 10
        assert stock_of(mongo_db, scarce["product_id"]) == 1

    def test_repeated_lines_count_towards_the_same_stock(
        self, base_url, user_client, stocked_product, mongo_db
    ):
        product = stocked_product(3)

        response = place_order(
            user_client,
            base_url,
            [
                {"product_id": product["product_id"], "quantity": 2},
                {"product_id": product["product_id"], "quantity": 2},
            ],
        )

        assert response.status_code == 409
        assert stock_of(mongo_db, product["product_id"]) == 3


class TestIdempotentSubmission:
    def test_the_same_key_returns_the_first_order(
        self, base_url, user_client, stocked_product, mongo_db
    ):
        product = stocked_product(10)
        key = uuid.uuid4().hex
        items = [{"product_id": product["product_id"], "quantity": 1}]

        first = place_order(user_client, base_url, items, key=key)
        second = place_order(user_client, base_url, items, key=key)

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["order_id"] == second.json()["order_id"]
        assert stock_of(mongo_db, product["product_id"]) == 9

    def test_a_new_key_creates_a_new_order(self, base_url, user_client, stocked_product, mongo_db):
        product = stocked_product(10)
        items = [{"product_id": product["product_id"], "quantity": 1}]

        first = place_order(user_client, base_url, items, key=uuid.uuid4().hex)
        second = place_order(user_client, base_url, items, key=uuid.uuid4().hex)

        assert first.json()["order_id"] != second.json()["order_id"]
        assert stock_of(mongo_db, product["product_id"]) == 8

    def test_a_key_can_be_reused_after_a_failure(
        self, base_url, user_client, stocked_product, mongo_db
    ):
        product = stocked_product(2)
        key = uuid.uuid4().hex

        refused = place_order(
            user_client,
            base_url,
            [{"product_id": product["product_id"], "quantity": 5}],
            key=key,
        )
        assert refused.status_code == 409

        retried = place_order(
            user_client,
            base_url,
            [{"product_id": product["product_id"], "quantity": 1}],
            key=key,
        )
        assert retried.status_code == 200
        assert stock_of(mongo_db, product["product_id"]) == 1


class TestStatusTransitions:
    """Delivered and cancelled are final, which is what protects stock."""

    def ordered(self, base_url, user_client, stocked_product, quantity=1):
        product = stocked_product(10)
        order_id = place_order(
            user_client,
            base_url,
            [{"product_id": product["product_id"], "quantity": quantity}],
        ).json()["order_id"]
        return product, order_id

    def advance(self, base_url, admin_client, order_id, status):
        return admin_client.put(f"{base_url}/api/admin/orders/{order_id}", json={"status": status})

    def test_an_order_moves_forward_through_its_states(
        self, base_url, user_client, admin_client, stocked_product
    ):
        _, order_id = self.ordered(base_url, user_client, stocked_product)

        for status in ("processing", "shipped", "delivered"):
            response = self.advance(base_url, admin_client, order_id, status)
            assert response.status_code == 200, status
            assert response.json()["status"] == status

    def test_an_order_cannot_move_backwards(
        self, base_url, user_client, admin_client, stocked_product
    ):
        _, order_id = self.ordered(base_url, user_client, stocked_product)
        self.advance(base_url, admin_client, order_id, "shipped")

        response = self.advance(base_url, admin_client, order_id, "placed")

        assert response.status_code == 409
        assert "cannot become" in response.json()["detail"]

    def test_a_delivered_order_is_final(self, base_url, user_client, admin_client, stocked_product):
        _, order_id = self.ordered(base_url, user_client, stocked_product)
        self.advance(base_url, admin_client, order_id, "shipped")
        self.advance(base_url, admin_client, order_id, "delivered")

        response = self.advance(base_url, admin_client, order_id, "cancelled")

        assert response.status_code == 409
        assert "final state" in response.json()["detail"]

    def test_a_cancelled_order_cannot_be_reopened(
        self, base_url, user_client, admin_client, stocked_product, mongo_db
    ):
        product, order_id = self.ordered(base_url, user_client, stocked_product, quantity=4)
        assert stock_of(mongo_db, product["product_id"]) == 6

        self.advance(base_url, admin_client, order_id, "cancelled")
        assert stock_of(mongo_db, product["product_id"]) == 10

        # Reopening would leave the order active after its stock went back,
        # so the catalogue would claim units that are actually spoken for.
        response = self.advance(base_url, admin_client, order_id, "processing")

        assert response.status_code == 409
        assert stock_of(mongo_db, product["product_id"]) == 10

    def test_repeating_the_current_status_is_accepted(
        self, base_url, user_client, admin_client, stocked_product, mongo_db
    ):
        product, order_id = self.ordered(base_url, user_client, stocked_product, quantity=2)
        self.advance(base_url, admin_client, order_id, "cancelled")
        assert stock_of(mongo_db, product["product_id"]) == 10

        response = self.advance(base_url, admin_client, order_id, "cancelled")

        assert response.status_code == 200
        # A retry must not hand back the same units twice.
        assert stock_of(mongo_db, product["product_id"]) == 10

    def test_an_order_can_be_cancelled_while_placed(
        self, base_url, user_client, admin_client, stocked_product
    ):
        _, order_id = self.ordered(base_url, user_client, stocked_product)

        assert self.advance(base_url, admin_client, order_id, "cancelled").status_code == 200

    def test_payment_status_can_still_be_corrected(
        self, base_url, user_client, admin_client, stocked_product
    ):
        _, order_id = self.ordered(base_url, user_client, stocked_product)

        response = admin_client.put(
            f"{base_url}/api/admin/orders/{order_id}",
            json={"payment_status": "paid"},
        )

        assert response.status_code == 200
        assert response.json()["payment_status"] == "paid"


class TestCancellationRestoresStock:
    def test_cancelling_returns_the_stock_once(
        self, base_url, user_client, admin_client, stocked_product, mongo_db
    ):
        product = stocked_product(10)
        order_id = place_order(
            user_client,
            base_url,
            [{"product_id": product["product_id"], "quantity": 4}],
        ).json()["order_id"]
        assert stock_of(mongo_db, product["product_id"]) == 6

        first = admin_client.put(
            f"{base_url}/api/admin/orders/{order_id}", json={"status": "cancelled"}
        )
        assert first.status_code == 200
        assert first.json()["status"] == "cancelled"
        assert stock_of(mongo_db, product["product_id"]) == 10

        # Cancelling again must not inflate the catalogue.
        admin_client.put(f"{base_url}/api/admin/orders/{order_id}", json={"status": "cancelled"})
        assert stock_of(mongo_db, product["product_id"]) == 10

    def test_other_status_changes_leave_stock_alone(
        self, base_url, user_client, admin_client, stocked_product, mongo_db
    ):
        product = stocked_product(10)
        order_id = place_order(
            user_client,
            base_url,
            [{"product_id": product["product_id"], "quantity": 2}],
        ).json()["order_id"]

        admin_client.put(f"{base_url}/api/admin/orders/{order_id}", json={"status": "shipped"})
        assert stock_of(mongo_db, product["product_id"]) == 8

    def test_updating_a_missing_order_returns_404(self, base_url, admin_client):
        response = admin_client.put(
            f"{base_url}/api/admin/orders/does_not_exist", json={"status": "shipped"}
        )
        assert response.status_code == 404
