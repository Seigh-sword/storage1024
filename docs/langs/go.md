# Go SDK

Native Go client. The library is a single file in this repository; copy it into
your module (or publish it under your own module path) rather than using `go get`.

### Installation

```bash
cp libraries/go/storage1024.go ./storage1024/
```

### Setup

```go
import "your/module/storage1024"

s1024 := storage1024.New()
s1024.SetUserID("YOUR_PROJECT_ID")
s1024.SetToken("YOUR_TOKEN")
// s1024.APIBase = "http://localhost:8000/api"
```

### Global Variables

```go
val, err := s1024.GetGV("score")
err = s1024.AddGV("score", "9001")
```

### File Upload

```go
err := s1024.UploadFile("my_image", "./photo.jpg")
```

`UploadFile` now uses `multipart.Writer.FormDataContentType()` and checks the
HTTP status, so errors are reported instead of silently ignored.
