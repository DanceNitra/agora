#!/bin/bash
# After the lip landmark move: auto-rig + textures, look G, build, BC patch (brows + lips), SRMF sheen, grooms, renders.
set -e
cd C:/Users/Danculus/agora/agora_output/reverse/gpt-image-2-6-personas/3d
TAG=${1:-S1}
python -c "
import json;p='makeup/apply_cfg.json';c=json.load(open(p));mm=c['metahuman_makeup'];m=json.load(open('makeup/lips_${LOOK:-G}_mh.json'))
mm['lips.type']='NATURAL';mm['lips.color']=m['color']+[1.0];mm['lips.opacity']=m.get('opacity',0.2);mm['lips.roughness']=m['roughness']
c['bc_png']='C:/Users/Danculus/agora/agora_output/reverse/gpt-image-2-6-personas/3d/makeup/look_lips_${LOOK:-G}_BC.png'
c['asset_name']='T_DepesaKF_Look_lips_$TAG';json.dump(c,open(p,'w'),indent=1)"
cd ue/fit
python _run.py ue_rigtex_kf.py 2400 2>&1 | grep -E "RIGTEX|rror" || true
python _run.py ../../makeup/ue_apply_look.py 600 2>/dev/null | grep LOOK
python _run.py ue_build_kf.py 1500 2>/dev/null | grep BUILT
sed -i "s/\"step\": \"import\"/\"step\": \"export\"/; s/\"asset\": \"[^\"]*\"/\"asset\": \"T_Head_BC_patched_lips_$TAG\"/" patch_baked_cfg.json
python _run.py ue_patch_baked.py 900 2>/dev/null | grep PATCH
cd ../..
python makeup/patch_baked_brows.py makeup/baked_fresh.png makeup/look_p6_BC_brows.png makeup/baked_lod1_patched.png
python makeup/patch_baked_lips.py makeup/baked_lod1_patched.png makeup/look_lips_${LOOK:-G}_BC.png makeup/baked_lod1_patched.png
cd ue/fit
sed -i 's/"step": "export"/"step": "import"/' patch_baked_cfg.json
python _run.py ue_patch_baked.py 900 2>/dev/null | tail -1
sed -i "s/\"step\": \"import\"/\"step\": \"export\"/; s/\"asset\": \"[^\"]*\"/\"asset\": \"T_Head_SRMF_lips_$TAG\"/" srmf_cfg.json
python _run.py ue_patch_srmf.py 600 2>/dev/null | grep PATCH
cd ../..; python makeup/patch_srmf_lips.py makeup/srmf_fresh.png makeup/srmf_patched.png ${DROP_LO:-0.22} ${DROP_UP:-0.10} ${GW:-0.24} ${GH:-0.07}; cd ue/fit
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
