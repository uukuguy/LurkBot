"""Translator Plugin

A simple example plugin that translates text between languages.
"""

from typing import Any


class TranslatorPlugin:
    """Text translator plugin"""

    def __init__(self):
        self.enabled = False
        self.supported_languages = ["en", "zh", "es", "fr", "de", "ja"]

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize plugin"""
        self.config = config
        print(f"Translator plugin initialized with config: {config}")

    async def execute(self, context: dict[str, Any]) -> Any:
        """Execute translation

        Args:
            context: Execution context containing:
                - input_data.text: Text to translate
                - parameters.source_lang: Source language code
                - parameters.target_lang: Target language code

        Returns:
            Translation result dict
        """
        text = context.get("input_data", {}).get("text", "")
        source_lang = context.get("parameters", {}).get("source_lang", "auto")
        target_lang = context.get("parameters", {}).get("target_lang", "en")

        # Mock translation (in real implementation, call translation API)
        if not text:
            return {"error": "No text provided"}

        if target_lang not in self.supported_languages:
            return {"error": f"Unsupported target language: {target_lang}"}

        # Simple mock translation
        translations = {
            "Hello": {"zh": "你好", "es": "Hola", "fr": "Bonjour", "de": "Hallo", "ja": "こんにちは"},
            "Thank you": {"zh": "谢谢", "es": "Gracias", "fr": "Merci", "de": "Danke", "ja": "ありがとう"},
        }

        translated_text = translations.get(text, {}).get(target_lang, f"[Translated: {text}]")

        return {
            "original_text": text,
            "translated_text": translated_text,
            "source_lang": source_lang,
            "target_lang": target_lang,
        }

    async def cleanup(self) -> None:
        """Cleanup resources"""
        print("Translator plugin cleanup")

    async def on_enable(self) -> None:
        """Called when plugin is enabled"""
        self.enabled = True
        print("Translator plugin enabled")

    async def on_disable(self) -> None:
        """Called when plugin is disabled"""
        self.enabled = False
        print("Translator plugin disabled")
