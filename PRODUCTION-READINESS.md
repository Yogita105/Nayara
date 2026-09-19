# Production Readiness Checklist

Use this document to track the work required to take Nayara from an MVP to a
production-ready ecommerce application.

## Status

- `[x]` Completed
- `[ ]` Not started or incomplete

## 1. Application structure

- [x] Split the FastAPI monolith into configuration, database, model, security,
      seed, and domain-router modules.
- [x] Keep a stable, minimal Uvicorn entry point.
- [x] Document the backend package structure and local startup commands.
- [ ] Add clear service and repository layers when business logic becomes more
      complex.
- [ ] Establish database migration and index-deployment tooling.

## 2. Authentication and account security

- [x] Replace external OAuth with native email/password authentication.
- [x] Hash passwords with bcrypt.
- [x] Support login with either email address or Indian mobile number.
- [x] Normalize mobile numbers to the `+91XXXXXXXXXX` format.
- [x] Store only SHA-256 hashes of session tokens in MongoDB.
- [x] Send session tokens in HttpOnly cookies.
- [x] Persist sessions across browser refreshes.
- [x] Hard-delete sessions during logout.
- [x] Automatically expire sessions using a MongoDB TTL index.
- [x] Prevent password hashes from appearing in API responses.
- [x] Protect admin API routes with server-side authorization.
- [x] Support an environment-based admin email allowlist.
- [x] Preserve existing MongoDB administrator assignments.
- [x] Add a secure interactive password migration command for legacy users.
- [x] Enable `COOKIE_SECURE=true` in production.
- [x] Add CSRF protection for cookie-authenticated write requests.
- [x] Add login and registration rate limits.
- [ ] Add password-reset rate limits once that flow exists.
- [x] Add temporary account lockouts or progressive delays after repeated
      failed logins.
- [ ] Add password-change functionality.
- [ ] Add password-reset functionality.
- [ ] Invalidate all existing sessions after a password reset or password
      change.
- [ ] Add a "log out from all devices" feature.
- [ ] Add breached-password checks and document password requirements.
- [ ] Record security audit events without recording passwords or raw tokens.

## 3. Contact verification

- [ ] Create and verify an MSG91 account.
- [ ] Complete Indian TRAI DLT registration.
- [ ] Register the SMS sender ID and OTP message template.
- [ ] Store MSG91 credentials in the production secret manager.
- [ ] Implement mobile-number OTP verification.
- [ ] Add OTP expiration, attempt limits, resend cooldowns, and rate limits.
- [ ] Create a Resend account.
- [ ] Verify a transactional email domain or subdomain.
- [ ] Create a sending-only, domain-restricted Resend API key.
- [ ] Store Resend credentials in the production secret manager.
- [ ] Implement email verification links.
- [ ] Add verification-token expiration and one-time usage.
- [ ] Add safe development delivery adapters for SMS and email.

## 4. Configuration and secrets

- [x] Centralize backend configuration.
- [x] Keep environment files and credentials out of Git.
- [x] Validate all required environment variables during startup.
- [x] Refuse to start production with insecure cookie settings.
- [x] Restrict CORS to explicitly configured frontend origins.
- [ ] Use separate development, staging, and production environments.
- [ ] Store production secrets in a managed secret store.
- [x] Require a strong, non-default signing secret in production.
- [ ] Use separate credentials for development and production.
- [ ] Restrict third-party credentials to minimum required permissions.
- [ ] Document credential rotation and incident-response procedures.

## 5. Database reliability and performance

- [x] Add unique indexes for user IDs and email addresses.
- [x] Add a unique sparse index for mobile numbers.
- [x] Add a unique sparse index for hashed session tokens.
- [x] Add a TTL index for session expiration.
- [x] Add a TTL index for expired rate-limit windows.
- [ ] Add indexes for product slug, category, and featured status.
- [ ] Add indexes for order ID, user ID, and creation date.
- [ ] Add an index for review product ID.
- [ ] Add indexes for contact and bulk-inquiry creation dates.
- [ ] Configure MongoDB connection-pool limits and timeouts.
- [ ] Enable managed backups and test restoration.
- [ ] Configure production replication.
- [ ] Define retention policies for personal and operational data.
- [ ] Add monitoring for slow queries and index usage.

## 6. API validation

- [x] Validate and normalize Indian mobile numbers.
- [x] Enforce unique email addresses and mobile numbers.
- [ ] Require positive product prices and stock values.
- [ ] Apply minimum and maximum cart quantities.
- [ ] Restrict review ratings to values from 1 through 5.
- [ ] Validate Indian pincodes and delivery phone numbers.
- [ ] Restrict payment methods to explicit supported values.
- [ ] Restrict order statuses and validate allowed transitions.
- [ ] Apply maximum lengths to contact and inquiry messages.
- [ ] Validate product slug format.
- [ ] Replace unrestricted admin update dictionaries with explicit Pydantic
      request models.
