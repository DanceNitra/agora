# Agora autostart — brings up the brain (:8000) and the dungeon (:5174) if not running.
# Outer watchdog layer: register for logon so the organism survives a machine reboot:
#   schtasks /Create /TN "AgoraAutostart" /SC ONLOGON /F /TR "powershell -WindowStyle Hidden -ExecutionPolicy Bypass -File C:\Users\Danculus\agora\tools\start_agora.ps1"

$ErrorActionPreference = "SilentlyContinue"
$procs = Get-CimInstance Win32_Process -Filter "name like '%python%'"

$brainUp = $procs | Where-Object { $_.CommandLine -like '*uvicorn*agora.main*' -or ($_.CommandLine -like '*uvicorn*' -and $_.CommandLine -like '*agora.main:app*') }
if (-not $brainUp) {
    $env:PYTHONPATH = '.'
    $env:PYTHONUNBUFFERED = '1'
    Start-Process -WindowStyle Hidden -WorkingDirectory "C:\Users\Danculus\agora\server" `
        -RedirectStandardError "C:\Users\Danculus\agora\server\_brain.err" `
        python -ArgumentList "-m", "uvicorn", "agora.main:app", "--host", "127.0.0.1", "--port", "8000"
}

# Dungeon runs UNDER the supervisor (dungeon_supervisor.py), which owns mcp_server.py's lifecycle
# and restarts it on a wedged life-loop or a crash (heartbeat watchdog). Launch the SUPERVISOR, not
# mcp_server directly. Re-running this script is safe: if the supervisor is already up, do nothing.
# Because this script (re-run on logon, or on a periodic schtask) revives the supervisor itself, the
# two layers cover each other: supervisor heals the dungeon, this script heals the supervisor.
$supUp = $procs | Where-Object { $_.CommandLine -like '*dungeon_supervisor.py*' }
if (-not $supUp) {
    Remove-Item Env:\DUNGEON_AUTOPUSH -ErrorAction SilentlyContinue
    $env:PYTHONUNBUFFERED = '1'
    # clear any stray bare dungeon so the supervisor starts from a clean slate
    Get-CimInstance Win32_Process -Filter "name like '%python%'" |
        Where-Object { $_.CommandLine -like '*mcp_server.py*' -and $_.CommandLine -notlike '*-c*' } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Process -WindowStyle Hidden -WorkingDirectory "C:\Users\Danculus\agora\agora-game-server" `
        python -ArgumentList "-u", "dungeon_supervisor.py"
}
