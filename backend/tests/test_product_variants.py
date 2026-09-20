"""Products sold in more than one form.

Price and stock have moved from the product onto a variant of it: a kilo bag
and a half-kilo bag are priced and run out independently. What these tests
hold is that every product has at least one form, that the product's own
figures always summarise them rather than being set by hand, and that a form
cannot be taken away while an order still depends on it.
"""

import sys
import uuid
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models import (  # noqa: E402
    MAX_VARIANTS,
    ProductVariant,
    cheapest_price,
    default_variant,
    variant_mirrors,
)
from scripts.add_product_variants import read_size  # noqa: E402

ADDRESS = {
    "full_name": "Variant Tester",
    "phone": "9999900007",
    "line1": "12 Market Road",
    "line2": "",
    "city": "Mumbai",
    "state": "MH",
    "pincode": "400001",
}


def product_payload(**overrides):
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "name": f"Variant Test {suffix}",
        "slug": f"variant-test-{suffix}",
        "category": "home-care",
        "price": 100.0,
        "mrp": 120.0,
        "stock": 7,
    }
    payload.update(overrides)
    return payload


def form(label, price, mrp=None, stock=5, **overrides):
    """One buyable form, as an administrator would send it."""
    entry = {"label": label, "price": price, "mrp": mrp or price, "stock": stock}
    entry.update(overrides)
    return entry


def labelled(product, label):
    return next(variant for variant in product["variants"] if variant["label"] == label)


class TestTheVariantItself:
    def test_a_variant_needs_a_label(self):
        with pytest.raises(ValueError):
            ProductVariant(label="", price=10, mrp=10)

    def test_mrp_cannot_be_below_the_price(self):
        """The saving shown to a customer would otherwise be negative."""
        with pytest.raises(ValueError):
            ProductVariant(label="1kg", price=200, mrp=150)

    def test_mrp_may_equal_the_price(self):
        variant = ProductVariant(label="1kg", price=200, mrp=200)

        assert variant.mrp == variant.price

    def test_a_variant_is_given_its_own_identity(self):
        first = ProductVariant(label="500g", price=100, mrp=120)
        second = ProductVariant(label="1kg", price=180, mrp=240)

        assert first.variant_id != second.variant_id
        assert first.variant_id.startswith("var_")

    def test_stock_cannot_be_negative(self):
        with pytest.raises(ValueError):
            ProductVariant(label="1kg", price=100, mrp=100, stock=-1)

    def test_an_image_is_optional(self):
        """Weights look alike and share the product's photograph; colours do
        not, which is the whole reason for choosing one."""
        assert ProductVariant(label="1kg", price=100, mrp=100).image == ""


class TestTheAdvertisedPrice:
    def test_it_is_the_cheapest_variant(self):
        variants = [
            {"price": 180.0},
            {"price": 100.0},
            {"price": 340.0},
        ]

        assert cheapest_price(variants) == 100.0

    def test_a_product_with_no_variants_falls_back(self):
        assert cheapest_price([], fallback=55.0) == 55.0

    def test_unreadable_entries_are_ignored(self):
        assert cheapest_price([{"price": None}, {"price": 20.0}]) == 20.0


class TestStandingInForAProductWithout:
    def test_it_carries_the_products_price_and_stock(self):
        variant = default_variant({"price": 45.0, "mrp": 60.0, "stock": 12})

        assert variant["price"] == 45.0
        assert variant["mrp"] == 60.0
        assert variant["stock"] == 12

    def test_a_missing_mrp_falls_back_to_the_price(self):
        variant = default_variant({"price": 45.0, "stock": 1})

        assert variant["mrp"] == 45.0


class TestReadingASizeFromAName:
    """A size already in the name is what the product is really sold as, so
    it is reused rather than every product being labelled "Standard"."""

    @pytest.mark.parametrize(
        "name,label,option",
        [
            ("Nayara Washing Powder Detergent 1kg", "1kg", "Weight"),
            ("Nayara Liquid Detergent 1L", "1L", "Volume"),
            ("Nayara Handwash Liquid 250ml", "250ml", "Volume"),
            ("Nayara Toilet Cleaner 500ml", "500ml", "Volume"),
            ("Something 500 g", "500g", "Weight"),
            ("Something 1.5 kg", "1.5kg", "Weight"),
        ],
    )
    def test_a_size_in_the_name_becomes_the_label(self, name, label, option):
        assert read_size(name) == (label, option)

    @pytest.mark.parametrize("name", ["Nayara Washing Soap Bar", "Nayara Bathing Soap", ""])
    def test_a_name_without_a_size_has_none(self, name):
        label, option = read_size(name)

        assert label is None
        assert option == "Size"


