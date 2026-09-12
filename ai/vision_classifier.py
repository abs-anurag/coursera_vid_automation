from __future__ import annotations

from coursera.lesson_detector import LessonType

from utils.logger import get_logger

log = get_logger("vision")

CLASSIFY_PROMPT = """Classify this Coursera course page screenshot.
Reply with JSON only: {"type":"VIDEO|QUIZ|READING|ASSIGNMENT|UNKNOWN","reason":"short"}
Do not answer quiz questions. Only classify the interface."""


class VisionClassifier:
    def __init__(self, api_key: str, model: str, base_url: str):
        self.api_key = api_key
        self.model = model or "gpt-4o-mini"
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")

    async def classify_image(self, image_bytes: bytes) -> LessonType:
        if not self.api_key:
            return LessonType.UNKNOWN
        import base64
        import json

        import httpx

        b64 = base64.b64encode(image_bytes).decode("ascii")
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": CLASSIFY_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"},
                        },
                    ],
                }
            ],
            "max_tokens": 80,
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
            data = json.loads(content[content.find("{") : content.rfind("}") + 1])
            return LessonType(str(data.get("type", "UNKNOWN")).upper())
        except Exception as exc:
            log.warning("Vision classification failed: %s", exc)
            return LessonType.UNKNOWN
