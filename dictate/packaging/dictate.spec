# PyInstaller build for the standalone app.
#
# Two executables share one directory of libraries: Dictate.exe is the app, and
# DictateSetup.exe is the first-run wizard the installer calls. Neither ships CUDA or the
# Whisper weights: the wizard downloads those, which is what keeps the installer small.
#
# Build:  .venv\Scripts\python.exe -m PyInstaller packaging\dictate.spec --noconfirm

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

ROOT = Path(SPECPATH).parent

datas = [
    (str(ROOT / "dictate" / "ui" / "index.html"), "dictate/ui"),
    (str(ROOT / "assets"), "assets"),
]
datas += collect_data_files("sherpa_onnx")
datas += collect_data_files("webview")

binaries = collect_dynamic_libs("sherpa_onnx")
binaries += collect_dynamic_libs("ctranslate2")

hiddenimports = [
    "dictate.setup_wizard",
    "sounddevice",
    "sherpa_onnx",
    "faster_whisper",
    "ctranslate2",
    "pystray._win32",
    "PIL._tkinter_finder",
    "webview.platforms.edgechromium",
    "clr_loader",
]

# nvidia: the CUDA wheels are 2 GB and the app downloads three of their DLLs at setup.
# playwright, pytest and matplotlib are development tools. torch is not a dependency and
# only appears through optional imports in other packages.
excludes = [
    "nvidia",
    # faster-whisper reaches for onnxruntime only for its own Silero VAD, which the app
    # does not use: it trims with sherpa-onnx before transcribing. 37 MB.
    "onnxruntime",
    # An optional download accelerator for huggingface_hub. Without it the download falls
    # back to plain HTTP, which is what the wizard measures against anyway. 9.5 MB.
    "hf_xet",
    "playwright",
    "pytest",
    "matplotlib",
    "torch",
    "IPython",
    "notebook",
]

app_analysis = Analysis(
    [str(ROOT / "packaging" / "app_entry.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=excludes,
    noarchive=False,
)

setup_analysis = Analysis(
    [str(ROOT / "packaging" / "setup_entry.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=excludes,
    noarchive=False,
)

MERGE((app_analysis, "app", "Dictate"), (setup_analysis, "setup", "DictateSetup"))

app_pyz = PYZ(app_analysis.pure)
setup_pyz = PYZ(setup_analysis.pure)

app_exe = EXE(
    app_pyz,
    app_analysis.scripts,
    [],
    exclude_binaries=True,
    name="Dictate",
    console=False,
    icon=str(ROOT / "assets" / "dictate.ico"),
)

setup_exe = EXE(
    setup_pyz,
    setup_analysis.scripts,
    [],
    exclude_binaries=True,
    name="DictateSetup",
    console=False,
    icon=str(ROOT / "assets" / "dictate.ico"),
)

COLLECT(
    app_exe,
    app_analysis.binaries,
    app_analysis.datas,
    setup_exe,
    setup_analysis.binaries,
    setup_analysis.datas,
    strip=False,
    upx=False,
    name="Dictate",
)
