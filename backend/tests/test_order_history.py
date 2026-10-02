"""When an order reached each state.

An order recorded only when it was placed. Nothing recorded when it shipped
or arrived, so "when was this delivered?" had no answer -- not for a customer
reading their order, and not for the shop answering a claim that a parcel
never came.

What matters here is that the history is a record of the parcel, not of
administrative clicks: a real change is recorded once, and re-saving an order
that has not moved adds nothing.
"""

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

ADDRESS = {
    "full_name": "History Tester",
    "phone": "9999900009",
    "line1": "12 Market Road",
    "line2": "",
    "city": "Mumbai",
    "state": "MH",
    "pincode": "400001",
}


@pytest.fixture
def an_order(base_url, user_client):
    products = user_client.get(f"{base_url}/api/products").json()
    items = [{"product_id": products[0]["product_id"], "quantity": 1}]
    placed = user_client.post(
        f"{base_url}/api/orders",
        json={"items": items, "address": ADDRESS, "payment_method": "cod"},
    )
    assert placed.status_code == 200, placed.text
    return placed.json()


def history_of(client, base_url, order_id):
    order = client.get(f"{base_url}/api/orders/{order_id}").json()
    return [(event["status"], event["at"]) for event in order.get("history", [])]


def advance(admin_client, base_url, order_id, status):
    return admin_client.put(
        f"{base_url}/api/admin/orders/{order_id}",
        json={"status": status},
    )


class TestAnOrderRemembersWhenItMoved:
    def test_placing_an_order_records_the_moment(self, an_order):
        assert [event["status"] for event in an_order["history"]] == ["placed"]
        assert an_order["history"][0]["at"] == an_order["created_at"]

    def test_each_step_is_added_in_the_order_it_happened(
        self, base_url, user_client, admin_client, an_order
    ):
        for status in ("processing", "shipped", "delivered"):
            assert advance(admin_client, base_url, an_order["order_id"], status).status_code == 200

        steps = [status for status, _ in history_of(user_client, base_url, an_order["order_id"])]
        assert steps == ["placed", "processing", "shipped", "delivered"]

    def test_the_delivery_time_is_the_one_recorded_for_delivery(
        self, base_url, user_client, admin_client, an_order
    ):
        """The point of the history: a date to put beside "Delivered"."""
        for status in ("processing", "shipped", "delivered"):
            advance(admin_client, base_url, an_order["order_id"], status)

        events = dict(history_of(user_client, base_url, an_order["order_id"]))
        assert events["delivered"] > events["shipped"] > events["placed"]

    def test_saving_an_order_that_has_not_moved_records_nothing(
        self, base_url, user_client, admin_client, an_order
    ):
        """Otherwise the history becomes a log of clicks, not of the parcel."""
        advance(admin_client, base_url, an_order["order_id"], "shipped")
        before = history_of(user_client, base_url, an_order["order_id"])

        advance(admin_client, base_url, an_order["order_id"], "shipped")
        advance(admin_client, base_url, an_order["order_id"], "shipped")

        assert history_of(user_client, base_url, an_order["order_id"]) == before

    def test_changing_only_the_payment_adds_no_delivery_step(
        self, base_url, user_client, admin_client, an_order
    ):
        admin_client.put(
            f"{base_url}/api/admin/orders/{an_order['order_id']}",
            json={"payment_status": "paid"},
        )
        steps = [status for status, _ in history_of(user_client, base_url, an_order["order_id"])]
        assert steps == ["placed"]

    def test_cancelling_is_recorded_too(self, base_url, user_client, admin_client, an_order):
        advance(admin_client, base_url, an_order["order_id"], "cancelled")
        steps = [status for status, _ in history_of(user_client, base_url, an_order["order_id"])]
        assert steps == ["placed", "cancelled"]

    def test_a_refused_change_is_not_recorded(self, base_url, user_client, admin_client, an_order):
        """An order that cannot go backwards must not look as though it did."""
        for status in ("shipped", "delivered"):
            advance(admin_client, base_url, an_order["order_id"], status)
        before = history_of(user_client, base_url, an_order["order_id"])
        assert [status for status, _ in before] == ["placed", "shipped", "delivered"]

        refused = advance(admin_client, base_url, an_order["order_id"], "placed")

        assert refused.status_code == 409
        assert history_of(user_client, base_url, an_order["order_id"]) == before
