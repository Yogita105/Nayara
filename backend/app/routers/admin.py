import logging
import uuid
from datetime import datetime, timezone

import cloudinary.uploader
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import RedirectResponse

from .. import audit
from ..config import MAX_UPLOAD_BYTES
from ..database import db
from ..inventory import release_stock
from ..models import (
    BulkInquiryRequest,
    BulkInquiryUpdate,
    ContactRequest,
    OrderUpdate,
    allowed_next_statuses,
    can_change_status,
)
from ..pagination import TOTAL_COUNT_HEADER, limit_query, offset_query
from ..security import require_admin
from ..utils import serialize_doc


router = APIRouter(prefix="/api", tags=["admin"])
logger = logging.getLogger(__name__)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
UPLOAD_CHUNK_BYTES = 64 * 1024


async def paged_admin_list(
    collection: str,
    response: Response,
    sort_field: str,
    limit: int,
    offset: int,
    projection: dict,
) -> list:
    """Return one page and report the total so the UI can show page counts."""
    response.headers[TOTAL_COUNT_HEADER] = str(
        await db[collection].count_documents({})
    )
    docs = await (
        db[collection]
        .find({}, projection)
        .sort(sort_field, -1)
        .skip(offset)
        .limit(limit)
        .to_list(limit)
    )
    return [serialize_doc(doc) for doc in docs]


@router.post("/contact")
async def contact_submit(payload: ContactRequest):
    doc = payload.model_dump()
    doc["contact_id"] = f"ct_{uuid.uuid4().hex[:10]}"
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.contacts.insert_one(doc)
    return {"ok": True, "contact_id": doc["contact_id"]}


@router.post("/bulk-inquiry")
async def bulk_inquiry_submit(payload: BulkInquiryRequest):
    doc = payload.model_dump()
    doc["inquiry_id"] = f"bi_{uuid.uuid4().hex[:10]}"
    doc["status"] = "new"
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    await db.bulk_inquiries.insert_one(doc)
    return {"ok": True, "inquiry_id": doc["inquiry_id"]}


@router.get("/admin/bulk-inquiries")
async def admin_bulk_inquiries(
    response: Response,
    limit: int = limit_query(500),
    offset: int = offset_query(),
    _: dict = Depends(require_admin),
):
    return await paged_admin_list(
        "bulk_inquiries", response, "created_at", limit, offset, {"_id": 0}
    )


