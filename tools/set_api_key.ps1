# set_api_key.ps1 - Danchi types an API key into a masked window; it is stored as a Windows
# user environment variable and verified. The key is never printed, logged or shown to Claude.
#
#   powershell -ExecutionPolicy Bypass -File tools\set_api_key.ps1 deepseek
#   powershell -ExecutionPolicy Bypass -File tools\set_api_key.ps1 gemini
#
# The verification result (model names, HTTP codes, no key) goes to agora_output\api_key_check_<provider>.json.
param([Parameter(Mandatory = $true)][ValidateSet("deepseek", "gemini")][string]$Provider)

$cfg = @{
    deepseek = @{ Var = "DEEPSEEK_API_KEY"; Base = "https://api.deepseek.com/v1"; Title = "DeepSeek API key" }
    gemini   = @{ Var = "GEMINI_API_KEY"; Base = "https://generativelanguage.googleapis.com/v1beta/openai"; Title = "Google Gemini API key" }
}[$Provider]

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$form = New-Object System.Windows.Forms.Form
$form.Text = $cfg.Title
$form.Size = New-Object System.Drawing.Size(520, 190)
$form.StartPosition = "CenterScreen"
$form.TopMost = $true
$label = New-Object System.Windows.Forms.Label
$label.Text = "Vloz $($cfg.Title). Ulozi sa ako $($cfg.Var) (Windows, pouzivatel). Nikde sa nezobrazi."
$label.Location = New-Object System.Drawing.Point(12, 12)
$label.Size = New-Object System.Drawing.Size(490, 36)
$box = New-Object System.Windows.Forms.TextBox
$box.UseSystemPasswordChar = $true
$box.Location = New-Object System.Drawing.Point(12, 55)
$box.Size = New-Object System.Drawing.Size(480, 24)
$ok = New-Object System.Windows.Forms.Button
$ok.Text = "Ulozit a overit"
$ok.Location = New-Object System.Drawing.Point(12, 95)
$ok.Size = New-Object System.Drawing.Size(140, 30)
$ok.DialogResult = [System.Windows.Forms.DialogResult]::OK
$cancel = New-Object System.Windows.Forms.Button
$cancel.Text = "Zrusit"
$cancel.Location = New-Object System.Drawing.Point(162, 95)
$cancel.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
$form.Controls.AddRange(@($label, $box, $ok, $cancel))
$form.AcceptButton = $ok
$form.CancelButton = $cancel
if ($form.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK -or -not $box.Text.Trim()) { Write-Output "Zrusene, nic sa neulozilo."; exit 1 }
$key = $box.Text.Trim()
$box.Text = ""

[Environment]::SetEnvironmentVariable($cfg.Var, $key, "User")   # persistent, current user only

# Verify: list models, then probe the Responses API that Codex 0.154 requires. Cost: one tiny request.
$h = @{ Authorization = "Bearer $key" }
$out = [ordered]@{ provider = $Provider; env_var = $cfg.Var; stored = $true; checked = (Get-Date).ToString("s") }
try {
    $m = Invoke-RestMethod -Uri "$($cfg.Base)/models" -Headers $h -TimeoutSec 30
    $out.models = @($m.data | ForEach-Object { $_.id })
    $out.models_http = 200
} catch { $out.models_http = [int]$_.Exception.Response.StatusCode; $out.models_error = $_.Exception.Message }
$probeModel = if ($out.models) { $out.models[0] } else { "" }
foreach ($ep in @("responses", "chat/completions")) {
    $body = if ($ep -eq "responses") { @{ model = $probeModel; input = "Reply with the word OK." } } else { @{ model = $probeModel; messages = @(@{ role = "user"; content = "Reply with the word OK." }); max_tokens = 400 } }
    try {
        $r = Invoke-RestMethod -Uri "$($cfg.Base)/$ep" -Method Post -Headers $h -ContentType "application/json" -Body ($body | ConvertTo-Json -Depth 5) -TimeoutSec 60
        $out["${ep}_http"] = 200
    } catch { $out["${ep}_http"] = [int]$_.Exception.Response.StatusCode }
}
$key = $null
$dir = Join-Path $PSScriptRoot "..\agora_output"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$path = Join-Path $dir "api_key_check_$Provider.json"
$out | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $path
Write-Output "Ulozene do $($cfg.Var). Overenie: $path"
Write-Output ($out | ConvertTo-Json -Depth 5)
[System.Windows.Forms.MessageBox]::Show(
    "Kluc ulozeny do $($cfg.Var).`nModely: $(@($out.models) -join ', ')`nResponses API: $($out.responses_http)  (200 = Codex ide priamo)",
    "$($cfg.Title) - overenie") | Out-Null
