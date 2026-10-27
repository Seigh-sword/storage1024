# Deploy Storage1024 on alwaysdata (free for life, 24/7)

> 🛑 **CARD WALL (Oct 2026):** alwaysdata's signup now shows *"To continue
> your registration and to prevent misuse, you must validate a credit or
> debit card"* for some regions/IPs - despite the site advertising
> "Registration without credit card". If you see that, **do not keep trying**;
> go to **[`no-card.md`](no-card.md)** for routes that never ask for a card.
> Everything below still applies if you got in.

This is the **no-credit-card** path. alwaysdata's Free plan is advertised as
"Registration without credit card", "Valid without time limit", 1 GB SSD,
256 MB RAM, ¼ CPU, for personal use [offers](https://www.alwaysdata.com/en/offers/).
Its **User program** site type runs a real long-lived ASGI process (uvicorn),
and its outbound TCP is open — which is exactly what a Telethon / chat-app-as-
database app needs. A public FastAPI + Telethon project is running on this free
plan right now: <https://ramwanstream.alwaysdata.net> — its
[README](https://github.com/ramwanstream/tg-stream) documents the same setup
and the same list of dead no-card alternatives.

Docs: [ASGI / uvicorn on
alwaysdata](https://help.alwaysdata.com/en/docs/web-hosting/languages/python/configuration/),
[User program site
type](https://help.alwaysdata.com/en/docs/web-hosting/sites/http-servers/user-program/),
[SSH](https://help.alwaysdata.com/en/docs/web-hosting/remote-access/ssh/),
[Free plan limits](https://help.alwaysdata.com/en/docs/admin-billing/billing/public-cloud-prices/).

---

## 0. The four Telegram secrets

Same as [`northflank.md` → step 0](northflank.md): get `API_ID` / `API_HASH`
from <https://my.telegram.org>, create a private channel with your account as
admin, then run `generate_session.py` **locally**. It prints
`TELEGRAM_SESSION` and the numeric id of every channel — copy one into
`CHANNEL_ID`. Also make a random `CREATE_PROJECT_KEY`
(`openssl rand -hex 24`).

Never commit these. They are pasted into alwaysdata's site environment, not
into any file in Git.

---

## 1. Sign up (no card)

1. Go to <https://www.alwaysdata.com/en/register/?p=2012> (the **Free** plan).
   Registration needs only an email — no card, no trial expiry.
2. Note your account name; your site will be
   `https://<account>.alwaysdata.net`.
3. In **Remote access → SSH/SFTP**, check the SSH user/password. You can skip
   installing an SSH client entirely: open
   `https://ssh-<account>.alwaysdata.net` in your browser for a web terminal
   (handy behind a college firewall).

> The Free plan is for **personal, non-commercial** use and sites are limited
> to the `alwaysdata.net` address. Free plans have no SLA — fine for a
> personal project, not for a business. Its fine print also says the plan
> "cannot be used to run services"; the **User program** site type is a
> documented alwaysdata feature and is exactly what the live FastAPI +
> Telethon project linked above uses, but if support ever objects, fall back
> to Serv00 or a home device below.

---

## 2. Install the app over SSH

No PR and no merge needed — alwaysdata clones the working branch directly:

```bash
git clone -b arena/1bde6926-storage1024 \
    https://github.com/Seigh-sword/storage1024.git ~/storage1024
cd ~/storage1024
python -V                     # 3.9+ is fine; 3.11 is ideal
python -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

alwaysdata documents that you should invoke `python` (not `python3`) and that
you can pin a version with `PYTHON_VERSION`; if the default is older than 3.9,
set **Environment → Python → 3.11** in the admin panel first, then recreate
the venv.

Check it boots before wiring up the site:

```bash
STORAGE_BACKEND=local PORT=8000 .venv/bin/python bridge.py
# -> Uvicorn running; Ctrl+C afterwards
```

---

## 3. Create the site (User program)

Admin panel → **Web → Sites → Add a site**:

| Field | Value |
| --- | --- |
| Addresses | `<account>.alwaysdata.net` |
| Type | **User program** |
| Command | `/home/<account>/storage1024/.venv/bin/uvicorn bridge:app --host $IP --port $PORT --workers 1` |
| Working directory | `/home/<account>/storage1024` |
| Environment | paste [`alwaysdata.env.example`](alwaysdata.env.example), replacing every placeholder |

`$IP` and `$PORT` are supplied by alwaysdata — the docs specifically require
listening on the given IP (IPv6) and port. Do **not** add `--reload`, and keep
`--workers 1`: the in-memory rate limiter is per-process and the Free plan has
256 MB RAM.

The app needs ~70 MB RSS with FastAPI + Telethon + all routes imported, so
256 MB leaves headroom. Uploads stream to disk in 1 MB chunks rather than being
buffered in RAM, but keep `MAX_UPLOAD_MB` modest (e.g. 200) if you see the
process being killed on large files.

Save the site. alwaysdata starts the process and keeps it running; there is no
sleep timer and **no keep-alive ping required**.

---

## 4. Verify

```bash
curl https://<account>.alwaysdata.net/api/health
```

Expected:

```json
{"status":"ok","configured_mode":"telegram",
 "telegram_configured":true,"github_configured":false,
 "backend":"telegram","projects":0}
```

Then open `https://<account>.alwaysdata.net` — dashboard, docs, `/s1024.js`
and the API all work on any hostname because every URL is relative.

Smoke test CADB:

```bash
curl -X POST https://<account>.alwaysdata.net/api/projects/create \
  -H "X-Create-Key: YOUR_KEY" -H 'Content-Type: application/json' \
  -d '{"name":"first"}'
```

Look at your Telegram channel: the index appears as a pinned
`storage1024-index.json` document. That channel is your database and your
backup — the server's disk holds nothing important.

Finally set the GitHub repo's homepage to the new URL and (optionally) update
the example URLs in `docs/`. The old `storage1024.onrender.com` address is
gone; this is the new permanent one.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Site 502 / connection refused | Command must use `$IP` and `$PORT`, not `0.0.0.0:8000`. Check `~/admin/logs/sites/` for the User program's log. |
| Process dies / 256 MB exceeded | Remove `--reload`, keep 1 worker, lower `MAX_UPLOAD_MB`, avoid importing extra packages. |
| `ImportError` / wrong Python | Recreate the venv after setting Python 3.11 in **Environment → Python**; alwaysdata says use `python`, not `python3`. |
| `/api/health` says `degraded` | Wrong `CHANNEL_ID` / session string, or the account cannot post in the channel. Regenerate with `generate_session.py`. |
| 403 on create | Send `X-Create-Key: <CREATE_PROJECT_KEY>`. |
| Data lost after a restart | You are on `local` mode. Set `STORAGE_BACKEND=telegram` and confirm `/api/health` says `backend: telegram`. |
| Need a custom domain | Not available on the Free plan; you get `<account>.alwaysdata.net`. Upgrade to Plus if you later need your own domain. |

---

## If alwaysdata ever refuses you

- [**Northflank**](northflank.md) — free Sandbox, official pricing says "No
  card needed" and "Always on, no sleeping", but some regions trigger a card
  *verification* hold at signup. Try it first if you want more RAM; if it asks
  for a card, come back here.
- **Serv00** — free, no card, 512 MB RAM / 3 GB disk / SSH / own processes,
  but you must log in via SSH or the panel at least once every 90 days or the
  account is deleted, and it is FreeBSD with no SLA.
- **Old phone / laptop + Tailscale Funnel** — free, no card, stable
  `*.ts.net` HTTPS URL with no domain; needs a device that stays on.
- See [`README.md`](README.md) in this folder for the full comparison.
