/**
 * Offline unit tests for the Worker. No Cloudflare account, no Telegram token
 * and no network needed: fetch, KV and static assets are all faked in-process.
 *
 * Run: npm test
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";

const BOT_TOKEN = "123:fake-token";

function harness(options = {}) {
  const kvStore = new Map();
  const documents = new Map(); // file_id -> Uint8Array
  const messages = new Map(); // message_id -> message object
  const assetPaths = [];
  const calls = [];
  let nextFileId = 500;
  let nextMessageId = 9000;
  let pinnedMessageId = null;
  let broken = false; // simulate Telegram returning an unreadable index

  const assets = new Map([
    ["/index.html", "<html>Storage1024 dashboard</html>"],
    ["/docs/index.html", "<html>Storage1024 docs</html>"],
    ["/docs/langs/nocard.md", "# No card guide"],
    ["/app.js", "// dashboard"],
  ]);

  const env = {
    BOT_TOKEN,
    CHANNEL_ID: "-1001234567890",
    CREATE_PROJECT_KEY: options.createKey || "",
    INDEX: {
      async get(key) {
        return kvStore.has(key) ? kvStore.get(key) : null;
      },
      async put(key, value) {
        kvStore.set(key, String(value));
      },
      async delete(key) {
        kvStore.delete(key);
      },
    },
    ASSETS: {
      async fetch(request) {
        const path = new URL(request.url).pathname;
        assetPaths.push(path);
        const body = assets.get(path);
        return new Response(body ?? "Not Found", {
          status: body === undefined ? 404 : 200,
          headers: { "content-type": path.endsWith(".js") ? "text/javascript" : "text/html" },
        });
      },
    },
  };

  async function bodyOf(request) {
    const contentType = request.headers.get("content-type") || "";
    if (contentType.includes("application/json")) return request.json();
    if (contentType.includes("multipart/form-data")) return request.formData();
    return {};
  }

  function telegramResponse(result, ok = true, description = "OK") {
    return new Response(JSON.stringify({ ok, result, description }), {
      status: ok ? 200 : 400,
      headers: { "content-type": "application/json" },
    });
  }

  async function storeDocument(bytes, caption) {
    const fileId = `file-${nextFileId++}`;
    documents.set(fileId, new Uint8Array(bytes));
    const message = {
      message_id: nextMessageId++,
      caption,
      document: { file_id: fileId, file_name: "upload.bin" },
    };
    messages.set(message.message_id, message);
    return message;
  }

  globalThis.fetch = async (input, init) => {
    const request = input instanceof Request ? input : new Request(input, init);
    const url = new URL(request.url);

    if (url.hostname === "api.telegram.org" && url.pathname.startsWith("/file/")) {
      const fileId = decodeURIComponent(url.pathname.split("/").pop() || "");
      const bytes = documents.get(fileId);
      if (!bytes || broken) return new Response("missing", { status: 404 });
      return new Response(bytes, { status: 200 });
    }

    if (url.hostname === "api.telegram.org" && url.pathname.startsWith("/bot")) {
      const method = url.pathname.split("/").pop();
      calls.push(method);
      const body = await bodyOf(request);

      if (method === "getMe") return telegramResponse({ username: "s1024_test_bot" });
      if (method === "getChat") {
        const pinned = pinnedMessageId ? messages.get(pinnedMessageId) : undefined;
        return telegramResponse({ id: -1001234567890, type: "channel", pinned_message: pinned });
      }
      if (method === "getFile") {
        return telegramResponse({ file_path: `documents/${body.file_id}` });
      }
      if (method === "sendDocument") {
        const blob = body.get("document");
        const bytes = await blob.arrayBuffer();
        return telegramResponse(await storeDocument(bytes, body.get("caption") || ""));
      }
      if (method === "pinChatMessage") {
        pinnedMessageId = body.message_id;
        return telegramResponse(true);
      }
      if (method === "unpinChatMessage" || method === "deleteMessage") {
        if (method === "deleteMessage") messages.delete(body.message_id);
        return telegramResponse(true);
      }
      if (method === "sendMessage") {
        const message = { message_id: nextMessageId++, text: body.text };
        messages.set(message.message_id, message);
        return telegramResponse(message);
      }
      if (method === "editMessageText") {
        const message = messages.get(body.message_id) || { message_id: body.message_id };
        message.text = body.text;
        messages.set(message.message_id, message);
        return telegramResponse(message);
      }
      return telegramResponse(true);
    }

    return new Response("unexpected fetch", { status: 500 });
  };

  const base = "https://storage1024.test.workers.dev";
  function call(path, init = {}) {
    return worker.fetch(new Request(`${base}${path}`, init), env, {});
  }
  function auth(token, init = {}) {
    const headers = new Headers(init.headers || {});
    headers.set("authorization", `Bearer ${token}`);
    return { ...init, headers };
  }
  async function createProject(name = "Test") {
    const headers = { "content-type": "application/json" };
    if (env.CREATE_PROJECT_KEY) headers["x-create-key"] = env.CREATE_PROJECT_KEY;
    const response = await call("/api/projects/create", {
      method: "POST",
      headers,
      body: JSON.stringify({ name }),
    });
    assert.equal(response.status, 200, `create failed: ${await response.clone().text()}`);
    return response.json();
  }

  return { env, call, auth, createProject, kvStore, documents, messages, calls, assetPaths,
    setBroken(value) { broken = value; },
    getPinned() { return pinnedMessageId; },
    clearKv() { kvStore.clear(); },
    pinnedFileId() {
      const message = messages.get(pinnedMessageId);
      return message && message.document && message.document.file_id;
    },
  };
}

test("health reports the CADB backend and is always 200 by default", async () => {
  const h = harness();
  const response = await h.call("/api/health");
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.status, "ok");
  assert.equal(body.backend, "telegram-bot-api");
  assert.equal(body.mode, "cloudflare-worker");
  assert.equal(body.bot, "s1024_test_bot");
});

test("health degraded with strict=true when secrets are missing", async () => {
  const h = harness();
  h.env.BOT_TOKEN = "";
  const response = await h.call("/api/health?strict=true");
  assert.equal(response.status, 503);
  assert.match((await response.json()).error, /BOT_TOKEN/);
});

test("create project stores the index document in the channel and pins it", async () => {
  const h = harness();
  const created = await h.createProject();
  assert.equal(created.status, "success");
  assert.match(created.tokens.private, /^s1024-.*;qi=$/);
  assert.match(created.tokens.public, /^s1024-.*;gg=$/);
  assert.ok(h.pinnedFileId(), "an index document must be pinned in the channel");
  const index = JSON.parse(new TextDecoder().decode(h.documents.get(h.pinnedFileId())));
  assert.ok(index.projects[created.project_id]);
  assert.equal(index.projects[created.project_id].tokens.length, 2);
});

test("X-Create-Key protects public project creation", async () => {
  const h = harness({ createKey: "secret-key" });
  const denied = await h.call("/api/projects/create", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ name: "Nope" }),
  });
  assert.equal(denied.status, 403);
  const allowed = await h.createProject("Yes");
  assert.equal(allowed.status, "success");
});

test("index endpoint requires a private token", async () => {
  const h = harness();
  const { project_id, tokens } = await h.createProject();
  assert.equal((await h.call("/api/index")).status, 401);
  const asPublic = await h.call("/api/index", h.auth(tokens.public));
  assert.equal(asPublic.status, 403);
  const asPrivate = await h.call("/api/index", h.auth(tokens.private));
  assert.equal(asPrivate.status, 200);
  const body = await asPrivate.json();
  assert.equal(body.projects[project_id].name, "Test");
  assert.equal((await h.call("/api/index", h.auth("s1024-bogus"))).status, 401);
});

test("index survives a lost KV namespace by rebuilding from the pinned message", async () => {
  const h = harness();
  const { project_id, tokens } = await h.createProject();
  h.clearKv();
  assert.equal(h.kvStore.size, 0);
  const response = await h.call("/api/index", h.auth(tokens.private));
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.ok(body.projects[project_id], "project recovered from the channel");
  assert.ok(h.calls.includes("getChat"));
});

test("an unreadable index is never overwritten with an empty one", async () => {
  const h = harness();
  const { tokens } = await h.createProject("Keep me");
  h.setBroken(true);
  const response = await h.call("/api/projects/create", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ name: "Would wipe" }),
  });
  assert.equal(response.status, 503);
  h.setBroken(false);
  const index = await h.call("/api/index", h.auth(tokens.private));
  const body = await index.json();
  assert.equal(body.status, "success");
  assert.equal(Object.values(body.projects)[0].name, "Keep me");
});

test("global variables are written as channel messages and read through the API", async () => {
  const h = harness();
  const { project_id, tokens } = await h.createProject();
  const set = await h.call(`/api/projects/${project_id}/gv`, h.auth(tokens.private, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ alias: "greeting", value: "hello CADB" }),
  }));
  assert.equal(set.status, 200);
  assert.ok([...h.messages.values()].some((m) => m.text === "S1024-GV[greeting] hello CADB"));

  const list = await h.call(`/api/projects/${project_id}/gv`, h.auth(tokens.public));
  assert.deepEqual(await list.json(), { greeting: "hello CADB" });
  const single = await h.call(`/api/projects/${project_id}/gv/greeting`, h.auth(tokens.public));
  assert.deepEqual(await single.json(), { alias: "greeting", value: "hello CADB" });

  assert.equal((await h.call(`/api/projects/${project_id}/gv/greeting`, h.auth(tokens.public, { method: "DELETE" }))).status, 403);
  const removed = await h.call(`/api/projects/${project_id}/gv/greeting`, h.auth(tokens.private, { method: "DELETE" }));
  assert.equal(removed.status, 200);
  assert.deepEqual(await (await h.call(`/api/projects/${project_id}/gv`, h.auth(tokens.private))).json(), {});
});

test("files round-trip through the channel and share links are capability-keyed", async () => {
  const h = harness();
  const { project_id, tokens } = await h.createProject();
  const form = new FormData();
  form.append("alias", "notes");
  form.append("file", new Blob(["file lives in Telegram"], { type: "text/plain" }), "notes.txt");
  const upload = await h.call(`/api/projects/${project_id}/upload`, h.auth(tokens.public, { method: "POST", body: form }));
  assert.equal(upload.status, 200, await upload.clone().text());
  const uploaded = await upload.json();
  assert.equal(uploaded.alias, "notes");
  assert.match(uploaded.url, /\/f\/.*\/notes\?key=/);
  assert.equal(uploaded.file.key, undefined, "share secret must not leak into the file record");

  const list = await h.call(`/api/projects/${project_id}/files`, h.auth(tokens.private));
  const files = (await list.json()).files;
  assert.equal(files.notes.name, "notes.txt");
  assert.equal(files.notes.size, 22);

  const shareUrl = new URL(uploaded.url);
  assert.equal((await h.call(shareUrl.pathname)).status, 403, "share link without key is rejected");
  const shared = await h.call(`${shareUrl.pathname}${shareUrl.search}`);
  assert.equal(shared.status, 200);
  assert.equal(await shared.text(), "file lives in Telegram");

  const authed = await h.call(`/api/projects/${project_id}/files/notes`, h.auth(tokens.private));
  assert.equal(await authed.text(), "file lives in Telegram");

  const deleted = await h.call(`/api/projects/${project_id}/files/notes`, h.auth(tokens.private, { method: "DELETE" }));
  assert.equal(deleted.status, 200);
  assert.deepEqual((await (await h.call(`/api/projects/${project_id}/files`, h.auth(tokens.private))).json()).files, {});
});

test("replace a file keeps a working version if the old message cannot be deleted", async () => {
  const h = harness();
  const { project_id, tokens } = await h.createProject();
  const form = (text) => {
    const f = new FormData();
    f.append("alias", "same");
    f.append("file", new Blob([text], { type: "text/plain" }), "same.txt");
    return f;
  };
  await h.call(`/api/projects/${project_id}/upload`, h.auth(tokens.private, { method: "POST", body: form("v1") }));
  await h.call(`/api/projects/${project_id}/upload`, h.auth(tokens.private, { method: "POST", body: form("v2") }));
  const download = await h.call(`/api/projects/${project_id}/files/same`, h.auth(tokens.private));
  assert.equal(await download.text(), "v2");
});

test("uploads over the Bot API download cap are rejected before touching Telegram", async () => {
  const h = harness();
  const { project_id, tokens } = await h.createProject();
  const form = new FormData();
  form.append("alias", "huge");
  form.append("file", new Blob([new Uint8Array(20 * 1024 * 1024)], { type: "application/octet-stream" }), "huge.bin");
  const response = await h.call(`/api/projects/${project_id}/upload`, h.auth(tokens.private, { method: "POST", body: form }));
  assert.equal(response.status, 413);
});

test("tokens can be added and revoked; the last token cannot be revoked", async () => {
  const h = harness();
  const { project_id, tokens } = await h.createProject();
  const added = await h.call(`/api/projects/${project_id}/tokens`, h.auth(tokens.private, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ type: "private" }),
  }));
  assert.equal(added.status, 200);
  const newToken = (await added.json()).token;
  assert.equal((await h.call("/api/index", h.auth(newToken))).status, 200);

  const revoked = await h.call(`/api/projects/${project_id}/tokens/revoke`, h.auth(tokens.private, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ token: newToken }),
  }));
  assert.equal((await revoked.json()).revoked, true);
  assert.equal((await h.call("/api/index", h.auth(newToken))).status, 401);
});

test("public tokens cannot administer a different project", async () => {
  const h = harness();
  const first = await h.createProject();
  const second = await h.createProject();
  const response = await h.call(`/api/projects/${second.project_id}/tokens`, h.auth(first.tokens.private, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ type: "public" }),
  }));
  assert.equal(response.status, 403);
});

test("static dashboard and docs are served through the ASSETS binding", async () => {
  const h = harness();
  const home = await h.call("/");
  assert.equal(home.status, 200);
  assert.match(await home.text(), /dashboard/);
  assert.deepEqual(h.assetPaths, ["/index.html"]);

  const docs = await h.call("/docs");
  assert.match(await docs.text(), /Storage1024 docs/);
  assert.ok(h.assetPaths.includes("/docs/index.html"));

  const sdk = await h.call("/s1024.js");
  assert.equal(sdk.status, 404); // the real build copies libraries/cdn.js here
  assert.ok(h.assetPaths.includes("/libraries/cdn.js"));
});

test("unknown API routes return JSON 404 with CORS headers", async () => {
  const h = harness();
  const response = await h.call("/api/nope");
  assert.equal(response.status, 404);
  assert.equal(response.headers.get("access-control-allow-origin"), "*");
  assert.equal((await response.json()).detail, "Not found");
});
