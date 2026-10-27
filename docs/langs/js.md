# Browser / JavaScript

The easiest way to get started in any HTML page. Just drop in the CDN script,
which is served by the Storage1024 host itself.

### Installation

```html
<script src="https://storage1024.onrender.com/s1024.js"></script>
```

Self-hosting? Point the SDK at your own server before any request:

```html
<script>
  s1024.set_api_base('https://my-host.example/api');
</script>
```

### Setup

```javascript
s1024.set_userID('YOUR_PROJECT_ID');
s1024.set_token('YOUR_TOKEN');
```

### Global Variables

```javascript
const score = await s1024.get_gv('score');   // "9001"
await s1024.add_gv('score', '9001');
const all = await s1024.gv_json();           // { score: "9001" }
await s1024.delete_gv('score');
```

### Files

```javascript
const file = document.querySelector('#file-input').files[0];
const result = await s1024.upload_file('my_image', file);
console.log(result.url);                     // shareable link, no token inside

const bytes = await s1024.get_file('my_image');  // Uint8Array
const files = await s1024.list_files();
```

### Projects & tokens

```javascript
const project = await s1024.create_project('My Game');
const publicToken = await s1024.create_token('website', 'public');
await s1024.revoke_token(publicToken);
```
