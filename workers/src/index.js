/**
 * Storage1024 on Cloudflare Workers — CADB (Chat App DataBase) edition.
 *
 * The Telegram channel is the database:
 *   - every uploaded file is a document message in the channel,
 *   - every global variable is a text message in the channel,
 *   - the project index is a JSON document pinned in the channel.
 * Workers KV only caches the *pointer* (file_id / message_id) to that pinned
 * document, so a lost KV namespace can always be rebuilt from the channel.
 *
 * This is the free-plan replacement for the Python/Telethon bridge. It uses
 * the Telegram Bot API because a Worker cannot open an MTProto connection.
 */

const TG_API = "https://api.telegram.org";
const INDEX_CAPTION = "S1024-INDEX-V2";
const GV_PREFIX = "S1024-GV";
const MAX_ALIAS_LENGTH = 120;
// Bot API `getFile` refuses to download files bigger than 20 MB. We stay under
// that with a small margin, otherwise files could be uploaded but never read.
const MAX_FILE_BYTES = 19 * 1024 * 1024;
const MAX_GV_LENGTH = 3800;
const PUBLIC_SCOPES = new Set(["upload", "get_gv", "download"]);

/* -------------------------------------------------------------------------- */
/* small helpers                                                              */
/* -------------------------------------------------------------------------- */

function base64url(bytes) {
  let raw = "";
  for (const b of bytes) raw += String.fromCharCode(b);
  return btoa(raw).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function newToken(type) {
  const bytes = crypto.getRandomValues(new Uint8Array(24));
  return `s1024-${base64url(bytes)};${type === "private" ? "qi" : "gg"}=`;
}

function newSecret() {
  return base64url(crypto.getRandomValues(new Uint8Array(18)));
}

function newProjectId(projects) {
  for (let i = 0; i < 500; i += 1) {
    const id = String(Math.floor(Math.random() * 9000) + 1000);
    if (!(id in projects)) return id;
  }
  throw new Error("Could not allocate a project id");
}

function json(data, status = 200, headers = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "access-control-allow-origin": "*",
      "cache-control": "no-store",
      ...headers,
    },
  });
}

function fail(status, detail) {
  return json({ detail }, status);
}

function validateAlias(value) {
  const alias = String(value ?? "").trim();
  if (!alias) throw new Error("Alias is required");
  if (alias.length > MAX_ALIAS_LENGTH) {
    throw new Error(`Alias must be at most ${MAX_ALIAS_LENGTH} characters`);
  }
  if (alias === "." || alias === ".." || /[\x00-\x1f/\\]/.test(alias)) {
    throw new Error("Alias contains invalid characters");
  }
  return alias;
}

function safeFilename(name) {
  return String(name || "file").replace(/[\x00-\x1f/\\]/g, "_").slice(0, 180) || "file";
}

function contentType(name) {
  const ext = String(name).toLowerCase().split(".").pop();
  const types = {
    txt: "text/plain", json: "application/json", md: "text/markdown",
    html: "text/html", css: "text/css", js: "text/javascript",
    png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg",
    gif: "image/gif", webp: "image/webp", svg: "image/svg+xml",
    pdf: "application/pdf", zip: "application/zip", mp3: "audio/mpeg",
    mp4: "video/mp4", csv: "text/csv", py: "text/x-python",
  };
  return types[ext] || "application/octet-stream";
}

