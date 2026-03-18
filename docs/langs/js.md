# Browser / JavaScript

The easiest way to get started in any HTML page. Just drop in the CDN script.

### Installation

Add the following tag to your `<head>`:

```html
<script src="https://storage1024.onrender.com/s1024.js"></script>
```

### Setup

```html
<script>
  s1024.set_userID('YOUR_PROJECT_ID');
  s1024.set_token('YOUR_TOKEN');
</script>
```

### Global Variables

```javascript
// Read a variable
const score = await s1024.get_gv('score');

// Write a variable
await s1024.add_gv('score', '9001');

// Get all variables as an object
const all = await s1024.gv_json();
console.log(all); // { score: "9001", ... }
```

### File Upload

```javascript
const fileInput = document.querySelector('#file-input');
const file = fileInput.files[0];
const result = await s1024.upload_file('my_image', file);
console.log(`Uploaded: ${result.alias}`);
```
