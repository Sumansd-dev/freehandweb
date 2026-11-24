import os
import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from backend.app.core.config import settings
from backend.app.browser.browser_controller import BrowserController
from backend.app.services.bedrock_service import BedrockService
from backend.app.services.elevenlabs_service import ElevenLabsService
from backend.app.safety.guardrail import SafetyGuardrail
from backend.app.agent.navigator_agent import NavigatorAgent
from backend.app.api.websocket_manager import ws_manager
from backend.app.api.routes import router, init_routes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("vaaniweb.main")

# Global references
browser_controller: BrowserController = None
bedrock_service: BedrockService = None
elevenlabs_service: ElevenLabsService = None
safety_guardrail: SafetyGuardrail = None
navigator_agent: NavigatorAgent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global browser_controller, bedrock_service, elevenlabs_service, safety_guardrail, navigator_agent

    logger.info("Starting up VaaniWeb system...")

    # 1. Initialize Browser Controller
    browser_controller = BrowserController(headless=settings.PLAYWRIGHT_HEADLESS)
    await browser_controller.initialize()

    # 2. Services
    bedrock_service = BedrockService()
    elevenlabs_service = ElevenLabsService()
    safety_guardrail = SafetyGuardrail()

    # 3. WebSocket event dispatcher callback
    async def dispatch_event(event_type: str, data: dict):
        await ws_manager.broadcast_to_session("default", event_type, data)

    # 4. Agent
    navigator_agent = NavigatorAgent(
        browser_controller=browser_controller,
        bedrock_service=bedrock_service,
        elevenlabs_service=elevenlabs_service,
        safety_guardrail=safety_guardrail,
        event_callback=dispatch_event
    )

    # 5. Inject dependencies into API routes
    init_routes(
        browser=browser_controller,
        bedrock=bedrock_service,
        elevenlabs=elevenlabs_service,
        safety=safety_guardrail,
        agent=navigator_agent
    )

    # Pre-navigate browser to mock portal so preview is ready immediately
    portal_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mock_portal", "index.html"))
    if os.path.exists(portal_file):
        try:
            logger.info(f"Pre-loading demonstration portal: file://{portal_file}")
            await browser_controller.navigate(f"file://{portal_file}")
        except Exception as e:
            logger.warning(f"Could not pre-load portal: {e}")

    logger.info("VaaniWeb backend initialization complete.")
    yield

    # Clean shutdown
    logger.info("Shutting down VaaniWeb...")
    if navigator_agent:
        await navigator_agent.stop_active_task()
    if browser_controller:
        await browser_controller.close()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="VaaniWeb Autonomous Web Navigator API",
    version="1.0.0",
    description="Vernacular Voice-First Autonomous Browser Agent Backend",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")

# Serve Mock Railway Booking Portal at /portal/
portal_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mock_portal"))
if os.path.exists(portal_dir):
    app.mount("/portal/static", StaticFiles(directory=os.path.join(portal_dir, "static"), check_dir=False), name="portal_static")

    @app.get("/portal", response_class=HTMLResponse)
    @app.get("/portal/", response_class=HTMLResponse)
    async def serve_portal():
        index_path = os.path.join(portal_dir, "index.html")
        return FileResponse(index_path, media_type="text/html")


@app.get("/")
async def root():
    return {
        "name": "VaaniWeb API",
        "tagline": "Your Voice. Your Language. Your Web.",
        "status": "online",
        "documentation": "/docs",
        "portal_url": "/portal/"
    }


@app.websocket("/ws")
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str = "default"):
    await ws_manager.connect(websocket, session_id)
    try:
        # Send initial state on connection
        if browser_controller:
            state = await browser_controller.get_state()
            await websocket.send_text(json.dumps({
                "type": "session_ready",
                "data": {
                    "session_id": session_id,
                    "url": state["url"],
                    "title": state["title"],
                    "screenshot": state["screenshot"],
                    "bedrock_engine": "aws_bedrock" if bedrock_service.is_configured else "bedrock_fallback",
                    "elevenlabs_status": elevenlabs_service.get_status()
                }
            }))

        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                action = payload.get("action")
                if action == "refresh_preview" and browser_controller:
                    screenshot = await browser_controller.capture_screenshot()
                    page = await browser_controller.ensure_page()
                    await websocket.send_text(json.dumps({
                        "type": "screenshot_update",
                        "data": {
                            "screenshot": screenshot,
                            "url": page.url,
                            "title": await page.title(),
                            "current_task": "User requested preview refresh"
                        }
                    }))
            except Exception as e:
                logger.warning(f"Error handling websocket message: {e}")

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, session_id)
