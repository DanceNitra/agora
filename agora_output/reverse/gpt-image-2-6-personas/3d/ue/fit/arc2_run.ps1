$out = "C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\render_v5"
Remove-Item "$out\*" -ErrorAction SilentlyContinue
$a = '"C:\Users\Danculus\Desktop\codex\1hra\SFX\MyProject\MyProject.uproject" /Game/Maps/L_Tomb_S03_Ambience -game -LevelSequence="/Game/Companions/Lipsync/LS_KF_Depesa_lajk_confidence_v3.LS_KF_Depesa_lajk_confidence_v3" -MoviePipelineConfig="/Game/Companions/Lipsync/MRQ_Depesa_portrait.MRQ_Depesa_portrait" -windowed -resx=540 -resy=720 -log=MRQ_arc2.log -NoLoadingScreen -Unattended'
$p = Start-Process -FilePath "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe" -ArgumentList $a -PassThru
$t0 = Get-Date; $last = -1; $lastT = Get-Date
while (-not $p.HasExited -and ((Get-Date) - $t0).TotalSeconds -lt 1200) {
  Start-Sleep 10
  $n = (Get-ChildItem $out -Filter *.png -ErrorAction SilentlyContinue).Count
  if ($n -ne $last) { $last = $n; $lastT = Get-Date; "t=" + [int]((Get-Date) - $t0).TotalSeconds + " frames=$n" }
  if ($n -gt 0 -and ((Get-Date) - $lastT).TotalSeconds -gt 180) { "STALLED"; Stop-Process -Id $p.Id -Force; break }
}
"END frames=" + (Get-ChildItem $out -Filter *.png).Count + " exited=" + $p.HasExited
