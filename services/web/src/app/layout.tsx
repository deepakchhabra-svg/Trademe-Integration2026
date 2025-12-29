import type { Metadata } from "next";
import "./globals.css";
import AppShell from "./_components/AppShell";

// This app is an operations console and must always run in real-time mode
// (cookies-based auth headers; no static export).
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "RetailOS Admin",
  description: "RetailOS operations console",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
