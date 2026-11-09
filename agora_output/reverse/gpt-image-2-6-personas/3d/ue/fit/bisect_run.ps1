param([string]$Tag)
$out = "C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit\render_v5"
Remove-Item "$out\*" -ErrorAction SilentlyContinue
$a = '"C:\Users\Danculus\Desktop\codex\1hra\SFX\MyProject\MyProject.uproject" /Game/Maps/L_Tomb_S03_Ambience -game -LevelSequence="/Game/Companions/Lipsync/Bisect/LS_' + $Tag + '.LS_' + $Tag + '" -MoviePipelineConfig="/Game/Companions/Lipsync/MRQ_Depesa_portrait.MRQ_Depesa_portrait" -windowed -resx=540 -resy=720 -log=MRQ_' + $Tag + '.log -NoLoadingScreen -Unattended'
$p = Start-Process -FilePath "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe" -ArgumentList $a -PassThru
$t0 = Get-Date
while (((Get-Date) - $t0).TotalSeconds -lt 150) {
  Start-Sleep 5
  $n = (Get-ChildItem $out -Filter *.png -ErrorAction SilentlyContinue).Count
  if ($p.HasExited) { break }
}
$n = (Get-ChildItem $out -Filter *.png -ErrorAction SilentlyContinue).Count
$state = if ($p.HasExited) { "exited" } else { "HUNG-stopped"; Stop-Process -Id $p.Id -Force }
"$Tag frames=$n state=$state secs=" + [int]((Get-Date) - $t0).TotalSeconds
if ($n -gt 0) { New-Item -ItemType Directory -Force "$out\..\bisect_$Tag" | Out-Null; Copy-Item "$out\*.png" "$out\..\bisect_$Tag\" }
