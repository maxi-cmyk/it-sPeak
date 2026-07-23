import {ClerkProvider} from "@clerk/nextjs";
import { createThemeInitializerScript } from "@/lib/theme.mjs";
import "./globals.css";

export const metadata = {
  title: "it'sPEAK",
  description: "Focused rehearsal feedback for measurable speaking improvement.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" data-theme="light" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: createThemeInitializerScript() }} />
      </head>
      <body className="min-h-screen antialiased">
        <ClerkProvider>
          {children}
        </ClerkProvider>
      </body>
    </html>
  );
}
