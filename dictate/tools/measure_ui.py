"""Headless screenshot of the dictate UI for visual verification."""
import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright

UI_HTML = Path(__file__).parent.parent / "dictate" / "ui" / "index.html"
OUT_PNG  = Path.home() / "Desktop" / "dictate_preview.png"
OUT_IDLE = Path.home() / "Desktop" / "dictate_idle.png"
OUT_REC  = Path.home() / "Desktop" / "dictate_recording.png"

async def screenshot_state(page, path, state, status, transcript="—", wave=None):
    mock = f"""
    window.pywebview = {{
      api: {{
        get_wave: async () => {json.dumps(wave or [0.02]*10)},
        get_status: async () => ({{
          state: "{state}",
          status: "{status}",
          transcript: {json.dumps(transcript)}
        }}),
        toggle_record: async () => {{}},
        open_config: async () => {{}},
        exit: async () => {{}}
      }}
    }};
    """
    await page.evaluate(mock)
    await page.evaluate("""
        const ev = new Event('pywebviewready');
        window.dispatchEvent(ev);
    """)
    # Let JS tick run a few cycles
    await page.wait_for_timeout(400)
    await page.screenshot(path=str(path), full_page=True)
    print("Saved:", path)

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)

        # IDLE state
        page = await browser.new_page(viewport={"width": 404, "height": 132})
        await page.goto(f"file:///{UI_HTML}")
        await page.wait_for_timeout(200)
        await screenshot_state(page, OUT_IDLE, "IDLE", "PRIPRAVENÝ")
        await page.close()

        # RECORDING state with waveform
        page = await browser.new_page(viewport={"width": 404, "height": 132})
        await page.goto(f"file:///{UI_HTML}")
        await page.wait_for_timeout(200)
        wave = [0.05,0.12,0.28,0.55,0.82,0.64,0.45,0.30,0.18,0.10,0.06,0.15,0.35,0.60,0.78,0.50,0.25,0.12,0.08,0.05]*12
        await screenshot_state(page, OUT_REC, "RECORDING", "NAHRÁVAM",
            "Toto je testovací prepis slovenského textu v aplikácii Dictate.",
            wave)
        await page.close()

        await browser.close()
        print("All screenshots done.")

if __name__ == "__main__":
    asyncio.run(main())
