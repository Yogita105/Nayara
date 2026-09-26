import React, { useEffect, useState } from "react";
import { useParams, useSearchParams, useNavigate, Link } from "react-router-dom";
import { api, formatINR } from "../lib/api";
import { isOutOfStock, stockNotice } from "../lib/stock";
import { asSold, defaultVariant, findVariant, hasChoice } from "../lib/variants";
import useAsyncData from "../hooks/useAsyncData";
import { ErrorPanel, LoadingPanel } from "../components/DataState";
import { useCart } from "../context/CartContext";
import { useAuth } from "../context/AuthContext";
import { Heart, ShoppingCart, Star, ShieldCheck, Truck, Leaf, Minus, Plus, Check, ArrowLeft } from "lucide-react";
import { Button } from "../components/ui/button";
import { Textarea } from "../components/ui/textarea";
import { Input } from "../components/ui/input";
import ProductImage from "../components/ProductImage";
import VariantPicker from "../components/VariantPicker";
import { toast } from "sonner";

export default function ProductDetail() {
  const { productId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const [reviews, setReviews] = useState([]);
  const [qty, setQty] = useState(1);
  const [chosenId, setChosenId] = useState(null);
  // What happened the last time Add to Cart was pressed, shown on the button
  // itself rather than in a corner of the screen.
  const [added, setAdded] = useState(false);
  const [addProblem, setAddProblem] = useState("");
  const [form, setForm] = useState({ rating: 5, title: "", comment: "" });
  const { addToCart, toggleWishlist, isInWishlist } = useCart();
  const { user } = useAuth();

  const {
    data: product,
    loading,
    error,
    reload,
  } = useAsyncData(
    async () => {
      const { data } = await api.get(`/products/${productId}`);
      const listed = await api.get(`/products/${productId}/reviews`);
      setReviews(listed.data);
      return data;
    },
    [productId],
    "This product could not be loaded."
  );

  const load = reload;

  // The confirmation on the button is temporary, so the button goes back to
  // inviting the next action rather than claiming success forever.
  useEffect(() => {
    if (!added) return undefined;
    const timer = setTimeout(() => setAdded(false), 2500);
    return () => clearTimeout(timer);
  }, [added]);

  if (loading) return <LoadingPanel label="Loading product..." />;
  if (error) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-16">
        <ErrorPanel message={error} onRetry={reload} />
      </div>
    );
  }
  if (!product) return null;

  // The form being shown: whatever was picked, then whatever the link asked
  // for, then the cheapest one still in stock.
  const chosen =
    findVariant(product, chosenId) ||
    findVariant(product, searchParams.get("variant")) ||
    defaultVariant(product);
  // Price, stock and photograph come from the form, under the names the rest
  // of this page already reads.
  const sold = asSold(product, chosen);

  const chooseVariant = (variantId) => {
    setChosenId(variantId);
    setQty(1);
    // A different form is a different decision, so last time's answer no
    // longer applies to it.
    setAdded(false);
    setAddProblem("");
    // A chosen form belongs in the address bar, so the page can be shared,
    // reloaded or gone back to and still show what was being looked at.
    setSearchParams({ variant: variantId }, { replace: true });
  };

  const notice = stockNotice(sold.stock);
  const soldOut = isOutOfStock(sold);
  // Fall back to a generous cap when the field is missing, so a product
  // without stock recorded is not made unbuyable.
  const available = typeof sold.stock === "number" ? sold.stock : Infinity;

  const discount = Math.round(((sold.mrp - sold.price) / sold.mrp) * 100) || 0;
  const saved = isInWishlist(product.product_id);

  const onAddToCart = async () => {
    setAddProblem("");
    const result = await addToCart(sold, qty);
    if (result.ok) setAdded(true);
    else setAddProblem(result.message);
  };

  /**
   * Back to wherever they came from, with the shop's filters, sort and page
   * intact, because those live in its address and stepping back restores
   * them. The breadcrumb below leads to an unfiltered shop instead, which is
   * a different intention and worth keeping separate.
   *
   * Someone who arrived from a shared link has nothing to step back to, so
   * they are sent to the shop rather than off the site.
   */
  const cameFromWithinTheSite = (window.history.state?.idx ?? 0) > 0;
  const goBack = () => (cameFromWithinTheSite ? navigate(-1) : navigate("/shop"));

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
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 mb-6">
        <button
          onClick={goBack}
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--nayara-primary)] hover:underline"
          data-testid="product-back"
        >
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <div className="text-xs text-[#64748B]">
          <Link to="/">Home</Link> / <Link to="/shop">Shop</Link> / <span className="text-[#0F172A]">{product.name}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
        <div className="rounded-3xl overflow-hidden bg-[#F1F5F9] aspect-square">
          <ProductImage src={sold.image} alt={product.name} className="w-full h-full object-cover" />
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
            <div className="font-heading text-3xl font-semibold" data-testid="product-price">{formatINR(sold.price)}</div>
            {sold.mrp > sold.price && (
              <>
                <div className="text-lg text-[#64748B] line-through mb-1">{formatINR(sold.mrp)}</div>
                <div className="text-sm text-[var(--nayara-primary)] font-semibold mb-1">{discount}% off</div>
              </>
            )}
          </div>

          <VariantPicker product={product} value={chosen?.variant_id} onChange={chooseVariant} />

          {notice && (
            <p
              className={`mt-3 text-sm font-medium ${notice.tone === "out" ? "text-[#64748B]" : "text-red-600"}`}
              data-testid="product-stock-notice"
            >
              {notice.text}
            </p>
          )}

          <div className="mt-6 flex items-center gap-4">
            <div className="flex items-center border border-[var(--nayara-border)] rounded-full h-12">
              <button
                onClick={() => setQty(Math.max(1, qty - 1))}
                disabled={soldOut}
                className="px-4 h-full disabled:opacity-40"
                data-testid="qty-decrease"
                aria-label="Reduce quantity"
              >
                <Minus className="w-4 h-4" />
              </button>
              <span className="w-8 text-center font-semibold" data-testid="qty-value">{qty}</span>
              <button
                onClick={() => setQty(Math.min(available, qty + 1))}
                disabled={soldOut || qty >= available}
                className="px-4 h-full disabled:opacity-40"
                data-testid="qty-increase"
                aria-label="Increase quantity"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
            <button
              onClick={onAddToCart}
              disabled={soldOut}
              className={`nayara-btn flex-1 sm:flex-none disabled:opacity-50 disabled:cursor-not-allowed ${added ? "!bg-[#15803D] hover:!bg-[#15803D]" : ""}`}
              data-testid="pdp-add-to-cart"
            >
              {added ? (
                <>
                  <Check className="w-4 h-4 mr-2" /> Added to cart
                </>
              ) : (
                <>
                  <ShoppingCart className="w-4 h-4 mr-2" /> {soldOut ? "Out of Stock" : "Add to Cart"}
                </>
              )}
            </button>
            <button onClick={() => toggleWishlist(product)} className="w-12 h-12 rounded-full border border-[var(--nayara-border)] flex items-center justify-center" data-testid="pdp-wishlist">
              <Heart className={`w-4 h-4 ${saved ? "fill-red-500 text-red-500" : ""}`} />
            </button>
          </div>

          {addProblem && (
            <p
              role="alert"
              className="mt-3 text-sm font-medium text-red-600"
              data-testid="pdp-add-problem"
            >
              {addProblem}
            </p>
          )}

          {added && (
            <p className="mt-3 text-sm" data-testid="pdp-add-confirmation">
              <Link to="/cart" className="font-semibold text-[var(--nayara-primary)] underline">
                Go to cart
              </Link>
              <span className="text-[#64748B]"> to check out, or keep shopping.</span>
            </p>
          )}

          {/* The button's own label changes, which a screen reader may not
              announce on its own, so the result is also stated politely. */}
          <span className="sr-only" role="status">
            {added ? `${sold.name} added to cart` : ""}
          </span>

          {!soldOut && qty >= available && (
            <p className="mt-2 text-xs text-[#64748B]" data-testid="qty-capped">
              {hasChoice(product)
                ? `That is all we have of the ${chosen.label}.`
                : "That is all we have of this one."}
            </p>
          )}

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