function cors(response) {
  const headers = new Headers(response.headers);
  headers.set("access-control-allow-origin", "*");
  headers.set("access-control-allow-methods", "GET, POST, DELETE, OPTIONS");
  headers.set("access-control-allow-headers", "authorization, content-type, x-create-key");
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

/* -------------------------------------------------------------------------- */
/* Telegram Bot API                                                           */
/* -------------------------------------------------------------------------- */

function tgUrl(env, method) {
  if (!env.BOT_TOKEN) throw new Error("BOT_TOKEN is not configured");
  return `${TG_API}/bot${env.BOT_TOKEN}/${method}`;
}

async function postTelegram(env, method, init) {
  // Telegram rate-limits messages per chat (HTTP 429 + retry_after). Waiting
  // costs no CPU time on Workers, so a short retry is much better than a 503.
  for (let attempt = 0; attempt < 4; attempt += 1) {
    const response = await fetch(tgUrl(env, method), init);
    const data = await response.json().catch(() => ({}));
    if (response.status === 429 && attempt < 3) {
      const seconds = Number(data.parameters?.retry_after || 1);
      await new Promise((resolve) => setTimeout(resolve, Math.min(seconds, 20) * 1000 + 100));
      continue;
    }
    if (!response.ok || !data.ok) {
      throw new Error(`Telegram ${method}: ${data.description || response.status}`);
    }
    return data.result;
  }
  throw new Error(`Telegram ${method}: rate limited`);
}

function tg(env, method, payload = {}) {
  return postTelegram(env, method, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
}

function tgForm(env, method, form) {
  return postTelegram(env, method, { method: "POST", body: form });
}

function documentForm(env, bytes, filename, mime, caption) {
  const form = new FormData();
  form.append("chat_id", String(env.CHANNEL_ID));
  form.append("disable_notification", "true");
  if (caption) form.append("caption", caption);
  form.append("document", new Blob([bytes], { type: mime }), filename);
  return form;
}

async function downloadTelegramFile(env, fileId) {
  const info = await tg(env, "getFile", { file_id: fileId });
  if (!info.file_path) throw new Error("Telegram returned no file_path");
  const response = await fetch(`${TG_API}/file/bot${env.BOT_TOKEN}/${info.file_path}`);
  if (!response.ok) throw new Error(`Telegram file download failed (${response.status})`);
  return response;
}

/* -------------------------------------------------------------------------- */
/* index: pinned JSON document in the channel, pointer cached in KV            */
/* -------------------------------------------------------------------------- */

function emptyIndex() {
  return { version: 2, next_id: 1001, projects: {} };
}

async function readIndexDocument(env, fileId) {
  const response = await downloadTelegramFile(env, fileId);
  const text = await response.text();
  const index = JSON.parse(text);
  if (!index || typeof index.projects !== "object" || index.projects === null) {
    throw new Error("Index document is malformed");
  }
  return index;
}

async function loadIndex(env) {
  let fileId = await env.INDEX.get("index_file_id");
  if (!fileId) {
    // Cold start / KV lost: the pinned message in the channel is the source of
    // truth, so the whole database is still recoverable from the chat.
    try {
      const chat = await tg(env, "getChat", { chat_id: env.CHANNEL_ID });
      const pinned = chat && chat.pinned_message;
      if (pinned && pinned.document && pinned.document.file_id) {
        fileId = pinned.document.file_id;
        await env.INDEX.put("index_file_id", fileId);
      }
    } catch (error) {
      console.warn("getChat/pinned_message lookup failed:", String(error));
    }
  }
  if (!fileId) return emptyIndex();
  // Deliberately NOT swallowed: an unreadable index must never be overwritten
  // with an empty one (that is how the original project lost data).
  return readIndexDocument(env, fileId);
}

async function saveIndex(env, index) {
  const payload = JSON.stringify(index);
  const bytes = new TextEncoder().encode(payload);
  const message = await tgForm(
    env,
    "sendDocument",
    documentForm(env, bytes, "storage1024-index.json", "application/json", INDEX_CAPTION),
  );
  const fileId = message && message.document && message.document.file_id;
  if (!fileId) throw new Error("sendDocument returned no file_id for the index");

  const previousMessageId = await env.INDEX.get("index_message_id");
  try {
    await tg(env, "pinChatMessage", {
      chat_id: env.CHANNEL_ID,
      message_id: message.message_id,
      disable_notification: true,
    });
    if (previousMessageId && Number(previousMessageId) !== message.message_id) {
      await tg(env, "unpinChatMessage", {
        chat_id: env.CHANNEL_ID,
        message_id: Number(previousMessageId),
      }).catch(() => {});
    }
  } catch (error) {
    // Pinning needs the "Pin messages" admin right. Without it the KV pointer
    // still works; only cold-start recovery degrades.
    console.warn("pinChatMessage failed (grant the bot Pin messages):", String(error));
  }

  await env.INDEX.put("index_file_id", fileId);
  await env.INDEX.put("index_message_id", String(message.message_id));
  return fileId;
}

/* -------------------------------------------------------------------------- */
/* auth                                                                       */
/* -------------------------------------------------------------------------- */

function bearer(request) {
  const header = request.headers.get("authorization") || "";
  return header.toLowerCase().startsWith("bearer ") ? header.slice(7).trim() : "";
}

function findAuth(index, token) {
  if (!token) return null;
  for (const [projectId, project] of Object.entries(index.projects)) {
    for (const entry of project.tokens || []) {
      if (entry.token === token) {
        return { projectId, project, type: entry.type };
      }
    }
  }
  return null;
}

function authorize(index, request, projectId, scope) {
  const token = bearer(request);
  if (!token) return { error: fail(401, "Missing bearer token") };
  const auth = findAuth(index, token);
  if (!auth) return { error: fail(401, "Invalid token") };
  if (auth.projectId !== projectId) {
    return { error: fail(403, "Token does not match project_id") };
  }
  if (auth.type !== "private" && !PUBLIC_SCOPES.has(scope)) {
    return { error: fail(403, "Scope restricted for Public tokens") };
  }
  return { auth };
}

function shareUrl(request, projectId, alias, key) {
  const url = new URL(request.url);
  const proto = (request.headers.get("x-forwarded-proto") || url.protocol.replace(":", "")).split(",")[0];
  const host = request.headers.get("x-forwarded-host") || url.host;
  return `${proto}://${host}/f/${encodeURIComponent(projectId)}/${encodeURIComponent(alias)}?key=${encodeURIComponent(key)}`;
}

function fileView(request, projectId, alias, record) {
  const view = { ...record };
  if (view.key) view.url = shareUrl(request, projectId, alias, view.key);
  delete view.key;
  delete view.mid;
  return view;
}

/* -------------------------------------------------------------------------- */
/* API routes                                                                 */
/* -------------------------------------------------------------------------- */

async function handleHealth(env, url) {
  const strict = url.searchParams.get("strict") === "true";
  if (!env.BOT_TOKEN || !env.CHANNEL_ID) {
    return json(
      { status: "degraded", error: "BOT_TOKEN and CHANNEL_ID secrets are required" },
      strict ? 503 : 200,
    );
  }
  try {
    const me = await tg(env, "getMe", {});
    const index = await loadIndex(env);
    return json({
      status: "ok",
      backend: "telegram-bot-api",
      mode: "cloudflare-worker",
      bot: me.username,
      projects: Object.keys(index.projects).length,
    });
  } catch (error) {
    return json(
      { status: "degraded", error: String(error.message || error) },
      strict ? 503 : 200,
    );
  }
}

async function createProject(env, request) {
  if (env.CREATE_PROJECT_KEY && request.headers.get("x-create-key") !== env.CREATE_PROJECT_KEY) {
    return fail(403, "Invalid X-Create-Key");
  }
  let body;
  try {
    body = await request.json();
  } catch {
    return fail(400, "Invalid JSON body");
  }
  const name = String((body && body.name) || "New Project").trim().slice(0, 120) || "New Project";
  const index = await loadIndex(env);
  const projectId = newProjectId(index.projects);
  const privateToken = newToken("private");
  const publicToken = newToken("public");
  index.projects[projectId] = {
    name,
    created: Date.now(),
    tokens: [
      { token: privateToken, type: "private" },
      { token: publicToken, type: "public" },
    ],
    files: {},
    global_vars: {},
  };
  await saveIndex(env, index);
  return json({
    status: "success",
    project_id: projectId,
    tokens: { private: privateToken, public: publicToken },
  });
}

async function getIndex(env, request) {
  const index = await loadIndex(env);
  const auth = findAuth(index, bearer(request));
  if (!bearer(request)) return fail(401, "Missing bearer token");
  if (!auth) return fail(401, "Invalid token");
  if (auth.type !== "private") return fail(403, "Scope restricted for Public tokens");
  return json({ status: "success", projects: { [auth.projectId]: auth.project } });
}

async function addToken(env, request, projectId) {
  const index = await loadIndex(env);
  const { error } = authorize(index, request, projectId, "admin");
  if (error) return error;
  let body;
  try {
    body = await request.json();
  } catch {
    return fail(400, "Invalid JSON body");
  }
  const type = (body && body.type) || "public";
  if (type !== "private" && type !== "public") {
    return fail(400, "type must be 'private' or 'public'");
  }
  const project = index.projects[projectId];
  if (!project) return fail(404, "Project not found");
  const token = newToken(type);
  project.tokens = project.tokens || [];
  project.tokens.push({ token, type });
  await saveIndex(env, index);
  return json({ status: "success", type, token });
}

async function revokeToken(env, request, projectId) {
  const index = await loadIndex(env);
  const { error } = authorize(index, request, projectId, "admin");
  if (error) return error;
  let body;
  try {
    body = await request.json();
  } catch {
    return fail(400, "Invalid JSON body");
  }
  const token = body && body.token;
  if (!token) return fail(400, "Token to revoke required");
  const project = index.projects[projectId];
  if (!project) return fail(404, "Project not found");
  const before = (project.tokens || []).length;
  project.tokens = (project.tokens || []).filter((entry) => entry.token !== token);
  if (project.tokens.length === before) return json({ status: "success", revoked: false });
  if (project.tokens.length === 0) return fail(400, "Cannot revoke the last token");
  await saveIndex(env, index);
  return json({ status: "success", revoked: true });
}

async function listFiles(env, request, projectId) {
  const index = await loadIndex(env);
  const { error } = authorize(index, request, projectId, "download");
  if (error) return error;
  const project = index.projects[projectId];
  if (!project) return fail(404, "Project not found");
  const files = {};
  for (const [alias, record] of Object.entries(project.files || {})) {
    files[alias] = fileView(request, projectId, alias, record);
  }
  return json({ status: "success", files });
}

async function uploadFile(env, request, projectId) {
  const index = await loadIndex(env);
  const { error } = authorize(index, request, projectId, "upload");
  if (error) return error;
  let form;
  try {
    form = await request.formData();
  } catch {
    return fail(400, "Expected multipart/form-data with 'file' and 'alias'");
  }
  const file = form.get("file");
  let alias;
  try {
    alias = validateAlias(form.get("alias"));
  } catch (e) {
    return fail(400, e.message);
  }
  if (!file || typeof file.arrayBuffer !== "function") return fail(400, "File is required");
  if (file.size > MAX_FILE_BYTES) {
    return fail(413, `File exceeds the ${Math.floor(MAX_FILE_BYTES / 1024 / 1024)} MiB Bot API limit`);
  }
  const bytes = await file.arrayBuffer();
  const name = safeFilename(file.name || alias);
  const project = index.projects[projectId];
  if (!project) return fail(404, "Project not found");

  // A replaced file's old message is deleted *after* the new one exists, so a
  // failed upload can never destroy the previous version.
  const previous = (project.files || {})[alias];
  const message = await tgForm(
    env,
    "sendDocument",
    documentForm(env, bytes, name, file.type || contentType(name), `S1024-FILE[${alias}]`),
  );
  const fileId = message && message.document && message.document.file_id;
  if (!fileId) throw new Error("sendDocument returned no file_id");
  if (previous && previous.mid) {
    await tg(env, "deleteMessage", {
      chat_id: env.CHANNEL_ID,
      message_id: previous.mid,
    }).catch(() => {});
  }
  const record = {
    id: fileId,
    mid: message.message_id,
    name,
    size: bytes.byteLength,
    type: file.type || contentType(name),
    key: newSecret(),
  };
  project.files = project.files || {};
  project.files[alias] = record;
  await saveIndex(env, index);
  return json({ status: "success", alias, url: shareUrl(request, projectId, alias, record.key), file: fileView(request, projectId, alias, record) });
}

async function streamFile(env, projectId, alias, index) {
  const state = index || (await loadIndex(env));
  const project = state.projects[projectId];
  const record = project && (project.files || {})[alias];
  if (!record) return fail(404, "File not found");
  const upstream = await downloadTelegramFile(env, record.id);
  const filename = safeFilename(record.name || alias);
  const headers = {
    "content-type": record.type || contentType(filename),
    "content-disposition": `attachment; filename="${filename.replace(/"/g, "")}"`,
    "cache-control": "private, max-age=300",
  };
  if (record.size != null) headers["content-length"] = String(record.size);
  return new Response(upstream.body, { status: 200, headers });
}

async function downloadFile(env, request, projectId, alias) {
  const index = await loadIndex(env);
  const { error } = authorize(index, request, projectId, "download");
  if (error) return error;
  return streamFile(env, projectId, alias, index);
}

async function deleteFile(env, request, projectId, alias) {
  const index = await loadIndex(env);
  const { error } = authorize(index, request, projectId, "admin");
  if (error) return error;
  const project = index.projects[projectId];
  if (!project || !(project.files || {})[alias]) return fail(404, "File not found");
  const record = project.files[alias];
  if (record.mid) {
    await tg(env, "deleteMessage", { chat_id: env.CHANNEL_ID, message_id: record.mid }).catch(() => {});
  }
  delete project.files[alias];
  await saveIndex(env, index);
  return json({ status: "success" });
}

async function listGvs(env, request, projectId) {
  const index = await loadIndex(env);
  const { error } = authorize(index, request, projectId, "get_gv");
  if (error) return error;
  const project = index.projects[projectId];
  if (!project) return fail(404, "Project not found");
  const values = {};
  for (const [alias, entry] of Object.entries(project.global_vars || {})) {
    values[alias] = typeof entry === "object" && entry !== null ? entry.v : entry;
  }
  return json(values);
}

async function getGv(env, request, projectId, alias) {
  const index = await loadIndex(env);
  const { error } = authorize(index, request, projectId, "get_gv");
  if (error) return error;
  const project = index.projects[projectId];
  const entry = project && (project.global_vars || {})[alias];
  if (entry === undefined || entry === null) return fail(404, "Variable not found");
  return json({ alias, value: typeof entry === "object" ? entry.v : entry });
}

async function setGv(env, request, projectId) {
  const index = await loadIndex(env);
  const { error } = authorize(index, request, projectId, "upload");
  if (error) return error;
  let body;
  try {
    body = await request.json();
  } catch {
    return fail(400, "Invalid JSON body");
  }
  let alias;
  try {
    alias = validateAlias(body && body.alias);
  } catch (e) {
    return fail(400, e.message);
  }
  const value = String((body && body.value) ?? "");
  if (value.length > MAX_GV_LENGTH) return fail(400, `Value must be at most ${MAX_GV_LENGTH} characters`);
  const project = index.projects[projectId];
  if (!project) return fail(404, "Project not found");
  project.global_vars = project.global_vars || {};
  const previous = project.global_vars[alias];
  const text = `${GV_PREFIX}[${alias}] ${value}`;
  let messageId;
  if (previous && typeof previous === "object" && previous.mid) {
    await tg(env, "editMessageText", {
      chat_id: env.CHANNEL_ID,
      message_id: previous.mid,
      text,
    });
    messageId = previous.mid;
  } else {
    const message = await tg(env, "sendMessage", {
      chat_id: env.CHANNEL_ID,
      text,
      disable_notification: true,
    });
    messageId = message.message_id;
  }
  project.global_vars[alias] = { v: value, mid: messageId };
  await saveIndex(env, index);
  return json({ status: "success", alias, id: messageId });
}

async function deleteGv(env, request, projectId, alias) {
  const index = await loadIndex(env);
  const { error } = authorize(index, request, projectId, "admin");
  if (error) return error;
  const project = index.projects[projectId];
  const entry = project && (project.global_vars || {})[alias];
  if (!entry) return fail(404, "Variable not found");
  if (typeof entry === "object" && entry.mid) {
    await tg(env, "deleteMessage", { chat_id: env.CHANNEL_ID, message_id: entry.mid }).catch(() => {});
  }
  delete project.global_vars[alias];
  await saveIndex(env, index);
  return json({ status: "success" });
}

async function shareDownload(env, request, projectId, alias) {
  const url = new URL(request.url);
  const key = url.searchParams.get("key") || "";
  const index = await loadIndex(env);
  const project = index.projects[projectId];
  const record = project && (project.files || {})[alias];
  if (!record || !record.key || record.key !== key) return fail(403, "Invalid share key");
  return streamFile(env, projectId, alias, index);
}

/* -------------------------------------------------------------------------- */
/* static assets (dashboard + docs are served by Cloudflare for free)         */
/* -------------------------------------------------------------------------- */

async function serveAsset(env, request) {
  const url = new URL(request.url);
  let path = url.pathname;
  if (path.startsWith("/docs/static/") || path.startsWith("/docs/assets/")) {
    path = `/docs/${path.split("/").slice(3).join("/")}`;
  }
  if (path === "/" || path === "/files" || path === "/index.html") path = "/index.html";
  if (path === "/s1024.js") path = "/libraries/cdn.js";
  if (path === "/docs" || path === "/docs/") path = "/docs/index.html";
  if (path.startsWith("/docs/") && !path.split("/").pop().includes(".")) path = "/docs/index.html";
  const target = new URL(path, url.origin);
  const init = { method: request.method, headers: request.headers };
  const response = await env.ASSETS.fetch(new Request(target, init));
  if (response.status === 404 && path.startsWith("/docs/")) {
    return env.ASSETS.fetch(new Request(new URL("/docs/index.html", url.origin), init));
  }
  return response;
}

/* -------------------------------------------------------------------------- */
/* router                                                                     */
/* -------------------------------------------------------------------------- */

function decode(value) {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

async function routeApi(env, request, url) {
  const path = url.pathname;
  const parts = path.split("/").filter(Boolean); // ["api", ...]

  if (path === "/api/health" && request.method === "GET") return handleHealth(env, url);
  if (path === "/api/projects/create" && request.method === "POST") return createProject(env, request);
  if (path === "/api/index" && request.method === "GET") return getIndex(env, request);

  if (parts[1] === "projects" && parts[2]) {
    const projectId = decode(parts[2]);
    const tail = parts.slice(3);
    if (tail.length === 1 && tail[0] === "tokens" && request.method === "POST") {
      return addToken(env, request, projectId);
    }
    if (tail.length === 2 && tail[0] === "tokens" && tail[1] === "revoke" && request.method === "POST") {
      return revokeToken(env, request, projectId);
    }
    if (tail.length === 1 && tail[0] === "files" && request.method === "GET") {
      return listFiles(env, request, projectId);
    }
    if (tail.length === 1 && tail[0] === "upload" && request.method === "POST") {
      return uploadFile(env, request, projectId);
    }
    if (tail.length === 2 && tail[0] === "files" && request.method === "GET") {
      return downloadFile(env, request, projectId, decode(tail[1]));
    }
    if (tail.length === 2 && tail[0] === "files" && request.method === "DELETE") {
      return deleteFile(env, request, projectId, decode(tail[1]));
    }
    if (tail.length === 1 && tail[0] === "gv" && request.method === "GET") {
      return listGvs(env, request, projectId);
    }
    if (tail.length === 1 && tail[0] === "gv" && request.method === "POST") {
      return setGv(env, request, projectId);
    }
    if (tail.length === 2 && tail[0] === "gv" && request.method === "GET") {
      return getGv(env, request, projectId, decode(tail[1]));
    }
    if (tail.length === 2 && tail[0] === "gv" && request.method === "DELETE") {
      return deleteGv(env, request, projectId, decode(tail[1]));
    }
  }
  return fail(404, "Not found");
}

export default {
  async fetch(request, env, ctx) {
    if (request.method === "OPTIONS") {
      return cors(new Response(null, { status: 204 }));
    }
    const url = new URL(request.url);
    try {
      if (url.pathname.startsWith("/api/")) return cors(await routeApi(env, request, url));
      if (url.pathname.startsWith("/f/")) {
        const parts = url.pathname.split("/").filter(Boolean);
        if (parts.length !== 3) return cors(fail(404, "Not found"));
        return cors(await shareDownload(env, request, decode(parts[1]), decode(parts[2])));
      }
      return serveAsset(env, request);
    } catch (error) {
      console.error("Storage1024 worker error:", error);
      return cors(json(
        { detail: `Storage error: ${String(error.message || error)}` },
        503,
      ));
    }
  },
};
