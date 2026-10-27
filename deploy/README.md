# Free 24/7 hosting with NO credit card (October 2026)

Render's free plan is **not** 24/7 (spins down after ~15 minutes idle), and
several 2026 no-card projects report that Render now asks for a card on file
even for the free tier. The app is host-agnostic now (relative URLs, `PORT`,
Docker, three storage backends), so it can run anywhere. This file compares
the options that need **no card** and gives copy-paste deployment steps.

> Prices and free tiers change constantly — verify on the provider's own
> pricing page before signing up. All figures below were checked 2026-10-27.

## TL;DR

| Host | Free? | 24/7? | Card? | RAM / disk | Catch |
| --- | --- | --- | --- | --- | --- |
| **alwaysdata Free** | Yes, for life | Yes | **No** | 256 MB / 1 GB | Personal use only, `*.alwaysdata.net` |
| **Northflank Sandbox** | Yes | **Yes — "always on, no sleeping"** | Official page says no | ~1 GB / ephemeral | Some regions trigger a card *verification* hold |
| **Serv00** | Yes | Yes | **No** | 512 MB / 3 GB | Must log in every 90 days; FreeBSD; no SLA |
| **Home device + Tailscale Funnel** | Yes | Yes, if the device stays on | **No** | whatever you have | Needs hardware + power |
| Oracle Cloud Always Free | Yes, forever | Yes | Yes, verification only | 12 GB / 200 GB | Card required — ruled out here |
| Render free | Yes | **No** — sleeps | Sometimes | 512 MB / ephemeral | Cold starts, 750 instance-hours/month |

**Recommended:** **alwaysdata + the Telegram backend** —
[`alwaysdata.md`](alwaysdata.md) is the exact walkthrough, and
[`alwaysdata.env.example`](alwaysdata.env.example) is the paste-ready env
block. No card, no hardware, no sleep timer, no PR needed (clone the working
branch directly). Storage1024 is **chat app as database**: the Telegram
channel holds everything, so an ephemeral/limited disk is harmless.

The `github` backend is an optional fallback for people who no longer have
their Telegram API credentials; it is not the main path.

## Why no-card is hard in 2026

A real FastAPI + Telethon project that hunted for the same thing in October
2026 ended up on alwaysdata after: Render asked for a card, SnapDeploy
suspended the account for Telegram API tooling, Zeabur stopped new signups,
Koyeb/Fly.io needed cards, Hugging Face Docker Spaces went behind PRO,
InfinityFree was PHP-only and Glitch shut down app hosting. See its
[README](https://github.com/ramwanstream/tg-stream) and its live site
<https://ramwanstream.alwaysdata.net>. alwaysdata's "User program" (documented
for FastAPI/uvicorn) plus fully open outbound TCP is what fits.

Other confirmed dead ends: Koyeb closed its free plan to new users in Feb
2026 <https://toolfreebie.com/koyeb-free-tier-alternatives/>; free HF Docker
Spaces need PRO <https://huggingface.co/docs/hub/en/spaces-overview>;
PythonAnywhere free is WSGI-only with an outbound allowlist and expires after
a month <https://help.pythonanywhere.com/pages/FreeAccountsFeatures/>; Zeabur
auto-sleeps <https://zeabur.com/docs/en-US/pricing/free-plan>.

---

## Option 1 — alwaysdata Free (no card, free for life, always-on)

Free plan: no credit card, valid without time limit, 1 GB SSD, **256 MB RAM**,
¼ CPU, SSH (including a browser terminal), Python 3.11, ASGI via the
**User program** site type, open outbound TCP. Personal/non-commercial use,
`*.alwaysdata.net` address, no custom domain, no SLA.
<https://www.alwaysdata.com/en/offers/> ·
<https://help.alwaysdata.com/en/docs/web-hosting/languages/python/configuration/> ·
<https://help.alwaysdata.com/en/docs/web-hosting/sites/http-servers/user-program/>

Over SSH (or the web terminal at `https://ssh-<account>.alwaysdata.net`):

```bash
git clone -b arena/1bde6926-storage1024 \
    https://github.com/Seigh-sword/storage1024.git ~/storage1024
cd ~/storage1024
python -m venv .venv && .venv/bin/pip install -r requirements.txt
```

Then **Web → Sites → Add a site → User program**:

- Command: `/home/<account>/storage1024/.venv/bin/uvicorn bridge:app --host $IP --port $PORT --workers 1`
- Working directory: `/home/<account>/storage1024`
- Environment: paste [`alwaysdata.env.example`](alwaysdata.env.example)

Full steps, memory notes and troubleshooting: **[`alwaysdata.md`](alwaysdata.md)**.

---

## Option 2 — Northflank Sandbox (worth trying first, more RAM)

Northflank's official pricing page lists a free **Sandbox**: 2 services,
2 jobs, 1 database, up to $20/month of resources, "Always on, no sleeping",
"No card needed". <https://northflank.com/pricing>

