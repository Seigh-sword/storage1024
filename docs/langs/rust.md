# Rust SDK

Native Rust client using `reqwest::blocking`. The crate lives in this
repository; reference it by path until it is published.

### Installation

```toml
[dependencies]
storage1024 = { path = "libraries/rust" }
```

### Setup

```rust
use storage1024::Storage1024;

let mut s1024 = Storage1024::new();
s1024.set_user_id("YOUR_PROJECT_ID");
s1024.set_token("YOUR_TOKEN");
// s1024.set_api_base("http://localhost:8000/api");
```

### Global Variables

```rust
let val = s1024.get_gv("score")?;
s1024.add_gv("score", "9001")?;
```

### File Upload

```rust
s1024.upload_file("my_image", "./photo.jpg")?;
```
