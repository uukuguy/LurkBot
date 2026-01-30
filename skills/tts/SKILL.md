---
name: tts
description: Convert text to speech with multiple providers including OpenAI, ElevenLabs, and Edge TTS.
metadata: {"moltbot":{"emoji":"🔊"}}
---

# Text-to-Speech

Generate natural-sounding speech from text using various TTS providers.

## Available Tool

- `tts` - Multi-provider text-to-speech synthesis

## Operations

### 1. Speak (generate audio)

```bash
{
  "op": "speak",
  "text": "Hello, this is a test message",
  "voice": "alloy",  # provider-specific voice ID
  "provider": "openai",  # openai, elevenlabs, edge, local
  "speed": 1.0,  # 0.25 to 4.0
  "pitch": 0,  # -20 to +20 semitones
  "outputFormat": "mp3",  # mp3, wav, ogg, opus
  "outputPath": "/tmp/speech.mp3"  # optional
}
```

### 2. List available voices

```bash
{
  "op": "voices",
  "provider": "openai"  # optional filter
}
```

### 3. List available providers

```bash
{
  "op": "providers"
}
```

### 4. Parse TTS directives

```bash
{
  "op": "parse",
  "inputText": "Hello [[tts:world]] from bot"
}
```

Extracts embedded `[[tts:...]]` directives from text.

## Supported Providers

### OpenAI TTS
- High-quality neural voices
- Voices: alloy, echo, fable, onyx, nova, shimmer
- Supports speed control
- Output formats: mp3, opus, aac, flac

### ElevenLabs
- Ultra-realistic voices
- Voice cloning support
- Multiple languages
- Premium quality (requires subscription)

### Edge TTS (free)
- Microsoft Azure voices
- Many languages and voices
- No API key required
- Good quality

### Local
- Offline synthesis
- Privacy-friendly
- Lower quality
- Fast generation

## Use Cases

**Voice responses**: Generate speech for voice channels.

**Accessibility**: Provide audio version of text content.

**Notifications**: Speak alerts or status updates.

**Multilingual**: Generate speech in different languages.

**Content creation**: Create audio content from text.

## Configuration

Provider-specific API keys required:
- **OpenAI**: `OPENAI_API_KEY`
- **ElevenLabs**: `ELEVENLABS_API_KEY`
- **Edge TTS**: No key needed (free)

## TTS Directives

Moltbot uses `[[tts:text]]` directives in responses:

```
Response: The task is complete [[tts:Task completed successfully]]
```

The text inside `[[tts:...]]` will be spoken.

## Tips

- Use natural, conversational text for better results
- Adjust speed for clarity (0.9-1.1 is natural range)
- Choose appropriate voice for content type
- Use mp3 for small file size, wav for quality
- Test voices before using in production
- Edge TTS is great for development (free, no key)

## Related Skills

- `messaging` - Send audio messages to channels
- `sessions` - Generate speech in subagent responses
