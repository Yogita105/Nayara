"""What delivery costs, and that the shop charges what it quoted.

The threshold was written into the cart, the checkout page and the order
endpoint separately. Three copies of one number is a customer shown one
total and billed another, so what matters here is that the figure the API
charges is the one an administrator set, and that the storefront can read
the same one.
"""

import sys
import uuid
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models import DEFAULT_SHIPPING, ShippingSettings  # noqa: E402
from app.routers.orders import calculate_totals  # noqa: E402

SHIPPING = "/api/settings/shipping"
ADMIN_SHIPPING = "/api/admin/settings/shipping"

ADDRESS = {
    "full_name": "Delivery Tester",
    "phone": "9999900009",
    "line1": "12 Market Road",
    "line2": "",
    "city": "Mumbai",
    "state": "MH",
    "pincode": "400001",
}


def lines(*prices):
    return [{"price": price, "quantity": 1} for price in prices]


@pytest.fixture
def restore_shipping(mongo_db):
    before = mongo_db.settings.find_one({"key": "shipping"})
    yield
    if before:
        mongo_db.settings.replace_one({"key": "shipping"}, before, upsert=True)
    else:
        mongo_db.settings.delete_one({"key": "shipping"})


@pytest.fixture
def priced_product(mongo_db):
    """A product at a price the test chooses, removed afterwards."""
    created = []

    def _create(price):
        suffix = uuid.uuid4().hex[:8]
        product = {
            "product_id": f"prod_test_{suffix}",
            "name": f"Delivery Test {suffix}",
            "slug": f"delivery-test-{suffix}",
            "category": "home-care",
            "description": "Temporary product used by the delivery tests.",
            "short_description": "Temporary product.",
            "image": "",
            "images": [],
            "option_name": "Size",
            "price_from": price,
            "variants": [
                {
                    "variant_id": f"var_test_{suffix}",
                    "label": "Standard",
                    "price": price,
                    "mrp": price,
                    "stock": 50,
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

    yield _create

    mongo_db.orders.delete_many({"items.product_id": {"$in": created}})
    mongo_db.products.delete_many({"product_id": {"$in": created}})


class TestWorkingOutTheTotal:
    def test_a_small_order_pays_for_delivery(self):
        totals = calculate_totals(lines(100), DEFAULT_SHIPPING)

        assert totals["shipping"] == DEFAULT_SHIPPING.flat_rate
        assert totals["total"] == 100 + DEFAULT_SHIPPING.flat_rate

    def test_reaching_the_threshold_exactly_is_enough(self):
        """Told "free above 499", a customer spending exactly 499 expects it."""
        totals = calculate_totals(lines(DEFAULT_SHIPPING.free_above), DEFAULT_SHIPPING)

        assert totals["shipping"] == 0

    def test_an_empty_order_is_not_charged_for_a_delivery(self):
        totals = calculate_totals([], DEFAULT_SHIPPING)

        assert totals == {"subtotal": 0, "shipping": 0, "total": 0}

    def test_the_figures_come_from_the_settings_given(self):
        """Not from a constant: the whole point is that they can change."""
        generous = ShippingSettings(free_above=200, flat_rate=25)

        assert calculate_totals(lines(250), generous)["shipping"] == 0
        assert calculate_totals(lines(150), generous)["shipping"] == 25

    def test_delivery_can_be_free_for_everyone(self):
        totals = calculate_totals(lines(10), ShippingSettings(free_above=0, flat_rate=40))

        assert totals["shipping"] == 0


class TestReadingThem:
    def test_anyone_may_read_them(self, base_url, anon_client):
        """The cart quotes delivery before anyone has signed in."""
        response = anon_client.get(f"{base_url}{SHIPPING}")

        assert response.status_code == 200
        assert set(response.json()) == {"free_above", "flat_rate"}

    def test_a_shop_that_has_never_set_them_still_quotes_delivery(
        self, base_url, anon_client, mongo_db, restore_shipping
    ):
        mongo_db.settings.delete_one({"key": "shipping"})

        body = anon_client.get(f"{base_url}{SHIPPING}").json()

        assert body["free_above"] == DEFAULT_SHIPPING.free_above
        assert body["flat_rate"] == DEFAULT_SHIPPING.flat_rate


class TestChangingThem:
    def test_an_administrator_may_change_them(
        self, base_url, admin_client, anon_client, restore_shipping
    ):
        response = admin_client.put(
            f"{base_url}{ADMIN_SHIPPING}", json={"free_above": 750, "flat_rate": 60}
        )

        assert response.status_code == 200, response.text
        assert anon_client.get(f"{base_url}{SHIPPING}").json() == {
            "free_above": 750,
            "flat_rate": 60,
        }

    def test_a_customer_may_not(self, base_url, user_client):
        response = user_client.put(
            f"{base_url}{ADMIN_SHIPPING}", json={"free_above": 1, "flat_rate": 1}
        )

        assert response.status_code == 403

    @pytest.mark.parametrize(
        "settings",
        [
            {"free_above": -1, "flat_rate": 49},
            {"free_above": 499, "flat_rate": -1},
            {"free_above": "free", "flat_rate": 49},
            {"flat_rate": 49},
            {"free_above": 499},
        ],
    )
    def test_nonsense_is_refused(self, base_url, admin_client, restore_shipping, settings):
        response = admin_client.put(f"{base_url}{ADMIN_SHIPPING}", json=settings)

        assert response.status_code == 422


class TestTheShopChargesWhatItSet:
    """The reason this is one setting rather than three copies of a number."""

    def test_an_order_below_the_threshold_is_charged_delivery(
        self, base_url, user_client, admin_client, priced_product, restore_shipping
    ):
        admin_client.put(f"{base_url}{ADMIN_SHIPPING}", json={"free_above": 500, "flat_rate": 70})
        product = priced_product(100)

        order = user_client.post(
            f"{base_url}/api/orders",
            json={
                "items": [{"product_id": product["product_id"], "quantity": 1}],
                "address": ADDRESS,
                "payment_method": "cod",
            },
        ).json()

        assert order["shipping"] == 70
        assert order["total"] == 170

    def test_raising_the_threshold_starts_charging_an_order_that_was_free(
        self, base_url, user_client, admin_client, priced_product, restore_shipping
    ):
        """The figure the shop charges has to follow the one that was set."""
        product = priced_product(600)
        admin_client.put(f"{base_url}{ADMIN_SHIPPING}", json={"free_above": 500, "flat_rate": 70})

        free = user_client.post(
            f"{base_url}/api/orders",
            json={
                "items": [{"product_id": product["product_id"], "quantity": 1}],
                "address": ADDRESS,
                "payment_method": "cod",
            },
        ).json()

        admin_client.put(f"{base_url}{ADMIN_SHIPPING}", json={"free_above": 1000, "flat_rate": 70})
        charged = user_client.post(
            f"{base_url}/api/orders",
            json={
                "items": [{"product_id": product["product_id"], "quantity": 1}],
                "address": ADDRESS,
                "payment_method": "cod",
            },
        ).json()

        assert free["shipping"] == 0, "600 was above the 500 threshold"
        assert charged["shipping"] == 70, "600 is below the 1000 threshold"
