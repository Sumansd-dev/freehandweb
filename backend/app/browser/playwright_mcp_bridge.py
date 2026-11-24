import logging
from typing import Dict, Any, List, Optional
from .browser_controller import BrowserController

logger = logging.getLogger("vaaniweb.playwright_mcp")


class PlaywrightMCPBridge:
    """Provides an MCP-compliant tool interface over the Playwright browser controller.

    Implements the standard `@playwright/mcp` tool signatures:
    - browser_navigate: Navigate to a URL
    - browser_take_screenshot: Capture viewport screenshot
    - browser_snapshot: Get accessibility tree snapshot
    - browser_click: Click an element by selector or semantic text
    - browser_fill_element: Fill an input element
    - browser_select_option: Select an option in a dropdown
    """

    def __init__(self, browser_controller: BrowserController):
        self.controller = browser_controller

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "browser_navigate",
                "description": "Navigate the browser to a specific URL and wait for domcontentloaded.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The URL to navigate to"}
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "browser_take_screenshot",
                "description": "Capture a live screenshot of the current page as a base64 JPEG.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "browser_snapshot",
                "description": "Read the full accessibility tree and semantic interactive elements of the current page.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "browser_click",
                "description": "Click an element by CSS selector, ARIA label, or role.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector of element to click"},
                        "role": {"type": "string", "description": "Optional ARIA role"},
                        "aria_label": {"type": "string", "description": "Optional ARIA label"},
                        "text": {"type": "string", "description": "Optional visible text"}
                    },
                    "required": ["selector"]
                }
            },
            {
                "name": "browser_fill_element",
                "description": "Fill a form input field with a string value.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector of input to fill"},
                        "value": {"type": "string", "description": "Text value to enter"},
                        "aria_label": {"type": "string", "description": "Optional ARIA label"}
                    },
                    "required": ["selector", "value"]
                }
            },
            {
                "name": "browser_select_option",
                "description": "Select an option from a dropdown element.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector of select element"},
                        "value": {"type": "string", "description": "Value to select"}
                    },
                    "required": ["selector", "value"]
                }
            }
        ]

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch an MCP tool call to the browser controller."""
        logger.info(f"[PlaywrightMCP] Executing {tool_name} with {arguments}")
        if tool_name == "browser_navigate":
            url = arguments.get("url")
            result = await self.controller.navigate(url)
            return {"content": [{"type": "text", "text": f"Successfully navigated to {url}. Title: {result['title']}"}]}

        elif tool_name == "browser_take_screenshot":
            screenshot = await self.controller.capture_screenshot()
            return {"content": [{"type": "image", "data": screenshot, "mimeType": "image/jpeg"}]}

        elif tool_name == "browser_snapshot":
            tree = await self.controller.get_accessibility_tree()
            elements = await self.controller.get_semantic_elements()
            return {
                "content": [
                    {
                        "type": "json",
                        "accessibility_tree": tree,
                        "semantic_elements": elements
                    }
                ]
            }

        elif tool_name == "browser_click":
            success = await self.controller.click_element(
                selector=arguments.get("selector", ""),
                role=arguments.get("role"),
                aria_label=arguments.get("aria_label"),
                text=arguments.get("text")
            )
            return {"content": [{"type": "text", "text": f"Click {'succeeded' if success else 'failed'}"}]}

        elif tool_name == "browser_fill_element":
            success = await self.controller.fill_input(
                selector=arguments.get("selector", ""),
                value=arguments.get("value", ""),
                aria_label=arguments.get("aria_label")
            )
            return {"content": [{"type": "text", "text": f"Fill {'succeeded' if success else 'failed'}"}]}

        elif tool_name == "browser_select_option":
            success = await self.controller.select_option(
                selector=arguments.get("selector", ""),
                value=arguments.get("value", "")
            )
            return {"content": [{"type": "text", "text": f"Select option {'succeeded' if success else 'failed'}"}]}

        else:
            raise ValueError(f"Unknown Playwright MCP tool: {tool_name}")
