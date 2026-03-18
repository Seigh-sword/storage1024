# Node.js

The same API you already know, optimized for server-side use.

### Installation

```bash
npm install storage1024
```

### Setup

```javascript
const s1024 = require('storage1024');

s1024.set_userID('YOUR_PROJECT_ID');
s1024.set_token('YOUR_TOKEN');
```

### Usage

```javascript
// Get a variable
const val = await s1024.get_gv('my_key');

// Set a variable
await s1024.add_gv('my_key', 'hello world');

// Upload a file (pass a Buffer or ReadStream)
const fs = require('fs');
await s1024.upload_file('data_file', fs.createReadStream('./data.json'));
```
