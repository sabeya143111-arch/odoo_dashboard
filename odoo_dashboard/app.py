"""
SWAG Product Comparison Dashboard
Version 28.0 — 3 glassmorphism themes added (Midnight Ocean, Desert Gold, Arctic Ice)
Version 27.0 — 10 new features added:
  1. Model Watchlist (⭐ favorites)
  2. Branch Coverage Heatmap tab
  3. Multi-system KPI tiles with variance warning
  4. Save / Load Filter Presets
  5. Inline Planner Notes per Model
  6. ABC / XYZ Classification Badges
  7. What-if Transfer Simulator tab
  8. PDF Summary Export
  9. Smart Search Suggestions (Recent + Fuzzy)
 10. Daily Snapshot Auto-Compare (delta metrics)
"""

import io
import re
import hashlib
import time
import xmlrpc.client
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="SWAG Product Comparison",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# THEME DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────
THEMES = {
    "🌊 Midnight Ocean": {
        # deep navy background layers
        "bg_grad"        : "linear-gradient(135deg,#020818 0%,#0a1628 40%,#0d2137 70%,#061020 100%)",
        "sidebar_grad"   : "linear-gradient(180deg,#040d1a 0%,#071526 50%,#04111f 100%)",
        "sidebar_border" : "#00d4ff18",
        "sidebar_text"   : "#b0e8ff",
        # glass card base
        "glass_bg"       : "rgba(0,180,255,0.06)",
        "glass_border"   : "rgba(0,210,255,0.18)",
        "glass_blur"     : "12px",
        # accent colours
        "accent1"        : "#00c6ff",
        "accent2"        : "#0072ff",
        "accent3"        : "#00ffd5",
        # text
        "text_primary"   : "#e0f4ff",
        "text_secondary" : "#7ec8e3",
        "text_muted"     : "#4a7a9b",
        # metric / tab
        "metric_bg"      : "rgba(0,180,255,0.08)",
        "tab_active"     : "linear-gradient(90deg,#00c6ff,#0072ff)",
        "tab_bg"         : "rgba(0,100,180,0.25)",
        # buttons
        "btn_grad"       : "linear-gradient(90deg,#00c6ff,#0072ff,#00ffd5,#00c6ff)",
        "btn_secondary"  : "rgba(0,100,180,0.25)",
        # scrollbar
        "scroll_thumb"   : "linear-gradient(#00c6ff,#0072ff)",
        # login orb
        "orb_grad"       : "linear-gradient(135deg,#00c6ff,#0072ff,#00ffd5)",
        "title_grad"     : "linear-gradient(90deg,#00c6ff,#00ffd5,#00c6ff)",
        "shimmer_title"  : "linear-gradient(90deg,#00ffd5,#00c6ff,#0072ff,#00c6ff)",
        # hr / progress
        "hr_color"       : "#00c6ff44",
        "progress_grad"  : "linear-gradient(90deg,#00c6ff,#00ffd5)",
        # banners
        "info_bg"        : "rgba(0,100,200,0.18)",
        "info_border"    : "#00c6ff",
        "info_text"      : "#7dd8f8",
        "warn_bg"        : "rgba(180,120,0,0.18)",
        "ok_bg"          : "rgba(0,100,60,0.18)",
        "alert_bg"       : "rgba(180,0,40,0.18)",
    },
    "🏜️ Desert Gold": {
        "bg_grad"        : "linear-gradient(135deg,#1a0e00 0%,#2d1a00 35%,#3d2400 65%,#1f1000 100%)",
        "sidebar_grad"   : "linear-gradient(180deg,#120900 0%,#1e1000 50%,#150c00 100%)",
        "sidebar_border" : "#f5a62318",
        "sidebar_text"   : "#ffe0a0",
        "glass_bg"       : "rgba(245,166,35,0.07)",
        "glass_border"   : "rgba(255,190,60,0.20)",
        "glass_blur"     : "12px",
        "accent1"        : "#f5a623",
        "accent2"        : "#e07b00",
        "accent3"        : "#ffdb70",
        "text_primary"   : "#fff3dc",
        "text_secondary" : "#d4a056",
        "text_muted"     : "#7a5a2a",
        "metric_bg"      : "rgba(245,166,35,0.09)",
        "tab_active"     : "linear-gradient(90deg,#f5a623,#e07b00)",
        "tab_bg"         : "rgba(180,100,0,0.25)",
        "btn_grad"       : "linear-gradient(90deg,#f5a623,#e07b00,#ffdb70,#f5a623)",
        "btn_secondary"  : "rgba(180,100,0,0.25)",
        "scroll_thumb"   : "linear-gradient(#f5a623,#e07b00)",
        "orb_grad"       : "linear-gradient(135deg,#f5a623,#e07b00,#ffdb70)",
        "title_grad"     : "linear-gradient(90deg,#f5a623,#ffdb70,#f5a623)",
        "shimmer_title"  : "linear-gradient(90deg,#ffdb70,#f5a623,#e07b00,#f5a623)",
        "hr_color"       : "#f5a62344",
        "progress_grad"  : "linear-gradient(90deg,#f5a623,#ffdb70)",
        "info_bg"        : "rgba(180,100,0,0.18)",
        "info_border"    : "#f5a623",
        "info_text"      : "#ffd580",
        "warn_bg"        : "rgba(180,60,0,0.18)",
        "ok_bg"          : "rgba(0,80,30,0.18)",
        "alert_bg"       : "rgba(160,20,0,0.18)",
    },
    "🧊 Arctic Ice": {
        "bg_grad"        : "linear-gradient(135deg,#010d18 0%,#021825 35%,#031f30 65%,#010c17 100%)",
        "sidebar_grad"   : "linear-gradient(180deg,#010810 0%,#011420 50%,#010d18 100%)",
        "sidebar_border" : "#a8e6ff18",
        "sidebar_text"   : "#d0f4ff",
        "glass_bg"       : "rgba(168,230,255,0.06)",
        "glass_border"   : "rgba(200,245,255,0.20)",
        "glass_blur"     : "14px",
        "accent1"        : "#a8e6ff",
        "accent2"        : "#4fc3f7",
        "accent3"        : "#e0f7ff",
        "text_primary"   : "#edfaff",
        "text_secondary" : "#90cfe8",
        "text_muted"     : "#3a6a80",
        "metric_bg"      : "rgba(168,230,255,0.08)",
        "tab_active"     : "linear-gradient(90deg,#a8e6ff,#4fc3f7)",
        "tab_bg"         : "rgba(50,140,200,0.20)",
        "btn_grad"       : "linear-gradient(90deg,#a8e6ff,#4fc3f7,#e0f7ff,#a8e6ff)",
        "btn_secondary"  : "rgba(50,140,200,0.20)",
        "scroll_thumb"   : "linear-gradient(#a8e6ff,#4fc3f7)",
        "orb_grad"       : "linear-gradient(135deg,#a8e6ff,#4fc3f7,#e0f7ff)",
        "title_grad"     : "linear-gradient(90deg,#a8e6ff,#e0f7ff,#a8e6ff)",
        "shimmer_title"  : "linear-gradient(90deg,#e0f7ff,#a8e6ff,#4fc3f7,#a8e6ff)",
        "hr_color"       : "#a8e6ff33",
        "progress_grad"  : "linear-gradient(90deg,#a8e6ff,#e0f7ff)",
        "info_bg"        : "rgba(50,150,200,0.16)",
        "info_border"    : "#a8e6ff",
        "info_text"      : "#c0eeff",
        "warn_bg"        : "rgba(180,120,0,0.16)",
        "ok_bg"          : "rgba(0,90,50,0.16)",
        "alert_bg"       : "rgba(160,10,30,0.16)",
    },
}

THEME_NAMES = list(THEMES.keys())

def get_theme():
    name = st.session_state.get("active_theme", THEME_NAMES[0])
    return THEMES.get(name, THEMES[THEME_NAMES[0]])

def apply_theme_css():
    th = get_theme()
    css = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

/* ── BASE ── */
*,html,body,[class*="css"]{{font-family:'IBM Plex Sans Arabic',sans-serif;box-sizing:border-box;}}
.stApp{{background:{th['bg_grad']};min-height:100vh;}}

/* ── GLASS MIXIN helper classes ── */
.glass{{
  background:{th['glass_bg']};
  backdrop-filter:blur({th['glass_blur']});
  -webkit-backdrop-filter:blur({th['glass_blur']});
  border:1px solid {th['glass_border']};
  border-radius:16px;
}}

