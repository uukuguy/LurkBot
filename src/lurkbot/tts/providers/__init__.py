"""TTS providers package.

Provides implementations for multiple TTS backends:
- OpenAI TTS (gpt-4o-mini-tts, tts-1, tts-1-hd)
- ElevenLabs TTS
- Edge TTS (free, no API key required)
"""

from lurkbot.tts.providers.base import TtsProviderBase, TtsProviderResult
from lurkbot.tts.providers.edge import EdgeTtsProvider
from lurkbot.tts.providers.elevenlabs import ElevenLabsTtsProvider
from lurkbot.tts.providers.openai import OpenAITtsProvider

__all__ = [
    "TtsProviderBase",
    "TtsProviderResult",
    "OpenAITtsProvider",
    "ElevenLabsTtsProvider",
    "EdgeTtsProvider",
]