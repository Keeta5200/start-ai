"use client";

import {
  buildExpiredAuthCookie,
  buildExpiredTokenCookie,
  clearPendingAnalysis,
  removeLocalStorageItem,
  removeSessionStorageItem,
} from "@/lib/auth";

export function LogoutButton() {
  function handleLogout() {
    removeLocalStorageItem("start-ai-token");
    removeLocalStorageItem("start-ai-user");
    clearPendingAnalysis();
    removeSessionStorageItem("start-ai-token");
    removeSessionStorageItem("start-ai-user");
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
