import os
import pytest
import asyncio
from backend.app.browser.browser_controller import BrowserController
from backend.app.browser.playwright_mcp_bridge import PlaywrightMCPBridge


@pytest.mark.asyncio
async def test_browser_controller_and_mock_portal():
    controller = BrowserController(headless=True)
    await controller.initialize()

    portal_path = os.path.abspath("backend/mock_portal/index.html")
    portal_url = f"file://{portal_path}"

    # Navigate
    result = await controller.navigate(portal_url)
    assert "BharatRail" in result["title"]
    assert len(result["screenshot"]) > 100

    # Accessibility Tree
    tree = await controller.get_accessibility_tree()
    assert tree is not None

    # Semantic Elements
    elements = await controller.get_semantic_elements()
    assert len(elements) > 0
    ids = [e["id"] for e in elements if e["id"]]
    assert "source-station" in ids
    assert "destination-station" in ids
    assert "search-btn" in ids

    # MCP Bridge test
    bridge = PlaywrightMCPBridge(controller)
    tools = bridge.get_tool_definitions()
    assert len(tools) >= 5

    # Test fill and search
    await bridge.execute_tool("browser_fill_element", {
        "selector": "#source-station",
        "value": "Bengaluru City (SBC)"
    })
    await bridge.execute_tool("browser_fill_element", {
        "selector": "#destination-station",
        "value": "Mysuru Jn (MYS)"
    })
    await bridge.execute_tool("browser_click", {
        "selector": "#search-btn"
    })

    # Wait for results
    await asyncio.sleep(0.5)
    extracted = await controller.extract_page_data()
    assert len(extracted.get("trains", [])) >= 3

    await controller.close()