class TestEveryProductHasOne:
    """The invariant the later steps depend on. A product without a variant
    would mean two code paths through the cart, the order and the shop."""

    def test_a_new_product_is_given_one(self, base_url, admin_client, mongo_db):
        response = admin_client.post(f"{base_url}/api/products", json=product_payload())
        assert response.status_code == 200
        product_id = response.json()["product_id"]

        stored = mongo_db.products.find_one({"product_id": product_id})
        mongo_db.products.delete_one({"product_id": product_id})

        assert len(stored["variants"]) == 1
        assert stored["variants"][0]["price"] == 100.0
        assert stored["variants"][0]["stock"] == 7
        assert stored["price_from"] == 100.0

    def test_the_only_variant_follows_the_product_price(self, base_url, admin_client, mongo_db):
        """Until variants can be edited directly, the two must not drift."""
        payload = product_payload()
        created = admin_client.post(f"{base_url}/api/products", json=payload)
        product_id = created.json()["product_id"]

        payload.update({"price": 250.0, "mrp": 300.0, "stock": 3})
        admin_client.put(f"{base_url}/api/products/{product_id}", json=payload)

        stored = mongo_db.products.find_one({"product_id": product_id})
        mongo_db.products.delete_one({"product_id": product_id})

        assert stored["variants"][0]["price"] == 250.0
        assert stored["variants"][0]["mrp"] == 300.0
        assert stored["variants"][0]["stock"] == 3
        assert stored["price_from"] == 250.0

    def test_every_product_in_the_catalogue_has_one(self, mongo_db):
        without = mongo_db.products.count_documents({"variants": {"$in": [None, []]}})

        assert without == 0, "a product without a variant would need its own code path"

    def test_the_advertised_price_matches_the_variants(self, mongo_db):
        for product in mongo_db.products.find({}, {"_id": 0}):
            expected = cheapest_price(product.get("variants", []), product["price"])

            assert product.get("price_from") == expected, product["name"]


class TestLimits:
    def test_a_product_cannot_hold_endless_variants(self):
        """Embedded variants are read with the product, so the list is
        bounded rather than left to grow without limit."""
        assert MAX_VARIANTS == 20


class TestTheProductsOwnFigures:
    """`price`, `mrp` and `stock` on the product summarise its variants.

    Nothing sets them by hand, so they cannot be saved disagreeing with the
    forms they describe.
    """

    def test_the_price_is_the_cheapest_form(self):
        mirrors = variant_mirrors([form("1kg", 180), form("500g", 100)])

        assert mirrors["price"] == 100
        assert mirrors["price_from"] == 100

    def test_the_mrp_belongs_to_that_same_form(self):
        """Showing one form's price beside another's MRP invents a discount."""
        mirrors = variant_mirrors([form("1kg", 180, mrp=240), form("500g", 100, mrp=130)])

        assert mirrors["mrp"] == 130

    def test_the_stock_is_every_form_together(self):
        mirrors = variant_mirrors([form("1kg", 180, stock=4), form("500g", 100, stock=9)])

        assert mirrors["stock"] == 13


@pytest.fixture
def saved_product(base_url, admin_client, mongo_db):
    """A product created through the admin API and removed afterwards."""
    created = []

    def _save(**overrides):
        response = admin_client.post(f"{base_url}/api/products", json=product_payload(**overrides))
        assert response.status_code == 200, response.text
        body = response.json()
        created.append(body["product_id"])
        return body

    yield _save

    mongo_db.orders.delete_many({"items.product_id": {"$in": created}})
    mongo_db.carts.update_many({}, {"$pull": {"items": {"product_id": {"$in": created}}}})
    mongo_db.products.delete_many({"product_id": {"$in": created}})


