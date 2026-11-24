from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import time


class LanguageCode(str, Enum):
    KANNADA = "kn"
    HINDI = "hi"
    TAMIL = "ta"
    ENGLISH = "en"


class UserCommandRequest(BaseModel):
    text: str = Field(..., description="User voice transcript or text command")
    language: str = Field(default="kn", description="Language code: kn, hi, ta, en")
    session_id: Optional[str] = Field(default=None, description="Active session ID")
    target_url: Optional[str] = Field(default=None, description="Optional custom target website URL")
    audio_base64: Optional[str] = Field(default=None, description="Optional base64 raw audio for STT")


class ConfirmationRequest(BaseModel):
    session_id: str
    confirmation_id: str
    approved: bool
    notes: Optional[str] = None


class BrowserActionType(str, Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    PRESS = "press"
    SCROLL = "scroll"
    WAIT = "wait"
    EXTRACT = "extract"
    SENSITIVE_COMMIT = "sensitive_commit"


class BrowserAction(BaseModel):
    id: str
    action_type: BrowserActionType
    selector: Optional[str] = None
    role: Optional[str] = None
    aria_label: Optional[str] = None
    text: Optional[str] = None
    element_description: Optional[str] = None
    value: Optional[str] = None
    reason: str
    is_sensitive: bool = False
    status: str = "pending"  # pending, executing, success, failed, awaiting_confirmation
    timestamp: float = Field(default_factory=time.time)
    explanation: Optional[str] = None
    verification_rule: Optional[str] = None


class ActionPlan(BaseModel):
    intent: str
    language: str
    target_url: str
    actions: List[BrowserAction] = []
    parameters: Dict[str, Any] = {}
    engine: str = "aws_bedrock"  # "aws_bedrock" or "bedrock_fallback"
    explanation: Optional[str] = None


class ActionLogEvent(BaseModel):
    id: str
    session_id: str
    timestamp: str
    action: str
    element: str
    status: str  # "info", "executing", "success", "failed", "warning", "awaiting_confirmation"
    explanation: str
    screenshot_url: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class SafetyCheckResult(BaseModel):
    is_safe: bool = True
    requires_confirmation: bool = False
    action_id: Optional[str] = None
    reason: str = ""
    risk_level: str = "low"  # low, medium, high, critical
    details: Dict[str, Any] = {}


class BrowserStateSnapshot(BaseModel):
    url: str
    title: str
    status: str  # idle, loading, interacting, paused, ready
    screenshot_base64: Optional[str] = None
    accessibility_tree: Optional[Dict[str, Any]] = None
    semantic_elements: List[Dict[str, Any]] = []
    current_task: Optional[str] = None
