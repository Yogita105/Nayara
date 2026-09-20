import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from .utils import normalize_indian_mobile

MAX_CART_QUANTITY = 50
MAX_ORDER_ITEMS = 50
MAX_VARIANTS = 20
SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
PINCODE_PATTERN = r"^[1-9][0-9]{5}$"
BUSINESS_PHONE_PATTERN = r"^\+?[0-9][0-9\s-]{7,19}$"


class ContentModel(BaseModel):
    """Base for models holding user-supplied content.

    Surrounding whitespace is removed so length rules cannot be satisfied with
    blank characters. Credential models deliberately do not inherit this,
    because trimming a password would change what the user typed.
    """

    model_config = ConfigDict(str_strip_whitespace=True, use_enum_values=True)


class ProductCategory(str, Enum):
    LAUNDRY = "laundry"
    PERSONAL_CARE = "personal-care"
    HOME_CARE = "home-care"


class PaymentMethod(str, Enum):
    CARD = "card"
    UPI = "upi"
    COD = "cod"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    COD_PENDING = "cod_pending"


class OrderStatus(str, Enum):
    PLACED = "placed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class BulkInquiryStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUOTED = "quoted"
    WON = "won"
    LOST = "lost"


# Which status an order may move to next. Delivered and cancelled are final:
# reopening a cancelled order would leave it active after its stock had
# already been returned to the catalogue, overstating what is in hand.
ORDER_STATUS_TRANSITIONS = {
    OrderStatus.PLACED.value: {
        OrderStatus.PROCESSING.value,
        OrderStatus.SHIPPED.value,
        OrderStatus.CANCELLED.value,
    },
    OrderStatus.PROCESSING.value: {
        OrderStatus.SHIPPED.value,
        OrderStatus.CANCELLED.value,
    },
    OrderStatus.SHIPPED.value: {
        OrderStatus.DELIVERED.value,
        OrderStatus.CANCELLED.value,
    },
    OrderStatus.DELIVERED.value: set(),
    OrderStatus.CANCELLED.value: set(),
}


def allowed_next_statuses(current: str) -> set:
    return ORDER_STATUS_TRANSITIONS.get(current, set())


def can_change_status(current: str, requested: str) -> bool:
    """Repeating the current status is accepted so a retry is harmless."""
    if current == requested:
        return True
    return requested in allowed_next_statuses(current)


