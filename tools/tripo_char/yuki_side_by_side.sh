#!/bin/sh
# Side-by-side check video: left the Unreal MetaHuman render of the same song span, right the path-T Tripo face.
#   ./yuki_side_by_side.sh <frames_dir with 00000.png...> <unreal clip.mp4> <out.mp4>
F="$1"; U="$2"; O="$3"
ffmpeg -hide_banner -loglevel error -y -framerate 30 -i "$F/%05d.png" -i "$U" \
  -filter_complex "[1:v]crop=600:600:240:420,scale=900:900[l];[0:v]scale=900:900[r];[l][r]hstack=inputs=2[v]" \
  -map "[v]" -map 1:a -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -shortest "$O"
