"""The customer's address book.

An address saved here is a convenience for filling in checkout, nothing more.
The record of where a parcel actually went lives on the order, so what matters
most in this file is that editing or deleting a saved address cannot reach
back and rewrite a past delivery.

The other thing worth holding firm is that exactly one address is the usual
one. With none, checkout has nothing to pre-select; with two, it guesses. A
customer could neither diagnose nor repair either state.
"""

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.models import MAX_ADDRESSES  # noqa: E402

ADDRESSES = "/api/addresses"


def an_address(**overrides):
    return {
        "full_name": "Address Tester",
        "phone": "9999900009",
        "line1": "12 Market Road",
        "line2": "",
        "city": "Mumbai",
        "state": "MH",
        "pincode": "400001",
        **overrides,
    }


@pytest.fixture
def one_product(base_url, user_client):
    """Something orderable, so an order can be placed to compare against."""
    products = user_client.get(f"{base_url}/api/products").json()
    return [{"product_id": products[0]["product_id"], "quantity": 1}]


@pytest.fixture
def book(base_url, user_client, user_session, mongo_db):
    """An empty address book, emptied again afterwards.

    Cleanup belongs here rather than at the end of each test, because a test
    that fails never reaches its own tidying up.
    """
    owner = {"user_id": user_session["user_id"]}
    mongo_db.addresses.delete_many(owner)

    class Book:
        def list(self):
            return user_client.get(f"{base_url}{ADDRESSES}")

        def add(self, **overrides):
            return user_client.post(f"{base_url}{ADDRESSES}", json=an_address(**overrides))

        def added(self, **overrides):
            """Add one and hand back the address itself.

            The endpoint answers with the whole book, so the new entry has to
            be identified rather than assumed to be first or last.
            """
            before = set(self.ids())
            response = self.add(**overrides)
            assert response.status_code == 200, response.text
            fresh = [a for a in response.json()["items"] if a["address_id"] not in before]
            assert len(fresh) == 1
            return fresh[0]

        def edit(self, address_id, **overrides):
            return user_client.put(
                f"{base_url}{ADDRESSES}/{address_id}", json=an_address(**overrides)
            )

        def remove(self, address_id):
            return user_client.delete(f"{base_url}{ADDRESSES}/{address_id}")

        def ids(self):
            return [a["address_id"] for a in self.list().json()["items"]]

        def default_id(self):
            marked = [a for a in self.list().json()["items"] if a["is_default"]]
            return marked[0]["address_id"] if len(marked) == 1 else None

    yield Book()
    mongo_db.addresses.delete_many(owner)


class TestKeepingAddresses:
    def test_a_new_customer_has_an_empty_book(self, book):
        assert book.list().json()["items"] == []

    def test_an_address_is_there_on_the_next_visit(self, book):
        book.add(label="Home")
        saved = book.list().json()["items"]
        assert len(saved) == 1
        assert saved[0]["label"] == "Home"
        assert saved[0]["line1"] == "12 Market Road"
        assert saved[0]["address_id"].startswith("addr_")

    def test_editing_changes_only_the_one_addressed(self, book):
        first = book.added(label="Home")["address_id"]
        book.add(label="Office", line1="5 Mill Lane")

        book.edit(first, label="Home", line1="99 New Road")

        by_label = {a["label"]: a for a in book.list().json()["items"]}
        assert by_label["Home"]["line1"] == "99 New Road"
        assert by_label["Office"]["line1"] == "5 Mill Lane"

    def test_a_deleted_address_is_gone(self, book):
        gone = book.added(label="Home")["address_id"]
        book.add(label="Office")

        book.remove(gone)

        assert gone not in book.ids()

    @pytest.mark.parametrize("call", ["edit", "remove"])
    def test_an_address_that_was_never_saved_is_refused_in_words(self, book, call):
        response = getattr(book, call)("addr_nosuchthing")
        assert response.status_code == 404
        assert "no longer saved" in response.text

    def test_the_book_does_not_grow_without_limit(self, book):
        for n in range(MAX_ADDRESSES):
            assert book.add(label=f"Place {n}").status_code == 200

        refused = book.add(label="One too many")
        assert refused.status_code == 409
        assert str(MAX_ADDRESSES) in refused.text
        assert len(book.ids()) == MAX_ADDRESSES