class User(BaseModel):
    user_id: str
    mobile: str
    email: Optional[str] = None
    name: str
    picture: Optional[str] = ""
    is_admin: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    mobile: str = Field(min_length=10, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    # Optional because many Indian customers have an address they never read,
    # so demanding one costs sign-ups without giving a usable contact.
    email: Optional[EmailStr] = None


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class ProfileUpdateRequest(ContentModel):
    name: str = Field(min_length=2, max_length=100)
    # The mobile number is the account's identifier and is not changed here.
    email: Optional[EmailStr] = None


class ProductVariant(ContentModel):
    """One buyable form of a product: a weight, a volume, or a colour.

    Price and stock belong here rather than on the product, because a kilo
    and a half-kilo are sold at different prices and run out independently.

    An image is optional and falls back to the product's. Colours need their
    own photograph, since that is the whole point of choosing one; weights
    generally look alike and can share.
    """

    variant_id: str = Field(default_factory=lambda: f"var_{uuid.uuid4().hex[:10]}")
    label: str = Field(min_length=1, max_length=60)
    price: float = Field(gt=0, le=10_000_000)
    mrp: float = Field(gt=0, le=10_000_000)
    stock: int = Field(default=0, ge=0, le=1_000_000)
    image: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def check_mrp_covers_price(self) -> "ProductVariant":
        if self.mrp < self.price:
            raise ValueError("MRP must be greater than or equal to the price")
        return self


class ProductCreate(ContentModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str = Field(min_length=2, max_length=200, pattern=SLUG_PATTERN)
    category: ProductCategory
    description: str = Field(default="", max_length=5000)
    short_description: str = Field(default="", max_length=500)
    price: float = Field(gt=0, le=10_000_000)
    mrp: float = Field(gt=0, le=10_000_000)
    image: str = Field(default="", max_length=2000)
    images: List[str] = Field(default_factory=list, max_length=10)
    stock: int = Field(default=100, ge=0, le=1_000_000)
    badges: List[str] = Field(default_factory=list, max_length=10)
    featured: bool = False

    @model_validator(mode="after")
    def check_mrp_covers_price(self) -> "ProductCreate":
        if self.mrp < self.price:
            raise ValueError("MRP must be greater than or equal to the price")
        return self


class Product(ProductCreate):
    product_id: str = Field(default_factory=lambda: f"prod_{uuid.uuid4().hex[:10]}")
    rating: float = Field(default=4.5, ge=0, le=5)
    reviews_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # What the variants of this product differ by: "Weight", "Volume",
    # "Colour". One axis per product, so a kilo bag of powder is not also
    # asked to be a colour.
    option_name: str = Field(default="Size", min_length=1, max_length=40)
    variants: List[ProductVariant] = Field(default_factory=list, max_length=MAX_VARIANTS)
    # The cheapest variant, held here so the catalogue can be sorted and
    # filtered by price with a plain indexed field. Recalculated whenever the
    # variants change; never edited directly.
    price_from: float = Field(default=0, ge=0, le=10_000_000)


def cheapest_price(variants: List[dict], fallback: float = 0) -> float:
    """The price a product is advertised from."""
    prices = [
        variant["price"]
        for variant in variants
        if isinstance(variant, dict) and isinstance(variant.get("price"), (int, float))
    ]
    return min(prices) if prices else fallback


def default_variant(product: dict) -> dict:
    """The single variant a product without any should stand in with.

    Every product carries at least one variant, so that nothing downstream
    has to handle both a product that has them and one that does not.
    """
    return ProductVariant(
        label=product.get("variant_label") or "Standard",
        price=product.get("price", 0),
        mrp=product.get("mrp") or product.get("price", 0),
        stock=product.get("stock", 0),
    ).model_dump()


class CartItem(ContentModel):
    product_id: str = Field(min_length=1, max_length=100)
    # Older clients do not send one. A product with a single variant resolves
    # to it; one with a real choice insists on being told which.
    variant_id: Optional[str] = Field(default=None, max_length=100)
    quantity: int = Field(ge=1, le=MAX_CART_QUANTITY)


class AddToCartRequest(ContentModel):
    product_id: str = Field(min_length=1, max_length=100)
    variant_id: Optional[str] = Field(default=None, max_length=100)
    quantity: int = Field(default=1, ge=1, le=MAX_CART_QUANTITY)


class UpdateCartRequest(ContentModel):
    variant_id: Optional[str] = Field(default=None, max_length=100)
    # Zero is allowed because it removes the line from the cart.
    quantity: int = Field(ge=0, le=MAX_CART_QUANTITY)


class WishlistRequest(ContentModel):
    product_id: str = Field(min_length=1, max_length=100)


class ReviewCreate(ContentModel):
    rating: int = Field(ge=1, le=5)
    title: str = Field(min_length=1, max_length=150)
    comment: str = Field(min_length=1, max_length=2000)


class Review(ReviewCreate):
    review_id: str = Field(default_factory=lambda: f"rev_{uuid.uuid4().hex[:10]}")
    product_id: str
    user_id: str
    user_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ContactRequest(ContentModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(default="", max_length=20)
    subject: str = Field(min_length=1, max_length=150)
    message: str = Field(min_length=1, max_length=2000)


class BulkInquiryRequest(ContentModel):
    name: str = Field(min_length=2, max_length=100)
    business_name: str = Field(min_length=2, max_length=150)
    phone: str = Field(min_length=8, max_length=20, pattern=BUSINESS_PHONE_PATTERN)
    email: EmailStr
    city: str = Field(min_length=2, max_length=100)
    products_interested: List[str] = Field(default_factory=list, max_length=20)
    quantity: str = Field(min_length=1, max_length=100)
    message: Optional[str] = Field(default="", max_length=2000)


class BulkInquiryUpdate(ContentModel):
    status: BulkInquiryStatus


class OrderUpdate(ContentModel):
    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None

    @model_validator(mode="after")
    def require_one_field(self) -> "OrderUpdate":
        if self.status is None and self.payment_status is None:
            raise ValueError("Provide status or payment_status")
        return self


class Address(ContentModel):
    full_name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=10, max_length=20)
    line1: str = Field(min_length=3, max_length=200)
    line2: Optional[str] = Field(default="", max_length=200)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    pincode: str = Field(pattern=PINCODE_PATTERN)

    @field_validator("phone")
    @classmethod
    def check_delivery_phone(cls, value: str) -> str:
        return normalize_indian_mobile(value)


class OrderCreate(ContentModel):
    items: List[CartItem] = Field(min_length=1, max_length=MAX_ORDER_ITEMS)
    address: Address
    payment_method: PaymentMethod
    origin_url: Optional[str] = Field(default="", max_length=2000)


class OrderItemSnapshot(ContentModel):
    product_id: str
    # Recorded so an invoice reads "Detergent (1kg)" rather than leaving the
    # customer to remember which one they bought. Optional because orders
    # placed before variants existed have none.
    variant_id: Optional[str] = None
    variant_label: Optional[str] = None
    name: str
    image: str
    price: float = Field(ge=0)
    quantity: int = Field(ge=1, le=MAX_CART_QUANTITY)


class Order(ContentModel):
    order_id: str = Field(default_factory=lambda: f"ord_{uuid.uuid4().hex[:10]}")
    user_id: str
    user_mobile: str
    user_email: Optional[str] = None
    items: List[OrderItemSnapshot] = Field(min_length=1)
    subtotal: float = Field(ge=0)
    shipping: float = Field(ge=0)
    total: float = Field(ge=0)
    address: Address
    payment_method: PaymentMethod
    payment_status: PaymentStatus = PaymentStatus.PENDING
    status: OrderStatus = OrderStatus.PLACED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
