import asyncio
import time
import logging
from typing import Dict, Any, Optional, Callable, Coroutine
from backend.app.models.schemas import (
    BrowserAction,
    BrowserActionType,
    ActionPlan,
    ActionLogEvent
)
from backend.app.browser.browser_controller import BrowserController
from backend.app.services.bedrock_service import BedrockService
from backend.app.services.elevenlabs_service import ElevenLabsService
from backend.app.safety.guardrail import SafetyGuardrail

logger = logging.getLogger("vaaniweb.agent")


class NavigatorAgent:
    """Vernacular Autonomous Browser Navigator Agent.

    Orchestrates Bedrock reasoning, accessibility inspection, Playwright browser actions,
    Confirm-Before-Commit safety guardrails, and ElevenLabs voice narration.
    """

    def __init__(
        self,
        browser_controller: BrowserController,
        bedrock_service: BedrockService,
        elevenlabs_service: ElevenLabsService,
        safety_guardrail: SafetyGuardrail,
        event_callback: Optional[Callable[[str, Dict[str, Any]], Coroutine[Any, Any, None]]] = None
    ):
        self.browser = browser_controller
        self.bedrock = bedrock_service
        self.elevenlabs = elevenlabs_service
        self.safety = safety_guardrail
        self.event_callback = event_callback

        self.current_task_id: Optional[str] = None
        self.is_running = False
        self.is_cancelled = False
        self.active_plan: Optional[ActionPlan] = None

    async def emit(self, event_type: str, data: Dict[str, Any]):
        """Emit real-time WebSocket event to the frontend."""
        if self.event_callback:
            try:
                await self.event_callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in event callback for '{event_type}': {e}")

    async def stop_active_task(self):
        """Immediately stop and cancel any ongoing browser automation."""
        logger.info("Stopping active agent task...")
        self.is_cancelled = True
        self.is_running = False
        self.safety.cancel_all_pending()
        await self.emit("task_cancelled", {"message": "Agent execution stopped by user."})

    async def execute_vernacular_command(
        self,
        command: str,
        language: str = "kn",
        target_url: Optional[str] = None,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """Execute full vernacular autonomous navigation pipeline."""
        self.is_running = True
        self.is_cancelled = False
        task_id = f"task_{int(time.time())}"
        self.current_task_id = task_id

        await self.emit("task_started", {
            "task_id": task_id,
            "command": command,
            "language": language,
            "timestamp": time.strftime("%H:%M:%S")
        })

        try:
            # 1. Inspect existing browser state if open
            current_state = await self.browser.get_state()

            # 2. AWS Bedrock Planning (or deterministic fallback)
            await self.emit("agent_thought", {
                "thought": f"Analyzing user intent in {language.upper()} and planning browser actions...",
                "status": "planning"
            })

            plan: ActionPlan = await self.bedrock.plan_browser_actions(
                command=command,
                language=language,
                target_url=target_url,
                page_context=current_state,
                session_id=session_id
            )
            self.active_plan = plan

            # Voice explanation of the plan
            tts_audio = None
            if plan.explanation:
                tts_audio = await self.elevenlabs.text_to_speech(plan.explanation, language=language)

            await self.emit("plan_ready", {
                "intent": plan.intent,
                "engine": plan.engine,
                "explanation": plan.explanation,
                "total_steps": len(plan.actions),
                "audio": tts_audio,
                "parameters": plan.parameters
            })

            # 3. Step-by-step browser action execution
            action_results = []
            for idx, action in enumerate(plan.actions):
                if self.is_cancelled:
                    logger.info("Execution loop halted due to user cancellation.")
                    break

                step_num = idx + 1
                action.status = "executing"

                # Check action safety with backend guardrail
                page_url = (await self.browser.ensure_page()).url
                safety_check = self.safety.check_action_safety(action, current_url=page_url)

                if safety_check.requires_confirmation:
                    # SENSITIVE ACTION: Pause and wait for user confirmation
                    logger.warning(f"Sensitive action triggered: {action.action_type} - {action.reason}")
                    action.status = "awaiting_confirmation"

                    confirmation = self.safety.create_confirmation_request(
                        action=action,
                        explanation=action.explanation or "Sensitive commitment requires authorization"
                    )

                    # Spoken warning in user's language
                    confirm_prompt = {
                        "kn": "ದಯವಿಟ್ಟು ಗಮನಿಸಿ: ಬುಕಿಂಗ್ ದೃಢೀಕರಿಸಲು ನಿಮ್ಮ ಅನುಮೋದನೆ ಅಗತ್ಯವಿದೆ. ಮುಂದುವರಿಯುವುದೇ?",
                        "hi": "कृपया ध्यान दें: बुकिंग की पुष्टि के लिए आपकी अनुमति चाहिए। क्या आगे बढ़ें?",
                        "ta": "கவனிக்கவும்: முன்பதிவை உறுதிப்படுத்த உங்கள் ஒப்புதல் தேவை. தொடரலாமா?",
                        "en": "Please confirm: Your authorization is required to complete this booking."
                    }.get(language, "User confirmation required.")

                    confirm_audio = await self.elevenlabs.text_to_speech(confirm_prompt, language=language)

                    # Update screenshot for visual confirmation
                    screenshot = await self.browser.capture_screenshot()

                    await self.emit("confirmation_required", {
                        "confirmation_id": confirmation["confirmation_id"],
                        "action_id": action.id,
                        "action_type": action.action_type.value,
                        "selector": action.selector,
                        "reason": safety_check.reason,
                        "risk_level": safety_check.risk_level,
                        "explanation": action.explanation,
                        "prompt_text": confirm_prompt,
                        "audio": confirm_audio,
                        "screenshot": screenshot,
                        "step": f"{step_num}/{len(plan.actions)}"
                    })

                    # Wait for user's explicit response (future)
                    try:
                        approved = await confirmation["future"]
                    except asyncio.CancelledError:
                        approved = False

                    if not approved or self.is_cancelled:
                        action.status = "cancelled"
                        await self.emit("action_log", {
                            "id": f"log_{int(time.time()*1000)}",
                            "action": action.action_type.value,
                            "element": action.selector or action.aria_label or "Booking Commit",
                            "status": "warning",
                            "explanation": "Action cancelled by user during confirmation.",
                            "timestamp": time.strftime("%H:%M:%S")
                        })
                        break
                    else:
                        logger.info("User granted explicit approval. Resuming execution.")
                        await self.emit("confirmation_approved", {
                            "confirmation_id": confirmation["confirmation_id"],
                            "message": "User approved sensitive action. Executing booking..."
                        })

                # Execute action
                start_time = time.time()
                await self.emit("action_started", {
                    "step": step_num,
                    "total_steps": len(plan.actions),
                    "action_id": action.id,
                    "action_type": action.action_type.value,
                    "selector": action.selector,
                    "element": action.aria_label or action.selector or "Page",
                    "explanation": action.explanation,
                    "timestamp": time.strftime("%H:%M:%S")
                })

                success = await self._perform_action(action)
                duration = round(time.time() - start_time, 2)
                action.status = "success" if success else "failed"

                # Capture updated screenshot
                screenshot = await self.browser.capture_screenshot()
                page = await self.browser.ensure_page()

                await self.emit("screenshot_update", {
                    "screenshot": screenshot,
                    "url": page.url,
                    "title": await page.title(),
                    "current_task": action.explanation or action.reason
                })

                await self.emit("action_completed", {
                    "step": step_num,
                    "action_id": action.id,
                    "success": success,
                    "duration": f"{duration}s",
                    "action_type": action.action_type.value,
                    "element": action.aria_label or action.selector or "Element",
                    "explanation": action.explanation,
                    "timestamp": time.strftime("%H:%M:%S")
                })

                action_results.append({
                    "action": action.id,
                    "success": success,
                    "duration": duration
                })

                # Human-like smooth pacing
                await asyncio.sleep(0.4)

            # 4. Extract final state & completion summary
            extracted = await self.browser.extract_page_data()
            final_summary = self._build_completion_summary(plan, extracted, language)

            summary_audio = await self.elevenlabs.text_to_speech(final_summary, language=language)

            await self.emit("task_completed", {
                "task_id": task_id,
                "summary": final_summary,
                "audio": summary_audio,
                "extracted_data": extracted,
                "total_actions": len(action_results),
                "timestamp": time.strftime("%H:%M:%S")
            })

            return {
                "success": True,
                "task_id": task_id,
                "summary": final_summary,
                "extracted_data": extracted
            }

        except Exception as e:
            logger.error(f"Error in agent execution: {e}", exc_info=True)
            await self.emit("task_error", {
                "error": str(e),
                "timestamp": time.strftime("%H:%M:%S")
            })
            return {"success": False, "error": str(e)}

        finally:
            self.is_running = False

    async def _perform_action(self, action: BrowserAction) -> bool:
        """Dispatch concrete browser action to Playwright."""
        try:
            if action.action_type == BrowserActionType.NAVIGATE:
                await self.browser.navigate(action.value or action.selector)
                return True

            elif action.action_type == BrowserActionType.FILL:
                return await self.browser.fill_input(
                    selector=action.selector,
                    value=action.value or "",
                    aria_label=action.aria_label
                )

            elif action.action_type == BrowserActionType.SELECT:
                return await self.browser.select_option(
                    selector=action.selector,
                    value=action.value or ""
                )

            elif action.action_type in [BrowserActionType.CLICK, BrowserActionType.SENSITIVE_COMMIT]:
                return await self.browser.click_element(
                    selector=action.selector,
                    aria_label=action.aria_label,
                    text=action.text
                )

            elif action.action_type == BrowserActionType.WAIT:
                await asyncio.sleep(float(action.value or "1"))
                return True

            return False
        except Exception as e:
            logger.error(f"Failed to perform action {action.id}: {e}")
            return False

    def _build_completion_summary(self, plan: ActionPlan, extracted: Dict[str, Any], language: str) -> str:
        """Formulate a friendly spoken completion summary in the target language."""
        trains_count = len(extracted.get("trains", []))
        pnr = extracted.get("pnr", "")

        if pnr:
            summaries = {
                "kn": f"ಅಭಿನಂದನೆಗಳು! ನಿಮ್ಮ ರೈಲ್ವೆ ಟಿಕೆಟ್ ಯಶಸ್ವಿಯಾಗಿ ಬುಕ್ ಆಗಿದೆ. ನಿಮ್ಮ {pnr}. ವಿವರಗಳನ್ನು ಸ್ಕ್ರೀನ್ ಮೇಲೆ ನೋಡಬಹುದು.",
                "hi": f"बधाई हो! आपका रेलवे टिकट सफलतापूर्वक बुक हो गया है। आपका {pnr} है। विवरण स्क्रीन पर उपलब्ध है।",
                "ta": f"வாழ்த்துகள்! உங்கள் ரயில் டிக்கெட் வெற்றிகரமாக முன்பதிவு செய்யப்பட்டது. உங்கள் {pnr}. விவரங்கள் திரையில் உள்ளன.",
                "en": f"Congratulations! Your railway ticket has been successfully booked. Your {pnr}. Details are shown on screen."
            }
            return summaries.get(language, summaries["en"])

        if trains_count > 0:
            summaries = {
                "kn": f"{trains_count} ರೈಲುಗಳು ಲಭ್ಯವಿವೆ. ವೊಡೆಯರ್ ಎಕ್ಸ್‌ಪ್ರೆಸ್ ಮುಂತಾದ ರೈಲುಗಳ ವಿವರಗಳನ್ನು ಸ್ಕ್ರೀನ್ ಮೇಲೆ ನೋಡಬಹುದು.",
                "hi": f"{trains_count} ट्रेनें उपलब्ध हैं। वोडेयार एक्सप्रेस सहित सभी ट्रेनों का विवरण स्क्रीन पर प्रदर्शित है।",
                "ta": f"{trains_count} ரயில்கள் கிடைக்கின்றன. வொடையார் எக்ஸ்பிரஸ் உள்ளிட்ட ரயில்களின் விவரங்கள் திரையில் உள்ளன.",
                "en": f"Found {trains_count} available trains. Details including Wodeyar Express are displayed on the screen."
            }
            return summaries.get(language, summaries["en"])

        return {
            "kn": "ವೆಬ್‌ಸೈಟ್ ನ್ಯಾವಿಗೇಶನ್ ಯಶಸ್ವಿಯಾಗಿ ಪೂರ್ಣಗೊಂಡಿದೆ.",
            "hi": "वेबसाइट नेविगेशन सफलतापूर्वक पूरा हुआ।",
            "ta": "இணையதள வழிசெலுத்தல் வெற்றிகரமாக முடிந்தது.",
            "en": "Website navigation completed successfully."
        }.get(language, "Navigation completed successfully.")
