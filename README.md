# Storage1024

Files + global variables behind one tiny REST API, with client libraries for
16 languages. The dashboard, docs and SDKs are all served by one FastAPI app.

> **Why the site stopped working:** `https://storage1024.onrender.com/` now
> returns a plain `Not Found` from **Render's proxy** — that is not an app
> 404, it means the web service behind that URL no longer exists (deleted,
> suspended, or its free-tier plan expired). On top of that, the code could
> not be redeployed as-is: importing `bridge.py` crashed immediately when
> `TELEGRAM_SESSION` / `CHANNEL_ID` were absent, and the repo had no
> `render.yaml`, `.env.example`, or setup instructions. Both problems are
> fixed below; the last step (creating a new Render service and pasting your
> Telegram secrets) needs your account.

---

## Quick start (works with zero configuration)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
python3 bridge.py                 # or: uvicorn bridge:app --host 0.0.0.0 --port 8000
```

Open <http://localhost:8000>. With no Telegram credentials the server uses a
**local filesystem backend** (`./data/`) and everything works: sign up, get a
token, upload files, set variables, generate tokens. `/api/health` tells you
which backend is live.

```bash
curl http://localhost:8000/api/health
# {"status":"ok","configured_mode":"auto","telegram_configured":false,
#  "backend":"local","projects":0,"data_dir":"..."}
```

### Tests

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

31 tests cover the API, both storage backends (Telegram is exercised with a
fake Telethon client), static docs, SDK syntax and the import-without-secrets
boot path.

---

## Deploying to Render again

1. Copy `.env.example` to `.env` locally to see every option.
2. In Render: **New → Blueprint**, pick this repo, and use the included
   [`render.yaml`](render.yaml). Blueprints deploy a branch of your choice —
   select the branch that contains these changes (merge to `main` first, or
   pick the working branch when creating the service). It sets `PYTHON_VERSION`, the start command,
   `/api/health` as the health check, and prompts for the secret env vars.
   Alternatively create a **Web Service** manually with:
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn bridge:app --host 0.0.0.0 --port $PORT`
   - Health check path: `/api/health`
3. Set `API_ID`, `API_HASH`, `TELEGRAM_SESSION`, `CHANNEL_ID` for durable
   storage (see below). If you leave them empty, the service boots in local
   mode — fine for a demo, but **Render's free-tier disk is ephemeral**, so
   data disappears on restart/sleep. Attach a persistent disk if you want
   local mode to survive.
4. The URL will be whatever Render assigns (e.g. `storage1024-xxxx.onrender.com`).
   The frontend, CDN SDK and docs now use relative URLs, so no code changes
   are needed for a new hostname. Update the examples in `docs/` if you want
   them to show your new URL, then set the GitHub repo homepage to it.

> Free-tier Render services also spin down after inactivity; the first request
> after a spin-down can take ~30s. A paid plan or an external uptime ping
> avoids that.

### Telegram backend setup

1. Get `API_ID` / `API_HASH` from <https://my.telegram.org>.
2. Create a private channel and add the account as admin (post / edit / pin
   messages). `CHANNEL_ID` is the numeric id, usually `-100...`.
3. Run `PHONE_NUMBER=+91... python generate_session.py` locally, then set
   `TELEGRAM_SESSION` to the printed string (or keep the generated
   `storage.session_string` file — it is gitignored).
4. The index is stored as a **pinned JSON document** in that channel. If
   pinning is not permitted, the server writes a small searchable locator
   message instead. The old fixed message id 4 plain-text index is still
   readable, so existing data migrates on first read.

---

## Environment variables

| Variable | Default | Meaning |
| --- | --- | --- |
| `STORAGE_BACKEND` | `auto` | `auto`, `telegram`, or `local` |
| `DATA_DIR` | `./data` | Local backend storage directory |
| `API_ID` / `API_HASH` | – | Telegram app credentials |
| `TELEGRAM_SESSION` | – | Telethon StringSession (or `storage.session_string` file) |
| `CHANNEL_ID` | – | Numeric Telegram channel id |
| `INDEX_MESSAGE_ID` | `4` | Legacy index message id (migration only) |
| `MAX_UPLOAD_MB` | `1800` | Upload limit (`413` above it) |
| `THROTTLE_ENABLED` | `true` | Space out Telegram writes to avoid FloodWait |
| `CREATE_PROJECT_KEY` | – | If set, `POST /api/projects/create` needs header `X-Create-Key` |
| `PORT` | `8000` | Server port |

Config is read from real environment variables first, then
`~/.storage1024/config.env`, then `./.env`.

