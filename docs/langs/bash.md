# Bash

Script with cURL for automation and CI/CD.

### Requirements

```bash
source ./libraries/bash/storage1024.sh
# Override the host with: export STORAGE1024_API="http://localhost:8000/api"
```

### Usage

```bash
# Setup
s1024_set_userid "YOUR_PROJECT_ID"
s1024_set_token "YOUR_TOKEN"

# Read a variable
val=$(s1024_get_gv "score")
echo "Score: $val"

# Write a variable
s1024_add_gv "score" "9001"

# Upload a file
s1024_upload_file "my_image" "./photo.jpg"
```
