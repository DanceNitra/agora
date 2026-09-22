# Registers the brief panel with Windows so its toasts are delivered.
# Windows drops a toast whose AppUserModelID it does not know, which is why the
# first attempt showed nothing. Two things make it known:
#   1. HKCU\Software\Classes\AppUserModelId\<id>  with a display name and icon.
#   2. A Start Menu shortcut carrying the same id in property 5 of the link.
# Both live under the current user. Nothing is written outside HKCU and the user's
# own Start Menu folder.
$ErrorActionPreference = "Stop"
$AppId = "Agora.BriefPanel"
$Name  = "Agora Brief"

$key = "HKCU:\Software\Classes\AppUserModelId\$AppId"
New-Item -Path $key -Force | Out-Null
New-ItemProperty -Path $key -Name "DisplayName" -Value $Name -PropertyType String -Force | Out-Null
New-ItemProperty -Path $key -Name "ShowInSettings" -Value 1 -PropertyType DWord -Force | Out-Null

$startMenu = [Environment]::GetFolderPath("Programs")
$lnkPath   = Join-Path $startMenu "$Name.lnk"
$target    = Join-Path $PSScriptRoot "show.ps1"

$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut($lnkPath)
$lnk.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$lnk.Arguments  = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$target`" -WindowOnly"
$lnk.WorkingDirectory = $PSScriptRoot
$lnk.Description = "Otvorí panel s briefom pre Buildera"
$lnk.Save()

# Stamp the AppUserModelID onto the shortcut (property key {9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3},5).
$code = @'
using System;
using System.Runtime.InteropServices;
public static class Lnk {
  [ComImport, Guid("00021401-0000-0000-C000-000000000046")] class ShellLink { }
  [ComImport, Guid("0000010b-0000-0000-C000-000000000046"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface IPersistFile { void GetClassID(out Guid c); [PreserveSig] int IsDirty();
    void Load([MarshalAs(UnmanagedType.LPWStr)] string f, int m);
    void Save([MarshalAs(UnmanagedType.LPWStr)] string f, [MarshalAs(UnmanagedType.Bool)] bool r);
    void SaveCompleted([MarshalAs(UnmanagedType.LPWStr)] string f);
    void GetCurFile([MarshalAs(UnmanagedType.LPWStr)] out string f); }
  [ComImport, Guid("886d8eeb-8cf2-4446-8d02-cdba1dbdcf99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface IPropertyStore { void GetCount(out uint c); void GetAt(uint i, out PropertyKey k);
    void GetValue(ref PropertyKey k, out PropVariant v);
    void SetValue(ref PropertyKey k, ref PropVariant v); void Commit(); }
  [StructLayout(LayoutKind.Sequential)] struct PropertyKey { public Guid fmtid; public uint pid;
    public PropertyKey(Guid g, uint p) { fmtid = g; pid = p; } }
  [StructLayout(LayoutKind.Explicit)] struct PropVariant {
    [FieldOffset(0)] public ushort vt; [FieldOffset(8)] public IntPtr p; }
  [DllImport("ole32.dll")] static extern int PropVariantClear(ref PropVariant pv);
  public static void SetAppId(string lnkPath, string appId) {
    var link = new ShellLink();
    ((IPersistFile)link).Load(lnkPath, 2);
    var store = (IPropertyStore)link;
    var key = new PropertyKey(new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), 5);
    var pv = new PropVariant { vt = 31, p = Marshal.StringToCoTaskMemUni(appId) };
    store.SetValue(ref key, ref pv);
    store.Commit();
    ((IPersistFile)link).Save(lnkPath, true);
    PropVariantClear(ref pv);
  }
}
'@
Add-Type -TypeDefinition $code -Language CSharp
[Lnk]::SetAppId($lnkPath, $AppId)

Write-Output "registered: $AppId"
Write-Output "shortcut:   $lnkPath"
