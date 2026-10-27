# Zero-card deployment (read this if signup asked for a card)

You hit this on Northflank **and** alwaysdata:

> "To continue your registration and to prevent misuse, you must validate a
> credit or debit card."

That is an anti-abuse **verification hold** (usually a temporary pre-auth, not
a charge). It is triggered by country, IP reputation, VPN/proxy, or a fresh
email — not by anything wrong with your project. Both hosts advertise "no card
needed" but apply this check to a subset of signups, so their marketing is
misleading. This guide lists the routes where **no card can ever be asked**.

> Quick fix if you get that screen: try again from a different network (mobile
> data instead of campus Wi-Fi), a different browser/incognito, and an
> established email (Gmail/Outlook) rather than a new/throwaway one. Some
> people get through; many in India do not. Don't waste an evening on it.

---

## The honest 2026 picture

There is no longer a free 24/7 **container PaaS** that reliably needs no card.
Every one of them either sleeps, expires, or asks for card verification. What
remains falls into four buckets:

| Route | Card | Hardware | Approval | Code change | Reliability |
| --- | --- | --- | --- | --- | --- |
| **1. Render free + 5-min pinger** | No (existing account) | No | No | None | Good; 5 GB bandwidth/month |
| **2. Own device + free tunnel** | No | Yes (phone/laptop) | No | None | Depends on your device |
| **3. Serv00 free shell** | No | No | **Manual, up to 72 h** | None | No SLA; 90-day login rule |
| **4. Cloudflare Workers (BUILT)** | No | No | No | **Already done** | Best; 19 MiB/file cap |

> **NEW — Route 4 is no longer a proposal.** The Worker implementation now
> exists in [`workers/`](../workers/) with 15 passing tests, and the exact
> copy-paste steps are in [`workers.md`](workers.md). It is the only route that
> is genuinely free, always on, needs no hardware, and needs nothing more from
> Telegram than a **bot token + channel id** (no `API_ID` / `API_HASH` /
> session string). **Start there.**

