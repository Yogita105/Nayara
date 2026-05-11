import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, formatINR } from "../lib/api";
import { useCart } from "../context/CartContext";
import { useAuth } from "../context/AuthContext";
import { Heart, ShoppingCart, Star, ShieldCheck, Truck, Leaf, Minus, Plus } from "lucide-react";
import { Button } from "../components/ui/button";
import { Textarea } from "../components/ui/textarea";
import { Input } from "../components/ui/input";
import { toast } from "sonner";

export default function ProductDetail() {
  const { productId } = useParams();
  const [product, setProduct] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [qty, setQty] = useState(1);
  const [form, setForm] = useState({ rating: 5, title: "", comment: "" });
  const { addToCart, toggleWishlist, isInWishlist } = useCart();
  const { user } = useAuth();

  const load = async () => {
    const { data } = await api.get(`/products/${productId}`);
    setProduct(data);
    const r = await api.get(`/products/${productId}/reviews`);
    setReviews(r.data);
  };
  useEffect(() => { load(); }, [productId]);

  if (!product) return <div className="py-20 text-center text-[#64748B]">Loading...</div>;

  const discount = Math.round(((product.mrp - product.price) / product.mrp) * 100) || 0;
  const saved = isInWishlist(product.product_id);

  const submitReview = async (e) => {
    e.preventDefault();
    if (!user) { toast.error("Please login to review"); return; }
    try {
      await api.post(`/products/${productId}/reviews`, form);
      toast.success("Review submitted");
      setForm({ rating: 5, title: "", comment: "" });
      load();
    } catch { toast.error("Could not submit review"); }
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-10" data-testid="product-detail-page">
      <div className="text-xs text-[#64748B] mb-6">
        <Link to="/">Home</Link> / <Link to="/shop">Shop</Link> / <span className="text-[#0F172A]">{product.name}</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
        <div className="rounded-3xl overflow-hidden bg-[#F1F5F9] aspect-square">
          <img src={product.image} alt={product.name} className="w-full h-full object-cover" />
        </div>
        <div>
          <div className="flex flex-wrap gap-2 mb-3">
            {product.badges?.map((b, i) => (
              <span key={i} className="badge-soft px-3 py-1 rounded-full text-xs font-semibold inline-flex items-center gap-1.5">
                <Leaf className="w-3 h-3" /> {b}
              </span>
            ))}
          </div>
          <h1 className="font-heading text-2xl md:text-3xl font-medium tracking-tight" data-testid="product-name">{product.name}</h1>
          <div className="mt-3 flex items-center gap-3 text-sm">
            <div className="flex items-center gap-1">
              <Star className="w-4 h-4 fill-[#F59E0B] text-[#F59E0B]" />
              <span className="font-semibold">{product.rating?.toFixed(1)}</span>
            </div>
            <span className="text-[#64748B]">· {product.reviews_count} reviews</span>
          </div>
          <p className="mt-5 text-[#64748B] leading-relaxed">{product.description}</p>

          <div className="mt-6 flex items-end gap-3">
            <div className="font-heading text-3xl font-semibold" data-testid="product-price">{formatINR(product.price)}</div>
            {product.mrp > product.price && (
              <>
                <div className="text-lg text-[#64748B] line-through mb-1">{formatINR(product.mrp)}</div>
                <div className="text-sm text-[var(--nayara-primary)] font-semibold mb-1">{discount}% off</div>
              </>
            )}
          </div>

          <div className="mt-6 flex items-center gap-4">
            <div className="flex items-center border border-[var(--nayara-border)] rounded-full h-12">
              <button onClick={() => setQty(Math.max(1, qty - 1))} className="px-4 h-full" data-testid="qty-decrease"><Minus className="w-4 h-4" /></button>
              <span className="w-8 text-center font-semibold" data-testid="qty-value">{qty}</span>
              <button onClick={() => setQty(qty + 1)} className="px-4 h-full" data-testid="qty-increase"><Plus className="w-4 h-4" /></button>
            </div>
            <button onClick={() => addToCart(product, qty)} className="nayara-btn flex-1 sm:flex-none" data-testid="pdp-add-to-cart">
              <ShoppingCart className="w-4 h-4 mr-2" /> Add to Cart
            </button>
            <button onClick={() => toggleWishlist(product)} className="w-12 h-12 rounded-full border border-[var(--nayara-border)] flex items-center justify-center" data-testid="pdp-wishlist">
              <Heart className={`w-4 h-4 ${saved ? "fill-red-500 text-red-500" : ""}`} />
            </button>
          </div>

          <div className="mt-8 grid grid-cols-3 gap-3 text-sm">
            <div className="rounded-xl border border-[var(--nayara-border)] p-3 bg-white">
              <Truck className="w-4 h-4 mb-1 text-[var(--nayara-primary)]" />
              <span className="font-semibold">Free shipping ₹499+</span>
            </div>
            <div className="rounded-xl border border-[var(--nayara-border)] p-3 bg-white">
              <ShieldCheck className="w-4 h-4 mb-1 text-[var(--nayara-primary)]" />
              <span className="font-semibold">Quality guarantee</span>
            </div>
            <div className="rounded-xl border border-[var(--nayara-border)] p-3 bg-white">
              <Leaf className="w-4 h-4 mb-1 text-[var(--nayara-primary)]" />
              <span className="font-semibold">Factory fresh</span>
            </div>
          </div>
        </div>
      </div>

      {/* Reviews */}
      <section className="mt-16">
        <h2 className="font-heading text-2xl font-medium mb-6">Customer Reviews</h2>
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-8">
          <div className="space-y-4">
            {reviews.length === 0 && <div className="text-[#64748B]">No reviews yet. Be the first!</div>}
            {reviews.map((r) => (
              <div key={r.review_id} className="rounded-2xl border border-[var(--nayara-border)] bg-white p-5" data-testid={`review-${r.review_id}`}>
                <div className="flex items-center gap-2 mb-2">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Star key={i} className={`w-4 h-4 ${i < r.rating ? "fill-[#F59E0B] text-[#F59E0B]" : "text-[#E2E8F0]"}`} />
                  ))}
                  <span className="text-sm font-semibold ml-1">{r.title}</span>
                </div>
                <p className="text-sm text-[#64748B]">{r.comment}</p>
                <div className="text-xs text-[#64748B] mt-3">— {r.user_name}</div>
              </div>
            ))}
          </div>
          <form onSubmit={submitReview} className="rounded-2xl border border-[var(--nayara-border)] bg-white p-6 h-fit" data-testid="review-form">
            <h3 className="font-heading font-semibold mb-4">Write a review</h3>
            <div className="flex items-center gap-1 mb-3">
              {[1, 2, 3, 4, 5].map((n) => (
                <button type="button" key={n} onClick={() => setForm({ ...form, rating: n })} data-testid={`review-star-${n}`}>
                  <Star className={`w-6 h-6 ${n <= form.rating ? "fill-[#F59E0B] text-[#F59E0B]" : "text-[#E2E8F0]"}`} />
                </button>
              ))}
            </div>
            <Input
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="Review title"
              className="mb-3"
              required
              data-testid="review-title-input"
            />
            <Textarea
              value={form.comment}
              onChange={(e) => setForm({ ...form, comment: e.target.value })}
              placeholder="Share your experience..."
              rows={4}
              required
              data-testid="review-comment-input"
            />
            <Button type="submit" className="mt-4 w-full bg-[var(--nayara-primary)] hover:bg-[var(--nayara-primary-hover)]" data-testid="submit-review-btn">
              Submit Review
            </Button>
            {!user && <p className="text-xs text-[#64748B] mt-2">Please login to post a review.</p>}
          </form>
        </div>
      </section>
    </div>
  );
}
