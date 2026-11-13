"""Inject the shared CSS theme into the Streamlit page."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

_CSS_PATH = Path(__file__).parent / "style.css"


def inject() -> None:
    """Read tracker/style.css and inject it into the Streamlit page."""
    css = _CSS_PATH.read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
