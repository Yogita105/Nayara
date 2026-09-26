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
            # Every product carries at least one variant, and stock lives on
            # it. The product's own count mirrors it.
            "option_name": "Size",
            "price_from": 100.0,
            "variants": [
                {
                    "variant_id": f"var_test_{suffix}",
                    "label": "Standard",
                    "price": 100.0,
                    "mrp": 120.0,
                    "stock": stock,
                    "image": "",
                }
            ],
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
    """Everything on hand across a product's forms.

    The product no longer keeps a count of its own, so this adds up the
    variants exactly as the shop does.
    """
    product = mongo_db.products.find_one({"product_id": product_id})
    return sum(variant.get("stock", 0) for variant in product.get("variants", []))


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


class TestCartRespectsStock:
    """A cart holding more than exists is an order that will be refused, so
    the refusal is brought forward to the moment it is added."""

    def test_more_than_exists_is_refused(self, base_url, user_client, stocked_product):
        product = stocked_product(2)

        response = user_client.post(
            f"{base_url}/api/cart",
            json={"product_id": product["product_id"], "quantity": 3},
        )

        assert response.status_code == 409
        assert "2" in response.json()["detail"]

    def test_exactly_what_exists_is_allowed(self, base_url, user_client, stocked_product):
        product = stocked_product(2)

        response = user_client.post(
            f"{base_url}/api/cart",
            json={"product_id": product["product_id"], "quantity": 2},
        )

        assert response.status_code == 200

    def test_repeated_adds_cannot_walk_past_the_limit(self, base_url, user_client, stocked_product):
        """Adding one at a time is the way round a check made only on arrival."""
        product = stocked_product(2)
        url = f"{base_url}/api/cart"
        body = {"product_id": product["product_id"], "quantity": 1}

        assert user_client.post(url, json=body).status_code == 200
        assert user_client.post(url, json=body).status_code == 200
        third = user_client.post(url, json=body)

        assert third.status_code == 409
        assert "already has 2" in third.json()["detail"]

    def test_the_cart_still_holds_only_what_is_available(
        self, base_url, user_client, stocked_product
    ):
        product = stocked_product(2)
        url = f"{base_url}/api/cart"
        body = {"product_id": product["product_id"], "quantity": 1}
        user_client.post(url, json=body)
        user_client.post(url, json=body)
        user_client.post(url, json=body)

        cart = user_client.get(f"{base_url}/api/cart").json()
        line = next(item for item in cart["items"] if item["product_id"] == product["product_id"])

        assert line["quantity"] == 2

    def test_setting_a_quantity_beyond_stock_is_refused(
        self, base_url, user_client, stocked_product
    ):
        product = stocked_product(2)
        user_client.post(
            f"{base_url}/api/cart",
            json={"product_id": product["product_id"], "quantity": 1},
        )

        response = user_client.put(
            f"{base_url}/api/cart/{product['product_id']}",
            json={"quantity": 5},
        )

        assert response.status_code == 409

    def test_an_out_of_stock_product_cannot_be_added(self, base_url, user_client, stocked_product):
        product = stocked_product(0)

        response = user_client.post(
            f"{base_url}/api/cart",
            json={"product_id": product["product_id"], "quantity": 1},
        )

        assert response.status_code == 409
        assert "out of stock" in response.json()["detail"].lower()

    def test_a_product_that_does_not_exist_is_refused(self, base_url, user_client):
        response = user_client.post(
            f"{base_url}/api/cart",
            json={"product_id": "prod_not_a_real_product", "quantity": 1},
        )

        assert response.status_code == 404

    def test_the_refusal_names_the_field(self, base_url, user_client, stocked_product):
        """So the quantity control can be marked rather than a bare sentence."""
        product = stocked_product(1)

        response = user_client.post(
            f"{base_url}/api/cart",
            json={"product_id": product["product_id"], "quantity": 4},
        )

        assert response.json()["errors"][0]["field"] == "quantity"


