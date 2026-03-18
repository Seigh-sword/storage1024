# Python SDK

Native Python library with a full synchronous API. No async required.

### Installation

Run the following command in your terminal:

```bash
pip install storage1024
```

### Setup

```python
from storage1024 import Storage1024

# Initialize the client
s1024 = Storage1024()
s1024.set_userid('YOUR_PROJECT_ID')
s1024.set_token('YOUR_TOKEN')
```

### Global Variables

```python
# Read a variable
score = s1024.get_gv('score')
print(f"Current score: {score}")

# Write a variable
s1024.add_gv('score', '9001')

# Get all variables as a dictionary
all_vars = s1024.gv_json()
print(all_vars) # {'score': '9001', ...}
```

### File Upload

```python
# Upload any local file
result = s1024.upload_file('my_data', './data.json')
print(f"File uploaded to: {result['url']}")
```

### Project Management

```python
# Create a new project programmatically
project = s1024.create_project('My New Project')
print(f"New Project ID: {project['project_id']}")
```
