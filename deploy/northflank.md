# Deploy Storage1024 on Northflank (free, 24/7, CADB)

> ⚠️ **No card available?** Northflank's official pricing says "No card
> needed", but some regions are asked for a card *verification hold* at
> signup. If that happens to you, stop and use
> **[`alwaysdata.md`](alwaysdata.md)** — that path needs no card at all.

**Northflank's free Sandbox** runs the container 24/7 with no sleep timer,
while **Telegram is the database** — the whole point of Storage1024 (chat app
as DB). Files and the project index live in your Telegram channel, so
Northflank's ephemeral disk does not matter.

Official references: [pricing (Sandbox: "No card needed", "Always on, no
sleeping")](https://northflank.com/pricing), [build & deploy your
code](https://northflank.com/docs/v1/application/getting-started/build-and-deploy-your-code),
[inject secrets](https://northflank.com/docs/v1/application/secure/inject-secrets),
[health checks](https://northflank.com/docs/v1/application/observe/configure-health-checks).

---

## 0. Before you start — get the four Telegram secrets

Storage1024 uses **your own Telegram account** (via a Telethon StringSession)
to read/write a private channel. No bot token is needed.

1. **API_ID / API_HASH** — log in at <https://my.telegram.org> → *API
   development tools* → create an app. Copy the two values.
2. **Create a private Telegram channel** (e.g. `s1024-data`). Add the account
   you'll use as an **admin** with rights to post, edit and pin messages.
3. **Generate the session string locally** (needs a real terminal so you can
   type the login code — never run this on the server):

   ```bash
   cd storage1024
   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   cp .env.example .env
   # fill API_ID, API_HASH and PHONE_NUMBER=+91... in .env
   .venv/bin/python generate_session.py
   ```

   It prints the `TELEGRAM_SESSION` string **and a list of your channels with
   their numeric ids**. Copy both. `CHANNEL_ID` looks like `-1001234567890`.
   (It also saves the string to the gitignored `storage.session_string`.)

> Never commit `.env`, the session string, or paste them into a public repo.
> Anyone with the session string controls that Telegram account.

4. **Optional but strongly recommended:** generate a random
   `CREATE_PROJECT_KEY` (`openssl rand -hex 24`). Once set, only callers with
   the `X-Create-Key` header can create projects — otherwise anyone who finds
   your URL can.

---

## 1. Get the repo onto a branch Northflank can build

The fixes are on `arena/1bde6926-storage1024`. Either merge that branch into
`main`, or simply choose that branch in the Northflank service form. Make sure
the branch contains the root `Dockerfile`.

---

## 2. Create the Northflank account + connect GitHub

1. Sign up at <https://app.northflank.com/signup> and choose the free
   **Sandbox** plan. The pricing page says no card is needed; if your region
   triggers a card *verification* hold, it is not a charge.
2. Connect your GitHub account when prompted and grant access to the
   `storage1024` repository.

---

## 3. Create a combined service

In the dashboard: **Create new → Service → Combined** (a combined service
builds from Git and deploys in one resource; the free Sandbox allows 2
services).

| Field | Value |
| --- | --- |
| Name | `storage1024` |
| Repository | `Seigh-sword/storage1024` |
| Branch | `main` (or `arena/1bde6926-storage1024`) |
| Build options | **Dockerfile** — path `/Dockerfile`, build context `/` |
| Resources | `nf-compute-50` (0.5 vCPU / 1 GB) or the smallest plan offered — comfortably inside the Sandbox's $20/month resource allowance |
| Instances | **1** (one worker: the rate limiter is per-process) |

Under **Networking → Add port**:

| Field | Value |
| --- | --- |
| Port | `8000` |
| Protocol | `HTTP` |
| Accessibility | **Public** |
| Name | `http` |

Northflank auto-detects `EXPOSE 8000` from the Dockerfile and issues a free
Let's Encrypt certificate, giving you a public `https://…code.run` URL.

Under **Advanced → Health checks** (optional but useful):

| Field | Value |
| --- | --- |
| Protocol | `HTTP` |
| Path | `/api/health?strict=true` |
| Port | `8000` |
| Initial delay | `15s` |
| Period | `60s` |

`?strict=true` returns 503 if Telegram is unreachable, so a broken session or
channel shows up as an unhealthy deployment instead of silent data loss.

---

## 4. Add the environment variables

In the service form (or afterwards under **Configure → Environment**), switch
the editor to **ENV format** and paste the contents of
[`northflank.env.example`](northflank.env.example), replacing every
placeholder. Northflank encrypts these as runtime variables; you can also put
them in a **secret group** so they can be reused by another service.

Minimum required set:

```env
STORAGE_BACKEND=telegram
API_ID=12345678
API_HASH=0123456789abcdef0123456789abcdef
TELEGRAM_SESSION=1BVts...
CHANNEL_ID=-1001234567890
CREATE_PROJECT_KEY=<random hex>
PORT=8000
MAX_UPLOAD_MB=1800
THROTTLE_ENABLED=true
```

Notes:

- `STORAGE_BACKEND=telegram` (not `auto`) makes a misconfiguration **fail
  loudly** in `/api/health` instead of silently falling back to a disposable
  local disk.
- `DATA_DIR` is irrelevant here — nothing important is written to the
  container's disk. Do **not** attach a paid persistent volume.
- Leave all `GITHUB_*` vars unset. The GitHub backend stays in the code as an
  optional fallback; this deployment does not use it.
- The Dockerfile listens on port 8000 with one uvicorn worker. If Northflank
  ever injects its own `PORT`, set `PORT=8000` explicitly as above so the app
  and the public port agree.

---

## 5. Deploy and verify

Click **Create service**. CI/CD is on by default: every push to the chosen
branch rebuilds and redeploys. There is **no sleep timer**, so no keep-alive
ping is needed.

1. Open the public DNS shown at the top of the service page. You should see
   the dashboard.
2. Check `https://<your-url>/api/health`:

   ```json
   {"status":"ok","configured_mode":"telegram",
    "telegram_configured":true,"github_configured":false,
    "backend":"telegram","projects":0}
   ```

   If it says `"status":"degraded"`, read the `error` field — usually a wrong
   `CHANNEL_ID`, an expired session string, or a channel where the account
   cannot post/pin.
3. Smoke test the full CADB round trip (replace `URL` and `KEY`):

   ```bash
   curl -X POST https://URL/api/projects/create \
     -H "X-Create-Key: KEY" -H 'Content-Type: application/json' \
     -d '{"name":"first"}'
   # -> save the private token that ends in ;qi=
   curl -X POST https://URL/api/projects/ID/gv \
     -H "Authorization: Bearer TOKEN" -H 'Content-Type: application/json' \
     -d '{"alias":"hello","value":"world"}'
   ```

   Look in your Telegram channel: the index is a pinned
   `storage1024-index.json` document and variables are `GV[alias]: value`
   messages. That is your database and your backup.
4. Optional: add a custom domain under **Configure → Networking → Domains**,
   then update the GitHub repo homepage and the examples in `docs/` to the new
   URL. All frontend code uses relative `/api` URLs, so nothing else changes.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Build fails "Dockerfile not found" | Set Dockerfile path to `/Dockerfile` and build context to `/`. |
| Site unreachable / 502 | Port must be `8000`, protocol `HTTP`, accessibility `Public`. `EXPOSE 8000` is in the image. |
| Health `degraded`, `backend: telegram` | Recheck `API_ID`, `API_HASH`, `TELEGRAM_SESSION`, `CHANNEL_ID`. Regenerate the session if you logged out that account elsewhere. |
| `503` on project/GV endpoints | Telegram cannot be reached from the region, or the channel id is wrong. Check the channel id printed by `generate_session.py`. |
| 403 on `/api/projects/create` | Send `X-Create-Key: <CREATE_PROJECT_KEY>`. |
| 413 on upload | `MAX_UPLOAD_MB` (default 1800); the platform proxy may impose its own body cap — test a large file before relying on it. |
| Data disappeared after redeploy | You are on `local` mode. Set `STORAGE_BACKEND=telegram` and confirm `/api/health` says `backend: telegram`. |
| Build minutes exhausted | Sandbox build resources are limited; avoid unnecessary pushes, keep `.dockerignore` intact. |

---

## What it costs

**₹0/month**, subject to Northflank's Sandbox limits (2 services, 2 jobs,
1 database, up to $20/month of resources, always-on). Free tiers can change —
verify on <https://northflank.com/pricing> before relying on it long term. If
Northflank ever drops the free Sandbox, the same `Dockerfile` + these same env
vars run unchanged on an Oracle Cloud Always Free VM or a home machine; see
[`README.md`](README.md) in this folder.