@pytest.fixture
def two_variant_product(mongo_db):
    """A product genuinely sold in two forms, removed afterwards."""
    created = []

    def _create(first_stock, second_stock):
        suffix = uuid.uuid4().hex[:8]
        product = {
            "product_id": f"prod_test_{suffix}",
            "name": f"Two Form Test {suffix}",
            "slug": f"two-form-test-{suffix}",
            "category": "home-care",
            "description": "Temporary product used by the variant tests.",
            "short_description": "Temporary product.",
            "price": 100.0,
            "mrp": 120.0,
            "price_from": 100.0,
            "option_name": "Weight",
            "image": "",
            "images": [],
            "stock": first_stock + second_stock,
            "variants": [
                {
                    "variant_id": f"var_{suffix}_small",
                    "label": "500g",
                    "price": 100.0,
                    "mrp": 120.0,
                    "stock": first_stock,
                    "image": "",
                },
                {
                    "variant_id": f"var_{suffix}_large",
                    "label": "1kg",
                    "price": 180.0,
                    "mrp": 240.0,
                    "stock": second_stock,
                    "image": "",
                },
            ],
            "rating": 4.5,
            "reviews_count": 0,
            "badges": [],
            "featured": False,
            "created_at": "2026-01-01T00:00:00+00:00",
        }
        mongo_db.products.insert_one(dict(product))
        created.append(product["product_id"])
        return product

    yield _create

    mongo_db.orders.delete_many({"items.product_id": {"$in": created}})
    mongo_db.products.delete_many({"product_id": {"$in": created}})


def variant_stock(mongo_db, product_id, variant_id):
    product = mongo_db.products.find_one({"product_id": product_id})
    return next(v["stock"] for v in product["variants"] if v["variant_id"] == variant_id)


