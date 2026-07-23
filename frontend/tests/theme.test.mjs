import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { createThemeInitializerScript, DARK_THEME, LIGHT_THEME, normalizeTheme, THEME_STORAGE_KEY } from "../lib/theme.mjs";

test("theme values default safely to light", () => {
  assert.equal(normalizeTheme(DARK_THEME), DARK_THEME);
  assert.equal(normalizeTheme(LIGHT_THEME), LIGHT_THEME);
  assert.equal(normalizeTheme("sepia"), LIGHT_THEME);
});

test("theme initializer restores only supported stored values", () => {
  const script = createThemeInitializerScript();
  assert.match(script, new RegExp(THEME_STORAGE_KEY));
  assert.match(script, /dataset\.theme/);
  assert.match(script, /localStorage\.getItem/);
});

test("navbar exposes an accessible theme switch", async () => {
  const navbar = await readFile(new URL("../components/Navbar.js", import.meta.url), "utf8");
  const toggle = await readFile(new URL("../components/ThemeToggle.js", import.meta.url), "utf8");
  const styles = await readFile(new URL("../app/globals.css", import.meta.url), "utf8");

  assert.equal(navbar.includes("<ThemeToggle />"), true);
  assert.equal(toggle.includes('role="switch"'), true);
  assert.equal(toggle.includes("aria-checked={dark}"), true);
  assert.equal(styles.includes(':root[data-theme="dark"]'), true);
  assert.equal(styles.includes("--zinc-950-rgb: 9 9 11"), true);
  assert.equal(styles.includes("--zinc-900-rgb: 24 24 27"), true);
  assert.equal(styles.includes("--zinc-50-rgb: 250 250 250"), true);
  assert.equal(styles.includes("--performance-cobalt: #2563eb"), true);
  assert.match(styles, /:root\[data-theme="dark"\] \.theme-toggle \{[\s\S]*?border-color: var\(--text-muted\);[\s\S]*?background: var\(--surface\);[\s\S]*?color: var\(--performance-cobalt-soft\);/);
  assert.match(styles, /:root\[data-theme="dark"\] \.theme-toggle__thumb \{[\s\S]*?background: var\(--text-primary\);/);
});
