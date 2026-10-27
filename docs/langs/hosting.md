# Free 24/7 Hosting

Render's free plan spins down after ~15 minutes of inactivity, so it is not
24/7. The app is host-agnostic now (relative URLs, `PORT`, Docker, three
storage backends), so you can move it anywhere. Full copy-paste steps live in
[`deploy/README.md`](https://github.com/Seigh-sword/storage1024/blob/main/deploy/README.md).

### Picks (checked October 2026)

| Host | Free | 24/7 | Card | Disk |
| --- | --- | --- | --- | --- |
| [Northflank Sandbox](https://northflank.com/pricing) | Yes | **Yes** | No | Ephemeral |
| [Oracle Cloud Always Free](https://www.oracle.com/cloud/free/) | Yes, forever | Yes | Verification only | 200 GB |
| Home device + [Cloudflare Tunnel](https://tech-insider.org/cloudflare-tunnel-setup-2026-homelab/) | Yes | Yes | No | Persistent |
| [alwaysdata Free](https://www.alwaysdata.com/en/offers/) | Yes, for life | Yes | No | 1 GB |

Not 24/7 (or no longer free): Koyeb (free plan closed to new users in 2026),
Hugging Face Docker Spaces (PRO required), PythonAnywhere (WSGI-only,
outbound allowlist), Zeabur (auto-sleep), Fly.io/Railway (trial credit), and
Render free (sleeps).

### Durability on ephemeral hosts — CADB

Storage1024 is **chat app as database**: your Telegram channel holds the index
and files. That is the primary backend, and it makes an ephemeral disk
harmless. Set `STORAGE_BACKEND=telegram` with the four Telegram secrets; see
[`deploy/northflank.md`](https://github.com/Seigh-sword/storage1024/blob/main/deploy/northflank.md)
for the exact walkthrough.

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

On Northflank, deploy this repo's `Dockerfile`, set port `8000` and health
check `/api/health`, then add `STORAGE_BACKEND=github`, `GITHUB_TOKEN` and
`GITHUB_REPO`. No keep-alive ping is needed there. For hosts that do sleep,
`.github/workflows/keep-alive.yml` pings `/api/health` every 10 minutes.
