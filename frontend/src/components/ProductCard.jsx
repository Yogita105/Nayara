import React from "react";
import { Link } from "react-router-dom";
import { Heart, ShoppingCart, Star } from "lucide-react";
import { useCart } from "../context/CartContext";
import { formatINR } from "../lib/api";

export default function ProductCard({ product, index = 0 }) {
  const { addToCart, toggleWishlist, isInWishlist } = useCart();
  const saved = isInWishlist(product.product_id);
  const discount = Math.round(((product.mrp - product.price) / product.mrp) * 100) || 0;

  return (
    <div
      className="group rounded-2xl border border-[var(--nayara-border)] bg-white overflow-hidden hover:shadow-lg transition-all duration-300 fade-up"
      style={{ animationDelay: `${index * 60}ms` }}
      data-testid={`product-card-${product.product_id}`}
    >
      <div className="relative aspect-square bg-[#F1F5F9] overflow-hidden">
        <Link to={`/product/${product.product_id}`} data-testid={`product-link-${product.product_id}`}>
          <img
            src={product.image}
            alt={product.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          />
        </Link>
        {discount > 0 && (
          <span className="absolute top-3 left-3 text-[11px] font-semibold bg-[var(--nayara-primary)] text-white px-2 py-1 rounded-full">
            -{discount}%
          </span>
        )}
        <button
          onClick={() => toggleWishlist(product)}
          className="absolute top-3 right-3 w-9 h-9 rounded-full bg-white/90 backdrop-blur flex items-center justify-center hover:bg-white shadow-sm transition"
          data-testid={`wishlist-btn-${product.product_id}`}
          aria-label="Toggle wishlist"
        >
          <Heart className={`w-4 h-4 ${saved ? "fill-red-500 text-red-500" : "text-[#64748B]"}`} />
        </button>
      </div>
      <div className="p-5">
        <div className="flex items-center gap-1 text-xs text-[#64748B] mb-1">
          <Star className="w-3.5 h-3.5 fill-[#F59E0B] text-[#F59E0B]" />
          <span>{product.rating?.toFixed(1) || "4.5"}</span>
          <span className="mx-1">·</span>
          <span className="capitalize">{product.category?.replace("-", " ")}</span>
        </div>
        <Link to={`/product/${product.product_id}`}>
          <h3 className="font-heading font-medium text-base leading-snug line-clamp-2 min-h-[2.6rem] hover:text-[var(--nayara-primary)]">{product.name}</h3>
        </Link>
        <p className="text-xs text-[#64748B] line-clamp-2 mt-1 min-h-[2rem]">{product.short_description}</p>
        <div className="flex items-end justify-between mt-4">
          <div>
            <div className="font-heading text-xl font-semibold">{formatINR(product.price)}</div>
            {product.mrp > product.price && (
              <div className="text-xs text-[#64748B] line-through">{formatINR(product.mrp)}</div>
            )}
          </div>
          <button
            onClick={() => addToCart(product, 1)}
            className="w-10 h-10 rounded-full bg-[var(--nayara-primary)] text-white flex items-center justify-center hover:bg-[var(--nayara-primary-hover)] transition"
            data-testid={`add-to-cart-${product.product_id}`}
            aria-label="Add to cart"
          >
            <ShoppingCart className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
