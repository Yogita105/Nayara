import React from "react";
import { useCart } from "../context/CartContext";
import ProductCard from "../components/ProductCard";
import { Link } from "react-router-dom";
import { Heart } from "lucide-react";

export default function Wishlist() {
  const { wishlist } = useCart();

  return (
    <div className="max-w-7xl mx-auto px-6 py-10" data-testid="wishlist-page">
      <h1 className="font-heading text-3xl md:text-4xl font-medium tracking-tight mb-8">My Wishlist</h1>
      {wishlist.length === 0 ? (
        <div className="text-center py-16 rounded-2xl border border-[var(--nayara-border)] bg-white">
          <Heart className="w-14 h-14 mx-auto text-[#5C7671] mb-4" />
          <p className="text-[#5C7671]">Your wishlist is empty.</p>
          <Link to="/shop" className="nayara-btn mt-5">Browse Products</Link>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {wishlist.map((p, i) => <ProductCard key={p.product_id} product={p} index={i} />)}
        </div>
      )}
    </div>
  );
}
