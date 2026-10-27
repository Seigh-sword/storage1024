#!/usr/bin/env bash
# Free public URL with NO domain and NO card, for a home server.
# The hostname changes whenever the tunnel restarts - fine for testing,
# not ideal as a permanent address. For a STABLE free URL with no domain,
# use ./tailscale-funnel.sh instead. With a domain, use config.yml.example.
set -euo pipefail
PORT_TO_EXPOSE="${1:-8000}"

if command -v cloudflared >/dev/null 2>&1; then
    echo "Starting Cloudflare quick tunnel on port ${PORT_TO_EXPOSE}..."
    echo "Copy the https://*.trycloudflare.com URL printed below."
    exec cloudflared tunnel --url "http://localhost:${PORT_TO_EXPOSE}"
fi

echo "cloudflared not found - using localhost.run over SSH instead."
echo "Copy the https://*.lhr.life URL printed below."
exec ssh -o StrictHostKeyChecking=no -R "80:localhost:${PORT_TO_EXPOSE}" nokey@localhost.run
