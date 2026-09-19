import React, { useState } from "react";
import { useCart } from "../context/CartContext";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";
import { formatINR, api } from "../lib/api";
import { Input } from "../components/ui/input";
import { RadioGroup, RadioGroupItem } from "../components/ui/radio-group";
import { Label } from "../components/ui/label";
import ProductImage from "../components/ProductImage";
import { Smartphone, Package, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

export default function Checkout() {
  const { cart, cartTotal, cartCount, clearCart } = useCart();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [payment, setPayment] = useState("upi");
  // Kept for the whole visit so a retried submission cannot create a second order.
  const [idempotencyKey] = useState(() =>
    (window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`)
  );
  const [address, setAddress] = useState({
    full_name: user?.name || "",
    phone: "",
    line1: "",
    line2: "",
    city: "",
    state: "",
    pincode: "",
  });

  const shipping = cartTotal >= 499 ? 0 : 49;
  const grand = cartTotal + shipping;

  const submit = async (e) => {
    e.preventDefault();
    if (cart.length === 0) { toast.error("Cart is empty"); return; }
    setSubmitting(true);
    try {
      const { data: order } = await api.post("/orders", {
        items: cart.map((c) => ({ product_id: c.product_id, quantity: c.quantity })),
        address,
        payment_method: payment,
      }, { headers: { "Idempotency-Key": idempotencyKey } });

      await clearCart();
      toast.success("Order placed successfully!");
      navigate(`/order-success?order_id=${order.order_id}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Could not place order");
    } finally { setSubmitting(false); }
  };

  if (cart.length === 0) {
    return <div className="max-w-4xl mx-auto px-6 py-20 text-center text-[#64748B]">Your cart is empty.</div>;
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-10" data-testid="checkout-page">
      <h1 className="font-heading text-2xl md:text-3xl font-medium tracking-tight mb-8">Checkout</h1>
      <form onSubmit={submit} className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-10">
        <div className="space-y-8">
          <section className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6">
            <h2 className="font-heading text-lg font-semibold mb-5">Shipping Address</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <Label className="text-xs font-bold uppercase tracking-[0.15em]" required>Full name</Label>
                <Input value={address.full_name} onChange={(e) => setAddress({ ...address, full_name: e.target.value })} required data-testid="addr-name" />
              </div>
              <div>
                <Label className="text-xs font-bold uppercase tracking-[0.15em]" required>Phone</Label>
                <Input value={address.phone} onChange={(e) => setAddress({ ...address, phone: e.target.value })} required data-testid="addr-phone" />
              </div>
              <div>
                <Label className="text-xs font-bold uppercase tracking-[0.15em]" required>Pincode</Label>
                <Input value={address.pincode} onChange={(e) => setAddress({ ...address, pincode: e.target.value })} required data-testid="addr-pincode" />
              </div>
              <div className="md:col-span-2">
                <Label className="text-xs font-bold uppercase tracking-[0.15em]" required>Address line 1</Label>
                <Input value={address.line1} onChange={(e) => setAddress({ ...address, line1: e.target.value })} required data-testid="addr-line1" />
              </div>
              <div className="md:col-span-2">
                <Label className="text-xs font-bold uppercase tracking-[0.15em]">Address line 2</Label>
                <Input value={address.line2} onChange={(e) => setAddress({ ...address, line2: e.target.value })} data-testid="addr-line2" />
              </div>
              <div>
                <Label className="text-xs font-bold uppercase tracking-[0.15em]" required>City</Label>
                <Input value={address.city} onChange={(e) => setAddress({ ...address, city: e.target.value })} required data-testid="addr-city" />
              </div>
              <div>
                <Label className="text-xs font-bold uppercase tracking-[0.15em]" required>State</Label>
                <Input value={address.state} onChange={(e) => setAddress({ ...address, state: e.target.value })} required data-testid="addr-state" />
              </div>
            </div>
          </section>

          <section className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6">
            <h2 className="font-heading text-lg font-semibold mb-5">Payment Method</h2>
            <RadioGroup value={payment} onValueChange={setPayment} className="space-y-3" data-testid="payment-options">
              <label className={`flex items-center gap-3 rounded-xl border p-4 cursor-pointer ${payment === "upi" ? "border-[var(--nayara-primary)] bg-[#FBEEE4]" : "border-[var(--nayara-border)]"}`}>
                <RadioGroupItem value="upi" id="pay-upi" data-testid="payment-upi" />
                <Smartphone className="w-5 h-5" />
                <div>
                  <div className="font-medium">UPI (Demo)</div>
                  <div className="text-sm text-[#64748B]">Google Pay, PhonePe, Paytm</div>
                </div>
              </label>
              <label className={`flex items-center gap-3 rounded-xl border p-4 cursor-pointer ${payment === "cod" ? "border-[var(--nayara-primary)] bg-[#FBEEE4]" : "border-[var(--nayara-border)]"}`}>
                <RadioGroupItem value="cod" id="pay-cod" data-testid="payment-cod" />
                <Package className="w-5 h-5" />
                <div>
                  <div className="font-medium">Cash on Delivery</div>
                  <div className="text-sm text-[#64748B]">Pay when you receive</div>
                </div>
              </label>
            </RadioGroup>
          </section>
        </div>

        <aside className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6 h-fit sticky top-24" data-testid="checkout-summary">
          <h3 className="font-heading text-lg font-semibold mb-4">Order Summary ({cartCount})</h3>
          <div className="space-y-3 max-h-64 overflow-y-auto mb-4">
            {cart.map((c) => (
              <div key={c.product_id} className="flex items-center gap-3 text-sm">
                <ProductImage src={c.image} alt={c.name} className="w-12 h-12 rounded-lg object-cover bg-[#F1F5F9]" />
                <div className="flex-1 min-w-0">
                  <div className="truncate">{c.name}</div>
                  <div className="text-xs text-[#64748B]">× {c.quantity}</div>
                </div>
                <div className="font-medium">{formatINR(c.price * c.quantity)}</div>
              </div>
            ))}
          </div>
          <div className="space-y-2 text-sm border-t border-[var(--nayara-border)] pt-4">
            <div className="flex justify-between"><span className="text-[#64748B]">Subtotal</span><span>{formatINR(cartTotal)}</span></div>
            <div className="flex justify-between"><span className="text-[#64748B]">Shipping</span><span>{shipping === 0 ? "Free" : formatINR(shipping)}</span></div>
            <div className="flex justify-between font-heading text-lg font-semibold pt-2 border-t border-[var(--nayara-border)]"><span>Total</span><span>{formatINR(grand)}</span></div>
          </div>
          <button type="submit" disabled={submitting} className="nayara-btn w-full mt-5" data-testid="place-order-btn">
            {submitting ? "Processing..." : `Place Order · ${formatINR(grand)}`}
          </button>
          <div className="mt-3 flex items-center gap-2 text-xs text-[#64748B]">
            <ShieldCheck className="w-3.5 h-3.5" /> Secure encrypted checkout
          </div>
        </aside>
      </form>
    </div>
  );
}
