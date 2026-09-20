# Nayara

Nayara is a React storefront backed by a FastAPI and MongoDB API.

Track launch preparation in the
[production readiness checklist](./PRODUCTION-READINESS.md).

## Settings

All backend settings are environment variables. Locally they are read from
`backend/.env`; in production they are set as secrets on the host. That file is never
committed, and nothing named `.env*` can be added to the repository.

A value is resolved in this order: an environment variable, then `backend/.env`, then
the built-in default. An exported variable therefore always wins.

### Required everywhere

| Name | Meaning |
| --- | --- |
| `MONGO_URL` | MongoDB connection string, for example `mongodb+srv://USERNAME:PASSWORD@cluster.example.mongodb.net/?retryWrites=true&w=majority` |
| `DB_NAME` | Database to use. Keep development on its own name so local work never touches live orders. |

### Required in production

| Name | Meaning |
| --- | --- |
| `ENVIRONMENT` | One of `development`, `test`, `staging`, `production`. Defaults to `development`. |
| `SECRET_KEY` | Signing key used to derive CSRF tokens. At least 32 characters and not the development default. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. |
| `CORS_ORIGINS` | Comma-separated frontend origins. Wildcards are rejected. Unused when the frontend is served from the same origin, which is the default. |
| `COOKIE_SECURE` | Send session cookies only over HTTPS. Forced on in production. |

### Access

| Name | Meaning |
| --- | --- |
| `ADMIN_MOBILES` | Comma-separated mobile numbers that receive administrator access. Any usual form works, with or without the country code, spaces or a leading `+`. |

### Optional

| Name | Default | Meaning |
| --- | --- | --- |
| `RATE_LIMIT_ENABLED` | `true` | Disable only for local debugging. |
| `TRUST_PROXY_HEADERS` | `false` | Trust `X-Forwarded-For`. Enable only behind a proxy you control, or callers can spoof their address and evade rate limits. |
| `LOG_LEVEL` | `INFO` | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `LOG_JSON` | on in production and staging | JSON logs suit an aggregator; plain text suits a terminal. |
| `AUTO_SEED_PRODUCTS` | on in development and test | Writes the starter catalogue into an empty products collection. |
| `API_DOCS_ENABLED` | on in development and test | Serves `/docs`, `/redoc` and `/openapi.json`. Off elsewhere because the schema describes every admin endpoint. |
| `MONGO_MAX_POOL_SIZE` | `20` | Connections held per worker. Workers multiply this, so keep the total well under the cluster's limit. |
| `MONGO_TIMEOUT_MS` | `10000` | Server selection timeout. |
| `MONGO_SOCKET_TIMEOUT_MS` | `20000` | Socket timeout. |
| `MAX_REQUEST_BODY_BYTES` | `1048576` | Largest accepted request body, in bytes. |
| `MAX_UPLOAD_BYTES` | `5242880` | Largest accepted image upload, in bytes. |
| `AUDIT_RETENTION_DAYS` | `180` | How long security audit records are kept before MongoDB removes them. |

### Image uploads

| Name | Meaning |
| --- | --- |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary account name. |
| `CLOUDINARY_API_KEY` | Cloudinary API key. |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret. |

Without these, admin image upload is unavailable; the rest of the site works.

An example production set:

```env
ENVIRONMENT=production
COOKIE_SECURE=true
CORS_ORIGINS=https://www.nayara.in,https://nayara.in
SECRET_KEY=<a long random value from a secret manager>
```

## Authentication

The **mobile number identifies an account**. It is required, unique, and how people
sign in. An email address is optional: many customers in India have an address they
never read, so demanding one costs sign-ups without providing a usable way to reach
them. When an email is given it must be unique, and it can also be used to sign in.

Sessions are server-managed and last seven days.

New accounts whose mobile number appears in `ADMIN_MOBILES` are administrators.
Existing MongoDB admin flags are preserved, so an administrator created before the
allowlist existed keeps access.

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

## Account security

Two endpoints let someone recover control of an account without waiting for a session
to expire:

| Endpoint | Effect |
| --- | --- |
| `PUT /api/auth/profile` | Updates the name and optional email address |
| `POST /api/auth/password` | Replaces the password after checking the current one, then ends every other session |
| `POST /api/auth/logout-all` | Ends every session, including the caller's |

A password change deliberately keeps the caller signed in while cutting off everywhere
else, so someone who suspects their account is being used can lock it down without
losing the device in front of them. Password attempts are throttled per account, which
matters because the current password can otherwise be guessed through a stolen session.

