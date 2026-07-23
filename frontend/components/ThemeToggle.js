"use client";

import { useEffect, useState } from "react";
import { DARK_THEME, LIGHT_THEME, normalizeTheme, THEME_STORAGE_KEY } from "@/lib/theme.mjs";

export default function ThemeToggle() {
  const [theme, setTheme] = useState(LIGHT_THEME);

  useEffect(() => {
    setTheme(normalizeTheme(document.documentElement.dataset.theme));
  }, []);

  function toggleTheme() {
    const currentTheme = normalizeTheme(document.documentElement.dataset.theme);
    const nextTheme = currentTheme === DARK_THEME ? LIGHT_THEME : DARK_THEME;
    document.documentElement.dataset.theme = nextTheme;
    try {
      localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
    } catch {
      // The selected theme still applies for this page when storage is unavailable.
    }
    setTheme(nextTheme);
  }

  const dark = theme === DARK_THEME;
  const label = dark ? "Switch to light mode" : "Switch to dark mode";

  return (
    <button
      type="button"
      role="switch"
      aria-checked={dark}
      aria-label={label}
      title={label}
      className="theme-toggle"
      onClick={toggleTheme}
    >
      <span className="theme-toggle__icon theme-toggle__sun" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="3.5" />
          <path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.65 17.65l1.42 1.42M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.65 6.35l1.42-1.42" />
        </svg>
      </span>
      <span className="theme-toggle__icon theme-toggle__moon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M20.5 14.5A8.4 8.4 0 0 1 9.5 3.5 8.5 8.5 0 1 0 20.5 14.5Z" />
          <path d="M18 5v2M17 6h2" />
        </svg>
      </span>
      <span className="theme-toggle__thumb" aria-hidden="true" />
    </button>
  );
}