`.python-version` pins Python 3.11 and `render.yaml` sets `PYTHON_VERSION` to
`3.11.9`; Render's current default (3.14) is newer than some of these
dependencies are tested against, so keep one of these pins. `runtime.txt` is
**not** read by Render. [Render's Python version docs](https://render.com/docs/python-version)

---

## API

Full reference: [`docs/langs/api.md`](docs/langs/api.md) (also served at
`/docs#api`).

| Method | Path | Notes |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness; `?strict=true` returns 503 if storage is down |
| `POST` | `/api/projects/create` | Returns private + public tokens |
| `GET` | `/api/index` | Private token only |
| `POST` | `/api/projects/{id}/gv` | `{"alias": ..., "value": ...}` |
| `GET` | `/api/projects/{id}/gv` / `/gv/{alias}` | All variables / one variable |
| `DELETE` | `/api/projects/{id}/gv/{alias}` | Private token |
| `POST` | `/api/projects/{id}/upload` | multipart `file` + `alias` |
| `GET` | `/api/projects/{id}/files` / `/files/{alias}` | List / download (bearer) |
| `GET` | `/f/{id}/{alias}?key=...` | Shareable link returned by upload |
| `POST` | `/api/projects/{id}/tokens` / `tokens/revoke` | Private token |

Private tokens end in `;qi=` (full access); public tokens end in `;gg=`
(read + upload only). Tokens are generated with `secrets`, and a project can
never lose its last private token.

---

## What was broken (and fixed)

**Deployment / startup**
- `manager = ProjectManager()` ran at import time and `TelegramStorage.__init__`
  raised `ValueError` without `TELEGRAM_SESSION` / `CHANNEL_ID`. A redeploy
  without perfectly-set env vars died before binding a port. Now nothing
  touches the network at import; missing config selects the local backend and
  `/api/health` reports it.
- No `render.yaml`, `.env.example`, README or pinned requirements. Added.
- Static files were resolved relative to the process CWD; now resolved from
  the repository root.

**Data integrity**
- `get_index()` caught every exception and returned `{"projects": {}}`. A
  transient Telegram error looked like an empty database, and the next
  `create_project` overwrote all projects. Backend failures now raise → HTTP
  503, and corrupt local indexes are rejected too.
- The index was `edit_message(id=4, json.dumps(indent=2))`, but Telegram caps
  text at 4096 characters — writes failed as soon as the index grew. It is now
  a pinned JSON document (or a locator + document fallback), with legacy
  message-id-4 reads for migration.
- Every operation connected/disconnected Telethon independently and mutated a
  shared `manager.index`; concurrent uploads could lose data. All mutations
  are now locked read-modify-write transactions and share one request-level
  connection.
- Uploads wrote `temp_<raw filename>` in the CWD (path traversal) and held a
  global lock during a 1–35s sleep. Uploads now go to a sanitized temp dir,
  and throttling only spaces out the actual writes.
- Tokens used `random.choices` / a truncated UUID. Now `secrets.token_urlsafe`.

**API / SDK contract**
- `GET /api/projects/{id}/gv/{alias}` did not exist, yet every SDK called it
  (dashboard Edit GV, Python, JS, Go, Rust, C#, Java, Kotlin, PHP, Ruby,
  Bash, PowerShell). Added — returns `{"alias", "value"}`.
- There was no way to download a file even though the docs promised a stable
  URL. Added authenticated download, a files listing, and a shareable URL with
  a random per-file capability key (no token leaked into the link).
- `add_gv` rejected `""` and `0` because of `if not value`. Fixed.
- `HTTPBearer` returned 403 for a missing token; now 401 with
  `WWW-Authenticate`.
- Go SDK sent `multipart.Writer.FormDataHeader()` as the request
  `Content-Type` (a *part* header) — uploads could never parse. Fixed to
  `FormDataContentType()`, with status checks and streaming.
- Node SDK used global `fetch` with no fallback and declared an unused ESM
  `node-fetch`; browser client defaulted to `http://127.0.0.1:8000`. Fixed.
- C#, Java, Kotlin, C++, PHP, Ruby and Bash clients interpolated values into
  JSON by hand (broke on quotes/newlines), ignored HTTP errors, or forced TLS
  on localhost. Rewritten with proper encoding and error handling. The C++
  header leaked its `curl_slist` on every call.

**Dashboard / docs**
- `app.js` defined `fetchAccountData()` twice (the second, broken copy won)
  and hardcoded the dead Render URL. Now one implementation uses `/api`
  relative URLs, so it works on any host.
- Empty button labels, no `.dashboard-grid` / `.modal-content` styles, an
  undefined `--text-muted` CSS variable, and unescaped server data in
  `innerHTML` (XSS). Fixed with labels, CSS, escaping and event delegation.
- Docs loaded `style.css` / `story.md` relative to `/docs` (resolved to the
  wrong paths) and hard-failed without the `marked` CDN. Fixed with absolute
  paths and a built-in fallback renderer.

---

## Security notes

- Never commit `.env`, `*.session*` or the `data/` directory — all are
  gitignored. Private tokens are the only admin credential; share only public
  tokens (`;gg=`), and revoke them when leaked.
- Set `CREATE_PROJECT_KEY` on a public deployment to stop anonymous project
  creation (then pass `X-Create-Key` from the dashboard/trusted clients), and
  keep the built-in 10-projects/minute/IP rate limit.
- File share URLs are capabilities: anyone holding one can read that file.
  Deleting the file invalidates the link.
- Run one worker (the default in `render.yaml`): the local backend and the
  in-memory rate limiter are per-process.

## Layout

```
bridge.py            FastAPI app, REST API, static site
client.py            Telegram + local storage backends
manager.py           projects, tokens, files, GVs (locked transactions)
config.py            env/.env loading shared by every entry point
main.py              CLI: upload/list/download
generate_session.py  one-time Telethon login helper
index.html/app.js/style.css   dashboard
docs/                developer docs (markdown + viewer)
libraries/           SDKs (16 languages) + python wheel/sdist
web/                 alternative browser clients
tests/               pytest suite
render.yaml          Render Blueprint
```
