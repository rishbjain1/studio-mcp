import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "studio-mcp console",
  description: "Web console over the studio-mcp Model Context Protocol server",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
