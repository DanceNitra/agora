#!/bin/bash
# Makeup tool test: neutral rim light, apply a look on Depesa, render closed + smile, restore the Dosvit light.
set -e
LOOK=${1:-luvpauli_doll}; TAG=${2:-$LOOK}
cd C:/Users/Danculus/agora/agora_output/reverse/gpt-image-2-6-personas/3d/ue/fit
# neutral rim [235,238,255] like the before_neutral frame (round 8 ran with the magenta Dosvit rim by mistake)
python -c "import json;c=json.load(open('light_cfg_dosvit_backup.json'));c['rig'][1][1]=[235,238,255];json.dump(c,open('light_cfg.json','w'))"
trap 'cp light_cfg_dosvit_backup.json light_cfg.json; python _run.py ue_light.py 300 2>&1 | grep -E "LIGHTSET|rror"; echo LIGHT_RESTORED' EXIT
python _run.py ue_light.py 300 2>&1 | grep -E "LIGHTSET|rror"
# reload: the editor keeps the module it imported first; an old core.py never painted the body (11-09)
printf 'import json, importlib\nimport agora_makeup_ue.core as c\nimportlib.reload(c)\nprint("MAKEUP", json.dumps(c.apply("%s", folder="/Game/Companions/MetaHuman/BuiltKF/MH_DepesaKF/Face")))\nimport os\nprint("MAKEUP body_painted", os.path.exists(os.path.join(c._saved("MH_DepesaKF"), "look_body_BC.png")))\n' "$LOOK" > _q27.py
python _run.py _q27.py 900 2>&1 | grep -E "MAKEUP|rror"
echo "pocket-companion: makeup tool MRQ" > C:/Users/Danculus/.claude/compute/pocket-companion.lock
powershell -ExecutionPolicy Bypass -File eyetest_run.ps1 | tail -1
powershell -ExecutionPolicy Bypass -File lipclosed_run.ps1 | tail -1
rm -f C:/Users/Danculus/.claude/compute/pocket-companion.lock
cp render_eyetest/0057.png ../../../../makeup_tool/renders/${TAG}_0057.png
cp render_lipclosed/0000.png ../../../../makeup_tool/renders/${TAG}_0000.png
echo "DONE $TAG"
