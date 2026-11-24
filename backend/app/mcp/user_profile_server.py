import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from mcp.server.mcpserver import MCPServer

logger = logging.getLogger("vaaniweb.mcp.user_profile")

# In-memory session store for user preferences (safe non-sensitive information)
_USER_PROFILES: Dict[str, Dict[str, Any]] = {
    "default": {
        "preferred_language": "kn",
        "primary_passenger_name": "Ramesh Kumar",
        "primary_passenger_age": 32,
        "primary_passenger_gender": "Male",
        "home_station": "Bengaluru City (SBC)",
        "preferred_travel_class": "Sleeper (SL)"
    }
}

# Create MCP server instance
profile_mcp_server = MCPServer("vaaniweb-user-profile-translation-server")


@profile_mcp_server.tool()
def get_user_profile(session_id: str = "default") -> Dict[str, Any]:
    """Retrieve safe user preferences and profile parameters for the active session.

    Never returns sensitive credentials, OTPs, or passwords.
    """
    profile = _USER_PROFILES.get(session_id, _USER_PROFILES["default"]).copy()
    logger.info(f"[MCP] get_user_profile for {session_id}: {profile}")
    return profile


@profile_mcp_server.tool()
def update_user_preference(key: str, value: str, session_id: str = "default") -> str:
    """Update a safe user preference attribute (e.g.

    preferred_language, home_station).
    Sensitive keys like password or payment details are strictly rejected.
    """
    prohibited = ["password", "otp", "token", "cvv", "card", "secret", "pin"]
    if any(p in key.lower() for p in prohibited):
        raise ValueError(f"Security restriction: '{key}' cannot be stored in User Profile MCP.")

    if session_id not in _USER_PROFILES:
        _USER_PROFILES[session_id] = _USER_PROFILES["default"].copy()

    _USER_PROFILES[session_id][key] = value
    logger.info(f"[MCP] update_user_preference: session={session_id}, {key}={value}")
    return f"Successfully updated {key} to {value}"


@profile_mcp_server.tool()
def standardize_station_name(vernacular_name: str) -> Dict[str, Any]:
    """Map vernacular or regional station names across Kannada, Hindi, Tamil, and English

    to standard Indian Railway codes and full station names.
    """
    v = vernacular_name.strip().lower()

    # Station mappings
    station_lookup = [
        (["ಬೆಂಗಳೂರು", "ಬೆಂಗಳೂರು ಸಿಟಿ", "ಬೆಂಗಳೂರು ನಗರ", "ಬೆಂಗಳೂರಿಗೆ", "ಬೆಂಗಳೂರಿನಿಂದ", "बेंगलुरु", "बैंगलोर", "பெங்களூரு", "பெங்களூர்", "bangalore", "bengaluru", "sbc"], 
         {"code": "SBC", "name": "Bengaluru City (SBC)", "city": "Bengaluru"}),
        
        (["ಮೈಸೂರು", "ಮೈಸೂರಿಗೆ", "ಮೈಸೂರಿನಿಂದ", "ಮೈಸೂರು ಜಂಕ್ಷನ್", "मैसूर", "मैसूरु", "மைசூர்", "மைசூருக்கு", "mysore", "mysuru", "mys"], 
         {"code": "MYS", "name": "Mysuru Jn (MYS)", "city": "Mysuru"}),
        
        (["ಚೆನ್ನೈ", "ಚೆನ್ನೈಗೆ", "ಚೆನ್ನೈ ಸೆಂಟ್ರಲ್", "चेन्नई", "சென்னை", "chennai", "madras", "mas"], 
         {"code": "MAS", "name": "Chennai Central (MAS)", "city": "Chennai"}),
        
        (["ದೆಹಲಿ", "ಹೊಸ ದೆಹಲಿ", "दिल्ली", "नई दिल्ली", "டெல்லி", "delhi", "new delhi", "ndls"], 
         {"code": "NDLS", "name": "New Delhi (NDLS)", "city": "New Delhi"}),
        
        (["ಮುಂಬೈ", "मुंबई", "மும்பை", "mumbai", "bombay", "csmt"], 
         {"code": "CSMT", "name": "Mumbai CSMT (CSMT)", "city": "Mumbai"}),
         
        (["ಹೈದರಾಬಾದ್", "हैदराबाद", "ஹைதராபாத்", "hyderabad", "secunderabad", "hyb"], 
         {"code": "HYB", "name": "Hyderabad Deccan (HYB)", "city": "Hyderabad"}),
         
        (["ಹುಬ್ಬಳ್ಳಿ", "ಹುಬ್ಬಳ್ಳಿಗೆ", "हुबली", "ஹுப்ளி", "hubli", "hubballi", "ubl"], 
         {"code": "UBL", "name": "Hubballi Jn (UBL)", "city": "Hubballi"})
    ]

    for aliases, data in station_lookup:
        for alias in aliases:
            if alias in v or v in alias:
                return data

    return {"code": "UNKNOWN", "name": vernacular_name.strip(), "city": vernacular_name.strip()}


