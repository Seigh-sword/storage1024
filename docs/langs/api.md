# REST API

The API is served by the same host as the dashboard. All project routes take a
bearer token; the dashboard itself is just a client of this API.

Base URL: `https://<your-host>/api`

The live deployment's health endpoint is [`GET /api/health`](/api/health). It
reports which storage backend is active without revealing any secret.

## Authentication

```http
Authorization: Bearer s1024-....;qi=
```

| Token | Ends with | Can do |
| --- | --- | --- |
| Private | `;qi=` | Everything (admin) |
| Public | `;gg=` | Upload files, write/read variables, download files |

Tokens live in the project index. Create a project in the dashboard or with
`POST /projects/create`, then keep the private token secret. Revoke a lost
token with `POST /projects/{id}/tokens/revoke`.

## Endpoints

| Method | Path | Scope | Description |
| --- | --- | --- | --- |
| GET | `/health` | – | Liveness + backend status |
| POST | `/projects/create` | – | Create a project, returns both tokens |
| GET | `/index` | private | Full project record (files, GVs, tokens) |
| POST | `/projects/{id}/tokens` | private | Create `{"type":"private"|"public"}` token |
| POST | `/projects/{id}/tokens/revoke` | private | `{"token":"..."}` |
| POST | `/projects/{id}/upload` | private/public | multipart `file` + `alias` |
| GET | `/projects/{id}/files` | private/public | List files with shareable URLs |
| GET | `/projects/{id}/files/{alias}` | private/public | Download a file (bearer required) |
| DELETE | `/projects/{id}/files/{alias}` | private | Remove a file from the index |
| POST | `/projects/{id}/gv` | private/public | `{"alias":"score","value":"9001"}` |
| GET | `/projects/{id}/gv` | private/public | All variables as `{alias: value}` |
| GET | `/projects/{id}/gv/{alias}` | private/public | `{"alias":"...","value":"..."}` |
| DELETE | `/projects/{id}/gv/{alias}` | private | Delete a variable |
| GET | `/f/{id}/{alias}?key=...` | – | Stable public file link (no header) |

### Create a project

```bash
curl -X POST https://<your-host>/api/projects/create \
  -H 'Content-Type: application/json' \
  -d '{"name":"My Game"}'
```

```json
{
  "status": "success",
  "project_id": "4821",
  "tokens": {
    "private": "s1024-...;qi=",
    "public": "s1024-...;gg="
  }
}
```

### Variables

```bash
# Set (values are stored as strings; numbers/booleans are accepted)
curl -X POST https://<your-host>/api/projects/4821/gv \
  -H 'Authorization: Bearer <TOKEN>' \
  -H 'Content-Type: application/json' \
  -d '{"alias":"score","value":"9001"}'

# Read one
curl https://<your-host>/api/projects/4821/gv/score \
  -H 'Authorization: Bearer <TOKEN>'
# {"alias":"score","value":"9001"}

# Read all
curl https://<your-host>/api/projects/4821/gv \
  -H 'Authorization: Bearer <TOKEN>'
# {"score":"9001"}
```

### Files

```bash
curl -X POST https://<your-host>/api/projects/4821/upload \
  -H 'Authorization: Bearer <TOKEN>' \
  -F 'file=@./photo.jpg' \
  -F 'alias=my_image'
```

```json
{
  "status": "success",
  "alias": "my_image",
  "url": "https://<your-host>/f/4821/my_image?key=RANDOM_KEY",
  "file": {"id": "...", "name": "photo.jpg", "bytes": 12345, "url": "..."}
}
```

The `url` is a capability link: anyone who has it can download the file, but it
contains no account token. Downloading through the API instead requires a
bearer token:

```bash
curl -OJ https://<your-host>/api/projects/4821/files/my_image \
  -H 'Authorization: Bearer <TOKEN>'
```

Uploads are limited by `MAX_UPLOAD_MB` (default 1800). Oversized uploads get
`413`, invalid tokens `401`, restricted scopes `403`, and an unreachable
storage backend `503` (the server never pretends the index is empty).

## Deployment notes

The backend can run in two modes, selected by `STORAGE_BACKEND`:

* `auto` (default) — Telegram, else GitHub, else local files.
* `telegram` — always Telegram (misconfiguration is reported by `/api/health`).
* `github` — always a GitHub repo: set `GITHUB_TOKEN` (`Contents: read/write`)
  and `GITHUB_REPO=owner/repo`. Free, durable, no card. Files are capped by
  `GITHUB_MAX_FILE_MB` (default 20); the API returns `413` above it.
* `local` — always local files under `DATA_DIR`.

On hosts with ephemeral disks (Render free tier, Northflank Sandbox), use the
Telegram or GitHub backend for durable data, or attach a persistent disk when
using `local`. See [Free 24/7 Hosting](/docs#hosting) for deployment options.