Both are reachable from the Account screen at `/account`, alongside the name and email
address. The mobile number is not editable there: it identifies the account, is how
people sign in, and grants administrator access through the allowlist, so changing it
safely needs a verified-number flow.

## Rate limiting

Sign-in and registration are throttled with fixed windows stored in MongoDB, so the
limits stay correct across multiple API workers. Exceeding a limit returns HTTP `429`
with a `Retry-After` header.

| Rule | Limit | Window |
| --- | --- | --- |
| Sign-in attempts per address | 50 | 15 minutes |
| Failed sign-in attempts per account | 5 | 15 minutes |
| Password attempts per account | 5 | 15 minutes |
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
GET /api/products?category=laundry&sort=price_asc&limit=24&offset=24
```

Each paged query sorts on an indexed field and ends with `product_id` as a tiebreaker.
Without a total order, two products sharing a price could swap places between requests,
showing one of them on two pages and hiding the other entirely.

The tiebreaker follows the direction of the field before it wherever that lets an
existing index supply the order. An index can only be read backwards when every one of
its keys reverses together, so a mixed-direction sort needs an index of its own.

`backend/tests/test_query_performance.py` asks MongoDB for its plan and refuses a
collection scan, so an index that stops being used is reported rather than discovered in
production. The plans are read against a populated collection, because with a handful of
records the planner's choice says little about what it would do later.

The catalogue is sorted and filtered by the API, not the browser. Ordering only the
records already fetched would rank one page against itself, so the cheapest product
could sit on the last page. `sort` accepts `popular`, `newest`, `price_asc`,
`price_desc` and `rating`; anything else returns `422`. `max_price` narrows by price.

List endpoints return an `X-Total-Count` header giving the number of records matching
the query, so the shop and the admin screens can show how many exist rather than
silently stopping at whatever the page limit was.

Indexes are declared in one table in `backend/app/database.py` and created at startup.
A failure is logged rather than blocking startup, because a unique index cannot be
built over pre-existing duplicates and the API should still serve traffic while that
is corrected.

## Request size

A request is held in memory while it is handled, and the machine serving the shop has
far less memory than a determined caller can send. Writes are refused on their declared
`Content-Length` before the body is read, returning `413`:

| Route | Limit |
| --- | --- |
| `POST /api/admin/upload` | `MAX_UPLOAD_BYTES`, plus a small allowance for the multipart wrapper |
| Everything else | `MAX_REQUEST_BODY_BYTES` |

Reading a body and then measuring it is no protection, because the memory has already
been spent by the time the size is known. Reads are never limited.

A caller that streams a body in chunks declares no length, so it cannot be judged that
way. The upload route counts those bytes as they arrive and stops at the limit. Capping
request size at the proxy in front of the API is still worth doing as a second layer.

## Product variants

A product is sold in forms that differ by one thing: a weight for powders, a volume for
liquids, a colour for soaps. Which is stored on the product as `option_name`, and the
forms themselves as `variants`:

```javascript
{
  option_name: "Weight",
  price_from: 100,
  variants: [
    { variant_id, label: "500g", price: 100, mrp: 130, stock: 40, image: "" },
    { variant_id, label: "1kg",  price: 180, mrp: 240, stock: 25, image: "" }
  ]
}
```

Price and stock belong to the variant, because a kilo and a half-kilo are priced
differently and run out independently. An image is optional and falls back to the
product's: colours need their own photograph, weights generally look alike.
`price_from` holds the cheapest variant's price so the catalogue can still be sorted by
a plain indexed field. Reviews and wishlists stay on the **product**.

One axis per product. A matrix of size against colour needs option sets and generated
combinations, which is a great deal of machinery for a catalogue this size.

The product's own `price`, `mrp` and `stock` are a **summary** of its variants, not
something anyone sets: the price is the cheapest on offer, the MRP belongs to that same
form, and the stock is everything on hand across the forms. The server recomputes them
on every save, so the two cannot be stored disagreeing. They exist because the
storefront still reads them, and are removed once it does not.

A form can be added, priced, stocked and photographed in **Admin → Products**. Two forms
cannot share a label, a product cannot be left with none, and a form cannot be removed
while an open order still holds it — cancelling that order would return its units to a
variant that no longer exists, and the stock would vanish without a word.

A request that names no variant resolves to the product's only one, which is what keeps
the existing site working. A product with a real choice refuses and asks which.

> **Not finished.** The storefront has no selector yet, so a product given a second form
> cannot be bought until that is built. Give a product two forms only once it can.

Databases that predate this are brought up to date with:

```powershell
cd backend
python scripts\add_product_variants.py            # report what would change
python scripts\add_product_variants.py --apply    # make the change
```

It is safe to run twice; a product that already has variants is left alone.

## Orders and stock

Placing an order reserves stock. Stock belongs to the variant, so a kilo bag and a
half-kilo bag run out independently. Each is adjusted with a single conditional update,
so two shoppers competing for the last unit cannot both succeed:

```javascript
// Matches only while that variant still has enough, then decrements it in the
// same step. The condition names the variant, so the positional update can
// only reach the one that satisfied it.
{ product_id, variants: { $elemMatch: { variant_id, stock: { $gte: quantity } } } }
  -> { $inc: { "variants.$.stock": -quantity } }
