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
          <p className="text-xs uppercase tracking-[0.45em] text-fog">あなたのスタートを、見直す。</p>
          <h1 className="mt-6 text-4xl font-semibold tracking-tight leading-[1.05] sm:text-5xl lg:text-7xl">
            <span className="block">3歩で、</span>
            <span className="block whitespace-nowrap">スタートは決まる。</span>
          </h1>
          <p className="mt-6 max-w-xl text-base text-fog lg:text-lg">
            映像をアップロードするだけで、
            <br />
            接地・押し出し・切り返しを解析。
            <br />
            コーチ視点の改善ポイントが手に入ります。
          </p>
        </section>

        <section className="flex items-center justify-center">
          <LoginForm nextPath={searchParams?.next} />
        </section>
      </div>
    </main>
  );
}
