# Rust SDK

Native Rust client for Storage1024 using `reqwest`.

### Installation

Add `storage1024` to your `Cargo.toml`:

```toml
[dependencies]
storage1024 = "0.1.0"
```

### Setup

```rust
use storage1024::Storage1024;

let mut s1024 = Storage1024::new();
s1024.set_user_id("YOUR_PROJECT_ID");
s1024.set_token("YOUR_TOKEN");
```

### Global Variables

```rust
// Read a variable
let val = s1024.get_gv("score")?;
println!("Score: {}", val);

// Write a variable
s1024.add_gv("score", "9001")?;
```

### File Upload

```rust
s1024.upload_file("my_image", "./photo.jpg")?;
```
