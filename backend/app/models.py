import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    user_id: str
    email: str
    mobile: Optional[str] = None
    name: str
    picture: Optional[str] = ""
    is_admin: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    mobile: str = Field(min_length=10, max_length=20)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class Product(BaseModel):
    product_id: str = Field(default_factory=lambda: f"prod_{uuid.uuid4().hex[:10]}")
    name: str
    slug: str
    category: str
    description: str
    short_description: str
    price: float
    mrp: float
    image: str
    images: List[str] = Field(default_factory=list)
    stock: int = 100
    rating: float = 4.5
    reviews_count: int = 0
    badges: List[str] = Field(default_factory=list)
    featured: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProductCreate(BaseModel):
    name: str
    slug: str
    category: str
    description: str
    short_description: str
    price: float
    mrp: float
    image: str
    images: List[str] = Field(default_factory=list)
    stock: int = 100
    badges: List[str] = Field(default_factory=list)
    featured: bool = False


class CartItem(BaseModel):
    product_id: str
    quantity: int


class AddToCartRequest(BaseModel):
    product_id: str
    quantity: int = 1


class UpdateCartRequest(BaseModel):
    quantity: int


class WishlistRequest(BaseModel):
    product_id: str


class ReviewCreate(BaseModel):
    rating: int
    title: str
    comment: str


class Review(BaseModel):
    review_id: str = Field(default_factory=lambda: f"rev_{uuid.uuid4().hex[:10]}")
    product_id: str
    user_id: str
    user_name: str
    rating: int
    title: str
    comment: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ContactRequest(BaseModel):
    name: str
    email: str
    phone: Optional[str] = ""
    subject: str
    message: str


class BulkInquiryRequest(BaseModel):
    name: str
    business_name: str
    phone: str
    email: str
    city: str
    products_interested: List[str] = Field(default_factory=list)
    quantity: str
    message: Optional[str] = ""


class Address(BaseModel):
    full_name: str
    phone: str
    line1: str
    line2: Optional[str] = ""
    city: str
    state: str
    pincode: str


class OrderCreate(BaseModel):
    items: List[CartItem]
    address: Address
    payment_method: str
    origin_url: Optional[str] = ""


class OrderItemSnapshot(BaseModel):
    product_id: str
    name: str
    image: str
    price: float
    quantity: int


class Order(BaseModel):
    order_id: str = Field(default_factory=lambda: f"ord_{uuid.uuid4().hex[:10]}")
    user_id: str
    user_email: str
    items: List[OrderItemSnapshot]
    subtotal: float
    shipping: float
    total: float
    address: Address
    payment_method: str
    payment_status: str = "pending"
    status: str = "placed"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
