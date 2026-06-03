# auto_backup.ps1
# Automatic session backup script
# Run periodically to preserve agent state

param(
    [string]$DataPath = (Get-Location).Path,
    [string]$BackupPath = "$env:TEMP\agent_backups"
)

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$backupDir = Join-Path $BackupPath $timestamp

Write-Host "📦 Backing up agent data..."
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

# Backup key files
$files = @("identity.md", "memory.md", "lessons.md", "mood.json", "queue.json", "summary.md", "AGENTS.md")
foreach ($f in $files) {
    $src = Join-Path $DataPath $f
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $backupDir $f) -Force
    }
}

# Keep only last 20 backups
$existing = Get-ChildItem $BackupPath -Directory | Sort-Object Name -Descending
if ($existing.Count -gt 20) {
    $existing[$existing.Count-1] | Remove-Item -Recurse -Force
}

Write-Host "✅ Backup saved to $backupDir"
