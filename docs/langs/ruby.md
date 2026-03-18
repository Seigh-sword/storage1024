# Ruby

Simple Ruby client for Storage1024.

### Requirements

```ruby
require './storage1024'
```

### Usage

```ruby
s1024 = Storage1024.new
s1024.set_user_id("YOUR_PROJECT_ID")
s1024.set_token("YOUR_TOKEN")

# Read a variable
val = s1024.get_gv("score")
puts "Current Score: #{val}"

# Write a variable
s1024.add_gv("score", "9001")
```
