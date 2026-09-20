import React, { useState } from "react";
import { useCart } from "../context/CartContext";
import { useAuth } from "../context/AuthContext";
import { useNavigate } from "react-router-dom";
import { formatINR, api, errorMessage, fieldErrors } from "../lib/api";
import { lineKey } from "../lib/variants";
import { Input } from "../components/ui/input";
import { RadioGroup, RadioGroupItem } from "../components/ui/radio-group";
import { Label } from "../components/ui/label";
import { ErrorSummary, FieldError, describedBy } from "../components/FormErrors";
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

  const [error, setError] = useState("");
  const [fields, setFields] = useState({});

  const updateAddress = (name) => (event) => {
    const { value } = event.target;
    setAddress((current) => ({ ...current, [name]: value }));
    setFields((current) => {
      if (!current[name]) return current;
      const next = { ...current };
      delete next[name];
      return next;
    });
  };

  const findProblems = () => {
    const problems = {};
    if (address.full_name.trim().length < 2) {
      problems.full_name = "Enter the name for this delivery.";
    }
    if (!address.phone.trim()) problems.phone = "Enter a phone number for the courier.";
    if (!address.line1.trim()) problems.line1 = "Enter the street address.";
    if (!address.city.trim()) problems.city = "Enter the city.";
    if (!address.state.trim()) problems.state = "Enter the state.";
    if (!address.pincode.trim()) problems.pincode = "Enter the pincode.";
    return problems;
  };

  const submit = async (e) => {
    e.preventDefault();
    if (cart.length === 0) { toast.error("Cart is empty"); return; }

    const problems = findProblems();
    if (Object.keys(problems).length > 0) {
      setError("");
      setFields(problems);
      return;
    }

    setSubmitting(true);
    setError("");
    setFields({});
    try {
      const { data: order } = await api.post("/orders", {
        items: cart.map((c) => ({
          product_id: c.product_id,
          variant_id: c.variant_id,
          quantity: c.quantity,
        })),
        address,
        payment_method: payment,
      }, { headers: { "Idempotency-Key": idempotencyKey } });

      await clearCart();
      toast.success("Order placed successfully!");
      navigate(`/order-success?order_id=${order.order_id}`);
    } catch (err) {
      const message = errorMessage(err, "Could not place the order");
      setError(message);
      setFields(fieldErrors(err));
      toast.error(message);
    } finally { setSubmitting(false); }
  };

  if (cart.length === 0) {
    return <div className="max-w-4xl mx-auto px-6 py-20 text-center text-[#64748B]">Your cart is empty.</div>;
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-10" data-testid="checkout-page">
      <h1 className="font-heading text-2xl md:text-3xl font-medium tracking-tight mb-8">Checkout</h1>
      <form onSubmit={submit} className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-10" noValidate>
        <div className="space-y-8">
          <section className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6">
            <h2 className="font-heading text-lg font-semibold mb-5">Shipping Address</h2>
            <div className="mb-4">
              <ErrorSummary message={error} fields={fields} />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <Label htmlFor="full_name" className="text-xs font-bold uppercase tracking-[0.15em]" required>Full name</Label>
                <Input
                  id="full_name"
                  value={address.full_name}
                  onChange={updateAddress("full_name")} required
                  data-testid="addr-name"
                  {...describedBy("full_name", { error: Boolean(fields.full_name) })}
                />
                <FieldError name="full_name">{fields.full_name}</FieldError>
              </div>
              <div>
                <Label htmlFor="phone" className="text-xs font-bold uppercase tracking-[0.15em]" required>Phone</Label>
                <Input
                  id="phone"
                  value={address.phone}
                  onChange={updateAddress("phone")} required
                  data-testid="addr-phone"
                  {...describedBy("phone", { error: Boolean(fields.phone) })}
                />
                <FieldError name="phone">{fields.phone}</FieldError>
              </div>
              <div>
                <Label htmlFor="pincode" className="text-xs font-bold uppercase tracking-[0.15em]" required>Pincode</Label>
                <Input
                  id="pincode"
                  value={address.pincode}
                  onChange={updateAddress("pincode")} required
                  data-testid="addr-pincode"
                  {...describedBy("pincode", { error: Boolean(fields.pincode) })}
                />
                <FieldError name="pincode">{fields.pincode}</FieldError>
              </div>
              <div className="md:col-span-2">
                <Label htmlFor="line1" className="text-xs font-bold uppercase tracking-[0.15em]" required>Address line 1</Label>
                <Input
                  id="line1"
                  value={address.line1}
                  onChange={updateAddress("line1")} required
                  data-testid="addr-line1"
                  {...describedBy("line1", { error: Boolean(fields.line1) })}
                />
                <FieldError name="line1">{fields.line1}</FieldError>
              </div>
              <div className="md:col-span-2">
                <Label htmlFor="line2" className="text-xs font-bold uppercase tracking-[0.15em]">Address line 2</Label>
                <Input
                  id="line2"
                  value={address.line2}
                  onChange={updateAddress("line2")}
                  data-testid="addr-line2"
                  {...describedBy("line2", { error: Boolean(fields.line2) })}
                />
                <FieldError name="line2">{fields.line2}</FieldError>
              </div>
              <div>
                <Label htmlFor="city" className="text-xs font-bold uppercase tracking-[0.15em]" required>City</Label>
                <Input
                  id="city"
                  value={address.city}
                  onChange={updateAddress("city")} required
                  data-testid="addr-city"
                  {...describedBy("city", { error: Boolean(fields.city) })}
                />
                <FieldError name="city">{fields.city}</FieldError>
              </div>
              <div>
                <Label htmlFor="state" className="text-xs font-bold uppercase tracking-[0.15em]" required>State</Label>
                <Input
                  id="state"
                  value={address.state}
                  onChange={updateAddress("state")} required
                  data-testid="addr-state"
                  {...describedBy("state", { error: Boolean(fields.state) })}
                />
                <FieldError name="state">{fields.state}</FieldError>
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
              <div key={lineKey(c)} className="flex items-center gap-3 text-sm">
                <ProductImage src={c.image} alt={c.name} className="w-12 h-12 rounded-lg object-cover bg-[#F1F5F9]" />
                <div className="flex-1 min-w-0">
                  <div className="truncate">{c.name}</div>
                  <div className="text-xs text-[#64748B]">
                    {c.variant_label ? `${c.variant_label} · ` : ""}× {c.quantity}
                  </div>
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
