#!/bin/bash
# Variants D-F: lip look painted in the BaseColor (lip_paint.py) + light MetaHuman lip layer for roughness only.
cd C:/Users/Danculus/agora/agora_output/reverse/gpt-image-2-6-personas/3d
OUT=C:/Users/Danculus/AppData/Local/Temp/claude/8d2d35ef4a747728/83118a43-1d36-4a52-a91d-799c725bc0b0/tasks/bh3czfwtu.output
run_variant () {
  NAME=$1
  python -c "
import json;p='makeup/apply_cfg.json';c=json.load(open(p));mm=c['metahuman_makeup'];m=json.load(open('makeup/lips_${NAME}_mh.json'))
mm['lips.type']='NATURAL';mm['lips.color']=m['color']+[1.0];mm['lips.opacity']=m.get('opacity',0.2);mm['lips.roughness']=m['roughness']
c['bc_png']='C:/Users/Danculus/agora/agora_output/reverse/gpt-image-2-6-personas/3d/makeup/look_lips_${NAME}_BC.png'
c['asset_name']='T_DepesaKF_Look_lips2_$NAME';json.dump(c,open(p,'w'),indent=1)"
  cd ue/fit
  python _run.py ../../makeup/ue_apply_look.py 600 2>/dev/null | grep LOOK
  python _run.py ue_build_kf.py 1500 2>/dev/null | grep BUILT
  sed -i "s/\"step\": \"import\"/\"step\": \"export\"/; s/\"asset\": \"[^\"]*\"/\"asset\": \"T_Head_BC_patched_lips2_$NAME\"/" patch_baked_cfg.json
  python _run.py ue_patch_baked.py 900 2>/dev/null | grep PATCH
  cd ../..; python makeup/patch_baked_brows.py makeup/baked_fresh.png makeup/look_p6_BC_brows.png makeup/baked_lod1_patched.png; python makeup/patch_baked_lips.py makeup/baked_lod1_patched.png makeup/look_lips_${NAME}_BC.png makeup/baked_lod1_patched.png; cd ue/fit
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
run_variant ${1:-G}