@profile_mcp_server.tool()
def standardize_travel_class(vernacular_class: str) -> Dict[str, Any]:
    """Map vernacular travel class references into standardized railway codes."""
    c = vernacular_class.strip().lower()

    if any(k in c for k in ["ಸ್ಲೀಪರ್", "स्लीपर", "தூங்கும்", "sleeper", "sl"]):
        return {"code": "SL", "name": "Sleeper (SL)", "tag": "Sleeper"}
    elif any(k in c for k in ["ಚೇರ್", "chair", "சேர்", "चेयर", "cc"]):
        return {"code": "CC", "name": "AC Chair Car (CC)", "tag": "Chair Car"}
    elif any(k in c for k in ["3ಎಸಿ", "3 ಎಸಿ", "3ac", "3 tier", "थर्ड", "மூன்றாம்", "3a"]):
        return {"code": "3A", "name": "AC 3 Tier (3A)", "tag": "AC 3 Tier"}
    elif any(k in c for k in ["2ಎಸಿ", "2 ಎಸಿ", "2ac", "2 tier", "सेकंड", "இரண்டாம்", "2a"]):
        return {"code": "2A", "name": "AC 2 Tier (2A)", "tag": "AC 2 Tier"}
    elif any(k in c for k in ["1ಎಸಿ", "first ac", "1st ac", "முதல்"]):
        return {"code": "1A", "name": "AC First Class (1A)", "tag": "First AC"}
    elif any(k in c for k in ["2s", "second sitting", "ಸಾಮಾನ್ಯ"]):
        return {"code": "2S", "name": "Second Sitting (2S)", "tag": "Second Sitting"}

    return {"code": "SL", "name": "Sleeper (SL)", "tag": "Default"}


@profile_mcp_server.tool()
def resolve_travel_date(date_expression: str) -> Dict[str, Any]:
    """Convert relative vernacular time expressions (tomorrow, day after tomorrow)

    into formatted ISO dates (YYYY-MM-DD).
    """
    expr = date_expression.strip().lower()
    today = datetime.now()

    if any(k in expr for k in ["ನಾಳೆ", "ನಾಳೆಯ", "ನಾಳಿನ", "कल", "நாளை", "tomorrow"]):
        target = today + timedelta(days=1)
        return {
            "date": target.strftime("%Y-%m-%d"),
            "relative": "tomorrow",
            "formatted": target.strftime("%d %b %Y")
        }
    elif any(k in expr for k in ["ನಾಡಿದ್ದು", "परसों", "நாளை மறுநாள்", "day after tomorrow"]):
        target = today + timedelta(days=2)
        return {
            "date": target.strftime("%Y-%m-%d"),
            "relative": "day_after_tomorrow",
            "formatted": target.strftime("%d %b %Y")
        }
    elif any(k in expr for k in ["ಇಂದು", "ಇವತ್ತು", "आज", "இன்று", "today"]):
        return {
            "date": today.strftime("%Y-%m-%d"),
            "relative": "today",
            "formatted": today.strftime("%d %b %Y")
        }
    
    # Check if already YYYY-MM-DD
    try:
        parsed = datetime.strptime(expr, "%Y-%m-%d")
        return {
            "date": parsed.strftime("%Y-%m-%d"),
            "relative": "exact",
            "formatted": parsed.strftime("%d %b %Y")
        }
    except Exception:
        # Default to tomorrow
        fallback = today + timedelta(days=1)
        return {
            "date": fallback.strftime("%Y-%m-%d"),
            "relative": "tomorrow_default",
            "formatted": fallback.strftime("%d %b %Y")
        }