```

If a later line in the same order cannot be filled, the units already reserved are
returned and the whole order is refused with `409`. Repeated lines for one product are
combined first, so the check uses the real total. MongoDB transactions are not used
because they require a replica set, which a local development database may not have.

Because an order is all or nothing, the shop says how many are left while there is
still time to change it. A product with five or fewer remaining shows the count, one
with none is marked out of stock and cannot be added, and a cart holding more than
remains names the line and will not proceed to checkout. The exact figure is only
shown when it is low: publishing the full count on every product tells competitors
what the shop holds, and means nothing to somebody buying one.

The browser is never the authority here. It reports what it last read, while the
reservation above decides what actually happens.

The cart refuses a quantity the shop cannot fill, whether it arrives in one request or
by adding one at a time, and names what is left. That check reads stock at the moment
of adding, so it is a courtesy rather than a guarantee: stock can fall between filling
a cart and paying for it, which is why the reservation still decides.

Cancelling an order returns its stock. The update matches only orders that are not yet
cancelled, so repeating the request cannot inflate the catalogue.

### Order states

An order moves forward only:

```text
placed ─→ processing ─→ shipped ─→ delivered
   └───────────┴───────────┴────→ cancelled
```

`delivered` and `cancelled` are final. Reopening a cancelled order would leave it
active after its stock had already gone back to the catalogue, so the shop would offer
units that are actually spoken for. A rejected change returns `409` and names the
statuses that are available instead. Repeating the current status succeeds without
doing anything, so a retry is harmless.

The admin screen offers only the statuses the API will accept, and disables the control
once an order is final.

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

## Security audit trail

Security-relevant actions are recorded in the `audit_events` collection, so there is
something to look at afterwards: which account changed an order, whether a run of
failed sign-ins preceded a successful one, when a password was last changed.

| Event | Recorded when |
| --- | --- |
| `auth.account_created` | A new account is registered |
| `auth.signed_in` | A sign-in succeeds |
| `auth.sign_in_failed` | A sign-in is refused |
| `auth.signed_out`, `auth.signed_out_everywhere` | A session ends |
| `auth.password_changed`, `auth.password_change_refused` | A password change is attempted |
| `auth.profile_updated` | A name or email address is changed |
| `auth.admin_granted` | An account gains administrator access through the allowlist |
| `admin.order_updated`, `admin.bulk_inquiry_updated` | An administrator changes a record |
| `admin.product_created`, `admin.product_updated`, `admin.product_deleted` | The catalogue changes |
| `admin.image_uploaded` | An image is published |

**Nothing recorded may be a credential.** A log holding passwords or session tokens
would be worth stealing in its own right, and would hand over the accounts it exists to
protect. Values are scrubbed on the way in: any field whose *name* suggests a password,
token, secret or key is replaced with `[redacted]` rather than stored.

Two details follow from that:

- A failed sign-in for an unknown account records no identifier. Someone may type their
  password into the mobile-number box, and storing what was typed would keep that
  password as plainly as if it had been asked for. When the account *is* known, the
  failure is recorded against it, which is what makes a run of attempts visible.
- A profile change records *which* fields changed, not what they were changed to.

Writing a record never fails a request that has already succeeded. Records expire after
`AUDIT_RETENTION_DAYS`, so the shop does not hold a sign-in history indefinitely.

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

## Continuous integration

`.github/workflows/ci.yml` runs on every push to `main` and on every pull request:

| Job | Checks |
| --- | --- |
| Backend | `flake8`, `black --check` and `mypy` over the backend, then the full suite against a MongoDB service container |
| Frontend | `yarn lint`, then `yarn build` with `CI=true` so build warnings fail the run |
| Secret scanning | `gitleaks` over the whole commit history, with findings redacted from the log |
| Dependencies | `pip-audit` against `backend/requirements.txt`, and `yarn audit` for JavaScript |

Run the same checks locally before pushing:

```powershell
cd backend
python -m flake8 app scripts tests
python -m black --check app scripts tests
python -m mypy app
python scripts\run_tests.py
python -m pip_audit --requirement requirements.txt --strict

