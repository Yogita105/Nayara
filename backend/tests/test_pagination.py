"""Paging parameters and index definitions."""
import pytest

from app.database import INDEXES
from app.pagination import MAX_PAGE_SIZE


class TestIndexDefinitions:
    def test_every_query_field_is_indexed(self):
        indexed = {
            (collection, tuple(field for field, _ in keys))
            for collection, keys, _ in INDEXES
        }
        expected = {
            ("users", ("email",)),
            ("users", ("mobile",)),
            ("user_sessions", ("session_token_hash",)),
            ("user_sessions", ("expires_at",)),
            ("rate_limits", ("expires_at",)),
            ("products", ("product_id",)),
            ("products", ("slug",)),
            ("products", ("category", "created_at")),
            ("products", ("featured", "created_at")),
            ("products", ("created_at", "product_id")),
            ("products", ("price", "product_id")),
            ("products", ("rating", "product_id")),
            ("orders", ("order_id",)),
            ("orders", ("user_id", "created_at")),
            ("reviews", ("product_id", "created_at")),
            ("contacts", ("created_at",)),
            ("bulk_inquiries", ("created_at",)),
            ("carts", ("user_id",)),
            ("wishlists", ("user_id",)),
        }
        assert expected <= indexed

    def test_expiring_collections_use_a_ttl_index(self):
        ttl = {
            collection
            for collection, _, options in INDEXES
            if "expireAfterSeconds" in options
        }
        assert ttl == {
            "user_sessions",
            "rate_limits",
            "order_claims",
            "audit_events",
        }

    def test_session_and_account_keys_stay_unique(self):
        unique = {
            (collection, keys[0][0])
            for collection, keys, options in INDEXES
            if options.get("unique")
        }
        assert ("users", "email") in unique
        assert ("products", "slug") in unique
        assert ("orders", "order_id") in unique


class TestProductPaging:
    def test_limit_restricts_the_page_size(self, base_url, anon_client):
        page = anon_client.get(f"{base_url}/api/products?limit=2").json()
        assert len(page) <= 2

    def test_offset_moves_through_the_catalogue(self, base_url, anon_client):
        everything = anon_client.get(f"{base_url}/api/products").json()
        if len(everything) < 2:
            pytest.skip("needs at least two products")

        first = anon_client.get(f"{base_url}/api/products?limit=1").json()
        second = anon_client.get(f"{base_url}/api/products?limit=1&offset=1").json()

        assert first[0]["product_id"] == everything[0]["product_id"]
        assert second[0]["product_id"] == everything[1]["product_id"]
        assert first[0]["product_id"] != second[0]["product_id"]

    def test_paging_covers_every_product_exactly_once(self, base_url, anon_client):
        everything = anon_client.get(f"{base_url}/api/products").json()

        collected = []
        for offset in range(0, len(everything), 2):
            collected += anon_client.get(
                f"{base_url}/api/products?limit=2&offset={offset}"
            ).json()

        assert [p["product_id"] for p in collected] == [
            p["product_id"] for p in everything
        ]

    def test_offset_past_the_end_returns_nothing(self, base_url, anon_client):
        assert anon_client.get(f"{base_url}/api/products?offset=100000").json() == []

    @pytest.mark.parametrize("limit", [0, -1, MAX_PAGE_SIZE + 1])
    def test_invalid_limits_are_rejected(self, base_url, anon_client, limit):
        response = anon_client.get(f"{base_url}/api/products?limit={limit}")
        assert response.status_code == 422

    def test_negative_offset_is_rejected(self, base_url, anon_client):
        assert anon_client.get(f"{base_url}/api/products?offset=-1").status_code == 422

    def test_filters_still_apply_with_paging(self, base_url, anon_client):
        page = anon_client.get(
            f"{base_url}/api/products?category=laundry&limit=1"
        ).json()
        assert len(page) <= 1
        assert all(item["category"] == "laundry" for item in page)


