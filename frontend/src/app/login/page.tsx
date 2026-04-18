import { LoginForm } from "@/components/login-form";

export default function LoginPage({
  searchParams
}: {
  searchParams?: { next?: string };
}) {
  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-16 text-bone">
      <div className="grid w-full max-w-6xl gap-10 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="flex flex-col justify-center">
          <p className="text-xs uppercase tracking-[0.45em] text-fog">スタート局面解析</p>
          <h1 className="mt-6 text-5xl font-semibold tracking-tight lg:text-7xl">
            レースが動き出す前に、
            <br />
            最初の3歩を見える化する。
          </h1>
          <p className="mt-6 max-w-xl text-base text-fog lg:text-lg">
            START AI は、スタート姿勢から最初の3歩までを整理して見返せる解析アプリです。
            会員登録後に、動画アップロード、解析、結果確認までをシンプルに進められます。
          </p>
          <p className="mt-4 max-w-xl text-sm text-fog lg:text-base">
            個人の解析履歴はアカウントごとに管理されます。継続して使う方は新規登録、案内を受けたデモ利用の方は共有された情報でログインしてください。
          </p>
        </section>

        <section className="flex items-center justify-center">
          <LoginForm nextPath={searchParams?.next} />
        </section>
      </div>
    </main>
  );
}
