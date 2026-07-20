import {ClerkProvider} from "@clerk/nextjs";
import "./globals.css";

export const metadata = {
  title: "ItsPeak",
  description: "AI-powered speech coaching",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-zinc-950 text-zinc-50 antialiased">
        <ClerkProvider>
          {children}
        </ClerkProvider>
      </body>
    </html>
  );
}