import streamlit as st

from database import init_db, cleanup_empty_conversations, set_active_to_latest_chat
from theme import apply_theme
from sidebar import render_sidebar
from main_form import render_main_form


st.set_page_config(
    page_title="AI Property Triage System",
    layout="wide",
    initial_sidebar_state="expanded",
)


init_db()
cleanup_empty_conversations()

if "active_conversation_id" not in st.session_state:
    st.session_state.active_conversation_id = None

if "open_chat_menu_id" not in st.session_state:
    st.session_state.open_chat_menu_id = None

apply_theme()
render_sidebar()
render_main_form()