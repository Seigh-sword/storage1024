# Storage1024 on Cloudflare Workers — free, no card, always on, CADB

> **Status: built and tested.** The Worker lives in [`workers/`](../workers/) and
> implements the same API as the Python bridge. 15 offline tests pass and
> `wrangler deploy --dry-run` bundles cleanly. You still have to run the deploy
> commands below — only you can create the Cloudflare/Telegram accounts.
>
> **No PR, no merge, no `main`.** Everything here deploys from this working
> branch. Cloudflare reads your local files, not a GitHub branch.

---

## 1. Is it really free? What you get and what you don't

| | Workers Free plan |
|---|---|
| Credit card | **Not required** on the Free plan (Cloudflare says "Start building for free — no credit card required") |
| URL | permanent `https://<name>.<subdomain>.workers.dev`, **always on, never sleeps** |
| Requests | 100,000 Worker invocations/day (API calls only — static files are served separately and are free/unlimited) |
| CPU | 10 ms CPU time per invocation (network waiting is not CPU time) |
| Memory | 128 MB per invocation |
| Subrequests | 50 per invocation (this app uses 2–6) |
| KV | 1 GB storage, 100,000 reads/day, 1,000 writes/day, 25 MiB max value |
| Paid plan | $5/month — you do **not** need it for a personal Storage1024 |

