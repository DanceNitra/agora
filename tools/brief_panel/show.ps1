# Opens the brief panel in a fixed-size Chrome app window and raises a Windows toast.
# Quiet hours: between 22:00 and 07:00 the toast is skipped; the window still opens on request.
param([switch]$NoToast, [switch]$WindowOnly)

$ErrorActionPreference = "Stop"
$root  = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$page  = Join-Path $PSScriptRoot "index.html"
$data  = Join-Path $root "agora_output\channels\brief.json"

if (-not (Test-Path -LiteralPath $data)) { throw "brief.json not found at $data" }
$brief = Get-Content -LiteralPath $data -Raw -Encoding UTF8 | ConvertFrom-Json
$urgent  = @($brief.items | Where-Object { $_.state -eq "URGENT" }).Count
$waiting = @($brief.items | Where-Object { $_.state -eq "WAITING" }).Count
$top     = ($brief.items | Where-Object { $_.state -eq "URGENT" } | Select-Object -First 1).title
if (-not $top) { $top = ($brief.items | Where-Object { $_.state -eq "WAITING" } | Select-Object -First 1).title }

$hour  = (Get-Date).Hour
$quiet = ($hour -ge 22 -or $hour -lt 7)

if (-not $NoToast -and -not $quiet -and ($urgent + $waiting) -gt 0) {
    # Our own frameless window, painted by us. Chrome's app mode always drew its
    # own title bar, so that window was never ours.
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    if ($py) {
        $notify = Join-Path $PSScriptRoot "notify_qt.py"
        Start-Process -FilePath $py -ArgumentList "`"$notify`"" -WindowStyle Hidden
    }
}

# -NoToast skips the toast, -WindowOnly is its alias kept for the Start Menu shortcut.
if ($true) {
    $chrome = @(
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $chrome) { throw "Chrome not found in the three standard locations" }
    $profile = Join-Path $env:LOCALAPPDATA "AgoraBriefPanel"
    $url = "file:///" + $page.Replace("\", "/")
    & $chrome "--app=$url" `
        "--user-data-dir=$profile" "--window-size=440,900" "--window-position=1460,60" `
        "--allow-file-access-from-files" "--no-first-run" "--no-default-browser-check"
}
