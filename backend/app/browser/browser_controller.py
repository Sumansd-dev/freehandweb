import asyncio
import base64
import logging
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger("vaaniweb.browser")


class BrowserController:
    """Autonomous Playwright browser controller with accessibility tree extraction,

    semantic element identification, action execution, and real-time screenshots.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._is_initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self):
        async with self._lock:
            if self._is_initialized and self._page:
                return

            logger.info(f"Initializing Playwright browser (headless={self.headless})...")
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled"
                ]
            )
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self._page = await self._context.new_page()
            self._is_initialized = True
            logger.info("Playwright browser initialized successfully.")

    async def ensure_page(self) -> Page:
        if not self._is_initialized or not self._page or self._page.is_closed():
            await self.initialize()
        return self._page

    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a website URL and wait for ready state."""
        page = await self.ensure_page()
        logger.info(f"Navigating to {url}...")
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        # Give a small cushion for dynamic scripts to render initial state
        await asyncio.sleep(0.5)

        title = await page.title()
        status_code = response.status if response else 200
        logger.info(f"Navigated to {url} - Title: '{title}', Status: {status_code}")

        screenshot = await self.capture_screenshot()
        return {
            "url": page.url,
            "title": title,
            "status_code": status_code,
            "screenshot": screenshot
        }

    async def capture_screenshot(self) -> str:
        """Capture viewport screenshot as base64 JPEG string."""
        page = await self.ensure_page()
        try:
            # High quality JPEG for fast real-time transfer
            screenshot_bytes = await page.screenshot(type="jpeg", quality=80)
            base64_data = base64.b64encode(screenshot_bytes).decode("utf-8")
            return f"data:image/jpeg;base64,{base64_data}"
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}")
            return ""

    async def get_accessibility_tree(self) -> Optional[Dict[str, Any]]:
        """Retrieve accessibility tree snapshot using Playwright's official aria_snapshot

        and Chrome DevTools Protocol (CDP) Accessibility tree.
        """
        page = await self.ensure_page()
        try:
            aria_yaml = await page.aria_snapshot()
            return {
                "format": "aria_yaml",
                "content": aria_yaml
            }
        except Exception as e:
            logger.warning(f"Failed to get aria_snapshot, falling back to CDP: {e}")
            try:
                client = await page.context.new_cdp_session(page)
                ax_data = await client.send("Accessibility.getFullAXTree")
                await client.detach()
                return {
                    "format": "cdp_ax_nodes",
                    "nodes": ax_data.get("nodes", [])[:100]
                }
            except Exception as e2:
                logger.error(f"CDP accessibility tree also failed: {e2}")
                return None

    async def get_semantic_elements(self) -> List[Dict[str, Any]]:
        """Inspect and return interactive semantic elements on the page

        including forms, inputs, buttons, links, ARIA roles, and labels.
        """
        page = await self.ensure_page()
        try:
            elements = await page.evaluate("""
                () => {
                    const results = [];
                    const selectors = 'button, input, select, textarea, a[href], [role="button"], [role="combobox"], [role="tab"], [role="link"], [data-sensitive="true"]';
                    const nodes = Array.from(document.querySelectorAll(selectors));

                    nodes.forEach((el, index) => {
                        // Check if visible
                        const style = window.getComputedStyle(el);
                        const isVisible = style.display !== 'none' && 
                                          style.visibility !== 'hidden' && 
                                          style.opacity !== '0' && 
                                          el.offsetParent !== null;

                        if (!isVisible && el.type !== 'hidden') return;

                        const id = el.id || '';
                        const name = el.getAttribute('name') || '';
                        const role = el.getAttribute('role') || el.tagName.toLowerCase();
                        const ariaLabel = el.getAttribute('aria-label') || '';
                        const placeholder = el.getAttribute('placeholder') || '';
                        const text = (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ').substring(0, 100);
                        const value = el.value !== undefined ? el.value : '';
                        const type = el.getAttribute('type') || '';
                        const isSensitive = el.getAttribute('data-sensitive') === 'true' || 
                                            /confirm|pay|book|purchase|checkout|otp/i.test(ariaLabel + ' ' + text + ' ' + id);

                        // Build preferred selector
                        let selector = '';
                        if (id) {
                            selector = '#' + id;
                        } else if (ariaLabel) {
                            selector = `[aria-label="${ariaLabel}"]`;
                        } else if (name) {
                            selector = `[name="${name}"]`;
                        } else {
                            selector = `${el.tagName.toLowerCase()}:nth-of-type(${index + 1})`;
                        }

                        results.push({
                            index,
                            tagName: el.tagName.toLowerCase(),
                            id,
                            name,
                            role,
                            ariaLabel,
                            placeholder,
                            text,
                            value,
                            type,
                            isSensitive,
                            selector
                        });
                    });

                    return results;
                }
            """)
            return elements
        except Exception as e:
            logger.error(f"Error evaluating semantic elements: {e}")
            return []

    async def fill_input(self, selector: str, value: str, role: Optional[str] = None, aria_label: Optional[str] = None) -> bool:
        """Fill an input field using robust semantic or CSS locator."""
        page = await self.ensure_page()
        try:
            target = None
            if aria_label:
                target = page.get_by_label(aria_label, exact=False)
            elif role:
                target = page.get_by_role(role, name=aria_label or selector)
            
            if target and await target.count() > 0:
                await target.first.fill(value)
            else:
                await page.fill(selector, value)

            await asyncio.sleep(0.3)
            return True
        except Exception as e:
            logger.error(f"Failed to fill element {selector} with '{value}': {e}")
            # Fallback to direct evaluate
            try:
                await page.evaluate(f"""
                    () => {{
                        const el = document.querySelector('{selector}');
                        if (el) {{
                            el.value = '{value}';
                            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                    }}
                """)
                return True
            except Exception as e2:
                logger.error(f"Direct evaluate fallback also failed: {e2}")
                return False

    async def select_option(self, selector: str, value: str) -> bool:
        """Select an option from a <select> element."""
        page = await self.ensure_page()
        try:
            await page.select_option(selector, value)
            await asyncio.sleep(0.3)
            return True
        except Exception as e:
            logger.error(f"Failed to select option '{value}' in {selector}: {e}")
            return False

    async def click_element(self, selector: str, role: Optional[str] = None, aria_label: Optional[str] = None, text: Optional[str] = None) -> bool:
        """Click an element using semantic locator or selector."""
        page = await self.ensure_page()
        try:
            target = None
            if aria_label:
                target = page.get_by_label(aria_label, exact=False)
                if await target.count() == 0:
                    target = page.locator(f'[aria-label*="{aria_label}"]')
            elif text:
                target = page.get_by_text(text, exact=False)
            
            if target and await target.count() > 0:
                await target.first.click()
            else:
                await page.click(selector)

            # Wait briefly for potential DOM update
            await asyncio.sleep(0.6)
            return True
        except Exception as e:
            logger.error(f"Failed to click element {selector}: {e}")
            # Try evaluate click fallback
            try:
                await page.evaluate(f"""
                    () => {{
                        const el = document.querySelector('{selector}');
                        if (el) {{
                            el.click();
                        }}
                    }}
                """)
                await asyncio.sleep(0.6)
                return True
            except Exception as e2:
                logger.error(f"Evaluate click also failed: {e2}")
                return False

    async def extract_page_data(self) -> Dict[str, Any]:
        """Extract key text and structured data from the active page."""
        page = await self.ensure_page()
        try:
            data = await page.evaluate("""
                () => {
                    const text = document.body.innerText || '';
                    const results = [];
                    // Extract train cards if present
                    const trainCards = document.querySelectorAll('.train-card');
                    trainCards.forEach(card => {
                        results.push({
                            trainName: card.querySelector('.train-name')?.innerText || '',
                            trainNumber: card.querySelector('.train-number')?.innerText || '',
                            schedule: card.querySelector('.train-schedule')?.innerText || '',
                            classes: Array.from(card.querySelectorAll('.class-pill')).map(p => p.innerText.replace(/\\n/g, ' - '))
                        });
                    });

                    // Check for booking success
                    const pnr = document.querySelector('#confirmed-pnr')?.innerText || '';
                    const success = !!document.querySelector('#success-section:not(.hidden)');

                    return {
                        trains: results,
                        pnr,
                        isSuccess: success,
                        pageSnippet: text.substring(0, 1500)
                    };
                }
            """)
            return data
        except Exception as e:
            logger.error(f"Failed to extract page data: {e}")
            return {}

    async def get_state(self) -> Dict[str, Any]:
        """Retrieve full current browser state snapshot."""
        page = await self.ensure_page()
        screenshot = await self.capture_screenshot()
        a11y_tree = await self.get_accessibility_tree()
        semantic_elements = await self.get_semantic_elements()
        title = await page.title()

        return {
            "url": page.url,
            "title": title,
            "screenshot": screenshot,
            "accessibility_tree": a11y_tree,
            "semantic_elements": semantic_elements
        }

    async def close(self):
        async with self._lock:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            self._is_initialized = False
            logger.info("Playwright browser closed.")
