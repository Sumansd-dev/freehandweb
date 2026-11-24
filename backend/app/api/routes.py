import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.app.models.schemas import (
    UserCommandRequest,
    ConfirmationRequest
)
from backend.app.core.config import settings
from backend.app.api.websocket_manager import ws_manager
from backend.app.mcp.user_profile_server import get_user_profile, update_user_preference

logger = logging.getLogger("vaaniweb.routes")
router = APIRouter()

# Global singletons injected by main.py
browser_controller = None
bedrock_service = None
elevenlabs_service = None
safety_guardrail = None
navigator_agent = None


def init_routes(browser, bedrock, elevenlabs, safety, agent):
    global browser_controller, bedrock_service, elevenlabs_service, safety_guardrail, navigator_agent
    browser_controller = browser
    bedrock_service = bedrock
    elevenlabs_service = elevenlabs
    safety_guardrail = safety
    navigator_agent = agent


@router.get("/status")
async def get_system_status():
    """Retrieve full status of VaaniWeb engines and services."""
    return {
        "status": "online",
        "engines": {
            "bedrock": {
                "configured": bedrock_service.is_configured if bedrock_service else False,
                "model_id": settings.BEDROCK_MODEL_ID,
                "engine": "aws_bedrock" if (bedrock_service and bedrock_service.is_configured) else "bedrock_fallback"
            },
            "elevenlabs": elevenlabs_service.get_status() if elevenlabs_service else {"configured": False},
            "playwright": {
                "initialized": browser_controller._is_initialized if browser_controller else False,
                "headless": settings.PLAYWRIGHT_HEADLESS
            },
            "mcp": {
                "server_name": "vaaniweb-user-profile-translation-server",
                "status": "active"
            }
        },
        "active_task": {
            "is_running": navigator_agent.is_running if navigator_agent else False,
            "task_id": navigator_agent.current_task_id if navigator_agent else None
        }
    }


@router.post("/command")
async def handle_user_command(req: UserCommandRequest, background_tasks: BackgroundTasks):
    """Submit a vernacular command (Kannada, Hindi, Tamil, English) for autonomous execution."""
    if not navigator_agent:
        raise HTTPException(status_code=500, detail="Navigator agent not initialized")

    session_id = req.session_id or "default"
    command_text = req.text.strip()
    language = req.language or "kn"

    if not command_text:
        raise HTTPException(status_code=400, detail="Command text cannot be empty")

    logger.info(f"Received command: '{command_text}' in language '{language}'")

    # Broadcast command received event
    await ws_manager.broadcast_to_session(session_id, "command_received", {
        "text": command_text,
        "language": language
    })

    # Execute in background task so API responds immediately and streams via WebSocket
    async def run_agent():
        await navigator_agent.execute_vernacular_command(
            command=command_text,
            language=language,
            target_url=req.target_url,
            session_id=session_id
        )

    background_tasks.add_task(run_agent)

    return {
        "status": "accepted",
        "message": f"Autonomous navigation started for: '{command_text}'",
        "language": language
    }


@router.post("/confirm")
async def handle_confirmation(req: ConfirmationRequest):
    """User approval or cancellation for sensitive actions (Confirm-Before-Commit)."""
    if not safety_guardrail:
        raise HTTPException(status_code=500, detail="Safety guardrail not initialized")

    resolved = safety_guardrail.resolve_confirmation(req.confirmation_id, req.approved)
    if not resolved:
        raise HTTPException(status_code=404, detail="Confirmation ticket not found or expired")

    return {
        "confirmation_id": req.confirmation_id,
        "approved": req.approved,
        "status": "resolved"
    }


@router.post("/stop")
async def stop_active_task():
    """Emergency stop button: halts active browser navigation immediately."""
    if navigator_agent:
        await navigator_agent.stop_active_task()
        return {"status": "stopped", "message": "Task cancelled successfully."}
    return {"status": "idle"}


@router.get("/browser/state")
async def get_browser_state():
    """Retrieve current live browser screenshot and state."""
    if not browser_controller:
        raise HTTPException(status_code=500, detail="Browser controller not initialized")
    return await browser_controller.get_state()


@router.get("/profile")
async def get_profile(session_id: str = "default"):
    """Retrieve safe user profile from User Profile MCP server."""
    return get_user_profile(session_id)


@router.post("/profile")
async def update_profile(data: Dict[str, str], session_id: str = "default"):
    """Update user preference in MCP server."""
    key = data.get("key")
    val = data.get("value")
    if not key or not val:
        raise HTTPException(status_code=400, detail="key and value are required")
    try:
        msg = update_user_preference(key, val, session_id)
        return {"message": msg, "profile": get_user_profile(session_id)}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.post("/tts")
async def synthesize_speech(payload: Dict[str, str]):
    """Direct text-to-speech helper endpoint."""
    text = payload.get("text", "")
    language = payload.get("language", "kn")
    if not text:
        raise HTTPException(status_code=400, detail="Text required")

    if elevenlabs_service and elevenlabs_service.is_configured:
        audio = await elevenlabs_service.text_to_speech(text, language=language)
        if audio:
            return {"audio": audio, "provider": "elevenlabs"}

    return {"audio": None, "provider": "web_speech_fallback", "text": text}
