"""Serving the built frontend from the API.

Keeping both halves on one origin means cookies stay first-party, so the CSRF
token the browser must read is readable, and no CORS configuration is needed in
production.
"""

import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

# Files the browser may request directly from the site root.
ROOT_FILES = {
    "favicon.ico",
    "manifest.json",
    "robots.txt",
    "asset-manifest.json",
    "logo192.png",
    "logo512.png",
}


def frontend_directory() -> Path:
    configured = os.environ.get("FRONTEND_DIST")
    if configured:
        return Path(configured)
    # The image copies the build here; a checkout has it under frontend/.
    backend_dir = Path(__file__).resolve().parents[1]
    packaged = backend_dir / "static"
    return packaged if packaged.is_dir() else backend_dir.parent / "frontend" / "build"


def mount_frontend(app: FastAPI) -> None:
    """Serve the built site, falling back to index.html for app routes.

    Without the fallback, reloading a page such as /account would ask the
    server for a file that does not exist.
    """
    directory = frontend_directory()
    index = directory / "index.html"
    if not index.is_file():
        logger.info(
            "No built frontend found; serving the API only",
            extra={"looked_in": str(directory)},
        )
        return

    assets = directory / "static"
    if assets.is_dir():
        app.mount("/static", StaticFiles(directory=assets), name="assets")

    @app.get("/{requested_path:path}", include_in_schema=False)
    async def serve_frontend(requested_path: str):
        # Unknown API paths must stay a JSON 404 rather than returning a page.
        if requested_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")

        if requested_path in ROOT_FILES:
            candidate = directory / requested_path
            if candidate.is_file():
                return FileResponse(candidate)

        return FileResponse(index)

    logger.info("Serving the built frontend", extra={"directory": str(directory)})
