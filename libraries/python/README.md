# Storage1024 Python Client

Native Python client for Storage1024.

## Installation

```bash
pip install storage1024
```

## Usage

```python
from storage1024 import Storage1024

s1024 = Storage1024()
s1024.set_userid("YOUR_ID")
s1024.set_token("YOUR_TOKEN")

# Get a global variable
val = s1024.get_gv("my_var")
print(val)
```
