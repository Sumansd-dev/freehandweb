import asyncio
import re
import uuid
import logging
from typing import Dict, Any, Optional
from backend.app.models.schemas import BrowserAction, BrowserActionType, SafetyCheckResult

logger = logging.getLogger("vaaniweb.safety")


class SafetyGuardrail:
    """Enforces mandatory backend Confirm-Before-Commit safety controls.

    Interceps sensitive financial commitments, ticket bookings, payment submissions,
    and OTP actions, pausing automation until explicit user approval is received.
    """

    SENSITIVE_KEYWORDS = [
        "confirm booking", "pay", "payment", "book & pay", "purchase", "checkout",
        "confirm & pay", "buy now", "otp", "verify otp", "one time password",
        "credit card", "cvv", "complete booking", "place order", "submit order",
        "ಬುಕ್ ಮಾಡಿ", "ಪಾವತಿಸಿ", "ದೃಢೀಕರಿಸಿ", 
        "भुगतान", "बुक करें", "पुष्टि करें",
        "கட்டணம்", "முன்பதிவு", "உறுதிப்படுத்தவும்"
    ]

    def __init__(self):
        # Maps confirmation_id -> asyncio.Future
        self._pending_confirmations: Dict[str, asyncio.Future] = {}

    def check_action_safety(self, action: BrowserAction, current_url: str = "") -> SafetyCheckResult:
        """Evaluate an action against strict safety guardrails."""
        # 1. Explicit SENSITIVE_COMMIT action type
        if action.action_type == BrowserActionType.SENSITIVE_COMMIT or action.is_sensitive:
            return SafetyCheckResult(
                is_safe=False,
                requires_confirmation=True,
                action_id=action.id,
                reason="Sensitive transaction detected: Ticket booking commitment or payment.",
                risk_level="critical",
                details={
                    "selector": action.selector,
                    "action": action.action_type.value,
                    "reason": action.reason
                }
            )

        # 2. Check selector, aria_label, text, reason against sensitive patterns
        combined_text = f"{action.selector or ''} {action.aria_label or ''} {action.text or ''} {action.reason or ''} {action.value or ''}".lower()

        for kw in self.SENSITIVE_KEYWORDS:
            if kw in combined_text:
                return SafetyCheckResult(
                    is_safe=False,
                    requires_confirmation=True,
                    action_id=action.id,
                    reason=f"Action contains sensitive financial or booking keyword: '{kw}'",
                    risk_level="high",
                    details={
                        "keyword": kw,
                        "selector": action.selector,
                        "action": action.action_type.value
                    }
                )

        # 3. Check for payment/checkout URLs
        if any(u in current_url.lower() for u in ["/checkout", "/payment", "/pay", "/gateway", "/otp"]):
            return SafetyCheckResult(
                is_safe=False,
                requires_confirmation=True,
                action_id=action.id,
                reason="Action is taking place on a sensitive payment or OTP verification page.",
                risk_level="critical",
                details={"url": current_url}
            )

        # Safe action
        return SafetyCheckResult(is_safe=True, requires_confirmation=False)

    def create_confirmation_request(self, action: BrowserAction, explanation: str) -> Dict[str, Any]:
        """Create a pending confirmation ticket that pauses execution."""
        confirmation_id = str(uuid.uuid4())
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._pending_confirmations[confirmation_id] = future

        return {
            "confirmation_id": confirmation_id,
            "action_id": action.id,
            "action_type": action.action_type.value,
            "selector": action.selector,
            "explanation": explanation,
            "future": future
        }

    def resolve_confirmation(self, confirmation_id: str, approved: bool) -> bool:
        """Resolve a pending confirmation by user approval or rejection."""
        if confirmation_id in self._pending_confirmations:
            future = self._pending_confirmations.pop(confirmation_id)
            if not future.done():
                future.set_result(approved)
                logger.info(f"Confirmation {confirmation_id} resolved: approved={approved}")
                return True
        return False

    def cancel_all_pending(self):
        """Cancel all pending confirmation tickets."""
        for cid, future in list(self._pending_confirmations.items()):
            if not future.done():
                future.set_result(False)
        self._pending_confirmations.clear()
