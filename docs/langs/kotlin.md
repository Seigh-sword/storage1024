# Kotlin SDK

Native Kotlin client for JVM and Android projects.

### Setup

```kotlin
import com.storage1024.Storage1024

val s1024 = Storage1024()
s1024.setUserID("YOUR_PROJECT_ID")
s1024.setToken("YOUR_TOKEN")
```

### Global Variables

```kotlin
// Read a variable (Async)
s1024.getGV("score").thenAccept { val ->
    println("Score: $val")
}

// Write a variable
s1024.addGV("score", "9001")
```
