import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api, errorMessage } from "../lib/api";
import { lineKey, lineName } from "../lib/variants";
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
  const { user, loading: authLoading } = useAuth();
  const [cart, setCart] = useState([]); // [{product..., quantity}]
  const [wishlist, setWishlist] = useState([]); // [product...]
  const [cartLoading, setCartLoading] = useState(true);
  const [wishlistLoading, setWishlistLoading] = useState(true);

  // LOCAL: product snapshots with {product_id, name, image, price, quantity}
  const refreshCart = useCallback(async () => {
    try {
      if (user) {
        const { data } = await api.get("/cart");
        setCart(data.items || []);
      } else {
        setCart(readLocal(LOCAL_KEY));
      }
    } catch (failure) {
      // Leaving the previous contents visible is safer than implying the
      // cart is empty, which invites someone to add the same items twice.
      toast.error(errorMessage(failure, "We could not load your cart."));
    } finally {
      setCartLoading(false);
    }
  }, [user]);

  const refreshWishlist = useCallback(async () => {
    try {
      if (user) {
        const { data } = await api.get("/wishlist");
        setWishlist(data.items || []);
      } else {
        setWishlist(readLocal(WL_KEY));
      }
    } catch (failure) {
      toast.error(errorMessage(failure, "We could not load your wishlist."));
    } finally {
      setWishlistLoading(false);
    }
  }, [user]);

  useEffect(() => { refreshCart(); refreshWishlist(); }, [refreshCart, refreshWishlist]);

  const addToCart = async (product, qty = 1) => {
    try {
      if (user) {
        await api.post("/cart", {
          product_id: product.product_id,
          // Which form is being bought. A product sold as only one resolves
          // it on the server, so this may be absent.
          variant_id: product.variant_id,
          quantity: qty,
        });
        await refreshCart();
      } else {
        const existing = readLocal(LOCAL_KEY);
        // Two forms of one product are two lines, so the line is found by
        // both parts.
        const i = existing.findIndex((x) => lineKey(x) === lineKey(product));
        const wanted = (i >= 0 ? existing[i].quantity : 0) + qty;
        if (typeof product.stock === "number" && wanted > product.stock) {
          toast.error(
            product.stock > 0
              ? `Only ${product.stock} left of ${lineName(product)}.`
              : `${lineName(product)} is out of stock.`
          );
          return;
        }
        if (i >= 0) existing[i].quantity = wanted;
        else existing.push({ ...product, quantity: qty });
        writeLocal(LOCAL_KEY, existing);
        setCart(existing);
      }
      toast.success(`${lineName(product)} added to cart`);
    } catch (failure) {
      // The API refuses a cart it could not fill, and that refusal names the
      // product and what is left of it.
      toast.error(errorMessage(failure, "Could not add that to your cart."));
    }
  };

  const updateQuantity = async (item, quantity) => {
    try {
      if (user) {
        await api.put(`/cart/${item.product_id}`, { quantity, variant_id: item.variant_id });
        await refreshCart();
      } else {
        let items = readLocal(LOCAL_KEY);
        if (quantity <= 0) items = items.filter((x) => lineKey(x) !== lineKey(item));
        else items = items.map((x) => (lineKey(x) === lineKey(item) ? { ...x, quantity } : x));
        writeLocal(LOCAL_KEY, items);
        setCart(items);
      }
    } catch (failure) {
      toast.error(errorMessage(failure, "Could not change that quantity."));
      await refreshCart();
    }
  };

  const removeFromCart = async (item) => {
    if (user) {
      const query = item.variant_id ? `?variant_id=${encodeURIComponent(item.variant_id)}` : "";
      await api.delete(`/cart/${item.product_id}${query}`);
      await refreshCart();
    } else {
      const items = readLocal(LOCAL_KEY).filter((x) => lineKey(x) !== lineKey(item));
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
      // Until we know who is signed in, the local-storage contents are not
      // the final answer, so the screens should keep waiting.
      cartLoading: cartLoading || authLoading,
      wishlistLoading: wishlistLoading || authLoading,
      addToCart, updateQuantity, removeFromCart, clearCart,
      toggleWishlist, isInWishlist, refreshCart, refreshWishlist,
    }}>
      {children}
    </CartContext.Provider>
  );
};

export const useCart = () => useContext(CartContext);