**Route 1 is the fastest if you want to keep the Python build unchanged.** You
already had a Render account (that's where `storage1024.onrender.com` lived).
Render's free plan gives **750 free instance-hours per month**; one service
awake 24/7 uses ~720–744 h, so it fits. The only problem was the 15-minute
spin-down — and a free 5-minute ping fixes that.
[Render free docs](https://render.com/docs/free) ·
[why pings work](https://odown.com/blog/how-to-keep-a-render-free-service-from-sleeping/)

---

## Route 1 — Render free + UptimeRobot (recommended, ~10 minutes)

1. Log into your **existing** Render account. If it also demands a card, skip
   to Route 2 or 3.
2. Create a **Web Service** from
   `https://github.com/Seigh-sword/storage1024`, branch
   `arena/1bde6926-storage1024` (no PR, no merge).
   - Runtime: Python 3.11 (`.python-version` already pins it)
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn bridge:app --host 0.0.0.0 --port $PORT`
   - Health check path: `/api/health`
3. Environment variables — paste
   [`render.env.example`](render.env.example) (same four Telegram secrets as
   the other guides). Key ones: `STORAGE_BACKEND=telegram`, `API_ID`,
   `API_HASH`, `TELEGRAM_SESSION`, `CHANNEL_ID`, `CREATE_PROJECT_KEY`.
4. Sign up at **UptimeRobot** — free plan, **no credit card**, 50 monitors,
   5-minute checks. <https://uptimerobot.com/pricing/>
   - Add New Monitor → **HTTP(S)** → URL:
     `https://<your-service>.onrender.com/api/health`
   - Interval: **5 minutes**.
   - ⚠️ Do **not** monitor `/robots.txt`: Render intercepts that path while
     the service is asleep, so the check lies and the app still sleeps. Ping a
     real route like `/api/health`.
5. Done. The service never idles for 15 minutes, so it never spins down.

**Caveats, honestly:**

- 750 instance-hours/month is a hard cap. One awake service fits; a second one
  will push you over and Render **suspends all free services** until the 1st.
  Keep exactly one free web service in the workspace.
- Free tier bandwidth is ~5 GB/month. Files proxied through the API count
  against it — fine for personal use, not for heavy sharing.
- If UptimeRobot has an outage or GitHub Actions is delayed past 15 minutes,
  you get one ~1-minute cold start. Not true 100.000% uptime, but effectively
  24/7.
- Render's own docs say no card is required
  <https://render.com/articles/platforms-with-a-real-free-tier-for-developers-in-2026>,
  but some 2026 trackers report card verification for **new** free web
  services <https://flywp.com/blog/9769/best-free-docker-hosting-platforms/>.
  An existing account usually avoids it.

**Alternative pingers (all free, no card):**

- `.github/workflows/keep-alive.yml` in this repo pings every 5 minutes.
  ⚠️ Scheduled GitHub Actions only run on the repository's **default branch** —
  set Settings → Branches → default branch to
  `arena/1bde6926-storage1024` (this is **not** a PR/merge and does not end
  this chat), or the workflow will never fire. Set the `APP_URL` repository
  variable first. GitHub disables schedules after 60 days of repo inactivity.
- A Cloudflare Worker cron (free, no card) is more reliable than GitHub
  Actions. See [`keepalive-worker.js`](keepalive-worker.js).

---

## Route 2 — Your own device + a free tunnel (zero signup, zero card)

No account of any kind is needed for a Cloudflare **Quick Tunnel**:

```bash
# Linux laptop / Raspberry Pi / WSL:
git clone -b arena/1bde6926-storage1024 \
    https://github.com/Seigh-sword/storage1024.git && cd storage1024
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env         # fill the 4 Telegram secrets
STORAGE_BACKEND=telegram PORT=8000 .venv/bin/python bridge.py &
./deploy/quick-tunnel.sh 8000    # no login; prints a free https URL
```

`cloudflared tunnel --url` needs **no account and no domain** — it prints a
random `https://<word>.trycloudflare.com` URL. The catch: the URL changes on
every restart. For a **stable** free URL, use one of these instead (both need
an account but no card):

- **Tailscale Funnel** — free Personal plan, sign in with Google/GitHub,
  stable `https://<machine>.<tailnet>.ts.net`, no port forwarding.
  `./deploy/tailscale-funnel.sh 8000`.
  <https://tailscale.com/docs/features/tailscale-funnel> ·
  <https://tailscale.com/pricing>
- **ngrok free** — one permanent static dev domain like
  `<name>.ngrok-free.dev`, no endpoint timeout, no card. Limits: 1 GB
  bandwidth/month, 20k requests/month, and browsers see an interstitial
  warning page. <https://ngrok.com/docs/pricing-limits/free-plan-limits>

**Android / Termux** works too (an old phone is a fine 24/7 server if you
leave it charging):

```bash
pkg update && pkg install -y python git openssh tmux
pkg install -y binutils rust clang   # needed to build pydantic-core on Android
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

If a wheel fails to build, install the Termux package of that dependency
first (`pkg install python-pydantic python-cryptography` etc.). Keep the
process alive with `tmux` and `termux-wake-lock`.

**Reality check:** this is only 24/7 if the device and your home internet are.
Android may kill background processes, so use `termux-wake-lock` and test
overnight.

---

## Route 3 — Serv00 (no card, but manual approval)

Serv00 is a genuinely free, no-card FreeBSD shell: 3 GB SSD, 512 MB RAM, SSH,
cron, 3 TCP/UDP ports, own long-running processes, Python 3.11.
<https://www.serv00.com/> · <https://docs.serv00.com/Python/>

1. Register at <https://www.serv00.com/register-account/>. Applications now go
   through **manual review, a few hours to 72 hours**, and registration is
   sometimes closed when servers are full — check the forum if nothing arrives.
2. In DevilWEB enable **Run your own applications** (Binexec) and reserve a
   TCP port under **Port reservation**.
3. Over SSH: clone the branch, make a venv, `pip install -r requirements.txt`.
   FreeBSD may need to compile some wheels; if `pydantic-core` fails, install
   Rust first.
4. Start uvicorn inside `tmux` on the reserved port, with the same Telegram
   env vars, and add a cron entry to restart it if it dies.
5. ⚠️ **Log in via SSH or the panel at least once every 90 days** or the
   account is deleted. Add a monthly calendar reminder (an HTTP ping does
   **not** count — it must be a login).

No SLA, forum-only support, and the free subdomain can be blocked on some
networks. It's fat 512 MB though, and no card, ever.

---

## Route 4 — Cloudflare Workers (BUILT — no card, no hardware, real 24/7)

Cloudflare's Workers Free plan needs **no credit card** and gives 100,000
requests/day with no sleep and no cold start. Static assets (the dashboard,
docs and SDK files) are free and unlimited and do not consume that quota.
<https://workers.cloudflare.com/> ·
<https://developers.cloudflare.com/workers/platform/pricing/>

**It is built.** [`workers/`](../workers/) contains a complete JavaScript
implementation of the Storage1024 API, using the Telegram Bot API instead of
Telethon (Workers cannot open raw MTProto sockets). It is still **chat app as
database**: every file is a document message in your Telegram channel, every
global variable is a text message, and the project index is a pinned JSON
document. Workers KV only caches the pointer to that pinned index — wipe KV and
the Worker rebuilds itself from `getChat().pinned_message`.

You get a permanent `https://storage1024.<you>.workers.dev` URL, free, always
on, no card. Only a **bot token** and a **channel id** are needed — no
`API_ID`, `API_HASH` or `TELEGRAM_SESSION`.

Trade-offs: Bot API files are capped at ~50 MB up / 20 MB down, so this build
enforces **19 MiB per file** (vs 1800 MB with Telethon); 10 ms CPU and 100k
invocations/day; KV's 1,000 writes/day allows ~500 mutations/day. There are
also two implementations to maintain. Full details and the copy-paste deploy:
**[`deploy/workers.md`](workers.md)** · docs page: `/docs#workers`.

Verify locally before deploying:

```bash
cd workers
npm install
npm test          # 15 offline tests
npm run dry-run   # validates config + bundles
```

---

## Hosts that will ask you for a card (stop trying these)

| Host | What happens |
| --- | --- |
| Northflank | Official page says "No card needed"; some regions get the verification hold you saw |
| alwaysdata | Official page says "Registration without credit card"; you got the same hold |
| Koyeb | Card + $29 pre-auth hold since Feb 2026; free plan closed to new users |
| Oracle Cloud / Google Cloud / AWS | Card for identity verification, even on free tiers |
| Fly.io | Free tier withdrawn; card required |
| Hugging Face Docker Spaces | PRO subscription ($9/mo) required to create one |
| Render (new account) | Conflicting reports — may ask for a card on new free web services |

## Hosts that are free but not 24/7

Render (sleeps after 15 min → Route 1 fixes it), Zeabur (auto-sleep),
SnapDeploy (sleeps after 15 min, 100 h/month), Back4App Containers free
(container is destroyed 60 min after each deploy), Railway ($1/month credit
does not cover a month of uptime), PythonAnywhere free (WSGI only, outbound
allowlist, web app expires after a month), Replit / Glitch / Colab (sleep or
disconnect).

---

## Bottom line

- **Want the technically best free 24/7 with no card and no hardware?** Route
  4 — **already built**, see [`workers.md`](workers.md). This is the
  recommended path. It only needs a Cloudflare account (email), a Telegram bot
  token and a channel id.
- **Want to keep full Python/Telethon with 1800 MB files and zero code change?**
  Route 1: redeploy on your existing Render account and add a UptimeRobot
  5-minute monitor on `/api/health`.
- **Want zero accounts at all?** Route 2: an old phone/laptop + Cloudflare
  Quick Tunnel.
- **Want zero hardware, zero card, full Python, and don't mind waiting?** Route
  3: Serv00, with manual approval and the 90-day login rule.
