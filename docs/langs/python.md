# Python SDK

Native Python client with a full synchronous API. No async required.

### Installation

```bash
pip install requests
# Copy libraries/python/storage1024 into your project, or build the wheel:
pip install ./libraries/python
```

> `pip install storage1024` only works once the package has been published to
> PyPI; until then install from this repository.

### Setup

```python
from storage1024 import Storage1024

s1024 = Storage1024()                      # defaults to the public host
# s1024 = Storage1024("http://localhost:8000/api")  # self-hosted
s1024.set_userid('YOUR_PROJECT_ID')
s1024.set_token('YOUR_TOKEN')
```

`set_userID()` is also accepted as an alias.

### Global Variables

```python
score = s1024.get_gv('score')       # -> "9001"
s1024.add_gv('score', '9001')
all_vars = s1024.gv_json()          # -> {'score': '9001'}
s1024.delete_gv('score')
```

### Files

```python
result = s1024.upload_file('my_data', './data.json')
print(result['url'])                # stable public link

data = s1024.get_file('my_data')    # raw bytes
s1024.save_file('my_data', './copy.json')
files = s1024.list_files()          # {'my_data': {...}}
```

### Project Management

```python
project = s1024.create_project('My New Project')
print(f"New Project ID: {project['project_id']}")

token = s1024.create_token('website', 'public')
s1024.revoke_token(token)
```
