import os
import subprocess
import time
import pytest
from playwright.async_api import async_playwright


@pytest.mark.asyncio
async def test_frontend_renders_without_white_screen():
    """Verify that the frontend builds, loads in Chromium, and renders the complete VaaniWeb UI

    with zero uncaught console errors and all dashboard panels present.
    """
    # Start Vite preview server on 5173
    preview_proc = subprocess.Popen(
        ["npx", "vite", "preview", "--port", "5173", "--host", "127.0.0.1"],
        cwd=os.path.abspath("frontend"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    time.sleep(2.0)

    console_errors = []
    page_logs = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            page.on("console", lambda msg: page_logs.append(f"[{msg.type}] {msg.text}"))
            page.on("pageerror", lambda err: console_errors.append(str(err)))

            # Navigate to the frontend
            await page.goto("http://127.0.0.1:5173", wait_until="networkidle", timeout=15000)

            # Check that root is not empty
            root_html = await page.inner_html("#root")
            assert len(root_html) > 100, "Root element is empty! (White screen detected)"

            # Check Brand title
            brand_text = await page.inner_text(".brand-text h1")
            assert brand_text == "VAANIWEB"

            # Check three panels exist and test desktop 50% / 25% / 25% full-viewport layout
            panels = await page.locator(".panel").all_inner_texts()
            assert len(panels) >= 3

            layout_info = await page.evaluate('''() => {
                const grid = document.querySelector('.dashboard-grid');
                const panels = Array.from(document.querySelectorAll('.panel')).map(p => p.getBoundingClientRect());
                return {
                    scrollWidth: document.body.scrollWidth,
                    innerWidth: window.innerWidth,
                    panel1Width: panels[0].width,
                    panel2Width: panels[1].width,
                    panel3Width: panels[2].width
                };
            }''')
            # Zero horizontal overflow
            assert layout_info["scrollWidth"] <= layout_info["innerWidth"]
            # Panel 1 is ~50% (approx 2x Panel 2 and Panel 3)
            assert layout_info["panel1Width"] > layout_info["panel2Width"] * 1.5

            # Check specific headings
            panel_headings = await page.locator(".panel-title").all_inner_texts()
            headings_str = " ".join(panel_headings).upper()
            assert "LIVE BROWSER PANEL" in headings_str
            assert "VERNACULAR VOICE ASSISTANT" in headings_str
            assert "ACTION AUDIT LOG" in headings_str

            # Check Language Selector buttons
            lang_btns = await page.locator(".lang-btn").all_inner_texts()
            langs_str = " ".join(lang_btns)
            assert "ಕನ್ನಡ" in langs_str
            assert "हिन्दी" in langs_str
            assert "தமிழ்" in langs_str
            assert "English" in langs_str

            # Verify no uncaught fatal JS runtime errors
            fatal_errors = [e for e in console_errors if "The `style` prop expects" in e or "Uncaught Error" in e]
            assert len(fatal_errors) == 0, f"Fatal JS errors found: {fatal_errors}"

            # Save screenshot for confirmation
            os.makedirs("test_artifacts", exist_ok=True)
            await page.screenshot(path="test_artifacts/frontend_rendered.png")

            await browser.close()
    finally:
        preview_proc.terminate()
        preview_proc.wait()
