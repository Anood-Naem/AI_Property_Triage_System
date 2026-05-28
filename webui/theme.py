import streamlit as st

from config import CSS_PATH

try:
    from streamlit_theme import st_theme
except ImportError:
    st_theme = None


def get_theme_base():
    """
    Detect active Streamlit theme from the native menu.
    Important:
    Do not use st.get_option("theme.base"), because it can return the default
    configured theme and ignore the user's current Light/Dark menu choice.
    """

    if st_theme is not None:
        theme = st_theme(key="active_streamlit_theme")

        if isinstance(theme, dict):
            base = str(theme.get("base") or "").lower()

            if base in ("dark", "light"):
                return base

    # Safe default while Streamlit theme component is loading
    return "light"


def apply_theme():
    dark = get_theme_base() == "dark"

    tokens = {
        "{{TEXT}}": "#f8fafc" if dark else "#0f172a",
        "{{SUBTEXT}}": "#cbd5e1" if dark else "#334155",

        # DARK stays exactly close to your good design
        "{{SIDEBAR}}": "#071224" if dark else "rgba(248, 250, 252, 0.96)",
        "{{INPUT_BG}}": "#0b1730" if dark else "rgba(255, 255, 255, 0.96)",
        "{{BORDER}}": "rgba(148, 163, 184, 0.35)" if dark else "rgba(15, 23, 42, 0.18)",

        # DARK unchanged, LIGHT becomes real light while keeping background image visible
        "{{OVERLAY}}": (
            "linear-gradient(rgba(2,6,23,0.88), rgba(2,6,23,0.92))"
            if dark
            else "linear-gradient(rgba(255,255,255,0.78), rgba(255,255,255,0.84))"
        ),
    }

    css = CSS_PATH.read_text(encoding="utf-8")

    for key, value in tokens.items():
        css = css.replace(key, value)

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)