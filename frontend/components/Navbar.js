"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function Navbar({ backHref }) {
  const router = useRouter();
  return (
    <nav className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 bg-zinc-950 sticky top-0 z-10">
      <div className="flex items-center gap-4">
        {backHref && (
          <button
            onClick={() => router.push(backHref)}
            className="text-zinc-400 hover:text-zinc-50 transition-colors mr-1"
            aria-label="Back"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5M12 5l-7 7 7 7" />
            </svg>
          </button>
        )}
        <Link href="/" className="text-xl font-bold tracking-tight text-zinc-50 hover:text-violet-400 transition-colors">
          ItsPeak
        </Link>
      </div>
      <div className="flex items-center gap-3">
        <button className="text-zinc-400 hover:text-zinc-50 transition-colors p-1" aria-label="Notifications">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
        </button>
        <div className="w-8 h-8 rounded-full bg-violet-600 flex items-center justify-center text-sm font-semibold text-white select-none">
          M
        </div>
      </div>
    </nav>
  );
}
