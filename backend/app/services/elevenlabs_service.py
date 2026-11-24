import base64
import logging
from typing import Optional, Dict, Any
import httpx
from backend.app.core.config import settings

logger = logging.getLogger("vaaniweb.elevenlabs")


class ElevenLabsService:
    """ElevenLabs voice synthesis and recognition service for multilingual vernacular voice.

    Supports Kannada, Hindi, Tamil, and English with eleven_multilingual_v2 model.
    Falls back gracefully when credentials are not configured.
    """

    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.voice_id = settings.ELEVENLABS_VOICE_ID or "21m00Tcm4TlvDq8ikWAM"
        self.is_configured = bool(self.api_key and len(self.api_key) > 5)

        if self.is_configured:
            logger.info("ElevenLabs service configured with voice ID: %s", self.voice_id)
        else:
            logger.info("ElevenLabs API key not configured. Web Speech API and text fallback will be active.")

    async def text_to_speech(self, text: str, language: str = "kn") -> Optional[str]:
        """Convert vernacular text to speech using ElevenLabs Multilingual v2 model.

        Returns base64 data URI of the MP3 audio, or None if unconfigured/failed.
        """
        if not self.is_configured:
            return None

        url = f"{self.BASE_URL}/text-to-speech/{self.voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }

        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8,
                "style": 0.2,
                "use_speaker_boost": True
            }
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    audio_bytes = response.content
                    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
                    return f"data:audio/mp3;base64,{b64_audio}"
                else:
                    logger.warning(
                        f"ElevenLabs TTS failed: Status {response.status_code} - {response.text[:200]}"
                    )
                    return None
        except Exception as e:
            logger.error(f"Error calling ElevenLabs TTS: {e}")
            return None

    async def speech_to_text(self, audio_bytes: bytes, language: str = "kn") -> Optional[str]:
        """Convert speech audio bytes to text using ElevenLabs STT API."""
        if not self.is_configured:
            return None

        url = f"{self.BASE_URL}/speech-to-text"
        headers = {
            "xi-api-key": self.api_key
        }

        try:
            files = {
                "file": ("audio.wav", audio_bytes, "audio/wav")
            }
            data = {
                "model_id": "scribe_v1"
            }
            if language in ["kn", "hi", "ta", "en"]:
                data["language_code"] = language

            async with httpx.AsyncClient(timeout=25.0) as client:
                response = await client.post(url, headers=headers, files=files, data=data)
                if response.status_code == 200:
                    result = response.json()
                    return result.get("text")
                else:
                    logger.warning(f"ElevenLabs STT failed: {response.status_code} - {response.text[:200]}")
                    return None
        except Exception as e:
            logger.error(f"Error calling ElevenLabs STT: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        return {
            "configured": self.is_configured,
            "provider": "ElevenLabs" if self.is_configured else "Web Speech API (Fallback)",
            "voice_id": self.voice_id if self.is_configured else "browser_default",
            "model": "eleven_multilingual_v2" if self.is_configured else "native_synthesis"
        }
