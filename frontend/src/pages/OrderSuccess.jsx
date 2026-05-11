import React, { useEffect, useState, useCallback } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { CheckCircle2, Package } from "lucide-react";
import { api, formatINR } from "../lib/api";
import { useCart } from "../context/CartContext";

export default function OrderSuccess() {
  const [params] = useSearchParams();
  const orderId = params.get("order_id");
  const [order, setOrder] = useState(null);
  const { refreshCart } = useCart();

  const loadOrder = useCallback(async () => {
    if (!orderId) return;
    const { data } = await api.get(`/orders/${orderId}`);
    setOrder(data);
  }, [orderId]);

  useEffect(() => { loadOrder(); refreshCart(); }, [loadOrder, refreshCart]);

  if (!order) return <div className="py-20 text-center text-[#64748B]">Loading order...</div>;

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
            <div key={it.product_id} className="flex items-center gap-4 text-sm">
              <img src={it.image} alt="" className="w-14 h-14 rounded-lg object-cover bg-[#F1F5F9]" />
              <div className="flex-1">
                <div className="font-medium">{it.name}</div>
                <div className="text-sm text-[#64748B]">Qty: {it.quantity} · {formatINR(it.price)}</div>
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
