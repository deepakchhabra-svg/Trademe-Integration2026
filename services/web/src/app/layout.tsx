import type { Metadata } from "next";
import { cookies } from "next/headers";
import "./globals.css";
import AppShell from "./_components/AppShell";
import { UISettingsProvider } from "./_components/UISettingsProvider";

// This app is an operations console and must always run in real-time mode
// (cookies-based auth headers; no static export).
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "RetailOS",
  description: "RetailOS operator console",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const c = cookies();
  const theme = (c.get("retailos_theme")?.value || "light").toLowerCase() === "dark" ? "dark" : "light";
  const density =
    (c.get("retailos_density")?.value || "compact").toLowerCase() === "comfortable" ? "comfortable" : "compact";

  return (
    <html lang="en" data-theme={theme} data-density={density}>
      <body className="antialiased">
        <UISettingsProvider initialTheme={theme} initialDensity={density}>
          <AppShell>{children}</AppShell>
        </UISettingsProvider>
      </body>
    </html>
  );
}
