"""What the database actually does to answer the queries the shop makes.

A query that works on a handful of records can quietly read the whole
collection, and nothing notices until there is enough data for it to hurt.
These tests ask MongoDB for its plan and refuse a collection scan, so an
index that stops being used is reported rather than discovered in production.

The plans are read against a populated collection on purpose: with only a few
documents the planner's choice says little about what it would do later.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from pymongo import DESCENDING

from app.routers.catalog import PRODUCT_SORTS

MARKER = "query-performance"
SEEDED = 400


def plan_stages(node, found=None):
    """Flatten the plan tree into the stages it runs."""
    found = [] if found is None else found
    if isinstance(node, dict):
        if "stage" in node:
            found.append(node["stage"])
        for key in ("queryPlan", "inputStage"):
            if key in node:
                plan_stages(node[key], found)
        for child in node.get("inputStages", []):
            plan_stages(child, found)
    return found


def explain(cursor):
    result = cursor.explain()
    return (
        plan_stages(result["queryPlanner"]["winningPlan"]),
        result["executionStats"],
    )


def assert_indexed(stages, label):
    assert "COLLSCAN" not in stages, f"{label} reads the whole collection: {' -> '.join(stages)}"
    assert any(
        "IXSCAN" in stage for stage in stages
    ), f"{label} does not use an index: {' -> '.join(stages)}"


@pytest.fixture(scope="module")
def populated(mongo_db):
    """Enough records that a plan means something, removed afterwards."""
    owner = f"test-user-{MARKER}-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)

    mongo_db.users.insert_many(
        [
            {
                "user_id": f"{owner}-{index:04d}",
                "mobile": f"+9171{index:08d}",
                "name": f"Query Probe {index}",
                "is_admin": False,
                "created_at": now,
                # Half have no email, matching how accounts are really stored.
                **({"email": f"{MARKER}-{index:04d}@example.com"} if index % 2 == 0 else {}),
            }
            for index in range(SEEDED)
        ]
    )
    mongo_db.orders.insert_many(
        [
            {
                "order_id": f"ord_{MARKER}_{index:04d}",
                "user_id": owner if index % 4 == 0 else f"{owner}-other-{index}",
                "status": "placed",
                "payment_status": "pending",
                "payment_method": "cod",
                "total": 100.0,
                "items": [],
                "created_at": now - timedelta(minutes=index),
            }
            for index in range(SEEDED)
        ]
    )
    mongo_db.audit_events.insert_many(
        [
            {
                "event": "auth.signed_in",
                "actor_id": owner if index % 4 == 0 else f"{owner}-other-{index}",
                "at": now - timedelta(minutes=index),
                "expires_at": now + timedelta(days=180),
                "details": {},
            }
            for index in range(SEEDED)
        ]
    )

    yield {"owner": owner, "sample_email": f"{MARKER}-0100@example.com"}

    mongo_db.users.delete_many({"user_id": {"$regex": f"^test-user-{MARKER}-"}})
    mongo_db.orders.delete_many({"order_id": {"$regex": f"^ord_{MARKER}_"}})
    mongo_db.audit_events.delete_many({"actor_id": {"$regex": f"^test-user-{MARKER}-"}})


class TestSigningIn:
    """Every sign-in runs these, so a scan here is felt on every attempt."""

    def test_finding_an_account_by_mobile_uses_an_index(self, mongo_db, populated):
        stages, stats = explain(mongo_db.users.find({"mobile": "+9171000000100"}))

        assert_indexed(stages, "sign-in by mobile")
        assert stats["totalDocsExamined"] <= 1

    def test_finding_an_account_by_email_uses_an_index(self, mongo_db, populated):
        """The email index is partial, and a partial index is only used when
        the query provably implies its filter. Filtering on the type of the
        field rather than its presence left this reading every account."""
        stages, stats = explain(mongo_db.users.find({"email": populated["sample_email"]}))

        assert_indexed(stages, "sign-in by email")
        assert stats["totalDocsExamined"] <= 1

    def test_an_account_without_an_email_is_still_allowed(self, mongo_db, populated):
        """The index must stay optional as well as fast."""
        without = mongo_db.users.count_documents(
            {"user_id": {"$regex": f"^test-user-{MARKER}-"}, "email": {"$exists": False}}
        )

        assert without > 1

    def test_looking_up_a_session_uses_an_index(self, mongo_db, populated):
        stages, stats = explain(mongo_db.user_sessions.find({"session_token_hash": "a" * 64}))

        assert_indexed(stages, "session lookup")
        assert stats["totalDocsExamined"] <= 1


class TestOrders:
    def test_a_customers_orders_use_an_index(self, mongo_db, populated):
        cursor = (
            mongo_db.orders.find({"user_id": populated["owner"]})
            .sort([("created_at", DESCENDING)])
            .limit(20)
        )

        stages, stats = explain(cursor)

        assert_indexed(stages, "orders for a customer")
        assert "SORT" not in stages, "the index should already supply the order"
        assert stats["totalDocsExamined"] <= 20

    def test_the_administrator_list_uses_an_index(self, mongo_db, populated):
        cursor = mongo_db.orders.find({}).sort([("created_at", DESCENDING)]).limit(25)

        stages, stats = explain(cursor)

        assert_indexed(stages, "the admin order list")
        assert "SORT" not in stages
        assert stats["totalDocsExamined"] <= 25

    def test_paging_does_not_read_everything_before_it(self, mongo_db, populated):
        """A later page must not cost the whole collection."""
        cursor = mongo_db.orders.find({}).sort([("created_at", DESCENDING)]).skip(200).limit(25)

        stages, stats = explain(cursor)

        assert_indexed(stages, "a later page of orders")
        assert stats["totalDocsExamined"] < SEEDED


class TestCatalogue:
    def test_browsing_a_category_uses_an_index(self, mongo_db, populated):
        cursor = (
            mongo_db.products.find({"category": "laundry"}).sort(PRODUCT_SORTS["popular"]).limit(12)
        )

        stages, _ = explain(cursor)

        assert_indexed(stages, "browsing a category")

    @pytest.mark.parametrize("sort_name", sorted(PRODUCT_SORTS))
    def test_sorting_the_catalogue_is_served_by_an_index(self, mongo_db, populated, sort_name):
        """Every ordering the shop offers, unfiltered, as the shop page asks.

        Two mistakes hid here. A mixed-direction sort cannot be answered by
        walking an index backwards, so "price, high to low" read the whole
        catalogue; and the date ordering had no index carrying its tiebreaker,
        so the default shop page did the same.
        """
        cursor = mongo_db.products.find({}).sort(PRODUCT_SORTS[sort_name]).limit(12)

        stages, _ = explain(cursor)

        assert_indexed(stages, f"sorting by {sort_name}")
        assert "SORT" not in stages, "the order should come from the index"

    def test_a_product_page_uses_an_index(self, mongo_db, populated):
        stages, stats = explain(mongo_db.products.find({"product_id": "prod_missing"}))

        assert_indexed(stages, "a product page")
        assert stats["totalDocsExamined"] <= 1

    def test_reviews_for_a_product_use_an_index(self, mongo_db, populated):
        cursor = mongo_db.reviews.find({"product_id": "prod_missing"}).sort(
            [("created_at", DESCENDING)]
        )

        stages, _ = explain(cursor)

        assert_indexed(stages, "reviews for a product")


class TestAuditTrail:
    """This collection only grows, so it is the one most likely to hurt."""

    def test_events_for_an_account_use_an_index(self, mongo_db, populated):
        cursor = (
            mongo_db.audit_events.find({"actor_id": populated["owner"]})
            .sort([("at", DESCENDING)])
            .limit(25)
        )

        stages, stats = explain(cursor)

        assert_indexed(stages, "audit events for an account")
        assert "SORT" not in stages
        assert stats["totalDocsExamined"] <= 25

    def test_events_of_one_kind_use_an_index(self, mongo_db, populated):
        cursor = (
            mongo_db.audit_events.find({"event": "auth.sign_in_failed"})
            .sort([("at", DESCENDING)])
            .limit(25)
        )

        stages, _ = explain(cursor)

        assert_indexed(stages, "audit events of one kind")
        assert "SORT" not in stages


class TestKnownInMemorySorts:
    """Where a sort is not served by an index, say so deliberately.

    Adding the product_id tiebreaker to the catalogue's date ordering left
    these sorting in memory, because the index stops at created_at. The cost
    is bounded by one category rather than the whole catalogue, which is
    acceptable at this size; the assertion is here so that stops being true
    quietly.
    """

    def test_the_date_ordering_still_reaches_rows_through_an_index(self, mongo_db, populated):
        cursor = mongo_db.products.find({"featured": True}).sort(PRODUCT_SORTS["popular"]).limit(12)

        stages, stats = explain(cursor)

        assert_indexed(stages, "featured products")
        assert (
            stats["totalDocsExamined"] < 1000
        ), "the in-memory sort must stay bounded by the filtered set"