⚠️ Third-party trackers report that some regions are asked for a card
**verification hold** at signup — not a charge, but still a card. If that
happens, close the tab and use **Option 1**. If it lets you in without one,
it's the better host (more RAM, Docker, custom domains).

Deploy the root `Dockerfile` as a combined service on port 8000. Full
walkthrough: **[`northflank.md`](northflank.md)** and
[`northflank.env.example`](northflank.env.example).

---

## Option 3 — Serv00 (no card, 512 MB, but keep the account alive)

Free: 3 GB SSD, **512 MB RAM**, 15 system processes, SSH, cron, 3 TCP/UDP
ports, own applications via "Run your own applications"/Binexec, Python 3.11.
<https://www.serv00.com/> · <https://docs.serv00.com/Python/>

Caveats you must accept:

- **Log in via SSH or the DevilWEB panel at least once every 90 days** or the
  account is deleted. Automate a monthly login with a scheduled GitHub
  Action using a repository secret, or just set a calendar reminder.
- FreeBSD, not Linux — some wheels may need compiling.
- No SLA, forum-only support, free subdomain may be blocked on some networks.

Steps: enable *Run your own applications*, reserve a TCP port, create a venv,
install `requirements.txt`, start uvicorn inside `tmux`/`screen` on the
reserved port, and add a cron entry to restart it if it dies. Set the same
Telegram environment variables as alwaysdata. Use `STORAGE_BACKEND=telegram`
so the 3 GB disk is irrelevant.

---

## Option 4 — Old laptop / Raspberry Pi / Android phone + Tailscale Funnel

Truly free, no card, no cloud account, **stable** HTTPS URL with no domain
and no port forwarding. Tailscale's Personal plan is free forever and includes
Funnel; the URL is `https://<machine>.<tailnet>.ts.net`.
<https://tailscale.com/pricing> ·
<https://tailscale.com/docs/features/tailscale-funnel>

```bash
# On the device (Linux / Termux / WSL):
git clone -b arena/1bde6926-storage1024 \
    https://github.com/Seigh-sword/storage1024.git && cd storage1024
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env      # fill the four Telegram vars; STORAGE_BACKEND=telegram
STORAGE_BACKEND=telegram PORT=8000 .venv/bin/python bridge.py &
./deploy/tailscale-funnel.sh 8000   # prints your permanent public URL
```

Funnel needs MagicDNS + HTTPS certificates enabled for the tailnet (the first
`tailscale funnel` run prompts you to approve). It only publishes on ports
443/8443/10000 and has non-configurable bandwidth limits. Keep the device on
24/7; use `deploy/systemd/storage1024.service` for auto-restart on Linux.

Alternatives if you have a domain: `deploy/cloudflared/config.yml.example`
(Cloudflare Tunnel, free unmetered bandwidth). Without a domain and without
Tailscale, `deploy/quick-tunnel.sh` gives a free **random** URL that changes
on every restart.

---

## Option 5 — Oracle Cloud (excluded: needs a card)

Always Free is genuinely free forever with 2 OCPU / 12 GB / 200 GB disk, but
signup requires a credit/debit card for identity verification (not charged).
<https://www.oracle.com/cloud/free/faq/> ·
<https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm>
If you later get a card, `docker compose up -d --build` with the root
`docker-compose.yml` is all you need.

---

## Storage: the CADB part

| `STORAGE_BACKEND` | Data lives in | Secrets | File cap | Needs a disk? |
| --- | --- | --- | --- | --- |
| `telegram` **(primary)** | Your Telegram channel | 4 vars | 1800 MB | No |
| `github` (fallback) | A private GitHub repo | `GITHUB_TOKEN`, `GITHUB_REPO` | 20 MB default | No |
| `local` | `DATA_DIR` on the host | none | 1800 MB | **Yes** |

Set `STORAGE_BACKEND=telegram` explicitly on any ephemeral host so a bad
config fails loudly in `/api/health` instead of silently writing to a disk
that will vanish. `auto` picks telegram → github → local. Get the four
secrets with `generate_session.py` (it prints channel ids too) — see step 0 of
either deployment guide.

## Keep-alive / uptime

None of the four no-card options sleep, so **no ping is required**. If you
still want a free uptime check, `.github/workflows/keep-alive.yml` hits
`/api/health` every 10 minutes — set the `APP_URL` repository variable. GitHub
disables scheduled workflows after 60 days of repo inactivity, so commit once
in a while. Serv00's 90-day login rule is separate and cannot be satisfied by
an HTTP ping.

## Checklist for any host

1. One worker; `PORT`/`$PORT` from the environment; relative URLs everywhere.
2. Set `CREATE_PROJECT_KEY` and pass `X-Create-Key` — otherwise anyone who
   finds the URL can create projects.
3. Secrets in the host's environment/secret manager, never in Git.
4. Check `/api/health` → `status: ok`, `backend: telegram`.
   `?strict=true` returns 503 when storage is unreachable.
5. Set the repo homepage to the new URL; the old `storage1024.onrender.com`
   address is gone.
6. Your backup is the Telegram channel itself (pinned
   `storage1024-index.json` + file/variable messages).
