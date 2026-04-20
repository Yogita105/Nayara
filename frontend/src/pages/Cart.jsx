import React from "react";
import { Link } from "react-router-dom";
import { useCart } from "../context/CartContext";
import { useAuth } from "../context/AuthContext";
import { formatINR } from "../lib/api";
import { Minus, Plus, Trash2, ShoppingBag } from "lucide-react";

export default function Cart() {
  const { cart, updateQuantity, removeFromCart, cartTotal, cartCount } = useCart();
  const { user } = useAuth();
  const shipping = cartTotal >= 499 ? 0 : cartCount > 0 ? 49 : 0;
  const grand = cartTotal + shipping;

  if (cart.length === 0) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-20 text-center" data-testid="cart-empty">
        <ShoppingBag className="w-16 h-16 mx-auto text-[#64748B] mb-5" />
        <h1 className="font-heading text-3xl font-medium">Your cart is empty</h1>
        <p className="text-[#64748B] mt-2">Add a few of our bestsellers to get started.</p>
        <Link to="/shop" className="nayara-btn mt-6" data-testid="cart-shop-link">Shop Now</Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-10" data-testid="cart-page">
      <h1 className="font-heading text-3xl md:text-4xl font-medium tracking-tight mb-8">Your Cart ({cartCount})</h1>
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-10">
        <div className="space-y-4">
          {cart.map((item) => (
            <div key={item.product_id} className="rounded-2xl border border-[var(--nayara-border)] bg-white p-4 flex gap-4 items-center" data-testid={`cart-item-${item.product_id}`}>
              <img src={item.image} alt={item.name} className="w-24 h-24 rounded-xl object-cover bg-[#F1F5F9]" />
              <div className="flex-1 min-w-0">
                <h3 className="font-heading font-medium">{item.name}</h3>
                <p className="text-sm text-[#64748B] mt-1">{formatINR(item.price)}</p>
                <div className="mt-3 flex items-center gap-3">
                  <div className="flex items-center border border-[var(--nayara-border)] rounded-full">
                    <button onClick={() => updateQuantity(item.product_id, Math.max(1, item.quantity - 1))} className="px-3 h-9" data-testid={`cart-dec-${item.product_id}`}><Minus className="w-3 h-3" /></button>
                    <span className="w-7 text-center text-sm font-semibold" data-testid={`cart-qty-${item.product_id}`}>{item.quantity}</span>
                    <button onClick={() => updateQuantity(item.product_id, item.quantity + 1)} className="px-3 h-9" data-testid={`cart-inc-${item.product_id}`}><Plus className="w-3 h-3" /></button>
                  </div>
                  <button onClick={() => removeFromCart(item.product_id)} className="text-sm text-red-500 flex items-center gap-1" data-testid={`cart-remove-${item.product_id}`}>
                    <Trash2 className="w-4 h-4" /> Remove
                  </button>
                </div>
              </div>
              <div className="font-heading text-lg font-semibold">{formatINR(item.price * item.quantity)}</div>
            </div>
          ))}
        </div>

        <aside className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6 h-fit" data-testid="cart-summary">
          <h3 className="font-heading text-xl font-semibold mb-4">Order Summary</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-[#64748B]">Subtotal</span><span>{formatINR(cartTotal)}</span></div>
            <div className="flex justify-between"><span className="text-[#64748B]">Shipping</span><span>{shipping === 0 ? "Free" : formatINR(shipping)}</span></div>
            {cartTotal < 499 && <div className="text-xs text-[var(--nayara-primary)]">Add {formatINR(499 - cartTotal)} more for free shipping</div>}
          </div>
          <div className="border-t border-[var(--nayara-border)] my-4" />
          <div className="flex justify-between font-heading text-lg font-semibold"><span>Total</span><span>{formatINR(grand)}</span></div>
          <Link
            to={user ? "/checkout" : "/login?redirect=/checkout"}
            className="nayara-btn w-full mt-6"
            data-testid="cart-checkout-btn"
          >
            Proceed to Checkout
          </Link>
          {!user && <p className="text-xs text-[#64748B] mt-3 text-center">You'll need to sign in to complete checkout.</p>}
        </aside>
      </div>
    </div>
  );
}