class TestProductSorting:
    """Sorting must be applied by the API, or a page would only be ordered
    within itself and the cheapest product could sit on the last page."""

    @pytest.mark.parametrize(
        "sort,key,reverse",
        [
            ("price_asc", "price", False),
            ("price_desc", "price", True),
            ("rating", "rating", True),
        ],
    )
    def test_results_come_back_in_the_requested_order(
        self, base_url, anon_client, sort, key, reverse
    ):
        items = anon_client.get(f"{base_url}/api/products?sort={sort}").json()
        values = [item[key] for item in items]
        assert values == sorted(values, reverse=reverse)

    def test_an_unknown_sort_is_rejected(self, base_url, anon_client):
        response = anon_client.get(f"{base_url}/api/products?sort=cheapest")
        assert response.status_code == 422

    @pytest.mark.parametrize(
        "sort", ["popular", "newest", "price_asc", "price_desc", "rating"]
    )
    def test_sorted_paging_covers_every_product_exactly_once(
        self, base_url, anon_client, sort
    ):
        """Every ordering, because each carries its own tiebreaker direction."""
        everything = anon_client.get(f"{base_url}/api/products?sort={sort}").json()

        collected = []
        for offset in range(0, len(everything), 2):
            collected += anon_client.get(
                f"{base_url}/api/products?sort={sort}&limit=2&offset={offset}"
            ).json()

        ids = [item["product_id"] for item in collected]
        assert ids == [item["product_id"] for item in everything]
        assert len(ids) == len(set(ids)), "a product appeared on two pages"

    def test_max_price_excludes_dearer_products(self, base_url, anon_client):
        everything = anon_client.get(f"{base_url}/api/products").json()
        if not everything:
            pytest.skip("needs a catalogue")
        cheapest = min(item["price"] for item in everything)

        items = anon_client.get(
            f"{base_url}/api/products?max_price={cheapest}"
        ).json()

        assert items, "the cheapest product should still be included"
        assert all(item["price"] <= cheapest for item in items)

    def test_a_negative_max_price_is_rejected(self, base_url, anon_client):
        response = anon_client.get(f"{base_url}/api/products?max_price=-1")
        assert response.status_code == 422

    def test_the_total_counts_matches_not_the_page(self, base_url, anon_client):
        response = anon_client.get(f"{base_url}/api/products?limit=1")
        total = int(response.headers["X-Total-Count"])
        everything = anon_client.get(f"{base_url}/api/products").json()

        assert len(response.json()) <= 1
        assert total == len(everything)

    def test_the_total_reflects_the_filter(self, base_url, anon_client):
        response = anon_client.get(f"{base_url}/api/products?category=laundry")
        assert int(response.headers["X-Total-Count"]) == len(response.json())


class TestOrderPaging:
    def test_orders_accept_paging_parameters(self, base_url, user_client):
        response = user_client.get(f"{base_url}/api/orders?limit=1&offset=0")
        assert response.status_code == 200
        assert len(response.json()) <= 1


class TestAdminPaging:
    def test_admin_lists_report_the_total(self, base_url, admin_client):
        response = admin_client.get(f"{base_url}/api/admin/users?limit=1")
        assert response.status_code == 200
        assert len(response.json()) <= 1
        assert int(response.headers["X-Total-Count"]) >= 1

    def test_total_is_independent_of_the_page(self, base_url, admin_client):
        first = admin_client.get(f"{base_url}/api/admin/users?limit=1")
        second = admin_client.get(f"{base_url}/api/admin/users?limit=1&offset=1")
        assert first.headers["X-Total-Count"] == second.headers["X-Total-Count"]


class TestSearchEscaping:
    def test_regex_characters_are_treated_as_text(self, base_url, anon_client):
        response = anon_client.get(f"{base_url}/api/products?q=%28%5B")
        assert response.status_code == 200
        assert response.json() == []
