import React from "react";
import { Outlet } from "react-router-dom";
import Navbar from "./Navbar";
import Footer from "./Footer";

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col bg-[#FFFFFF] text-[#0F172A]">
      <Navbar />
      <main className="flex-1 pt-20" data-testid="main-content">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
