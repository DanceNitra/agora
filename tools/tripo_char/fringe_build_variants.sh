#!/bin/bash
# Builds the fringe proposals on top of the current hair (mh15 parameters), then previews them in Unreal.
cd "$(dirname "$0")"
GLB=C:/Users/Danculus/HairDeck/workspace/results/yuki_full/yuki_full/hair_seed8.glb
BASE="NO_RENDER=1 HUG=0.55 HUG_KEEP_EARS=0.015 THICK=0.6 TIDY=1 EYE_LOCK=0 SIDE_FROM=0.058 FILL=0.3 DRIFT=0.035 CLUMP=0.8 FRINGE_VAR=0.008 MH_HEAD=models/yuki/mh_v5/MHC_Yuki_v5_Head.fbx WAVE_AMP=0.06 WAVE_LEN=1.3 STRANDS=100000"
build() { echo "BUILD $1 $(date +%T)"; [ -s models/yuki/hair_strands_$1/yuki_hair_short_ue.abc ] || ( export $BASE $2; ./blender_headless.sh yuki_hair_strands.py -- $GLB models/yuki/hair_strands_$1 ) 2>&1 | grep -E "FRINGE|TIDY|CONCEPT|DONE|Error" ; }
build fv1 "CONCEPT_LOCK=0 LOCK_W=0.022 FRINGE_SWEEP=0.012 FRINGE_COPIES=2"
build fv2 "CONCEPT_LOCK=0 LOCK_W=0.028 FRINGE_SWEEP=0.028 FRINGE_COPIES=2"
build fv3 "CONCEPT_LOCK=300 LOCK_W=0.028 FRINGE_SWEEP=0.028 FRINGE_COPIES=2"
echo "BUILT $(date +%T)"
.venv_mp/Scripts/python.exe wait_for_gpu.py agora-tripo-char.lock 12 120
.venv_mp/Scripts/python.exe fringe_preview_ue.py reports/yuki_ue_v14/fringe_proposals A_lighter=models/yuki/hair_strands_fv1 B_swept_locks=models/yuki/hair_strands_fv2 C_locks_and_eye_lock=models/yuki/hair_strands_fv3
