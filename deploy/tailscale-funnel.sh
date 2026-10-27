#!/usr/bin/env bash
# Free, stable public HTTPS URL for a home device - no domain, no card, no
# port forwarding. Tailscale's Personal plan is free forever and includes
# Funnel. Public URL: https://<machine>.<tailnet>.ts.net (ports 443/8443/10000).
# Docs: https://tailscale.com/docs/features/tailscale-funnel
set -euo pipefail
LOCAL_PORT="${1:-8000}"

if ! command -v tailscale >/dev/null 2>&1; then
    echo "Install Tailscale first: https://tailscale.com/download" >&2
    exit 1
fi

# First run may open a browser to enable MagicDNS + HTTPS certificates and
# add the funnel node attribute to your tailnet policy. Approve it, then rerun.
echo "Publishing local port ${LOCAL_PORT}..."
echo "Copy the https://<machine>.<tailnet>.ts.net URL printed below."
exec tailscale funnel "$LOCAL_PORT"
