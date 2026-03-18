# Go SDK

Native Go client for Storage1024.

### Installation

```bash
go get github.com/Seigh-sword/storage1024-go # Example path
```

### Setup

```go
import "storage1024"

s1024 := storage1024.New()
s1024.SetUserID("YOUR_PROJECT_ID")
s1024.SetToken("YOUR_TOKEN")
```

### Global Variables

```go
// Read a variable
val, _ := s1024.GetGV("score")
fmt.Println("Score:", val)

// Write a variable
s1024.AddGV("score", "9001")
```

### File Upload

```go
s1024.UploadFile("my_image", "./photo.jpg")
```