/* ── SIDEBAR ── */
section[data-testid="stSidebar"]{{
  background:{th['sidebar_grad']}!important;
  border-right:1px solid {th['sidebar_border']};
  backdrop-filter:blur(20px);
  -webkit-backdrop-filter:blur(20px);
}}
section[data-testid="stSidebar"] *,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] div{{color:{th['sidebar_text']}!important;}}
section[data-testid="stSidebar"] input{{color:#111!important;}}

/* ── KEYFRAMES ── */
@keyframes fadeInUp{{from{{opacity:0;transform:translateY(40px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes fadeInDown{{from{{opacity:0;transform:translateY(-30px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes bounceIn{{0%{{transform:scale(0.2) rotate(-10deg);opacity:0}}60%{{transform:scale(1.2) rotate(5deg);opacity:1}}80%{{transform:scale(0.9)}}100%{{transform:scale(1);opacity:1}}}}
@keyframes shimmer{{0%{{background-position:-400% center}}100%{{background-position:400% center}}}}
@keyframes pulse{{0%,100%{{box-shadow:0 0 0 0 {th['accent1']}44}}50%{{box-shadow:0 0 20px 8px {th['accent1']}22}}}}
@keyframes glow{{0%,100%{{text-shadow:0 0 10px {th['accent1']}88}}50%{{text-shadow:0 0 30px {th['accent3']}cc,0 0 60px {th['accent1']}88}}}}
@keyframes slideInLeft{{from{{opacity:0;transform:translateX(-40px)}}to{{opacity:1;transform:translateX(0)}}}}
@keyframes slideInRight{{from{{opacity:0;transform:translateX(40px)}}to{{opacity:1;transform:translateX(0)}}}}
@keyframes float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-8px)}}}}
@keyframes btnShine{{0%{{background-position:-200% center}}100%{{background-position:200% center}}}}
@keyframes borderGlow{{0%,100%{{border-color:{th['accent1']};box-shadow:0 0 5px {th['accent1']}44}}50%{{border-color:{th['accent3']};box-shadow:0 0 15px {th['accent3']}66}}}}
@keyframes countUp{{from{{opacity:0;transform:scale(0.5)}}to{{opacity:1;transform:scale(1)}}}}

/* ── LOGIN ── */
.login-orb{{width:120px;height:120px;border-radius:50%;background:{th['orb_grad']};display:flex;align-items:center;justify-content:center;font-size:3rem;margin:0 auto 20px;animation:float 3s ease-in-out infinite,bounceIn 1s ease forwards;box-shadow:0 8px 40px {th['accent1']}55,0 0 60px {th['accent3']}33;}}
.login-title{{font-size:2.4rem;font-weight:700;background:{th['shimmer_title']};background-size:200% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:shimmer 3s linear infinite,fadeInDown 0.8s ease forwards;text-align:center;margin-bottom:6px;}}
.login-subtitle{{color:{th['text_secondary']}!important;font-size:0.95rem;text-align:center;animation:fadeInUp 1s ease forwards;margin-bottom:28px;}}
.login-card{{background:{th['glass_bg']};backdrop-filter:blur({th['glass_blur']});-webkit-backdrop-filter:blur({th['glass_blur']});border:1px solid {th['glass_border']};border-radius:20px;padding:32px 36px;width:100%;animation:fadeInUp 0.9s ease forwards,pulse 3s infinite;}}
.welcome-banner{{background:{th['glass_bg']};backdrop-filter:blur(8px);border:1px solid {th['accent1']}44;border-radius:12px;padding:14px 20px;text-align:center;margin-bottom:20px;font-size:0.95rem;color:{th['text_secondary']}!important;animation:fadeInDown 0.7s ease forwards,borderGlow 3s infinite;}}

/* ── INPUTS ── */
.stTextInput input,.stNumberInput input,.stTextArea textarea{{background:{th['glass_bg']}!important;border:1px solid {th['accent1']}55!important;border-radius:10px!important;color:{th['text_primary']}!important;caret-color:{th['accent3']}!important;transition:all 0.3s ease!important;backdrop-filter:blur(8px);}}
.stTextInput input::placeholder,.stNumberInput input::placeholder,.stTextArea textarea::placeholder{{color:{th['text_muted']}!important;}}
.stTextInput input:focus,.stNumberInput input:focus,.stTextArea textarea:focus{{border-color:{th['accent1']}!important;box-shadow:0 0 0 3px {th['accent1']}33!important;}}
.stTextInput label,.stNumberInput label,.stTextArea label{{color:{th['text_secondary']}!important;font-weight:600!important;}}

/* ── BUTTONS ── */
.stFormSubmitButton button,.stButton button[kind="primary"]{{background:{th['btn_grad']}!important;background-size:300% auto!important;border:none!important;border-radius:12px!important;color:#fff!important;font-weight:700!important;font-size:1rem!important;padding:12px!important;animation:btnShine 3s linear infinite!important;transition:transform 0.2s,box-shadow 0.2s!important;box-shadow:0 4px 20px {th['accent1']}55!important;}}
.stFormSubmitButton button:hover,.stButton button[kind="primary"]:hover{{transform:translateY(-2px) scale(1.02)!important;box-shadow:0 8px 30px {th['accent2']}99!important;}}
.stButton button[kind="secondary"]{{background:{th['btn_secondary']}!important;backdrop-filter:blur(8px);border:1px solid {th['accent1']}55!important;color:{th['text_secondary']}!important;border-radius:10px!important;}}
.stButton button[kind="secondary"]:hover{{background:{th['btn_grad']}!important;background-size:300% auto!important;color:white!important;border-color:transparent!important;}}
.stButton button{{color:{th['text_secondary']}!important;}}
.stDownloadButton button{{background:{th['glass_bg']}!important;backdrop-filter:blur(8px);border:1px solid {th['accent1']}44!important;border-radius:10px!important;color:{th['text_secondary']}!important;font-size:0.78rem!important;font-weight:600!important;padding:6px 14px!important;transition:all 0.25s ease!important;box-shadow:0 2px 8px #00000044!important;}}
.stDownloadButton button:hover{{background:{th['btn_grad']}!important;background-size:300% auto;color:white!important;border-color:transparent!important;transform:translateY(-2px) scale(1.04)!important;box-shadow:0 6px 20px {th['accent1']}55!important;}}

/* ── DASHBOARD HEADER ── */
.dash-header{{text-align:center;padding:16px 0 24px;animation:fadeInDown 0.6s ease forwards;}}
.dash-title{{font-size:2.4rem;font-weight:700;background:{th['shimmer_title']};background-size:300% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:shimmer 4s linear infinite,glow 3s ease-in-out infinite;}}
.dash-subtitle{{color:{th['text_muted']};font-size:0.95rem;margin-top:-4px;}}

/* ── METRICS ── */
[data-testid="stMetric"]{{background:{th['metric_bg']}!important;backdrop-filter:blur({th['glass_blur']});-webkit-backdrop-filter:blur({th['glass_blur']});border:1px solid {th['glass_border']}!important;border-radius:16px!important;padding:16px 20px!important;animation:countUp 0.6s ease forwards;transition:transform 0.2s,box-shadow 0.2s;}}
[data-testid="stMetric"]:hover{{transform:translateY(-4px);box-shadow:0 8px 30px {th['accent1']}44;}}
[data-testid="stMetricLabel"]{{color:{th['text_muted']}!important;font-size:0.82rem!important;}}
[data-testid="stMetricValue"]{{font-size:1.7rem!important;font-weight:700!important;background:{th['title_grad']};-webkit-background-clip:text;-webkit-text-fill-color:transparent;}}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"]{{background:{th['tab_bg']};backdrop-filter:blur(10px);border-radius:12px;padding:4px;gap:4px;border:1px solid {th['glass_border']};}}
.stTabs [data-baseweb="tab"]{{color:{th['text_muted']}!important;border-radius:10px!important;font-size:0.83rem!important;font-weight:600!important;padding:8px 16px!important;transition:all 0.2s ease!important;}}
.stTabs [aria-selected="true"]{{background:{th['tab_active']}!important;color:white!important;box-shadow:0 4px 12px {th['accent1']}55!important;}}

/* ── BANNERS ── */
.info-banner{{background:{th['info_bg']};backdrop-filter:blur(8px);border-left:4px solid {th['info_border']};border-radius:0 10px 10px 0;padding:11px 16px;margin:8px 0 16px;font-size:0.85rem;color:{th['info_text']}!important;animation:slideInLeft 0.4s ease;}}
.warn-banner{{background:{th['warn_bg']};backdrop-filter:blur(8px);border-left:4px solid #f59e0b;border-radius:0 10px 10px 0;padding:11px 16px;margin:8px 0 16px;font-size:0.85rem;color:#fcd34d!important;}}
.alert-banner{{background:{th['alert_bg']};backdrop-filter:blur(8px);border-left:4px solid #f43f5e;border-radius:0 10px 10px 0;padding:11px 16px;margin:8px 0 16px;font-size:0.85rem;color:#fca5a5!important;animation:pulse 2s infinite;}}
.ok-banner{{background:{th['ok_bg']};backdrop-filter:blur(8px);border-left:4px solid #22c55e;border-radius:0 10px 10px 0;padding:11px 16px;margin:8px 0 16px;font-size:0.85rem;color:#86efac!important;}}

/* ── SNAP CARD ── */
.snap-card{{background:{th['glass_bg']};backdrop-filter:blur({th['glass_blur']});-webkit-backdrop-filter:blur({th['glass_blur']});border:1px solid {th['glass_border']};border-radius:14px;padding:16px 20px;font-size:0.87rem;color:{th['text_primary']}!important;line-height:2;animation:slideInRight 0.5s ease;box-shadow:0 4px 20px #00000055;}}
.snap-card b{{color:{th['text_secondary']}!important;}}

/* ── MISC ── */
.sys-row{{display:flex;align-items:center;gap:8px;margin-bottom:6px;}}
.sys-row span{{color:{th['text_primary']}!important;}}
.badge-ok{{background:linear-gradient(90deg,#065f46,#047857);color:#d1fae5!important;border-radius:20px;padding:3px 12px;font-size:0.76rem;font-weight:700;}}
.badge-off{{background:linear-gradient(90deg,#991b1b,#b91c1c);color:#fee2e2!important;border-radius:20px;padding:3px 12px;font-size:0.76rem;font-weight:700;}}
.badge-err{{background:linear-gradient(90deg,#78350f,#92400e);color:#fef3c7!important;border-radius:20px;padding:3px 12px;font-size:0.76rem;font-weight:700;}}
.stRadio label,.stRadio div[role="radiogroup"] label span,[data-testid="stToggle"] label,.stCheckbox label{{color:{th['text_primary']}!important;}}
div[data-testid="stRadio"] p{{color:{th['text_primary']}!important;}}
h1,h2,h3,h4,h5,h6{{color:{th['text_primary']}!important;}}
.stMarkdown p,.stMarkdown li{{color:{th['text_secondary']}!important;}}
.stCaption,[data-testid="stCaptionContainer"] p{{color:{th['text_muted']}!important;}}
.stAlert p{{color:#111!important;font-weight:600;}}

/* ── EXPANDER / UPLOADER ── */
[data-testid="stExpander"]{{background:{th['glass_bg']}!important;backdrop-filter:blur({th['glass_blur']});border:1px solid {th['glass_border']}!important;border-radius:12px!important;}}
[data-testid="stExpander"] summary,[data-testid="stExpander"] summary p{{color:{th['text_secondary']}!important;}}
[data-testid="stFileUploader"]{{background:{th['glass_bg']}!important;backdrop-filter:blur(8px);border:2px dashed {th['accent1']}55!important;border-radius:14px!important;}}
[data-testid="stFileUploader"] p,[data-testid="stFileUploader"] span{{color:{th['text_secondary']}!important;}}

/* ── HR / PROGRESS / SCROLLBAR ── */
hr{{border:none!important;height:1px!important;background:linear-gradient(90deg,transparent,{th['hr_color']},transparent)!important;margin:16px 0!important;}}
[data-testid="stProgressBar"]>div{{background:{th['progress_grad']}!important;border-radius:10px!important;}}
::-webkit-scrollbar{{width:6px;height:6px;}}
::-webkit-scrollbar-track{{background:rgba(0,0,0,0.3);}}
::-webkit-scrollbar-thumb{{background:{th['scroll_thumb']};border-radius:10px;}}
::-webkit-scrollbar-thumb:hover{{background:{th['accent3']};}}
.stNumberInput button{{color:{th['text_secondary']}!important;background:{th['glass_bg']}!important;}}
.mono{{font-family:'IBM Plex Mono',monospace;font-size:0.82rem;color:{th['text_secondary']};}}
footer{{visibility:hidden;}}
[data-baseweb="tag"]{{background:{th['accent1']}33!important;color:{th['text_secondary']}!important;}}
[data-baseweb="select"] div{{background:{th['glass_bg']}!important;color:{th['text_primary']}!important;border-color:{th['accent1']}55!important;}}

/* ── THEME SWITCHER PILLS in sidebar ── */
.theme-pill{{display:inline-block;padding:6px 14px;margin:4px;border-radius:20px;font-size:0.78rem;font-weight:700;cursor:pointer;border:1px solid {th['accent1']}55;background:{th['glass_bg']};color:{th['text_secondary']};transition:all 0.2s;}}
.theme-pill.active,.theme-pill:hover{{background:{th['btn_grad']};background-size:300% auto;color:white;border-color:transparent;box-shadow:0 4px 14px {th['accent1']}55;}}

/* ── ABC/XYZ BADGES ── */
.badge-A{{background:#065f46;color:#d1fae5;border-radius:8px;padding:2px 8px;font-size:.75rem;font-weight:700;}}
.badge-B{{background:#1e3a5f;color:#bfdbfe;border-radius:8px;padding:2px 8px;font-size:.75rem;font-weight:700;}}
.badge-C{{background:#374151;color:#d1d5db;border-radius:8px;padding:2px 8px;font-size:.75rem;font-weight:700;}}
.badge-X{{background:#7f1d1d;color:#fecaca;border-radius:8px;padding:2px 8px;font-size:.75rem;font-weight:700;}}
.badge-Y{{background:#78350f;color:#fde68a;border-radius:8px;padding:2px 8px;font-size:.75rem;font-weight:700;}}
.badge-Z{{background:#374151;color:#d1d5db;border-radius:8px;padding:2px 8px;font-size:.75rem;font-weight:700;}}
.badge-star{{background:linear-gradient(90deg,#d97706,#f59e0b);color:white;border-radius:8px;padding:2px 10px;font-size:.8rem;font-weight:700;cursor:pointer;}}
</style>
"""
    st.markdown(css, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# APPLY THEME (called once at top of every render)
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_KEYS = ["SWAG", "LAROUCHE", "DIFFC", "FASHION_LIMITS"]

# ─────────────────────────────────────────────────────────────────────────────
# LANGUAGE
# ─────────────────────────────────────────────────────────────────────────────
def get_lang():
    return st.session_state.get("lang", "EN")

def t(en, ar):
    return ar if get_lang() == "AR" else en

def get_system_name(key):
    cfg = st.secrets.get(key, {})
    return cfg.get("name_ar", cfg.get("name", key)) if get_lang() == "AR" else cfg.get("name", key)

# ─────────────────────────────────────────────────────────────────────────────
# TRANSLATE SYSTEM NAMES
# ─────────────────────────────────────────────────────────────────────────────
def translate_system_names(df):
    if df is None or df.empty:
        return df
    sys_col = t("System", "النظام")
    if sys_col not in df.columns:
        return df
    key_to_name = {k: get_system_name(k) for k in SYSTEM_KEYS}
    out = df.copy()
    out[sys_col] = out[sys_col].map(lambda v: key_to_name.get(v, v))
    return out

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE DEFAULTS
# ─────────────────────────────────────────────────────────────────────────────
_DEF = {
    "authenticated"      : False,
    "user_email"         : "",
    "lang"               : "EN",
    "last_run"           : None,
    "total_df"           : None,
    "branch_df"          : None,
    "transfers_df"       : None,
    "reorder_df"         : None,
    "sys_stats"          : {},
    "search_exact"       : False,
    "low_stock_thresh"   : 5,
    "price_history"      : {},
    "show_transfers"     : False,
    "show_reorder"       : False,
    "reorder_mode"       : "days_cover",
    "reorder_target_days": 30,
    "reorder_max_level"  : 100,
    "reorder_point"      : 10,
    "pdf_codes"          : None,
    "pdf_mode"           : "total",
    "so_analytics_df"    : None,
    "so_last_model"      : "",
    # ── Feature 1: Watchlist ──
    "watchlist"          : set(),
    # ── Feature 4: Filter Presets ──
    "filter_presets"     : {},
    # ── Feature 5: Planner Notes ──
    "planner_notes"      : {},
    # ── Feature 9: Recent Queries ──
    "recent_queries"     : [],
    # ── Feature 10: Last Snapshot ──
    "last_snapshot"      : None,
    # ── Themes ──
    "active_theme"       : "🌊 Midnight Ocean",
}
for k, v in _DEF.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Apply theme CSS immediately (re-runs on every rerun, picks up session state)
apply_theme_css()

# ─────────────────────────────────────────────────────────────────────────────
# SESSION LOGIN RESTORE
# ─────────────────────────────────────────────────────────────────────────────
_COOKIE_SECRET = "swag_2025_secure"

def _make_token(email):
    return hashlib.sha256(f"{_COOKIE_SECRET}_{email}".encode()).hexdigest()[:32]

def _verify_token(email, token):
    return bool(email and token and token == _make_token(email))

def restore_session():
    if st.session_state.get("authenticated"):
        return
    try:
        params = st.query_params
        email  = params.get("u", "")
        token  = params.get("t", "")
        if email and token and _verify_token(email, token):
            st.session_state.authenticated = True
            st.session_state.user_email    = email
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────────────────────
# XML-RPC
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def _proxy(url, ep):
    return xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/{ep}", allow_none=True)

@st.cache_data(ttl=28800, show_spinner=False)
def _auth(url, db, user, key):
    try:
        uid = _proxy(url, "common").authenticate(db, user, key, {})
        return uid or None
    except Exception:
        return None

def _x(url, db, uid, key, model, method, domain, kw):
    return _proxy(url, "object").execute_kw(db, uid, key, model, method, domain, kw)

# ─────────────────────────────────────────────────────────────────────────────
# DOMAIN BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def _domain(codes, exact):
    if exact:
        return [["default_code", "in", codes]]
    if len(codes) == 1:
        return [["default_code", "=like", f"{codes[0]}%"]]
    parts = [["default_code", "=like", f"{c}%"] for c in codes]
    return ["|"] * (len(parts) - 1) + parts

# ─────────────────────────────────────────────────────────────────────────────
# PDF PARSING
# ─────────────────────────────────────────────────────────────────────────────
_RE_BRACKET = re.compile(r'\[([A-Za-z0-9\-_()]{3,30})\]')
_RE_SR_LINE = re.compile(
    r'(?:^|\s)([A-Z]{2,6}\d+(?:-\d+)?(?:-[A-Z0-9()]{1,10})?)\s+.{0,80}?\d+\.?\d*\s+SR',
    re.MULTILINE)
_RE_GENERAL = re.compile(
    r'\b([A-Z]{2,6}\d+(?:-\d+)?(?:-[A-Z0-9]{1,4})?(?:\([^)]{1,15}\))?)\b')
_EXCLUDE = frozenset([
    'SR','VAT','TAX','PCS','QTY','NO','REF','INV','PO','SO',
    'DO','ID','EN','AR','PDF','AED','SAR','USD','KWD','OMR',
    'BHD','JOD','EGP','TRY'
])

def _valid(code):
    c = code.strip().upper()
    return (bool(re.search(r'[A-Z]', c)) and bool(re.search(r'\d', c))
            and 4 <= len(c) <= 25 and c not in _EXCLUDE)

def extract_base_model(code):
    code = re.sub(r'\([^)]*\)', '', code)
    for s in ['-2XL','-3XL','-4XL','-XXL','-XL','-L','-M','-S','-XS','-2X','-3X']:
        if code.upper().endswith(s.upper()):
            code = code[:-len(s)]; break
    return re.sub(r'-\d{2,3}$', '', code).strip()

def get_unique_base_models(raw):
    seen, out = set(), []
    for item in raw:
        b = extract_base_model(item["code"])
        if b and b not in seen:
            seen.add(b)
            out.append({"sequence": item["sequence"], "code": b})
    return out

@st.cache_data(show_spinner=False)
def parse_invoice_pdf_cached(file_bytes):
    try:
        from pypdf import PdfReader
    except ImportError:
        return []
    text = ""
    for page in PdfReader(io.BytesIO(file_bytes)).pages:
        text += (page.extract_text() or "") + "\n"
    if not text.strip():
        return []
    raw = (_RE_BRACKET.findall(text)
           + [m.group(1) for m in _RE_SR_LINE.finditer(text)]
           + _RE_GENERAL.findall(text))
    seen, out = set(), []
    seq = 1
    for c in raw:
        u = c.strip().upper()
        if _valid(u) and u not in seen:
            seen.add(u)
            out.append({"sequence": seq, "code": u})
            seq += 1
    return out

# ─────────────────────────────────────────────────────────────────────────────
# EXCEL HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _style_worksheet(ws, df_clean, lang="EN"):
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.formatting.rule import DataBarRule, ColorScaleRule, CellIsRule
    from openpyxl.chart import BarChart, Reference
    if lang == "AR":
        ws.sheet_view.rightToLeft = True
    hdr_fill     = PatternFill("solid", fgColor="4B0082")
    hdr_font     = Font(bold=True, color="FFFFFF", size=11, name="Calibri")
    hdr_align    = Alignment(horizontal="center", vertical="center")
    thin         = Side(border_style="thin", color="D0D0D0")
    border       = Border(left=thin, right=thin, top=thin, bottom=thin)
    alt_fill     = PatternFill("solid", fgColor="F3EFFF")
    zero_fill    = PatternFill("solid", fgColor="FFE0E0")
    zero_font    = Font(color="CC0000", bold=True, name="Calibri")
    normal_font  = Font(name="Calibri", size=10)
    num_align    = Alignment(horizontal="right",  vertical="center")
    center_align = Alignment(horizontal="center", vertical="center")
    total_fill   = PatternFill("solid", fgColor="2E2E2E")
    total_font   = Font(bold=True, name="Calibri", color="FFFFFF")
    max_row = ws.max_row
    max_col = ws.max_column
    ws.row_dimensions[1].height = 28
    for col_num in range(1, max_col + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = hdr_fill; cell.font = hdr_font
        cell.alignment = hdr_align; cell.border = border
    col_names = [ws.cell(row=1, column=c).value for c in range(1, max_col + 1)]
    on_hand_col = sale_price_col = loc_col = branch_col = model_col = None
    for i, name in enumerate(col_names, 1):
        if name in ("On Hand", "متوفر"):       on_hand_col    = i
        if name in ("Sale Price", "سعر البيع"): sale_price_col = i
        if name in ("Location", "الموقع"):      loc_col        = i
        if name in ("Branch", "الفرع"):         branch_col     = i
        if name in ("Model Code", "رمز الموديل"): model_col    = i
    for row in ws.iter_rows(min_row=2, max_row=max_row):
        is_zero = False
        if on_hand_col:
            val = ws.cell(row=row[0].row, column=on_hand_col).value
            is_zero = (val is None or
                       str(val).strip() in ['0','Not Available','غير متوفر','—','-',''] or
                       val == 0)
        for cell in row:
            cell.border = border
            cell.font   = zero_font if is_zero else normal_font
            if is_zero:              cell.fill = zero_fill
            elif cell.row % 2 == 0: cell.fill = alt_fill
            cell.alignment = num_align if isinstance(cell.value, (int, float)) else center_align
        ws.row_dimensions[row[0].row].height = 18
    for col_num in range(1, max_col + 1):
        col_letter = get_column_letter(col_num)
        max_len = 0
        for r in ws.iter_rows(min_col=col_num, max_col=col_num):
            for cell in r:
                if cell.value: max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(max_col)}{max_row}"
    if on_hand_col and max_row > 1:
        col_letter = get_column_letter(on_hand_col)
        ws.conditional_formatting.add(
            f"{col_letter}2:{col_letter}{max_row}",
            DataBarRule(start_type="min", end_type="max", color="4472C4"))
    if sale_price_col and max_row > 1:
        col_letter = get_column_letter(sale_price_col)
        ws.conditional_formatting.add(
            f"{col_letter}2:{col_letter}{max_row}",
            ColorScaleRule(start_type="min", start_color="63BE7B",
                           mid_type="percentile", mid_value=50, mid_color="FFEB84",
                           end_type="max", end_color="F8696B"))
    if on_hand_col and max_row > 1:
        col_letter     = get_column_letter(on_hand_col)
        low_stock_fill = PatternFill("solid", fgColor="FFF2CC")
        low_stock_font = Font(color="7F6000", bold=True, name="Calibri")
        ws.conditional_formatting.add(
            f"{col_letter}2:{col_letter}{max_row}",
            CellIsRule(operator="lessThanOrEqual", formula=["3"],
                       fill=low_stock_fill, font=low_stock_font))
    total_row = max_row + 1
    ws.cell(row=total_row, column=1, value="TOTAL")
    ws.cell(row=total_row, column=1).font      = total_font
    ws.cell(row=total_row, column=1).fill      = total_fill
    ws.cell(row=total_row, column=1).alignment = Alignment(horizontal="center")
    if on_hand_col:
        col = get_column_letter(on_hand_col)
        ws.cell(row=total_row, column=on_hand_col,
                value=f"=SUM({col}2:{col}{max_row})")
        ws.cell(row=total_row, column=on_hand_col).font      = total_font
        ws.cell(row=total_row, column=on_hand_col).fill      = total_fill
        ws.cell(row=total_row, column=on_hand_col).alignment = Alignment(horizontal="center")
    ws.row_dimensions[total_row].height = 20
    ws.sheet_properties.tabColor = "667EEA"
    footer_row = total_row + 2
    ws.cell(row=footer_row, column=1,
            value=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  SWAG Dashboard")
    ws.cell(row=footer_row, column=1).font = Font(italic=True, color="888888", size=9, name="Calibri")
    ws.page_setup.orientation  = "landscape"
    ws.page_setup.fitToPage    = True
    ws.page_setup.fitToWidth   = 1
    ws.print_title_rows        = "1:1"
    ws.print_area              = f"A1:{get_column_letter(max_col)}{max_row}"
    ws.oddHeader.center.text   = "SWAG Product Report"
    ws.oddHeader.center.font   = "Calibri,Bold"
    ws.oddFooter.center.text   = "Page &P of &N  |  Generated: &D"
    ws.sheet_view.zoomScale    = 85
    if loc_col:
        ws.column_dimensions[get_column_letter(loc_col)].width = 35
        for row_num in range(2, max_row + 1):
            ws.cell(row=row_num, column=loc_col).alignment = Alignment(
                wrap_text=True, vertical="center", horizontal="left")
            ws.row_dimensions[row_num].height = 28
    if on_hand_col and model_col and max_row > 2:
        chart = BarChart()
        chart.type = "bar"; chart.shape = 4
        chart.title = "Stock by Branch"; chart.style = 10
        chart.y_axis.title = "On Hand"; chart.x_axis.title = "Branch"
        chart.width = 20; chart.height = 12
        data_ref = Reference(ws, min_col=on_hand_col, min_row=1, max_row=max_row)
        cats_ref = Reference(ws, min_col=model_col,   min_row=2, max_row=max_row)
        chart.add_data(data_ref, titles_from_data=True)
        chart.set_categories(cats_ref)
        ws.add_chart(chart, f"A{max_row + 5}")

def to_csv(df):
    return df.drop(columns=["_status"], errors="ignore").to_csv(index=False).encode("utf-8-sig")

def to_excel(df):
    lang  = st.session_state.get('lang', 'EN')
    buf   = io.BytesIO()
    clean = df.drop(columns=['_status'], errors='ignore').copy()
    on_hand_col = 'On Hand' if 'On Hand' in clean.columns else (
        'متوفر' if 'متوفر' in clean.columns else None)
    if on_hand_col:
        na_text = 'غير متوفر' if lang == 'AR' else 'Not Available'
        clean[on_hand_col] = clean[on_hand_col].apply(
            lambda x: na_text if (pd.isna(x) or str(x).strip() in ['0','']) or x == 0 else x)
    desired_order = [
        t("Model Code","رمز الموديل"), t("System","النظام"),
        t("Branch","الفرع"),           t("Location","الموقع"),
        t("Sale Price","سعر البيع"),   t("On Hand","متوفر"),
    ]
    ordered_cols  = [c for c in desired_order if c in clean.columns]
    remaining     = [c for c in clean.columns if c not in ordered_cols]
    clean         = clean[ordered_cols + remaining]
    with pd.ExcelWriter(buf, engine='openpyxl') as w:
        clean.to_excel(w, index=False, sheet_name='Data')
        _style_worksheet(w.sheets['Data'], clean, lang=lang)
    return buf.getvalue()

def to_excel_bulk(df):
    lang    = st.session_state.get("lang", "EN")
    buf     = io.BytesIO()
    sys_col = t("System", "النظام")
    _desired = [
        t("Model Code","رمز الموديل"), t("System","النظام"),
        t("Branch","الفرع"),           t("Location","الموقع"),
        t("Sale Price","سعر البيع"),   t("On Hand","متوفر"),
    ]
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        def _ws(data, name):
            c = data.drop(columns=["_status"], errors="ignore").copy()
            on_hand_col = t("On Hand", "متوفر")
            if on_hand_col in c.columns:
                na_text = 'غير متوفر' if lang == 'AR' else 'Not Available'
                c[on_hand_col] = c[on_hand_col].apply(
                    lambda x: na_text if (pd.isna(x) or str(x).strip() in ['0','']) or x == 0 else x)
            _ordered   = [col for col in _desired if col in c.columns]
            _remaining = [col for col in c.columns if col not in _ordered]
            c = c[_ordered + _remaining]
            c.to_excel(w, index=False, sheet_name=name[:31])
            _style_worksheet(w.sheets[name[:31]], c, lang=lang)
        _ws(df, t("All Systems", "كل الأنظمة"))
        if sys_col in df.columns:
            for key in SYSTEM_KEYS:
                nm  = get_system_name(key)
                sub = df[df[sys_col] == nm]
                if not sub.empty:
                    _ws(sub, nm)
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────────────────────
# PURCHASE SUMMARY HELPER
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def get_purchase_summary_by_model(model_codes_tuple, date_from, date_to):
    empty_df = pd.DataFrame(columns=["Model Code", "Purchase Qty"])
    cfg = st.secrets.get("SWAG")
    if not cfg: return empty_df
    uid = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not uid: return empty_df
    u = cfg["url"]; db = cfg["db"]; ak = cfg["api_key"]
    try:
        line_domain = [
            ["order_id.state", "in", ["purchase", "done"]],
            ["order_id.date_order", ">=", f"{date_from} 00:00:00"],
            ["order_id.date_order", "<=", f"{date_to} 23:59:59"],
        ]
        if model_codes_tuple:
            line_domain.append(["product_id.default_code", "in", list(model_codes_tuple)])
        lines = _x(u, db, uid, ak, "purchase.order.line", "search_read", [line_domain],
                   {"fields": ["product_id", "product_qty"], "limit": 10000, "order": "id desc"})
        if not lines: return empty_df
        product_ids = list({l["product_id"][0] for l in lines if isinstance(l.get("product_id"), list)})
        products = _x(u, db, uid, ak, "product.product", "search_read",
                      [[["id", "in", product_ids]]],
                      {"fields": ["id", "default_code"], "limit": len(product_ids) + 10})
        prod_map = {p["id"]: p for p in products}
        agg = {}
        for line in lines:
            pid  = line["product_id"][0] if isinstance(line.get("product_id"), list) else None
            prod = prod_map.get(pid, {})
            mc   = prod.get("default_code", "").strip()
            if not mc: continue
            agg[mc] = agg.get(mc, 0) + float(line.get("product_qty") or 0)
        if not agg: return empty_df
        df = pd.DataFrame([{"Model Code": mc, "Purchase Qty": qty} for mc, qty in agg.items()])
        return df.groupby("Model Code", as_index=False)["Purchase Qty"].sum()
    except Exception:
        return empty_df

# ─────────────────────────────────────────────────────────────────────────────
# PURCHASE HISTORY (detailed)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_swag_purchase_history(model_code, date_from, date_to):
    empty_cols = ["Date","PO","Vendor","Brand Category","Category",
                  "Model Code","Product","Qty","Unit Price","Subtotal"]
    empty_df = pd.DataFrame(columns=empty_cols)
    cfg = st.secrets.get("SWAG")
    if not cfg: return empty_df
    uid = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not uid: return empty_df
    u = cfg["url"]; db = cfg["db"]; ak = cfg["api_key"]
    try:
        line_domain = [
            ["order_id.state", "in", ["purchase", "done"]],
            ["order_id.date_order", ">=", f"{date_from} 00:00:00"],
            ["order_id.date_order", "<=", f"{date_to} 23:59:59"],
        ]
        if model_code and model_code.strip():
            line_domain.append(["product_id.default_code", "=", model_code.strip()])
        lines = _x(u, db, uid, ak, "purchase.order.line", "search_read", [line_domain],
                   {"fields": ["order_id","product_id","product_qty","price_unit"],
                    "limit": 5000, "order": "order_id desc"})
        if not lines: return empty_df
        order_ids   = list({l["order_id"][0] for l in lines if isinstance(l.get("order_id"), list)})
        product_ids = list({l["product_id"][0] for l in lines if isinstance(l.get("product_id"), list)})
        orders   = _x(u, db, uid, ak, "purchase.order", "search_read",
                      [[["id","in",order_ids]]],
                      {"fields":["id","name","partner_id","date_order"],"limit":len(order_ids)+10})
        order_map = {o["id"]: o for o in orders}
        products  = _x(u, db, uid, ak, "product.product", "search_read",
                       [[["id","in",product_ids]]],
                       {"fields":["id","default_code","display_name","categ_id","product_tmpl_id"],
                        "limit":len(product_ids)+10})
        prod_map  = {p["id"]: p for p in products}
        tmpl_ids  = list({p["product_tmpl_id"][0] for p in products
                          if isinstance(p.get("product_tmpl_id"), list)})
        tmpl_map  = {}
        if tmpl_ids:
            try:
                tmpls    = _x(u, db, uid, ak, "product.template", "search_read",
                              [[["id","in",tmpl_ids]]],
                              {"fields":["id","x_brand_category_id"],"limit":len(tmpl_ids)+10})
                tmpl_map = {t_["id"]: t_ for t_ in tmpls}
            except Exception:
                tmpl_map = {}
        rows = []
        for line in lines:
            oid   = line["order_id"][0] if isinstance(line.get("order_id"), list) else None
            pid   = line["product_id"][0] if isinstance(line.get("product_id"), list) else None
            order = order_map.get(oid, {})
            prod  = prod_map.get(pid, {})
            raw_date = order.get("date_order") or ""
            try:    date_str = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
            except: date_str = raw_date[:10] if raw_date else "—"
            partner        = order.get("partner_id")
            vendor         = partner[1] if isinstance(partner, list) else (str(partner) if partner else "—")
            categ          = prod.get("categ_id")
            category       = categ[1] if isinstance(categ, list) else (str(categ) if categ else "")
            brand_category = ""
            tmpl_ref       = prod.get("product_tmpl_id")
            if isinstance(tmpl_ref, list) and tmpl_ref:
                tmpl = tmpl_map.get(tmpl_ref[0], {})
                bc   = tmpl.get("x_brand_category_id")
                if isinstance(bc, list): brand_category = bc[1] if len(bc) > 1 else ""
                elif bc:                 brand_category = str(bc)
            qty      = float(line.get("product_qty") or 0)
            price    = float(line.get("price_unit") or 0)
            rows.append({
                "Date"          : date_str,
                "PO"            : order.get("name") or "—",
                "Vendor"        : vendor,
                "Brand Category": brand_category,
                "Category"      : category,
                "Model Code"    : prod.get("default_code") or "",
                "Product"       : prod.get("display_name") or "",
                "Qty"           : qty,
                "Unit Price"    : price,
                "Subtotal"      : round(qty * price, 2),
            })
        if not rows: return empty_df
        df = pd.DataFrame(rows)
        return df.sort_values(by="Date", ascending=False).reset_index(drop=True)
    except Exception:
        return empty_df

# ─────────────────────────────────────────────────────────────────────────────
# SWAG SALES HISTORY
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_swag_sales_history(model_code=None, date_from=None, date_to=None):
    empty = pd.DataFrame(columns=[
        "Date","SO","Customer","Branch","Brand Category","Category",
        "Model Code","Product","Qty","Unit Price","Subtotal"])
    cfg = st.secrets.get("SWAG")
    if not cfg: return empty
    uid = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not uid: return empty
    u, db, ak = cfg["url"], cfg["db"], cfg["api_key"]
    try:
        domain = [
            ["order_id.state","in",["sale","done"]],
            ["order_id.date_order",">=",f"{date_from} 00:00:00"],
            ["order_id.date_order","<=",f"{date_to} 23:59:59"],
        ]
        if model_code:
            domain.append(["product_id.default_code","=like",f"{model_code}%"])
        lines = _x(u, db, uid, ak, "sale.order.line", "search_read", [domain],
                   {"fields":["order_id","product_id","product_uom_qty","price_unit","price_subtotal"],
                    "limit":15000,"order":"order_id desc"})
        if not lines: return empty
        order_ids = list({l["order_id"][0] for l in lines if isinstance(l.get("order_id"), list)})
        orders    = _x(u, db, uid, ak, "sale.order", "search_read",
                       [[["id","in",order_ids]]],
                       {"fields":["id","name","partner_id","date_order","branch_id"],
                        "limit":len(order_ids)+10})
        order_map = {o["id"]: o for o in orders}
        prod_ids  = list({l["product_id"][0] for l in lines if isinstance(l.get("product_id"), list)})
        products  = _x(u, db, uid, ak, "product.product", "search_read",
                       [[["id","in",prod_ids]]],
                       {"fields":["id","default_code","name","categ_id","product_tmpl_id"],
                        "limit":len(prod_ids)+10})
        prod_map  = {p["id"]: p for p in products}
        tmpl_ids  = list({p["product_tmpl_id"][0] for p in products
                          if isinstance(p.get("product_tmpl_id"), list)})
        tmpl_map  = {}
        if tmpl_ids:
            try:
                tmpls    = _x(u, db, uid, ak, "product.template", "search_read",
                              [[["id","in",tmpl_ids]]],
                              {"fields":["id","x_studio_brand_category"],"limit":len(tmpl_ids)+10})
                tmpl_map = {tt["id"]: tt for tt in tmpls}
            except Exception:
                tmpl_map = {}
        rows = []
        for line in lines:
            oid = line["order_id"][0] if isinstance(line.get("order_id"), list) else None
            pid = line["product_id"][0] if isinstance(line.get("product_id"), list) else None
            o   = order_map.get(oid, {})
            p   = prod_map.get(pid, {})
            tmpl_ref  = p.get("product_tmpl_id")
            tid       = tmpl_ref[0] if isinstance(tmpl_ref, list) else tmpl_ref
            tmpl      = tmpl_map.get(tid, {})
            branch_obj    = o.get("branch_id")
            branch        = branch_obj[1] if isinstance(branch_obj, list) and len(branch_obj)>1 else (str(branch_obj) if branch_obj else "Unknown")
            categ_obj     = p.get("categ_id")
            categ         = categ_obj[1] if isinstance(categ_obj, list) and len(categ_obj)>1 else (str(categ_obj) if categ_obj else "")
            brand_cat_raw = tmpl.get("x_studio_brand_category", "")
            brand_cat     = brand_cat_raw[1] if isinstance(brand_cat_raw, list) and len(brand_cat_raw)>1 else (str(brand_cat_raw) if brand_cat_raw else "")
            partner_obj   = o.get("partner_id")
            customer      = partner_obj[1] if isinstance(partner_obj, list) and len(partner_obj)>1 else (str(partner_obj) if partner_obj else "")
            prod_name_ref = line.get("product_id")
            product_display = prod_name_ref[1] if isinstance(prod_name_ref, list) and len(prod_name_ref)>1 else p.get("name","")
            raw_date  = str(o.get("date_order",""))
            date_val  = raw_date[:10] if raw_date else ""
            rows.append({
                "Date"          : date_val,
                "SO"            : o.get("name",""),
                "Customer"      : customer,
                "Branch"        : branch,
                "Brand Category": brand_cat or "(No Brand)",
                "Category"      : categ or "(No Category)",
                "Model Code"    : str(p.get("default_code","")).strip(),
                "Product"       : product_display,
                "Qty"           : float(line.get("product_uom_qty") or 0),
                "Unit Price"    : float(line.get("price_unit") or 0),
                "Subtotal"      : float(line.get("price_subtotal") or 0),
            })
        df = pd.DataFrame(rows)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        return df.sort_values("Date", ascending=False).reset_index(drop=True)
    except Exception:
        return empty

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN MAPS
# ─────────────────────────────────────────────────────────────────────────────
_COL_MAP_EN = {
    "System":"System","Model Code":"Model Code","Product":"Product",
    "Sale Price":"Sale Price","On Hand":"On Hand","Branch":"Branch",
    "Location":"Location","Reference":"Reference","Type":"Type",
    "State":"State","From":"From","To":"To","Qty":"Qty",
    "Scheduled":"Scheduled","Sold(30d)":"Sold(30d)","Daily Vel":"Daily Vel",
    "Days Left":"Days Left","Suggest":"Suggest","Priority":"Priority",
    "Purchase Qty":"Purchase Qty",
}
_COL_MAP_AR = {
    "System":"النظام","Model Code":"رمز الموديل","Product":"المنتج",
    "Sale Price":"سعر البيع","On Hand":"متوفر","Branch":"الفرع",
    "Location":"الموقع","Reference":"المرجع","Type":"النوع",
    "State":"الحالة","From":"من","To":"إلى","Qty":"الكمية",
    "Scheduled":"المجدول","Sold(30d)":"مباع(30ي)","Daily Vel":"معدل/يوم",
    "Days Left":"أيام متبقية","Suggest":"المقترح","Priority":"الأولوية",
    "Purchase Qty":"كمية المشتريات",
}

def localize_columns(df):
    if df is None or df.empty: return df
    col_map = _COL_MAP_AR if get_lang() == "AR" else _COL_MAP_EN
    return df.rename(columns=col_map)

def prepare_df(df):
    df = localize_columns(df)
    df = translate_system_names(df)
    return df

# ─────────────────────────────────────────────────────────────────────────────
# FETCH ALL DATA
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=180, show_spinner=False)
def fetch_all_data(
    codes_tuple, exact=False,
    need_branch=False, need_transfers=False, need_reorder=False,
    reorder_mode="days_cover", target_days=30,
    max_level=100, reorder_point=10,
):
    DAYS  = 30
    dfrom = (datetime.now() - timedelta(days=DAYS)).strftime("%Y-%m-%d 00:00:00")
    codes = list(codes_tuple)
    dom   = _domain(codes, exact)

    CS="System"; CM="Model Code"; CPR="Product"; CP="Sale Price"
    CQ="On Hand"; CB="Branch";    CR="Reference"; CT="Type"
    CST="State";  CF="From";      CTO="To";       CQT="Qty"
    CD="Scheduled"; CSOLD="Sold(30d)"; CVEL="Daily Vel"
    CDAY="Days Left"; CSUGG="Suggest"; CPRI="Priority"
    SM={"draft":"Draft","waiting":"Waiting","confirmed":"Confirmed","assigned":"Ready"}

    def _one(key):
        cfg = st.secrets.get(key)
        sn  = key
        R   = {"key":key,"total":[],"branch":[],"transfers":[],"reorder":[]}
        if not cfg:
            R["total"].append({CS:sn,CM:"—",CPR:"No config",CP:0.0,CQ:0,"_status":"ERROR"})
            return R
        uid = _auth(cfg["url"],cfg["db"],cfg["user"],cfg["api_key"])
        if not uid:
            R["total"].append({CS:sn,CM:"—",CPR:"⚠️ Auth failed",CP:0.0,CQ:0,"_status":"ERROR"})
            return R
        u=cfg["url"]; db=cfg["db"]; ak=cfg["api_key"]
        try:
            prods = _x(u,db,uid,ak,"product.product","search_read",[dom],
                       {"fields":["id","display_name","default_code","qty_available","list_price"],
                        "limit":2000,"order":"default_code asc"})
            if not prods:
                R["total"].append({CS:sn,CM:"—",CPR:"Not found",CP:0.0,CQ:0,"_status":"NOT_FOUND"})
                return R
            pids = [p["id"] for p in prods]
            pmap = {p["id"]:p for p in prods}
            for p in prods:
                R["total"].append({
                    CS:sn, CM:p.get("default_code") or "—",
                    CPR:p.get("display_name") or "",
                    CP:float(p.get("list_price") or 0),
                    CQ:int(p.get("qty_available") or 0),
                    "_status":"OK"})

            if need_branch:
                internal_locs = _x(u,db,uid,ak,"stock.location","search_read",
                                   [[["usage","=","internal"],["active","=",True]]],
                                   {"fields":["id"],"limit":10000})
                internal_ids  = {l["id"] for l in internal_locs}
                qs = _x(u,db,uid,ak,"stock.quant","search_read",
                        [[["product_id","in",pids],
                          ["location_id","in",list(internal_ids)],
                          ["quantity",">",0]]],
                        {"fields":["product_id","location_id","quantity"],"limit":5000})
                for q in qs:
                    pid = q["product_id"][0] if isinstance(q.get("product_id"),list) else None
                    loc = q.get("location_id") or [None,"—"]
                    ln  = loc[1] if isinstance(loc,list) else str(loc)
                    pm  = pmap.get(pid,{})
                    R["branch"].append({
                        CS:sn, CB:ln,
                        CM:pm.get("default_code") or "—",
                        CP:float(pm.get("list_price") or 0),
                        CQ:int(q.get("quantity") or 0), "_status":"OK"})

            if need_transfers:
                mvs = _x(u,db,uid,ak,"stock.move","search_read",
                         [[["product_id","in",pids],
                           ["state","in",["draft","waiting","confirmed","assigned"]]]],
                         {"fields":["picking_id","product_id","product_uom_qty"],"limit":2000})
                if mvs:
                    pkids = list({m["picking_id"][0] for m in mvs if isinstance(m.get("picking_id"),list)})
                    if pkids:
                        pks   = _x(u,db,uid,ak,"stock.picking","search_read",
                                   [[["id","in",pkids]]],
                                   {"fields":["id","name","picking_type_id","state",
                                              "location_id","location_dest_id","scheduled_date"]})
                        pkmap = {p["id"]:p for p in pks}
                        for mv in mvs:
                            pr = mv.get("picking_id")
                            if not isinstance(pr,list): continue
                            pk = pkmap.get(pr[0],{})
                            def _n(f,_p=pk):
                                v=_p.get(f); return v[1] if isinstance(v,list) else (v or "—")
                            sd = pk.get("scheduled_date") or "—"
                            if sd != "—":
                                try: sd=datetime.strptime(sd,"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
                                except: pass
                            pid2 = mv["product_id"][0] if isinstance(mv.get("product_id"),list) else None
                            pm2  = pmap.get(pid2,{})
                            R["transfers"].append({
                                CS:sn, CR:pk.get("name") or "—",
                                CT:_n("picking_type_id"),
                                CST:SM.get(pk.get("state",""),pk.get("state","")),
                                CF:_n("location_id"), CTO:_n("location_dest_id"),
                                CM:pm2.get("default_code") or "—",
                                CQT:int(mv.get("product_uom_qty") or 0),
                                CD:sd, "_status":"OK"})

            if need_reorder:
                sl = _x(u,db,uid,ak,"sale.order.line","search_read",
                        [[["product_id","in",pids],
                          ["order_id.state","in",["sale","done"]],
                          ["order_id.date_order",">=",dfrom]]],
                        {"fields":["product_id","product_uom_qty"],"limit":10000})
                sm2 = {}
                for l in sl:
                    pid = l["product_id"][0] if isinstance(l.get("product_id"),list) else None
                    if pid: sm2[pid] = sm2.get(pid,0)+float(l.get("product_uom_qty") or 0)
                for p in prods:
                    pid  = p["id"]; cq=int(p.get("qty_available") or 0)
                    sold = sm2.get(pid,0); vel=round(sold/DAYS,2)
                    dl   = str(round(cq/vel,1)) if vel>0 else "∞"
                    sg   = max(0,round(target_days*vel-cq)) if reorder_mode=="days_cover" else max(0,max_level-cq)
                    pr2  = ("🔴 Critical" if cq<=0 else "🟡 Low" if cq<=reorder_point else "🟢 OK")
                    R["reorder"].append({
                        CS:sn, CM:p.get("default_code") or "—",
                        CPR:p.get("display_name") or "",
                        CQ:cq, CSOLD:int(sold), CVEL:vel,
                        CDAY:dl, CSUGG:sg, CPRI:pr2, "_status":"OK"})
        except Exception as e:
            R["total"].append({CS:sn,CM:"—",CPR:f"❌ {e}",CP:0.0,CQ:0,"_status":"ERROR"})
        return R

    at=[]; ab=[]; atr=[]; ar=[]
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(_one,k):k for k in SYSTEM_KEYS}
        for f in as_completed(futs):
            r = f.result()
            at.extend(r["total"]); ab.extend(r["branch"])
            atr.extend(r["transfers"]); ar.extend(r["reorder"])

    def _df(rows,cols):
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=cols)
    return {
        "total"    : _df(at,  ["System","Model Code","Product","Sale Price","On Hand","_status"]),
        "branch"   : _df(ab,  ["System","Branch","Model Code","Sale Price","On Hand","_status"]),
        "transfers": _df(atr, ["System","Reference","Type","State","From","To","Model Code","Qty","Scheduled","_status"]),
        "reorder"  : _df(ar,  ["System","Model Code","Product","On Hand","Sold(30d)","Daily Vel","Days Left","Suggest","Priority","_status"]),
    }

# ─────────────────────────────────────────────────────────────────────────────
# EXCEL PURCHASE / SALES EXPORT
# ─────────────────────────────────────────────────────────────────────────────
def to_excel_purchase(df):
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    buf   = io.BytesIO()
    clean = df.copy()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        clean.to_excel(w, index=False, sheet_name="SWAG Purchase")
        ws = w.sheets["SWAG Purchase"]
        hdr_fill   = PatternFill("solid", fgColor="4B0082")
        hdr_font   = Font(bold=True, color="FFFFFF", size=11, name="Calibri")
        hdr_align  = Alignment(horizontal="center", vertical="center")
        thin       = Side(border_style="thin", color="D0D0D0")
        border     = Border(left=thin, right=thin, top=thin, bottom=thin)
        alt_fill   = PatternFill("solid", fgColor="F3EFFF")
        norm_font  = Font(name="Calibri", size=10)
        num_align  = Alignment(horizontal="right", vertical="center")
        ctr_align  = Alignment(horizontal="center", vertical="center")
        tot_fill   = PatternFill("solid", fgColor="2E2E2E")
        tot_font   = Font(bold=True, name="Calibri", color="FFFFFF")
        max_row = ws.max_row; max_col = ws.max_column
        ws.row_dimensions[1].height = 28
        for col_num in range(1, max_col+1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill=hdr_fill; cell.font=hdr_font; cell.alignment=hdr_align; cell.border=border
        for row in ws.iter_rows(min_row=2, max_row=max_row):
            for cell in row:
                cell.border=border; cell.font=norm_font
                if cell.row%2==0: cell.fill=alt_fill
                cell.alignment = num_align if isinstance(cell.value,(int,float)) else ctr_align
            ws.row_dimensions[row[0].row].height=18
        for col_num in range(1, max_col+1):
            col_letter = get_column_letter(col_num)
            max_len    = max((len(str(ws.cell(row=r,column=col_num).value or "")) for r in range(1,max_row+1)), default=8)
            ws.column_dimensions[col_letter].width = min(max(max_len+3,12),50)
        ws.freeze_panes="A2"; ws.auto_filter.ref=f"A1:{get_column_letter(max_col)}{max_row}"
        tot_row = max_row+1
        ws.cell(row=tot_row,column=1,value="TOTAL").font=tot_font
        ws.cell(row=tot_row,column=1).fill=tot_fill
        ws.cell(row=tot_row,column=1).alignment=Alignment(horizontal="center")
        col_names=[ws.cell(row=1,column=c).value for c in range(1,max_col+1)]
        for cname in ("Qty","Subtotal"):
            if cname in col_names:
                ci=col_names.index(cname)+1; cl=get_column_letter(ci)
                ws.cell(row=tot_row,column=ci,value=f"=SUM({cl}2:{cl}{max_row})")
                ws.cell(row=tot_row,column=ci).font=tot_font
                ws.cell(row=tot_row,column=ci).fill=tot_fill
                ws.cell(row=tot_row,column=ci).alignment=Alignment(horizontal="center")
        ws.row_dimensions[tot_row].height=20
        ws.sheet_properties.tabColor="667EEA"
    return buf.getvalue()

def to_excel_sales(df):
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    buf   = io.BytesIO()
    clean = df.copy()
    if "Date" in clean.columns:
        clean["Date"] = clean["Date"].astype(str).str[:10]
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        clean.to_excel(w, index=False, sheet_name="SWAG Sales")
        ws = w.sheets["SWAG Sales"]
        hdr_fill  = PatternFill("solid", fgColor="1a6b3c")
        hdr_font  = Font(bold=True, color="FFFFFF", size=11, name="Calibri")
        hdr_align = Alignment(horizontal="center", vertical="center")
        thin      = Side(border_style="thin", color="D0D0D0")
        border    = Border(left=thin, right=thin, top=thin, bottom=thin)
        alt_fill  = PatternFill("solid", fgColor="E8F5E9")
        norm_font = Font(name="Calibri", size=10)
        num_align = Alignment(horizontal="right",  vertical="center")
        ctr_align = Alignment(horizontal="center", vertical="center")
        tot_fill  = PatternFill("solid", fgColor="2E2E2E")
        tot_font  = Font(bold=True, name="Calibri", color="FFFFFF")
        max_row, max_col = ws.max_row, ws.max_column
        ws.row_dimensions[1].height=28
        for c in range(1,max_col+1):
            cell=ws.cell(row=1,column=c)
            cell.fill=hdr_fill; cell.font=hdr_font; cell.alignment=hdr_align; cell.border=border
        for row in ws.iter_rows(min_row=2,max_row=max_row):
            for cell in row:
                cell.border=border; cell.font=norm_font
                cell.fill = alt_fill if cell.row%2==0 else PatternFill()
                cell.alignment = num_align if isinstance(cell.value,(int,float)) else ctr_align
            ws.row_dimensions[row[0].row].height=18
        for c in range(1,max_col+1):
            cl=get_column_letter(c)
            mxl=max((len(str(ws.cell(row=r,column=c).value or "")) for r in range(1,max_row+1)),default=8)
            ws.column_dimensions[cl].width=min(max(mxl+3,12),50)
        ws.freeze_panes="A2"; ws.auto_filter.ref=f"A1:{get_column_letter(max_col)}{max_row}"
        tot_row=max_row+1
        tot_cell=ws.cell(row=tot_row,column=1,value="TOTAL")
        tot_cell.font=tot_font; tot_cell.fill=tot_fill; tot_cell.alignment=ctr_align
        col_names=[ws.cell(row=1,column=c).value for c in range(1,max_col+1)]
        for cname in ("Qty","Subtotal"):
            if cname in col_names:
                ci=col_names.index(cname)+1; cl=get_column_letter(ci)
                ws.cell(row=tot_row,column=ci,value=f"=SUM({cl}2:{cl}{max_row})")
                ws.cell(row=tot_row,column=ci).font=tot_font
                ws.cell(row=tot_row,column=ci).fill=tot_fill
                ws.cell(row=tot_row,column=ci).alignment=ctr_align
        ws.sheet_properties.tabColor="43e97b"
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────────────────────
# BRANCH MATRIX EXCEL EXPORT
# ─────────────────────────────────────────────────────────────────────────────
def to_excel_branch_matrix(df_branch_filtered, lang="EN"):
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    if df_branch_filtered is None or df_branch_filtered.empty:
        return b""

    col_model   = t("Model Code",   "رمز الموديل")
    col_branch  = t("Branch",       "الفرع")
    col_location= t("Location",     "الموقع")
    col_price   = t("Sale Price",   "سعر البيع")
    col_onhand  = t("On Hand",      "متوفر")
    col_product = t("Product",      "المنتج")
    label_pur   = t("Purchase Qty", "كمية المشتريات")

    df = df_branch_filtered.copy()

    if col_location in df.columns:
        pivot_col = col_location
    elif col_branch in df.columns:
        pivot_col = col_branch
    else:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="BranchMatrix")
        return buf.getvalue()

    if col_onhand in df.columns:
        df[col_onhand] = pd.to_numeric(df[col_onhand], errors="coerce").fillna(0)
    else:
        df[col_onhand] = 0

    if col_model not in df.columns:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="BranchMatrix")
        return buf.getvalue()

    pivot = (
        df.pivot_table(index=col_model, columns=pivot_col, values=col_onhand,
                       aggfunc="sum", fill_value=0)
        .reset_index()
    )
    pivot.columns.name = None

    if col_price in df.columns:
        price_map = df.groupby(col_model)[col_price].first().reset_index()
        pivot = pivot.merge(price_map, on=col_model, how="left")
        pivot[col_price] = pd.to_numeric(pivot[col_price], errors="coerce").fillna(0).round(2)
    else:
        pivot[col_price] = 0.0

    product_map = {}
    total_df_ss = st.session_state.get("total_df")
    if total_df_ss is not None and not total_df_ss.empty:
        if col_model in total_df_ss.columns and col_product in total_df_ss.columns:
            product_map = total_df_ss.groupby(col_model)[col_product].first().dropna().to_dict()
    pivot[col_product] = pivot[col_model].map(product_map).fillna("")

    purchase_qty_map = {}
    if total_df_ss is not None and not total_df_ss.empty:
        for possible in ["Purchase Qty", "كمية المشتريات", label_pur]:
            if possible in total_df_ss.columns and col_model in total_df_ss.columns:
                tmp = total_df_ss.groupby(col_model)[possible].sum().to_dict()
                if tmp:
                    purchase_qty_map = tmp
                    break

    if not purchase_qty_map:
        unique_models = pivot[col_model].dropna().unique().tolist()
        if unique_models:
            try:
                end_date   = datetime.now().date()
                start_date = end_date - timedelta(days=365)
                pur_df     = get_purchase_summary_by_model(
                    tuple(unique_models),
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d"))
                if not pur_df.empty:
                    purchase_qty_map = dict(zip(pur_df["Model Code"], pur_df["Purchase Qty"]))
            except Exception:
                pass

    pivot[label_pur] = pivot[col_model].map(purchase_qty_map).fillna(0).astype(int)

    fixed_left  = [col_model, col_product, col_price, label_pur]
    loc_columns = sorted(c for c in pivot.columns if c not in fixed_left)
    ordered     = [c for c in fixed_left if c in pivot.columns] + loc_columns
    pivot       = pivot[ordered]

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pivot.to_excel(writer, index=False, sheet_name="BranchMatrix")
        ws = writer.sheets["BranchMatrix"]

        if lang == "AR":
            ws.sheet_view.rightToLeft = True

        hdr_fill  = PatternFill("solid", fgColor="4B0082")
        hdr_font  = Font(bold=True, color="FFFFFF", size=11, name="Calibri")
        hdr_align = Alignment(horizontal="center", vertical="center")
        thin      = Side(border_style="thin", color="D0D0D0")
        border    = Border(left=thin, right=thin, top=thin, bottom=thin)
        alt_fill  = PatternFill("solid", fgColor="F3EFFF")
        norm_font = Font(name="Calibri", size=10)
        num_align = Alignment(horizontal="right",  vertical="center")
        ctr_align = Alignment(horizontal="center", vertical="center")
        tot_fill  = PatternFill("solid", fgColor="2E2E2E")
        tot_font  = Font(bold=True, color="FFFFFF", name="Calibri")
        zero_fill = PatternFill("solid", fgColor="FFF2CC")
        zero_font = Font(color="7F6000", bold=True, name="Calibri")

        max_row = ws.max_row
        max_col = ws.max_column
        col_names_ws = [ws.cell(row=1, column=c).value for c in range(1, max_col + 1)]

        ws.row_dimensions[1].height = 28
        for c in range(1, max_col + 1):
            cell = ws.cell(row=1, column=c)
            cell.fill = hdr_fill; cell.font = hdr_font
            cell.alignment = hdr_align; cell.border = border

        for row_idx in range(2, max_row + 1):
            for col_idx in range(1, max_col + 1):
                cell     = ws.cell(row=row_idx, column=col_idx)
                col_name = col_names_ws[col_idx - 1]
                is_loc   = col_name not in (col_model, col_product, col_price, label_pur, None)
                cell.border = border
                cell.font   = norm_font
                if row_idx % 2 == 0:
                    cell.fill = alt_fill
                if is_loc and isinstance(cell.value, (int, float)) and cell.value == 0:
                    cell.fill = zero_fill
                    cell.font = zero_font
                cell.alignment = (
                    num_align if isinstance(cell.value, (int, float)) else ctr_align)
            ws.row_dimensions[row_idx].height = 18

        for c in range(1, max_col + 1):
            col_letter = get_column_letter(c)
            max_len = max(
                (len(str(ws.cell(row=r, column=c).value or "")) for r in range(1, max_row + 1)),
                default=8)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 50)

        ws.freeze_panes    = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(max_col)}{max_row}"

        total_row = max_row + 1
        tc = ws.cell(row=total_row, column=1, value=t("TOTAL", "الإجمالي"))
        tc.font = tot_font; tc.fill = tot_fill; tc.alignment = ctr_align
        ws.row_dimensions[total_row].height = 22

        for c_idx, c_name in enumerate(col_names_ws, start=1):
            if c_name in (None, col_model, col_product, col_price):
                continue
            cl  = get_column_letter(c_idx)
            tot = ws.cell(row=total_row, column=c_idx)
            tot.value     = f"=SUM({cl}2:{cl}{max_row})"
            tot.font      = tot_font
            tot.fill      = tot_fill
            tot.alignment = num_align

        footer_row = total_row + 2
        ws.cell(
            row=footer_row, column=1,
            value=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  SWAG Dashboard"
        ).font = Font(italic=True, color="888888", size=9, name="Calibri")

        ws.sheet_properties.tabColor = "667EEA"
        ws.page_setup.orientation    = "landscape"
        ws.page_setup.fitToPage      = True
        ws.page_setup.fitToWidth     = 1
        ws.print_title_rows          = "1:1"
        ws.print_area                = f"A1:{get_column_letter(max_col)}{max_row}"
        ws.sheet_view.zoomScale      = 85

    return buf.getvalue()


def dl_name(tag, ext):
    return f"swag_{tag}_{datetime.now().strftime('%Y%m%d_%H%M')}.{ext}"

# ─────────────────────────────────────────────────────────────────────────────
# PRICE HISTORY
# ─────────────────────────────────────────────────────────────────────────────
def record_price_snapshot(df):
    pc=t("Sale Price","سعر البيع"); sc=t("System","النظام"); mc=t("Model Code","رمز الموديل")
    if pc not in df.columns: return
    ok = df[df["_status"]=="OK"] if "_status" in df.columns else df
    if ok.empty: return
    ts = datetime.now().strftime("%H:%M:%S")
    for _, row in ok.iterrows():
        k = f"{row.get(sc,'?')}|{row.get(mc,'?')}"
        st.session_state.price_history.setdefault(k,[]).append(
            {"time":ts,"price":float(row.get(pc,0))})

def build_price_history_df():
    hist = st.session_state.price_history
    if not hist: return pd.DataFrame()
    all_t = sorted({e["time"] for v in hist.values() for e in v})
    recs  = []
    for ts in all_t:
        row = {"time":ts}
        for k, entries in hist.items():
            px = [e["price"] for e in entries if e["time"]==ts]
            row[k] = px[-1] if px else None
        recs.append(row)
    return pd.DataFrame(recs).set_index("time")

# ─────────────────────────────────────────────────────────────────────────────
# QTY DISPLAY HELPER
# ─────────────────────────────────────────────────────────────────────────────
def get_qty_display(qty, lang="EN"):
    try:
        v = float(qty)
        if pd.isna(v) or v == 0:
            return "❌ لا يوجد" if lang == "AR" else "❌ Not Available"
        return int(v)
    except Exception:
        return "❌ لا يوجد" if lang == "AR" else "❌ Not Available"

# ─────────────────────────────────────────────────────────────────────────────
# HTML TABLE CSS
# ─────────────────────────────────────────────────────────────────────────────
_TABLE_CSS = """<style>
.swag-wrap{width:100%;overflow-x:auto;border-radius:16px;box-shadow:0 4px 32px rgba(0,0,0,.5);margin-bottom:4px;}
.swag-tbl{width:100%;border-collapse:collapse;font-family:'IBM Plex Sans Arabic',sans-serif;font-size:.84rem;}
.swag-tbl thead tr{background:linear-gradient(90deg,#667eea,#764ba2,#9b59b6);}
.swag-tbl thead th{color:#fff;font-weight:700;padding:14px 16px;text-align:center;white-space:nowrap;letter-spacing:.4px;border:none;position:sticky;top:0;z-index:2;}
.swag-tbl thead th:first-child{border-radius:16px 0 0 0;}
.swag-tbl thead th:last-child{border-radius:0 16px 0 0;}
.swag-tbl tbody tr:nth-child(odd){background:#1a1a3e;}
.swag-tbl tbody tr:nth-child(odd) td{color:#e8e8ff;}
.swag-tbl tbody tr:nth-child(even){background:#22224a;}
.swag-tbl tbody tr:nth-child(even) td{color:#c4b5fd;}
.swag-tbl tbody td{padding:10px 16px;text-align:center;border-bottom:1px solid #ffffff08;transition:background .15s,color .15s;}
.swag-tbl tbody td.cf{font-weight:700;color:#a78bfa!important;border-right:2px solid #667eea33;}
.swag-tbl tbody tr:hover td{background:#3b2f7a!important;color:#fff!important;}
.swag-tbl tbody tr:hover td.cf{color:#f093fb!important;}
.swag-tbl tbody tr.rl td{background:#3b0a1e!important;color:#fca5a5!important;font-weight:600;}
.swag-tbl tbody tr.rl:hover td{background:#5b1030!important;color:#ffd5d5!important;}
.swag-tbl tbody tr.hi td{background:#1a3b1a!important;color:#86efac!important;font-weight:600;}
.swag-tbl tbody tr.na-row td{background:#2a1a1a!important;opacity:.82;}
.swag-tbl tbody td.na-cell{color:#f97316!important;font-weight:700;letter-spacing:.3px;}
.swag-tbl tbody td.star-cell{font-size:1.1rem;cursor:pointer;}
</style>"""

# ─────────────────────────────────────────────────────────────────────────────
# FEATURE 6: ABC/XYZ CLASSIFICATION
# ─────────────────────────────────────────────────────────────────────────────
def compute_abc_xyz(df):
    """
    Add ABC_Class column based on cumulative stock value.
    A = top 20% value, B = next 30%, C = rest.
    XYZ skipped (no sales variability data here).
    """
    qc = t("On Hand","متوفر")
    pc = t("Sale Price","سعر البيع")
    mc = t("Model Code","رمز الموديل")

    work = df.copy()
    if qc not in work.columns or pc not in work.columns:
        work["ABC_Class"] = "—"
        return work

    qty = pd.to_numeric(work[qc], errors="coerce").fillna(0)
    prc = pd.to_numeric(work[pc], errors="coerce").fillna(0)
    work["_val"] = qty * prc

    total_val = work["_val"].sum()
    if total_val == 0:
        work["ABC_Class"] = "C"
        work.drop(columns=["_val"], inplace=True)
        return work

    sorted_idx = work["_val"].sort_values(ascending=False).index
    cumsum_pct = work.loc[sorted_idx, "_val"].cumsum() / total_val

    abc_map = {}
    for idx in sorted_idx:
        pct = cumsum_pct.loc[idx]
        abc_map[idx] = "A" if pct <= 0.20 else ("B" if pct <= 0.50 else "C")

    work["ABC_Class"] = pd.Series(abc_map)
    work.drop(columns=["_val"], inplace=True)
    return work

def _abc_badge(cls):
    colors = {"A":"badge-A","B":"badge-B","C":"badge-C"}
    css    = colors.get(cls, "badge-C")
    return f'<span class="{css}">{cls}</span>'

# ─────────────────────────────────────────────────────────────────────────────
# FEATURE 9: FUZZY SEARCH HELPER (Levenshtein)
# ─────────────────────────────────────────────────────────────────────────────
def _levenshtein(a, b):
    a, b = a.lower(), b.lower()
    if len(a) < len(b): a, b = b, a
    prev = list(range(len(b)+1))
    for i, ca in enumerate(a):
        curr = [i+1]
        for j, cb in enumerate(b):
            curr.append(min(prev[j+1]+1, curr[-1]+1, prev[j]+(ca!=cb)))
        prev = curr
    return prev[-1]

def fuzzy_suggestions(query, candidates, n=5):
    q = query.strip().upper()
    if not q or not candidates:
        return []
    scored = sorted(candidates, key=lambda c: _levenshtein(q, c.upper()))
    return scored[:n]

def _push_recent_query(q):
    rq = st.session_state.get("recent_queries", [])
    if q and q not in rq:
        rq = [q] + rq
    st.session_state["recent_queries"] = rq[:5]

# ─────────────────────────────────────────────────────────────────────────────
# FEATURE 10: SNAPSHOT HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _make_snapshot(df, thr):
    qc = t("On Hand","متوفر")
    ok = df[df["_status"]=="OK"] if "_status" in df.columns else df
    qty = pd.to_numeric(ok[qc], errors="coerce").fillna(0) if qc in ok.columns else pd.Series(dtype=float)
    pc  = t("Sale Price","سعر البيع")
    prc = pd.to_numeric(ok[pc], errors="coerce").fillna(0) if pc in ok.columns else pd.Series(dtype=float)
    total_val   = float((qty * prc).sum()) if len(qty)==len(prc) else 0.0
    total_qty   = int(qty.sum())
    low_stock   = int((qty[(qty > 0) & (qty <= thr)]).count()) if thr > 0 else 0
    not_avail   = int((qty == 0).sum())
    return {
        "ts"        : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_qty" : total_qty,
        "total_val" : total_val,
        "low_stock" : low_stock,
        "not_avail" : not_avail,
    }

def _delta_str(curr, prev, key, fmt=None, suffix=""):
    if prev is None or key not in prev:
        return ""
    c, p = curr.get(key, 0), prev.get(key, 0)
    if p == 0:
        return ""
    pct = (c - p) / abs(p) * 100
    sign = "+" if pct >= 0 else ""
    if fmt == "pct":
        return f"{sign}{pct:.1f}% vs last run"
    diff = c - p
    sign2 = "+" if diff >= 0 else ""
    return f"{sign2}{diff} vs last run"

# ─────────────────────────────────────────────────────────────────────────────
# FEATURE 8: PDF SUMMARY EXPORT
# ─────────────────────────────────────────────────────────────────────────────
def generate_pdf_summary(df):
    """Generate a 1-2 page PDF summary using fpdf2."""
    try:
        from fpdf import FPDF
    except ImportError:
        return None

    qc = t("On Hand","متوفر")
    pc = t("Sale Price","سعر البيع")
    mc = t("Model Code","رمز الموديل")
    sc = t("System","النظام")

    ok = df[df["_status"]=="OK"].copy() if "_status" in df.columns else df.copy()
    qty = pd.to_numeric(ok.get(qc, 0), errors="coerce").fillna(0)
    prc = pd.to_numeric(ok.get(pc, 0), errors="coerce").fillna(0)
    ok["_val"] = qty * prc

    top10 = ok.nlargest(10, "_val")[[mc, sc, qc, pc, "_val"]].reset_index(drop=True)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(102, 126, 234)
    pdf.cell(0, 12, "SWAG Product Comparison - Summary", ln=True, align="C")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Total rows: {len(df)}", ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 9, "Top 10 Models by Stock Value", ln=True)
    pdf.ln(2)

    col_w = [45, 35, 28, 28, 40]
    headers = ["Model Code", "System", "On Hand", "Sale Price", "Stock Value"]

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(75, 0, 130)
    pdf.set_text_color(255, 255, 255)
    for i, (h, w) in enumerate(zip(headers, col_w)):
        pdf.cell(w, 8, h, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for idx, row in top10.iterrows():
        pdf.set_fill_color(243, 239, 255) if idx % 2 == 0 else pdf.set_fill_color(255, 255, 255)
        pdf.set_text_color(30, 30, 30)
        vals = [
            str(row.get(mc, ""))[:20],
            str(row.get(sc, ""))[:15],
            str(int(pd.to_numeric(row.get(qc, 0), errors="coerce") or 0)),
            f"{float(pd.to_numeric(row.get(pc, 0), errors='coerce') or 0):.2f}",
            f"{float(row.get('_val', 0)):,.2f}",
        ]
        for v, w in zip(vals, col_w):
            pdf.cell(w, 7, v, border=1, fill=True, align="C")
        pdf.ln()

    pdf.ln(6)

    # Bar chart (simple ASCII-style using rectangles)
    if sc in ok.columns and "_val" in ok.columns:
        sys_totals = ok.groupby(sc)["_val"].sum()
        if not sys_totals.empty:
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(30, 30, 30)
            pdf.cell(0, 9, "Stock Value by System", ln=True)
            pdf.ln(2)

            max_val = sys_totals.max()
            bar_max_w = 120
            colors_rgb = [(102,126,234),(240,147,251),(67,233,123),(255,166,77)]

            for i, (sys_name, val) in enumerate(sys_totals.items()):
                bar_w = int((val / max_val) * bar_max_w) if max_val > 0 else 0
                r, g, b = colors_rgb[i % len(colors_rgb)]
                pdf.set_font("Helvetica", "", 9)
                pdf.set_text_color(30, 30, 30)
                pdf.cell(50, 7, str(sys_name)[:22], align="R")
                pdf.set_fill_color(r, g, b)
                if bar_w > 0:
                    pdf.cell(bar_w, 7, "", fill=True)
                pdf.set_fill_color(230, 230, 230)
                remaining = bar_max_w - bar_w
                if remaining > 0:
                    pdf.cell(remaining, 7, "", fill=True)
                pdf.set_text_color(50, 50, 50)
                pdf.cell(30, 7, f" {val:,.0f} SAR", align="L")
                pdf.ln()

    buf = io.BytesIO()
    buf.write(pdf.output())
    buf.seek(0)
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY DF — extended with watchlist toggle
# ─────────────────────────────────────────────────────────────────────────────
def display_df(df, thresh=0, table_key="tbl", show_watchlist_toggle=False):
    """
    Render the styled HTML table with inline filters.
    Returns the post-filter DataFrame (columns without _status) for exports.
    """
    if df is None or df.empty:
        st.info(t("No data.","لا بيانات."))
        return pd.DataFrame()

    work    = df.copy()
    sys_col = t("System","النظام")
    mc_col  = t("Model Code","رمز الموديل")
    pr_col  = t("Product","المنتج")
    br_col  = t("Branch","الفرع")
    loc_col = t("Location","الموقع")
    qc      = t("On Hand","متوفر")
    pc      = t("Sale Price","سعر البيع")
    has_sys = sys_col in work.columns
    has_br  = br_col  in work.columns

    # ── Feature 1: Watchlist filter ──────────────────────────────────────────
    watchlist = st.session_state.get("watchlist", set())
    show_fav_only = st.session_state.get(f"show_fav_{table_key}", False)
    if show_watchlist_toggle:
        col_fav, *_ = st.columns([2, 6])
        with col_fav:
            show_fav_only = st.toggle(
                f"⭐ {t('Show only favorites','المفضلة فقط')}",
                value=show_fav_only, key=f"show_fav_{table_key}")
    if show_fav_only and mc_col in work.columns:
        work = work[work[mc_col].isin(watchlist)]
        if work.empty:
            st.info(t("No favorites match the current data.","لا مفضلات في البيانات الحالية."))
            return pd.DataFrame()

    fc = st.columns([2, 2, 2, 1.5])

    if has_sys:
        all_sys = sorted(work[sys_col].dropna().unique().tolist())
        with fc[0]:
            sel_sys = st.multiselect(
                f"🏢 {t('Company','الشركة')}", options=all_sys, default=all_sys,
                key=f"{table_key}_sys")
        if sel_sys:
            work = work[work[sys_col].isin(sel_sys)]

    if has_br:
        all_br = sorted(work[br_col].dropna().unique().tolist())
        with fc[1]:
            sel_br = st.multiselect(
                f"🏪 {t('Branch','الفرع')}", options=all_br, default=all_br,
                key=f"{table_key}_br")
        if sel_br:
            work = work[work[br_col].isin(sel_br)]

    with fc[2]:
        q = st.text_input(
            f"🔍 {t('Search model / product','بحث موديل / منتج')}",
            value="", placeholder=t("e.g. XP6013 or Shirt","مثال: XP6013"),
            key=f"{table_key}_q").strip()
    if q:
        ql   = q.lower()
        mask = pd.Series([False] * len(work), index=work.index)
        for col in [mc_col, pr_col, loc_col]:
            if col in work.columns:
                mask = mask | work[col].fillna("").str.lower().str.contains(ql, regex=False)
        work = work[mask]

    with fc[3]:
        sortable = [c for c in work.columns if c != "_status"]
        sort_by  = st.selectbox(
            f"↕️ {t('Sort by','ترتيب')}", options=["—"] + sortable, index=0,
            key=f"{table_key}_sort")
    if sort_by and sort_by != "—" and sort_by in work.columns:
        try:
            work = work.sort_values(
                by=sort_by,
                key=lambda s: pd.to_numeric(s, errors="coerce").fillna(0)
                              if pd.api.types.is_numeric_dtype(pd.to_numeric(s, errors="coerce"))
                              else s,
                ascending=True)
        except Exception:
            work = work.sort_values(by=sort_by)

    if work.empty:
        st.warning(t("⚠️ No rows match your filters.","لا توجد نتائج بعد الفلتر."))
        # ── Feature 9: fuzzy suggestions ──
        if q and mc_col in df.columns:
            candidates = df[mc_col].dropna().unique().tolist()
            suggs = fuzzy_suggestions(q, candidates)
            if suggs:
                st.markdown(f"**🔍 {t('Did you mean:','هل تقصد:')}** " +
                            " · ".join(f"`{s}`" for s in suggs))
        return pd.DataFrame()

    if qc in work.columns:
        raw_q = pd.to_numeric(work[qc], errors="coerce")
        mn, mx = int(raw_q.min() or 0), int(raw_q.max() or 0)
        if mx > mn:
            qr    = st.slider(f"📦 {t('Qty range','نطاق الكمية')}",
                              min_value=mn, max_value=mx, value=(mn, mx),
                              key=f"{table_key}_qrange")
            raw_q2 = pd.to_numeric(work[qc], errors="coerce")
            work   = work[(raw_q2 >= qr[0]) & (raw_q2 <= qr[1])]

    ok_work = work[work["_status"]=="OK"] if "_status" in work.columns else work
    sm1,sm2,sm3,sm4 = st.columns(4)
    sm1.metric(t("Rows","الصفوف"), len(work))
    if qc in ok_work.columns:
        sm2.metric(t("Total Qty","إجمالي الكمية"),
                   int(pd.to_numeric(ok_work[qc], errors="coerce").fillna(0).sum()))
    if pc in ok_work.columns:
        vp = pd.to_numeric(ok_work[pc], errors="coerce")
        sm3.metric(t("Avg Price","متوسط السعر"),
                   f"{vp[vp>0].mean():.2f} SAR" if not vp[vp>0].empty else "—")
    if has_sys and sys_col in ok_work.columns:
        sm4.metric(t("Companies","الشركات"), ok_work[sys_col].nunique())

    show   = work.drop(columns=["_status"], errors="ignore").copy()
    _raw_qty = (pd.to_numeric(work[qc], errors="coerce").fillna(0)
                if qc in work.columns else pd.Series(dtype=float, index=work.index))

    if pc in show.columns:
        show[pc] = pd.to_numeric(show[pc], errors="coerce").map(
            lambda v: f"{v:.2f} SAR" if pd.notna(v) else "—")
    if qc in show.columns:
        _lang = get_lang()
        show[qc] = pd.to_numeric(show[qc], errors="coerce").map(
            lambda v: get_qty_display(v, _lang))

    # ── Feature 6: inject ABC badges ─────────────────────────────────────────
    if "ABC_Class" in show.columns:
        show["ABC_Class"] = show["ABC_Class"].map(
            lambda v: _abc_badge(v) if v in ("A","B","C") else v)

    low_idx = set()
    if thresh > 0 and qc in work.columns:
        raw_q3  = pd.to_numeric(work[qc], errors="coerce")
        low_idx = set(work.index[(raw_q3 > 0) & (raw_q3 <= thresh)])

    _zero_set    = set(_raw_qty.index[_raw_qty == 0]) if not _raw_qty.empty else set()
    _na_label_en = "❌ Not Available"
    _na_label_ar = "❌ لا يوجد"

    cols = show.columns.tolist()

    # ── Feature 1: add ⭐ column ──────────────────────────────────────────────
    star_col = "⭐"
    if mc_col in work.columns:
        cols_with_star = [star_col] + cols
    else:
        cols_with_star = cols

    th_ = "".join(f"<th>{c}</th>" for c in cols_with_star)

    def _row(idx_row):
        i, row = idx_row
        is_zero = i in _zero_set
        cls = " na-row" if is_zero else (" rl" if i in low_idx else "")

        # star cell
        if mc_col in work.columns:
            code = work.at[i, mc_col] if i in work.index else ""
            in_wl = code in watchlist
            star_icon = "⭐" if in_wl else "☆"
            star_cell = f'<td class="star-cell" title="{code}">{star_icon}</td>'
        else:
            star_cell = ""

        cells = "".join(
            f'<td class="cf">{v}</td>'
            if ci == 0
            else (f'<td class="na-cell">{v}</td>'
                  if is_zero and isinstance(v, str) and v in (_na_label_en, _na_label_ar)
                  else f"<td>{v}</td>")
            for ci, v in enumerate(row))
        return f'<tr class="{cls}">{star_cell}{cells}</tr>'

    tbody = "".join(_row(x) for x in show.iterrows())
    st.markdown(
        f'{_TABLE_CSS}<div class="swag-wrap">'
        f'<table class="swag-tbl"><thead><tr>{th_}</tr></thead>'
        f'<tbody>{tbody}</tbody></table></div>',
        unsafe_allow_html=True)
    st.caption(f"📊 {len(show)} {t('rows shown','صفوف معروضة')} "
               f"/ {len(df)} {t('total','إجمالي')}")

    # ── Feature 1: watchlist toggle buttons ──────────────────────────────────
    if mc_col in work.columns and not work.empty:
        model_codes_visible = work[mc_col].dropna().unique().tolist()
        with st.expander(f"⭐ {t('Manage Favorites (Watchlist)','إدارة المفضلة')}", expanded=False):
            wl_cols = st.columns(min(len(model_codes_visible), 6))
            for idx_m, code in enumerate(model_codes_visible[:30]):
                col_i = wl_cols[idx_m % min(len(model_codes_visible), 6)]
                in_wl = code in watchlist
                label = f"⭐ {code}" if in_wl else f"☆ {code}"
                if col_i.button(label, key=f"wl_{table_key}_{idx_m}_{code}"):
                    if in_wl:
                        st.session_state["watchlist"].discard(code)
                    else:
                        st.session_state["watchlist"].add(code)
                    st.rerun()

    # ── Feature 5: Planner Notes in the table ────────────────────────────────
    if mc_col in work.columns:
        notes = st.session_state.get("planner_notes", {})
        if any(notes.get(code) for code in work[mc_col].dropna().unique()):
            st.markdown(f"#### 📝 {t('Planner Notes','ملاحظات المخطط')}")
            for _, row in work.iterrows():
                code = row.get(mc_col, "")
                note = notes.get(code, "")
                if note:
                    st.markdown(
                        f"<div class='info-banner'><b>{code}</b>: {note}</div>",
                        unsafe_allow_html=True)

    return work.drop(columns=["_status"], errors="ignore").copy()

# ─────────────────────────────────────────────────────────────────────────────
# GENERIC HTML TABLE RENDER
# ─────────────────────────────────────────────────────────────────────────────
def _render_html_table(df_display):
    if df_display is None or df_display.empty:
        st.info(t("No data.","لا بيانات.")); return
    cols = df_display.columns.tolist()
    th_  = "".join(f"<th>{c}</th>" for c in cols)
    def _row(idx_row):
        _, row = idx_row
        cells = "".join(
            f'<td class="cf">{v}</td>' if ci == 0 else f"<td>{v}</td>"
            for ci, v in enumerate(row))
        return f"<tr>{cells}</tr>"
    tbody = "".join(_row(x) for x in df_display.iterrows())
    st.markdown(
        f'{_TABLE_CSS}<div class="swag-wrap">'
        f'<table class="swag-tbl"><thead><tr>{th_}</tr></thead>'
        f'<tbody>{tbody}</tbody></table></div>',
        unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────────────────────
def show_login():
    _,_,lc = st.columns([2,1,0.5])
    with lc:
        lg = st.radio("",["EN","AR"],horizontal=True,
                      index=0 if get_lang()=="EN" else 1,
                      label_visibility="collapsed",key="llr")
        if lg!=get_lang(): st.session_state.lang=lg; st.rerun()

    _,col,_ = st.columns([1,1.1,1])
    with col:
        st.markdown("""
        <div style='display:flex;flex-direction:column;align-items:center;padding:20px 0 8px;'>
            <div class='login-orb'>📊</div>
            <div class='login-title'>SWAG Dashboard</div>
            <div class='login-subtitle'>Real-time Stock &amp; Price · 4 Odoo Systems</div>
        </div>""", unsafe_allow_html=True)
        wm = ("🌙 مرحباً بك — سجّل دخولك للمتابعة" if get_lang()=="AR"
              else "👋 Welcome back! Sign in to continue.")
        st.markdown(f"<div class='welcome-banner'>{wm}</div>", unsafe_allow_html=True)
        st.markdown("<div class='login-card'>", unsafe_allow_html=True)
        with st.form("lf", clear_on_submit=False):
            em = st.text_input(
                "📧 Email" if get_lang()=="EN" else "📧 البريد الإلكتروني",
                placeholder="you@swag.com.sa")
            pw = st.text_input(
                "🔑 Password" if get_lang()=="EN" else "🔑 كلمة المرور",
                type="password", placeholder="••••••••")
            st.markdown("<br>", unsafe_allow_html=True)
            sub = st.form_submit_button(
                "🚀 Sign In" if get_lang()=="EN" else "🚀 تسجيل الدخول",
                use_container_width=True, type="primary")
        st.markdown("</div>", unsafe_allow_html=True)
        if sub:
            if not em or not pw:
                st.error(t("Fill in both fields.","يرجى ملء جميع الحقول.")); return
            if "LOGIN" not in st.secrets:
                st.error("❌ [LOGIN] section missing in secrets.toml"); return
            cfg = st.secrets["LOGIN"]
            if "url" not in cfg or "db" not in cfg:
                st.error("❌ LOGIN.url or LOGIN.db missing in secrets.toml"); return
            with st.spinner(t("⚡ Signing in…","⚡ جارٍ تسجيل الدخول…")):
                try:
                    proxy = xmlrpc.client.ServerProxy(
                        f"{cfg['url']}/xmlrpc/2/common", allow_none=True)
                    uid = proxy.authenticate(cfg["db"], em, pw, {})
                    if uid:
                        token = _make_token(em)
                        st.query_params["u"] = em
                        st.query_params["t"] = token
                        st.session_state.authenticated = True
                        st.session_state.user_email    = em
                        time.sleep(0.3); st.balloons(); st.rerun()
                    else:
                        st.error(t("❌ Wrong email or password.",
                                   "❌ بريد إلكتروني أو كلمة مرور خاطئة."))
                except Exception as e:
                    st.error(f"❌ Connection error: {e}")
        st.markdown("""<p style='text-align:center;color:#4a4a6a;font-size:.75rem;margin-top:24px;'>
        © 2025 SWAG Fashion · Powered by Odoo · Built with ❤️</p>""",
                    unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────────────────────────────────────
def do_logout():
    try: st.query_params.clear()
    except Exception: pass
    st.session_state.authenticated = False
    st.session_state.user_email    = ""
    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def show_dashboard():
    with st.sidebar:
        st.markdown(f"### ⚙️ {t('Settings','الإعدادات')}")

        # ── THEME SWITCHER ────────────────────────────────────────────────────
        st.markdown(f"##### 🎨 {t('Theme','المظهر')}")
        current_theme = st.session_state.get("active_theme", THEME_NAMES[0])
        th_now = get_theme()
        for tname in THEME_NAMES:
            is_active = (tname == current_theme)
            label = f"{'✦ ' if is_active else ''}{tname}"
            btn_style = (
                f"background:{th_now['btn_grad']};background-size:300% auto;"
                f"color:white;border:none;box-shadow:0 4px 14px {th_now['accent1']}55;"
                if is_active else
                f"background:{th_now['glass_bg']};backdrop-filter:blur(8px);"
                f"color:{th_now['text_secondary']};border:1px solid {th_now['accent1']}44;"
            )
            st.markdown(
                f"<div style='margin-bottom:6px;'>"
                f"<span style='{btn_style}border-radius:20px;padding:6px 16px;"
                f"font-size:0.78rem;font-weight:700;display:inline-block;"
                f"width:100%;text-align:center;'>{label}</span></div>",
                unsafe_allow_html=True)
            if st.button(tname, key=f"theme_btn_{tname}", use_container_width=True,
                         type="primary" if is_active else "secondary"):
                st.session_state["active_theme"] = tname
                st.rerun()
        st.divider()
        lc2 = st.radio(t("🌐 Language","🌐 اللغة"),["EN","AR"],
                       index=0 if get_lang()=="EN" else 1, horizontal=True)
        if lc2!=get_lang(): st.session_state.lang=lc2; st.rerun()
        st.divider()
        st.markdown(f"👤 **{st.session_state.user_email}**")
        if st.button(f"🚪 {t('Logout','تسجيل الخروج')}", use_container_width=True):
            do_logout()
        st.divider()
        st.markdown(f"##### 🔬 {t('Search Mode','وضع البحث')}")
        et = st.toggle(t("Exact match only","تطابق تام فقط"), value=st.session_state.search_exact)
        if et!=st.session_state.search_exact:
            st.session_state.search_exact = et
            st.session_state.total_df     = None
            st.session_state.branch_df    = None
            st.session_state.transfers_df = None
            st.rerun()
        st.caption(t("🎯 Exact","🎯 تطابق تام") if st.session_state.search_exact
                   else t("🔍 Variant wildcard","🔍 كل المتغيرات"))
        st.divider()
        st.markdown(f"##### 🔴 {t('Low Stock Alert','تنبيه المخزون')}")
        thr = st.number_input(t("Threshold (qty ≤)","الحد (كمية ≤)"),
                              min_value=0, max_value=1000,
                              value=st.session_state.low_stock_thresh, step=1)
        if thr!=st.session_state.low_stock_thresh:
            st.session_state.low_stock_thresh = int(thr)

        # ── Feature 4: Filter Presets ─────────────────────────────────────────
        st.divider()
        st.markdown(f"##### 💾 {t('Filter Presets','إعدادات مسبقة')}")
        preset_name = st.text_input(t("Preset name","اسم الإعداد"), key="preset_name_input",
                                    placeholder=t("e.g. Low Stock View","مثال: عرض المخزون المنخفض"))
        if st.button(f"💾 {t('Save preset','حفظ الإعداد')}", use_container_width=True):
            if preset_name.strip():
                current_filters = {
                    "search_exact"       : st.session_state.search_exact,
                    "low_stock_thresh"   : st.session_state.low_stock_thresh,
                    "reorder_mode"       : st.session_state.reorder_mode,
                    "reorder_target_days": st.session_state.reorder_target_days,
                    "reorder_max_level"  : st.session_state.reorder_max_level,
                    "reorder_point"      : st.session_state.reorder_point,
                    "lang"               : st.session_state.lang,
                }
                st.session_state["filter_presets"][preset_name.strip()] = current_filters
                st.success(t(f"✅ Saved '{preset_name.strip()}'",
                             f"✅ تم حفظ '{preset_name.strip()}'"))

        presets = st.session_state.get("filter_presets", {})
        if presets:
            preset_options = ["— " + t("Select preset","اختر إعداداً")] + list(presets.keys())
            selected_preset = st.selectbox(
                t("Load preset","تحميل إعداد"), options=preset_options, key="load_preset_select")
            if (selected_preset and not selected_preset.startswith("—")
                    and st.button(f"📂 {t('Apply preset','تطبيق الإعداد')}", use_container_width=True)):
                pdata = presets[selected_preset]
                for k, v in pdata.items():
                    st.session_state[k] = v
                st.rerun()

        st.divider()
        if st.session_state.last_run:
            st.markdown(f"🕒 **{t('Last Run','آخر تشغيل')}**")
            st.caption(st.session_state.last_run.get("time",""))

    # ── Dashboard header ──────────────────────────────────────────────────────
    st.markdown(f"""
    <div class='dash-header'>
        <div class='dash-title'>📊 {t('SWAG Product Comparison','مقارنة منتجات سواغ')}</div>
        <div class='dash-subtitle'>{t('Real-time stock & price across 4 Odoo systems',
                                       'المخزون والسعر الآني عبر 4 أنظمة أودو')}</div>
    </div>""", unsafe_allow_html=True)
    st.divider()

    # ── PDF Upload ────────────────────────────────────────────────────────────
    st.markdown(f"### 📄 {t('Upload Invoice PDF','رفع فاتورة PDF')}")
    p1,p2 = st.columns([2.5,1.5])
    with p1:
        updf = st.file_uploader(t("Upload PDF","رفع PDF"), type=["pdf"],
                                label_visibility="collapsed")
    with p2:
        emode = None
        if updf:
            emode = st.radio(t("Extract mode","وضع الاستخراج"),
                             [t("Main models","موديلات رئيسية"),
                              t("With sizes","مع المقاسات")], horizontal=True)
    if updf:
        fbytes = updf.read()
        fhash  = hashlib.md5(fbytes).hexdigest()
        ck     = f"pdf_{fhash}"
        if ck not in st.session_state:
            with st.spinner(t("⚡ Parsing PDF...","⚡ جاري قراءة الفاتورة...")):
                st.session_state[ck] = parse_invoice_pdf_cached(fbytes)
        raw = st.session_state[ck]
        if raw:
            is_main = emode is None or "Main" in emode or "رئيسية" in emode
            if is_main:
                unique = get_unique_base_models(raw)
            else:
                seen_ws, unique = set(), []
                for item in raw:
                    if item["code"] not in seen_ws:
                        seen_ws.add(item["code"]); unique.append(item)
            unique_sorted = sorted(unique, key=lambda x: x["sequence"])
            unique_codes  = [item["code"] for item in unique_sorted]
            c1,c2,c3 = st.columns(3)
            c1.metric(t("Raw codes","رموز مستخرجة"), len(raw))
            c2.metric(t("Unique models","موديلات فريدة"), len(unique_codes))
            c3.info(f"📌 {t('Main','رئيسية') if is_main else t('With sizes','مع المقاسات')}")
            with st.expander(t(f"📋 {len(unique_codes)} codes","📋 الرموز"), expanded=False):
                st.code("\n".join(f"{item['sequence']:>3}. {item['code']}"
                                  for item in unique_sorted))
            ca,cb = st.columns(2)
            with ca:
                if st.button(f"🚀 {t('Total Stock','مخزون إجمالي')}",
                             type="primary", use_container_width=True, key="pt"):
                    st.session_state.pdf_codes = unique_codes
                    st.session_state.pdf_mode  = "total"; st.rerun()
            with cb:
                if st.button(f"🗺️ {t('Branch-wise','حسب الفرع')}",
                             type="secondary", use_container_width=True, key="pb"):
                    st.session_state.pdf_codes = unique_codes
                    st.session_state.pdf_mode  = "branch"; st.rerun()
        else:
            st.warning(t("No codes found in PDF.","لم يتم العثور على رموز."))
    st.divider()

    # ── Manual Search ─────────────────────────────────────────────────────────
    st.markdown(f"### ✍️ {t('Manual Search','بحث يدوي')}")
    L,R = st.columns([1.5,1])
    with L:
        if not st.session_state.search_exact:
            st.markdown("<div class='info-banner'>🔍 <b>Variant mode</b> — XP6013 → XP6013-S/M/L</div>",
                        unsafe_allow_html=True)
        else:
            st.markdown("<div class='warn-banner'>🎯 <b>Exact match mode</b> — identical codes only.</div>",
                        unsafe_allow_html=True)
        ms   = t("Single Model","موديل واحد")
        mm   = t("Multiple Models","موديلات متعددة")
        mode = st.radio(t("Mode","الوضع"),[ms,mm], horizontal=True, label_visibility="collapsed")
        if mode==mm:
            rt    = st.text_area(t("Codes","الرموز"), height=130, placeholder="ABC123\nDEF456")
            codes = [c.strip() for c in rt.replace(",","\n").splitlines() if c.strip()]
        else:
            # ── Feature 9: Smart search with recent queries ──
            rq = st.session_state.get("recent_queries", [])
            sg = st.text_input(t("Model Code","رمز الموديل"), placeholder="e.g. XP6013",
                               key="single_search_input")
            if rq:
                st.caption(f"🕐 {t('Recent:','الأخيرة:')}")
                rq_cols = st.columns(min(len(rq), 5))
                for ri, rqv in enumerate(rq):
                    if rq_cols[ri % 5].button(rqv, key=f"rq_{ri}_{rqv}"):
                        st.session_state["single_search_input_val"] = rqv
                        st.rerun()
            codes = [sg.strip()] if sg.strip() else []

        t1,t2,t3,t4,t5 = st.columns(5)
        sz  = t1.toggle(t("Zero","الصفري"),     value=False)
        sb  = t2.toggle(t("Branch","فروع"),      value=False)
        ss  = t3.toggle(t("Sort","ترتيب"),       value=False)
        st_ = t4.toggle(t("Transfers","نقليات"), value=False)
        sr  = t5.toggle(t("Reorder","طلب"),      value=False)
        if sr:
            with st.expander(f"⚙️ {t('Reorder Settings','إعدادات')}", expanded=True):
                rx,ry = st.columns(2)
                with rx:
                    rm = st.radio(
                        t("Mode","الوضع"),
                        [t("Days cover","تغطية أيام"),t("Max level","مستوى أقصى")],
                        horizontal=True,
                        index=0 if st.session_state.reorder_mode=="days_cover" else 1)
                    st.session_state.reorder_mode = (
                        "days_cover" if "Days" in rm or "تغطية" in rm else "max_level")
                with ry:
                    st.session_state.reorder_point = st.number_input(
                        t("Reorder point","نقطة الطلب"), min_value=0, max_value=9999,
                        value=st.session_state.reorder_point, step=1)
                if st.session_state.reorder_mode=="days_cover":
                    st.session_state.reorder_target_days = st.slider(
                        t("Target days","أيام"), 7, 180, st.session_state.reorder_target_days)
                else:
                    st.session_state.reorder_max_level = st.number_input(
                        t("Max level","الحد"), min_value=1, max_value=99999,
                        value=st.session_state.reorder_max_level, step=1)
        cbtn = st.button(f"🔍 {t('Compare','مقارنة')}", use_container_width=True, type="primary")

    with R:
        st.markdown(f"#### 📋 {t('Last Run','آخر تشغيل')}")
        snap  = st.session_state.last_run
        stats = st.session_state.sys_stats
        if not snap:
            st.info(t("Run a comparison first.","قم بتشغيل مقارنة أولاً."))
        else:
            on = sum(1 for v in stats.values() if v=="OK")
            st.markdown(
                f"<div class='snap-card'>"
                f"🕒 <b>{t('Time','الوقت')}:</b> {snap.get('time','—')}<br>"
                f"📦 <b>{t('Models','الموديلات')}:</b> {snap.get('models','—')}<br>"
                f"🌐 <b>{t('Online','متصل')}:</b> {on}/4<br>"
                f"📊 <b>{t('Rows','الصفوف')}:</b> {snap.get('rows','—')}"
                f"</div>", unsafe_allow_html=True)
            st.markdown("")
            for key in SYSTEM_KEYS:
                s  = stats.get(key,"—")
                bc = "badge-ok" if s=="OK" else "badge-off" if s=="NOT_FOUND" else "badge-err"
                bt = "✅ OK"    if s=="OK" else "🔴 OFF"    if s=="NOT_FOUND" else "⚠️ ERR"
                display_name = get_system_name(key)
                st.markdown(
                    f"<div class='sys-row'>"
                    f"<span style='font-size:.85rem;color:#e8e8ff'><b>{display_name}</b></span>"
                    f"<span class='{bc}'>{bt}</span></div>",
                    unsafe_allow_html=True)

    # ── Trigger run ───────────────────────────────────────────────────────────
    run_codes    = None
    force_branch = False
    if st.session_state.get("pdf_codes"):
        run_codes    = st.session_state.pdf_codes
        force_branch = st.session_state.get("pdf_mode","total") == "branch"
        sb = True
        st.session_state.pdf_codes = None
        st.session_state.pdf_mode  = "total"
    elif cbtn:
        run_codes = codes

    if run_codes is not None:
        if not run_codes:
            st.warning(t("Enter at least one model code.","أدخل رمزاً واحداً.")); st.stop()
        run_codes = list(dict.fromkeys([c.strip() for c in run_codes if c.strip()]))

        # ── Feature 9: record recent query ───────────────────────────────────
        for rc in run_codes:
            _push_recent_query(rc)

        ct = tuple(run_codes)
        with st.spinner(t("⚡ Fetching from 4 systems…","⚡ جلب البيانات من 4 أنظمة…")):
            data = fetch_all_data(
                ct, exact=st.session_state.search_exact,
                need_branch=sb or force_branch,
                need_transfers=st_, need_reorder=sr,
                reorder_mode=st.session_state.reorder_mode,
                target_days=st.session_state.reorder_target_days,
                max_level=st.session_state.reorder_max_level,
                reorder_point=st.session_state.reorder_point)

        tdf  = prepare_df(data["total"])
        bdf  = prepare_df(data["branch"])
        trdf = prepare_df(data["transfers"])
        rdf  = prepare_df(data["reorder"])

        sc2     = "System"
        raw_tdf = data["total"]
        ns = {k:"NOT_FOUND" for k in SYSTEM_KEYS}
        if "_status" in raw_tdf.columns and sc2 in raw_tdf.columns:
            for key in SYSTEM_KEYS:
                mask = raw_tdf[sc2] == key
                if mask.any():
                    sv = raw_tdf.loc[mask,"_status"]
                    if   "OK"    in sv.values: ns[key]="OK"
                    elif "ERROR" in sv.values: ns[key]="ERROR"

        qc2     = t("On Hand","متوفر")
        sc2_loc = t("System","النظام")
        mc_loc  = t("Model Code","رمز الموديل")

        if qc2 in tdf.columns:
            zero_mask = pd.to_numeric(tdf[qc2], errors="coerce").fillna(0) == 0
            tdf.loc[zero_mask, "_status"] = "not_available"

        if ss and sc2_loc in tdf.columns:
            tdf = tdf.sort_values(sc2_loc).reset_index(drop=True)
        if not bdf.empty and ss and sc2_loc in bdf.columns:
            bdf = bdf.sort_values(sc2_loc).reset_index(drop=True)

        if sz:
            zero_count = int((pd.to_numeric(tdf[qc2], errors="coerce").fillna(0) == 0).sum())
            if zero_count:
                st.sidebar.info(t(f"ℹ️ {zero_count} rows have zero qty (shown as ❌ Not Available)",
                                  f"ℹ️ {zero_count} صف بكمية صفر (معروض كـ ❌ لا يوجد)"))

        swag_system_name = get_system_name("SWAG")
        swag_mask        = (tdf[sc2_loc] == swag_system_name)

        if swag_mask.any():
            model_codes_swag = tdf.loc[swag_mask, mc_loc].dropna().unique().tolist()
            if model_codes_swag:
                end_date   = datetime.now().date()
                start_date = end_date - timedelta(days=365)
                with st.spinner(t("📦 Fetching purchase totals for SWAG models…",
                                  "📦 جلب إجمالي المشتريات لموديلات سواغ…")):
                    pur_summary = get_purchase_summary_by_model(
                        tuple(model_codes_swag),
                        start_date.strftime("%Y-%m-%d"),
                        end_date.strftime("%Y-%m-%d"))
                if not pur_summary.empty:
                    pur_renamed = pur_summary.rename(columns={"Model Code": mc_loc})
                    tdf = tdf.merge(pur_renamed[[mc_loc,"Purchase Qty"]], on=mc_loc, how="left")
                    tdf["Purchase Qty"] = tdf["Purchase Qty"].fillna(0).astype(int)
                    tdf.loc[~swag_mask, "Purchase Qty"] = 0
                else:
                    tdf["Purchase Qty"] = 0
            else:
                tdf["Purchase Qty"] = 0
        else:
            tdf["Purchase Qty"] = 0

        pur_col_name = t("Purchase Qty", "كمية المشتريات")
        tdf = tdf.rename(columns={"Purchase Qty": pur_col_name})

        desired_cols = [sc2_loc, mc_loc, t("Product","المنتج"),
                        t("Sale Price","سعر البيع"), pur_col_name, qc2]
        existing_cols = tdf.columns.tolist()
        final_cols    = [c for c in desired_cols if c in existing_cols]
        for c in existing_cols:
            if c not in final_cols: final_cols.append(c)
        tdf = tdf[final_cols]

        # ── Feature 6: add ABC classification ────────────────────────────────
        tdf = compute_abc_xyz(tdf)

        # ── Feature 10: save snapshot ─────────────────────────────────────────
        _prev_snap = st.session_state.get("last_snapshot")
        _new_snap  = _make_snapshot(tdf, int(thr))
        st.session_state["last_snapshot"] = _new_snap
        st.session_state["_prev_snapshot"] = _prev_snap

        st.session_state.total_df       = tdf
        st.session_state.branch_df      = bdf
        st.session_state.transfers_df   = trdf
        st.session_state.reorder_df     = rdf
        st.session_state.show_transfers = st_
        st.session_state.show_reorder   = sr
        st.session_state.sys_stats      = ns
        st.session_state.last_run       = {
            "time"  : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "models": len(run_codes),
            "rows"  : len(tdf),
        }
        record_price_snapshot(tdf)
        st.rerun()

    # ── Results ───────────────────────────────────────────────────────────────
    tdf  = st.session_state.total_df
    bdf  = st.session_state.branch_df
    trdf = st.session_state.transfers_df
    rdf  = st.session_state.reorder_df
    if tdf is None or tdf.empty: return

    st.divider()
    thr   = st.session_state.low_stock_thresh
    qc2   = t("On Hand","متوفر")
    pc2   = t("Sale Price","سعر البيع")
    sc2   = t("System","النظام")
    stats = st.session_state.sys_stats
    ok    = tdf[tdf["_status"]=="OK"] if "_status" in tdf.columns else tdf
    on    = sum(1 for v in stats.values() if v=="OK")

    if thr>0 and qc2 in ok.columns:
        low = ok[(ok[qc2]>0)&(ok[qc2]<=thr)]
        if not low.empty:
            mc2 = t("Model Code","رمز الموديل")
            det = ", ".join(
                f"{r.get(mc2,'?')}@{r.get(sc2,'?')}({r.get(qc2,0)})"
                for _,r in low.head(8).iterrows())
            if len(low)>8: det+=f" +{len(low)-8}"
            st.markdown(
                f"<div class='alert-banner'>🔴 <b>{t('Low Stock','مخزون منخفض')}:</b> "
                f"{len(low)} ≤{thr} — <span class='mono'>{det}</span></div>",
                unsafe_allow_html=True)

    # ── Feature 3: Multi-system KPI tiles ────────────────────────────────────
    st.markdown(f"#### 🏢 {t('System KPI Summary','ملخص مؤشرات الأنظمة')}")
    sys_kpi_cols = st.columns(len(SYSTEM_KEYS))
    sys_totals_qty = {}
    sys_totals_val = {}
    for ki, key in enumerate(SYSTEM_KEYS):
        sys_name = get_system_name(key)
        sys_rows = ok[ok[sc2] == sys_name] if sc2 in ok.columns else pd.DataFrame()
        sys_qty  = int(pd.to_numeric(sys_rows.get(qc2, pd.Series()), errors="coerce").fillna(0).sum())
        sys_prc  = pd.to_numeric(sys_rows.get(pc2, pd.Series()), errors="coerce").fillna(0)
        sys_qty_s= pd.to_numeric(sys_rows.get(qc2, pd.Series()), errors="coerce").fillna(0)
        sys_val  = float((sys_qty_s * sys_prc).sum())
        sys_totals_qty[key] = sys_qty
        sys_totals_val[key] = sys_val
        sys_kpi_cols[ki].metric(
            f"🏢 {sys_name}",
            f"{sys_qty:,} pcs",
            f"{sys_val:,.0f} SAR")

    # variance warning
    if sys_totals_qty:
        vals = list(sys_totals_qty.values())
        avg_qty = sum(vals) / len(vals) if vals else 0
        outliers = [get_system_name(k) for k, v in sys_totals_qty.items()
                    if avg_qty > 0 and abs(v - avg_qty) / avg_qty > 0.2]
        if outliers:
            st.markdown(
                f"<div class='warn-banner'>⚠️ {t('Systems differ >20% from average:','أنظمة تختلف أكثر من 20% عن المتوسط:')} "
                f"<b>{', '.join(outliers)}</b></div>",
                unsafe_allow_html=True)

    # ── Feature 10: Delta metrics vs last snapshot ────────────────────────────
    curr_snap = st.session_state.get("last_snapshot")
    prev_snap = st.session_state.get("_prev_snapshot")
    if curr_snap and prev_snap:
        st.markdown(f"#### 📈 {t('vs Last Run','مقارنة بآخر تشغيل')}")
        d1,d2,d3,d4 = st.columns(4)
        d1.metric(t("Total Qty","إجمالي الكمية"), curr_snap["total_qty"],
                  _delta_str(curr_snap, prev_snap, "total_qty"))
        d2.metric(t("Stock Value","قيمة المخزون"),
                  f"{curr_snap['total_val']:,.0f}",
                  _delta_str(curr_snap, prev_snap, "total_val", "pct"))
        d3.metric(t("Low Stock Items","منخفض المخزون"), curr_snap["low_stock"],
                  _delta_str(curr_snap, prev_snap, "low_stock"))
        d4.metric(t("Not Available","غير متوفر"), curr_snap["not_avail"],
                  _delta_str(curr_snap, prev_snap, "not_avail"))
        st.divider()

    m1,m2,m3,m4 = st.columns(4)
    m1.metric(t("Total Rows","إجمالي الصفوف"), len(tdf))
    m2.metric(t("Systems Online","الأنظمة"), f"{on}/4")
    if qc2 in ok.columns:
        m3.metric(t("Total Qty","إجمالي الكمية"),
                  int(pd.to_numeric(ok[qc2], errors="coerce").fillna(0).sum()))
    if pc2 in ok.columns:
        vp = ok[ok[pc2]>0][pc2]
        m4.metric(t("Avg Price","متوسط السعر"),
                  f"{vp.mean():.2f} SAR" if not vp.empty else "—")

    hb = bdf  is not None and not bdf.empty
    ht = st.session_state.show_transfers and trdf is not None and not trdf.empty
    hr = st.session_state.show_reorder   and rdf  is not None and not rdf.empty

    tlabels = [
        f"📦 {t('Total Stock','المخزون الإجمالي')}",
        f"📊 {t('Price History','تاريخ الأسعار')}",
    ]
    if hb:
        tlabels.append(f"🗺️ {t('Branch Stock','مخزون الفروع')}")
        tlabels.append(f"🌡️ {t('Branch Coverage','تغطية الفروع')}")   # Feature 2
    if ht: tlabels.append(f"🚚 {t('Transfers','النقليات')}")
    if hr: tlabels.append(f"📦 {t('Reorder','إعادة الطلب')}")
    tlabels.append(f"🔀 {t('What-if Simulator','محاكاة النقل')}")     # Feature 7
    tlabels.append(f"📝 {t('Planner Notes','ملاحظات المخطط')}")       # Feature 5
    tlabels.append(f"🛒 {t('SWAG Purchase','مشتريات سواغ')}")
    tlabels.append(f"🛍️ {t('SWAG Sales','مبيعات سواغ')}")

    tabs = st.tabs(tlabels)
    ti   = 0

    # ── Tab: Total Stock ──────────────────────────────────────────────────────
    with tabs[ti]:
        ti += 1
        st.markdown(f"### 📦 {t('Total Stock','المخزون الإجمالي')}")
        _filtered_total = display_df(tdf, thr, table_key="total", show_watchlist_toggle=True)
        st.markdown("<br>", unsafe_allow_html=True)
        d1,d2,d3,d4,d5 = st.columns([1,1,1,1,1])
        d1.download_button("⬇️ CSV", to_csv(tdf), dl_name("total","csv"), "text/csv",
                           use_container_width=True)
        d2.download_button("⬇️ Excel", to_excel(tdf), dl_name("total","xlsx"),
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
        d3.download_button("📥 All Systems", to_excel_bulk(tdf), dl_name("bulk","xlsx"),
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
        if _filtered_total is not None and not _filtered_total.empty:
            d4.download_button(
                f"🔍 {t('Filtered Excel','Excel المفلتر')}",
                to_excel(_filtered_total), dl_name("filtered_total","xlsx"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)
        else:
            d4.markdown("")
        # ── Feature 8: PDF Summary Export ────────────────────────────────────
        _pdf_data = generate_pdf_summary(tdf)
        if _pdf_data:
            d5.download_button(
                f"📄 {t('PDF Summary','ملخص PDF')}",
                _pdf_data, dl_name("summary","pdf"),
                mime="application/pdf",
                use_container_width=True)
        else:
            d5.caption(t("Install fpdf2 for PDF export","ثبّت fpdf2 لتصدير PDF"))

    # ── Tab: Price History ────────────────────────────────────────────────────
    with tabs[ti]:
        ti += 1
        st.markdown(f"### 📈 {t('Price History','تاريخ الأسعار')}")
        hdf = build_price_history_df()
        if hdf.empty:
            st.info(t("Run multiple comparisons to track prices.",
                      "قم بتشغيل مقارنات متعددة لتتبع الأسعار."))
        else:
            st.line_chart(hdf, use_container_width=True)
            if st.button(f"🗑️ {t('Clear History','مسح السجل')}"):
                st.session_state.price_history={}; st.rerun()

    # ── Tab: Branch Stock ─────────────────────────────────────────────────────
    if hb:
        with tabs[ti]:
            ti += 1
            st.markdown(f"### 🗺️ {t('Branch-wise Stock','مخزون حسب الفرع')}")
            _filtered_branch = display_df(bdf, thr, table_key="branch")
            bc2 = t("Branch","الفرع")
            okb = bdf[bdf["_status"]=="OK"] if "_status" in bdf.columns else bdf
            if not okb.empty and bc2 in okb.columns and qc2 in okb.columns:
                chart = okb.groupby([sc2,bc2])[qc2].sum().reset_index()
                if not chart.empty:
                    st.markdown(f"#### 📊 {t('Qty by Branch','الكميات حسب الفرع')}")
                    st.bar_chart(chart.set_index(bc2)[qc2], use_container_width=True)
            b1,b2,b3,b4 = st.columns([1,1,1,1])
            b1.download_button("⬇️ CSV", to_csv(bdf), dl_name("branch","csv"), "text/csv",
                               use_container_width=True)
            b2.download_button("⬇️ Excel", to_excel(bdf), dl_name("branch","xlsx"),
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)
            if _filtered_branch is not None and not _filtered_branch.empty:
                b3.download_button(
                    f"🔍 {t('Filtered Excel','Excel المفلتر')}",
                    to_excel(_filtered_branch), dl_name("filtered_branch","xlsx"),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True)
                b4.download_button(
                    f"📊 {t('Branch Matrix Excel','Excel مصفوفة الفروع')}",
                    to_excel_branch_matrix(_filtered_branch, get_lang()),
                    dl_name("branch_matrix","xlsx"),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True)
            else:
                b3.markdown(""); b4.markdown("")

        # ── Tab: Branch Coverage Heatmap (Feature 2) ──────────────────────────
        with tabs[ti]:
            ti += 1
            st.markdown(f"### 🌡️ {t('Branch Coverage Heatmap','خريطة تغطية الفروع')}")

            mc_col = t("Model Code","رمز الموديل")
            bc_col = t("Branch","الفرع")
            loc_c  = t("Location","الموقع")

            okb2 = bdf[bdf["_status"]=="OK"].copy() if "_status" in bdf.columns else bdf.copy()
            if okb2.empty:
                st.info(t("No branch data.","لا بيانات فروع."))
            else:
                pivot_c = loc_c if loc_c in okb2.columns else (bc_col if bc_col in okb2.columns else None)
                if pivot_c and mc_col in okb2.columns and qc2 in okb2.columns:
                    okb2[qc2] = pd.to_numeric(okb2[qc2], errors="coerce").fillna(0)
                    heat_piv = okb2.pivot_table(
                        index=mc_col, columns=pivot_c, values=qc2,
                        aggfunc="sum", fill_value=0)

                    # Branch Count summary column
                    heat_piv["Branch Count"] = (heat_piv > 0).sum(axis=1)
                    heat_piv = heat_piv.sort_values("Branch Count", ascending=False)

                    st.markdown(
                        f"<div class='info-banner'>📊 "
                        + t(f"{len(heat_piv)} models · {len(heat_piv.columns)-1} branches",
                            f"{len(heat_piv)} موديل · {len(heat_piv.columns)-1} فرع")
                        + "</div>", unsafe_allow_html=True)

                    bc_sum = heat_piv["Branch Count"].reset_index()
                    bc_sum.columns = [mc_col, "Branch Count"]
                    bc_top = bc_sum.head(15)
                    st.markdown(f"**{t('Top 15 – Branch Coverage','أعلى 15 – تغطية الفروع')}**")
                    st.bar_chart(bc_top.set_index(mc_col)["Branch Count"], use_container_width=True)

                    st.markdown(f"**{t('Coverage Heatmap (On-Hand Qty)','خريطة حرارية للكميات')}**")
                    try:
                        import plotly.express as px
                        heat_plot = heat_piv.drop(columns=["Branch Count"]).reset_index()
                        heat_melt = heat_plot.melt(id_vars=mc_col, var_name="Branch", value_name="Qty")
                        fig_h = px.density_heatmap(
                            heat_melt, x="Branch", y=mc_col, z="Qty",
                            color_continuous_scale="Viridis",
                            title=t("On-Hand Qty by Model & Branch","الكميات حسب الموديل والفرع"))
                        fig_h.update_layout(
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            font_color="#e8e8ff", title_font_color="#c4b5fd",
                            height=max(400, min(len(heat_piv)*22, 900)))
                        st.plotly_chart(fig_h, use_container_width=True)
                    except ImportError:
                        # Fallback: st.dataframe with background_gradient
                        display_heat = heat_piv.copy()
                        num_cols = [c for c in display_heat.columns if c != "Branch Count"]
                        st.dataframe(
                            display_heat.style.background_gradient(
                                cmap="YlOrRd", subset=num_cols, axis=None),
                            use_container_width=True)

                    st.markdown(f"**{t('Full Pivot Table','الجدول المحوري الكامل')}**")
                    st.dataframe(heat_piv, use_container_width=True)
                else:
                    st.info(t("Cannot build pivot — missing columns.","لا يمكن بناء الجدول المحوري."))

    # ── Tab: Transfers ────────────────────────────────────────────────────────
    if ht:
        with tabs[ti]:
            ti += 1
            st.markdown(f"### 🚚 {t('Pending Transfers','النقليات المعلقة')}")
            okt = trdf[trdf["_status"]=="OK"] if "_status" in trdf.columns else trdf
            if not okt.empty:
                k1,k2,k3 = st.columns(3)
                k1.metric(t("Total","إجمالي"), len(okt))
                qd = t("Qty","الكمية")
                if qd  in okt.columns: k2.metric(t("Total Qty","إجمالي الكمية"), int(okt[qd].sum()))
                if sc2 in okt.columns: k3.metric(t("Systems","الأنظمة"), okt[sc2].nunique())
            display_df(trdf, thresh=0, table_key="transfers")
            x1,x2,_ = st.columns([1,1,2])
            x1.download_button("⬇️ CSV", to_csv(trdf), dl_name("transfers","csv"), "text/csv",
                               use_container_width=True)
            x2.download_button("⬇️ Excel", to_excel(trdf), dl_name("transfers","xlsx"),
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)

    # ── Tab: Reorder ──────────────────────────────────────────────────────────
    if hr:
        with tabs[ti]:
            ti += 1
            CPRI  = t("Priority","الأولوية")
            CSUGG = t("Suggest","المقترح")
            st.markdown(f"### 📦 {t('Reorder Suggestions','اقتراحات إعادة الطلب')}")
            okr = rdf[rdf["_status"]=="OK"] if "_status" in rdf.columns else rdf
            if not okr.empty:
                crit = okr[okr[CPRI].str.startswith("🔴")].shape[0] if CPRI in okr.columns else 0
                lo   = okr[okr[CPRI].str.startswith("🟡")].shape[0] if CPRI in okr.columns else 0
                okn  = okr[okr[CPRI].str.startswith("🟢")].shape[0] if CPRI in okr.columns else 0
                sg   = int(okr[CSUGG].sum())                         if CSUGG in okr.columns else 0
                r1,r2,r3,r4 = st.columns(4)
                r1.metric(t("🔴 Critical","🔴 حرج"), crit)
                r2.metric(t("🟡 Low","🟡 منخفض"), lo)
                r3.metric(t("🟢 OK","🟢 كافٍ"), okn)
                r4.metric(t("To Order","للطلب"), sg)
                if crit+lo>0:
                    st.markdown(
                        f"<div class='alert-banner'>🔴 {crit+lo} "
                        f"{t('products need reordering','منتجات تحتاج إعادة طلب')}</div>",
                        unsafe_allow_html=True)
                sa = st.toggle(t("Show all","عرض الكل"), value=False)
                dr = (okr if sa else
                      okr[okr[CPRI].str.startswith(("🔴","🟡"))] if CPRI in okr.columns else okr)
                display_df(dr.reset_index(drop=True), table_key="reorder")
            else:
                st.info(t("No reorder data.","لا بيانات إعادة طلب."))
            o1,o2,_ = st.columns([1,1,2])
            o1.download_button("⬇️ CSV", to_csv(rdf), dl_name("reorder","csv"), "text/csv",
                               use_container_width=True)
            o2.download_button("⬇️ Excel", to_excel(rdf), dl_name("reorder","xlsx"),
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)

    # ── Tab: What-if Transfer Simulator (Feature 7) ───────────────────────────
    with tabs[ti]:
        ti += 1
        st.markdown(f"### 🔀 {t('What-if Transfer Simulator','محاكاة النقل الافتراضية')}")
        st.markdown(
            "<div class='info-banner'>📌 "
            + t("Purely analytic — no data is posted back to Odoo.",
                "للتحليل فقط — لا يتم إرسال أي بيانات إلى أودو.")
            + "</div>", unsafe_allow_html=True)

        if bdf is None or bdf.empty:
            st.info(t("Enable 'Branch' toggle and run a search first.",
                      "فعّل زر 'فروع' ثم قم بتشغيل البحث أولاً."))
        else:
            mc_col2 = t("Model Code","رمز الموديل")
            bc_col2 = t("Branch","الفرع")
            lc_col2 = t("Location","الموقع")
            qc_col2 = t("On Hand","متوفر")

            okb3 = bdf[bdf["_status"]=="OK"].copy() if "_status" in bdf.columns else bdf.copy()
            if okb3.empty:
                st.info(t("No OK branch data.","لا بيانات فروع صالحة."))
            else:
                pivot_c2 = lc_col2 if lc_col2 in okb3.columns else (bc_col2 if bc_col2 in okb3.columns else None)
                model_options = sorted(okb3[mc_col2].dropna().unique().tolist()) if mc_col2 in okb3.columns else []

                wa,wb,wc = st.columns([1.2,1.2,1])
                with wa:
                    sel_model = st.selectbox(
                        t("Select Model Code","اختر رمز الموديل"),
                        options=model_options, key="sim_model")
                branch_options = []
                if sel_model and pivot_c2:
                    model_rows = okb3[okb3[mc_col2] == sel_model]
                    branch_options = sorted(model_rows[pivot_c2].dropna().unique().tolist()) if pivot_c2 in model_rows.columns else []
                with wb:
                    from_branch = st.selectbox(
                        t("From branch","من الفرع"),
                        options=branch_options, key="sim_from")
                    to_branch   = st.selectbox(
                        t("To branch","إلى الفرع"),
                        options=branch_options, key="sim_to")
                with wc:
                    transfer_qty = st.number_input(
                        t("Transfer Qty","كمية النقل"),
                        min_value=1, max_value=99999, value=10, step=1, key="sim_qty")
                    simulate_btn = st.button(
                        f"🔀 {t('Simulate','محاكاة')}",
                        type="primary", use_container_width=True, key="sim_btn")

                if simulate_btn and sel_model and from_branch and to_branch:
                    if from_branch == to_branch:
                        st.warning(t("Source and destination branches must differ.",
                                     "الفرع المصدر والوجهة يجب أن يختلفا."))
                    else:
                        sim_df = okb3.copy()
                        sim_df[qc_col2] = pd.to_numeric(sim_df[qc_col2], errors="coerce").fillna(0)

                        src_mask = (sim_df[mc_col2] == sel_model) & (sim_df[pivot_c2] == from_branch)
                        dst_mask = (sim_df[mc_col2] == sel_model) & (sim_df[pivot_c2] == to_branch)

                        src_qty = int(sim_df.loc[src_mask, qc_col2].sum())
                        dst_qty = int(sim_df.loc[dst_mask, qc_col2].sum())

                        new_src = src_qty - transfer_qty
                        new_dst = dst_qty + transfer_qty

                        r1c, r2c, r3c = st.columns(3)
                        r1c.metric(
                            f"📤 {from_branch}",
                            f"{new_src} pcs",
                            f"{new_src - src_qty:+d} vs current")
                        r2c.metric(
                            f"📥 {to_branch}",
                            f"{new_dst} pcs",
                            f"{new_dst - dst_qty:+d} vs current")

                        below_thresh = new_src <= thr
                        if new_src < 0:
                            st.markdown(
                                f"<div class='alert-banner'>🚨 {t('Insufficient stock at source!','مخزون المصدر غير كافٍ!')} "
                                f"{t('Available:','المتاح:')} {src_qty} — {t('Requested:','المطلوب:')} {transfer_qty}</div>",
                                unsafe_allow_html=True)
                        elif below_thresh and thr > 0:
                            st.markdown(
                                f"<div class='warn-banner'>⚠️ {t('Source branch will fall below low-stock threshold','الفرع المصدر سينخفض دون حد المخزون المنخفض')} "
                                f"(≤{thr}): {new_src} {t('remaining','متبقي')}</div>",
                                unsafe_allow_html=True)
                        else:
                            st.markdown(
                                f"<div class='ok-banner'>✅ {t('Transfer feasible. Source stays above threshold.','النقل ممكن. المصدر يبقى فوق الحد.')}</div>",
                                unsafe_allow_html=True)

                        with r3c:
                            st.markdown(f"**{t('Current Stock','المخزون الحالي')}**")
                            st.markdown(f"• {from_branch}: **{src_qty}** → **{new_src}**")
                            st.markdown(f"• {to_branch}: **{dst_qty}** → **{new_dst}**")

    # ── Tab: Planner Notes (Feature 5) ────────────────────────────────────────
    with tabs[ti]:
        ti += 1
        st.markdown(f"### 📝 {t('Planner Notes','ملاحظات المخطط')}")
        mc_col3 = t("Model Code","رمز الموديل")
        notes = st.session_state.get("planner_notes", {})

        if tdf is not None and not tdf.empty and mc_col3 in tdf.columns:
            all_codes = sorted(tdf[mc_col3].dropna().unique().tolist())
        else:
            all_codes = []

        # Add / edit note
        with st.form("planner_note_form"):
            nc1,nc2 = st.columns([1,2])
            with nc1:
                note_model = st.selectbox(t("Model Code","رمز الموديل"), options=all_codes,
                                          key="note_model_sel")
            with nc2:
                note_text = st.text_area(t("Note","الملاحظة"), height=80,
                                         value=notes.get(note_model, "") if note_model else "",
                                         placeholder=t("Enter planner note here…","أدخل ملاحظة المخطط هنا…"),
                                         key="note_text_input")
            submitted = st.form_submit_button(f"💾 {t('Save Note','حفظ الملاحظة')}", type="primary")
            if submitted and note_model:
                st.session_state["planner_notes"][note_model] = note_text.strip()
                st.success(t(f"✅ Note saved for {note_model}",
                             f"✅ تم حفظ الملاحظة لـ {note_model}"))
                st.rerun()

        st.divider()
        if notes:
            st.markdown(f"#### {t('All Planner Notes','جميع ملاحظات المخطط')}")
            note_rows = [{"Model Code": k, "Note": v} for k, v in notes.items() if v]
            if note_rows:
                note_df = pd.DataFrame(note_rows)
                _render_html_table(note_df)
                if st.button(f"🗑️ {t('Clear all notes','مسح جميع الملاحظات')}"):
                    st.session_state["planner_notes"] = {}
                    st.rerun()
        else:
            st.info(t("No planner notes yet. Add one above.",
                      "لا توجد ملاحظات بعد. أضف ملاحظة من الأعلى."))

    # ── Tab: SWAG Purchase ────────────────────────────────────────────────────
    with tabs[ti]:
        ti += 1
        th_now = get_theme()
        st.markdown(f"### 🛒 {t('SWAG Purchase History','سجل مشتريات سواغ')}")
        st.markdown(
            "<div class='info-banner'>📌 "
            + t("Purchase orders from the <b>SWAG</b> system only (state: purchase / done).",
                "أوامر الشراء من نظام <b>سواغ</b> فقط (الحالة: مشترى / منجز).")
            + "</div>", unsafe_allow_html=True)

        pf1,pf2,pf3 = st.columns([1.5,1,1])
        with pf1:
            po_model_code = st.text_input(
                f"🔖 {t('Model Code (Internal Ref)','رمز الموديل (المرجع الداخلي)')}",
                placeholder=t("e.g. RVT196 — leave blank for all","مثال: RVT196 — اتركه فارغاً للكل"),
                key="po_model_code").strip()
        default_from = datetime.now().date() - timedelta(days=365)
        default_to   = datetime.now().date()
        with pf2:
            po_date_from = st.date_input(f"📅 {t('From','من')}", value=default_from, key="po_date_from")
        with pf3:
            po_date_to = st.date_input(f"📅 {t('To','إلى')}", value=default_to, key="po_date_to")
        fetch_po_btn = st.button(f"🔍 {t('Fetch Purchase Analytics','جلب تحليلات المشتريات')}",
                                 type="primary", use_container_width=False, key="fetch_po_btn")

        if fetch_po_btn:
            po_model_norm = po_model_code.upper() if po_model_code else None
            with st.spinner(t("⚡ Fetching purchase analytics from SWAG…","⚡ جلب تحليلات المشتريات من نظام سواغ…")):
                _po = fetch_swag_purchase_history(
                    model_code=po_model_norm,
                    date_from=po_date_from.strftime("%Y-%m-%d"),
                    date_to=po_date_to.strftime("%Y-%m-%d"))
            st.session_state["po_analytics_df"] = _po

        po_df = st.session_state.get("po_analytics_df")

        if po_df is None or (isinstance(po_df, pd.DataFrame) and po_df.empty):
            st.info(t("No purchases found. Click Fetch to load.", "لا مشتريات. اضغط جلب للتحميل."))
        else:
            # ── KPI row ───────────────────────────────────────────────────────
            km1,km2,km3,km4 = st.columns(4)
            km1.metric(t("Total Qty Purchased","إجمالي الكمية المشتراة"),   f"{float(po_df['Qty'].sum()):,.0f}")
            km2.metric(t("Total Purchase Amount","إجمالي مبلغ الشراء"),     f"{float(po_df['Subtotal'].sum()):,.2f} SAR")
            km3.metric(t("Distinct Products","عدد المنتجات"),                int(po_df["Model Code"].nunique()))
            km4.metric(t("Distinct Vendors","عدد الموردين"),                 int(po_df["Vendor"].nunique()))
            st.divider()

            try:
                import plotly.express as px
                import plotly.graph_objects as go

                _accent1 = th_now["accent1"]
                _accent2 = th_now["accent2"]
                _accent3 = th_now["accent3"]
                _text_p  = th_now["text_primary"]
                _text_s  = th_now["text_secondary"]
                _glass   = th_now["glass_bg"]
                _chart_layout = dict(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color=_text_s, family="IBM Plex Sans Arabic"),
                    title_font=dict(color=_text_p, size=15),
                    legend=dict(font=dict(color=_text_s), bgcolor="rgba(0,0,0,0)"),
                    xaxis=dict(gridcolor="rgba(255,255,255,0.06)", color=_text_s,
                               tickfont=dict(color=_text_s)),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.06)", color=_text_s,
                               tickfont=dict(color=_text_s)),
                    margin=dict(l=10,r=10,t=40,b=10),
                    height=340,
                )
                _bar_colors = [_accent1, _accent2, _accent3,
                               "#ff6b9d","#c77dff","#48cae4","#90e0ef","#06d6a0","#ffd166","#ef476f"]

                # ── Row 1: Top 10 products qty + subtotal ─────────────────────
                st.markdown(f"#### 📊 {t('Purchase Analytics','تحليلات المشتريات')}")
                r1c1, r1c2 = st.columns(2)

                prod_grp = (po_df.groupby("Model Code", as_index=False)["Qty"].sum()
                            .sort_values("Qty", ascending=False).head(10))
                with r1c1:
                    fig1 = go.Figure(go.Bar(
                        x=prod_grp["Model Code"], y=prod_grp["Qty"],
                        marker=dict(color=_bar_colors[:len(prod_grp)],
                                    line=dict(width=0)),
                        text=prod_grp["Qty"].map(lambda v: f"{v:,.0f}"),
                        textposition="outside", textfont=dict(color=_text_s, size=10)))
                    fig1.update_layout(**_chart_layout,
                        title=t("Top 10 — Qty Purchased","أعلى 10 — الكمية المشتراة"),
                        bargap=0.3)
                    fig1.update_xaxes(tickangle=-35)
                    st.plotly_chart(fig1, use_container_width=True)

                prod_val = (po_df.groupby("Model Code", as_index=False)["Subtotal"].sum()
                            .sort_values("Subtotal", ascending=False).head(10))
                with r1c2:
                    fig2 = go.Figure(go.Bar(
                        x=prod_val["Model Code"], y=prod_val["Subtotal"],
                        marker=dict(
                            color=prod_val["Subtotal"],
                            colorscale=[[0,_accent2],[0.5,_accent1],[1,_accent3]],
                            showscale=False,
                            line=dict(width=0)),
                        text=prod_val["Subtotal"].map(lambda v: f"{v:,.0f}"),
                        textposition="outside", textfont=dict(color=_text_s, size=10)))
                    fig2.update_layout(**_chart_layout,
                        title=t("Top 10 — Purchase Value (SAR)","أعلى 10 — قيمة الشراء"),
                        bargap=0.3)
                    fig2.update_xaxes(tickangle=-35)
                    st.plotly_chart(fig2, use_container_width=True)

                # ── Row 2: Vendor + Category ──────────────────────────────────
                r2c1, r2c2 = st.columns(2)

                vendor_grp = (po_df.groupby("Vendor", as_index=False)
                              .agg(Qty=("Qty","sum"), Amount=("Subtotal","sum"))
                              .sort_values("Amount", ascending=False).head(10))
                with r2c1:
                    fig3 = go.Figure(go.Bar(
                        y=vendor_grp["Vendor"], x=vendor_grp["Amount"],
                        orientation="h",
                        marker=dict(
                            color=vendor_grp["Amount"],
                            colorscale=[[0,_accent2],[1,_accent1]],
                            showscale=False,
                            line=dict(width=0)),
                        text=vendor_grp["Amount"].map(lambda v: f"{v:,.0f} SAR"),
                        textposition="outside", textfont=dict(color=_text_s, size=9)))
                    fig3.update_layout(**_chart_layout,
                        title=t("Top 10 Vendors — Amount","أعلى 10 موردين — المبلغ"),
                        xaxis=dict(gridcolor="rgba(255,255,255,0.06)", color=_text_s,
                                   tickfont=dict(color=_text_s)),
                        yaxis=dict(gridcolor="rgba(255,255,255,0.06)", color=_text_s,
                                   tickfont=dict(color=_text_s), autorange="reversed"))
                    st.plotly_chart(fig3, use_container_width=True)

                cat_grp = (po_df.assign(Category=po_df["Category"].replace("","(No Category)").fillna("(No Category)"))
                           .groupby("Category", as_index=False)["Qty"].sum()
                           .sort_values("Qty", ascending=False).head(10))
                with r2c2:
                    fig4 = go.Figure(go.Pie(
                        labels=cat_grp["Category"], values=cat_grp["Qty"],
                        hole=0.45,
                        marker=dict(colors=_bar_colors[:len(cat_grp)],
                                    line=dict(color="rgba(0,0,0,0.3)", width=1)),
                        textfont=dict(color="#ffffff", size=10),
                        hovertemplate="%{label}<br>Qty: %{value:,.0f}<br>%{percent}<extra></extra>"))
                    fig4.update_layout(**_chart_layout,
                        title=t("Qty by Category","الكمية حسب الفئة"),
                        showlegend=True,
                        legend=dict(font=dict(color=_text_s, size=9),
                                    bgcolor="rgba(0,0,0,0)"))
                    st.plotly_chart(fig4, use_container_width=True)

                # ── Row 3: Brand Category + Monthly trend ─────────────────────
                r3c1, r3c2 = st.columns(2)

                brand_grp = (po_df.assign(**{"Brand Category": po_df["Brand Category"].replace("","(No Brand)").fillna("(No Brand)")})
                             .groupby("Brand Category", as_index=False)["Qty"].sum()
                             .sort_values("Qty", ascending=False).head(10))
                with r3c1:
                    fig5 = go.Figure(go.Bar(
                        x=brand_grp["Brand Category"], y=brand_grp["Qty"],
                        marker=dict(
                            color=brand_grp["Qty"],
                            colorscale=[[0,_accent2],[0.5,_accent1],[1,_accent3]],
                            showscale=True,
                            colorbar=dict(tickfont=dict(color=_text_s),
                                          title=dict(text="Qty", font=dict(color=_text_s))),
                            line=dict(width=0)),
                        text=brand_grp["Qty"].map(lambda v: f"{v:,.0f}"),
                        textposition="outside", textfont=dict(color=_text_s, size=9)))
                    fig5.update_layout(**_chart_layout,
                        title=t("Qty by Brand Category","الكمية حسب فئة العلامة"),
                        bargap=0.25)
                    fig5.update_xaxes(tickangle=-35)
                    st.plotly_chart(fig5, use_container_width=True)

                # Monthly trend
                _po_trend = po_df.copy()
                _po_trend["Date_parsed"] = pd.to_datetime(_po_trend["Date"], errors="coerce")
                _po_trend = _po_trend.dropna(subset=["Date_parsed"])
                if not _po_trend.empty:
                    _po_trend["Month"] = _po_trend["Date_parsed"].dt.to_period("M").astype(str)
                    monthly = (_po_trend.groupby("Month", as_index=False)
                               .agg(Qty=("Qty","sum"), Amount=("Subtotal","sum"))
                               .sort_values("Month"))
                    with r3c2:
                        fig6 = go.Figure()
                        fig6.add_trace(go.Scatter(
                            x=monthly["Month"], y=monthly["Qty"],
                            name=t("Qty","الكمية"),
                            mode="lines+markers",
                            line=dict(color=_accent1, width=2.5),
                            marker=dict(size=7, color=_accent1,
                                        line=dict(color=_accent3, width=1.5)),
                            fill="tozeroy",
                            fillcolor=f"rgba({int(_accent1[1:3],16)},{int(_accent1[3:5],16)},{int(_accent1[5:7],16)},0.08)",
                            hovertemplate="%{x}<br>Qty: %{y:,.0f}<extra></extra>"))
                        fig6.add_trace(go.Scatter(
                            x=monthly["Month"], y=monthly["Amount"],
                            name=t("Amount SAR","المبلغ"),
                            mode="lines+markers",
                            line=dict(color=_accent3, width=2, dash="dot"),
                            marker=dict(size=6, color=_accent3),
                            yaxis="y2",
                            hovertemplate="%{x}<br>Amount: %{y:,.0f} SAR<extra></extra>"))
                        fig6.update_layout(**_chart_layout,
                            title=t("Monthly Purchase Trend","اتجاه المشتريات الشهري"),
                            yaxis=dict(title=t("Qty","الكمية"), gridcolor="rgba(255,255,255,0.06)",
                                       color=_text_s, tickfont=dict(color=_text_s)),
                            yaxis2=dict(title="SAR", overlaying="y", side="right",
                                        gridcolor="rgba(0,0,0,0)", color=_text_s,
                                        tickfont=dict(color=_text_s)),
                            legend=dict(font=dict(color=_text_s), bgcolor="rgba(0,0,0,0)"))
                        fig6.update_xaxes(tickangle=-35)
                        st.plotly_chart(fig6, use_container_width=True)
                else:
                    with r3c2:
                        st.info(t("No date data for trend.", "لا تواريخ للرسم البياني."))

            except ImportError:
                st.info(t("Install plotly for charts: pip install plotly",
                          "ثبّت plotly للرسوم البيانية: pip install plotly"))
                # plain fallback charts
                prod_grp_f = (po_df.groupby("Model Code", as_index=False)["Qty"].sum()
                              .sort_values("Qty", ascending=False).head(10))
                st.bar_chart(prod_grp_f.set_index("Model Code")["Qty"], use_container_width=True)

            # ── Paginated full detail table ───────────────────────────────────
            st.divider()
            st.markdown(f"#### 📋 {t('Full Purchase Detail','تفاصيل المشتريات الكاملة')}")

            PAGE_SIZE = 50
            total_rows = len(po_df)
            total_pages = max(1, -(-total_rows // PAGE_SIZE))  # ceiling div

            # search + page controls
            fc1, fc2, fc3 = st.columns([2, 1, 1])
            with fc1:
                po_search = st.text_input(
                    f"🔍 {t('Search','بحث')}",
                    placeholder=t("Model / Vendor / PO / Category…","موديل / مورد / أمر شراء…"),
                    key="po_tbl_search").strip().lower()
            with fc2:
                po_sort_col = st.selectbox(
                    f"↕️ {t('Sort by','ترتيب')}",
                    options=["Date","Model Code","Vendor","Qty","Subtotal"],
                    key="po_sort_col")
            with fc3:
                po_sort_asc = st.radio(
                    t("Order","الترتيب"), ["↓ Desc","↑ Asc"],
                    horizontal=True, key="po_sort_asc") == "↑ Asc"

            # filter
            _show_po = po_df.copy()
            if po_search:
                _mask = pd.Series([False]*len(_show_po), index=_show_po.index)
                for _col in ["Model Code","Vendor","PO","Category","Brand Category","Product"]:
                    if _col in _show_po.columns:
                        _mask |= _show_po[_col].fillna("").str.lower().str.contains(po_search, regex=False)
                _show_po = _show_po[_mask]

            # sort
            if po_sort_col in _show_po.columns:
                _show_po = _show_po.sort_values(po_sort_col, ascending=po_sort_asc)

            total_filtered = len(_show_po)
            total_pages_f  = max(1, -(-total_filtered // PAGE_SIZE))

            pg_col1, pg_col2, pg_col3 = st.columns([1, 2, 1])
            with pg_col2:
                po_page = st.number_input(
                    f"📄 {t('Page','الصفحة')} (1 – {total_pages_f})",
                    min_value=1, max_value=total_pages_f,
                    value=1, step=1, key="po_page_num")

            start_idx = (po_page - 1) * PAGE_SIZE
            end_idx   = start_idx + PAGE_SIZE
            page_data = _show_po.iloc[start_idx:end_idx].copy()

            # format for display
            disp_po = page_data.copy()
            if "Unit Price" in disp_po.columns:
                disp_po["Unit Price"] = disp_po["Unit Price"].map(lambda v: f"{float(v):.2f} SAR" if pd.notna(v) else "—")
            if "Subtotal" in disp_po.columns:
                disp_po["Subtotal"]   = disp_po["Subtotal"].map(lambda v: f"{float(v):,.2f} SAR" if pd.notna(v) else "—")
            if "Qty" in disp_po.columns:
                disp_po["Qty"]        = disp_po["Qty"].map(lambda v: f"{float(v):,.0f}" if pd.notna(v) else "—")

            cols_po  = disp_po.columns.tolist()
            th_po    = "".join(f"<th>{c}</th>" for c in cols_po)
            rows_po  = "".join(
                f"<tr>{''.join(f'<td class=\"cf\">{v}</td>' if ci==0 else f'<td>{v}</td>' for ci,v in enumerate(r))}</tr>"
                for r in disp_po.values)
            st.markdown(
                f'{_TABLE_CSS}<div class="swag-wrap">'
                f'<table class="swag-tbl"><thead><tr>{th_po}</tr></thead>'
                f'<tbody>{rows_po}</tbody></table></div>',
                unsafe_allow_html=True)

            st.caption(
                f"📊 {t('Showing','عرض')} {start_idx+1}–{min(end_idx,total_filtered)} "
                f"{t('of','من')} {total_filtered} {t('rows','صفوف')} "
                f"· {t('Page','الصفحة')} {po_page}/{total_pages_f}")

            # prev / next buttons
            pn1, pn2, pn3 = st.columns([1,2,1])
            with pn1:
                if po_page > 1 and st.button(f"◀ {t('Prev','السابق')}", key="po_prev"):
                    st.session_state["po_page_num"] = po_page - 1; st.rerun()
            with pn3:
                if po_page < total_pages_f and st.button(f"{t('Next','التالي')} ▶", key="po_next"):
                    st.session_state["po_page_num"] = po_page + 1; st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            dl1,dl2,_ = st.columns([1,1,2])
            dl1.download_button("⬇️ CSV (All)",
                po_df.to_csv(index=False).encode("utf-8-sig"),
                dl_name("purchase","csv"), "text/csv", use_container_width=True)
            dl2.download_button("⬇️ Excel (All)",
                to_excel_purchase(po_df), dl_name("purchase","xlsx"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)

    # ── Tab: SWAG Sales ────────────────────────────────────────────────────────
    with tabs[ti]:
        ti += 1
        th_now = get_theme()
        st.markdown(f"### 🛍️ {t('SWAG Sales Analytics','تحليلات مبيعات سواغ')}")
        st.markdown(
            "<div class='info-banner'>📌 "
            + t("Sales orders from the <b>SWAG</b> system only (state: sale / done).",
                "أوامر البيع من نظام <b>سواغ</b> فقط (الحالة: مباع / منجز).")
            + "</div>", unsafe_allow_html=True)

        so_col1,so_col2,so_col3,so_col4 = st.columns([1,1,1.5,0.8])
        _today       = datetime.now().date()
        _first_month = _today.replace(day=1)
        with so_col1:
            so_date_from = st.date_input(f"📅 {t('From','من')}", value=_first_month, key="so_date_from")
        with so_col2:
            so_date_to = st.date_input(f"📅 {t('To','إلى')}", value=_today, key="so_date_to")
        with so_col3:
            so_model_filter = st.text_input(
                f"🔖 {t('Model Code (optional)','رمز الموديل (اختياري)')}",
                placeholder=t("e.g. XP6013 — leave blank for all","مثال: XP6013 — اتركه فارغاً للكل"),
                key="so_model_filter").strip()
        with so_col4:
            fetch_so_btn = st.button(f"🔍 {t('Fetch Sales','جلب المبيعات')}",
                                     type="primary", use_container_width=True, key="fetch_so_btn")

        if fetch_so_btn:
            _model_norm = so_model_filter.upper() if so_model_filter else None
            with st.spinner(t("⚡ Fetching sales from SWAG…","⚡ جلب بيانات المبيعات من سواغ…")):
                _so_df = fetch_swag_sales_history(
                    model_code=_model_norm,
                    date_from=so_date_from.strftime("%Y-%m-%d"),
                    date_to=so_date_to.strftime("%Y-%m-%d"))
            st.session_state["so_analytics_df"] = _so_df
            st.session_state["so_last_model"]   = so_model_filter

        so_df = st.session_state.get("so_analytics_df")

        if so_df is None or (isinstance(so_df, pd.DataFrame) and so_df.empty):
            st.info(t("Click 'Fetch Sales' to load data.", "اضغط 'جلب المبيعات' لتحميل البيانات."))
        else:
            # ensure numeric
            so_df = so_df.copy()
            so_df["Qty"]      = pd.to_numeric(so_df["Qty"],      errors="coerce").fillna(0)
            so_df["Subtotal"] = pd.to_numeric(so_df["Subtotal"], errors="coerce").fillna(0)
            so_df["Unit Price"]= pd.to_numeric(so_df["Unit Price"],errors="coerce").fillna(0)
            so_df["Date"]     = pd.to_datetime(so_df["Date"],    errors="coerce")

            # ── KPI ──────────────────────────────────────────────────────────
            sk1,sk2,sk3,sk4 = st.columns(4)
            sk1.metric(t("Total Qty Sold","إجمالي الكميات المباعة"),   f"{so_df['Qty'].sum():,.0f}")
            sk2.metric(t("Total Sales Amount","إجمالي مبلغ المبيعات"), f"{so_df['Subtotal'].sum():,.2f} SAR")
            sk3.metric(t("Distinct Customers","عدد العملاء"),           int(so_df["Customer"].nunique()))
            sk4.metric(t("Distinct Products","عدد المنتجات"),           int(so_df["Model Code"].nunique()))
            st.divider()

            try:
                import plotly.express as px
                import plotly.graph_objects as go

                _accent1 = th_now["accent1"]
                _accent2 = th_now["accent2"]
                _accent3 = th_now["accent3"]
                _text_p  = th_now["text_primary"]
                _text_s  = th_now["text_secondary"]
                _bar_colors = [_accent1, _accent2, _accent3,
                               "#ff6b9d","#c77dff","#48cae4","#90e0ef","#06d6a0","#ffd166","#ef476f"]
                _chart_layout = dict(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color=_text_s, family="IBM Plex Sans Arabic"),
                    title_font=dict(color=_text_p, size=15),
                    legend=dict(font=dict(color=_text_s), bgcolor="rgba(0,0,0,0)"),
                    xaxis=dict(gridcolor="rgba(255,255,255,0.06)", color=_text_s,
                               tickfont=dict(color=_text_s)),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.06)", color=_text_s,
                               tickfont=dict(color=_text_s)),
                    margin=dict(l=10,r=10,t=44,b=10),
                    height=340,
                )

                # ── Row 1: Top products qty + revenue ────────────────────────
                st.markdown(f"#### 📊 {t('Sales Analytics','تحليلات المبيعات')}")
                s1c1, s1c2 = st.columns(2)

                top_qty = (so_df.groupby("Model Code", as_index=False)["Qty"].sum()
                           .sort_values("Qty", ascending=False).head(10))
                with s1c1:
                    fig_sq = go.Figure(go.Bar(
                        x=top_qty["Model Code"], y=top_qty["Qty"],
                        marker=dict(color=_bar_colors[:len(top_qty)], line=dict(width=0)),
                        text=top_qty["Qty"].map(lambda v: f"{v:,.0f}"),
                        textposition="outside", textfont=dict(color=_text_s, size=10)))
                    fig_sq.update_layout(**_chart_layout,
                        title=t("Top 10 — Qty Sold","أعلى 10 — الكمية المباعة"), bargap=0.3)
                    fig_sq.update_xaxes(tickangle=-35)
                    st.plotly_chart(fig_sq, use_container_width=True)

                top_rev = (so_df.groupby("Model Code", as_index=False)["Subtotal"].sum()
                           .sort_values("Subtotal", ascending=False).head(10))
                with s1c2:
                    fig_sr = go.Figure(go.Bar(
                        x=top_rev["Model Code"], y=top_rev["Subtotal"],
                        marker=dict(color=top_rev["Subtotal"],
                                    colorscale=[[0,_accent2],[0.5,_accent1],[1,_accent3]],
                                    showscale=False, line=dict(width=0)),
                        text=top_rev["Subtotal"].map(lambda v: f"{v:,.0f}"),
                        textposition="outside", textfont=dict(color=_text_s, size=10)))
                    fig_sr.update_layout(**_chart_layout,
                        title=t("Top 10 — Revenue (SAR)","أعلى 10 — الإيراد"), bargap=0.3)
                    fig_sr.update_xaxes(tickangle=-35)
                    st.plotly_chart(fig_sr, use_container_width=True)

                # ── Row 2: Branch performance ─────────────────────────────────
                s2c1, s2c2 = st.columns(2)
                branch_grp = (so_df.fillna({"Branch":"Unknown"})
                              .groupby("Branch", as_index=False)
                              .agg(Qty=("Qty","sum"), Revenue=("Subtotal","sum"))
                              .sort_values("Revenue", ascending=False).head(10))
                with s2c1:
                    fig_bq = go.Figure(go.Bar(
                        y=branch_grp["Branch"], x=branch_grp["Qty"],
                        orientation="h",
                        marker=dict(color=branch_grp["Qty"],
                                    colorscale=[[0,_accent2],[1,_accent1]],
                                    showscale=False, line=dict(width=0)),
                        text=branch_grp["Qty"].map(lambda v: f"{v:,.0f}"),
                        textposition="outside", textfont=dict(color=_text_s, size=9)))
                    fig_bq.update_layout(**_chart_layout,
                        title=t("Branch — Qty Sold","الفروع — الكمية المباعة"),
                        yaxis=dict(autorange="reversed", gridcolor="rgba(255,255,255,0.06)",
                                   color=_text_s, tickfont=dict(color=_text_s)))
                    st.plotly_chart(fig_bq, use_container_width=True)
                with s2c2:
                    fig_br = go.Figure(go.Bar(
                        y=branch_grp["Branch"], x=branch_grp["Revenue"],
                        orientation="h",
                        marker=dict(color=branch_grp["Revenue"],
                                    colorscale=[[0,_accent2],[0.5,_accent1],[1,_accent3]],
                                    showscale=False, line=dict(width=0)),
                        text=branch_grp["Revenue"].map(lambda v: f"{v:,.0f}"),
                        textposition="outside", textfont=dict(color=_text_s, size=9)))
                    fig_br.update_layout(**_chart_layout,
                        title=t("Branch — Revenue (SAR)","الفروع — الإيراد"),
                        yaxis=dict(autorange="reversed", gridcolor="rgba(255,255,255,0.06)",
                                   color=_text_s, tickfont=dict(color=_text_s)))
                    st.plotly_chart(fig_br, use_container_width=True)

                # ── Row 3: Brand + Category Donut ────────────────────────────
                s3c1, s3c2 = st.columns(2)
                brand_grp = (so_df.assign(**{"Brand Category": so_df["Brand Category"].fillna("(No Brand)").replace("","(No Brand)")})
                             .groupby("Brand Category", as_index=False)["Subtotal"].sum()
                             .sort_values("Subtotal", ascending=False))
                if len(brand_grp) > 9:
                    _b_top  = brand_grp.head(8).copy()
                    _b_oth  = pd.DataFrame([{"Brand Category":"Others","Subtotal":brand_grp.iloc[8:]["Subtotal"].sum()}])
                    brand_grp = pd.concat([_b_top,_b_oth], ignore_index=True)
                with s3c1:
                    fig_bc = go.Figure(go.Pie(
                        labels=brand_grp["Brand Category"], values=brand_grp["Subtotal"],
                        hole=0.48,
                        marker=dict(colors=_bar_colors[:len(brand_grp)],
                                    line=dict(color="rgba(0,0,0,0.3)", width=1)),
                        textfont=dict(color="#fff", size=10),
                        hovertemplate="%{label}<br>%{value:,.0f} SAR<br>%{percent}<extra></extra>"))
                    fig_bc.update_layout(**_chart_layout,
                        title=t("Revenue by Brand Category","الإيراد حسب فئة العلامة"),
                        showlegend=True,
                        legend=dict(font=dict(color=_text_s, size=9), bgcolor="rgba(0,0,0,0)"))
                    st.plotly_chart(fig_bc, use_container_width=True)

                cat_grp_s = (so_df.assign(Category=so_df["Category"].fillna("(No Category)").replace("","(No Category)"))
                             .groupby("Category", as_index=False)["Qty"].sum()
                             .sort_values("Qty", ascending=False))
                if len(cat_grp_s) > 9:
                    _c_top = cat_grp_s.head(8).copy()
                    _c_oth = pd.DataFrame([{"Category":"Others","Qty":cat_grp_s.iloc[8:]["Qty"].sum()}])
                    cat_grp_s = pd.concat([_c_top,_c_oth], ignore_index=True)
                with s3c2:
                    fig_cd = go.Figure(go.Pie(
                        labels=cat_grp_s["Category"], values=cat_grp_s["Qty"],
                        hole=0.48,
                        marker=dict(colors=_bar_colors[:len(cat_grp_s)],
                                    line=dict(color="rgba(0,0,0,0.3)", width=1)),
                        textfont=dict(color="#fff", size=10),
                        hovertemplate="%{label}<br>Qty: %{value:,.0f}<br>%{percent}<extra></extra>"))
                    fig_cd.update_layout(**_chart_layout,
                        title=t("Qty by Category","الكمية حسب الفئة"),
                        showlegend=True,
                        legend=dict(font=dict(color=_text_s, size=9), bgcolor="rgba(0,0,0,0)"))
                    st.plotly_chart(fig_cd, use_container_width=True)

                # ── Row 4: Top Customers + Daily Trend ───────────────────────
                s4c1, s4c2 = st.columns(2)
                cust_grp = (so_df.fillna({"Customer":"Unknown"})
                            .groupby("Customer", as_index=False)["Subtotal"].sum()
                            .sort_values("Subtotal", ascending=False).head(10))
                with s4c1:
                    fig_cu = go.Figure(go.Bar(
                        y=cust_grp["Customer"], x=cust_grp["Subtotal"],
                        orientation="h",
                        marker=dict(color=cust_grp["Subtotal"],
                                    colorscale=[[0,_accent2],[0.5,_accent1],[1,_accent3]],
                                    showscale=False, line=dict(width=0)),
                        text=cust_grp["Subtotal"].map(lambda v: f"{v:,.0f}"),
                        textposition="outside", textfont=dict(color=_text_s, size=9)))
                    fig_cu.update_layout(**_chart_layout,
                        title=t("Top 10 Customers — Revenue","أعلى 10 عملاء — الإيراد"),
                        yaxis=dict(autorange="reversed", gridcolor="rgba(255,255,255,0.06)",
                                   color=_text_s, tickfont=dict(color=_text_s)))
                    st.plotly_chart(fig_cu, use_container_width=True)

                # Daily sales trend
                _so_trend = so_df.dropna(subset=["Date"]).copy()
                if not _so_trend.empty:
                    daily_so = (_so_trend.groupby(_so_trend["Date"].dt.date, as_index=False)
                                .agg(Qty=("Qty","sum"), Revenue=("Subtotal","sum"))
                                .sort_values("Date"))
                    daily_so["Date"] = daily_so["Date"].astype(str)
                    with s4c2:
                        fig_tr = go.Figure()
                        fig_tr.add_trace(go.Scatter(
                            x=daily_so["Date"], y=daily_so["Qty"],
                            name=t("Qty","الكمية"),
                            mode="lines", line=dict(color=_accent1, width=2),
                            fill="tozeroy",
                            fillcolor=f"rgba({int(_accent1[1:3],16)},{int(_accent1[3:5],16)},{int(_accent1[5:7],16)},0.08)",
                            hovertemplate="%{x}<br>Qty: %{y:,.0f}<extra></extra>"))
                        fig_tr.add_trace(go.Scatter(
                            x=daily_so["Date"], y=daily_so["Revenue"],
                            name="SAR", yaxis="y2",
                            mode="lines", line=dict(color=_accent3, width=1.5, dash="dot"),
                            hovertemplate="%{x}<br>Revenue: %{y:,.0f} SAR<extra></extra>"))
                        fig_tr.update_layout(**_chart_layout,
                            title=t("Daily Sales Trend","الاتجاه اليومي للمبيعات"),
                            yaxis=dict(title=t("Qty","الكمية"),
                                       gridcolor="rgba(255,255,255,0.06)",
                                       color=_text_s, tickfont=dict(color=_text_s)),
                            yaxis2=dict(title="SAR", overlaying="y", side="right",
                                        gridcolor="rgba(0,0,0,0)", color=_text_s,
                                        tickfont=dict(color=_text_s)))
                        fig_tr.update_xaxes(tickangle=-35)
                        st.plotly_chart(fig_tr, use_container_width=True)

            except ImportError:
                st.info(t("Install plotly for charts: pip install plotly",
                          "ثبّت plotly للرسوم البيانية: pip install plotly"))

            # ── Paginated full Sales table ────────────────────────────────────
            st.divider()
            st.markdown(f"#### 📋 {t('Full Sales Detail','تفاصيل المبيعات الكاملة')}")

            PAGE_SIZE_SO = 50
            # filters
            sf1, sf2, sf3 = st.columns([2,1,1])
            with sf1:
                so_search = st.text_input(
                    f"🔍 {t('Search','بحث')}",
                    placeholder=t("Model / Customer / Branch / SO…","موديل / عميل / فرع…"),
                    key="so_tbl_search").strip().lower()
            with sf2:
                so_sort_col = st.selectbox(
                    f"↕️ {t('Sort by','ترتيب')}",
                    options=["Date","Model Code","Customer","Branch","Qty","Subtotal"],
                    key="so_sort_col")
            with sf3:
                so_sort_asc = st.radio(
                    t("Order","الترتيب"), ["↓ Desc","↑ Asc"],
                    horizontal=True, key="so_sort_asc") == "↑ Asc"

            _show_so = so_df.copy()
            _show_so["Date_str"] = _show_so["Date"].dt.strftime("%Y-%m-%d").fillna("—")
            if so_search:
                _so_mask = pd.Series([False]*len(_show_so), index=_show_so.index)
                for _sc in ["Model Code","Customer","Branch","SO","Category","Brand Category","Product"]:
                    if _sc in _show_so.columns:
                        _so_mask |= _show_so[_sc].fillna("").str.lower().str.contains(so_search, regex=False)
                _show_so = _show_so[_so_mask]

            _sort_col_actual = "Date" if so_sort_col == "Date" else so_sort_col
            if _sort_col_actual in _show_so.columns:
                _show_so = _show_so.sort_values(_sort_col_actual, ascending=so_sort_asc)

            total_so      = len(_show_so)
            total_pages_so= max(1, -(-total_so // PAGE_SIZE_SO))

            sp1, sp2, sp3 = st.columns([1,2,1])
            with sp2:
                so_page = st.number_input(
                    f"📄 {t('Page','الصفحة')} (1 – {total_pages_so})",
                    min_value=1, max_value=total_pages_so,
                    value=1, step=1, key="so_page_num")

            s_start = (so_page - 1) * PAGE_SIZE_SO
            s_end   = s_start + PAGE_SIZE_SO
            so_page_data = _show_so.iloc[s_start:s_end].copy()

            # format display
            disp_so = so_page_data.copy()
            disp_so["Date"]       = disp_so["Date_str"]
            disp_so = disp_so.drop(columns=["Date_str"], errors="ignore")
            if "Unit Price" in disp_so.columns:
                disp_so["Unit Price"] = disp_so["Unit Price"].map(lambda v: f"{float(v):.2f} SAR" if pd.notna(v) else "—")
            if "Subtotal" in disp_so.columns:
                disp_so["Subtotal"]   = disp_so["Subtotal"].map(lambda v: f"{float(v):,.2f} SAR" if pd.notna(v) else "—")
            if "Qty" in disp_so.columns:
                disp_so["Qty"]        = disp_so["Qty"].map(lambda v: f"{float(v):,.0f}" if pd.notna(v) else "—")

            cols_so  = disp_so.columns.tolist()
            th_so    = "".join(f"<th>{c}</th>" for c in cols_so)
            rows_so  = "".join(
                f"<tr>{''.join(f'<td class=\"cf\">{v}</td>' if ci==0 else f'<td>{v}</td>' for ci,v in enumerate(r))}</tr>"
                for r in disp_so.values)
            st.markdown(
                f'{_TABLE_CSS}<div class="swag-wrap">'
                f'<table class="swag-tbl"><thead><tr>{th_so}</tr></thead>'
                f'<tbody>{rows_so}</tbody></table></div>',
                unsafe_allow_html=True)

            st.caption(
                f"📊 {t('Showing','عرض')} {s_start+1}–{min(s_end,total_so)} "
                f"{t('of','من')} {total_so} {t('rows','صفوف')} "
                f"· {t('Page','الصفحة')} {so_page}/{total_pages_so}")

            sp_n1, sp_n2, sp_n3 = st.columns([1,2,1])
            with sp_n1:
                if so_page > 1 and st.button(f"◀ {t('Prev','السابق')}", key="so_prev"):
                    st.session_state["so_page_num"] = so_page - 1; st.rerun()
            with sp_n3:
                if so_page < total_pages_so and st.button(f"{t('Next','التالي')} ▶", key="so_next"):
                    st.session_state["so_page_num"] = so_page + 1; st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            _export_so = so_df.copy()
            _export_so["Date"] = _export_so["Date"].dt.strftime("%Y-%m-%d").fillna("")
            sdl1,sdl2,_ = st.columns([1,1,2])
            sdl1.download_button("⬇️ CSV (All)",
                _export_so.to_csv(index=False).encode("utf-8-sig"),
                dl_name("sales","csv"), "text/csv", use_container_width=True, key="so_csv_dl")
            sdl2.download_button("⬇️ Excel (All)",
                to_excel_sales(_export_so), dl_name("sales","xlsx"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True, key="so_excel_dl")

# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
restore_session()

if not st.session_state.authenticated:
    show_login()
else:
    show_dashboard()
