"""Liveness and readiness endpoints for load balancers and deployments.

They live under /api so any proxy already routing the API can reach them, and
they are deliberately unauthenticated so a probe needs no credentials.
"""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..config import ENVIRONMENT
from ..database import db


router = APIRouter(prefix="/api", tags=["health"])
logger = logging.getLogger(__name__)

PING_TIMEOUT_MS = 2000


@router.get("/health")
async def liveness():
    """Report that the process is running and able to answer."""
    return {"status": "ok", "environment": ENVIRONMENT}


@router.get("/health/ready")
async def readiness():
    """Report whether the API can serve traffic, checking its database."""
    try:
        await db.command({"ping": 1}, maxTimeMS=PING_TIMEOUT_MS)
    except Exception as error:
        logger.error("Readiness check failed", extra={"reason": str(error)})
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "database": "unreachable"},
        )
    return {"status": "ready", "database": "reachable"}
