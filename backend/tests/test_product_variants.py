"""Products gaining the variant they are currently sold as.

Price and stock are moving from the product onto a variant of it. This first
step only adds the variant; nothing reads it yet, so the shop behaves exactly
as it did. What these tests hold is the invariant the later steps rely on:
every product has at least one variant, and the advertised price matches the
cheapest of them.
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
)
from scripts.add_product_variants import read_size  # noqa: E402


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
