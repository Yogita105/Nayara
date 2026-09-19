import React from "react";
import { useCart } from "../context/CartContext";
import ProductCard from "../components/ProductCard";
import { EmptyPanel, LoadingPanel } from "../components/DataState";
import { Link } from "react-router-dom";
import { Heart } from "lucide-react";

export default function Wishlist() {
  const { wishlist, wishlistLoading } = useCart();

  return (
    <div className="max-w-7xl mx-auto px-6 py-10" data-testid="wishlist-page">
      <h1 className="font-heading text-3xl md:text-4xl font-medium tracking-tight mb-8">My Wishlist</h1>
      {wishlistLoading ? (
        <LoadingPanel label="Loading your wishlist..." />
      ) : wishlist.length === 0 ? (
        <EmptyPanel
          icon={Heart}
          message="Your wishlist is empty."
          action={<Link to="/shop" className="nayara-btn mt-5">Browse Products</Link>}
        />
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {wishlist.map((p, i) => <ProductCard key={p.product_id} product={p} index={i} />)}
        </div>
      )}
    </div>
  );
}