cd ..\frontend
yarn lint
yarn build
```

Formatting and type settings live in `backend/pyproject.toml`. The formatter's line
length matches the one flake8 enforces, so the two cannot disagree, and both tools are
pinned in `requirements.txt` because a different version would reach a different
verdict on the same code.

The JavaScript audit is advisory for now. The Create React App toolchain carries
transitive advisories that cannot be resolved without replacing it, so the step reports
findings without failing the run. The Python audit does fail the run, and the pinned
dependencies in `backend/requirements.txt` are currently clean.

## Errors

Every error uses one shape, so a client can rely on `detail` being a readable
sentence:

```json
{
  "detail": "Password: String should have at least 8 characters",
  "errors": [{"field": "password", "message": "String should have at least 8 characters"}],
  "request_id": "9393c7f0..."
}
```

Validation failures previously returned a list of objects that also echoed what was
submitted, including the password on a sign-up form. The browser could not render that
list at all, so a rejected form left a blank page. Submitted values are now dropped
before the response is built.

`request_id` matches the `X-Request-ID` header, so a customer can quote it and the
matching log line can be found.

A refusal raised by hand can name the field responsible with `FieldError`, so a form can
mark the box itself rather than showing a sentence with nothing to attach it to:

```python
raise FieldError(409, "email", "Another account already uses this email")
```

## Forms and accessibility

Every input is associated with its label, so a screen reader announces what the box is
for. When a submission is refused:

- an error summary appears at the top of the form, takes focus, and is announced;
- each message links to the field it belongs to;
- the field carries `aria-invalid` and points at its message through `aria-describedby`;
- correcting a field clears its own message and leaves the others alone.

The browser's own validation is switched off so that one set of messages is used
throughout, presented the same way whether the objection came from the browser or the
API. Only emptiness and length are judged in the browser. Rules such as what makes a
valid Indian mobile number belong to the API, and repeating them would mean two places
to keep in step.

## Deploying

The API serves the built frontend, so the whole site is one container on one origin.
That keeps cookies first-party, which is what the CSRF protection depends on, and means
there is no CORS configuration to maintain in production.

### Build and run locally

```powershell
docker build -t nayara .
docker run --rm -p 8080:8080 --env-file backend\.env nayara
```

### Deploy to Fly.io

`fly.toml` targets Mumbai, because the MongoDB Atlas cluster answers in single-digit
milliseconds from India. Hosting further away would add that distance to every query on
every page.

```powershell
fly launch --no-deploy        # first time only, reuses the committed fly.toml
fly secrets set MONGO_URL="..." DB_NAME="Nayara" SECRET_KEY="..." ADMIN_MOBILES="..." `
                CLOUDINARY_CLOUD_NAME="..." CLOUDINARY_API_KEY="..." CLOUDINARY_API_SECRET="..."
fly deploy
```

`ENVIRONMENT`, `PORT`, `WEB_CONCURRENCY` and `MONGO_MAX_POOL_SIZE` are already set in
`fly.toml`. Everything secret belongs in `fly secrets`, never in that file.

Setting `ENVIRONMENT=production` turns on secure cookies and JSON logging, requires a
real `SECRET_KEY`, and stops products being seeded automatically.

### Connections

Each worker keeps its own MongoDB pool, so the two multiply. The defaults hold two
workers at twenty connections each, which is forty of the five hundred a shared Atlas
cluster allows. Raising `WEB_CONCURRENCY` without lowering `MONGO_MAX_POOL_SIZE` is the
quickest way to exhaust that limit, and it presents as a database outage rather than a
configuration mistake.

### A local build is not the deployed build

`yarn build` run by hand reads `frontend/.env` and bakes `REACT_APP_BACKEND_URL` into
the bundle. The image builds without that file, so the bundle calls `/api` on whatever
origin served it. Never copy a locally built `frontend/build` into a deployment.

Legacy OAuth accounts do not have passwords. Set one without exposing it in shell
history by running:

```powershell
cd backend
python scripts\set_user_password.py user@example.com
```