class TestStockBelongsToTheVariant:
    """A kilo bag and a half-kilo bag run out independently."""

    def test_buying_one_form_leaves_the_other_alone(
        self, base_url, user_client, two_variant_product, mongo_db
    ):
        product = two_variant_product(5, 5)
        small, large = product["variants"]

        response = place_order(
            user_client,
            base_url,
            [
                {
                    "product_id": product["product_id"],
                    "variant_id": small["variant_id"],
                    "quantity": 2,
                }
            ],
        )

        assert response.status_code == 200
        assert variant_stock(mongo_db, product["product_id"], small["variant_id"]) == 3
        assert variant_stock(mongo_db, product["product_id"], large["variant_id"]) == 5

    def test_one_form_selling_out_does_not_stop_the_other(
        self, base_url, user_client, two_variant_product, mongo_db
    ):
        product = two_variant_product(0, 4)
        small, large = product["variants"]

        sold_out = place_order(
            user_client,
            base_url,
            [
                {
                    "product_id": product["product_id"],
                    "variant_id": small["variant_id"],
                    "quantity": 1,
                }
            ],
        )
        available = place_order(
            user_client,
            base_url,
            [
                {
                    "product_id": product["product_id"],
                    "variant_id": large["variant_id"],
                    "quantity": 1,
                }
            ],
        )

        assert sold_out.status_code == 409
        assert available.status_code == 200
        assert variant_stock(mongo_db, product["product_id"], large["variant_id"]) == 3

    def test_the_refusal_names_the_form(self, base_url, user_client, two_variant_product):
        product = two_variant_product(1, 5)
        small = product["variants"][0]

        response = place_order(
            user_client,
            base_url,
            [
                {
                    "product_id": product["product_id"],
                    "variant_id": small["variant_id"],
                    "quantity": 3,
                }
            ],
        )

        assert response.status_code == 409
        assert "500g" in response.json()["detail"]

    def test_an_order_records_which_form_was_bought(
        self, base_url, user_client, two_variant_product
    ):
        product = two_variant_product(5, 5)
        large = product["variants"][1]

        response = place_order(
            user_client,
            base_url,
            [
                {
                    "product_id": product["product_id"],
                    "variant_id": large["variant_id"],
                    "quantity": 1,
                }
            ],
        )

        line = response.json()["items"][0]
        assert line["variant_label"] == "1kg"
        assert line["price"] == 180.0, "the variant's price, not the product's"

    def test_two_forms_of_one_product_are_separate_lines(
        self, base_url, user_client, two_variant_product, mongo_db
    ):
        product = two_variant_product(5, 5)
        small, large = product["variants"]

        response = place_order(
            user_client,
            base_url,
            [
                {
                    "product_id": product["product_id"],
                    "variant_id": small["variant_id"],
                    "quantity": 1,
                },
                {
                    "product_id": product["product_id"],
                    "variant_id": large["variant_id"],
                    "quantity": 1,
                },
            ],
        )

        assert response.status_code == 200
        assert len(response.json()["items"]) == 2
        assert variant_stock(mongo_db, product["product_id"], small["variant_id"]) == 4
        assert variant_stock(mongo_db, product["product_id"], large["variant_id"]) == 4

    def test_choosing_nothing_is_refused_when_there_is_a_choice(
        self, base_url, user_client, two_variant_product
    ):
        """A product sold in two forms cannot be bought without saying which."""
        product = two_variant_product(5, 5)

        response = place_order(
            user_client, base_url, [{"product_id": product["product_id"], "quantity": 1}]
        )

        assert response.status_code == 422

    def test_an_unknown_form_is_refused(self, base_url, user_client, two_variant_product):
        product = two_variant_product(5, 5)

        response = place_order(
            user_client,
            base_url,
            [
                {
                    "product_id": product["product_id"],
                    "variant_id": "var_does_not_exist",
                    "quantity": 1,
                }
            ],
        )

        assert response.status_code == 404

    def test_cancelling_returns_stock_to_the_right_form(
        self, base_url, user_client, admin_client, two_variant_product, mongo_db
    ):
        product = two_variant_product(5, 5)
        small, large = product["variants"]
        placed = place_order(
            user_client,
            base_url,
            [
                {
                    "product_id": product["product_id"],
                    "variant_id": small["variant_id"],
                    "quantity": 2,
                }
            ],
        )
        order_id = placed.json()["order_id"]

        admin_client.put(f"{base_url}/api/admin/orders/{order_id}", json={"status": "cancelled"})

        assert variant_stock(mongo_db, product["product_id"], small["variant_id"]) == 5
        assert variant_stock(mongo_db, product["product_id"], large["variant_id"]) == 5


