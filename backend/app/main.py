import logging

from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS
from .database import close_database, create_indexes
from .middleware import csrf_protection
from .routers import admin, auth, catalog, orders, shopping
from .seed import seed_products


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(title="Nayara API")

for router in (
    auth.router,
    catalog.router,
    shopping.router,
    orders.router,
    admin.router,
):
    app.include_router(router)

root_router = APIRouter(prefix="/api")


@root_router.get("/")
async def root():
    return {"message": "Nayara API", "status": "ok"}


app.include_router(root_router)

# CSRF is registered first so the CORS middleware stays outermost and can
# attach its headers to rejected cross-site requests.
app.middleware("http")(csrf_protection)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=list(CORS_ORIGINS),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    await create_indexes()
    await seed_products()


@app.on_event("shutdown")
async def on_shutdown():
    close_database()
