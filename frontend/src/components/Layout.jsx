import React from "react";
import { Outlet } from "react-router-dom";
import Navbar from "./Navbar";
import Footer from "./Footer";

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col bg-[#F8F9FA] text-[#1A2E2A]">
      <Navbar />
      <main className="flex-1 pt-20" data-testid="main-content">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
