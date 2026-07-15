#!/usr/bin/env bash
# Unattended overnight supervisor for the Hubbard DMRG grid.
# Self-healing: keeps a parallel driver running until all 64 cells are done
# (resumable — finished cells skipped, crashed/missing cells retried), with a
# 10-min heartbeat and a STALL guard (give up only if 2h pass with no new cell
# AND nothing is running — so a slow 2-3h L=320 cell never false-triggers).
set -u
cd "$(dirname "$0")"
STATUS=_overnight_status.txt
STALL_SEC=$((2*3600))
HEARTBEAT=600

done_count() {
python - <<'PY'
import os,json
n=0
if os.path.isdir('cells'):
    for fn in os.listdir('cells'):
        if fn.endswith('.json'):
            try:
                j=json.load(open(os.path.join('cells',fn))); k=list(j)[0]
                if j[k].get('sector_ok'): n+=1
            except Exception: pass
print(n)
PY
}

proc_count() {  # $1 = substring to match in the python command line
    powershell.exe -NoProfile -Command \
      "(Get-CimInstance Win32_Process -Filter \"name like '%python%'\" | Where-Object { \$_.CommandLine -like '*$1*' } | Measure-Object).Count" \
      2>/dev/null | tr -d '[:space:]'
}

launch_driver() {
    nohup python -u run_parallel.py --workers 6 --threads 2 >> _driver.log 2>&1 &
}

finalize() {  # $1 = marker file
    python -u dmrg_hubbard.py --analyze-only > _final_analysis.txt 2>&1
    : > "$1"
    echo "FINALIZED -> $1 $(date)" >> "$STATUS"
}

echo "supervisor start $(date)" > "$STATUS"
last_count=$(done_count)
last_prog=$(date +%s)
launch_driver
echo "$(date +%H:%M:%S) launched driver, done=$last_count/64" >> "$STATUS"

while true; do
    sleep "$HEARTBEAT"
    n=$(done_count); now=$(date +%s)
    w=$(proc_count dmrg_hubbard); d=$(proc_count run_parallel)
    w=${w:-0}; d=${d:-0}
    echo "$(date +%H:%M:%S) done=$n/64 workers=$w driver=$d" >> "$STATUS"

    if [ "$n" -ge 64 ]; then
        echo "ALL 64 DONE $(date)" >> "$STATUS"
        finalize _OVERNIGHT_DONE
        break
    fi
    if [ "$n" -gt "$last_count" ]; then last_count=$n; last_prog=$now; fi

    # driver + workers all gone but work remains => relaunch (self-heal)
    if [ "$d" = "0" ] && [ "$w" = "0" ]; then
        echo "  driver+workers gone, relaunch $(date)" >> "$STATUS"
        launch_driver
        sleep 5
        continue
    fi

    # stall guard: 2h without a new cell AND nothing computing => wedged
    if [ $((now-last_prog)) -ge $STALL_SEC ] && [ "$w" = "0" ]; then
        echo "STALLED: 2h no progress + no workers, done=$n/64 $(date)" >> "$STATUS"
        finalize _OVERNIGHT_STALLED
        break
    fi
done
