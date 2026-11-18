# Run in an Administrator PowerShell window to allow LAN devices (same Wi-Fi / subnet)
# to connect to the USeP OBE Studio server on TCP port 5000.

$RuleName = "USeP OBE Studio Port 5000 (LAN)"

if (Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue) {
    Remove-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
}

New-NetFirewallRule `
    -DisplayName $RuleName `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort 5000 `
    -Profile Private,Domain,Public `
    -Description "Allows inbound LAN/Wi-Fi traffic to USeP OBE Studio & Student Portal on port 5000."

Write-Host "Inbound TCP port 5000 is now allowed for LAN connections." -ForegroundColor Green