class TestEditingTheForms:
    """An administrator decides what a product is sold as."""

    def test_a_product_can_be_created_with_several(self, saved_product):
        product = saved_product(
            option_name="Weight",
            variants=[form("500g", 100, mrp=130), form("1kg", 180, mrp=240)],
        )

        assert [variant["label"] for variant in product["variants"]] == ["500g", "1kg"]
        assert product["option_name"] == "Weight"

    def test_each_form_is_given_its_own_identity(self, saved_product):
        product = saved_product(variants=[form("500g", 100), form("1kg", 180)])

        identities = {variant["variant_id"] for variant in product["variants"]}
        assert len(identities) == 2

    def test_the_product_summarises_them(self, saved_product):
        product = saved_product(
            price=999.0,
            mrp=999.0,
            stock=999,
            variants=[form("500g", 100, mrp=130, stock=4), form("1kg", 180, mrp=240, stock=9)],
        )

        # What the request said about price and stock is ignored: those are
        # the variants' to decide.
        assert product["price"] == 100
        assert product["mrp"] == 130
        assert product["price_from"] == 100
        assert product["stock"] == 13

    def test_a_form_can_be_added_later(self, base_url, admin_client, saved_product):
        product = saved_product(variants=[form("500g", 100, stock=4)])
        payload = product_payload(
            name=product["name"],
            slug=product["slug"],
            variants=[
                {**product["variants"][0]},
                form("1kg", 180, mrp=240, stock=9),
            ],
        )

        response = admin_client.put(
            f"{base_url}/api/products/{product['product_id']}", json=payload
        )

        assert response.status_code == 200, response.text
        updated = response.json()
        assert [variant["label"] for variant in updated["variants"]] == ["500g", "1kg"]
        assert updated["stock"] == 13

    def test_an_existing_form_keeps_its_identity_when_edited(
        self, base_url, admin_client, saved_product
    ):
        """A new identity would orphan every cart and order naming the old one."""
        product = saved_product(variants=[form("500g", 100, stock=4)])
        only = product["variants"][0]
        payload = product_payload(
            name=product["name"],
            slug=product["slug"],
            variants=[{**only, "price": 120.0, "mrp": 150.0, "stock": 6}],
        )

        response = admin_client.put(
            f"{base_url}/api/products/{product['product_id']}", json=payload
        )

        assert response.status_code == 200, response.text
        updated = response.json()
        assert updated["variants"][0]["variant_id"] == only["variant_id"]
        assert updated["variants"][0]["price"] == 120.0
        assert updated["price"] == 120.0

    def test_a_form_can_be_removed(self, base_url, admin_client, saved_product):
        product = saved_product(variants=[form("500g", 100, stock=4), form("1kg", 180, stock=9)])
        payload = product_payload(
            name=product["name"],
            slug=product["slug"],
            variants=[labelled(product, "1kg")],
        )

        response = admin_client.put(
            f"{base_url}/api/products/{product['product_id']}", json=payload
        )

        assert response.status_code == 200, response.text
        updated = response.json()
        assert [variant["label"] for variant in updated["variants"]] == ["1kg"]
        assert updated["stock"] == 9
        assert updated["price"] == 180

    def test_two_forms_cannot_share_a_label(self, base_url, admin_client):
        """A customer choosing between two identical options is choosing blind."""
        payload = product_payload(variants=[form("1kg", 100), form(" 1KG ", 180)])

        response = admin_client.post(f"{base_url}/api/products", json=payload)

        assert response.status_code == 422
        assert "label" in response.json()["detail"].lower()

    def test_a_product_cannot_be_left_with_none(self, base_url, admin_client, saved_product):
        product = saved_product()
        payload = product_payload(name=product["name"], slug=product["slug"], variants=[])

        response = admin_client.put(
            f"{base_url}/api/products/{product['product_id']}", json=payload
        )

        assert response.status_code == 422

    def test_a_form_priced_above_its_mrp_is_refused(self, base_url, admin_client):
        payload = product_payload(variants=[form("1kg", 200, mrp=150)])

        response = admin_client.post(f"{base_url}/api/products", json=payload)

        assert response.status_code == 422


