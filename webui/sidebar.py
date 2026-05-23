import os

import streamlit as st

from ai_service import ask_assistant
from database import (
    cleanup_empty_conversations,
    delete_conversation,
    get_conversations,
    get_messages,
    set_active_to_latest_chat,
)


def render_sidebar():
    with st.sidebar:
        st.markdown("""
            <div class="assistant-card">
                <h2>AI Assistant</h2>
                <p>Saved property chats.</p>
            </div>
        """, unsafe_allow_html=True)

        if st.button("✎  New chat", use_container_width=True):
            st.session_state.active_conversation_id = None
            st.session_state.open_chat_menu_id = None
            cleanup_empty_conversations()
            st.rerun()

        st.markdown('<div class="sidebar-label">Conversation</div>', unsafe_allow_html=True)
        render_conversation()
        render_chat_input()

        if st.button("Clear chat", use_container_width=True):
            delete_conversation(st.session_state.active_conversation_id)
            set_active_to_latest_chat()
            st.rerun()

        st.markdown('<div class="sidebar-label">Chats</div>', unsafe_allow_html=True)
        render_chat_history()


def render_conversation():
    messages = get_messages(st.session_state.active_conversation_id)

    with st.container(height=215):
        if not messages:
            st.markdown(
                '<div class="empty-chat">Ask about a listing or attach images.</div>',
                unsafe_allow_html=True,
            )
            return

        for message in messages:
            css_class = "user-bubble" if message["role"] == "user" else "assistant-bubble"
            st.markdown(
                f'<div class="{css_class}">{message["content"]}</div>',
                unsafe_allow_html=True,
            )

            for image_path in message.get("image_paths", []):
                if os.path.exists(image_path):
                    st.image(image_path, use_container_width=True)


def render_chat_input():
    with st.form("assistant_chat_form", clear_on_submit=True):
        user_text = st.text_area(
            "Message",
            placeholder="Message AI Assistant...",
            height=68,
            label_visibility="collapsed",
        )

        upload_col, send_col = st.columns(2)

        with upload_col:
            uploaded_images = st.file_uploader(
                "Upload",
                type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=True,
                label_visibility="collapsed",
            )

        with send_col:
            submitted = st.form_submit_button("Send", use_container_width=True)

    if submitted:
        ask_assistant(user_text, uploaded_images)


def render_chat_history():
    conversations = get_conversations()

    with st.container(height=170):
        if not conversations:
            st.info("No saved conversations yet.")
            return

        for conversation_id, title, _ in conversations:
            title = (title.strip() or "New chat")[:28]
            chat_col, menu_col = st.columns([0.82, 0.18])

            with chat_col:
                prefix = "💬  " if conversation_id == st.session_state.active_conversation_id else "   "

                if st.button(prefix + title, key=f"chat_{conversation_id}", use_container_width=True):
                    st.session_state.active_conversation_id = conversation_id
                    st.session_state.open_chat_menu_id = None
                    st.rerun()

            with menu_col:
                if st.button("⋯", key=f"menu_{conversation_id}", use_container_width=True):
                    st.session_state.open_chat_menu_id = (
                        None
                        if st.session_state.open_chat_menu_id == conversation_id
                        else conversation_id
                    )
                    st.rerun()

            if st.session_state.open_chat_menu_id == conversation_id:
                _, delete_col = st.columns([0.18, 0.82])

                with delete_col:
                    if st.button("Delete", key=f"delete_{conversation_id}", use_container_width=True):
                        delete_conversation(conversation_id)

                        if st.session_state.active_conversation_id == conversation_id:
                            set_active_to_latest_chat()
                        else:
                            st.session_state.open_chat_menu_id = None

                        st.rerun()