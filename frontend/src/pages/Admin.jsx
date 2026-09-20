import React, { useState } from "react";
import { Routes, Route, Link, useLocation } from "react-router-dom";
import { api, errorMessage, formatINR } from "../lib/api";
import useAsyncData from "../hooks/useAsyncData";
import usePagedData from "../hooks/usePagedData";
import Pagination from "../components/Pagination";
import { EmptyPanel, ErrorPanel, LoadingPanel, TableStateRow } from "../components/DataState";
import ProductImage from "../components/ProductImage";
import RequiredMark from "../components/RequiredMark";
import { LayoutDashboard, Package, Users, IndianRupee, ShoppingBag, MessageSquare, Briefcase } from "lucide-react";
import { toast } from "sonner";

const navs = [
  { to: "/admin", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/admin/orders", label: "Orders", icon: ShoppingBag },
  { to: "/admin/products", label: "Products", icon: Package },
  { to: "/admin/bulk", label: "Bulk Inquiries", icon: Briefcase },
  { to: "/admin/messages", label: "Messages", icon: MessageSquare },
  { to: "/admin/users", label: "Users", icon: Users },
];

function Dashboard() {
  const { data: stats, loading, error, reload } = useAsyncData(
    async () => (await api.get("/admin/stats")).data,
    [],
    "Dashboard figures could not be loaded."
  );
  if (loading) return <LoadingPanel label="Loading dashboard..." />;
  if (error) return <ErrorPanel message={error} onRetry={reload} />;
  if (!stats) return null;
  const cards = [
    { label: "Revenue", value: formatINR(stats.revenue), icon: IndianRupee, color: "var(--nayara-primary)" },
    { label: "Orders", value: stats.total_orders, icon: ShoppingBag, color: "var(--nayara-secondary)" },
    { label: "Products", value: stats.total_products, icon: Package, color: "#7FB4D9" },
    { label: "Bulk Inquiries", value: stats.total_bulk_inquiries || 0, icon: Briefcase, color: "var(--nayara-primary-hover)" },
    { label: "Messages", value: stats.total_messages || 0, icon: MessageSquare, color: "#F59E0B" },
    { label: "Users", value: stats.total_users, icon: Users, color: "#64748B" },
  ];
  return (
    <div data-testid="admin-dashboard">
      <h1 className="font-heading text-3xl font-medium mb-8 tracking-tight">Dashboard</h1>
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-5">
        {cards.map((c) => (
          <div key={c.label} className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6" data-testid={`stat-${c.label.toLowerCase()}`}>
            <div className="w-10 h-10 rounded-full text-white flex items-center justify-center mb-3" style={{ background: c.color }}>
              <c.icon className="w-5 h-5" />
            </div>
            <div className="text-xs uppercase tracking-[0.2em] font-bold text-[#64748B]">{c.label}</div>
            <div className="font-heading text-2xl font-semibold mt-1">{c.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Mirrors the rules the API enforces, so the dropdown never offers a change
// that would be rejected. Delivered and cancelled orders are final.
const NEXT_ORDER_STATUSES = {
  placed: ["processing", "shipped", "cancelled"],
  processing: ["shipped", "cancelled"],
  shipped: ["delivered", "cancelled"],
  delivered: [],
  cancelled: [],
};

function OrdersAdmin() {
  const {
    items: orders, total, loading, error, reload,
    page, pageSize, pageCount, setPage,
  } = usePagedData("/admin/orders", {
    pageSize: 25,
    fallbackMessage: "Orders could not be loaded.",
  });
  const load = reload;
  const update = async (id, status) => {
    try {
      await api.put(`/admin/orders/${id}`, { status });
      load();
    } catch (error) {
      toast.error(errorMessage(error, "Could not update the order"));
      load();
    }
  };
  return (
    <div data-testid="admin-orders">
      <h1 className="font-heading text-3xl font-medium mb-8 tracking-tight">Orders</h1>
      <div className="rounded-2xl border border-[var(--nayara-border)] bg-white overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-[#FFFFFF] text-[#64748B] text-left">
            <tr>
              <th className="px-4 py-3">Order</th><th className="px-4 py-3">Customer</th>
              <th className="px-4 py-3">Total</th><th className="px-4 py-3">Pay</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody>
            <TableStateRow
              columns={5}
              loading={loading}
              error={error}
              onRetry={reload}
              emptyMessage={orders.length === 0 ? "No orders yet." : null}
            />
            {orders.map((o) => (
              <tr key={o.order_id} className="border-t border-[var(--nayara-border)]">
                <td className="px-4 py-3 font-mono text-xs">{o.order_id}</td>
                <td className="px-4 py-3">{o.user_mobile || o.user_email || "—"}</td>
                <td className="px-4 py-3">{formatINR(o.total)}</td>
                <td className="px-4 py-3"><span className="badge-soft px-2 py-1 rounded-full text-xs">{o.payment_method}</span></td>
                <td className="px-4 py-3">
                  <select
                    value={o.status}
                    onChange={(e) => update(o.order_id, e.target.value)}
                    disabled={(NEXT_ORDER_STATUSES[o.status] || []).length === 0}
                    className="border border-[var(--nayara-border)] rounded px-2 py-1 text-xs disabled:opacity-60"
                    title={
                      (NEXT_ORDER_STATUSES[o.status] || []).length === 0
                        ? "This order has reached its final state"
                        : undefined
                    }
                  >
                    {[o.status, ...(NEXT_ORDER_STATUSES[o.status] || [])].map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pagination
        page={page}
        pageSize={pageSize}
        pageCount={pageCount}
        total={total}
        onPageChange={setPage}
        noun="orders"
      />
    </div>
  );
}

function ProductsAdmin() {
  const [editing, setEditing] = useState(null); // null | "new" | product
  const { data, loading, error, reload } = useAsyncData(
    async () => (await api.get("/products")).data,
    [],
    "Products could not be loaded."
  );
  const products = data || [];
  const load = reload;

  const onDelete = async (id) => {
    if (!window.confirm("Delete this product?")) return;
    try {
      await api.delete(`/products/${id}`);
      toast.success("Product deleted");
    } catch (failure) {
      toast.error(errorMessage(failure, "Could not delete the product"));
    }
    load();
  };

  return (
    <div data-testid="admin-products">
      <div className="flex items-center justify-between mb-8">
        <h1 className="font-heading text-3xl font-medium tracking-tight">Products</h1>
        <button onClick={() => setEditing("new")} className="nayara-btn" data-testid="admin-new-product-btn">+ New Product</button>
      </div>
      {loading ? (
        <LoadingPanel label="Loading products..." />
      ) : error ? (
        <ErrorPanel message={error} onRetry={reload} />
      ) : products.length === 0 ? (
        <EmptyPanel
          icon={Package}
          message="No products yet. Use “+ New Product” to add your first one."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {products.map((p) => (
            <div key={p.product_id} className="rounded-2xl border border-[var(--nayara-border)] bg-white p-4 flex gap-4" data-testid={`admin-product-${p.product_id}`}>
              <ProductImage src={p.image} alt={p.name} className="w-20 h-20 rounded-lg object-cover bg-[#F1F5F9]" />
              <div className="flex-1 min-w-0">
                <h3 className="font-heading font-medium text-sm truncate">{p.name}</h3>
                <div className="text-xs text-[#64748B] mt-1">Stock: {p.stock} · {p.category}</div>
                <div className="font-heading font-semibold mt-2">{formatINR(p.price)}</div>
                <div className="flex gap-2 mt-2">
                  <button onClick={() => setEditing(p)} className="text-xs px-3 py-1 rounded-md border border-[var(--nayara-border)] hover:bg-[#FBEEE4]" data-testid={`edit-product-${p.product_id}`}>Edit</button>
                  <button onClick={() => onDelete(p.product_id)} className="text-xs px-3 py-1 rounded-md border border-red-200 text-red-600 hover:bg-red-50" data-testid={`delete-product-${p.product_id}`}>Delete</button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      {editing && <ProductEditor initial={editing === "new" ? null : editing} onClose={() => { setEditing(null); load(); }} />}
    </div>
  );
}

function ProductEditor({ initial, onClose }) {
  const [form, setForm] = useState(initial || {
    name: "", slug: "", category: "laundry",
    short_description: "", description: "",
    price: 0, mrp: 0, stock: 100, image: "",
    badges: ["Made in India"], featured: false,
  });
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);

  const onUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) { toast.error("File too large (max 5MB)"); return; }
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post("/admin/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setForm((f) => ({ ...f, image: data.url }));
      toast.success("Image uploaded");
    } catch { toast.error("Upload failed"); }
    finally { setUploading(false); }
  };

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        name: form.name,
        slug: form.slug || form.name.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, ""),
        category: form.category,
        short_description: form.short_description,
        description: form.description,
        price: Number(form.price),
        mrp: Number(form.mrp),
        stock: parseInt(form.stock) || 0,
        image: form.image,
        images: form.images || [],
        badges: form.badges || [],
        featured: !!form.featured,
      };
      if (initial && initial.product_id) await api.put(`/products/${initial.product_id}`, payload);
      else await api.post("/products", payload);
      toast.success(initial ? "Product updated" : "Product created");
      onClose();
    } catch (err) {
      toast.error(errorMessage(err, "Could not save the product"));
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()} data-testid="product-editor">
        <form onSubmit={save} className="p-6 space-y-4">
          <h2 className="font-heading text-2xl font-medium">{initial ? "Edit Product" : "New Product"}</h2>

          <div className="flex gap-4 items-start">
            <div className="w-32 h-32 rounded-xl overflow-hidden bg-[#F1F5F9] flex items-center justify-center">
              {form.image ? <ProductImage src={form.image} alt="Product preview" className="w-full h-full object-cover" /> : <span className="text-xs text-[#64748B]">No image</span>}
            </div>
            <div className="flex-1">
              <label htmlFor="product-image" className="text-xs uppercase tracking-[0.15em] font-bold text-[#64748B]">Product image</label>
              <input id="product-image" type="file" accept="image/*" onChange={onUpload} className="mt-2 block text-sm" disabled={uploading} data-testid="product-image-upload" />
              {uploading && <p className="text-xs text-[#64748B] mt-2">Uploading...</p>}
              <label htmlFor="product-image-url" className="text-xs text-[#64748B] mt-2 block">Or paste an image URL below.</label>
              <input id="product-image-url" value={form.image} onChange={(e) => setForm({ ...form, image: e.target.value })} placeholder="https://..." className="mt-1 w-full border border-[var(--nayara-border)] rounded h-9 px-3 text-sm" />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="product-name" className="text-xs font-bold uppercase tracking-[0.15em] text-[#64748B]">Name<RequiredMark /></label>
              <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full border border-[var(--nayara-border)] rounded h-10 px-3 mt-1 text-sm" id="product-name" data-testid="product-name-input" />
            </div>
            <div>
              <label htmlFor="product-category" className="text-xs font-bold uppercase tracking-[0.15em] text-[#64748B]">Category</label>
              <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="w-full border border-[var(--nayara-border)] rounded h-10 px-3 mt-1 text-sm bg-white" id="product-category" data-testid="product-category-input">
                <option value="laundry">Laundry</option>
                <option value="personal-care">Personal Care</option>
                <option value="home-care">Home Care</option>
              </select>
            </div>
            <div>
              <label htmlFor="product-price" className="text-xs font-bold uppercase tracking-[0.15em] text-[#64748B]">Price (₹)<RequiredMark /></label>
              <input required type="number" min="0" step="0.01" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} className="w-full border border-[var(--nayara-border)] rounded h-10 px-3 mt-1 text-sm" id="product-price" data-testid="product-price-input" />
            </div>
            <div>
              <label htmlFor="product-mrp" className="text-xs font-bold uppercase tracking-[0.15em] text-[#64748B]">MRP (₹)<RequiredMark /></label>
              <input required type="number" min="0" step="0.01" value={form.mrp} onChange={(e) => setForm({ ...form, mrp: e.target.value })} className="w-full border border-[var(--nayara-border)] rounded h-10 px-3 mt-1 text-sm" id="product-mrp" data-testid="product-mrp-input" />
            </div>
            <div>
              <label htmlFor="product-stock" className="text-xs font-bold uppercase tracking-[0.15em] text-[#64748B]">Stock<RequiredMark /></label>
              <input required type="number" min="0" value={form.stock} onChange={(e) => setForm({ ...form, stock: e.target.value })} className="w-full border border-[var(--nayara-border)] rounded h-10 px-3 mt-1 text-sm" id="product-stock" data-testid="product-stock-input" />
            </div>
            <div className="flex items-center gap-2 mt-6">
              <input id="featured" type="checkbox" checked={!!form.featured} onChange={(e) => setForm({ ...form, featured: e.target.checked })} data-testid="product-featured-input" />
              <label htmlFor="featured" className="text-sm">Featured on home page</label>
            </div>
          </div>
          <div>
            <label htmlFor="product-short-desc" className="text-xs font-bold uppercase tracking-[0.15em] text-[#64748B]">Short description</label>
            <input value={form.short_description} onChange={(e) => setForm({ ...form, short_description: e.target.value })} className="w-full border border-[var(--nayara-border)] rounded h-10 px-3 mt-1 text-sm" id="product-short-desc" data-testid="product-short-desc-input" />
          </div>
          <div>
            <label htmlFor="product-description" className="text-xs font-bold uppercase tracking-[0.15em] text-[#64748B]">Description</label>
            <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={4} className="w-full border border-[var(--nayara-border)] rounded px-3 py-2 mt-1 text-sm" id="product-description" data-testid="product-desc-input" />
          </div>
          <div>
            <label htmlFor="product-badges" className="text-xs font-bold uppercase tracking-[0.15em] text-[#64748B]">Badges (comma-separated)</label>
            <input value={(form.badges || []).join(", ")} onChange={(e) => setForm({ ...form, badges: e.target.value.split(",").map((x) => x.trim()).filter(Boolean) })} className="w-full border border-[var(--nayara-border)] rounded h-10 px-3 mt-1 text-sm" placeholder="Made in India, Herbal" id="product-badges" data-testid="product-badges-input" />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="px-5 py-2 rounded-md border border-[var(--nayara-border)]" data-testid="product-cancel-btn">Cancel</button>
            <button type="submit" disabled={saving} className="nayara-btn" data-testid="product-save-btn">{saving ? "Saving..." : "Save Product"}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

function UsersAdmin() {
  const {
    items: users, total, loading, error, reload,
    page, pageSize, pageCount, setPage,
  } = usePagedData("/admin/users", {
    pageSize: 25,
    fallbackMessage: "Users could not be loaded.",
  });
  return (
    <div data-testid="admin-users">
      <h1 className="font-heading text-3xl font-medium mb-8 tracking-tight">Users</h1>
      <div className="rounded-2xl border border-[var(--nayara-border)] bg-white overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-[#FFFFFF] text-[#64748B] text-left">
            <tr><th className="px-4 py-3">Name</th><th className="px-4 py-3">Mobile</th><th className="px-4 py-3">Email</th><th className="px-4 py-3">Role</th><th className="px-4 py-3">Joined</th></tr>
          </thead>
          <tbody>
            <TableStateRow
              columns={5}
              loading={loading}
              error={error}
              onRetry={reload}
              emptyMessage={users.length === 0 ? "No users yet." : null}
            />
            {users.map((u) => (
              <tr key={u.user_id} className="border-t border-[var(--nayara-border)]">
                <td className="px-4 py-3">{u.name}</td>
                <td className="px-4 py-3">{u.mobile || "—"}</td>
                <td className="px-4 py-3">{u.email || "—"}</td>
                <td className="px-4 py-3">{u.is_admin ? <span className="badge-soft px-2 py-1 rounded-full text-xs">Admin</span> : "Customer"}</td>
                <td className="px-4 py-3 text-xs text-[#64748B]">{u.created_at?.slice(0, 10)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pagination
        page={page}
        pageSize={pageSize}
        pageCount={pageCount}
        total={total}
        onPageChange={setPage}
        noun="users"
      />
    </div>
  );
}

function MessagesAdmin() {
  const [selected, setSelected] = useState(null);
  const {
    items: messages, total, loading, error, reload,
    page, pageSize, pageCount, setPage,
  } = usePagedData("/admin/contacts", {
    pageSize: 25,
    fallbackMessage: "Messages could not be loaded.",
  });

  return (
    <div data-testid="admin-messages">
      <h1 className="font-heading text-3xl font-medium mb-8 tracking-tight">Messages</h1>
      {loading ? (
        <LoadingPanel label="Loading messages..." />
      ) : error ? (
        <ErrorPanel message={error} onRetry={reload} />
      ) : messages.length === 0 ? (
        <div className="rounded-2xl border border-[var(--nayara-border)] bg-white p-10 text-center text-[#64748B]">
          <MessageSquare className="w-10 h-10 mx-auto mb-3" />
          No customer messages yet.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-5">
          <div className="rounded-2xl border border-[var(--nayara-border)] bg-white overflow-hidden h-fit max-h-[70vh] overflow-y-auto">
            {messages.map((m) => (
              <button
                key={m.contact_id}
                onClick={() => setSelected(m)}
                className={`w-full text-left p-4 border-b border-[var(--nayara-border)] transition ${selected?.contact_id === m.contact_id ? "bg-[#FBEEE4]" : "hover:bg-[#FAFAFA]"}`}
                data-testid={`msg-item-${m.contact_id}`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium text-sm truncate">{m.name}</span>
                  <span className="text-xs text-[#64748B]">{m.created_at?.slice(0, 10)}</span>
                </div>
                <div className="text-xs text-[#64748B] truncate">{m.subject}</div>
                <div className="text-xs text-[#64748B] truncate mt-1">{m.message}</div>
              </button>
            ))}
            <div className="px-4 pb-3">
              <Pagination
                page={page}
                pageSize={pageSize}
                pageCount={pageCount}
                total={total}
                onPageChange={(next) => { setSelected(null); setPage(next); }}
                noun="messages"
              />
            </div>
          </div>
          <div className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6">
            {selected ? (
              <div data-testid="msg-detail">
                <div className="flex items-center justify-between gap-4 flex-wrap mb-5">
                  <div>
                    <h3 className="font-heading text-xl font-medium">{selected.subject}</h3>
                    <p className="text-sm text-[#64748B] mt-1">From <span className="font-medium text-[#0F172A]">{selected.name}</span> · {selected.created_at && new Date(selected.created_at).toLocaleString("en-IN")}</p>
                  </div>
                  <a href={`mailto:${selected.email}?subject=Re: ${encodeURIComponent(selected.subject)}`} className="nayara-btn-outline text-sm" data-testid="msg-reply-btn">Reply by email</a>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm mb-5">
                  <div className="rounded-lg bg-[#FAFAFA] p-3">
                    <div className="text-xs uppercase tracking-[0.15em] font-bold text-[#64748B]">Email</div>
                    <a href={`mailto:${selected.email}`} className="text-[var(--nayara-primary)] break-all">{selected.email}</a>
                  </div>
                  {selected.phone && (
                    <div className="rounded-lg bg-[#FAFAFA] p-3">
                      <div className="text-xs uppercase tracking-[0.15em] font-bold text-[#64748B]">Phone</div>
                      <a href={`tel:${selected.phone}`} className="text-[var(--nayara-primary)]">{selected.phone}</a>
                    </div>
                  )}
                </div>
                <div className="rounded-lg border border-[var(--nayara-border)] p-5 leading-relaxed text-sm whitespace-pre-wrap">{selected.message}</div>
              </div>
            ) : (
              <div className="text-center text-[#64748B] py-10">Select a message to read.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function BulkInquiriesAdmin() {
  const [selected, setSelected] = useState(null);
  const {
    items, total, loading, error, reload,
    page, pageSize, pageCount, setPage,
  } = usePagedData("/admin/bulk-inquiries", {
    pageSize: 25,
    fallbackMessage: "Bulk inquiries could not be loaded.",
  });
  const load = reload;

  const setStatus = async (id, status) => {
    try {
      await api.put(`/admin/bulk-inquiries/${id}`, { status });
      setSelected((s) => (s && s.inquiry_id === id ? { ...s, status } : s));
    } catch (failure) {
      toast.error(errorMessage(failure, "Could not update the inquiry"));
    }
    load();
  };

  const STATUS_COLORS = {
    new: "bg-blue-100 text-blue-700",
    contacted: "bg-amber-100 text-amber-700",
    quoted: "bg-indigo-100 text-indigo-700",
    won: "bg-green-100 text-green-700",
    lost: "bg-red-100 text-red-700",
  };

  return (
    <div data-testid="admin-bulk">
      <h1 className="font-heading text-3xl font-medium mb-8 tracking-tight">Bulk Inquiries</h1>
      {loading ? (
        <LoadingPanel label="Loading bulk inquiries..." />
      ) : error ? (
        <ErrorPanel message={error} onRetry={reload} />
      ) : items.length === 0 ? (
        <div className="rounded-2xl border border-[var(--nayara-border)] bg-white p-10 text-center text-[#64748B]">
          <Briefcase className="w-10 h-10 mx-auto mb-3" />
          No bulk inquiries yet.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-5">
          <div className="rounded-2xl border border-[var(--nayara-border)] bg-white overflow-hidden h-fit max-h-[70vh] overflow-y-auto">
            {items.map((m) => (
              <button
                key={m.inquiry_id}
                onClick={() => setSelected(m)}
                className={`w-full text-left p-4 border-b border-[var(--nayara-border)] transition ${selected?.inquiry_id === m.inquiry_id ? "bg-[#FBEEE4]" : "hover:bg-[#FAFAFA]"}`}
                data-testid={`bulk-item-${m.inquiry_id}`}
              >
                <div className="flex items-center justify-between mb-1 gap-2">
                  <span className="font-medium text-sm truncate">{m.business_name}</span>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${STATUS_COLORS[m.status] || 'bg-gray-100'}`}>{m.status || 'new'}</span>
                </div>
                <div className="text-xs text-[#64748B] truncate">{m.name} · {m.city}</div>
                <div className="text-xs text-[#64748B] truncate mt-1">{m.quantity}</div>
              </button>
            ))}
            <div className="px-4 pb-3">
              <Pagination
                page={page}
                pageSize={pageSize}
                pageCount={pageCount}
                total={total}
                onPageChange={(next) => { setSelected(null); setPage(next); }}
                noun="inquiries"
              />
            </div>
          </div>
          <div className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6">
            {selected ? (
              <div data-testid="bulk-detail">
                <div className="flex items-start justify-between gap-4 flex-wrap mb-5">
                  <div>
                    <h3 className="font-heading text-xl font-medium">{selected.business_name}</h3>
                    <p className="text-sm text-[#64748B] mt-1">{selected.name} · {selected.city} · {selected.created_at && new Date(selected.created_at).toLocaleString("en-IN")}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <select defaultValue={selected.status || "new"} onChange={(e) => setStatus(selected.inquiry_id, e.target.value)} className="border border-[var(--nayara-border)] rounded px-2 py-1 text-xs" data-testid="bulk-status-select">
                      {["new", "contacted", "quoted", "won", "lost"].map((s) => <option key={s}>{s}</option>)}
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm mb-5">
                  <div className="rounded-lg bg-[#FAFAFA] p-3">
                    <div className="text-xs uppercase tracking-[0.15em] font-bold text-[#64748B]">Email</div>
                    <a href={`mailto:${selected.email}`} className="text-[var(--nayara-primary)] break-all">{selected.email}</a>
                  </div>
                  <div className="rounded-lg bg-[#FAFAFA] p-3">
                    <div className="text-xs uppercase tracking-[0.15em] font-bold text-[#64748B]">Phone</div>
                    <a href={`tel:${selected.phone}`} className="text-[var(--nayara-primary)]">{selected.phone}</a>
                  </div>
                  <div className="rounded-lg bg-[#FAFAFA] p-3 sm:col-span-2">
                    <div className="text-xs uppercase tracking-[0.15em] font-bold text-[#64748B]">Quantity</div>
                    <div>{selected.quantity}</div>
                  </div>
                  {selected.products_interested?.length > 0 && (
                    <div className="rounded-lg bg-[#FAFAFA] p-3 sm:col-span-2">
                      <div className="text-xs uppercase tracking-[0.15em] font-bold text-[#64748B] mb-2">Products</div>
                      <div className="flex flex-wrap gap-1.5">
                        {selected.products_interested.map((p) => (
                          <span key={p} className="badge-soft px-2 py-1 rounded-full text-xs">{p}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                {selected.message && (
                  <div>
                    <div className="text-xs uppercase tracking-[0.15em] font-bold text-[#64748B] mb-2">Message</div>
                    <div className="rounded-lg border border-[var(--nayara-border)] p-5 leading-relaxed text-sm whitespace-pre-wrap">{selected.message}</div>
                  </div>
                )}
                <div className="mt-5 flex gap-3">
                  <a href={`mailto:${selected.email}?subject=Re: Bulk inquiry from ${encodeURIComponent(selected.business_name)}`} className="nayara-btn-outline text-sm" data-testid="bulk-reply-email">Reply by email</a>
                  <a href={`tel:${selected.phone}`} className="nayara-btn text-sm" data-testid="bulk-call-btn">Call now</a>
                </div>
              </div>
            ) : (
              <div className="text-center text-[#64748B] py-10">Select an inquiry to view details.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function Admin() {
  const location = useLocation();
  return (
    <div className="max-w-7xl mx-auto px-6 py-10 grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-8" data-testid="admin-page">
      <aside className="rounded-2xl border border-[var(--nayara-border)] bg-white p-3 h-fit">
        {navs.map((n) => {
          const active = n.end ? location.pathname === n.to : location.pathname.startsWith(n.to) && n.to !== "/admin";
          return (
            <Link key={n.to} to={n.to} className={`flex items-center gap-2 px-4 py-3 rounded-lg text-sm transition ${active ? "bg-[var(--nayara-primary)] text-white" : "hover:bg-[#FBEEE4]"}`} data-testid={`admin-nav-${n.label.toLowerCase()}`}>
              <n.icon className="w-4 h-4" /> {n.label}
            </Link>
          );
        })}
      </aside>
      <Routes>
        <Route index element={<Dashboard />} />
        <Route path="orders" element={<OrdersAdmin />} />
        <Route path="products" element={<ProductsAdmin />} />
        <Route path="bulk" element={<BulkInquiriesAdmin />} />
        <Route path="messages" element={<MessagesAdmin />} />
        <Route path="users" element={<UsersAdmin />} />
      </Routes>
    </div>
  );
}
