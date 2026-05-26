import base64
import os
from pathlib import Path

from openai import OpenAI

from config import (
    PERPLEXITY_BASE_URL,
    SONAR_MODEL,
    MAX_HISTORY_MESSAGES,
    get_perplexity_api_key,
)
from database import get_messages
from prompt import SYSTEM_PROMPT


SONAR_SYSTEM_ADDITION = """
You have access to real-time web search through Perplexity Sonar.

Use current web information when the user asks about:
- current property prices
- latest real estate market trends
- today's mortgage rates
- recent real estate news
- updated regulations
- fresh statistics
- anything likely to change over time

You may also receive property images.
When an image is provided, use it only as visual context for the real-estate question.
Do not invent exact prices from the image alone.
For current prices, trends, regulations, or market data, rely on web-grounded information.

Stay within the real-estate domain.
Keep answers concise and practical.
Include citations when available.
Do not repeat the same answer multiple times.
"""


def get_sonar_client():
    api_key = get_perplexity_api_key()

    if not api_key:
        raise RuntimeError(
            "Missing PERPLEXITY_API_KEY. Add it to your .env file."
        )

    return OpenAI(
        api_key=api_key,
        base_url=PERPLEXITY_BASE_URL,
    )


def image_to_data_url(image_path):
    suffix = Path(image_path).suffix.lower()

    mime_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(suffix, "image/jpeg")

    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")

    return f"data:{mime_type};base64,{encoded}"


def build_sonar_messages(messages):
    sonar_messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT + "\n\n" + SONAR_SYSTEM_ADDITION,
        }
    ]

    recent_messages = messages[-MAX_HISTORY_MESSAGES:]

    for message in recent_messages:
        role = message["role"]
        content = message.get("content", "")
        image_paths = message.get("image_paths", [])

        if role == "user" and image_paths:
            user_content = [
                {
                    "type": "text",
                    "text": content or "Please use these property images as visual context.",
                }
            ]

            for image_path in image_paths:
                if os.path.exists(image_path):
                    user_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": image_to_data_url(image_path)
                        }
                    })

            sonar_messages.append({
                "role": "user",
                "content": user_content,
            })

        else:
            if content:
                sonar_messages.append({
                    "role": role,
                    "content": content,
                })

    return sonar_messages


def stream_sonar_response(conversation_id):
    client = get_sonar_client()
    messages = get_messages(conversation_id)

    stream = client.chat.completions.create(
        model=SONAR_MODEL,
        messages=build_sonar_messages(messages),
        temperature=0.2,
        stream=True,
    )

    for chunk in stream:
        token = getattr(chunk.choices[0].delta, "content", None)

        if token:
            yield token