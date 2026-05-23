import json
import sqlite3
import uuid
from datetime import datetime

import streamlit as st

from config import DB_PATH


def connect_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                image_paths TEXT,
                created_at TEXT NOT NULL
            )
        """)


def cleanup_empty_conversations():
    with connect_db() as conn:
        conn.execute("""
            DELETE FROM conversations
            WHERE id NOT IN (SELECT DISTINCT conversation_id FROM messages)
        """)


def create_conversation(title="New chat"):
    conversation_id = str(uuid.uuid4())
    now = datetime.now().isoformat(timespec="seconds")

    with connect_db() as conn:
        conn.execute(
            "INSERT INTO conversations VALUES (?, ?, ?, ?)",
            (conversation_id, title, now, now),
        )

    return conversation_id


def ensure_conversation():
    if st.session_state.active_conversation_id is None:
        st.session_state.active_conversation_id = create_conversation()

    return st.session_state.active_conversation_id


def get_conversations():
    cleanup_empty_conversations()

    with connect_db() as conn:
        return conn.execute("""
            SELECT id, title, updated_at
            FROM conversations
            ORDER BY updated_at DESC
        """).fetchall()


def get_messages(conversation_id):
    if not conversation_id:
        return []

    with connect_db() as conn:
        rows = conn.execute("""
            SELECT role, content, image_paths
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
        """, (conversation_id,)).fetchall()

    return [
        {
            "role": role,
            "content": content,
            "image_paths": json.loads(image_paths or "[]"),
        }
        for role, content, image_paths in rows
    ]


def add_message(conversation_id, role, content, image_paths=None):
    now = datetime.now().isoformat(timespec="seconds")
    image_paths = image_paths or []

    with connect_db() as conn:
        conn.execute(
            "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                conversation_id,
                role,
                content,
                json.dumps(image_paths),
                now,
            ),
        )

        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )

        if role == "user":
            current_title = conn.execute(
                "SELECT title FROM conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()[0]

            if current_title == "New chat":
                title = content.strip()[:34] if content.strip() else "Image chat"
                conn.execute(
                    "UPDATE conversations SET title = ? WHERE id = ?",
                    (title, conversation_id),
                )


def delete_conversation(conversation_id):
    if not conversation_id:
        return

    with connect_db() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))


def set_active_to_latest_chat():
    conversations = get_conversations()
    st.session_state.active_conversation_id = conversations[0][0] if conversations else None
    st.session_state.open_chat_menu_id = None