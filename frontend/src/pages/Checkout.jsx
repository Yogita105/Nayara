import React, { useEffect, useState } from "react";
import { useCart } from "../context/CartContext";
import { useAuth } from "../context/AuthContext";
import { useNavigate, Link } from "react-router-dom";
import { formatINR, api, errorMessage, fieldErrors } from "../lib/api";
import { lineKey } from "../lib/variants";
import { shippingFor } from "../lib/shipping";
import { useShipping } from "../context/BusinessContext";
import useAddresses from "../hooks/useAddresses";
import ShippingLine from "../components/ShippingLine";
import AddressFields from "../components/AddressFields";
import { EMPTY_ADDRESS, deliveryPartOf, findProblems, oneLine, usualAddress } from "../lib/addresses";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { ErrorSummary } from "../components/FormErrors";
import ProductImage from "../components/ProductImage";
import { Package, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

export default function Checkout() {
  const { cart, cartTotal, cartCount, clearCart } = useCart();
  const shippingSettings = useShipping();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  // Cash on Delivery is the only method the shop can actually collect today,
  // so it is stated rather than chosen. When online payment arrives this
  // becomes a choice again.
  const payment = "cod";
  // Kept for the whole visit so a retried submission cannot create a second order.
  const [idempotencyKey] = useState(() =>
    (window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`)
  );
  const [address, setAddress] = useState({
    ...EMPTY_ADDRESS,
    full_name: user?.name || "",
  });
  const [error, setError] = useState("");
  const [fields, setFields] = useState({});
  // Which saved address is in use, or "new" while typing one that is not
  // saved yet. Null until the book has been read, so a book arriving late
  // cannot overwrite something already being typed.
  const [chosen, setChosen] = useState(null);
  const [label, setLabel] = useState("");
  const book = useAddresses();
  const { addresses } = book;

  useEffect(() => {
    if (chosen !== null) return;
    const usual = usualAddress(addresses);
    if (!usual) return;
    setChosen(usual.address_id);
    setAddress(deliveryPartOf(usual));
  }, [addresses, chosen]);

  const chooseSaved = (saved) => {
    setChosen(saved.address_id);
    setAddress(deliveryPartOf(saved));
    setFields({});
  };

  const chooseNewAddress = () => {
    setChosen("new");
    setAddress({ ...EMPTY_ADDRESS, full_name: user?.name || "" });
    setLabel("");
    setFields({});
  };

  const shipping = shippingFor(cartTotal, shippingSettings, cartCount);
  const grand = cartTotal + shipping;

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

  const submit = async (e) => {
    e.preventDefault();
    if (cart.length === 0) { toast.error("Cart is empty"); return; }

    const problems = findProblems(address);
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

      // The order is placed, so keeping the address is a convenience that must
      // never cost the customer their order. A full book or a failed save is
      // silently accepted rather than turned into an error about something
      // that already succeeded.
      if (chosen === "new" || addresses.length === 0) {
        await book.save({ ...deliveryPartOf(address), label, is_default: addresses.length === 0 });
      }

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
            {addresses.length > 0 && (
              <ul className="space-y-3 mb-5" data-testid="saved-addresses">
                {addresses.map((saved) => (
                  <li key={saved.address_id}>
                    <label
                      className={`flex items-start gap-3 rounded-xl border p-4 cursor-pointer ${
                        chosen === saved.address_id
                          ? "border-[var(--nayara-primary)] bg-[#FBEEE4]"
                          : "border-[var(--nayara-border)]"
                      }`}
                    >
                      <input
                        type="radio"
                        name="saved-address"
                        className="mt-1"
                        checked={chosen === saved.address_id}
                        onChange={() => chooseSaved(saved)}
                        data-testid={`choose-address-${saved.address_id}`}
                      />
                      <span className="min-w-0">
                        <span className="font-medium block">
                          {saved.label || saved.full_name}
                        </span>
                        <span className="text-sm text-[#64748B] block">{saved.full_name}</span>
                        <span className="text-sm text-[#64748B] block">{oneLine(saved)}</span>
                        <span className="text-sm text-[#64748B] block">{saved.phone}</span>
                      </span>
                    </label>
                  </li>
                ))}
                <li>
                  <label
                    className={`flex items-center gap-3 rounded-xl border p-4 cursor-pointer ${
                      chosen === "new"
                        ? "border-[var(--nayara-primary)] bg-[#FBEEE4]"
                        : "border-[var(--nayara-border)]"
                    }`}
                  >
                    <input
                      type="radio"
                      name="saved-address"
                      checked={chosen === "new"}
                      onChange={chooseNewAddress}
                      data-testid="choose-address-new"
                    />
                    <span className="font-medium">Deliver somewhere else</span>
                  </label>
                </li>
              </ul>
            )}

            {(chosen === "new" || addresses.length === 0) && (
              <>
                {addresses.length > 0 && (
                  <div className="space-y-2 mb-4">
                    <Label htmlFor="label" className="text-xs font-bold uppercase tracking-[0.15em]">
                      Name this address
                    </Label>
                    <Input
                      id="label"
                      value={label}
                      onChange={(event) => setLabel(event.target.value)}
                      maxLength={30}
                      placeholder="Home, Office, Mum's"
                      data-testid="addr-label"
                    />
                  </div>
                )}
                <AddressFields address={address} onChange={updateAddress} fields={fields} />
                <p className="text-sm text-[#64748B] mt-3" data-testid="address-will-be-saved">
                  This address will be saved for next time. You can change or
                  remove it from{" "}
                  <Link to="/account" className="text-[var(--nayara-primary)] underline">
                    your account
                  </Link>.
                </p>
              </>
            )}
          </section>

          <section className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6">
            <h2 className="font-heading text-lg font-semibold mb-5">Payment Method</h2>
            <div
              className="flex items-center gap-3 rounded-xl border border-[var(--nayara-primary)] bg-[#FBEEE4] p-4"
              data-testid="payment-options"
            >
              <Package className="w-5 h-5" />
              <div>
                <div className="font-medium" data-testid="payment-cod">Cash on Delivery</div>
                <div className="text-sm text-[#64748B]">
                  Pay the courier when your order arrives.
                </div>
              </div>
            </div>
            <p className="mt-3 text-sm text-[#64748B]">
              Paying online is not available yet.
            </p>
          </section>
        </div>

        <aside className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6 h-fit sticky top-24" data-testid="checkout-summary">
          <h3 className="font-heading text-lg font-semibold mb-4">Order Summary ({cartCount})</h3>
          <div className="space-y-3 max-h-64 overflow-y-auto mb-4">
            {cart.map((c) => (
              <div key={lineKey(c)} className="flex items-center gap-3 text-sm">
                <ProductImage src={c.image} alt={c.name} width={120} className="w-12 h-12 rounded-lg object-cover bg-[#F1F5F9]" />
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
            <ShippingLine
              subtotal={cartTotal}
              shipping={shipping}
              settings={shippingSettings}
              testId="checkout-shipping"
            />
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
