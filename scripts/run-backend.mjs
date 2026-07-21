import { createInterface } from "node:readline";
import { existsSync, readFileSync } from "node:fs";
import { spawn, spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { tmpdir } from "node:os";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(scriptDir, "..");
const backendRoot = join(repositoryRoot, "backend");
const python = process.platform === "win32"
  ? join(backendRoot, ".venv", "Scripts", "python.exe")
  : join(backendRoot, ".venv", "bin", "python");
const redisServer = process.platform === "win32" ? "redis-server.exe" : "redis-server";
const redisCli = process.platform === "win32" ? "redis-cli.exe" : "redis-cli";
const children = [];
let shuttingDown = false;

function readBackendEnvironment() {
  const values = {};
  const path = join(backendRoot, ".env");
  if (!existsSync(path)) return values;
  for (const rawLine of readFileSync(path, "utf8").split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const separator = line.indexOf("=");
    if (separator < 1) continue;
    const key = line.slice(0, separator).trim();
    let value = line.slice(separator + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    values[key] = value;
  }
  return values;
}

function prefixOutput(stream, label) {
  if (!stream) return;
  createInterface({ input: stream }).on("line", (line) => {
    process.stdout.write(`[${label}] ${line}\n`);
  });
}

function startService(label, command, args, options = {}) {
  const child = spawn(command, args, {
    cwd: backendRoot,
    env: { ...process.env, ...options.env },
    stdio: ["ignore", "pipe", "pipe"],
  });
  children.push({ label, child, owned: options.owned !== false });
  prefixOutput(child.stdout, label);
  prefixOutput(child.stderr, label);
  child.on("error", (error) => {
    process.stderr.write(`[${label}] Failed to start: ${error.message}\n`);
  });
  return child;
}

function redisResponds(redisUrl) {
  const result = spawnSync(redisCli, ["-u", redisUrl, "ping"], {
    cwd: backendRoot,
    stdio: "ignore",
    timeout: 2000,
  });
  return result.status === 0;
}

function delay(milliseconds) {
  return new Promise((resolveDelay) => setTimeout(resolveDelay, milliseconds));
}

async function ensureRedis(redisUrl) {
  if (redisResponds(redisUrl)) {
    process.stdout.write("[redis] Reusing the running Redis instance.\n");
    return;
  }

  const parsed = new URL(redisUrl);
  if (!["localhost", "127.0.0.1", "::1"].includes(parsed.hostname)) {
    throw new Error(`Redis at ${parsed.hostname} is unavailable; refusing to replace a remote service with a local one.`);
  }
  const port = parsed.port || "6379";
  startService("redis", redisServer, ["--port", port, "--save", "", "--appendonly", "no"]);
  for (let attempt = 0; attempt < 25; attempt += 1) {
    await delay(200);
    if (redisResponds(redisUrl)) {
      process.stdout.write(`[redis] Ready on ${parsed.hostname}:${port}.\n`);
      return;
    }
  }
  throw new Error("Redis did not become ready within five seconds.");
}

async function shutdown(exitCode = 0) {
  if (shuttingDown) return;
  shuttingDown = true;
  process.stdout.write("\n[backend] Stopping services...\n");
  for (const { child, owned } of [...children].reverse()) {
    if (owned && child.exitCode === null) child.kill("SIGTERM");
  }
  await delay(1500);
  for (const { child, owned } of [...children].reverse()) {
    if (owned && child.exitCode === null) child.kill("SIGKILL");
  }
  process.exitCode = exitCode;
}

async function main() {
  if (!existsSync(python)) {
    throw new Error(`Backend virtual environment not found at ${python}. Run the README install steps first.`);
  }
  const fileEnvironment = readBackendEnvironment();
  const redisUrl = process.env.ITSPEAK_REDIS_URL || fileEnvironment.ITSPEAK_REDIS_URL || "redis://localhost:6379/0";
  await ensureRedis(redisUrl);

  const sharedEnvironment = { MPLCONFIGDIR: process.env.MPLCONFIGDIR || join(tmpdir(), "itspeak-matplotlib") };
  startService("api", python, ["-m", "uvicorn", "itspeak.api:app", "--host", "127.0.0.1", "--port", "8000"], { env: sharedEnvironment });
  startService("worker", python, ["-m", "celery", "-A", "itspeak.celery_app.celery_app", "worker", "--loglevel=info", "--pool=solo"], { env: sharedEnvironment });
  startService("beat", python, ["-m", "celery", "-A", "itspeak.celery_app.celery_app", "beat", "--loglevel=info"], { env: sharedEnvironment });

  process.stdout.write("[backend] API, worker, beat, and Redis are supervised in this terminal.\n");
  process.stdout.write("[backend] API: http://127.0.0.1:8000 — press Ctrl+C to stop.\n");

  for (const { label, child } of children) {
    child.on("exit", async (code, signal) => {
      if (shuttingDown) return;
      process.stderr.write(`[backend] ${label} exited unexpectedly (${signal || code}).\n`);
      await shutdown(code || 1);
    });
  }
}

process.on("SIGINT", () => shutdown(0));
process.on("SIGTERM", () => shutdown(0));

main().catch(async (error) => {
  process.stderr.write(`[backend] ${error.message}\n`);
  await shutdown(1);
});
