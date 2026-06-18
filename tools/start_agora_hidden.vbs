' Windowless launcher for the Agora keepalive — runs start_agora.ps1 with NO visible window.
' Window style 0 = hidden; this stops the scheduled task from flashing a console on screen.
CreateObject("WScript.Shell").Run _
  "powershell.exe -NoProfile -ExecutionPolicy Bypass -File ""C:\Users\Danculus\agora\tools\start_agora.ps1""", _
  0, False