class TestTheUsualAddress:
    """Exactly one address is the default, whatever route the book took."""

    def test_the_first_address_saved_becomes_the_usual_one(self, book):
        saved = book.added(label="Home")
        assert saved["is_default"] is True

    def test_a_second_address_does_not_take_over_by_itself(self, book):
        home = book.added(label="Home")["address_id"]
        book.add(label="Office")
        assert book.default_id() == home

    def test_choosing_a_new_usual_address_unseats_the_old_one(self, book):
        book.add(label="Home")
        office = book.added(label="Office")["address_id"]

        book.edit(office, label="Office", is_default=True)

        assert book.default_id() == office

    def test_adding_one_as_the_usual_address_unseats_the_old_one(self, book):
        book.add(label="Home")
        office = book.added(label="Office", is_default=True)["address_id"]
        assert book.default_id() == office

    def test_deleting_the_usual_address_promotes_another(self, book):
        home = book.added(label="Home")["address_id"]
        book.add(label="Office")

        book.remove(home)

        assert book.default_id() is not None

    def test_the_last_address_cannot_be_left_unchosen(self, book):
        only = book.added(label="Home")["address_id"]
        book.edit(only, label="Home", is_default=False)
        assert book.default_id() == only


class TestAddressesAreValidated:
    """The book holds addresses a courier could deliver to."""

    def test_a_bad_pincode_is_refused_in_a_sentence(self, book):
        response = book.add(pincode="12")
        assert response.status_code == 422
        assert "6-digit PIN code" in response.text
        assert "pattern" not in response.text

    def test_a_label_longer_than_a_label_is_refused(self, book):
        assert book.add(label="x" * 31).status_code == 422


class TestOrdersKeepTheirOwnAddress:
    def test_editing_a_saved_address_does_not_move_a_past_delivery(
        self, base_url, user_client, book, one_product
    ):
        saved = book.added(label="Home")
        placed = user_client.post(
            f"{base_url}/api/orders",
            json={
                "items": one_product,
                "address": an_address(),
                "payment_method": "cod",
            },
        )
        assert placed.status_code == 200, placed.text
        order_id = placed.json()["order_id"]

        book.edit(saved["address_id"], label="Home", line1="Somewhere else entirely")

        delivered_to = user_client.get(f"{base_url}/api/orders/{order_id}").json()["address"]
        assert delivered_to["line1"] == "12 Market Road"

    def test_deleting_a_saved_address_does_not_erase_a_past_delivery(
        self, base_url, user_client, book, one_product
    ):
        saved = book.added(label="Home")
        order_id = user_client.post(
            f"{base_url}/api/orders",
            json={
                "items": one_product,
                "address": an_address(),
                "payment_method": "cod",
            },
        ).json()["order_id"]

        book.remove(saved["address_id"])

        order = user_client.get(f"{base_url}/api/orders/{order_id}").json()
        assert order["address"]["line1"] == "12 Market Road"


class TestAnAddressBookIsPrivate:
    def test_one_customer_cannot_read_another_book(self, base_url, book, admin_client, user_client):
        book.add(label="Home")
        mine = user_client.get(f"{base_url}{ADDRESSES}").json()["items"]
        theirs = admin_client.get(f"{base_url}{ADDRESSES}").json()["items"]
        assert len(mine) == 1
        assert theirs == []

    def test_one_customer_cannot_delete_another_address(self, base_url, book, admin_client):
        mine = book.added(label="Home")["address_id"]

        response = admin_client.delete(f"{base_url}{ADDRESSES}/{mine}")

        assert response.status_code == 404
        assert mine in book.ids()
