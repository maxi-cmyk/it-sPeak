import assert from "node:assert/strict";
import test from "node:test";
import { createApiClient } from "../lib/api.js";

test("API client attaches a fresh Clerk bearer token", async () => {
  const originalFetch = globalThis.fetch;
  let request;
  globalThis.fetch = async (url, options) => {
    request = { url, options };
    return new Response("[]", { status: 200, headers: { "Content-Type": "application/json" } });
  };
  try {
    const client = createApiClient(async () => "clerk-session-token");
    await client.listProjects();
    assert.equal(request.options.headers.Authorization, "Bearer clerk-session-token");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("API client fails closed when Clerk has no active session", async () => {
  const client = createApiClient(async () => null);
  await assert.rejects(client.listProjects(), (error) => error.status === 401);
});
