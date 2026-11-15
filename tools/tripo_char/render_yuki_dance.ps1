# Renders one Yuki dance sequence in a separate -game process (the pattern of dance/ue/render_dance.ps1, on UE 5.9).
# yuki_game_hook.py runs inside that process and makes the hair collide with the whole body; it leaves
# reports/yuki_dance/hook_ran.txt as proof.
param([string]$tag = "Savage_t2", [int]$last = 0)
$out = "C:\Users\Danculus\agora\tools\tripo_char\reports\yuki_dance\render_$tag"
New-Item -ItemType Directory -Force $out | Out-Null
Get-ChildItem $out -Filter *.png -ErrorAction SilentlyContinue | Remove-Item
$a = '"C:\Users\Danculus\Desktop\codex\1hra\SFX\MyProject\MyProject.uproject" /Game/AgoraChar/Tripo/Yuki/L_Yuki_Preview -game -LevelSequence="/Game/AgoraChar/Tripo/Yuki/Anim/LS_Yuki_Dance_' + $tag + '.LS_Yuki_Dance_' + $tag + '" -MoviePipelineConfig="/Game/AgoraChar/Tripo/Yuki/Anim/MRQ_Yuki_Dance_' + $tag + '.MRQ_Yuki_Dance_' + $tag + '" -windowed -resx=540 -resy=960 -log=MRQ_Yuki_' + $tag + '.log -NoLoadingScreen -Unattended -ExecCmds="py C:/Users/Danculus/agora/tools/tripo_char/yuki_game_hook.py"'
$p = Start-Process -FilePath "C:\Program Files\Epic Games\UE_5.9\Engine\Binaries\Win64\UnrealEditor.exe" -ArgumentList $a -PassThru
"RENDER PID " + $p.Id
$t0 = Get-Date; $lastN = -1; $lastT = Get-Date
while (-not $p.HasExited -and ((Get-Date) - $t0).TotalSeconds -lt 3000) {
  Start-Sleep 15
  $n = (Get-ChildItem $out -Filter *.png -ErrorAction SilentlyContinue).Count
  if ($n -ne $lastN) { $lastN = $n; $lastT = Get-Date; "t=" + [int]((Get-Date) - $t0).TotalSeconds + " frames=$n" }
  if ($last -gt 0 -and $n -ge $last) { "REACHED $last"; Stop-Process -Id $p.Id -Force; break }
  if ($n -gt 0 -and ((Get-Date) - $lastT).TotalSeconds -gt 240) { "STALLED"; Stop-Process -Id $p.Id -Force; break }
}
if (-not $p.HasExited) { "TIMEOUT"; Stop-Process -Id $p.Id -Force }
"END frames=" + (Get-ChildItem $out -Filter *.png).Count
