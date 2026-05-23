import base64
import os
import uuid
from pathlib import Path

import streamlit as st
from groq import Groq

from config import (
    UPLOAD_DIR,
    GROQ_TEXT_MODEL,
    GROQ_VISION_MODEL,
    MAX_HISTORY_MESSAGES,
    get_groq_api_key,
)
from database import ensure_conversation, add_message, get_messages
from prompt import SYSTEM_PROMPT


def save_images(files):
    paths = []

    for file in files or []:
        file_name = f"{uuid.uuid4()}_{file.name.replace(' ', '_')}"
        file_path = UPLOAD_DIR / file_name

        with open(file_path, "wb") as f:
            f.write(file.getbuffer())

        paths.append(str(file_path))

    return paths


def get_groq_client():
    api_key = get_groq_api_key()

    if not api_key:
        raise RuntimeError(
            "Missing GROQ_API_KEY. Add it to your .env file."
        )

    return Groq(api_key=api_key)


def image_to_data_url(image_path):
    suffix = Path(image_path).suffix.lower()

    mime_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(suffix, "image/jpeg")

    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")

    return f"data:{mime_type};base64,{encoded}"


def build_groq_messages(messages):
    groq_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    recent_messages = messages[-MAX_HISTORY_MESSAGES:]
    used_images_count = 0

    for message in recent_messages:
        role = message["role"]
        content = message["content"]
        image_paths = message.get("image_paths", [])

        if role == "user" and image_paths and used_images_count < 5:
            user_content = [{"type": "text", "text": content}]

            for image_path in image_paths:
                if used_images_count >= 5:
                    break

                if os.path.exists(image_path):
                    user_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": image_to_data_url(image_path)
                        }
                    })
                    used_images_count += 1

            groq_messages.append({
                "role": "user",
                "content": user_content
            })

        else:
            groq_messages.append({
                "role": role,
                "content": content
            })

    return groq_messages


def conversation_has_images(messages):
    return any(message.get("image_paths") for message in messages)


def stream_groq_response(conversation_id):
    client = get_groq_client()
    messages = get_messages(conversation_id)

    model = GROQ_VISION_MODEL if conversation_has_images(messages) else GROQ_TEXT_MODEL

    stream = client.chat.completions.create(
        model=model,
        messages=build_groq_messages(messages),
        temperature=0.3,
        max_completion_tokens=900,
        top_p=1,
        stream=True,
    )

    for chunk in stream:
        token = chunk.choices[0].delta.content

        if token:
            yield token


def ask_assistant(user_text, uploaded_images):
    image_paths = save_images(uploaded_images)
    user_text = user_text.strip()

    if not user_text and not image_paths:
        st.warning("Please write a message or upload an image.")
        return

    if not user_text:
        user_text = "Please analyze these property images."

    conversation_id = ensure_conversation()
    add_message(conversation_id, "user", user_text, image_paths)

    try:
        response_placeholder = st.empty()
        full_response = ""

        for token in stream_groq_response(conversation_id):
            full_response += token
            response_placeholder.markdown(
                f'<div class="assistant-bubble">{full_response}</div>',
                unsafe_allow_html=True,
            )

        add_message(conversation_id, "assistant", full_response)
        st.rerun()

    except Exception as error:
        st.error(f"Assistant error: {error}")