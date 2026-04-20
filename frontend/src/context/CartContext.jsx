import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import { useAuth } from "./AuthContext";
import { toast } from "sonner";

const CartContext = createContext(null);
const LOCAL_KEY = "nayara_cart_v1";
const WL_KEY = "nayara_wishlist_v1";

const readLocal = (key) => {
  try { return JSON.parse(localStorage.getItem(key)) || []; } catch { return []; }
};
const writeLocal = (key, val) => localStorage.setItem(key, JSON.stringify(val));

export const CartProvider = ({ children }) => {
  const { user } = useAuth();
  const [cart, setCart] = useState([]); // [{product..., quantity}]
  const [wishlist, setWishlist] = useState([]); // [product...]

  // LOCAL: product snapshots with {product_id, name, image, price, quantity}
  const refreshCart = useCallback(async () => {
    if (user) {
      const { data } = await api.get("/cart");
      setCart(data.items || []);
    } else {
      setCart(readLocal(LOCAL_KEY));
    }
  }, [user]);

  const refreshWishlist = useCallback(async () => {
    if (user) {
      const { data } = await api.get("/wishlist");
      setWishlist(data.items || []);
    } else {
      setWishlist(readLocal(WL_KEY));
    }
  }, [user]);

  useEffect(() => { refreshCart(); refreshWishlist(); }, [refreshCart, refreshWishlist]);

  const addToCart = async (product, qty = 1) => {
    if (user) {
      await api.post("/cart", { product_id: product.product_id, quantity: qty });
      await refreshCart();
    } else {
      const existing = readLocal(LOCAL_KEY);
      const i = existing.findIndex((x) => x.product_id === product.product_id);
      if (i >= 0) existing[i].quantity += qty;
      else existing.push({ ...product, quantity: qty });
      writeLocal(LOCAL_KEY, existing);
      setCart(existing);
    }
    toast.success(`${product.name} added to cart`);
  };

  const updateQuantity = async (product_id, quantity) => {
    if (user) {
      await api.put(`/cart/${product_id}`, { quantity });
      await refreshCart();
    } else {
      let items = readLocal(LOCAL_KEY);
      if (quantity <= 0) items = items.filter((x) => x.product_id !== product_id);
      else items = items.map((x) => (x.product_id === product_id ? { ...x, quantity } : x));
      writeLocal(LOCAL_KEY, items);
      setCart(items);
    }
  };

  const removeFromCart = async (product_id) => {
    if (user) {
      await api.delete(`/cart/${product_id}`);
      await refreshCart();
    } else {
      const items = readLocal(LOCAL_KEY).filter((x) => x.product_id !== product_id);
      writeLocal(LOCAL_KEY, items);
      setCart(items);
    }
  };

  const clearCart = async () => {
    if (user) {
      await api.delete("/cart");
      await refreshCart();
    } else {
      writeLocal(LOCAL_KEY, []);
      setCart([]);
    }
  };

  const toggleWishlist = async (product) => {
    const isInWL = wishlist.some((w) => w.product_id === product.product_id);
    if (user) {
      if (isInWL) await api.delete(`/wishlist/${product.product_id}`);
      else await api.post("/wishlist", { product_id: product.product_id });
      await refreshWishlist();
    } else {
      let items = readLocal(WL_KEY);
      if (isInWL) items = items.filter((w) => w.product_id !== product.product_id);
      else items = [...items, product];
      writeLocal(WL_KEY, items);
      setWishlist(items);
    }
    toast.success(isInWL ? "Removed from wishlist" : "Added to wishlist");
  };

  const isInWishlist = (product_id) => wishlist.some((w) => w.product_id === product_id);

  const cartCount = cart.reduce((a, b) => a + (b.quantity || 0), 0);
  const cartTotal = cart.reduce((a, b) => a + (b.price || 0) * (b.quantity || 0), 0);

  return (
    <CartContext.Provider value={{
      cart, wishlist, cartCount, cartTotal,
      addToCart, updateQuantity, removeFromCart, clearCart,
      toggleWishlist, isInWishlist, refreshCart, refreshWishlist,
    }}>
      {children}
    </CartContext.Provider>
  );
};

export const useCart = () => useContext(CartContext);
