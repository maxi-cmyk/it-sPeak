"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { SignInButton, SignUpButton, Show, UserButton } from "@clerk/nextjs";
import ThemeToggle from "@/components/ThemeToggle";

export default function Navbar({ backHref }) {
  const router = useRouter();
  return (
    <nav className="sticky top-0 z-40 border-b border-zinc-800 bg-zinc-950/95 backdrop-blur transition-colors duration-200" aria-label="Primary navigation">
      <div className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between px-4 sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          {backHref && (
            <button onClick={() => router.push(backHref)} className="icon-button" aria-label="Back">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M19 12H5M12 5l-7 7 7 7" />
              </svg>
            </button>
          )}
          <Link href="/" className="rounded-md text-xl font-bold tracking-tight text-zinc-50">
            it's<span className="text-accent">PEAK</span>
          </Link>
        </div>
        <div className="flex items-center gap-3">
          <ThemeToggle />
          <Show when="signed-out">
            <SignInButton>
              <button className="rounded-lg px-3 py-2 text-sm font-medium text-zinc-400 transition-colors hover:bg-zinc-900 hover:text-zinc-50">Sign in</button>
            </SignInButton>
            <SignUpButton>
              <button className="btn-primary min-h-9 px-3 py-2">Sign up</button>
            </SignUpButton>
          </Show>
          <Show when="signed-in"><UserButton /></Show>
        </div>
      </div>
    </nav>
  );
}
