# Java

Native Java library for cloud storage and variables.

### Installation

Add `Storage1024.java` to your project source.

### Usage

```java
Storage1024 s1024 = new Storage1024();
s1024.setUserID("YOUR_PROJECT_ID");
s1024.setToken("YOUR_TOKEN");

// Read a variable (Asynchronous)
s1024.getGV("score").thenAccept(val -> {
    System.out.println("Score: " + val);
});

// Write a variable (Synchronous wait example)
s1024.addGV("score", "9001").get(); 
```
