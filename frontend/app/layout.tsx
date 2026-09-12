import type { Metadata, Viewport } from "next";
import { Suspense } from "react";
import { AppShell } from "@/components/app-shell";
import "./globals.css";

export const metadata: Metadata = {
  title: "Oshi Dashboard",
  description: "A private personal oshi-information dashboard.",
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "#0B0D10",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <Suspense
          fallback={
            <div className="boot-state" role="status">
              <strong>OSHI.</strong>
              <p>Opening your dashboard…</p>
            </div>
          }
        >
          <AppShell>{children}</AppShell>
        </Suspense>
      </body>
    </html>
  );
}
