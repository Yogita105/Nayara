# Build the site, then run the API that serves both it and the JSON endpoints.
# One image means one deployment, one origin, and first-party cookies.

FROM node:22-alpine AS frontend
WORKDIR /build

# Dependencies change far less often than source, so install them first and let
# the layer cache survive ordinary edits.
COPY frontend/package.json frontend/yarn.lock ./
RUN yarn install --frozen-lockfile --network-timeout 600000

COPY frontend/ ./
# No API address is baked in: the browser calls /api on the origin it loaded from.
RUN yarn build


FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    FRONTEND_DIST=/app/static

WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend /build/build /app/static

# Running as root would let a flaw in the application own the container.
RUN useradd --create-home --uid 10001 nayara \
    && chown -R nayara:nayara /app
USER nayara

EXPOSE 8080

# Readiness reports the database too, so an instance that cannot reach MongoDB
# is replaced rather than left serving errors.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/api/health/ready', timeout=4).status == 200 else 1)"

CMD ["sh", "-c", "exec uvicorn server:app --host 0.0.0.0 --port ${PORT} --workers ${WEB_CONCURRENCY:-2} --proxy-headers --forwarded-allow-ips='*'"]
