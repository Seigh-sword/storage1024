# cURL

The universal HTTP client. Perfect for testing and DevOps.

### Get a Variable

```bash
curl -X GET https://storage1024.onrender.com/api/projects/YOUR_ID/gv/score \
     -H "Authorization: Bearer YOUR_TOKEN"
```

### Set a Variable

```bash
curl -X POST https://storage1024.onrender.com/api/projects/YOUR_ID/gv \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"alias":"score","value":"9001"}'
```

### Upload a File

```bash
curl -X POST https://storage1024.onrender.com/api/projects/YOUR_ID/upload \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -F "file=@./myfile.png" \
     -F "alias=my_image"
```

### List All Variables

```bash
curl -X GET https://storage1024.onrender.com/api/projects/YOUR_ID/gv \
     -H "Authorization: Bearer YOUR_TOKEN"
```
