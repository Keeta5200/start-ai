"use client";

import { useEffect } from "react";
import { buildTokenCookie, buildAuthCookie } from "@/lib/auth";

export function CookieSync() {
  useEffect(() => {
    const token = localStorage.getItem("start-ai-token");
    if (!token) return;

    const hasCookie = document.cookie
      .split(";")
      .some((c) => c.trim().startsWith("start-ai-token="));

    if (!hasCookie) {
      document.cookie = buildAuthCookie();
      document.cookie = buildTokenCookie(token);
    }
  }, []);

  return null;
}