## Releasing and rolling back

Every deployment is a new image, and Fly keeps the previous ones, so going back is
redeploying an earlier image rather than rebuilding an earlier commit.

### Before releasing

1. `git status` is clean and the change is pushed, so the running image matches a commit
   somebody else can find.
2. Continuous integration is green on that commit. It runs the same checks locally
   available, against a real database.
3. Note the current release, so the way back is known before it is needed:

```powershell
fly releases --image
```

### Releasing

```powershell
fly deploy
```

The default strategy replaces machines one at a time and waits for the health checks in
`fly.toml`, so a container that fails to start does not take the site down with it.
Watch it with `fly logs`, and confirm `/api/health/ready` answers before walking away:
that probe reports whether MongoDB is reachable, not merely whether the process is up.

### Rolling back

```powershell
fly releases --image                       # find the last good image reference
fly deploy --image registry.fly.io/<app>:deployment-XXXXXXXX
```

**What rolling back does not undo:**

- **Data.** Orders placed, accounts created and stock reserved by the newer version stay
  exactly as they are. Only the code goes back.
- **Indexes.** They are created at startup and never dropped, so an index added by the
  newer version remains. That is harmless — an unused index costs a little write time
  and nothing else — but it means the database is not returned to its earlier shape.
- **Anything a newer version wrote in a shape the older one cannot read.** There is no
  such case today, because no field has been renamed or removed. It is the thing to
  check before releasing a change that alters stored documents.

If a release has to be reverted, revert the commit too. An image running ahead of
`main` is the state nobody expects when they next deploy.

## Rotating credentials

Secrets live in `fly secrets`, which stores them encrypted and exposes them to the
container as environment variables. `fly secrets list` shows names and digests, never
values.

Setting a secret restarts the machines, so each rotation is a small deployment.

| Credential | How to rotate | What it costs |
| --- | --- | --- |
| `MONGO_URL` | Create a second Atlas user, set the new URL, then delete the old user | Nothing, provided the new user exists *before* the switch |
| `SECRET_KEY` | `fly secrets set SECRET_KEY="..."` | Every CSRF token stops matching until each browser reloads |
| `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET` | Rotate in Cloudinary, then set both together | New uploads only; images already served keep working |
| `ADMIN_MOBILES` | `fly secrets set ADMIN_MOBILES="..."` | Grants access. It does **not** revoke it — see below |

Generate a signing key without it reaching the shell history of a machine you share:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### What rotating the signing key actually breaks

A CSRF token is an HMAC of the session token under `SECRET_KEY`, so changing the key
makes every token in a browser stop matching. Sessions themselves survive, because those
are rows in MongoDB. The first call to `/api/auth/me` reissues the cookie, which the site
makes when a page loads, so the window is short: a write attempted between the restart
and that call is refused with `403` and succeeds on retry.

Rotate it deliberately, not routinely, and never as a way of signing people out — it
does not do that.

### Removing an administrator

Taking a number out of `ADMIN_MOBILES` does not demote anybody. The allowlist grants
`is_admin` when an account is created or signs in, and the flag then lives on the
account, so that an administrator added before the allowlist existed keeps working.

To actually remove access, clear the flag and end the sessions:

```javascript
db.users.updateOne({ mobile: "+919876500000" }, { $set: { is_admin: false } })
db.user_sessions.deleteMany({ user_id: "<their user_id>" })
```

## If a credential leaks

Order matters: revoke first, investigate second. An investigation that begins before the
credential is dead is a decision to let it be used a while longer.

1. **Revoke.** Rotate the exposed credential as above. For a database password, delete
   the Atlas user outright rather than changing it.
2. **Close the sessions** if account data may have been reached:

   ```javascript
   db.user_sessions.deleteMany({})   // everybody signs in again
   ```

3. **Read the audit trail.** `audit_events` records sign-ins, failed attempts and every
   administrator action, with the address each came from:

   ```javascript
   db.audit_events.find({ at: { $gt: ISODate("2026-01-01") } }).sort({ at: -1 })
   ```

4. **Purge it from history if it was committed.** Rotating is not enough: the value
   stays in every clone of the repository. The secret scan in continuous integration
   reads the whole history for this reason.
5. **Write down what happened** — what leaked, how, when it was revoked, and what the
   audit trail showed — before the detail is lost.

Nothing in this repository should ever hold a real credential. `.gitignore` excludes
both `.env.*` and `*.env`, which between them cover every form these files take, and
settings are documented by name only.

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
