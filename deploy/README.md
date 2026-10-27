# Free 24/7 hosting (October 2026)

Render's free plan is **not** 24/7: the service spins down after ~15 minutes of
inactivity and takes about a minute to cold-start again. The app itself is now
host-agnostic (relative URLs, `PORT`, Docker, three storage backends), so it can
run anywhere. This file compares the free options that are actually still
available and gives copy-paste deployment steps.

> Prices and free tiers change constantly — verify on the provider's own
> pricing page before signing up. All figures below were checked 2026-10-27.

## TL;DR

| Host | Free? | 24/7? | Card? | Persistent disk? | Best when |
| --- | --- | --- | --- | --- | --- |
| **Northflank Sandbox** | Yes | **Yes — "always on, no sleeping"** | Official page: no | No (ephemeral) | You want zero cost, no hardware, no card |
| **Oracle Cloud Always Free** | Yes, forever | Yes | Yes, verification only | Yes (200 GB) | You have a card and want a real VM |
| **Home device + Cloudflare Tunnel** | Yes | Yes, if the device stays on | No | Yes | You have an old laptop/Pi/phone |
| **alwaysdata Free** | Yes, for life | Yes | No | Yes (1 GB) | Tiny personal project, no Docker |
| Render free | Yes | **No** — sleeps | No | No (ephemeral) | Only with a keep-alive ping |
| Koyeb / HF Spaces / PythonAnywhere / Zeabur / Fly.io | see "Ruled out" below | | | | |

**Recommended combo:** Northflank (always-on, no card) + the **GitHub storage
backend** (durable, free, no card) — see below. If you already have the
Telegram API credentials from the original project, use `STORAGE_BACKEND=telegram`
instead and skip the GitHub setup.

## The durability problem (read this first)

Free hosts give you an **ephemeral** disk: every redeploy/restart wipes
`DATA_DIR`. That is why the app now has three backends:

| `STORAGE_BACKEND` | Where data lives | Secrets needed | File size | Needs a disk? |
| --- | --- | --- | --- | --- |
| `telegram` | Your Telegram channel | `API_ID`, `API_HASH`, `TELEGRAM_SESSION`, `CHANNEL_ID` | up to 1800 MB | No |
| `github` | A private GitHub repo | `GITHUB_TOKEN`, `GITHUB_REPO` | 20 MB default (`GITHUB_MAX_FILE_MB`) | No |
| `local` | `DATA_DIR` on the host | none | up to 1800 MB | **Yes** |

`auto` picks telegram → github → local depending on which secrets are set.
`/api/health` always tells you which backend is live. Use `telegram` or
`github` on ephemeral hosts; use `local` only on a VM/home server with a
persistent volume.

---

## Option 1 — Northflank Sandbox (no card, truly always-on)

Northflank's official pricing page lists a free **Sandbox**: 2 services,
2 jobs, 1 database, up to $20/month of resources, "Always on, no sleeping",
"No card needed". Ephemeral storage is free; persistent volumes are paid —
which is fine, because the GitHub/Telegram backends need no volume.
<https://northflank.com/pricing>

Some third-party trackers report that a card is requested for anti-abuse
verification at signup (a hold, not a charge). If that happens to you, try
Option 2 or 3.

1. Push this branch to GitHub and merge to `main` (or select the branch during
   setup).
2. In Northflank: **Create project → Service → Deploy from Git**, pick the repo.
3. Build type: **Dockerfile** (root `Dockerfile`), port **8000**, health check
   path `/api/health`.
4. Add secret environment variables in the service settings:
   - `STORAGE_BACKEND=github`
   - `GITHUB_TOKEN=<fine-grained token with Contents: read/write on one repo>`
   - `GITHUB_REPO=<owner>/<private-repo>`
   - optionally `CREATE_PROJECT_KEY=<random>` (then pass `X-Create-Key` when
     creating projects).
   - Or use `STORAGE_BACKEND=telegram` and the four Telegram vars.
