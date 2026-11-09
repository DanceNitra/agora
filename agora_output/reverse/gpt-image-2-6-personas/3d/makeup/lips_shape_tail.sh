#!/bin/bash
set -e
cd C:/Users/Danculus/agora/agora_output/reverse/gpt-image-2-6-personas/3d/ue/fit
TAG=${1:-S1}
sed -i "s/\"step\": \"import\"/\"step\": \"export\"/; s/\"asset\": \"[^\"]*\"/\"asset\": \"T_Head_SRMF_lips_$TAG\"/" srmf_cfg.json
python _run.py ue_patch_srmf.py 600 2>/dev/null | grep PATCH
cd ../..; python makeup/patch_srmf_lips.py makeup/srmf_fresh.png makeup/srmf_patched.png 0.22 0.10; cd ue/fit
sed -i 's/"step": "export"/"step": "import"/' srmf_cfg.json
python _run.py ue_patch_srmf.py 600 2>/dev/null | grep PATCH
python _run.py ue_browlayer.py 600 2>/dev/null | tail -1
python _run.py ue_browgroom.py 900 2>/dev/null | tail -1
python _run.py ue_browgroom_bound.py 900 2>/dev/null | tail -1
python _run.py ue_lashgroom.py 900 2>/dev/null | tail -1
python _run.py ue_mrqpreset_lipclosed.py 300 2>/dev/null | grep PRESET
echo "pocket-companion: lips shape MRQ" > C:/Users/Danculus/.claude/compute/pocket-companion.lock
powershell -ExecutionPolicy Bypass -File eyetest_run.ps1 | tail -1
powershell -ExecutionPolicy Bypass -File lipclosed_run.ps1 | tail -1
rm -f C:/Users/Danculus/.claude/compute/pocket-companion.lock
cd ../..
cp ue/fit/render_eyetest/0057.png makeup/review/lips_${TAG}_0057.png
cp ue/fit/render_lipclosed/0000.png makeup/review/lips_${TAG}_0000.png
echo "DONE $TAG"
