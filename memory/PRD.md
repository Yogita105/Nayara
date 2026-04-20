# Nayara E-commerce — PRD

## Problem statement
Build a modern, responsive e-commerce website for the Nayara cleaning-products brand (Indian households). Theme: clean, fresh, minimal (white + green/blue). Products: Washing Soap, Washing Powder, Liquid Detergent, Handwash Soap, Handwash Liquid, Bathing Soap, Toilet Cleaner. Pages: Home, Shop, Product Detail, About, Contact, Cart, Checkout. Features: auth, add to cart & wishlist, secure checkout (UPI/Card/COD), reviews, admin panel, "Made in India" and "Factory Direct" highlights.

## User choices
- Auth: Google social login (Emergent-managed)
- Payments: Stripe Checkout (card) + mocked UPI + COD
- Product images: curated Unsplash placeholders
- Admin: basic admin panel included
- Currency: INR (reasonable Indian market prices)

## Architecture
- Frontend: React + Tailwind + shadcn/ui, react-router-dom v7, sonner toasts
- Backend: FastAPI + Motor (MongoDB)
- Auth: Emergent OAuth → session_token cookie (httpOnly, secure, SameSite=None)
- Payments: emergentintegrations.payments.stripe.checkout (INR)
- Collections: users, user_sessions, products, carts, wishlists, orders, reviews, contacts, payment_transactions

## Implemented (2026-02)
- 7 seeded products with INR pricing
- Full storefront: Home, Shop (filters/search/sort), Product Detail (+ reviews), About, Contact, Cart, Checkout, OrderSuccess, Orders, Wishlist
- Google OAuth login + session cookie
- Cart & wishlist (logged-in persisted via API; guest via localStorage)
- Stripe Checkout flow with polling on OrderSuccess
- Mock UPI + COD flows
- Admin dashboard: stats, orders (with status update), products, users, contacts
- Design system: Outfit + DM Sans, mint/deep-green palette, glass nav, badge pills

## Backlog
- P1: Real UPI integration (Razorpay / Stripe UPI)
- P1: Product image upload + admin CRUD UI
- P2: Email order confirmations (Resend / SendGrid)
- P2: Coupons / discount codes
- P2: SEO meta tags per page, sitemap
- P2: Related products carousel on PDP
