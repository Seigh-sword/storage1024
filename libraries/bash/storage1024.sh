#!/usr/bin/env bash
# Storage1024 bash helpers. Source this file, then call the functions below.
# Requires curl and python3 (for JSON/URL encoding).

STORAGE1024_API="${STORAGE1024_API:-https://storage1024.onrender.com/api}"
STORAGE1024_API="${STORAGE1024_API%/}"
STORAGE1024_TOKEN="${STORAGE1024_TOKEN:-}"
STORAGE1024_USERID="${STORAGE1024_USERID:-}"

s1024_set_api_base() { STORAGE1024_API="${1%/}"; }
s1024_set_token() { STORAGE1024_TOKEN="$1"; }
s1024_set_userid() { STORAGE1024_USERID="$1"; }
s1024_set_userID() { s1024_set_userid "$1"; }

_s1024_encode() {
    python3 -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$1"
}

_s1024_url() {
    printf '%s/projects/%s%s' "$STORAGE1024_API" "$(_s1024_encode "$STORAGE1024_USERID")" "$1"
}

_s1024_curl() {
    curl -sS -H "Authorization: Bearer $STORAGE1024_TOKEN" "$@"
}

s1024_health() {
    _s1024_curl "$STORAGE1024_API/health"
}

s1024_get_gv() {
    local url
    url="$(_s1024_url "/gv/$(_s1024_encode "$1")")"
    _s1024_curl "$url" | python3 -c 'import sys, json
try:
    print(json.load(sys.stdin).get("value", ""))
except Exception:
    print("")'
}

s1024_add_gv() {
    local payload
    # Build JSON with python3: values containing quotes/newlines used to break the payload.
    payload="$(python3 -c 'import json, sys; print(json.dumps({"alias": sys.argv[1], "value": sys.argv[2]}))' "$1" "$2")"
    _s1024_curl -X POST -H 'Content-Type: application/json' -d "$payload" "$(_s1024_url /gv)"
}

s1024_gv_json() {
    _s1024_curl "$(_s1024_url /gv)"
}

s1024_delete_gv() {
    _s1024_curl -X DELETE "$(_s1024_url "/gv/$(_s1024_encode "$1")")"
}

s1024_upload_file() {
    local alias="$1" path="$2"
    if [[ ! -f "$path" ]]; then echo "File not found: $path" >&2; return 1; fi
    _s1024_curl -X POST -F "file=@$path" -F "alias=$alias" "$(_s1024_url /upload)"
}

s1024_download_file() {
    local alias="$1" output="$2"
    _s1024_curl -o "$output" "$(_s1024_url "/files/$(_s1024_encode "$alias")")"
}

s1024_list_files() {
    _s1024_curl "$(_s1024_url /files)"
}
