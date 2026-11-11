"""Shared visual system for EduPath's Streamlit application."""

from html import escape

import streamlit as st


_THEME_CSS = """
:root {
    --edupath-ink: #17233a;
    --edupath-muted: #68758b;
    --edupath-primary: #425fe3;
    --edupath-primary-dark: #304bc4;
    --edupath-border: #e5eaf2;
    --edupath-surface: #ffffff;
    --edupath-canvas: #f5f7fb;
}

.stApp {
    background: var(--edupath-canvas);
    color: var(--edupath-ink);
}

[data-testid="stHeader"] {
    background: rgba(245, 247, 251, 0.88);
}

[data-testid="stToolbar"] {
    right: 1.5rem;
}

.block-container {
    max-width: 1420px;
    padding: 2.1rem 2.8rem 3.5rem;
}

h1, h2, h3, h4 {
    color: var(--edupath-ink);
    letter-spacing: -0.035em;
    font-weight: 700;
}

h1 {
    font-size: clamp(1.9rem, 3vw, 2.45rem);
    line-height: 1.15;
}

h2 {
    font-size: 1.55rem;
}

h3 {
    font-size: 1.15rem;
}

p, li, label, [data-testid="stMarkdownContainer"] {
    line-height: 1.62;
}

[data-testid="stCaptionContainer"] {
    color: var(--edupath-muted);
}

/* Sidebar */
[data-testid="stSidebar"] > div:first-child {
    background: linear-gradient(180deg, #111d35 0%, #172744 100%);
    border-right: 1px solid rgba(255, 255, 255, 0.06);
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: #c5d0e3;
}

[data-testid="stSidebar"] a {
    color: #b7c6ff !important;
    text-decoration: none;
}

[data-testid="stSidebar"] a:hover {
    color: #ffffff !important;
    text-decoration: underline;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #ffffff;
}

[data-testid="stSidebar"] hr {
    border-color: rgba(226, 232, 240, 0.15);
}

[data-testid="stSidebar"] [data-testid="stRadio"] > label {
    color: #dce5f3;
    font-weight: 650;
    font-size: 0.78rem;
    letter-spacing: 0.09em;
    text-transform: uppercase;
}

[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {
    display: flex;
    flex-direction: column;
    gap: 0.42rem;
}

[data-testid="stSidebar"] [data-testid="stRadio"] [data-baseweb="radio"] {
    display: none !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label {
    display: flex;
    align-items: center;
    box-sizing: border-box;
    width: 100%;
    min-height: 2.65rem;
    margin: 0;
    padding: 0.58rem 0.82rem;
    border: 1px solid transparent;
    border-radius: 11px;
    color: #dce5f3;
    background: transparent;
    font-weight: 560;
    transition: background 140ms ease, border-color 140ms ease, color 140ms ease;
}

[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label p {
    margin: 0;
    color: inherit;
    line-height: 1.35;
}

[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label:hover {
    background: rgba(255, 255, 255, 0.09);
    border-color: rgba(205, 216, 255, 0.13);
}

[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {
    background: rgba(111, 139, 255, 0.22);
    border-color: rgba(158, 177, 255, 0.36);
    color: #ffffff;
    font-weight: 680;
}

.edupath-sidebar-brand {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.45rem 0 0.65rem;
}

.edupath-brand-mark {
    display: grid;
    place-items: center;
    width: 2.55rem;
    height: 2.55rem;
    flex: 0 0 2.55rem;
    border-radius: 12px;
    color: #ffffff;
    background: linear-gradient(135deg, #6f86ff, #4058d9);
    font-size: 1.25rem;
    font-weight: 800;
    box-shadow: 0 8px 22px rgba(48, 75, 196, 0.28);
}

.edupath-sidebar-name {
    color: #ffffff;
    font-size: 1.2rem;
    line-height: 1.15;
    font-weight: 750;
    letter-spacing: -0.035em;
}

.edupath-sidebar-subtitle {
    margin-top: 0.23rem;
    color: #aebbd1;
    font-size: 0.68rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

/* Page headings and dashboard hero */
.edupath-page-header {
    margin: 0.1rem 0 1.6rem;
}

.edupath-eyebrow {
    margin-bottom: 0.42rem;
    color: var(--edupath-primary);
    font-size: 0.70rem;
    font-weight: 800;
    letter-spacing: 0.13em;
    text-transform: uppercase;
}

.edupath-page-title {
    margin: 0;
    color: var(--edupath-ink);
    font-size: clamp(1.9rem, 3vw, 2.5rem);
    line-height: 1.12;
    font-weight: 760;
    letter-spacing: -0.045em;
}

.edupath-page-description {
    max-width: 760px;
    margin-top: 0.65rem;
    color: var(--edupath-muted);
    font-size: 1rem;
    line-height: 1.65;
}

.edupath-dashboard-hero {
    position: relative;
    overflow: hidden;
    padding: 1.65rem 1.8rem;
    border: 1px solid #dce4ff;
    border-radius: 20px;
    background:
        radial-gradient(circle at 92% 10%, rgba(126, 151, 255, 0.20), transparent 32%),
        linear-gradient(135deg, #ffffff 0%, #f0f4ff 100%);
}

.edupath-dashboard-hero .eyebrow {
    color: var(--edupath-primary);
    font-size: 0.68rem;
    font-weight: 800;
    letter-spacing: 0.13em;
    text-transform: uppercase;
}

.edupath-dashboard-hero h2 {
    max-width: 720px;
    margin: 0.55rem 0;
    color: #17233a;
    font-size: clamp(1.45rem, 2.5vw, 2rem);
    line-height: 1.22;
    letter-spacing: -0.04em;
}

.edupath-dashboard-hero p {
    max-width: 680px;
    margin: 0;
    color: #5e6b82;
}

.edupath-hero-stats {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    margin-top: 1.15rem;
}

.edupath-hero-stat {
    padding: 0.42rem 0.7rem;
    border: 1px solid #dfe6fa;
    border-radius: 999px;
    color: #43516b;
    background: rgba(255, 255, 255, 0.78);
    font-size: 0.78rem;
    font-weight: 650;
}

.edupath-login-wrap {
    padding: 2.1rem 1.7rem 2.1rem 0.4rem;
}

.edupath-login-kicker {
    margin-bottom: 1rem;
    color: var(--edupath-primary);
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    font-weight: 800;
    text-transform: uppercase;
}

.edupath-login-title {
    max-width: 620px;
    margin: 0;
    color: #17233a;
    font-size: clamp(2.35rem, 5vw, 3.7rem);
    line-height: 1.06;
    font-weight: 790;
    letter-spacing: -0.055em;
}

.edupath-login-copy {
    max-width: 560px;
    margin-top: 1.1rem;
    color: #64728a;
    font-size: 1.05rem;
    line-height: 1.75;
}

.edupath-login-points {
    display: flex;
    flex-wrap: wrap;
    gap: 0.55rem;
    margin-top: 1.6rem;
}

.edupath-login-points span {
    padding: 0.48rem 0.72rem;
    border: 1px solid #e1e7f2;
    border-radius: 999px;
    color: #42516a;
    background: #ffffff;
    font-size: 0.78rem;
    font-weight: 650;
}

/* Cards, metrics and expanders */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid var(--edupath-border) !important;
    border-radius: 16px !important;
    background: var(--edupath-surface);
    box-shadow: 0 5px 18px rgba(25, 42, 75, 0.035);
}

[data-testid="stMetric"] {
    min-height: 104px;
    padding: 1rem 1.05rem;
    border: 1px solid var(--edupath-border);
    border-radius: 14px;
    background: #ffffff;
}

[data-testid="stMetricLabel"] {
    color: #68758b;
    font-size: 0.80rem;
    font-weight: 650;
}

[data-testid="stMetricValue"] {
    color: #17233a;
    font-weight: 760;
    letter-spacing: -0.035em;
}

[data-testid="stExpander"] {
    border: 1px solid var(--edupath-border);
    border-radius: 13px;
    background: #ffffff;
}

[data-testid="stExpander"] summary {
    font-weight: 650;
}

/* Buttons: one consistent hierarchy and accessible contrast */
.stButton > button,
.stFormSubmitButton > button,
[data-testid="stDownloadButton"] > button,
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-primary"] {
    min-height: 2.7rem;
    padding: 0.48rem 1rem;
    border: 1px solid #d5deed;
    border-radius: 11px;
    color: #263650 !important;
    background: #ffffff !important;
    font-weight: 650;
    box-shadow: 0 1px 2px rgba(23, 35, 58, 0.04);
    transition: background 140ms ease, color 140ms ease, border-color 140ms ease,
        box-shadow 140ms ease, transform 140ms ease;
}

.stButton > button:hover:not(:disabled),
.stFormSubmitButton > button:hover:not(:disabled),
[data-testid="stDownloadButton"] > button:hover:not(:disabled),
[data-testid="stBaseButton-secondary"]:hover:not(:disabled) {
    border-color: #9bacef !important;
    color: #304bc4 !important;
    background: #f4f6ff !important;
    box-shadow: 0 4px 12px rgba(48, 75, 196, 0.09);
    transform: translateY(-1px);
}

.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    border: 1px solid #405bd7 !important;
    color: #ffffff !important;
    background: linear-gradient(135deg, #526de9 0%, #3d57d5 100%) !important;
    box-shadow: 0 5px 13px rgba(66, 95, 227, 0.22);
}

.stButton > button[kind="primary"]:hover:not(:disabled),
.stFormSubmitButton > button[kind="primary"]:hover:not(:disabled),
[data-testid="stBaseButton-primary"]:hover:not(:disabled) {
    border-color: #2f47bb !important;
    color: #ffffff !important;
    background: #304bc4 !important;
    box-shadow: 0 6px 15px rgba(48, 75, 196, 0.24);
}

.stButton > button:focus-visible,
.stFormSubmitButton > button:focus-visible,
[data-testid="stBaseButton-secondary"]:focus-visible,
[data-testid="stBaseButton-primary"]:focus-visible {
    outline: 3px solid rgba(82, 109, 233, 0.28) !important;
    outline-offset: 2px;
}

.stButton > button:disabled,
.stFormSubmitButton > button:disabled,
[data-testid="stBaseButton-secondary"]:disabled,
[data-testid="stBaseButton-primary"]:disabled {
    opacity: 1 !important;
    border-color: #e0e6ef !important;
    color: #718096 !important;
    background: #edf1f7 !important;
    box-shadow: none !important;
    transform: none !important;
    cursor: not-allowed;
}

/* Form controls */
[data-baseweb="input"] > div,
[data-baseweb="textarea"] > div,
[data-baseweb="select"] > div {
    border-color: #dce3ef;
    border-radius: 10px;
    background: #ffffff;
}

[data-baseweb="input"] > div:focus-within,
[data-baseweb="textarea"] > div:focus-within,
[data-baseweb="select"] > div:focus-within {
    border-color: #788df0;
    box-shadow: 0 0 0 1px #788df0;
}

[data-testid="stFileUploader"] section {
    border: 1px dashed #bdc9df;
    border-radius: 13px;
    background: #fafbfe;
}

/* Feedback and data surfaces */
[data-testid="stAlert"] {
    border-radius: 12px;
}

[data-testid="stDataFrame"],
[data-testid="stTable"] {
    border: 1px solid var(--edupath-border);
    border-radius: 12px;
    overflow: hidden;
}

[data-testid="stChatMessage"] {
    border: 1px solid #e7ebf3;
    border-radius: 15px;
    background: #ffffff;
    padding: 0.9rem 1rem;
}

[data-testid="stChatInput"] {
    border-color: #dce3ef;
    border-radius: 14px;
    box-shadow: 0 5px 16px rgba(25, 42, 75, 0.045);
}

.stProgress > div > div > div > div {
    background: linear-gradient(90deg, #536fe9, #7c91f3);
    border-radius: 999px;
}

hr {
    border-color: #e8edf4;
}

/* Responsive spacing */
@media (max-width: 900px) {
    .block-container {
        padding: 1.5rem 1.15rem 2.5rem;
    }

    .edupath-login-wrap {
        padding: 0.8rem 0 1.2rem;
    }

    .edupath-dashboard-hero {
        padding: 1.35rem;
        border-radius: 16px;
    }
}
"""


def apply_theme() -> None:
    """Apply the shared EduPath visual system to the current Streamlit page."""

    st.markdown(f"<style>{_THEME_CSS}</style>", unsafe_allow_html=True)


def render_page_header(
    eyebrow: str,
    title: str,
    description: str,
) -> None:
    """Render a consistent, safely escaped page heading."""

    st.markdown(
        f"""
        <div class="edupath-page-header">
            <div class="edupath-eyebrow">{escape(eyebrow)}</div>
            <h1 class="edupath-page-title">{escape(title)}</h1>
            <div class="edupath-page-description">{escape(description)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
