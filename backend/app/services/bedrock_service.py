import json
import logging
from typing import Dict, Any, List, Optional
from backend.app.core.config import settings
from backend.app.models.schemas import ActionPlan, BrowserAction, BrowserActionType
from backend.app.mcp.user_profile_server import (
    standardize_station_name,
    standardize_travel_class,
    resolve_travel_date,
    get_user_profile
)

logger = logging.getLogger("vaaniweb.bedrock")


class BedrockService:
    """AWS Bedrock client for vernacular intent extraction and browser action planning.

    Features a clearly labeled deterministic fallback when AWS credentials are not configured.
    """

    def __init__(self):
        self.client = None
        self.is_configured = False
        self._init_client()

    def _init_client(self):
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            try:
                import boto3
                session_kwargs = {
                    "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
                    "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
                    "region_name": settings.AWS_REGION or "us-east-1"
                }
                if settings.AWS_SESSION_TOKEN:
                    session_kwargs["aws_session_token"] = settings.AWS_SESSION_TOKEN

                self.client = boto3.client("bedrock-runtime", **session_kwargs)
                self.is_configured = True
                logger.info(f"AWS Bedrock initialized with model: {settings.BEDROCK_MODEL_ID}")
            except Exception as e:
                logger.warning(f"Failed to initialize AWS Bedrock client: {e}. Fallback will be active.")
                self.is_configured = False
        else:
            logger.info("AWS credentials not provided. Using deterministic vernacular reasoning fallback.")
            self.is_configured = False

    async def plan_browser_actions(
        self,
        command: str,
        language: str = "kn",
        target_url: Optional[str] = None,
        page_context: Optional[Dict[str, Any]] = None,
        session_id: str = "default"
    ) -> ActionPlan:
        """Decompose vernacular user command into structured browser actions."""
        if self.is_configured and self.client:
            try:
                return await self._call_bedrock(command, language, target_url, page_context, session_id)
            except Exception as e:
                logger.error(f"AWS Bedrock execution failed: {e}. Falling back to deterministic reasoning.")
                return self._deterministic_fallback(command, language, target_url, page_context, session_id)
        else:
            return self._deterministic_fallback(command, language, target_url, page_context, session_id)

    async def _call_bedrock(
        self,
        command: str,
        language: str,
        target_url: Optional[str],
        page_context: Optional[Dict[str, Any]],
        session_id: str
    ) -> ActionPlan:
        """Call AWS Bedrock Claude or Nova model with structured JSON prompting."""
        logger.info(f"[BedrockService] Calling Bedrock model {settings.BEDROCK_MODEL_ID} for command: '{command}'")

        system_prompt = (
            "You are VaaniWeb AI, an autonomous browser navigation agent for vernacular languages (Kannada, Hindi, Tamil, English).\n"
            "Given a user's voice command and available webpage accessibility tree / elements, formulate a structured JSON plan.\n"
            "Output MUST be valid JSON adhering strictly to the schema:\n"
            "{\n"
            '  "intent": "string",\n'
            '  "target_url": "string",\n'
            '  "explanation": "string in the user\'s language",\n'
            '  "parameters": {"source": "...", "destination": "...", "date": "...", "class": "..."},\n'
            '  "actions": [\n'
            '    {\n'
            '      "id": "act_1",\n'
            '      "action_type": "navigate|fill|select|click|wait|sensitive_commit",\n'
            '      "selector": "#element-id",\n'
            '      "aria_label": "...",\n'
            '      "value": "...",\n'
            '      "reason": "...",\n'
            '      "is_sensitive": false,\n'
            '      "explanation": "Vernacular step explanation"\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        user_content = f"User Command: {command}\nLanguage: {language}\nTarget URL: {target_url or settings.MOCK_PORTAL_URL}\n"
        if page_context and "semantic_elements" in page_context:
            user_content += f"Available Page Elements: {json.dumps(page_context['semantic_elements'][:25])}\n"

        # Using Bedrock Converse API for universal model compatibility
        response = self.client.converse(
            modelId=settings.BEDROCK_MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": user_content}]
                }
            ],
            system=[{"text": system_prompt}],
            inferenceConfig={"temperature": 0.2, "maxTokens": 2048}
        )

        output_text = response["output"]["message"]["content"][0]["text"]
        # Extract JSON
        json_start = output_text.find("{")
        json_end = output_text.rfind("}")
        if json_start != -1 and json_end != -1:
            raw_json = output_text[json_start:json_end+1]
            data = json.loads(raw_json)
            actions = [BrowserAction(**act) for act in data.get("actions", [])]
            return ActionPlan(
                intent=data.get("intent", command),
                language=language,
                target_url=data.get("target_url", target_url or settings.MOCK_PORTAL_URL),
                actions=actions,
                parameters=data.get("parameters", {}),
                engine="aws_bedrock",
                explanation=data.get("explanation")
            )
        else:
            raise ValueError("No valid JSON found in Bedrock response")

    def _deterministic_fallback(
        self,
        command: str,
        language: str,
        target_url: Optional[str],
        page_context: Optional[Dict[str, Any]],
        session_id: str
    ) -> ActionPlan:
        """Deterministic reasoning engine for the demonstration workflow and general web actions.

        Explicitly marked with engine='bedrock_fallback'.
        """
        logger.info(f"[BedrockService] Using deterministic vernacular intent parser (engine=bedrock_fallback)")

        cmd = command.lower().strip()
        profile = get_user_profile(session_id)
        effective_url = target_url or settings.MOCK_PORTAL_URL

        # 1. Check for Railway Navigation / Booking intent
        is_railway_intent = any(k in cmd for k in [
            "ರೈಲು", "ಟ್ರೈನ್", "ಹುಡುಕಿ", "ಬುಕ್", "ಬೆಂಗಳೂರು", "ಮೈಸೂರು",
            "ट्रेन", "रेल", "खोजें", "बुक", "बेंगलुरु", "मैसूर",
            "ரயில்", "தேடுங்கள்", "புக்", "பெங்களூரு", "மைசூர்",
            "train", "rail", "book", "search", "bengaluru", "mysuru", "mysore", "ticket"
        ]) or "portal" in effective_url

        if is_railway_intent:
            # Extract source & destination using MCP translation tools
            src_info = standardize_station_name("ಬೆಂಗಳೂರು" if ("ಬೆಂಗಳೂರು" in cmd or "बेंगलुरु" in cmd or "பெங்களூரு" in cmd or "bengaluru" in cmd or "bangalore" in cmd) else profile["home_station"])
            dst_info = standardize_station_name("ಮೈಸೂರು" if ("ಮೈಸೂರು" in cmd or "मैसूर" in cmd or "மைசூர்" in cmd or "mysuru" in cmd or "mysore" in cmd) else "Mysuru Jn (MYS)")
            
            # Date resolution
            date_info = resolve_travel_date("ನಾಳೆ" if ("ನಾಳೆ" in cmd or "कल" in cmd or "நாளை" in cmd or "tomorrow" in cmd) else "tomorrow")
            
            # Class resolution
            class_info = standardize_travel_class("ಸ್ಲೀಪರ್" if ("ಸ್ಲೀಪರ್" in cmd or "स्लीपर" in cmd or "sleeper" in cmd) else "Sleeper (SL)")

            # Vernacular explanations
            explanations = {
                "kn": f"ನಾವು {src_info['name']} ಇಂದ {dst_info['name']} ಗೆ {date_info['formatted']} ದಿನಾಂಕದ {class_info['name']} ರೈಲುಗಳನ್ನು ಹುಡುಕಿ ಬುಕಿಂಗ್ ಪ್ರಕ್ರಿಯೆ ಆರಂಭಿಸುತ್ತಿದ್ದೇವೆ.",
                "hi": f"हम {src_info['name']} से {dst_info['name']} के लिए {date_info['formatted']} की {class_info['name']} ट्रेनों की खोज और बुकिंग प्रक्रिया शुरू कर रहे हैं।",
                "ta": f"நாங்கள் {src_info['name']} லிருந்து {dst_info['name']} க்கு {date_info['formatted']} தேதிக்கான {class_info['name']} ரயில்களைத் தேடி முன்பதிவு செய்கிறோம்.",
                "en": f"Searching and preparing booking for {class_info['name']} trains from {src_info['name']} to {dst_info['name']} on {date_info['formatted']}."
            }

            actions = [
                BrowserAction(
                    id="act_nav",
                    action_type=BrowserActionType.NAVIGATE,
                    selector=effective_url,
                    value=effective_url,
                    reason="Open railway booking portal",
                    explanation={
                        "kn": "ರೈಲ್ವೆ ಬುಕಿಂಗ್ ಪೋರ್ಟಲ್ ತೆರೆಯಲಾಗುತ್ತಿದೆ",
                        "hi": "रेलवे आरक्षण पोर्टल खोला जा रहा है",
                        "ta": "ரயில் முன்பதிவு தளம் திறக்கப்படுகிறது",
                        "en": "Opening railway reservation portal"
                    }.get(language, "Opening railway reservation portal")
                ),
                BrowserAction(
                    id="act_src",
                    action_type=BrowserActionType.FILL,
                    selector="#source-station",
                    aria_label="Source Station",
                    value=src_info["name"],
                    reason=f"Enter source station {src_info['name']}",
                    explanation={
                        "kn": f"ಪ್ರಾರಂಭಿಕ ನಿಲ್ದಾಣ: {src_info['name']} ನಮೂದಿಸಲಾಗುತ್ತಿದೆ",
                        "hi": f"प्रस्थान स्टेशन: {src_info['name']} दर्ज किया जा रहा है",
                        "ta": f"புறப்படும் நிலையம்: {src_info['name']} உள்ளிடப்படுகிறது",
                        "en": f"Entering departure station: {src_info['name']}"
                    }.get(language, f"Entering departure station: {src_info['name']}")
                ),
                BrowserAction(
                    id="act_dst",
                    action_type=BrowserActionType.FILL,
                    selector="#destination-station",
                    aria_label="Destination Station",
                    value=dst_info["name"],
                    reason=f"Enter destination station {dst_info['name']}",
                    explanation={
                        "kn": f"ಗಮ್ಯಸ್ಥಾನ ನಿಲ್ದಾಣ: {dst_info['name']} ನಮೂದಿಸಲಾಗುತ್ತಿದೆ",
                        "hi": f"गंतव्य स्टेशन: {dst_info['name']} दर्ज किया जा रहा है",
                        "ta": f"சேருமிடம் நிலையம்: {dst_info['name']} உள்ளிடப்படுகிறது",
                        "en": f"Entering destination station: {dst_info['name']}"
                    }.get(language, f"Entering destination station: {dst_info['name']}")
                ),
                BrowserAction(
                    id="act_date",
                    action_type=BrowserActionType.FILL,
                    selector="#travel-date",
                    aria_label="Travel Date",
                    value=date_info["date"],
                    reason=f"Select travel date {date_info['date']}",
                    explanation={
                        "kn": f"ಪ್ರಯಾಣದ ದಿನಾಂಕ: {date_info['formatted']} ಆಯ್ಕೆ ಮಾಡಲಾಗುತ್ತಿದೆ",
                        "hi": f"यात्रा तिथि: {date_info['formatted']} चुनी जा रही है",
                        "ta": f"பயண தேதி: {date_info['formatted']} தேர்ந்தெடுக்கப்படுகிறது",
                        "en": f"Setting travel date: {date_info['formatted']}"
                    }.get(language, f"Setting travel date: {date_info['formatted']}")
                ),
                BrowserAction(
                    id="act_class",
                    action_type=BrowserActionType.SELECT,
                    selector="#travel-class",
                    value=class_info["code"],
                    reason=f"Select travel class {class_info['name']}",
                    explanation={
                        "kn": f"ಪ್ರಯಾಣದ ವರ್ಗ: {class_info['name']} ಆಯ್ಕೆ ಮಾಡಲಾಗುತ್ತಿದೆ",
                        "hi": f"यात्रा श्रेणी: {class_info['name']} चुनी जा रही है",
                        "ta": f"பயண வகுப்பு: {class_info['name']} தேர்ந்தெடுக்கப்படுகிறது",
                        "en": f"Selecting travel class: {class_info['name']}"
                    }.get(language, f"Selecting travel class: {class_info['name']}")
                ),
                BrowserAction(
                    id="act_search",
                    action_type=BrowserActionType.CLICK,
                    selector="#search-btn",
                    aria_label="Search Trains",
                    reason="Submit train search form",
                    explanation={
                        "kn": "ರೈಲುಗಳ ಹುಡುಕಾಟ ಬಟನ್ ಒತ್ತಲಾಗುತ್ತಿದೆ",
                        "hi": "ट्रेन खोजें बटन पर क्लिक किया जा रहा है",
                        "ta": "ரயில் தேடல் பொத்தானை அழுத்துகிறது",
                        "en": "Clicking Search Trains button"
                    }.get(language, "Clicking Search Trains button")
                ),
                BrowserAction(
                    id="act_select_train",
                    action_type=BrowserActionType.CLICK,
                    selector="#book-btn-12614",
                    aria_label="Book Tickets on WODEYAR EXPRESS",
                    reason="Select WODEYAR EXPRESS sleeper coach",
                    explanation={
                        "kn": "ವೊಡೆಯರ್ ಎಕ್ಸ್‌ಪ್ರೆಸ್ (12614) ಸ್ಲೀಪರ್ ಕೋಚ್ ಆಯ್ಕೆ ಮಾಡಲಾಗುತ್ತಿದೆ",
                        "hi": "वोडेयार एक्सप्रेस (12614) स्लीपर कोच चुना जा रहा है",
                        "ta": "வொடையார் எக்ஸ்பிரஸ் (12614) ஸ்லீப்பர் பெட்டி தேர்ந்தெடுக்கப்படுகிறது",
                        "en": "Selecting Wodeyar Express (12614) Sleeper class"
                    }.get(language, "Selecting Wodeyar Express (12614) Sleeper class")
                ),
                BrowserAction(
                    id="act_passenger_name",
                    action_type=BrowserActionType.FILL,
                    selector="#passenger-name",
                    aria_label="Primary Passenger Name",
                    value=profile["primary_passenger_name"],
                    reason="Enter primary passenger name",
                    explanation={
                        "kn": f"ಪ್ರಯಾಣಿಕರ ಹೆಸರು: {profile['primary_passenger_name']} ನಮೂದಿಸಲಾಗುತ್ತಿದೆ",
                        "hi": f"यात्री का नाम: {profile['primary_passenger_name']} दर्ज किया जा रहा है",
                        "ta": f"பயணி பெயர்: {profile['primary_passenger_name']} உள்ளிடப்படுகிறது",
                        "en": f"Entering passenger name: {profile['primary_passenger_name']}"
                    }.get(language, f"Entering passenger name: {profile['primary_passenger_name']}")
                ),
                BrowserAction(
                    id="act_confirm_commit",
                    action_type=BrowserActionType.SENSITIVE_COMMIT,
                    selector="#confirm-booking-btn",
                    aria_label="Confirm Booking & Pay ₹145",
                    is_sensitive=True,
                    reason="Final booking and payment authorization (Guarded by Confirm-Before-Commit)",
                    explanation={
                        "kn": "ಗಮನಿಸಿ: ಟಿಕೆಟ್ ದೃಢೀಕರಣ ಮತ್ತು ಪಾವತಿಗಾಗಿ ನಿಮ್ಮ ಒಪ್ಪಿಗೆಯ ಅಗತ್ಯವಿದೆ.",
                        "hi": "सावधानी: टिकट पुष्टि और भुगतान के लिए आपकी अनुमति आवश्यक है।",
                        "ta": "கவனம்: டிக்கெட் உறுதிப்படுத்தல் மற்றும் கட்டணம் செலுத்த உங்கள் ஒப்புதல் தேவை.",
                        "en": "Notice: User approval required before final ticket booking and payment."
                    }.get(language, "User approval required before final ticket booking and payment.")
                )
            ]

            return ActionPlan(
                intent="Railway Ticket Booking & Navigation",
                language=language,
                target_url=effective_url,
                actions=actions,
                parameters={
                    "source": src_info["name"],
                    "destination": dst_info["name"],
                    "date": date_info["date"],
                    "class": class_info["code"],
                    "passenger": profile["primary_passenger_name"]
                },
                engine="bedrock_fallback",
                explanation=explanations.get(language, explanations["en"])
            )

        # 2. General custom website navigation fallback
        return ActionPlan(
            intent=f"Custom Navigation for '{command}'",
            language=language,
            target_url=effective_url,
            actions=[
                BrowserAction(
                    id="act_custom_nav",
                    action_type=BrowserActionType.NAVIGATE,
                    selector=effective_url,
                    value=effective_url,
                    reason=f"Open custom target URL {effective_url}",
                    explanation=f"Navigating to {effective_url}"
                )
            ],
            parameters={"command": command, "url": effective_url},
            engine="bedrock_fallback",
            explanation=f"Navigating to {effective_url} to inspect available options for '{command}'."
        )
