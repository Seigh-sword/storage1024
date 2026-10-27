# cURL

The universal HTTP client. Perfect for testing and DevOps.

Replace `https://storage1024.onrender.com` with your own host if you self-host.
Every example below works against the local dev server too (`http://localhost:8000`).

### Check the server

```bash
curl https://storage1024.onrender.com/api/health
```

### Create a project

```bash
curl -X POST https://storage1024.onrender.com/api/projects/create \
     -H 'Content-Type: application/json' \
     -d '{"name":"My Project"}'
```

### Get a Variable

```bash
curl -X GET https://storage1024.onrender.com/api/projects/YOUR_ID/gv/score \
     -H "Authorization: Bearer YOUR_TOKEN"
# {"alias":"score","value":"9001"}
```

### Set a Variable

```bash
curl -X POST https://storage1024.onrender.com/api/projects/YOUR_ID/gv \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"alias":"score","value":"9001"}'
```

### List All Variables

```bash
curl -X GET https://storage1024.onrender.com/api/projects/YOUR_ID/gv \
     -H "Authorization: Bearer YOUR_TOKEN"
# {"score":"9001"}
```

### Upload a File

```bash
curl -X POST https://storage1024.onrender.com/api/projects/YOUR_ID/upload \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -F "file=@./myfile.png" \
     -F "alias=my_image"
```

The response contains a shareable `url`. You can also download with your token:

```bash
curl -OJ https://storage1024.onrender.com/api/projects/YOUR_ID/files/my_image \
     -H "Authorization: Bearer YOUR_TOKEN"
```
