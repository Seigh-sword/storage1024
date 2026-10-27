# Zero-Card Hosting

> Both **Northflank** and **alwaysdata** show *"To continue your registration
> and to prevent misuse, you must validate a credit or debit card"* for many
> signups (especially from India), even though their pricing pages say "no
> card needed". That is an anti-abuse verification hold. This page lists the
> routes where no card can ever be asked. Full steps:
> [`deploy/no-card.md`](https://github.com/Seigh-sword/storage1024/blob/main/deploy/no-card.md).

## The four zero-card routes

| Route | Card | Hardware | Approval | Code change |
| --- | --- | --- | --- | --- |
| **1. Render free + 5-min pinger** | No (existing account) | No | No | None |
| **2. Own device + free tunnel** | No | Yes | No | None |
| **3. Serv00 free shell** | No | No | Manual, up to 72 h | None |
| **4. Cloudflare Workers rewrite** | No | No | No | Yes (big) |

There is no longer a free 24/7 **container PaaS** that reliably needs no card.
Every one of them either sleeps, expires, or asks for card verification.

### Route 1 — Render free + UptimeRobot (fastest)

You already had a Render account. Its free plan gives **750 instance-hours per
month**; one service awake 24/7 uses ~720–744 h, so it fits. The 15-minute
spin-down is defeated by a free 5-minute ping.

1. Redeploy the Web Service from this branch (no PR/merge): build
   `pip install -r requirements.txt`, start
   `uvicorn bridge:app --host 0.0.0.0 --port $PORT`, health `/api/health`.
2. Paste the four Telegram secrets (`STORAGE_BACKEND=telegram`, `API_ID`,
   `API_HASH`, `TELEGRAM_SESSION`, `CHANNEL_ID`) plus `CREATE_PROJECT_KEY`.
3. Create a free [UptimeRobot](https://uptimerobot.com/pricing/) HTTP monitor
   on `https://<service>.onrender.com/api/health`, interval **5 minutes**,
   no credit card. Never monitor `/robots.txt` — Render answers that itself
   while asleep, so the check lies.

Caveats: one awake service only (750 h cap), ~5 GB bandwidth/month, and a
possible cold start if the pinger misses. Alternatives: the repo's 5-minute
GitHub Actions workflow (must be on the default branch) or a Cloudflare Worker
cron.

### Route 2 — Own device + free tunnel

```bash
git clone -b arena/1bde6926-storage1024 \
    https://github.com/Seigh-sword/storage1024.git && cd storage1024
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
STORAGE_BACKEND=telegram PORT=8000 .venv/bin/python bridge.py &
./deploy/quick-tunnel.sh 8000     # zero signup, free https URL
```

`cloudflared tunnel --url` needs no account, but the URL changes on restart.
For a stable free URL use `./deploy/tailscale-funnel.sh 8000` (Tailscale
Personal, free forever, no card) or ngrok's free static dev domain. An old
Android phone with Termux works — keep it charging with `termux-wake-lock`.

### Route 3 — Serv00

Free, no card, 3 GB / 512 MB / SSH / own processes / Python 3.11. Registration
is **manually reviewed (hours to 72 h)** and sometimes closed. You must log in
via SSH or the panel at least once every **90 days** or the account is deleted.
No SLA.

### Route 4 — Cloudflare Workers rewrite

Workers Free needs no card: 100k requests/day, no sleep, no cold start,
permanent `*.workers.dev` URL. But Workers can't run Python/Telethon, so the
app would be rewritten in JavaScript using the **Telegram Bot API** — still
chat app as database, just via a bot token. Files capped at ~50 MB, and it's a
second implementation to maintain. Ask the agent and it will build this.

## Hosts that will ask for a card

Northflank, alwaysdata, Koyeb ($29 hold), Oracle/Google/AWS (identity
verification), Fly.io, Hugging Face Docker Spaces (PRO), and — for some new
accounts — Render.

## Hosts that are free but not 24/7

Render (sleeps → Route 1 fixes it), Zeabur (auto-sleep), SnapDeploy (100
h/month), Back4App free container (dies after 60 min per deploy), Railway
($1/month credit), PythonAnywhere free (WSGI only, outbound allowlist, expires
monthly), Replit/Glitch/Colab (sleep or disconnect).