class TestARequestThatKnowsNothingOfForms:
    """Something that predates variants must not be able to destroy them."""

    def test_it_leaves_several_alone(self, base_url, admin_client, saved_product):
        product = saved_product(variants=[form("500g", 100, stock=4), form("1kg", 180, stock=9)])
        payload = product_payload(name=product["name"], slug=product["slug"])
        assert "variants" not in payload

        response = admin_client.put(
            f"{base_url}/api/products/{product['product_id']}", json=payload
        )

        assert response.status_code == 200, response.text
        assert len(response.json()["variants"]) == 2

    def test_it_cannot_put_the_summary_out_of_step(self, base_url, admin_client, saved_product):
        """Its price and stock are recomputed from the forms, not believed."""
        product = saved_product(variants=[form("500g", 100, stock=4), form("1kg", 180, stock=9)])
        payload = product_payload(
            name=product["name"], slug=product["slug"], price=5.0, mrp=5.0, stock=500
        )

        response = admin_client.put(
            f"{base_url}/api/products/{product['product_id']}", json=payload
        )

        updated = response.json()
        assert updated["price"] == 100
        assert updated["stock"] == 13


def place_order(client, base_url, items):
    return client.post(
        f"{base_url}/api/orders",
        json={"items": items, "address": ADDRESS, "payment_method": "cod"},
    )


class TestRemovingAFormAnOrderHolds:
    """Cancelling an order returns its units to the form they came from.

    If that form has been deleted there is nothing to return them to and the
    stock is lost without a word, so the removal is refused while the order
    can still be cancelled.
    """

    def test_it_is_refused_while_the_order_is_open(
        self, base_url, admin_client, user_client, saved_product
    ):
        product = saved_product(variants=[form("500g", 100, stock=4), form("1kg", 180, stock=9)])
        small = labelled(product, "500g")
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
        assert placed.status_code == 200, placed.text

        payload = product_payload(
            name=product["name"],
            slug=product["slug"],
            variants=[labelled(product, "1kg")],
        )
        response = admin_client.put(
            f"{base_url}/api/products/{product['product_id']}", json=payload
        )

        assert response.status_code == 409
        assert response.json()["errors"][0]["field"] == "variants"

    def test_the_forms_are_left_as_they_were(
        self, base_url, admin_client, user_client, saved_product, mongo_db
    ):
        """A refused edit must not half-apply."""
        product = saved_product(variants=[form("500g", 100, stock=4), form("1kg", 180, stock=9)])
        small = labelled(product, "500g")
        place_order(
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

        admin_client.put(
            f"{base_url}/api/products/{product['product_id']}",
            json=product_payload(
                name="Renamed by a refused edit",
                slug=product["slug"],
                variants=[labelled(product, "1kg")],
            ),
        )

        stored = mongo_db.products.find_one({"product_id": product["product_id"]})
        assert len(stored["variants"]) == 2
        assert stored["name"] == product["name"]

    def test_editing_the_rest_is_still_allowed(
        self, base_url, admin_client, user_client, saved_product
    ):
        """The refusal is about removal alone, not about touching the product."""
        product = saved_product(variants=[form("500g", 100, stock=4), form("1kg", 180, stock=9)])
        small = labelled(product, "500g")
        place_order(
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

        response = admin_client.put(
            f"{base_url}/api/products/{product['product_id']}",
            json=product_payload(
                name=product["name"],
                slug=product["slug"],
                variants=[{**small, "price": 110.0, "mrp": 140.0}, labelled(product, "1kg")],
            ),
        )

        assert response.status_code == 200, response.text
        assert labelled(response.json(), "500g")["price"] == 110.0

    def test_it_is_allowed_once_the_order_is_cancelled(
        self, base_url, admin_client, user_client, saved_product
    ):
        product = saved_product(variants=[form("500g", 100, stock=4), form("1kg", 180, stock=9)])
        small = labelled(product, "500g")
        order_id = place_order(
            user_client,
            base_url,
            [
                {
                    "product_id": product["product_id"],
                    "variant_id": small["variant_id"],
                    "quantity": 2,
                }
            ],
        ).json()["order_id"]
        admin_client.put(f"{base_url}/api/admin/orders/{order_id}", json={"status": "cancelled"})

        response = admin_client.put(
            f"{base_url}/api/products/{product['product_id']}",
            json=product_payload(
                name=product["name"],
                slug=product["slug"],
                variants=[labelled(product, "1kg")],
            ),
        )

        assert response.status_code == 200, response.text
        assert len(response.json()["variants"]) == 1
