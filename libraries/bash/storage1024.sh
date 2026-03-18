#!/bin/bash

STORAGE1024_API="https://storage1024.onrender.com/api"
STORAGE1024_TOKEN=""
STORAGE1024_USERID=""

s1024_set_token() {
    STORAGE1024_TOKEN="$1"
}

s1024_set_userid() {
    STORAGE1024_USERID="$1"
}

s1024_get_gv() {
    curl -s -H "Authorization: Bearer $STORAGE1024_TOKEN" \
        "$STORAGE1024_API/projects/$STORAGE1024_USERID/gv/$1" | python3 -c "import sys, json; print(json.load(sys.stdin).get('value', ''))"
}

s1024_add_gv() {
    curl -s -X POST -H "Authorization: Bearer $STORAGE1024_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"alias\": \"$1\", \"value\": \"$2\"}" \
        "$STORAGE1024_API/projects/$STORAGE1024_USERID/gv"
}

s1024_upload_file() {
    curl -s -X POST -H "Authorization: Bearer $STORAGE1024_TOKEN" \
        -F "file=@$2" \
        -F "alias=$1" \
        "$STORAGE1024_API/projects/$STORAGE1024_USERID/upload"
}
