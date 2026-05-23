import streamlit as st

from config import CSS_PATH

try:
    from streamlit_theme import st_theme
except ImportError:
    st_theme = None


def get_theme_base():
    if st_theme is not None:
        theme = st_theme(key="active_streamlit_theme")

        if isinstance(theme, dict):
            base = str(
                theme.get("base")
                or theme.get("type")
                or theme.get("theme")
                or ""
            ).lower()

            if base in ("dark", "light"):
                return base

    try:
        context_theme = getattr(st.context, "theme", None)

        if isinstance(context_theme, dict):
            base = str(context_theme.get("type") or context_theme.get("base") or "").lower()
        else:
            base = str(
                getattr(context_theme, "type", "")
                or getattr(context_theme, "base", "")
            ).lower()

        if base in ("dark", "light"):
            return base

    except Exception:
        pass

    try:
        configured_theme = str(st.get_option("theme.base") or "").lower()

        if configured_theme in ("dark", "light"):
            return configured_theme

    except Exception:
        pass

    return "light"


def apply_theme():
    dark = get_theme_base() == "dark"

    tokens = {
        "{{TEXT}}": "#f8fafc" if dark else "#0f172a",
        "{{SUBTEXT}}": "#cbd5e1" if dark else "#64748b",
        "{{SIDEBAR}}": "#071224" if dark else "#eef2f7",
        "{{INPUT_BG}}": "#0b1730" if dark else "#ffffff",
        "{{BORDER}}": "rgba(148, 163, 184, 0.35)",
        "{{OVERLAY}}": (
            "linear-gradient(rgba(2,6,23,0.88), rgba(2,6,23,0.92))"
            if dark
            else "linear-gradient(rgba(255,255,255,0.78), rgba(255,255,255,0.82))"
        ),
    }

    css = CSS_PATH.read_text(encoding="utf-8")

    for key, value in tokens.items():
        css = css.replace(key, value)

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)