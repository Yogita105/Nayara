import React, { useEffect } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { CheckCircle2, Package } from "lucide-react";
import { api, formatINR } from "../lib/api";
import useAsyncData from "../hooks/useAsyncData";
import { ErrorPanel, LoadingPanel } from "../components/DataState";
import ProductImage from "../components/ProductImage";
import { lineKey, lineName } from "../lib/variants";
import { useCart } from "../context/CartContext";

export default function OrderSuccess() {
  const [params] = useSearchParams();
  const orderId = params.get("order_id");
  const { refreshCart } = useCart();

  const { data: order, loading, error, reload } = useAsyncData(
    async () => {
      if (!orderId) return null;
      const { data } = await api.get(`/orders/${orderId}`);
      return data;
    },
    [orderId],
    "We could not load this order."
  );

  useEffect(() => { refreshCart(); }, [refreshCart]);

  if (loading) return <LoadingPanel label="Loading your order..." />;
  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-16">
        <ErrorPanel message={error} onRetry={reload} />
        <p className="text-center text-sm text-[#64748B] mt-4">
          Your order may still have been placed. Check{" "}
          <Link to="/orders" className="text-[var(--nayara-primary)] underline">
            My Orders
          </Link>.
        </p>
      </div>
    );
  }
  if (!order) return null;

  return (
    <div className="max-w-3xl mx-auto px-6 py-16 text-center" data-testid="order-success-page">
      <div className="mx-auto w-20 h-20 rounded-full flex items-center justify-center text-white mb-6" style={{ background: "var(--nayara-primary)" }}>
        <CheckCircle2 className="w-10 h-10" />
      </div>
      <h1 className="font-heading text-2xl md:text-3xl font-medium tracking-tight">Thank you for your order!</h1>
      <p className="mt-3 text-[#64748B]">Order #{order.order_id}</p>

      <div className="mt-10 rounded-2xl border border-[var(--nayara-border)] bg-white p-6 text-left">
        <h3 className="font-heading font-semibold mb-4 flex items-center gap-2"><Package className="w-4 h-4" /> Items ordered</h3>
        <div className="space-y-3">
          {order.items.map((it) => (
            <div key={lineKey(it)} className="flex items-center gap-4 text-sm">
              <ProductImage src={it.image} alt={lineName(it)} width={150} className="w-14 h-14 rounded-lg object-cover bg-[#F1F5F9]" />
              <div className="flex-1">
                <div className="font-medium">{it.name}</div>
                <div className="text-sm text-[#64748B]">
                  {it.variant_label ? `${it.variant_label} · ` : ""}Qty: {it.quantity} · {formatINR(it.price)}
                </div>
              </div>
              <div className="font-semibold">{formatINR(it.price * it.quantity)}</div>
            </div>
          ))}
        </div>
        <div className="border-t border-[var(--nayara-border)] mt-5 pt-4 flex justify-between font-heading font-semibold">
          <span>Total</span><span>{formatINR(order.total)}</span>
        </div>
      </div>

      <div className="mt-8 flex gap-3 justify-center">
        <Link to="/orders" className="nayara-btn-outline" data-testid="view-orders-btn">View Orders</Link>
        <Link to="/shop" className="nayara-btn" data-testid="continue-shopping-btn">Continue Shopping</Link>
      </div>
    </div>
  );
}
