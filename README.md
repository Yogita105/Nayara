# Nayara

Nayara is a React storefront backed by a FastAPI and MongoDB API.

Track launch preparation in the
[production readiness checklist](./PRODUCTION-READINESS.md).

## Authentication configuration

The application uses email-or-mobile and password authentication with seven-day,
server-managed sessions. New accounts require both an email address and an Indian
mobile number. Existing accounts without a mobile number can continue to sign in by
email. Configure these backend environment variables:

- `ADMIN_EMAILS`: comma-separated email addresses that should receive administrator access.
- `COOKIE_SECURE`: set to `true` in HTTPS production environments; leave `false` for local HTTP development.
- `ENVIRONMENT`: one of `development`, `test`, `staging`, or `production`.
- `CORS_ORIGINS`: comma-separated frontend origins. It is required in production,
  and wildcard origins are rejected.
- `SECRET_KEY`: signing key used to derive CSRF tokens. It is required in production,
  must be at least 32 characters, and must not reuse the development default.
- `RATE_LIMIT_ENABLED`: defaults to `true`. Disable it only for local debugging.
- `TRUST_PROXY_HEADERS`: defaults to `false`. Enable it only when the API sits behind a
  proxy you control that overwrites `X-Forwarded-For`, otherwise callers can spoof
  their address and bypass rate limits.
- `LOG_LEVEL`: one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`. Defaults to
  `INFO`.
- `LOG_JSON`: defaults to `true` in production and staging, `false` elsewhere.
- `AUTO_SEED_PRODUCTS`: defaults to `true` in development and test, `false` elsewhere.

For example:

```env
ENVIRONMENT=production
COOKIE_SECURE=true
CORS_ORIGINS=https://www.nayara.in,https://nayara.in
SECRET_KEY=<a long random value from a secret manager>
```

New accounts whose normalized email appears in `ADMIN_EMAILS` are administrators.
Existing MongoDB admin flags are preserved, and allowlisted accounts are promoted when
they log in.

Passwords are stored as bcrypt hashes. Session tokens are sent only through an HttpOnly
cookie and are stored as SHA-256 hashes in MongoDB.

## CSRF protection

State-changing requests (`POST`, `PUT`, `PATCH`, and `DELETE`) that authenticate with
the session cookie must send an `X-CSRF-Token` header. The token is an HMAC of the
session token, so it is bound to one session and cannot be forged by another site.

- The backend issues the token in the login and registration response bodies, and in a
  readable `csrf_token` cookie that `GET /api/auth/me` refreshes.
- The frontend API client attaches the header automatically for unsafe methods.
- Requests authenticated with an `Authorization: Bearer` header are exempt, because
  browsers never attach that header automatically.

Deploy the frontend and API on the same site (for example behind one domain with the
API under `/api`) so the browser can read the `csrf_token` cookie.

## Rate limiting

Sign-in and registration are throttled with fixed windows stored in MongoDB, so the
limits stay correct across multiple API workers. Exceeding a limit returns HTTP `429`
with a `Retry-After` header.

| Rule | Limit | Window |
| --- | --- | --- |
| Sign-in attempts per address | 50 | 15 minutes |
| Failed sign-in attempts per account | 5 | 15 minutes |
| Registrations per address | 10 | 1 hour |

Once an account reaches its failed-attempt limit it is locked for the rest of the
window, even if the correct password is supplied, so guessing cannot shortcut the
lockout. A successful sign-in clears that account's failure counter. Expired windows
are removed automatically by a MongoDB TTL index.

## Request validation

Request models in `backend/app/models.py` reject invalid data before it reaches
MongoDB, returning HTTP `422` with the offending field. The main rules are:

| Area | Rule |
| --- | --- |
| Products | Price and MRP must be positive, MRP cannot be below price, stock cannot be negative, category must be a known value, and the slug must be lowercase and hyphenated |
| Cart | Quantities run from 1 to 50; a cart update may use 0 to remove a line |
| Reviews | Ratings must be 1 to 5, with a non-empty title and comment |
| Addresses | Pincodes must be six digits not starting with zero, and the delivery phone is validated and stored as `+91XXXXXXXXXX` |
| Orders | At least one item, at most 50, and the payment method must be `card`, `upi` or `cod` |
| Contact and bulk inquiries | Valid email addresses and capped message lengths |

Administrator updates use explicit models rather than free-form dictionaries, so only
known order and inquiry statuses are accepted and unrelated fields such as an order
total can never be overwritten. Updating a missing record returns `404` instead of
silently succeeding.

## Paging and indexes

Every list endpoint accepts `limit` and `offset` query parameters. Responses stay plain
arrays, so existing clients are unaffected, and the defaults match the previous fixed
caps. `limit` must be between 1 and 500; invalid values return `422`.

```http
GET /api/products?category=laundry&limit=24&offset=24
```

Each paged query sorts on an indexed field. Without a deterministic sort, skipping
records could return the same document twice or miss one entirely.

Administrator lists also return an `X-Total-Count` header so a page-numbered UI knows
how many records exist. Storefront listings omit it to avoid a second query on every
page view.

Indexes are declared in one table in `backend/app/database.py` and created at startup.
A failure is logged rather than blocking startup, because a unique index cannot be
built over pre-existing duplicates and the API should still serve traffic while that
is corrected.

## Orders and stock

Placing an order reserves stock. Each product is adjusted with a single conditional
update, so two shoppers competing for the last unit cannot both succeed:

```javascript
// Matches only while enough stock remains, then decrements in the same step.
{ product_id, stock: { $gte: quantity } } -> { $inc: { stock: -quantity } }
```

If a later line in the same order cannot be filled, the units already reserved are
returned and the whole order is refused with `409`. Repeated lines for one product are
combined first, so the check uses the real total. MongoDB transactions are not used
because they require a replica set, which a local development database may not have.

Cancelling an order returns its stock. The update matches only orders that are not yet
cancelled, so repeating the request cannot inflate the catalogue.

### Idempotent checkout

Send an `Idempotency-Key` header when placing an order:

```http
POST /api/orders
Idempotency-Key: 6f1c1f2e-...
```

Repeating a request with the same key returns the original order instead of creating a
second one, and a request arriving while the first is still running is rejected with
`409`. Keys are scoped per user and expire after 24 hours. After a failure the key is
released, so a shopper can correct the problem and submit again. The checkout page
generates one key per visit.

## Logging and health

Each request is tagged with an id, returned as `X-Request-ID`. A caller may supply its
own id to trace a request across services; otherwise one is generated. Every log line
written while handling that request carries the same id, so one customer report can be
followed through the service.

Requests are logged with their method, path, status and duration. Query strings,
headers and bodies are deliberately excluded because they carry passwords and session
tokens. Failed requests and anything slower than a second are raised to `WARNING`, and
server errors to `ERROR`, so a log search for warnings surfaces real problems such as
repeated failed sign-ins.

```json
{"time": "2026-09-19T14:57:23+00:00", "level": "WARNING", "logger": "nayara.request",
 "message": "Request completed", "request_id": "5cc73e15...", "method": "POST",
 "path": "/api/auth/login", "status": 401, "duration_ms": 287.38}
