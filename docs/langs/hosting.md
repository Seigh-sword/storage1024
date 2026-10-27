# Free 24/7 Hosting

> 🛑 **No credit card?** Northflank and alwaysdata both show a card
> verification wall for many signups. Use
> [Zero-Card Hosting](/docs#nocard) instead.

Render's free plan spins down after ~15 minutes of inactivity, so it is not
24/7 on its own — but a free 5-minute ping fixes that. The app is
host-agnostic now (relative URLs, `PORT`, Docker, three storage backends), so
you can move it anywhere. Full copy-paste steps live in
[`deploy/README.md`](https://github.com/Seigh-sword/storage1024/blob/main/deploy/README.md).

### No-card picks (checked October 2026)

| Host | Free | 24/7 | Card | RAM / disk |
| --- | --- | --- | --- | --- |
| **Render free + 5-min pinger** | Yes | Yes | No (existing account) | 512 MB / ephemeral |
| **[alwaysdata Free](https://www.alwaysdata.com/en/offers/)** | Yes, for life | Yes | No* | 256 MB / 1 GB |
| [Northflank Sandbox](https://northflank.com/pricing) | Yes | Yes | Official page says no; some regions ask for verification | ~1 GB / ephemeral |
| [Serv00](https://www.serv00.com/) | Yes | Yes | **No** | 512 MB / 3 GB |
| Home device + [Tailscale Funnel](https://tailscale.com/docs/features/tailscale-funnel) | Yes | Yes | **No** | your hardware |

[Oracle Cloud Always Free](https://www.oracle.com/cloud/free/) is excellent but
requires a card for identity verification, so it is excluded here.
`*` alwaysdata and Northflank may still demand card *verification*; see
[Zero-Card Hosting](/docs#nocard).

Not 24/7 (or no longer free): Koyeb (free plan closed to new users in 2026),
Hugging Face Docker Spaces (PRO required), PythonAnywhere (WSGI-only,
outbound allowlist), Zeabur (auto-sleep), Fly.io/Railway (trial credit), and
Render free (sleeps).

### Durability on ephemeral hosts — CADB

Storage1024 is **chat app as database**: your Telegram channel holds the index
and files. That is the primary backend, and it makes an ephemeral disk
harmless. Set `STORAGE_BACKEND=telegram` with the four Telegram secrets; see
[`deploy/alwaysdata.md`](https://github.com/Seigh-sword/storage1024/blob/main/deploy/alwaysdata.md)
(no card) or
[`deploy/northflank.md`](https://github.com/Seigh-sword/storage1024/blob/main/deploy/northflank.md)
(Docker) for the exact walkthrough.

- `STORAGE_BACKEND=telegram` — **primary.** Up to 1800 MB files, data lives in
  your channel, which is also your backup.
- `STORAGE_BACKEND=github` — optional fallback (private repo + token), files
  capped by `GITHUB_MAX_FILE_MB` (default 20).
- `STORAGE_BACKEND=local` — only on a host with a persistent volume.

`auto` selects telegram → github → local based on which secrets exist.
`/api/health` reports the active backend.

### Quick deploy

```bash
docker compose up -d --build     # any VM / home server
curl localhost:8000/api/health
```

On alwaysdata, create a **User program** site with
`uvicorn bridge:app --host $IP --port $PORT --workers 1` and paste the four
Telegram secrets. On Northflank, deploy the `Dockerfile` on port `8000` with
health check `/api/health`. Neither host sleeps, so no keep-alive ping is
needed. For hosts that do sleep,
`.github/workflows/keep-alive.yml` pings `/api/health` every 10 minutes.
