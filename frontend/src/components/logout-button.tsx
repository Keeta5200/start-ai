"use client";

import { buildExpiredAuthCookie, buildExpiredTokenCookie } from "@/lib/auth";

export function LogoutButton() {
  function handleLogout() {
    localStorage.removeItem("start-ai-token");
    localStorage.removeItem("start-ai-user");
    document.cookie = buildExpiredAuthCookie();
    document.cookie = buildExpiredTokenCookie();
    window.location.href = "/login";
  }

  return (
    <button
      type="button"
      onClick={handleLogout}
      className="rounded-full border border-white/10 bg-white/[0.03] px-4 py-2 text-sm text-bone transition hover:border-ember hover:bg-white/[0.06] hover:text-ember"
    >
      ログアウト
    </button>
  );
}
