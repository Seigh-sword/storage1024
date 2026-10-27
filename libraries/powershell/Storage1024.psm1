# Storage1024 PowerShell module (PowerShell 6.1+ for multipart -Form).
$script:STORAGE1024_API = if ($env:STORAGE1024_API) { $env:STORAGE1024_API } else { "https://storage1024.onrender.com/api" }
$script:STORAGE1024_TOKEN = ""
$script:STORAGE1024_USERID = ""

function Set-S1024ApiBase {
    param([Parameter(Mandatory = $true)][string]$Url)
    $script:STORAGE1024_API = $Url.TrimEnd('/')
}

function Set-S1024Token {
    param([Parameter(Mandatory = $true)][string]$Token)
    $script:STORAGE1024_TOKEN = $Token
}

function Set-S1024UserID {
    param([Parameter(Mandatory = $true)][string]$Id)
    $script:STORAGE1024_USERID = $Id
}

function Get-S1024Url {
    param([string]$Suffix = "")
    $id = [uri]::EscapeDataString($script:STORAGE1024_USERID)
    return "$script:STORAGE1024_API/projects/$id$Suffix"
}

function Get-S1024Headers {
    return @{ "Authorization" = "Bearer $script:STORAGE1024_TOKEN" }
}

function Get-S1024GV {
    param([Parameter(Mandatory = $true)][string]$Name)
    $url = Get-S1024Url -Suffix ("/gv/" + [uri]::EscapeDataString($Name))
    $response = Invoke-RestMethod -Uri $url -Headers (Get-S1024Headers)
    return $response.value
}

function Get-S1024AllGV {
    $response = Invoke-RestMethod -Uri (Get-S1024Url -Suffix "/gv") -Headers (Get-S1024Headers)
    return $response
}

function Add-S1024GV {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Value
    )
    $body = @{ alias = $Name; value = $Value } | ConvertTo-Json
    return Invoke-RestMethod -Method Post -Uri (Get-S1024Url -Suffix "/gv") `
        -Headers (Get-S1024Headers) -Body $body -ContentType "application/json"
}

function Remove-S1024GV {
    param([Parameter(Mandatory = $true)][string]$Name)
    $url = Get-S1024Url -Suffix ("/gv/" + [uri]::EscapeDataString($Name))
    return Invoke-RestMethod -Method Delete -Uri $url -Headers (Get-S1024Headers)
}

function Send-S1024File {
    param(
        [Parameter(Mandatory = $true)][string]$Alias,
        [Parameter(Mandatory = $true)][string]$Path
    )
    if (-not (Test-Path -LiteralPath $Path)) { throw "File not found: $Path" }
    return Invoke-RestMethod -Method Post -Uri (Get-S1024Url -Suffix "/upload") `
        -Headers (Get-S1024Headers) -Form @{ file = Get-Item -LiteralPath $Path; alias = $Alias }
}

function Get-S1024File {
    param(
        [Parameter(Mandatory = $true)][string]$Alias,
        [Parameter(Mandatory = $true)][string]$Output
    )
    $url = Get-S1024Url -Suffix ("/files/" + [uri]::EscapeDataString($Alias))
    Invoke-WebRequest -Uri $url -Headers (Get-S1024Headers) -OutFile $Output
}

Export-ModuleMember -Function Set-S1024ApiBase, Set-S1024Token, Set-S1024UserID, `
    Get-S1024GV, Get-S1024AllGV, Add-S1024GV, Remove-S1024GV, Send-S1024File, Get-S1024File