```

Production and staging emit JSON for a log aggregator; other environments print a
readable line. The plain uvicorn access log is switched off because these entries
replace it.

Two probes are available, both unauthenticated and under `/api` so any proxy already
routing the API can reach them:

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Liveness. Confirms the process is answering. |
| `GET /api/health/ready` | Readiness. Returns `503` when MongoDB is unreachable. |

Point a load balancer at readiness so an instance that loses its database is taken out
of rotation rather than serving failures.

## Starter products

`backend/app/seed.py` holds a small starter catalogue so a fresh clone has something to
show. It is written only into an **empty** products collection, so prices and stock
edited through the admin screens are never overwritten.

Seeding runs automatically in development and test only. Elsewhere it is a deliberate
step:

```powershell
cd backend
python scripts\seed_products.py
```

The reason is worth stating plainly: if a live catalogue were emptied by accident, an
automatic seed on the next restart would refill it with seven development products at
invented prices. The shop would look healthy while the real catalogue was gone. Leaving
it empty keeps the problem visible.

Seeding is a development convenience, not a migration system. The real catalogue
belongs in the admin screens.

## Databases

Three separate databases on the same cluster keep the shop, local work, and the test
suite from interfering:

| Purpose | Name | Set by |
| --- | --- | --- |
| Local development | `Nayara_dev` | `DB_NAME` in `backend/.env` |
| Tests | `Nayara_test` | `scripts/run_tests.py`, or `TEST_DB_NAME` |
| Production | `Nayara` | `DB_NAME` in the host's environment |

A database is only ever chosen by `DB_NAME`. Environment variables take precedence over
`.env`, which is how the test runner redirects both the API and the tests without
editing any file, and how a hosting platform supplies production settings where no
`.env` exists.

Local development deliberately does not use the production database. Once the shop is
live, its orders hold real names, phone numbers and addresses, and routine development
should never reach them.

## Running the tests

The suite creates and deletes accounts, orders and stock, so it must not run against
the database the shop is serving from. Use the runner, which starts its own API on port
8001 pointed at a separate database:

```powershell
cd backend
python scripts\run_tests.py
```

Arguments are passed through to pytest:

```powershell
python scripts\run_tests.py tests\test_inventory.py -k stock
```

The database name defaults to the local name with any `_dev` suffix replaced by
`_test`, for example `Nayara_dev` becomes `Nayara_test`. Override it with
`TEST_DB_NAME`.

Running `pytest` directly fails with an explanatory error when it would otherwise use
the database this project is configured for, so the mistake cannot be made by accident.

Legacy OAuth accounts do not have passwords. Set one without exposing it in shell
history by running:

```powershell
cd backend
python scripts\set_user_password.py user@example.com
```

## Backend structure

The Uvicorn entry point remains `backend/server.py`. Application code lives in the
`backend/app` package:

- `config.py`: environment and third-party service configuration
- `database.py`: MongoDB connection lifecycle and indexes
- `models.py`: Pydantic request and domain models
- `security.py`: password hashing, session cookies, CSRF tokens, and authorization dependencies
- `middleware.py`: CSRF enforcement for cookie-authenticated writes
- `observability.py`: structured logging and request correlation
- `rate_limit.py`: sign-in and registration throttling
- `utils.py`: shared serialization and normalization helpers
- `seed.py`: initial product data
- `pagination.py`: shared paging parameters for list endpoints
- `inventory.py`: stock reservation and release
- `idempotency.py`: duplicate-submission protection for checkout
- `routers/auth.py`: registration, login, logout, and current-user routes
- `routers/catalog.py`: products and reviews
- `routers/shopping.py`: cart and wishlist
- `routers/orders.py`: customer order operations
- `routers/admin.py`: inquiries, administration, and file uploads
- `routers/health.py`: liveness and readiness probes
- `main.py`: FastAPI composition, middleware, and lifecycle hooks

Run the API from the repository root with:

```powershell
python -m uvicorn backend.server:app --host 127.0.0.1 --port 8000
```

Or from the `backend` directory with:

```powershell
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```
