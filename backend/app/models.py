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


class CartItem(ContentModel):
    product_id: str = Field(min_length=1, max_length=100)
    quantity: int = Field(ge=1, le=MAX_CART_QUANTITY)


class AddToCartRequest(ContentModel):
    product_id: str = Field(min_length=1, max_length=100)
    quantity: int = Field(default=1, ge=1, le=MAX_CART_QUANTITY)


class UpdateCartRequest(ContentModel):
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
