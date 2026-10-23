import type { Metadata } from "next";

import "./globals.css";
import { TwiniDrawer } from "@/components/twini-drawer";

export const metadata: Metadata = {
  title: "TwinBean | Kidney digital twin",
  description: "Secure access to the TwinBean kidney digital twin research prototype.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}<TwiniDrawer /></body>
    </html>
  );
}