class TestCartHoldsAForm:
    """Two forms of one product are two lines, not one."""

    def test_each_form_is_its_own_line(self, base_url, user_client, two_variant_product):
        product = two_variant_product(5, 5)
        small, large = product["variants"]
        user_client.delete(f"{base_url}/api/cart")

        for variant in (small, large):
            added = user_client.post(
                f"{base_url}/api/cart",
                json={
                    "product_id": product["product_id"],
                    "variant_id": variant["variant_id"],
                    "quantity": 1,
                },
            )
            assert added.status_code == 200

        cart = user_client.get(f"{base_url}/api/cart").json()
        lines = [i for i in cart["items"] if i["product_id"] == product["product_id"]]

        assert len(lines) == 2
        assert {line["variant_label"] for line in lines} == {"500g", "1kg"}
        user_client.delete(f"{base_url}/api/cart")

    def test_a_line_is_priced_by_its_form(self, base_url, user_client, two_variant_product):
        product = two_variant_product(5, 5)
        large = product["variants"][1]
        user_client.delete(f"{base_url}/api/cart")

        user_client.post(
            f"{base_url}/api/cart",
            json={
                "product_id": product["product_id"],
                "variant_id": large["variant_id"],
                "quantity": 1,
            },
        )

        cart = user_client.get(f"{base_url}/api/cart").json()
        line = next(i for i in cart["items"] if i["product_id"] == product["product_id"])

        assert line["price"] == 180.0
        assert line["stock"] == 5
        user_client.delete(f"{base_url}/api/cart")

    def test_the_limit_is_that_form_alone(self, base_url, user_client, two_variant_product):
        """Five of the large one does not make the small one available."""
        product = two_variant_product(1, 50)
        small = product["variants"][0]
        user_client.delete(f"{base_url}/api/cart")

        response = user_client.post(
            f"{base_url}/api/cart",
            json={
                "product_id": product["product_id"],
                "variant_id": small["variant_id"],
                "quantity": 2,
            },
        )

        assert response.status_code == 409
        assert "500g" in response.json()["detail"]
        user_client.delete(f"{base_url}/api/cart")

    def test_changing_one_forms_quantity_leaves_the_other(
        self, base_url, user_client, two_variant_product
    ):
        """Setting the 1kg to three must not disturb the 500g beside it."""
        product = two_variant_product(5, 5)
        small, large = product["variants"]
        user_client.delete(f"{base_url}/api/cart")
        for variant in (small, large):
            user_client.post(
                f"{base_url}/api/cart",
                json={
                    "product_id": product["product_id"],
                    "variant_id": variant["variant_id"],
                    "quantity": 1,
                },
            )

        changed = user_client.put(
            f"{base_url}/api/cart/{product['product_id']}",
            json={"variant_id": large["variant_id"], "quantity": 3},
        )

        assert changed.status_code == 200, changed.text
        cart = user_client.get(f"{base_url}/api/cart").json()
        held = {
            line["variant_label"]: line["quantity"]
            for line in cart["items"]
            if line["product_id"] == product["product_id"]
        }
        assert held == {"500g": 1, "1kg": 3}
        user_client.delete(f"{base_url}/api/cart")

    def test_removing_one_form_leaves_the_other(self, base_url, user_client, two_variant_product):
        """Taking the 1kg out of a cart must not take the 500g with it."""
        product = two_variant_product(5, 5)
        small, large = product["variants"]
        user_client.delete(f"{base_url}/api/cart")
        for variant in (small, large):
            user_client.post(
                f"{base_url}/api/cart",
                json={
                    "product_id": product["product_id"],
                    "variant_id": variant["variant_id"],
                    "quantity": 1,
                },
            )

        removed = user_client.delete(
            f"{base_url}/api/cart/{product['product_id']}",
            params={"variant_id": large["variant_id"]},
        )

        assert removed.status_code == 200
        cart = user_client.get(f"{base_url}/api/cart").json()
        lines = [i for i in cart["items"] if i["product_id"] == product["product_id"]]
        assert [line["variant_label"] for line in lines] == ["500g"]
        user_client.delete(f"{base_url}/api/cart")

    def test_naming_no_form_removes_the_product_entirely(
        self, base_url, user_client, two_variant_product
    ):
        """What a client that predates forms means by removing an item."""
        product = two_variant_product(5, 5)
        user_client.delete(f"{base_url}/api/cart")
        for variant in product["variants"]:
            user_client.post(
                f"{base_url}/api/cart",
                json={
                    "product_id": product["product_id"],
                    "variant_id": variant["variant_id"],
                    "quantity": 1,
                },
            )

        user_client.delete(f"{base_url}/api/cart/{product['product_id']}")

        cart = user_client.get(f"{base_url}/api/cart").json()
        lines = [i for i in cart["items"] if i["product_id"] == product["product_id"]]
        assert lines == []
        user_client.delete(f"{base_url}/api/cart")

    def test_a_line_stored_before_forms_existed_still_reads(
        self, base_url, user_client, user_session, mongo_db, stocked_product
    ):
        """Carts written before this change name no form, and must not break."""
        product = stocked_product(4)
        mongo_db.carts.update_one(
            {"user_id": user_session["user_id"]},
            {"$set": {"items": [{"product_id": product["product_id"], "quantity": 1}]}},
            upsert=True,
        )

        cart = user_client.get(f"{base_url}/api/cart").json()
        line = next(i for i in cart["items"] if i["product_id"] == product["product_id"])

        assert line["quantity"] == 1
        assert line["variant_label"] == "Standard"
        assert line["stock"] == 4
        user_client.delete(f"{base_url}/api/cart")
