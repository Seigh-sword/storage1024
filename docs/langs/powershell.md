# PowerShell

Native Windows scripting with a clean module.

### Requirements

```powershell
Import-Module ./Storage1024.psm1
```

### Usage

```powershell
# Setup
Set-S1024UserID "YOUR_PROJECT_ID"
Set-S1024Token "YOUR_TOKEN"

# Read a variable
$val = Get-S1024GV -name "score"
Write-Output "Score: $val"

# Write a variable
Add-S1024GV -name "score" -value "9001"

# Upload a file
Send-S1024File -alias "my_image" -path "./photo.jpg"
```
