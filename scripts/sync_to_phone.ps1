param (
    [string]$TargetIp = "100.68.31.91",
    [int]$Port = 8022,
    [string]$RemoteDir = "~/addy_space",
    [switch]$UseAdb
)

$ErrorActionPreference = "Stop"

if ($UseAdb) {
    $TargetIp = "127.0.0.1"
    Write-Host "[*] Using ADB Localhost target: $($TargetIp):$($Port)" -ForegroundColor Cyan
} else {
    Write-Host "[*] Using Tailscale Mesh target: $($TargetIp):$($Port)" -ForegroundColor Cyan
}

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Write-Host "[*] Project root: $ProjectRoot" -ForegroundColor Gray

# Define items to sync (add/modify as project expands)
$ItemsToSync = @("app", "scripts", "main.py", "requirements.txt")

foreach ($item in $ItemsToSync) {
    $localPath = Join-Path $ProjectRoot $item
    if (Test-Path $localPath) {
        Write-Host "[>] Syncing $item to $RemoteDir..." -ForegroundColor Yellow
        # In Termux single-user environment, any username (e.g. u0_a0 or termux) is accepted
        & scp.exe -P $Port -r $localPath "termux@${TargetIp}:${RemoteDir}/"
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to sync $item"
        }
    }
}

Write-Host "[+] Sync complete!" -ForegroundColor Green
