import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Dog Cam",
  description: "A low-latency view of your dog",
};

export default function RootLayout({children}: Readonly<{children: React.ReactNode}>) {
  return <html lang="en"><body>{children}</body></html>;
}
