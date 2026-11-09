#!/bin/bash
# Build and render each brow groom in $@; frames go to render_brow_<name>.
cd C:/Users/Danculus/agora/agora_output/reverse/gpt-image-2-6-personas/3d/ue/fit
for B in "$@"; do
  sed -i "s#Eyebrows/WI_Eyebrows_[A-Za-z_]*\"#Eyebrows/WI_Eyebrows_${B}\"#" ue_build_kf.py
  python _run.py ue_build_kf.py 1500 2>/dev/null | grep BUILT
  python _run.py ue_lashes.py 300 2>/dev/null
  echo "pocket-companion: brow test MRQ" > C:/Users/Danculus/.claude/compute/pocket-companion.lock
  powershell -ExecutionPolicy Bypass -File eyetest_run.ps1 | tail -1
  rm -f C:/Users/Danculus/.claude/compute/pocket-companion.lock
  rm -rf render_brow_$B; cp -r render_eyetest render_brow_$B
  echo "DONE $B"
done
