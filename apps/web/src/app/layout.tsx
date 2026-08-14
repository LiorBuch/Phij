import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Phij TV",
  description: "Phij's finest moments",
};

export default function RootLayout({children}: Readonly<{children: React.ReactNode}>) {
  return <html lang="en"><body>{children}</body></html>;
}
