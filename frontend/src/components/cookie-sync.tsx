"use client";

import { useEffect } from "react";
import { buildTokenCookie, buildAuthCookie, getStoredAuthToken } from "@/lib/auth";

export function CookieSync() {
  useEffect(() => {
    const persistentToken = localStorage.getItem("start-ai-token");
    const token = getStoredAuthToken();
    if (!token) return;
    const persistent = Boolean(persistentToken);

    const hasTokenCookie = document.cookie
      .split(";")
      .some((c) => c.trim().startsWith("start-ai-token="));
    const hasSessionCookie = document.cookie
      .split(";")
      .some((c) => c.trim().startsWith("start-ai-session="));

    if (!hasSessionCookie) {
      document.cookie = buildAuthCookie(persistent);
    }

    if (!hasTokenCookie) {
      document.cookie = buildTokenCookie(token, persistent);
    }
  }, []);

  return null;
}