5. Deploy. Northflank gives you a public HTTPS URL; custom domains are
   supported on the free plan. No sleep timer, no ping needed.

GitHub token setup: create a **private** repo (it can be empty), then
**Settings → Developer settings → Personal access tokens → Fine-grained
tokens**, scope it to that one repo with **Contents: read and write**. The
backend creates `storage1024-data/index.json`, `global_vars.json` and
`files/` on first write. Keep `GITHUB_MAX_FILE_MB` at 20 or lower — the
GitHub Contents API is not meant for large binary blobs.

---

## Option 2 — Oracle Cloud Always Free VM (best resources, card for verification)

Always Free includes up to **2 OCPUs / 12 GB RAM** on Ampere A1 (halved from
4/24 in June 2026), **200 GB** block storage and **10 TB** outbound per month,
with no time limit. A credit/debit card is required for **identity
verification only** — Oracle places a temporary hold and does not charge for
Always Free resources. Signup rejections and "out of host capacity" errors are
common; pick your home region carefully (it is permanent), e.g. Mumbai.
<https://www.oracle.com/cloud/free/> ·
<https://www.oracle.com/cloud/free/faq/> ·
<https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm>

1. Create an Always Free VM (Ubuntu 22.04+ or Oracle Linux, Ampere A1,
   1–2 OCPU / 4–8 GB is plenty).
2. Open port **8000** in the VCN security list *and* in the VM's firewall
   (`sudo iptables -I INPUT -p tcp --dport 8000 -j ACCEPT` /
   `firewall-cmd --add-port=8000/tcp --permanent`).
   Alternatively skip public ports entirely and use a Cloudflare Tunnel
   (Option 3).
3. Install Docker + Compose, clone the repo, copy `.env.example` to `.env`:

   ```bash
   git clone https://github.com/Seigh-sword/storage1024.git
   cd storage1024
   cp .env.example .env
   # STORAGE_BACKEND=local is fine here: the VM disk is persistent
   docker compose up -d --build
   curl localhost:8000/api/health
   ```

4. `restart: unless-stopped` in `docker-compose.yml` brings it back after
   reboots. Add a Cloudflare Tunnel or a Caddy reverse proxy for HTTPS.

Because the disk is persistent, `STORAGE_BACKEND=local` works here with **no
Telegram or GitHub credentials at all**.

---

## Option 3 — Old laptop / Raspberry Pi / Android phone + free tunnel

Truly free, no card, 24/7 as long as the device and your home internet stay
on. Cloudflare Tunnel's connector and bandwidth are free; it needs a domain on
Cloudflare for a stable hostname (a `.com`/`.in` domain is a few hundred rupees
a year), or use a quick tunnel with a random URL that changes on restart.
<https://tech-insider.org/cloudflare-tunnel-setup-2026-homelab/>
<https://tech-insider.org/cloudflare-tunnel-setup-2026/>

```bash
# On the device (Linux / Termux / WSL):
git clone https://github.com/Seigh-sword/storage1024.git && cd storage1024
cp .env.example .env          # STORAGE_BACKEND=local, disk is persistent
docker compose up -d --build  # or: .venv/bin/uvicorn bridge:app --port 8000
./deploy/quick-tunnel.sh 8000   # prints a free public https URL
```

For a stable URL: install `cloudflared`, create a tunnel, and use
`deploy/cloudflared/config.yml.example`. For a non-Docker setup use
`deploy/systemd/storage1024.service` (auto-restart on crash/reboot).

Termux note: install Docker alternative is not available — use the venv path:

```bash
pkg install python git
python -m venv .venv && .venv/bin/pip install -r requirements.txt
STORAGE_BACKEND=local PORT=8000 .venv/bin/python bridge.py
```

---

## Option 4 — alwaysdata Free (no card, free for life, small)

