# Dictate UI — Handoff Prompt for External Design Tool

## Project Overview
Dictate is a Windows desktop dictation app that transcribes Slovak/Czech/English speech using local Whisper AI and pastes the text at the cursor position.

## Technology Stack
- **UI Framework**: pywebview 6.x (WebView2/Chromium, NOT Electron/Tauri)
- **Window**: Frameless, always-on-top, draggable via `.pywebview-drag-region`
- **File**: `dictate/ui/index.html` — single HTML file with embedded CSS + JS
- **DPI**: 150% scaling on target display (AppliedDPI=144). `SetProcessDpiAwareness(2)` is called in Python.
- **Window size**: 404×168 physical pixels (scaled by DPI multiplier in `overlay.py`)

## Current UI Structure
```
┌─ drag bar (title + settings + close buttons) ─┐
│  DICTATE · Ctrl+Shift+R              ⚙  ✕     │
├─ waveform canvas ─────────────────────────────┤
│  ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ │
├─ status row ──────────────────────────────────┤
│  [●]  PRIPRAVENÝ                              │
│       —                                       │
└───────────────────────────────────────────────┘
```

## JS ↔ Python Contract (NEVER BREAK THIS)
The JS must wait for `pywebviewready` DOM event before accessing `window.pywebview`.

**JS polls Python every 60ms:**
- `get_wave()` → `list[float]` (audio envelope points, 0.0–1.0)
- `get_status()` → `{state: str, status: str, transcript: str}`
  - `state`: IDLE | RECORDING | TRANSCRIBING | INJECTING
  - `status`: user-facing label ("PRIPRAVENÝ", "NAHRÁVAM", etc.)
  - `transcript`: current/previous transcription text

**JS calls Python on user action:**
- `toggle_record()` — start/stop recording
- `open_config()` — opens config JSON in default editor
- `exit()` — closes the app

## Known Issues to Fix
1. **Waveform too tall** — takes half the window, should be compact (~40px)
2. **Transcript single-line** — long text gets ellipsis (`…`), needs multi-line scrollable box
3. **Pulse ring clipped** — recording indicator uses `::after` with `transform: scale(1.45)` that gets cut off by window edge
4. **Window too tall** — 168px is excessive; 110–130px is sufficient
5. **White corners glitch** — `transparent=False` + `border-radius` occasionally shows white at corners on some GPUs
6. **Two concentric circles misaligned** — recording button pulse ring and main button are not perfectly centered

## Design Requirements
- **Language**: Slovak labels ("PRIPRAVENÝ", "NAHRÁVAM", "PREPISUJEM…", "VKLÁDAM…")
- **Colors**: Dark theme. Current: `#14161d` background, `#8b5cf6`→`#ec4899` gradient button, `#22d3aa`→`#22d3ee` waveform gradient
- **Font**: "Segoe UI Variable", "Segoe UI", system-ui, sans-serif
- **Must remain**: frameless, on_top, drag region, resizable=False
- **Must keep**: all JS↔Python contract functions working exactly as documented above

## File Locations
- `C:\Users\Danculus\agora\dictate\dictate\ui\index.html` — the UI file to edit
- `C:\Users\Danculus\agora\dictate\dictate\overlay.py` — Python window controller (DPI scaling, window size)

## Testing
After changes, run:
```powershell
cd C:\Users\Danculus\agora\dictate
uv run python tools\measure_ui.py
```
This creates screenshots at `Desktop\dictate_idle.png` and `Desktop\dictate_recording.png`.

## Constraints
- NO external CSS/JS files — everything must be in `index.html`
- NO changes to Python files unless window size needs adjustment
- NO breaking the JS↔Python API contract
- NO transparent=True (causes white corner glitches in WebView2)
