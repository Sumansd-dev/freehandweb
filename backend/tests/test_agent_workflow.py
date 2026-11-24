import os
import pytest
import asyncio
from backend.app.browser.browser_controller import BrowserController
from backend.app.services.bedrock_service import BedrockService
from backend.app.services.elevenlabs_service import ElevenLabsService
from backend.app.safety.guardrail import SafetyGuardrail
from backend.app.agent.navigator_agent import NavigatorAgent


@pytest.mark.asyncio
async def test_full_kannada_railway_navigation_with_guardrail_approval():
    """Verify complete vernacular autonomous navigation pipeline in Kannada:

    Command -> Planning -> Playwright DOM Inspection & Actions -> Guardrail Intercept -> Approval -> Completion
    """
    portal_path = os.path.abspath("backend/mock_portal/index.html")
    portal_url = f"file://{portal_path}"

    browser = BrowserController(headless=True)
    await browser.initialize()
    bedrock = BedrockService()
    elevenlabs = ElevenLabsService()
    safety = SafetyGuardrail()

    emitted_events = []
    confirmation_payload = {}

    async def mock_event_callback(event_type: str, data: dict):
        emitted_events.append({"type": event_type, "data": data})
        if event_type == "confirmation_required":
            confirmation_payload.update(data)

    agent = NavigatorAgent(
        browser_controller=browser,
        bedrock_service=bedrock,
        elevenlabs_service=elevenlabs,
        safety_guardrail=safety,
        event_callback=mock_event_callback
    )

    kannada_cmd = "ಬೆಂಗಳೂರು ಇಂದ ಮೈಸೂರಿಗೆ ನಾಳೆ ರೈಲು ಹುಡುಕಿ"

    # Start task in background so we can handle the confirmation
    task = asyncio.create_task(
        agent.execute_vernacular_command(
            command=kannada_cmd,
            language="kn",
            target_url=portal_url
        )
    )

    # Wait until confirmation_required is emitted
    for _ in range(60):
        if confirmation_payload.get("confirmation_id"):
            break
        await asyncio.sleep(0.2)

    assert confirmation_payload.get("confirmation_id") is not None
    cid = confirmation_payload["confirmation_id"]
    assert "confirm-booking-btn" in confirmation_payload["selector"]

    # Verify that safety guardrail intercepted and paused execution
    event_types = [e["type"] for e in emitted_events]
    assert "task_started" in event_types
    assert "plan_ready" in event_types
    assert "action_started" in event_types
    assert "confirmation_required" in event_types

    # Now approve the sensitive booking
    safety.resolve_confirmation(cid, approved=True)

    # Await completion
    result = await asyncio.wait_for(task, timeout=15.0)

    assert result["success"] is True
    assert "PNR" in result["summary"] or "ಟಿಕೆಟ್" in result["summary"]
    extracted = result["extracted_data"]
    assert extracted.get("pnr") != ""
    assert extracted.get("isSuccess") is True

    await browser.close()


@pytest.mark.asyncio
async def test_guardrail_user_cancellation():
    """Verify that when a user rejects a sensitive booking action,

    automation halts immediately without committing.
    """
    portal_path = os.path.abspath("backend/mock_portal/index.html")
    portal_url = f"file://{portal_path}"

    browser = BrowserController(headless=True)
    await browser.initialize()
    bedrock = BedrockService()
    elevenlabs = ElevenLabsService()
    safety = SafetyGuardrail()

    confirmation_payload = {}

    async def mock_event_callback(event_type: str, data: dict):
        if event_type == "confirmation_required":
            confirmation_payload.update(data)

    agent = NavigatorAgent(
        browser_controller=browser,
        bedrock_service=bedrock,
        elevenlabs_service=elevenlabs,
        safety_guardrail=safety,
        event_callback=mock_event_callback
    )

    task = asyncio.create_task(
        agent.execute_vernacular_command(
            command="Find sleeper train from Bangalore to Mysore tomorrow",
            language="en",
            target_url=portal_url
        )
    )

    # Wait for confirmation request
    for _ in range(60):
        if confirmation_payload.get("confirmation_id"):
            break
        await asyncio.sleep(0.2)

    cid = confirmation_payload["confirmation_id"]
    # User REJECTS the confirmation
    safety.resolve_confirmation(cid, approved=False)

    result = await asyncio.wait_for(task, timeout=15.0)

    # Check that booking was NOT committed
    page = await browser.ensure_page()
    success_visible = await page.is_visible("#success-section")
    assert not success_visible

    await browser.close()
