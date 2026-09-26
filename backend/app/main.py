import logging

from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware

from .config import (
    AUTO_SEED_PRODUCTS,
    API_DOCS_ENABLED,
    CORS_ORIGINS,
    ENVIRONMENT,
    LOG_JSON,
    LOG_LEVEL,
)
from .database import close_database, create_indexes
from .errors import register_error_handlers
from .frontend import mount_frontend
from .middleware import csrf_protection, limit_request_size, request_context
from .observability import REQUEST_ID_HEADER, configure_logging
from .pagination import TOTAL_COUNT_HEADER
from .routers import admin, auth, catalog, health, orders, settings, shopping
from .seed import seed_products

configure_logging(LOG_LEVEL, LOG_JSON)
logger = logging.getLogger(__name__)

# The interactive documentation publishes every route and request shape,
# including the admin API. See API_DOCS_ENABLED in config for the reasoning.
app = FastAPI(
    title="Nayara API",
    docs_url="/docs" if API_DOCS_ENABLED else None,
    redoc_url="/redoc" if API_DOCS_ENABLED else None,
    openapi_url="/openapi.json" if API_DOCS_ENABLED else None,
)
register_error_handlers(app)

for router in (
    health.router,
    auth.router,
    catalog.router,
    shopping.router,
    orders.router,
    admin.router,
    settings.router,
):
    app.include_router(router)

root_router = APIRouter(prefix="/api")


@root_router.get("/")
async def root():
    return {"message": "Nayara API", "status": "ok"}


app.include_router(root_router)

# Registered after the API so its catch-all cannot shadow a route.
mount_frontend(app)

# Middleware runs outermost-last, so CORS is added after the others and can
# attach its headers even to responses they generate. The size limit sits
# inside the request context, so a refusal is still logged and carries a
# request id.
app.middleware("http")(csrf_protection)
app.middleware("http")(limit_request_size)
app.middleware("http")(request_context)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=list(CORS_ORIGINS),
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[TOTAL_COUNT_HEADER, REQUEST_ID_HEADER],
)


@app.on_event("startup")
async def on_startup():
    logger.info("Starting API", extra={"environment": ENVIRONMENT})
    await create_indexes()
    if AUTO_SEED_PRODUCTS:
        inserted = await seed_products()
        if inserted:
            logger.info("Inserted starter products", extra={"count": inserted})
    else:
        logger.info(
            "Automatic product seeding is off; run scripts/seed_products.py to "
            "fill an empty catalogue",
            extra={"environment": ENVIRONMENT},
        )
    logger.info("API ready")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Shutting down API")
    close_database()
