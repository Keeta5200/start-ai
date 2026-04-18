import Link from "next/link";
import { ReactNode } from "react";
import { LogoutButton } from "@/components/logout-button";

const navItems = [
  { href: "/", label: "ホーム" },
  { href: "/dashboard", label: "ダッシュボード" },
  { href: "/upload", label: "アップロード" }
];

export function AppShell({
  children,
  title,
  subtitle
}: {
  children: ReactNode;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="panel-grid min-h-screen bg-ink text-bone">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-6 py-6 lg:px-10">
        <header className="flex flex-col gap-6 border-b border-white/10 pb-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="animate-fade-rise">
            <p className="text-xs uppercase tracking-[0.45em] text-fog">START AI</p>
            <h1 className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight lg:text-6xl">
              {title}
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-fog lg:text-base">{subtitle}</p>
          </div>

          <nav className="flex items-center gap-3">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-full border border-white/10 bg-white/[0.03] px-4 py-2 text-sm text-bone transition hover:border-ember hover:bg-white/[0.06] hover:text-ember"
              >
                {item.label}
              </Link>
            ))}
            <LogoutButton />
          </nav>
        </header>

        <main className="flex-1 py-8">{children}</main>
      </div>
    </div>
  );
}
