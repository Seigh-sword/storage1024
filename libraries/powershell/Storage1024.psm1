$STORAGE1024_API = "https://storage1024.onrender.com/api"
$STORAGE1024_TOKEN = ""
$STORAGE1024_USERID = ""

function Set-S1024Token {
    param($token)
    $script:STORAGE1024_TOKEN = $token
}

function Set-S1024UserID {
    param($id)
    $script:STORAGE1024_USERID = $id
}

function Get-S1024GV {
    param($name)
    $headers = @{ "Authorization" = "Bearer $STORAGE1024_TOKEN" }
    $response = Invoke-RestMethod -Uri "$STORAGE1024_API/projects/$STORAGE1024_USERID/gv/$name" -Headers $headers
    return $response.value
}

function Add-S1024GV {
    param($name, $value)
    $headers = @{ "Authorization" = "Bearer $STORAGE1024_TOKEN" }
    $body = @{ alias = $name; value = $value } | ConvertTo-Json
    $response = Invoke-RestMethod -Method Post -Uri "$STORAGE1024_API/projects/$STORAGE1024_USERID/gv" -Headers $headers -Body $body -ContentType "application/json"
    return $response
}

function Send-S1024File {
    param($alias, $path)
    $headers = @{ "Authorization" = "Bearer $STORAGE1024_TOKEN" }
    $response = Invoke-RestMethod -Method Post -Uri "$STORAGE1024_API/projects/$STORAGE1024_USERID/upload" -Headers $headers -Form @{ file = Get-Item $path; alias = $alias }
    return $response
}

Export-ModuleMember -Function Set-S1024Token, Set-S1024UserID, Get-S1024GV, Add-S1024GV, Send-S1024File
