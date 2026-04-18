"use client";

import { FormEvent, useState } from "react";
import { ApiError, login, register } from "@/lib/api";
import { buildAuthCookie, buildTokenCookie } from "@/lib/auth";

export function LoginForm({ nextPath }: { nextPath?: string }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("会員登録またはログイン後に、動画アップロードと解析をご利用いただけます。");
  const [isSubmitting, setIsSubmitting] = useState(false);

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

      localStorage.setItem("start-ai-token", authResponse.access_token);
      localStorage.setItem("start-ai-user", JSON.stringify(authResponse.user));
      document.cookie = buildAuthCookie();
      document.cookie = buildTokenCookie(authResponse.access_token);
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
      <h2 className="mt-3 text-4xl font-semibold">START AI に入る</h2>
      <p className="mt-3 text-sm text-fog">{message}</p>

      <div className="mt-8 space-y-4">
        <input
          className="w-full rounded-2xl border border-white/10 bg-transparent px-4 py-4 text-base outline-none placeholder:text-fog focus:border-ember"
          type="email"
          name="email"
          autoComplete="username"
          placeholder="メールアドレス"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <input
          className="w-full rounded-2xl border border-white/10 bg-transparent px-4 py-4 text-base outline-none placeholder:text-fog focus:border-ember"
          type="password"
          name="password"
          autoComplete={mode === "login" ? "current-password" : "new-password"}
          placeholder="パスワード"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </div>

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

      <p className="mt-5 text-xs leading-6 text-fog">
        会員の方はログイン、新しくご利用の方はアカウント作成へお進みください。デモ利用の方は、共有された案内に沿ってログインしてください。
      </p>
    </form>
  );
}
