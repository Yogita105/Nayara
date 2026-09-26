# Nayara E-commerce — PRD

## Problem statement
Build a modern, responsive e-commerce website for the Nayara cleaning-products brand (Indian households). Theme: clean, fresh, minimal (white + green/blue). Products: Washing Soap, Washing Powder, Liquid Detergent, Handwash Soap, Handwash Liquid, Bathing Soap, Toilet Cleaner. Pages: Home, Shop, Product Detail, About, Contact, Cart, Checkout. Features: auth, add to cart & wishlist, secure checkout (UPI/Card/COD), reviews, admin panel, "Made in India" and "Factory Direct" highlights.

> The brief above is the original one and is kept as written. The palette settled on
> terracotta rather than green/blue as the design came together; what was actually
> built is described under **Implemented**.

## User choices
- Auth: mobile number or email with a password, managed by this application
- Payments: **not yet integrated.** Checkout offers a demo UPI flow and cash on
  delivery; no money moves. See section 9 of `PRODUCTION-READINESS.md`.
- Product images: curated Unsplash placeholders, pending the brand's own photography
- Admin: basic admin panel included
- Currency: INR (reasonable Indian market prices)

## Architecture
- Frontend: React + Tailwind + shadcn/ui, react-router-dom v7, sonner toasts
- Backend: FastAPI + Motor (MongoDB), split into routers under `backend/app/`
- Auth: password sign-in issuing a session token, stored as a SHA-256 hash and sent
  in an HttpOnly cookie; CSRF protection on cookie-authenticated writes
- Collections: users, user_sessions, products, carts, wishlists, orders, reviews,
  contacts, bulk_inquiries, audit_events, files, rate_limits, order_claims

## Implemented
- 7 seeded products, each sold in one or more **variants** — a weight, a volume or a
  colour — with price and stock belonging to the variant
- Full storefront: Home, Shop (filters/search/sort), Product Detail (+ reviews and a
  variant selector), About, Contact, Cart, Checkout, OrderSuccess, Orders, Wishlist
- Sign-up and sign-in by mobile or email, with rate limiting and session expiry
- Cart & wishlist (logged-in persisted via API; guest via localStorage)
- Orders with stock reserved by a single conditional update, so simultaneous shoppers
  cannot oversell the last unit; idempotent submission; cancellation returns stock
- Demo UPI and cash-on-delivery flows
- Admin: dashboard stats, orders with status transitions, product and variant editing,
  image upload, users, contacts, bulk inquiries
- Design system: Outfit + DM Sans, terracotta accent (`#D97548`) on white

## Backlog
The working list is `PRODUCTION-READINESS.md`, which tracks what still stands between
this and a shop that can take real money. The largest open items:

- Payments: choose a provider, create orders server-side, verify webhooks
- Deployment: staging, automated deploys, a rehearsed rollback
- Email and SMS: order confirmations, mobile verification
- Reviewing uploaded images before they publish
- The brand's own product photography, replacing the placeholders
