import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "My Stock | 개인 투자 플랫폼",
  description: "거시경제 흐름을 읽고, 데이터 기반으로 투자하는 개인 투자 플랫폼",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className="h-full antialiased">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-full md:flex bg-surface text-on-surface">
        <Sidebar />

        {/* Main Content */}
        <main className="pl-0 md:pl-64 md:flex-1 min-h-screen min-w-0">
          <div className="px-4 pt-16 pb-8 md:px-12 md:py-10 max-w-[1200px]">{children}</div>
        </main>
      </body>
    </html>
  );
}
