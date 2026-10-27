# Node.js

The same UMD client works in Node.js 18+ (which provides `fetch` and
`FormData` natively).

### Installation

```bash
# From this repository (the package is not published to npm yet):
npm install ./libraries/s1024
```

### Setup

```javascript
const s1024 = require('storage1024');

s1024.set_userID('YOUR_PROJECT_ID');
s1024.set_token('YOUR_TOKEN');
// s1024.set_api_base('http://localhost:8000/api');
```

### Usage

```javascript
const val = await s1024.get_gv('my_key');
await s1024.add_gv('my_key', 'hello world');
const all = await s1024.gv_json();

const fs = require('fs');
const { Blob } = require('buffer');
const blob = new Blob([fs.readFileSync('./data.json')]);
await s1024.upload_file('data_file', blob, 'data.json');
```
