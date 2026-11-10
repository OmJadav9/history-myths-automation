# Stores the automation's secrets in GitHub Actions. Run it yourself in PowerShell:
#   powershell -ExecutionPolicy Bypass -File scripts\set_secrets.ps1
# Values are typed with hidden input and piped straight to `gh secret set`. Nothing is printed or written to disk.
$ErrorActionPreference = 'Stop'
$Repo = 'OmJadav9/history-myths-automation'
$Secrets = [ordered]@{
    'CLAUDE_CODE_OAUTH_TOKEN' = 'Claude token (run `claude setup-token` yourself first)'
    'IG_ACCESS_TOKEN'         = 'Meta system-user access token (never-expiring)'
    'IG_USER_ID'              = 'Instagram account ID (17841456970662962 for @did.you.know9104)'
}

gh auth status | Out-Null
foreach ($name in $Secrets.Keys) {
    $secure = Read-Host -AsSecureString "$name - $($Secrets[$name]) (Enter to skip)"
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr).Trim()
        if ($plain.Length -eq 0) { Write-Host "  skipped $name"; continue }
        $plain | gh secret set $name --repo $Repo
        if ($LASTEXITCODE -ne 0) { throw "gh secret set $name failed" }
        Write-Host "  stored $name"
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        $plain = $null
    }
}
Write-Host "Done. Check them at https://github.com/$Repo/settings/secrets/actions"