Sources: [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/),
[Workers limits](https://developers.cloudflare.com/workers/platform/limits/),
[KV pricing](https://developers.cloudflare.com/kv/platform/pricing/),
[static assets routing](https://developers.cloudflare.com/workers/static-assets/routing/worker-script/).

**Honest caveats**

- "No card" is Cloudflare's official position for Workers Free, but like every
  host it can trigger an anti-abuse verification step for some accounts. If that
  happens to you, do not fight it — use [Route 2 in `no-card.md`](no-card.md)
  (your own device + a free tunnel), which needs no signup at all.
- A Worker is **JavaScript**, not Python. Telethon / MTProto cannot run there.
  This version uses the **Telegram Bot API** instead. Consequence: the Bot API
  only lets you download files up to ~20 MB, so this build caps uploads at
  **19 MiB per file**. The Python/Telethon version supports up to 1800 MB per
  file. Supporting big files here would need chunking into ≤19 MiB parts and
  reassembly — that is a possible follow-up, not something this build does.
- KV's 1,000 writes/day is the real ceiling. Every mutation (create project,
  upload, set GV, …) uses **2 KV writes**, so ~500 mutations/day. Fine for one
  person or a small project; not fine for a busy public service.
- No Durable Objects on the free plan, so two writes at the exact same instant
  can race. Single-user usage is fine. Keep the index small (a few thousand
  files) so JSON parsing stays well under the 10 ms CPU budget.

---

## 2. What is actually stored where (CADB preserved)

The **Telegram channel is still the database**:

- each uploaded file → a document message in the channel,
- each global variable → a text message in the channel (`S1024-GV[alias] …`),
- the project index → a JSON document **pinned** in the channel (`S1024-INDEX-V2`).

Workers KV only caches the *pointer* (`file_id` + `message_id`) to that pinned
index document. If the KV namespace is wiped, the Worker calls `getChat`, reads
`pinned_message`, downloads the index document and rebuilds itself — there is a
test for exactly that. Cloudflare is compute, not the database.

---

## 3. What you need before starting

1. A **Cloudflare account** — sign up at <https://dash.cloudflare.com/sign-up/workers>
   with an email. Do not add a card, do not start a trial.
2. **Node.js 20+** and npm on your machine (`node -v`).
3. A **Telegram bot token** — 2 minutes, no phone verification beyond the
   Telegram account you already have:
   - open Telegram → search `@BotFather` → send `/newbot`
   - pick a name and a username (must end in `bot`)
   - copy the token that looks like `123456789:AAH…`
4. A **Telegram channel** — any channel you own, private or public.
   - Add your bot as an **admin** with **Post messages**, **Edit messages of
     others** / **Delete messages of others**, and **Pin messages**.
   - Get the chat id by posting a test message (this also proves the bot works):

     ```bash
     curl -s "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage" \
       -d "chat_id=@your_channel_username" \
       -d "text=Storage1024 channel test" | python3 -m json.tool
     ```

     Look for `result.chat.id`, e.g. `-1001234567890`. You can use either that
     numeric id or `@your_channel_username` as `CHANNEL_ID`.

> **You do NOT need `API_ID`, `API_HASH`, `TELEGRAM_SESSION`, or
> `generate_session.py` for this route.** The Worker only needs a bot token and
> a channel id.

---

## 4. Deploy (copy-paste, ~5 minutes)

All commands run from the repo root on this branch.

```bash
git checkout arena/1bde6926-storage1024
git pull origin arena/1bde6926-storage1024

cd workers
npm install
npx wrangler login                      # opens your browser, no card
npx wrangler kv namespace create INDEX
```

The last command prints something like:

```
{ "title": "storage1024-INDEX", "id": "a1b2c3d4e5f67890abcdef1234567890ab" }
```

Paste that `id` into `workers/wrangler.toml`, replacing
`REPLACE_WITH_YOUR_KV_NAMESPACE_ID`:

```toml
[[kv_namespaces]]
binding = "INDEX"
id = "a1b2c3d4e5f67890abcdef1234567890ab"
```

Then set the secrets (each command prompts you to paste the value, so the
secret never lands in the repo):

```bash
npx wrangler secret put BOT_TOKEN           # 123456789:AAH…
npx wrangler secret put CHANNEL_ID          # -1001234567890 or @your_channel
npx wrangler secret put CREATE_PROJECT_KEY  # any long random string, e.g. openssl rand -hex 20
```

`CREATE_PROJECT_KEY` is optional but strongly recommended: the dashboard is
public, and without it anyone can create projects in your channel. When set,
project creation requires an `X-Create-Key` header (see §6).

Now deploy:

```bash
npm run deploy
```

Wrangler prints your URL, e.g.
`https://storage1024.<your-subdomain>.workers.dev`. Verify:

```bash
curl https://storage1024.<your-subdomain>.workers.dev/api/health
# {"status":"ok","backend":"telegram-bot-api","mode":"cloudflare-worker","bot":"…","projects":0}
```

If you see `"status":"degraded"`, the error string tells you what is wrong
(usually a bad `CHANNEL_ID` or a bot that is not a channel admin).

Open the root URL in a browser — the dashboard and all `/docs` pages are served
by Cloudflare's free static asset hosting.

**Before deploying again**, check your work locally:

```bash
cd workers
npm test                 # 15 offline tests, no account needed
npm run dry-run          # validates wrangler.toml + bundles the Worker
npm run dev              # http://127.0.0.1:8787 (needs .dev.vars, see below)
```

For local dev, copy `workers/.dev.vars.example` → `workers/.dev.vars` and fill
in the same values. `.dev.vars` is gitignored.

---

## 5. Create your first project

```bash
curl -X POST https://storage1024.<your-subdomain>.workers.dev/api/projects/create \
  -H "Content-Type: application/json" \
  -H "X-Create-Key: <your CREATE_PROJECT_KEY>" \
  -d '{"name":"My Project"}'
```

Save the returned `project_id` and `tokens.private`. Paste the private token
into the dashboard, or use it directly:

```bash
TOKEN='s1024-…;qi='
BASE='https://storage1024.<your-subdomain>.workers.dev'

# upload a file (the bytes go into the Telegram channel)
curl -X POST "$BASE/api/projects/1234/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "alias=notes" -F "file=@./notes.txt"

# list files / download
curl -H "Authorization: Bearer $TOKEN" "$BASE/api/projects/1234/files"
curl -H "Authorization: Bearer $TOKEN" "$BASE/api/projects/1234/files/notes" -o notes.txt

# global variables
curl -X POST "$BASE/api/projects/1234/gv" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"alias":"greeting","value":"hello CADB"}'
curl -H "Authorization: Bearer $TOKEN" "$BASE/api/projects/1234/gv/greeting"
```

The Python, JS and other SDKs in `libraries/` work unchanged — just point them
at the new `BASE` URL.

---

## 6. API compatibility

The Worker implements the same routes as `bridge.py`:

| Method | Path | Scope |
|---|---|---|
| GET | `/api/health`, `/api/health?strict=true` | public |
| POST | `/api/projects/create` | `X-Create-Key` if set |
| GET | `/api/index` | private |
| POST | `/api/projects/{id}/tokens` | private |
| POST | `/api/projects/{id}/tokens/revoke` | private |
| GET | `/api/projects/{id}/files` | public |
| POST | `/api/projects/{id}/upload` | public |
| GET | `/api/projects/{id}/files/{alias}` | public |
| DELETE | `/api/projects/{id}/files/{alias}` | private |
| GET | `/api/projects/{id}/gv` | public |
| GET | `/api/projects/{id}/gv/{alias}` | public |
| POST | `/api/projects/{id}/gv` | public |
| DELETE | `/api/projects/{id}/gv/{alias}` | private |
| GET | `/f/{id}/{alias}?key=…` | capability URL, no token |
| GET | `/`, `/app.js`, `/style.css`, `/s1024.js`, `/docs/**`, `/assets/**` | static |

Private tokens end in `;qi=`; public tokens end in `;gg=` and may only upload,
download and read GVs. Share URLs carry an unguessable `key` instead of the
token. CORS is open on `/api` and `/f`.

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `degraded: "BOT_TOKEN and CHANNEL_ID secrets are required"` | run `npx wrangler secret put …` again, then `npx wrangler deploy` |
| `Telegram sendDocument: Bad Request: chat not found` | wrong `CHANNEL_ID`, or the bot is not a channel admin yet |
| `Telegram pinChatMessage: not enough rights` | grant **Pin messages**. The app still works via the KV pointer, but cold-start recovery degrades |
| `Telegram getChat` finds no pinned index | open the channel and pin the `S1024-INDEX-V2` document manually once, then redeploy |
| `Index document is malformed` / 503 on every write | the pinned index is not a Storage1024 v2 document. Pin the newest `S1024-INDEX-V2` document. The Worker refuses to overwrite an unreadable index (deliberate — this is the bug that used to wipe projects) |
| `429 Too Many Requests` | the Worker retries Telegram 429s automatically, but Telegram's per-channel limit is real — space out bulk uploads |
| `File exceeds the 19 MiB Bot API limit` | expected. Use the Python/Telethon deployment for big files, or ask for chunking support |
| `/docs` redirects to `/docs/` | normal (Cloudflare's automatic trailing slash) |
| KV `1000 writes/day` exhausted | free limit reached; wait for the UTC day to roll over or move to the Python route |

---

## 8. If this route is blocked

1. [Route 2 — own device + free tunnel](no-card.md) (`deploy/quick-tunnel.sh`):
   zero signup, zero card, full Python/Telethon, 1800 MB files. Needs a machine
   that stays on.
2. [Route 3 — Serv00 free shell](no-card.md): full Python, no card, but manual
   approval and a 90-day login rule.
3. [Route 1 — Render free + UptimeRobot](no-card.md): no code change, but the
   service depends on a 5-minute ping to stay awake.
