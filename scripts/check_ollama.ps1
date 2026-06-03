# check_ollama.ps1
# Verify Ollama is running and responsive

$hostname = "http://localhost:11434"

try {
    $resp = Invoke-RestMethod -Uri "$hostname/api/tags" -Method Get -ErrorAction Stop
    $models = $resp.models
    Write-Host "✅ Ollama is running. Models available:"
    foreach ($m in $models) {
        Write-Host "   - $($m.name)"
    }
} catch {
    Write-Host "❌ Ollama is NOT running. Start it with: ollama serve"
    exit 1
}