@router.put("/admin/bulk-inquiries/{inquiry_id}")
async def admin_update_bulk_inquiry(
    inquiry_id: str,
    payload: BulkInquiryUpdate,
    request: Request,
    user: dict = Depends(require_admin),
):
    result = await db.bulk_inquiries.update_one(
        {"inquiry_id": inquiry_id},
        {"$set": {"status": payload.status}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    doc = await db.bulk_inquiries.find_one(
        {"inquiry_id": inquiry_id},
        {"_id": 0},
    )
    await audit.record(
        "admin.bulk_inquiry_updated",
        actor_id=user["user_id"],
        request=request,
        inquiry_id=inquiry_id,
        status=payload.status,
    )
    return serialize_doc(doc)


@router.get("/admin/stats")
async def admin_stats(_: dict = Depends(require_admin)):
    total_orders = await db.orders.count_documents({})
    total_users = await db.users.count_documents({})
    total_products = await db.products.count_documents({})
    total_messages = await db.contacts.count_documents({})
    total_bulk_inquiries = await db.bulk_inquiries.count_documents({})
    orders = await db.orders.find(
        {"payment_status": {"$in": ["paid", "cod_pending"]}},
        {"_id": 0, "total": 1},
    ).to_list(2000)
    revenue = sum(order.get("total", 0) for order in orders)
    return {
        "total_orders": total_orders,
        "total_users": total_users,
        "total_products": total_products,
        "total_messages": total_messages,
        "total_bulk_inquiries": total_bulk_inquiries,
        "revenue": round(revenue, 2),
    }


@router.get("/admin/orders")
async def admin_all_orders(
    response: Response,
    limit: int = limit_query(500),
    offset: int = offset_query(),
    _: dict = Depends(require_admin),
):
    return await paged_admin_list(
        "orders", response, "created_at", limit, offset, {"_id": 0}
    )


@router.put("/admin/orders/{order_id}")
async def admin_update_order(
    order_id: str,
    payload: OrderUpdate,
    request: Request,
    user: dict = Depends(require_admin),
):
    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    current_status = order.get("status", "")
    if payload.status is not None and not can_change_status(
        current_status, payload.status
    ):
        allowed = sorted(allowed_next_statuses(current_status))
        raise HTTPException(
            status_code=409,
            detail=(
                f"An order that is {current_status} cannot become "
                f"{payload.status}. "
                + (f"It can only become: {', '.join(allowed)}." if allowed
                   else "It has reached its final state.")
            ),
        )

    if payload.status == "cancelled":
        await cancel_order(order, payload)
    else:
        await db.orders.update_one(
            {"order_id": order_id},
            {"$set": payload.model_dump(exclude_none=True)},
        )

    doc = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    await audit.record(
        "admin.order_updated",
        actor_id=user["user_id"],
        request=request,
        order_id=order_id,
        status_from=current_status,
        status_to=doc.get("status") if doc else None,
        payment_status=payload.payment_status,
    )
    return serialize_doc(doc)


async def cancel_order(order: dict, payload: OrderUpdate) -> None:
    """Cancel an order and return its stock exactly once.

    The guard makes the write succeed only for the first cancellation, so
    repeated requests cannot inflate the catalogue.
    """
    updates = payload.model_dump(exclude_none=True)
    result = await db.orders.update_one(
        {
            "order_id": order["order_id"],
            "status": {"$ne": "cancelled"},
            "stock_released": {"$ne": True},
        },
        {"$set": {**updates, "stock_released": True}},
    )
    if result.modified_count == 0:
        return

    await release_stock([
        {"product_id": item["product_id"], "quantity": item["quantity"]}
        for item in order.get("items", [])
    ])


@router.get("/admin/users")
async def admin_users(
    response: Response,
    limit: int = limit_query(500),
    offset: int = offset_query(),
    _: dict = Depends(require_admin),
):
    return await paged_admin_list(
        "users",
        response,
        "created_at",
        limit,
        offset,
        {"_id": 0, "password_hash": 0},
    )


@router.get("/admin/contacts")
async def admin_contacts(
    response: Response,
    limit: int = limit_query(500),
    offset: int = offset_query(),
    _: dict = Depends(require_admin),
):
    return await paged_admin_list(
        "contacts", response, "created_at", limit, offset, {"_id": 0}
    )


@router.post("/admin/upload")
async def admin_upload(
    file: UploadFile = File(...),
    user: dict = Depends(require_admin),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename")
    extension = (
        file.filename.rsplit(".", 1)[-1].lower()
        if "." in file.filename
        else "bin"
    )
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # Read in pieces and stop at the limit. Reading the whole file and then
    # measuring it would mean the memory was already spent before the file
    # could be refused.
    data = bytearray()
    while True:
        chunk = await file.read(UPLOAD_CHUNK_BYTES)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=(
                    "File is too large. The limit is "
                    f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
                ),
            )
    if not data:
        raise HTTPException(status_code=400, detail="The file is empty")
    data = bytes(data)

    file_id = uuid.uuid4().hex
    try:
        result = cloudinary.uploader.upload(
            data,
            public_id=f"nayara/products/{file_id}",
            resource_type="image",
            overwrite=True,
        )
    except Exception as error:
        logger.error("Cloudinary upload failed: %s", error)
        raise HTTPException(status_code=500, detail="Image upload failed") from error

    cloudinary_url = result["secure_url"]
    await db.files.insert_one({
        "file_id": file_id,
        "cloudinary_url": cloudinary_url,
        "cloudinary_public_id": result["public_id"],
        "content_type": f"image/{extension}",
        "size": len(data),
        "uploaded_by": user["user_id"],
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await audit.record(
        "admin.image_uploaded",
        actor_id=user["user_id"],
        file_id=file_id,
        size_bytes=len(data),
    )
    return {"file_id": file_id, "url": cloudinary_url}


@router.get("/files/{file_id}")
async def serve_file(file_id: str):
    record = await db.files.find_one(
        {"file_id": file_id, "is_deleted": False},
        {"_id": 0},
    )
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    return RedirectResponse(url=record["cloudinary_url"], status_code=302)
