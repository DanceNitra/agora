#!/bin/bash
# Build and render lip variants (MetaHuman lip makeup) with the current brows/lashes; frame 57 per variant.
cd C:/Users/Danculus/agora/agora_output/reverse/gpt-image-2-6-personas/3d
run_variant () {
  NAME=$1; TYPE=$2; COL=$3; OP=$4; RO=$5
  python -c "
import json;p='makeup/apply_cfg.json';c=json.load(open(p));mm=c['metahuman_makeup']
mm['lips.type']='$TYPE';mm['lips.color']=$COL;mm['lips.opacity']=$OP;mm['lips.roughness']=$RO
c['asset_name']='T_DepesaKF_Look_lips_$NAME';json.dump(c,open(p,'w'),indent=1)"
  cd ue/fit
  python _run.py ../../makeup/ue_apply_look.py 600 2>/dev/null | grep LOOK
  python _run.py ue_build_kf.py 1500 2>/dev/null | grep BUILT
  sed -i "s/\"step\": \"import\"/\"step\": \"export\"/; s/\"asset\": \"[^\"]*\"/\"asset\": \"T_Head_BC_patched_lips_$NAME\"/" patch_baked_cfg.json
  python _run.py ue_patch_baked.py 900 2>/dev/null | grep PATCH
  cd ../..; python makeup/patch_baked_brows.py makeup/baked_fresh.png makeup/look_p6_BC_brows.png makeup/baked_lod1_patched.png; cd ue/fit
  sed -i 's/"step": "export"/"step": "import"/' patch_baked_cfg.json
  python _run.py ue_patch_baked.py 900 2>/dev/null | tail -1
  python _run.py ue_browlayer.py 600 2>/dev/null | tail -1
  python _run.py ue_browgroom.py 900 2>/dev/null | tail -1
  python _run.py ue_browgroom_bound.py 900 2>/dev/null | tail -1
  python _run.py ue_lashgroom.py 900 2>/dev/null | tail -1
  echo "pocket-companion: lips MRQ" > C:/Users/Danculus/.claude/compute/pocket-companion.lock
  powershell -ExecutionPolicy Bypass -File eyetest_run.ps1 | tail -1
  rm -f C:/Users/Danculus/.claude/compute/pocket-companion.lock
  cd ../..; cp ue/fit/render_eyetest/0057.png makeup/review/lips_${NAME}_0057.png; echo "DONE $NAME"
}
run_variant A HOLLYWOOD "[0.28,0.035,0.045,1.0]" 0.85 0.12
run_variant B CUPID "[0.18,0.02,0.05,1.0]" 0.85 0.12
run_variant C HOLLYWOOD "[0.40,0.02,0.02,1.0]" 0.9 0.15
