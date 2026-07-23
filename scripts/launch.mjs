#!/usr/bin/env node
// Spawns a detached process and records its real Windows PID to a file.
// Needed because under Git Bash / MSYS, `$!` does not match the actual
// Windows PID, which breaks taskkill-based stop scripts.
import { spawn } from "node:child_process";
import { openSync, writeFileSync } from "node:fs";

const [pidFile, logFile, cwd, command, ...args] = process.argv.slice(2);

const out = openSync(logFile, "a");
const child = spawn(command, args, {
  cwd,
  stdio: ["ignore", out, out],
  detached: true,
  windowsHide: true,
});
writeFileSync(pidFile, String(child.pid));
child.unref();
