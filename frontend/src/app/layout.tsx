import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "START AI",
  description: "スタート局面の解析アプリ"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
