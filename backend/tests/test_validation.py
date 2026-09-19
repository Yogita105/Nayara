"""Request-model validation rules."""
import pytest
from pydantic import ValidationError

from app.models import (
    MAX_CART_QUANTITY,
    Address,
    AddToCartRequest,
    BulkInquiryUpdate,
    ContactRequest,
    OrderCreate,
    OrderUpdate,
    ProductCreate,
    ReviewCreate,
    UpdateCartRequest,
)


VALID_PRODUCT = {
    "name": "Nayara Test Soap",
    "slug": "nayara-test-soap",
    "category": "laundry",
    "price": 45.0,
    "mrp": 60.0,
}
VALID_ADDRESS = {
    "full_name": "Test Buyer",
    "phone": "9999999999",
    "line1": "12 Market Road",
    "city": "Mumbai",
    "state": "MH",
    "pincode": "400001",
}


class TestProductValidation:
    def test_valid_product_is_accepted(self):
        product = ProductCreate(**VALID_PRODUCT)
        assert product.price == 45.0
        assert product.category == "laundry"

    @pytest.mark.parametrize("price", [0, -1])
    def test_price_must_be_positive(self, price):
        with pytest.raises(ValidationError):
            ProductCreate(**{**VALID_PRODUCT, "price": price})

    def test_stock_cannot_be_negative(self):
        with pytest.raises(ValidationError):
            ProductCreate(**{**VALID_PRODUCT, "stock": -1})

    def test_mrp_cannot_be_below_price(self):
        with pytest.raises(ValidationError):
            ProductCreate(**{**VALID_PRODUCT, "price": 90.0, "mrp": 60.0})

    def test_unknown_category_is_rejected(self):
        with pytest.raises(ValidationError):
            ProductCreate(**{**VALID_PRODUCT, "category": "electronics"})

    @pytest.mark.parametrize("slug", ["Not A Slug", "trailing-", "has_underscore"])
    def test_slug_format_is_enforced(self, slug):
        with pytest.raises(ValidationError):
            ProductCreate(**{**VALID_PRODUCT, "slug": slug})


class TestCartValidation:
    def test_quantity_must_be_at_least_one(self):
        with pytest.raises(ValidationError):
            AddToCartRequest(product_id="prod_1", quantity=0)

    def test_quantity_is_capped(self):
        with pytest.raises(ValidationError):
            AddToCartRequest(product_id="prod_1", quantity=MAX_CART_QUANTITY + 1)

    def test_update_allows_zero_to_remove_a_line(self):
        assert UpdateCartRequest(quantity=0).quantity == 0

    def test_update_rejects_negative_quantity(self):
        with pytest.raises(ValidationError):
            UpdateCartRequest(quantity=-1)


class TestReviewValidation:
    @pytest.mark.parametrize("rating", [1, 5])
    def test_ratings_in_range_are_accepted(self, rating):
        assert ReviewCreate(rating=rating, title="Good", comment="Nice").rating == rating

    @pytest.mark.parametrize("rating", [0, 6, -2])
    def test_ratings_out_of_range_are_rejected(self, rating):
        with pytest.raises(ValidationError):
            ReviewCreate(rating=rating, title="Good", comment="Nice")

    def test_blank_comment_is_rejected(self):
        with pytest.raises(ValidationError):
            ReviewCreate(rating=4, title="Good", comment="   ")


class TestAddressValidation:
    def test_valid_address_normalises_the_phone(self):
        assert Address(**VALID_ADDRESS).phone == "+919999999999"

    @pytest.mark.parametrize("pincode", ["0400011", "40001", "abcdef", "012345"])
    def test_invalid_pincodes_are_rejected(self, pincode):
        with pytest.raises(ValidationError):
            Address(**{**VALID_ADDRESS, "pincode": pincode})

    @pytest.mark.parametrize("phone", ["12345", "1234567890", "not-a-phone"])
    def test_invalid_delivery_phones_are_rejected(self, phone):
        with pytest.raises(ValidationError):
            Address(**{**VALID_ADDRESS, "phone": phone})


class TestOrderValidation:
    def test_valid_order_is_accepted(self):
        order = OrderCreate(
            items=[{"product_id": "prod_1", "quantity": 2}],
            address=VALID_ADDRESS,
            payment_method="cod",
        )
        assert order.payment_method == "cod"

    def test_unknown_payment_method_is_rejected(self):
        with pytest.raises(ValidationError):
            OrderCreate(
                items=[{"product_id": "prod_1", "quantity": 1}],
                address=VALID_ADDRESS,
                payment_method="crypto",
            )

    def test_order_requires_at_least_one_item(self):
        with pytest.raises(ValidationError):
            OrderCreate(items=[], address=VALID_ADDRESS, payment_method="cod")


class TestAdminUpdateValidation:
    def test_known_order_status_is_accepted(self):
        assert OrderUpdate(status="shipped").status == "shipped"

    def test_unknown_order_status_is_rejected(self):
        with pytest.raises(ValidationError):
            OrderUpdate(status="teleported")

    def test_empty_order_update_is_rejected(self):
        with pytest.raises(ValidationError):
            OrderUpdate()

    def test_order_update_ignores_unlisted_fields(self):
        update = OrderUpdate(status="shipped", total=0)
        assert update.model_dump(exclude_none=True) == {"status": "shipped"}

    def test_unknown_inquiry_status_is_rejected(self):
        with pytest.raises(ValidationError):
            BulkInquiryUpdate(status="maybe")


class TestContactValidation:
    def test_invalid_email_is_rejected(self):
        with pytest.raises(ValidationError):
            ContactRequest(
                name="Test Buyer",
                email="not-an-email",
                subject="Hi",
                message="Hello",
            )

    def test_overlong_message_is_rejected(self):
        with pytest.raises(ValidationError):
            ContactRequest(
                name="Test Buyer",
                email="buyer@example.com",
                subject="Hi",
                message="x" * 2001,
            )
