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

# Dungeon: the CANONICAL manager is the brain's in-process watchdog (watch_dungeon_forever), which
# HTTP-checks :5174 and relaunches a BARE mcp_server.py after a couple of misses. So the canonical
# setup is brain-watchdog + exactly ONE bare mcp_server.py and ZERO supervisors. A dungeon_supervisor
# here would FIGHT the brain watchdog — its kill_stray_dungeons() kills the watchdog's dungeon, and
# each relaunches what the other kills => restart churn that starves the Scout scan. So this script
# (a) always kills any stray supervisor, and (b) launches a bare mcp_server only if none is up.
$procs | Where-Object { $_.CommandLine -like '*dungeon_supervisor.py*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

$dungeonUp = $procs | Where-Object { $_.CommandLine -like '*mcp_server.py*' -and $_.CommandLine -notlike '*-c*' }
if (-not $dungeonUp) {
    Remove-Item Env:\DUNGEON_AUTOPUSH -ErrorAction SilentlyContinue
    $env:PYTHONUNBUFFERED = '1'
    Start-Process -WindowStyle Hidden -WorkingDirectory "C:\Users\Danculus\agora\agora-game-server" `
        -RedirectStandardOutput "C:\Users\Danculus\agora\agora-game-server\_dungeon.log" `
        -RedirectStandardError "C:\Users\Danculus\agora\agora-game-server\_dungeon.err" `
        python -ArgumentList "-u", "mcp_server.py"
}