Free plan: no credit card, valid without time limit, **1 GB SSD, 256 MB RAM,
¼ CPU**, SSH, Python 3.11 available, personal/non-commercial use only. ASGI
apps are supported through the **User program** site type, which runs uvicorn
on the provided `$IP`/`$PORT`.
<https://www.alwaysdata.com/en/offers/> ·
<https://help.alwaysdata.com/en/docs/web-hosting/languages/python/configuration/> ·
<https://help.alwaysdata.com/en/docs/admin-billing/billing/public-cloud-prices/>

Steps (over SSH):

```bash
git clone https://github.com/Seigh-sword/storage1024.git ~/storage1024
cd ~/storage1024
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Then in the admin panel: **Web → Sites → Add a site → User program**

- Address: `yourname.alwaysdata.net`
- Working directory: `/home/yourname/storage1024`
- Command: `.venv/bin/uvicorn bridge:app --host $IP --port $PORT --workers 1`
- Environment: `STORAGE_BACKEND=local`, `DATA_DIR=/home/yourname/storage1024/data`,
  `PORT=$PORT` (plus Telegram/GitHub vars if you prefer those backends).

Caveats: 256 MB RAM is tight — keep one worker and avoid huge uploads. The
free plan's terms say it "cannot be used to run services"; the User program
site type is a documented feature, but verify with their support before
relying on it 24/7. Unused free sites may be expired.

---

## Ruled out in 2026

- **Koyeb** — free Starter plan closed to new users in February 2026 after the
  Mistral acquisition; new accounts need a paid plan and a $29 pre-authorization
  hold, and the remaining free instance scales to zero after an hour idle.
  <https://toolfreebie.com/koyeb-free-tier-alternatives/>
  <https://www.koyeb.com/docs/faqs/pricing>
- **Hugging Face Spaces** — since July 2026, creating a Docker or Gradio Space
  on CPU Basic requires PRO (~$9/month); free CPU spaces sleep after 48 h.
  <https://huggingface.co/docs/huggingface_hub/en/guides/manage-spaces>
  <https://huggingface.co/docs/hub/en/spaces-overview>
- **PythonAnywhere** — free tier is WSGI-only (no FastAPI/ASGI), outbound
  network is an HTTP(S) allowlist (Telethon needs raw TCP), and unused free web
  apps expire after 1 month. <https://help.pythonanywhere.com/pages/FreeAccountsFeatures/>
- **Zeabur** — free plan auto-sleeps. <https://zeabur.com/docs/en-US/pricing/free-plan>
- **Fly.io / Railway** — trial credit only; trial machines stop after minutes /
  the free credit runs out monthly.
- **Cloud Run / Vercel / Netlify / Cloudflare Workers** — serverless cold
  starts, small request bodies (Cloud Run ~32 MB vs our 1800 MB uploads), and a
  billing account is required for Cloud Run.
- **Render free** — sleeps after 15 min idle; only 750 instance-hours/month.

If you must use a host that sleeps, `.github/workflows/keep-alive.yml` pings
`/api/health` every 10 minutes for free (set the `APP_URL` repository
variable). GitHub disables scheduled workflows after 60 days of repo
inactivity — commit once in a while or re-enable it. A ping reduces downtime;
it does not remove cold starts.

---

## Checklist for any host

1. `PORT` must be read from the environment (the Dockerfile and `bridge.py`
   already do). Bind `0.0.0.0`, one worker.
2. Set `CREATE_PROJECT_KEY` on a public deployment and pass `X-Create-Key`
   from trusted clients; otherwise anyone can create projects.
3. Put secrets in the host's secret manager, never in `.env` in Git.
4. Point a custom domain (or the host's free subdomain) at the service; the
   dashboard, docs and `/s1024.js` all use relative URLs, so they work on any
   hostname.
5. Check `/api/health` — `status: ok` plus `backend: github|telegram|local`.
   `?strict=true` returns 503 if storage is unreachable (use it for external
   monitoring).
6. Back up the index: it is one JSON document in your Telegram channel or
   `index.json` in your GitHub repo / `DATA_DIR`.