- [ ] Standardize API error response shapes.

## 7. Pagination and query efficiency

- [ ] Add pagination to product listings.
- [ ] Add pagination to customer and administrator order listings.
- [ ] Add pagination to administrator user listings.
- [ ] Add pagination to reviews, contacts, and bulk inquiries.
- [ ] Avoid loading every review when recalculating a product rating.
- [ ] Add query-level performance tests for growing collections.
- [ ] Add caching only after measuring production access patterns.

## 8. Orders and inventory

- [ ] Validate stock before accepting an order.
- [ ] Atomically decrement inventory when an order is placed.
- [ ] Prevent duplicate order submissions with idempotency keys.
- [ ] Validate allowed order-status transitions.
- [ ] Restore inventory when qualifying orders are cancelled.
- [ ] Define behavior for partially available orders.
- [ ] Add server-side price and discount validation.
- [ ] Add tests for concurrent orders against limited stock.

## 9. Payments

- [ ] Select and configure a production payment provider suitable for India.
- [ ] Implement server-side payment-order creation.
- [ ] Implement the currently missing checkout-session endpoint.
- [ ] Verify payment webhook signatures.
- [ ] Make webhook processing idempotent.
- [ ] Never trust payment status supplied by the browser.
- [ ] Handle successful, failed, expired, cancelled, and refunded payments.
- [ ] Reconcile payment records with orders.
- [ ] Add payment and webhook integration tests.

## 10. Background processing

- [ ] Select a background-job system or managed queue.
- [ ] Send verification email through background jobs.
- [ ] Send SMS messages through background jobs.
- [ ] Send order and shipping notifications asynchronously.
- [ ] Move image processing out of request handlers where appropriate.
- [ ] Add retry policies with backoff and dead-letter handling.
- [ ] Ensure background jobs are idempotent.

## 11. Observability and operations

- [ ] Add structured JSON logging.
- [ ] Add request and correlation IDs.
- [ ] Add centralized exception reporting.
- [ ] Add API request latency and error metrics.
- [ ] Add database health and latency metrics.
- [ ] Monitor authentication failures and rate-limit events.
- [ ] Add liveness and readiness endpoints.
- [ ] Configure alerts for elevated errors and failed payments.
- [ ] Ensure logs never contain passwords, API keys, raw session tokens, or
      unnecessary personal data.

## 12. Frontend production readiness

- [x] Prevent the Login button from flashing while authentication is loading.
- [x] Support registration with email and mobile number.
- [x] Support password login with either identifier.
- [ ] Replace or self-host unreliable third-party product images.
- [ ] Add global API error handling and user-friendly retry states.
- [ ] Add loading and empty states across every data-driven screen.
- [ ] Add accessible form validation and error summaries.
- [ ] Evaluate migration from Create React App to Vite.
- [ ] Evaluate server-side rendering only if SEO requirements justify it.
- [ ] Build and serve production assets through a CDN.

## 13. Testing and quality

- [x] Add authentication integration coverage.
- [x] Test registration, session persistence, login, and logout in a browser.
- [x] Test login with both email and mobile number.
- [ ] Fix the product-count fixture mismatch.
- [ ] Implement or remove the test for the missing payment endpoint.
- [ ] Add unit tests for security and normalization helpers.
- [ ] Add authorization tests for every admin endpoint.
- [ ] Add invalid-input and boundary tests.
- [ ] Add concurrent registration and order tests.
- [ ] Add session-expiration tests.
- [ ] Add frontend component tests.
- [ ] Add complete browser tests for registration, cart, checkout, orders, and
      admin access.
- [ ] Add dependency vulnerability and secret scanning.
- [ ] Enforce linting, formatting, type checks, and tests in CI.

## 14. Deployment

- [ ] Select production hosting for the frontend, API, database, and workers.
- [ ] Serve the application exclusively over HTTPS.
- [ ] Run multiple Uvicorn workers or API containers.
- [ ] Add a managed reverse proxy or load balancer.
- [ ] Configure request-body and upload-size limits at the edge.
- [ ] Add automated staging and production deployments.
- [ ] Add health-based deployment checks.
- [ ] Add rollback support.
- [ ] Add database backup verification before risky releases.
- [ ] Document the release and rollback process.

## Recommended execution order

1. Production configuration validation, secure cookies, and restricted CORS
2. CSRF protection and authentication rate limiting
3. Strong request validation
4. Database indexes and pagination
5. Inventory-safe order creation
6. Payment integration
7. Email verification and mobile OTP
8. Logging, metrics, health checks, and alerts
9. Background jobs
10. CI/CD and production deployment
