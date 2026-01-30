---
name: image
description: Image understanding, generation, and manipulation using AI vision and DALL-E.
metadata: {"moltbot":{"emoji":"🖼️"}}
---

# Image Tools

Analyze images, generate new images, and perform basic image manipulations.

## Available Tool

- `image` - Multi-operation image tool supporting understand, generate, and resize

## Operations

### 1. Understand (analyze images)

```bash
{
  "op": "understand",
  "path": "/path/to/image.jpg",  # or "url" or "base64"
  "prompt": "Describe this image in detail",
  "extractText": false  # OCR if true
}
```

### 2. Generate (create images)

```bash
{
  "op": "generate",
  "prompt": "A serene lake at sunset with mountains",
  "model": "dall-e-3",  # or "dall-e-2"
  "size": "1024x1024",  # or "1792x1024", "1024x1792"
  "quality": "hd",  # or "standard"
  "style": "vivid",  # or "natural"
  "n": 1
}
```

### 3. Resize (modify images)

```bash
{
  "op": "resize",
  "path": "/path/to/image.jpg",
  "width": 800,
  "height": 600,
  "format": "png",  # or "jpeg", "webp"
  "quality": 85  # for JPEG
}
```

## Use Cases

**Image analysis**: Describe images, extract information, identify objects.

**OCR**: Extract text from images (set `extractText: true`).

**Content generation**: Create images from text descriptions.

**Image optimization**: Resize and convert images for web or storage.

**Visual understanding**: Analyze charts, diagrams, screenshots.

## Configuration

Requires API keys for:
- **OpenAI** - For DALL-E image generation and GPT-4V understanding
- Or other vision/generation providers

## Tips

- For understanding, provide specific prompts for better analysis
- DALL-E 3 provides higher quality than DALL-E 2
- Use "hd" quality for detailed images (costs more)
- Resize before uploading large images to save bandwidth
- OCR works best with clear, high-contrast text

## Related Skills

- `messaging` - Send generated images to channels
- `web` - Fetch images from URLs for analysis
