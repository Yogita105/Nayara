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
- `rate_limit.py`: sign-in and registration throttling
- `utils.py`: shared serialization and normalization helpers
- `seed.py`: initial product data
- `routers/auth.py`: registration, login, logout, and current-user routes
- `routers/catalog.py`: products and reviews
- `routers/shopping.py`: cart and wishlist
- `routers/orders.py`: customer order operations
- `routers/admin.py`: inquiries, administration, and file uploads
- `main.py`: FastAPI composition, middleware, and lifecycle hooks

Run the API from the repository root with:

```powershell
python -m uvicorn backend.server:app --host 127.0.0.1 --port 8000
```

Or from the `backend` directory with:

```powershell
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```
