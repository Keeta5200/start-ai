import Link from "next/link";

export default function HomePage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-ink px-6 text-bone">
      <div className="max-w-4xl text-center">
        <p className="text-xs uppercase tracking-[0.45em] text-fog">START AI</p>
        <h1 className="mt-6 text-5xl font-semibold tracking-tight lg:text-7xl">
          スタート局面を見える化し、
          <br />
          次の一本を速くする。
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-base text-fog lg:text-lg">
          START AI は、set から最初の3歩までの動きを整理し、
          接地、押し出し方向、切り返し、初期加速の流れをコーチ視点で振り返るための解析ツールです。
          会員登録後に動画アップロードと解析結果の保存をご利用いただけます。
        </p>
        <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Link
            href="/login"
            className="rounded-full bg-ember px-8 py-4 text-base font-semibold text-ink"
          >
            会員登録して始める
          </Link>
          <Link
            href="/dashboard"
            className="rounded-full border border-white/10 px-8 py-4 text-base text-bone"
          >
            ダッシュボードを見る
          </Link>
        </div>
      </div>
    </main>
  );
}
