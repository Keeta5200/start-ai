"use client";

import { FormEvent, useEffect, useState } from "react";
import { ApiError, login, register } from "@/lib/api";
import {
  LAST_EMAIL_KEY,
  REMEMBER_ME_KEY,
  buildAuthCookie,
  buildTokenCookie,
  getLocalStorageItem,
  removeLocalStorageItem,
  removeSessionStorageItem,
  setLocalStorageItem,
  setSessionStorageItem,
} from "@/lib/auth";

export function LoginForm({ nextPath }: { nextPath?: string }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const rememberedEmail = getLocalStorageItem(LAST_EMAIL_KEY);
    const rememberedPreference = getLocalStorageItem(REMEMBER_ME_KEY);

    if (rememberedEmail) {
      setEmail(rememberedEmail);
    }
    if (rememberedPreference !== null) {
      setRememberMe(rememberedPreference === "true");
    }
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);

    try {
      let authResponse;
      if (mode === "login") {
        try {
          authResponse = await login({ email, password });
        } catch (error) {
          const isDemoLogin =
            email === "demo@startai.app" && password === "password123";
          if (isDemoLogin && error instanceof ApiError && error.status === 401) {
            await register({ email, password });
            authResponse = await login({ email, password });
          } else {
            throw error;
          }
        }
      } else {
        authResponse = await register({ email, password });
      }

      if (rememberMe) {
        removeSessionStorageItem("start-ai-token");
        removeSessionStorageItem("start-ai-user");
        setLocalStorageItem("start-ai-token", authResponse.access_token);
        setLocalStorageItem("start-ai-user", JSON.stringify(authResponse.user));
      } else {
        removeLocalStorageItem("start-ai-token");
        removeLocalStorageItem("start-ai-user");
        setSessionStorageItem("start-ai-token", authResponse.access_token);
        setSessionStorageItem("start-ai-user", JSON.stringify(authResponse.user));
      }

      if (rememberMe) {
        setLocalStorageItem(LAST_EMAIL_KEY, authResponse.user.email);
      } else {
        removeLocalStorageItem(LAST_EMAIL_KEY);
      }
      setLocalStorageItem(REMEMBER_ME_KEY, String(rememberMe));

      document.cookie = buildAuthCookie(rememberMe);
      document.cookie = buildTokenCookie(authResponse.access_token, rememberMe);
      setMessage(
        `${mode === "login" ? "ログインしました" : "登録しました"}: ${authResponse.user.email}`,
      );
      window.location.href = nextPath && nextPath.startsWith("/") ? nextPath : "/dashboard";
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 401) {
          setMessage("メールアドレスまたはパスワードが違います。");
        } else if (error.status === 400) {
          setMessage(error.detail === "Email already exists"
            ? "このメールアドレスはすでに登録されています。ログインに切り替えてください。"
            : "入力内容を確認してください。");
        } else {
          setMessage(`ログインに失敗しました。${error.detail ?? "バックエンドの状態を確認してください。"}`);
        }
      } else {
        setMessage("ログインに失敗しました。バックエンドの起動状況を確認してください。");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      autoComplete="on"
      className="w-full max-w-md rounded-[2rem] border border-white/10 bg-white/5 p-8 shadow-panel"
    >
      <p className="text-xs uppercase tracking-[0.35em] text-fog">ログイン</p>
      <h2 className="mt-3 text-4xl font-semibold">ログインして分析をはじめる</h2>
      <p className="mt-3 text-sm text-fog">
        会員登録またはログイン後に、
        動画アップロードと解析をご利用いただけます。
      </p>
      {message ? <p className="mt-3 text-sm text-fog">{message}</p> : null}

      <div className="mt-8 space-y-4">
        <input
          className="w-full rounded-2xl border border-white/10 bg-transparent px-4 py-4 text-base outline-none placeholder:text-fog focus:border-ember"
          type="email"
          id="email"
          name="username"
          autoComplete="username"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          inputMode="email"
          placeholder="メールアドレス"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <input
          className="w-full rounded-2xl border border-white/10 bg-transparent px-4 py-4 text-base outline-none placeholder:text-fog focus:border-ember"
          type="password"
          id="password"
          name="password"
          autoComplete={mode === "login" ? "current-password" : "new-password"}
          placeholder="パスワード"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </div>

      {mode === "login" ? (
        <label className="mt-5 flex items-center gap-3 text-sm text-fog">
          <input
            type="checkbox"
            checked={rememberMe}
            onChange={(event) => setRememberMe(event.target.checked)}
            className="h-4 w-4 rounded border-white/20 bg-transparent accent-ember"
          />
          <span>30日間ログイン状態を保持する</span>
        </label>
      ) : null}

      <button
        type="submit"
        disabled={isSubmitting}
        className="mt-8 w-full rounded-full bg-ember px-5 py-4 text-base font-semibold text-ink transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSubmitting ? "処理中..." : mode === "login" ? "ログイン" : "アカウント作成"}
      </button>

      <button
        type="button"
        onClick={() => setMode(mode === "login" ? "register" : "login")}
        className="mt-4 text-sm text-fog transition hover:text-bone"
      >
        {mode === "login"
          ? "アカウントがない場合は新規登録"
          : "すでにアカウントがある場合はログイン"}
      </button>

      <div className="mt-5 border-t border-white/10 pt-5">
        <p className="text-xs leading-6 text-fog">
        メールアドレス欄をタップしたときに保存済みの候補が出る場合は、ブラウザや端末のパスワード保存機能もそのままご利用いただけます。
        </p>
      </div>
    </form>
  );
}
