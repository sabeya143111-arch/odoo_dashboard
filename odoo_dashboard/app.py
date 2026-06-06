"""
SWAG Product & Season Comparison Dashboard
Merged Version — Season Comparison added, Purchase/Sales/Barcode removed
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
    page_title="SWAG Dashboard",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;1,300&family=Tajawal:wght@300;400;700&family=Outfit:wght@300;400;500;600&display=swap');

*,html,body,[class*="css"]{font-family:'Outfit','Tajawal',sans-serif;box-sizing:border-box;}

.stApp{background:#060d0e !important;}
.stApp > header{background:transparent !important;}
.block-container{padding-top:0 !important;padding-bottom:0 !important;max-width:100% !important;}
.main .block-container{padding:0 !important;}

/* SIDEBAR */
section[data-testid="stSidebar"]{
  background:#060d0e !important;
  border-right:1px solid rgba(74,172,180,0.1) !important;
}
section[data-testid="stSidebar"] *{color:rgba(255,255,255,0.6) !important;}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3{
  color:#4AACB4 !important;
  font-family:'Outfit',sans-serif !important;
  font-size:9px !important;
  font-weight:400 !important;
  letter-spacing:4px !important;
  text-transform:uppercase !important;
}
section[data-testid="stSidebar"] input{color:#060d0e !important;}

/* METRICS */
[data-testid="stMetric"]{
  background:rgba(74,172,180,0.03) !important;
  border:1px solid rgba(74,172,180,0.08) !important;
  border-radius:4px !important;
  padding:20px 24px !important;
  position:relative !important;
  overflow:hidden !important;
  transition:border-color 0.25s !important;
}
[data-testid="stMetric"]:hover{border-color:rgba(74,172,180,0.25) !important;}
[data-testid="stMetric"]::after{
  content:'';position:absolute;bottom:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,#4AACB4,transparent);
  transform:scaleX(0);transform-origin:left;transition:transform 0.3s;
}
[data-testid="stMetric"]:hover::after{transform:scaleX(1);}
[data-testid="stMetricLabel"]{
  font-family:'Outfit',sans-serif !important;
  font-size:8px !important;
  letter-spacing:3px !important;
  text-transform:uppercase !important;
  color:rgba(255,255,255,0.25) !important;
}
[data-testid="stMetricValue"]{
  font-family:'Cormorant Garamond',serif !important;
  font-size:44px !important;
  font-weight:300 !important;
  color:#fff !important;
  line-height:1.1 !important;
}

/* TABS */
.stTabs [data-baseweb="tab-list"]{
  background:transparent !important;
  border-bottom:1px solid rgba(74,172,180,0.08) !important;
  gap:0 !important;padding:0 !important;
}
.stTabs [data-baseweb="tab"]{
  font-family:'Outfit',sans-serif !important;
  font-size:9px !important;letter-spacing:2.5px !important;
  text-transform:uppercase !important;color:rgba(255,255,255,0.25) !important;
  padding:14px 22px !important;border-radius:0 !important;
  border-bottom:2px solid transparent !important;
  background:transparent !important;transition:all 0.2s !important;
}
.stTabs [aria-selected="true"]{
  color:#4AACB4 !important;
  border-bottom:2px solid #4AACB4 !important;
  background:transparent !important;
}

/* INPUTS */
.stTextInput input,
.stNumberInput input,
.stTextArea textarea{
  background:rgba(255,255,255,0.03) !important;
  border:1px solid rgba(74,172,180,0.15) !important;
  border-radius:4px !important;color:#fff !important;
  font-family:'Outfit',sans-serif !important;font-size:13px !important;
  caret-color:#4AACB4 !important;transition:all 0.2s !important;
}
.stTextInput input:focus,
.stTextArea textarea:focus{
  border-color:#4AACB4 !important;
  background:rgba(74,172,180,0.03) !important;
  box-shadow:none !important;
}
.stTextInput input::placeholder,
.stTextArea textarea::placeholder{color:rgba(255,255,255,0.15) !important;}
.stTextInput label,
.stNumberInput label,
.stTextArea label,
.stSelectbox label,
.stMultiSelect label{
  font-family:'Outfit',sans-serif !important;
  font-size:8px !important;letter-spacing:3px !important;
  text-transform:uppercase !important;color:rgba(74,172,180,0.7) !important;
  font-weight:400 !important;
}

/* SELECT */
[data-baseweb="select"] div,[data-baseweb="select"] span{
  background:rgba(6,13,14,0.95) !important;
  color:rgba(255,255,255,0.6) !important;
  border-color:rgba(74,172,180,0.12) !important;
  border-radius:4px !important;
  font-family:'Outfit',sans-serif !important;font-size:12px !important;
}
[data-baseweb="tag"]{
  background:rgba(74,172,180,0.1) !important;
  color:#7FCDD3 !important;border-radius:100px !important;
  border:1px solid rgba(74,172,180,0.2) !important;
}

/* BUTTONS */
.stButton button{
  font-family:'Outfit',sans-serif !important;
  font-size:9px !important;letter-spacing:2px !important;
  text-transform:uppercase !important;border-radius:100px !important;
  transition:all 0.2s !important;
}
.stButton button[kind="primary"],
.stFormSubmitButton button{
  background:#4AACB4 !important;color:#060d0e !important;
  border:none !important;font-weight:600 !important;
  padding:10px 28px !important;border-radius:100px !important;
}
.stButton button[kind="primary"]:hover,
.stFormSubmitButton button:hover{
  background:#2E8A91 !important;transform:translateY(-1px) !important;
}
.stButton button[kind="secondary"]{
  background:transparent !important;color:rgba(74,172,180,0.6) !important;
  border:1px solid rgba(74,172,180,0.2) !important;border-radius:100px !important;
}
.stButton button[kind="secondary"]:hover{
  border-color:#4AACB4 !important;color:#4AACB4 !important;
}

/* DOWNLOAD BUTTONS */
.stDownloadButton button{
  background:transparent !important;
  color:rgba(74,172,180,0.6) !important;
  border:1px solid rgba(74,172,180,0.15) !important;
  border-radius:100px !important;
  font-family:'Outfit',sans-serif !important;
  font-size:8px !important;letter-spacing:2px !important;
  text-transform:uppercase !important;
  padding:6px 16px !important;transition:all 0.2s !important;
}
.stDownloadButton button:hover{
  border-color:#4AACB4 !important;color:#4AACB4 !important;
  transform:translateY(-1px) !important;
}

/* TOGGLE / RADIO / CHECKBOX */
.stToggle label,
.stCheckbox label,
.stRadio label,
div[data-testid="stRadio"] p{
  color:rgba(255,255,255,0.5) !important;
  font-family:'Outfit',sans-serif !important;
  font-size:9px !important;letter-spacing:2px !important;
  text-transform:uppercase !important;
}
[data-testid="stToggle"] span[data-checked="true"]{background:#4AACB4 !important;}

/* EXPANDER */
[data-testid="stExpander"]{
  background:rgba(74,172,180,0.02) !important;
  border:1px solid rgba(74,172,180,0.1) !important;
  border-radius:4px !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p{
  color:rgba(74,172,180,0.7) !important;
  font-family:'Outfit',sans-serif !important;
  font-size:9px !important;letter-spacing:3px !important;
  text-transform:uppercase !important;
}

/* FILE UPLOADER */
[data-testid="stFileUploader"]{
  background:rgba(74,172,180,0.02) !important;
  border:1px dashed rgba(74,172,180,0.15) !important;
  border-radius:4px !important;
}
[data-testid="stFileUploader"] p,
[data-testid="stFileUploader"] span{
  color:rgba(255,255,255,0.25) !important;
  font-family:'Outfit',sans-serif !important;font-size:11px !important;
}

/* PROGRESS */
[data-testid="stProgressBar"]>div{
  background:linear-gradient(90deg,#4AACB4,#D4A84B) !important;
  border-radius:0 !important;
}
[data-testid="stProgressBar"]{
  background:rgba(74,172,180,0.08) !important;
  border-radius:0 !important;height:1px !important;
}

/* SLIDER */
[data-testid="stSlider"] label{
  color:rgba(74,172,180,0.7) !important;
  font-family:'Outfit',sans-serif !important;
  font-size:8px !important;letter-spacing:3px !important;
  text-transform:uppercase !important;
}

/* DIVIDER */
hr{
  border:none !important;height:1px !important;
  background:rgba(74,172,180,0.08) !important;
  margin:20px 0 !important;
}

/* CAPTION */
.stCaption,[data-testid="stCaptionContainer"] p{
  color:rgba(255,255,255,0.15) !important;
  font-family:'Outfit',sans-serif !important;
  font-size:8px !important;letter-spacing:2px !important;
}

/* TEXT */
h1,h2,h3,h4,h5,h6{color:#fff !important;font-family:'Tajawal',sans-serif !important;}
.stMarkdown p,.stMarkdown li{color:rgba(255,255,255,0.5) !important;}
p,div,span,label{color:rgba(255,255,255,0.5);}

/* NUMBER INPUT */
.stNumberInput button{
  color:#4AACB4 !important;
  background:rgba(74,172,180,0.06) !important;
  border-color:rgba(74,172,180,0.1) !important;
}

/* SCROLLBAR */
::-webkit-scrollbar{width:2px;height:2px;}
::-webkit-scrollbar-track{background:#060d0e;}
::-webkit-scrollbar-thumb{background:#4AACB4;border-radius:0;}

/* CUSTOM COMPONENTS */
.hero-section{
  padding:48px 0 36px;
  border-bottom:1px solid rgba(74,172,180,0.08);
  position:relative;overflow:hidden;
}
.hero-glow{
  position:absolute;left:-150px;top:-150px;
  width:500px;height:500px;border-radius:50%;
  background:rgba(74,172,180,0.05);
  filter:blur(100px);pointer-events:none;
  z-index:0;
}
.hero-gold-glow{
  position:absolute;right:50px;bottom:-100px;
  width:350px;height:350px;border-radius:50%;
  background:rgba(212,168,75,0.03);
  filter:blur(80px);pointer-events:none;z-index:0;
}
.hero-geo-bg{
  position:absolute;right:-60px;top:-60px;
  opacity:0.04;pointer-events:none;z-index:0;
}
.hero-inner{position:relative;z-index:1;}
.eyebrow{
  font-family:'Outfit',sans-serif;
  font-size:9px;letter-spacing:5px;text-transform:uppercase;
  color:#4AACB4;margin-bottom:14px;
  display:flex;align-items:center;gap:10px;
}
.eyebrow::before{content:'';width:24px;height:1px;background:#4AACB4;}
.hero-title{
  font-family:'Tajawal',sans-serif;
  font-size:48px;font-weight:700;color:#fff;
  line-height:1.05;letter-spacing:-1px;margin-bottom:6px;
}
.hero-title em{color:#4AACB4;font-style:normal;}
.hero-subtitle{
  font-family:'Cormorant Garamond',serif;
  font-size:20px;font-weight:300;font-style:italic;
  color:rgba(255,255,255,0.18);letter-spacing:5px;margin-bottom:0;
}
.section-tag{
  font-family:'Outfit',sans-serif;font-size:9px;
  letter-spacing:4px;text-transform:uppercase;color:#4AACB4;
  margin-bottom:12px;display:flex;align-items:center;gap:10px;
}
.section-tag::before{
  content:'';width:20px;height:1px;background:#4AACB4;
  display:inline-block;flex-shrink:0;
}
.snap-card{
  background:rgba(74,172,180,0.03);
  border:1px solid rgba(74,172,180,0.1);
  border-radius:4px;padding:20px 22px;
  font-family:'Outfit',sans-serif;font-size:11px;
  color:rgba(255,255,255,0.4);line-height:2.2;
}
.snap-card b{color:#4AACB4;font-weight:400;letter-spacing:1px;}
.sys-row{display:flex;align-items:center;gap:10px;margin-bottom:8px;}
.badge-ok{
  font-size:7px;letter-spacing:2px;text-transform:uppercase;
  color:#4AACB4;border:1px solid rgba(74,172,180,0.3);
  border-radius:100px;padding:2px 10px;
}
.badge-off{
  font-size:7px;letter-spacing:2px;text-transform:uppercase;
  color:#D4A84B;border:1px solid rgba(212,168,75,0.3);
  border-radius:100px;padding:2px 10px;
}
.badge-err{
  font-size:7px;letter-spacing:2px;text-transform:uppercase;
  color:rgba(255,100,100,0.8);border:1px solid rgba(255,100,100,0.2);
  border-radius:100px;padding:2px 10px;
}
.info-banner{
  background:rgba(74,172,180,0.04);
  border-left:2px solid #4AACB4;
  padding:10px 16px;margin:8px 0 14px;
  font-family:'Outfit',sans-serif;font-size:9px;
  letter-spacing:1.5px;text-transform:uppercase;color:rgba(74,172,180,0.7);
}
.warn-banner{
  background:rgba(212,168,75,0.04);
  border-left:2px solid #D4A84B;
  padding:10px 16px;margin:8px 0 14px;
  font-family:'Outfit',sans-serif;font-size:9px;
  letter-spacing:1.5px;text-transform:uppercase;color:rgba(212,168,75,0.7);
}
.alert-banner{
  display:flex;align-items:center;gap:12px;
  background:rgba(212,168,75,0.04);
  border:1px solid rgba(212,168,75,0.12);
  border-left:3px solid #D4A84B;
  padding:12px 16px;margin-bottom:18px;
}
.alert-dot{width:5px;height:5px;border-radius:50%;background:#D4A84B;flex-shrink:0;}
.alert-txt{
  font-family:'Outfit',sans-serif;font-size:9px;
  letter-spacing:2px;text-transform:uppercase;color:#D4A84B;
}
.ok-banner{
  background:rgba(74,172,180,0.04);
  border-left:2px solid #4AACB4;
  padding:10px 16px;margin:8px 0 14px;
  font-family:'Outfit',sans-serif;font-size:9px;
  letter-spacing:1.5px;text-transform:uppercase;color:rgba(74,172,180,0.7);
}
.login-card{
  background:rgba(74,172,180,0.03);
  border:1px solid rgba(74,172,180,0.1);
  border-radius:4px;padding:40px;
}
.login-title{
  font-family:'Cormorant Garamond',serif;
  font-size:52px;font-weight:300;
  color:#fff;text-align:center;
  letter-spacing:6px;margin-bottom:4px;
}
.login-sub{
  font-family:'Outfit',sans-serif;font-size:9px;
  letter-spacing:5px;text-transform:uppercase;
  color:#4AACB4;text-align:center;margin-bottom:36px;
}
.mono{
  font-family:'Outfit',monospace;font-size:10px;
  letter-spacing:0.5px;color:rgba(74,172,180,0.6);
}
footer{visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# TABLE CSS injected separately so it's reusable
_TABLE_CSS = """<style>
.swag-wrap{width:100%;overflow-x:auto;border:1px solid rgba(74,172,180,0.08);border-radius:4px;overflow:hidden;margin-bottom:4px;}
.swag-tbl{width:100%;border-collapse:collapse;font-family:'Outfit','Tajawal',sans-serif;}
.swag-tbl thead tr{background:rgba(74,172,180,0.05);border-bottom:1px solid rgba(74,172,180,0.1);}
.swag-tbl thead th{
  color:rgba(74,172,180,0.6);font-family:'Outfit',sans-serif;
  font-size:8px;letter-spacing:3px;text-transform:uppercase;font-weight:400;
  padding:13px 16px;text-align:center;white-space:nowrap;
}
.swag-tbl tbody tr{border-bottom:1px solid rgba(255,255,255,0.03);transition:background 0.15s;}
.swag-tbl tbody tr:last-child{border-bottom:none;}
.swag-tbl tbody tr:hover td{background:rgba(74,172,180,0.03);}
.swag-tbl tbody td{padding:12px 16px;text-align:center;font-size:12px;color:rgba(255,255,255,0.45);}
.swag-tbl tbody td.cf{
  font-family:'Outfit',monospace;font-size:11px;letter-spacing:0.5px;
  color:#fff;font-weight:500;border-right:1px solid rgba(74,172,180,0.08);
}
.swag-tbl tbody tr.rl{background:rgba(212,168,75,0.025);}
.swag-tbl tbody tr.rl td{color:#D4A84B;}
.swag-tbl tbody tr.na-row td{opacity:0.4;}
.swag-tbl tbody td.na-cell{color:rgba(255,255,255,0.2);font-style:italic;font-size:11px;}
</style>"""

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_KEYS = ["SWAG", "STOCK", "LAROUCHE", "DIFFC", "FASHIONLIMITS"]

# ─────────────────────────────────────────────────────────────────────────────
# LANGUAGE
# ─────────────────────────────────────────────────────────────────────────────
def get_lang():
    return st.session_state.get("lang", "EN")

def t(en, ar):
    return ar if get_lang() == "AR" else en

def get_system_name(key):
    cfg = get_system_config(key) or {}
    return cfg.get("name_ar", cfg.get("name", key)) if get_lang() == "AR" else cfg.get("name", key)

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
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
_DEF = {
    "authenticated": False, "user_email": "", "lang": "EN",
    "last_run": None, "total_df": None, "branch_df": None,
    "transfers_df": None, "reorder_df": None, "sys_stats": {},
    "search_exact": False, "low_stock_thresh": 5,
    "show_transfers": False, "show_reorder": False,
    "reorder_target_days": 30,
    "reorder_point": 10,
    "pdf_codes": None, "pdf_mode": "total",
    "so_analytics_df": None, "so_last_model": "", "so_last_system": "",
}
for k, v in _DEF.items():
    if k not in st.session_state:
        st.session_state[k] = v

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
        email = params.get("u", "")
        token = params.get("t", "")
        if email and token and _verify_token(email, token):
            st.session_state.authenticated = True
            st.session_state.user_email = email
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────────────────────
# XML-RPC
# ─────────────────────────────────────────────────────────────────────────────
# CONFIG HELPER — normalises key aliases + strips trailing /odoo from URL
# ─────────────────────────────────────────────────────────────────────────────
_KEY_ALIASES: dict = {
    # Both spellings map to the canonical key stored in secrets
    "FASHION_LIMITS" : "FASHIONLIMITS",
    "FASHIONLIMITS"  : "FASHIONLIMITS",
}

def _canonical_key(key: str) -> str:
    """Return the canonical secrets key for any alias."""
    return _KEY_ALIASES.get(key, key)

def get_system_config(key: str) -> dict | None:
    """
    Fetch config from st.secrets, trying canonical key then known aliases.
    Strips a trailing '/odoo' from the URL so XML-RPC proxy works correctly:
      proxy builds  url + /xmlrpc/2/common
      so url must be  https://host.swag.com.sa  (no /odoo suffix)
    Returns dict or None.
    """
    canonical = _canonical_key(key)
    # Try canonical first, then the raw key as fallback
    cfg = st.secrets.get(canonical) or st.secrets.get(key)
    if not cfg:
        return None
    cfg = dict(cfg)                         # make mutable copy
    url = str(cfg.get("url", "")).rstrip("/")
    if url.endswith("/odoo"):
        url = url[: -len("/odoo")]
    cfg["url"] = url
    return cfg

# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def _proxy(url, ep):
    return xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/{ep}", allow_none=True)

@st.cache_data(ttl=28800, show_spinner=False)
def _auth(url, db, user, api_key):
    """
    Returns structured dict:
      {"ok": True,  "uid": <int>}
      {"ok": False, "error": "<TAG>: <detail>"}
    Tags: NO_RESPONSE | BAD_CREDENTIALS | AUTH_EXCEPTION
    """
    try:
        uid = _proxy(url, "common").authenticate(db, user, api_key, {})
        if uid:
            return {"ok": True, "uid": uid}
        return {"ok": False, "error": "BAD_CREDENTIALS: uid=False — check user/api_key"}
    except ConnectionRefusedError as e:
        return {"ok": False, "error": f"NO_RESPONSE: {e}"}
    except Exception as e:
        return {"ok": False, "error": f"AUTH_EXCEPTION: {e}"}

def _auth_uid(url, db, user, api_key):
    """Backward-compat wrapper — returns uid int or None."""
    r = _auth(url, db, user, api_key)
    return r["uid"] if r["ok"] else None

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
    from openpyxl.formatting.rule import DataBarRule
    if lang == "AR":
        ws.sheet_view.rightToLeft = True
    hdr_fill  = PatternFill("solid", fgColor="060D0E")
    hdr_font  = Font(bold=True, color="4AACB4", size=11, name="Calibri")
    hdr_align = Alignment(horizontal="center", vertical="center")
    thin      = Side(border_style="thin", color="1A2A2C")
    border    = Border(left=thin, right=thin, top=thin, bottom=thin)
    alt_fill  = PatternFill("solid", fgColor="0D1A1C")
    zero_fill = PatternFill("solid", fgColor="1C1000")
    zero_font = Font(color="D4A84B", bold=True, name="Calibri")
    norm_font = Font(name="Calibri", size=10, color="8AACB0")
    num_align = Alignment(horizontal="right",  vertical="center")
    ctr_align = Alignment(horizontal="center", vertical="center")
    tot_fill  = PatternFill("solid", fgColor="060D0E")
    tot_font  = Font(bold=True, name="Calibri", color="4AACB4")
    max_row   = ws.max_row
    max_col   = ws.max_column
    ws.row_dimensions[1].height = 28
    for col_num in range(1, max_col + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = hdr_fill; cell.font = hdr_font
        cell.alignment = hdr_align; cell.border = border
    col_names = [ws.cell(row=1, column=c).value for c in range(1, max_col + 1)]
    on_hand_col = None
    for i, name in enumerate(col_names, 1):
        if name in ("On Hand", "متوفر"): on_hand_col = i
    for row in ws.iter_rows(min_row=2, max_row=max_row):
        is_zero = False
        if on_hand_col:
            val = ws.cell(row=row[0].row, column=on_hand_col).value
            is_zero = (val is None or
                       str(val).strip() in ['0','Not Available','غير متوفر','—','-','']
                       or val == 0)
        for cell in row:
            cell.border = border
            cell.font   = zero_font if is_zero else norm_font
            if is_zero:              cell.fill = zero_fill
            elif cell.row % 2 == 0: cell.fill = alt_fill
            cell.alignment = num_align if isinstance(cell.value, (int, float)) else ctr_align
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
            DataBarRule(start_type="min", end_type="max", color="4AACB4"))
    total_row = max_row + 1
    ws.cell(row=total_row, column=1, value="TOTAL")
    ws.cell(row=total_row, column=1).font      = tot_font
    ws.cell(row=total_row, column=1).fill      = tot_fill
    ws.cell(row=total_row, column=1).alignment = ctr_align
    if on_hand_col:
        col = get_column_letter(on_hand_col)
        ws.cell(row=total_row, column=on_hand_col,
                value=f"=SUM({col}2:{col}{max_row})")
        ws.cell(row=total_row, column=on_hand_col).font      = tot_font
        ws.cell(row=total_row, column=on_hand_col).fill      = tot_fill
        ws.cell(row=total_row, column=on_hand_col).alignment = ctr_align
    ws.row_dimensions[total_row].height = 20
    ws.sheet_properties.tabColor = "4AACB4"
    footer_row = total_row + 2
    ws.cell(row=footer_row, column=1,
            value=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  SWAG Dashboard")
    ws.cell(row=footer_row, column=1).font = Font(italic=True, color="4AACB4", size=9, name="Calibri")
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToPage   = True
    ws.page_setup.fitToWidth  = 1
    ws.print_title_rows       = "1:1"
    ws.sheet_view.zoomScale   = 85

def to_csv(df):
    return df.drop(columns=["_status"], errors="ignore").to_csv(index=False).encode("utf-8-sig")

def to_excel(df):
    lang  = st.session_state.get('lang', 'EN')
    buf   = io.BytesIO()
    clean = df.drop(columns=['_status'], errors='ignore').copy()
    oh    = 'On Hand' if 'On Hand' in clean.columns else ('متوفر' if 'متوفر' in clean.columns else None)
    if oh:
        na = 'غير متوفر' if lang == 'AR' else 'Not Available'
        clean[oh] = clean[oh].apply(
            lambda x: na if (pd.isna(x) or str(x).strip() in ['0','']) or x == 0 else x)
    desired = [t("Model Code","رمز الموديل"), t("System","النظام"),
               t("Branch","الفرع"), t("Location","الموقع"),
               t("Sale Price","سعر البيع"), t("On Hand","متوفر")]
    ordered  = [c for c in desired if c in clean.columns]
    remaining = [c for c in clean.columns if c not in ordered]
    clean    = clean[ordered + remaining]
    with pd.ExcelWriter(buf, engine='openpyxl') as w:
        clean.to_excel(w, index=False, sheet_name='Data')
        _style_worksheet(w.sheets['Data'], clean, lang=lang)
    return buf.getvalue()

def to_excel_bulk(df):
    lang    = st.session_state.get("lang", "EN")
    buf     = io.BytesIO()
    sys_col = t("System", "النظام")
    desired = [t("Model Code","رمز الموديل"), t("System","النظام"),
               t("Branch","الفرع"), t("Location","الموقع"),
               t("Sale Price","سعر البيع"), t("On Hand","متوفر")]
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        def _ws(data, name):
            c  = data.drop(columns=["_status"], errors="ignore").copy()
            oh = t("On Hand", "متوفر")
            if oh in c.columns:
                na = 'غير متوفر' if lang == 'AR' else 'Not Available'
                c[oh] = c[oh].apply(
                    lambda x: na if (pd.isna(x) or str(x).strip() in ['0','']) or x == 0 else x)
            ordered   = [col for col in desired if col in c.columns]
            remaining = [col for col in c.columns if col not in ordered]
            c = c[ordered + remaining]
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
# PURCHASE SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def get_purchase_summary_by_model(model_codes_tuple, date_from, date_to, system_key="SWAG"):
    empty = pd.DataFrame(columns=["Model Code", "Purchase Qty"])
    cfg = get_system_config(system_key)
    if not cfg: return empty
    ar = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not ar["ok"]: return empty
    uid = ar["uid"]; u = cfg["url"]; db = cfg["db"]; ak = cfg["api_key"]
    try:
        dom = [
            ["order_id.state", "in", ["purchase", "done"]],
            ["order_id.date_order", ">=", f"{date_from} 00:00:00"],
            ["order_id.date_order", "<=", f"{date_to} 23:59:59"],
        ]
        if model_codes_tuple:
            dom.append(["product_id.default_code", "in", list(model_codes_tuple)])
        lines = _x(u, db, uid, ak, "purchase.order.line", "search_read", [dom],
                   {"fields": ["product_id", "product_qty"], "limit": 10000, "order": "id desc"})
        if not lines: return empty
        pids = list({l["product_id"][0] for l in lines if isinstance(l.get("product_id"), list)})
        prods = _x(u, db, uid, ak, "product.product", "search_read",
                   [[["id", "in", pids]]],
                   {"fields": ["id", "default_code"], "limit": len(pids) + 10})
        pmap = {p["id"]: p for p in prods}
        agg = {}
        for line in lines:
            pid  = line["product_id"][0] if isinstance(line.get("product_id"), list) else None
            mc   = pmap.get(pid, {}).get("default_code", "").strip()
            if not mc: continue
            agg[mc] = agg.get(mc, 0) + float(line.get("product_qty") or 0)
        if not agg: return empty
        df = pd.DataFrame([{"Model Code": mc, "Purchase Qty": qty} for mc, qty in agg.items()])
        return df.groupby("Model Code", as_index=False)["Purchase Qty"].sum()
    except Exception:
        return empty

# ─────────────────────────────────────────────────────────────────────────────
# DEAD STOCK FINDER — SWAG only (FAST VERSION)
# Strategy:
#   - Use product.product qty_available directly (no quant scan)
#   - Get last sale via a SINGLE search_read with date filter + group_by trick
#   - Chunk size 1000 to minimize API round trips
#   - Cache 10 min so repeat runs are instant
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def fetch_dead_stock(threshold_days=60, system_key="SWAG",
                     _progress=None, _status_text=None):
    """
    _progress     : st.progress() object — updated 0.0→1.0
    _status_text  : st.empty()     object — live step messages
    Returns (df, is_partial) tuple.
      is_partial=True  means timeout/error interrupted midway — partial results returned
      is_partial=False means full run completed
    """
    empty_cols = [
        "Model Code","Product","Category","On Hand",
        "Unit Price","Frozen Value (SAR)",
        "Last Sale Date","Days Since Sale","Status"
    ]
    empty = pd.DataFrame(columns=empty_cols)

    def _prog(pct, msg=""):
        if _progress:
            _progress.progress(min(pct, 1.0))
        if _status_text and msg:
            _status_text.markdown(
                f"<div class='info-banner' style='margin:4px 0;'>{msg}</div>",
                unsafe_allow_html=True)

    cfg = get_system_config(system_key)
    if not cfg:
        _prog(1.0, "No config found for system.")
        return empty, False
    ar = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not ar["ok"]:
        _prog(1.0, f"Auth failed: {ar['error']}")
        return empty, False
    uid = ar["uid"]; u, db, ak = cfg["url"], cfg["db"], cfg["api_key"]

    today  = datetime.now().date()
    cutoff = (today - timedelta(days=threshold_days)).strftime("%Y-%m-%d")
    rows         = []
    is_partial   = False
    last_sale_map= {}

    try:
        # ── Step 1: In-stock products ────────────────────────────────────
        _prog(0.05, t(
            "Step 1/4 — Loading in-stock products...",
            "الخطوة 1/4 — تحميل المنتجات المتوفرة..."))

        all_prods = _x(u, db, uid, ak, "product.product", "search_read",
                       [[["qty_available",">",0],["sale_ok","=",True]]],
                       {"fields":["id","default_code","display_name",
                                  "categ_id","list_price","qty_available"],
                        "limit":10000,"order":"default_code asc"})

        if not all_prods:
            _prog(1.0, t("No in-stock products found.","لا توجد منتجات في المخزون."))
            return empty, False

        all_pids = [p["id"] for p in all_prods]
        prod_map = {p["id"]: p for p in all_prods}
        _prog(0.15, t(
            f"Step 1/4 — Found {len(all_pids):,} in-stock products.",
            f"الخطوة 1/4 — تم العثور على {len(all_pids):,} منتج في المخزون."))

        # ── Step 2: Recently sold pids (single fast call) ────────────────
        _prog(0.20, t(
            f"Step 2/4 — Checking recent sales (last {threshold_days} days)...",
            f"الخطوة 2/4 — فحص المبيعات الأخيرة (آخر {threshold_days} يوم)..."))

        recent_sol = _x(u, db, uid, ak, "sale.order.line", "search_read",
                        [[["product_id","in",all_pids],
                          ["order_id.state","in",["sale","done"]],
                          ["order_id.date_order",">=",f"{cutoff} 00:00:00"]]],
                        {"fields":["product_id"],"limit":50000})

        recently_sold = set()
        for ln in (recent_sol or []):
            pid = ln["product_id"][0] if isinstance(ln.get("product_id"),list) else None
            if pid: recently_sold.add(pid)

        dead_pids = [p for p in all_pids if p not in recently_sold]
        _prog(0.35, t(
            f"Step 2/4 — {len(dead_pids):,} items have no recent sale (dead candidates).",
            f"الخطوة 2/4 — {len(dead_pids):,} صنف بلا مبيعات حديثة (مرشحون للركود)."))

        if not dead_pids:
            _prog(1.0, t(
                "All products sold recently — no dead stock!",
                "جميع المنتجات بيعت مؤخراً — لا مخزون راكد!"))
            return empty, False

        # ── Step 3: Last sale date per dead candidate ────────────────────
        # Smaller chunk = more progress updates + less timeout risk
        CHUNK      = 200
        n_chunks   = max(1, (len(dead_pids) + CHUNK - 1) // CHUNK)
        prog_start = 0.35
        prog_end   = 0.85

        _prog(prog_start, t(
            f"Step 3/4 — Fetching sale history for {len(dead_pids):,} items "
            f"({n_chunks} batches)...",
            f"الخطوة 3/4 — جلب تاريخ المبيعات لـ {len(dead_pids):,} صنف "
            f"({n_chunks} دفعة)..."))

        for batch_idx, i in enumerate(range(0, len(dead_pids), CHUNK)):
            chunk = dead_pids[i:i+CHUNK]
            batch_num = batch_idx + 1

            # live progress per batch
            pct = prog_start + (prog_end - prog_start) * (batch_idx / n_chunks)
            _prog(pct, t(
                f"Step 3/4 — Batch {batch_num}/{n_chunks} "
                f"({min(i+CHUNK, len(dead_pids)):,}/{len(dead_pids):,} items)...",
                f"الخطوة 3/4 — الدفعة {batch_num}/{n_chunks} "
                f"({min(i+CHUNK, len(dead_pids)):,}/{len(dead_pids):,} صنف)..."))

            try:
                sol_chunk = _x(u, db, uid, ak, "sale.order.line", "search_read",
                               [[["product_id","in",chunk],
                                 ["order_id.state","in",["sale","done"]]]],
                               {"fields":["product_id","order_id"],
                                "limit":50000,"order":"id desc"})
            except Exception as chunk_err:
                # One batch failed — mark partial and continue with what we have
                is_partial = True
                _prog(pct, t(
                    f"⚠️ Batch {batch_num} failed ({chunk_err}) — continuing with partial results.",
                    f"⚠️ فشلت الدفعة {batch_num} — متابعة بنتائج جزئية."))
                continue

            if not sol_chunk: continue

            oids = list({ln["order_id"][0] for ln in sol_chunk
                         if isinstance(ln.get("order_id"),list)})
            if not oids: continue

            try:
                orders_ch = _x(u, db, uid, ak, "sale.order", "search_read",
                               [[["id","in",oids]]],
                               {"fields":["id","date_order"],
                                "limit":len(oids)+5})
            except Exception:
                is_partial = True
                continue

            odate = {}
            for o in orders_ch:
                raw = o.get("date_order","")
                if raw:
                    try:
                        odate[o["id"]] = datetime.strptime(
                            raw, "%Y-%m-%d %H:%M:%S").date()
                    except Exception:
                        pass

            for ln in sol_chunk:
                pid = ln["product_id"][0] if isinstance(ln.get("product_id"),list) else None
                oid = ln["order_id"][0]    if isinstance(ln.get("order_id"),list) else None
                if pid is None or oid is None: continue
                d = odate.get(oid)
                if d is None: continue
                if pid not in last_sale_map or d > last_sale_map[pid]:
                    last_sale_map[pid] = d

        # ── Step 4: Build rows ───────────────────────────────────────────
        _prog(0.90, t(
            "Step 4/4 — Building results...",
            "الخطوة 4/4 — بناء النتائج..."))

        for pid in dead_pids:
            prod      = prod_map.get(pid, {})
            code      = str(prod.get("default_code") or "").strip()
            name      = prod.get("display_name") or ""
            cat       = prod.get("categ_id")
            categ     = cat[1] if isinstance(cat,list) and len(cat)>1 else ""
            price     = float(prod.get("list_price") or 0)
            qty       = float(prod.get("qty_available") or 0)
            if qty <= 0: continue
            frozen_val = round(qty * price, 2)

            last_sale = last_sale_map.get(pid)
            if last_sale is None:
                days_since = 99999
                status     = "Never Sold"
            else:
                days_since = (today - last_sale).days
                status     = "Dead Stock"

            rows.append({
                "Model Code"        : code if code else "—",
                "Product"           : name,
                "Category"          : categ,
                "On Hand"           : int(qty),
                "Unit Price"        : price,
                "Frozen Value (SAR)": frozen_val,
                "Last Sale Date"    : last_sale.strftime("%Y-%m-%d") if last_sale else "Never",
                "Days Since Sale"   : days_since,
                "Status"            : status,
            })

        if not rows:
            _prog(1.0, t("No dead stock found.","لا يوجد مخزون راكد."))
            return empty, False

        df = pd.DataFrame(rows)
        df = df.sort_values("Frozen Value (SAR)", ascending=False).reset_index(drop=True)
        _prog(1.0, t(
            f"Done — {len(df):,} dead stock items found.",
            f"اكتمل — تم العثور على {len(df):,} صنف راكد."))
        return df, is_partial

    except Exception as e:
        # Top-level failure — return whatever rows we built so far
        is_partial = True
        _prog(1.0, f"⚠️ Error: {e}")
        if rows:
            df = pd.DataFrame(rows)
            df = df.sort_values("Frozen Value (SAR)", ascending=False).reset_index(drop=True)
            return df, is_partial
        return empty, is_partial

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN MAPS
# ─────────────────────────────────────────────────────────────────────────────
_COL_EN = {
    "System":"System","Model Code":"Model Code","Product":"Product",
    "Sale Price":"Sale Price","On Hand":"On Hand","Branch":"Branch",
    "Location":"Location","Reference":"Reference","Type":"Type",
    "State":"State","From":"From","To":"To","Qty":"Qty",
    "Scheduled":"Scheduled","Sold(30d)":"Sold(30d)","Daily Vel":"Daily Vel",
    "Days Left":"Days Left","Suggest":"Suggest","Priority":"Priority",
    "Purchase Qty":"Purchase Qty",
}
_COL_AR = {
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
    return df.rename(columns=_COL_AR if get_lang() == "AR" else _COL_EN)

def prepare_df(df):
    return translate_system_names(localize_columns(df))

# ─────────────────────────────────────────────────────────────────────────────
# FETCH ALL DATA
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=180, show_spinner=False)
def fetch_all_data(codes_tuple, exact=False, need_branch=False,
                   need_transfers=False, need_reorder=False,
                   target_days=30, reorder_point=10):
    DAYS  = 30
    dfrom = (datetime.now() - timedelta(days=DAYS)).strftime("%Y-%m-%d 00:00:00")
    codes = list(codes_tuple)
    dom   = _domain(codes, exact)

    CS="System";CM="Model Code";CPR="Product";CP="Sale Price"
    CQ="On Hand";CB="Branch";CR="Reference";CT="Type"
    CST="State";CF="From";CTO="To";CQT="Qty"
    CD="Scheduled";CSOLD="Sold(30d)";CVEL="Daily Vel"
    CDAY="Days Left";CSUGG="Suggest";CPRI="Priority"
    SM={"draft":"Draft","waiting":"Waiting","confirmed":"Confirmed","assigned":"Ready"}

    def _one(key):
        cfg = get_system_config(key)
        # Store RAW KEY in System column so ns-matching works correctly.
        # prepare_df() will translate it to display name afterwards.
        sn  = key
        R   = {"key":key,"total":[],"branch":[],"transfers":[],"reorder":[]}
        if not cfg:
            R["total"].append({CS:sn,CM:"—",
                CPR:f"No config — add [{_canonical_key(key)}] to secrets.toml",
                CP:0.0,CQ:0,"_status":"ERROR"})
            return R
        auth_r = _auth(cfg["url"],cfg["db"],cfg["user"],cfg["api_key"])
        if not auth_r["ok"]:
            err_short = auth_r["error"].split(":")[0]   # e.g. BAD_CREDENTIALS
            R["total"].append({CS:sn,CM:"—",
                CPR:f"{err_short} — {auth_r['error']}",
                CP:0.0,CQ:0,"_status":"ERROR"})
            return R
        uid=auth_r["uid"];u=cfg["url"];db=cfg["db"];ak=cfg["api_key"]
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
                    CS:sn,CM:p.get("default_code") or "—",
                    CPR:p.get("display_name") or "",
                    CP:float(p.get("list_price") or 0),
                    CQ:int(p.get("qty_available") or 0),
                    "_status":"OK"})
            if need_branch:
                locs = _x(u,db,uid,ak,"stock.location","search_read",
                          [[["usage","=","internal"],["active","=",True]]],
                          {"fields":["id"],"limit":10000})
                loc_ids = {l["id"] for l in locs}
                qs = _x(u,db,uid,ak,"stock.quant","search_read",
                        [[["product_id","in",pids],
                          ["location_id","in",list(loc_ids)],
                          ["quantity",">",0]]],
                        {"fields":["product_id","location_id","quantity"],"limit":5000})
                for q in qs:
                    pid = q["product_id"][0] if isinstance(q.get("product_id"),list) else None
                    loc = q.get("location_id") or [None,"—"]
                    ln  = loc[1] if isinstance(loc,list) else str(loc)
                    pm  = pmap.get(pid,{})
                    R["branch"].append({
                        CS:sn,CB:ln,CM:pm.get("default_code") or "—",
                        CP:float(pm.get("list_price") or 0),
                        CQ:int(q.get("quantity") or 0),"_status":"OK"})
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
                                CS:sn,CR:pk.get("name") or "—",
                                CT:_n("picking_type_id"),
                                CST:SM.get(pk.get("state",""),pk.get("state","")),
                                CF:_n("location_id"),CTO:_n("location_dest_id"),
                                CM:pm2.get("default_code") or "—",
                                CQT:int(mv.get("product_uom_qty") or 0),
                                CD:sd,"_status":"OK"})
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
                    sg   = max(0,round(target_days*vel-cq))
                    pr2  = ("Critical" if cq<=0 else "Low" if cq<=reorder_point else "OK")
                    R["reorder"].append({
                        CS:sn,CM:p.get("default_code") or "—",
                        CPR:p.get("display_name") or "",
                        CQ:cq,CSOLD:int(sold),CVEL:vel,
                        CDAY:dl,CSUGG:sg,CPRI:pr2,"_status":"OK"})
        except Exception as e:
            R["total"].append({CS:sn,CM:"—",CPR:f"Error: {e}",CP:0.0,CQ:0,"_status":"ERROR"})
        return R

    at=[];ab=[];atr=[];ar=[]
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(_one,k):k for k in SYSTEM_KEYS}
        for f in as_completed(futs):
            r = f.result()
            at.extend(r["total"]);ab.extend(r["branch"])
            atr.extend(r["transfers"]);ar.extend(r["reorder"])

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
def _excel_generic(df, sheet_name, hdr_color="060D0E", hdr_txt="4AACB4"):
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    buf = io.BytesIO()
    clean = df.copy()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        clean.to_excel(w, index=False, sheet_name=sheet_name)
        ws  = w.sheets[sheet_name]
        hfill = PatternFill("solid", fgColor=hdr_color)
        hfont = Font(bold=True, color=hdr_txt, size=11, name="Calibri")
        halign = Alignment(horizontal="center", vertical="center")
        thin   = Side(border_style="thin", color="1A2A2C")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        afill  = PatternFill("solid", fgColor="0D1A1C")
        nfont  = Font(name="Calibri", size=10, color="8AACB0")
        num_a  = Alignment(horizontal="right",  vertical="center")
        ctr_a  = Alignment(horizontal="center", vertical="center")
        tfill  = PatternFill("solid", fgColor="060D0E")
        tfont  = Font(bold=True, name="Calibri", color="D4A84B")
        mr, mc = ws.max_row, ws.max_column
        ws.row_dimensions[1].height = 28
        for c in range(1, mc+1):
            cell = ws.cell(row=1, column=c)
            cell.fill=hfill; cell.font=hfont; cell.alignment=halign; cell.border=border
        for row in ws.iter_rows(min_row=2, max_row=mr):
            for cell in row:
                cell.border=border; cell.font=nfont
                if cell.row%2==0: cell.fill=afill
                cell.alignment = num_a if isinstance(cell.value,(int,float)) else ctr_a
            ws.row_dimensions[row[0].row].height=18
        for c in range(1, mc+1):
            cl = get_column_letter(c)
            ml = max((len(str(ws.cell(row=r,column=c).value or "")) for r in range(1,mr+1)), default=8)
            ws.column_dimensions[cl].width = min(max(ml+3,12),50)
        ws.freeze_panes=f"A2"; ws.auto_filter.ref=f"A1:{get_column_letter(mc)}{mr}"
        tr = mr+1
        ws.cell(row=tr,column=1,value="TOTAL").font=tfont
        ws.cell(row=tr,column=1).fill=tfill
        ws.cell(row=tr,column=1).alignment=ctr_a
        cnames = [ws.cell(row=1,column=c).value for c in range(1,mc+1)]
        for cn in ("Qty","Subtotal"):
            if cn in cnames:
                ci=cnames.index(cn)+1; cl=get_column_letter(ci)
                ws.cell(row=tr,column=ci,value=f"=SUM({cl}2:{cl}{mr})")
                ws.cell(row=tr,column=ci).font=tfont
                ws.cell(row=tr,column=ci).fill=tfill
                ws.cell(row=tr,column=ci).alignment=ctr_a
        ws.sheet_properties.tabColor="4AACB4"
    return buf.getvalue()

def to_excel_purchase(df): return _excel_generic(df, "SWAG Purchase")
def to_excel_sales(df):
    d = df.copy()
    if "Date" in d.columns: d["Date"] = d["Date"].astype(str).str[:10]
    return _excel_generic(d, "SWAG Sales")

# ─────────────────────────────────────────────────────────────────────────────
# BRANCH MATRIX EXCEL
# ─────────────────────────────────────────────────────────────────────────────
def to_excel_branch_matrix(df_branch_filtered, lang="EN"):
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    if df_branch_filtered is None or df_branch_filtered.empty: return b""
    cm = t("Model Code","رمز الموديل"); cb = t("Branch","الفرع")
    cl = t("Location","الموقع");        cp = t("Sale Price","سعر البيع")
    cq = t("On Hand","متوفر");          cpr = t("Product","المنتج")
    lp = t("Purchase Qty","كمية المشتريات")
    df = df_branch_filtered.copy()
    pc = cl if cl in df.columns else (cb if cb in df.columns else None)
    if not pc or cm not in df.columns:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="BranchMatrix")
        return buf.getvalue()
    if cq in df.columns: df[cq] = pd.to_numeric(df[cq], errors="coerce").fillna(0)
    else: df[cq] = 0
    pivot = (df.pivot_table(index=cm, columns=pc, values=cq, aggfunc="sum", fill_value=0)
             .reset_index())
    pivot.columns.name = None
    if cp in df.columns:
        pm = df.groupby(cm)[cp].first().reset_index()
        pivot = pivot.merge(pm, on=cm, how="left")
        pivot[cp] = pd.to_numeric(pivot[cp], errors="coerce").fillna(0).round(2)
    else: pivot[cp] = 0.0
    tdf = st.session_state.get("total_df")
    pmap = {}
    if tdf is not None and not tdf.empty and cm in tdf.columns and cpr in tdf.columns:
        pmap = tdf.groupby(cm)[cpr].first().dropna().to_dict()
    pivot[cpr] = pivot[cm].map(pmap).fillna("")
    purmap = {}
    if tdf is not None and not tdf.empty:
        for k in ["Purchase Qty","كمية المشتريات",lp]:
            if k in tdf.columns and cm in tdf.columns:
                tmp = tdf.groupby(cm)[k].sum().to_dict()
                if tmp: purmap = tmp; break
    if not purmap:
        um = pivot[cm].dropna().unique().tolist()
        if um:
            try:
                ed = datetime.now().date(); sd = ed - timedelta(days=365)
                pdf = get_purchase_summary_by_model(tuple(um),
                      sd.strftime("%Y-%m-%d"), ed.strftime("%Y-%m-%d"))
                if not pdf.empty: purmap = dict(zip(pdf["Model Code"], pdf["Purchase Qty"]))
            except Exception: pass
    pivot[lp] = pivot[cm].map(purmap).fillna(0).astype(int)
    fixed = [cm,cpr,cp,lp]
    locs  = sorted(c for c in pivot.columns if c not in fixed)
    pivot = pivot[[c for c in fixed if c in pivot.columns] + locs]
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pivot.to_excel(writer, index=False, sheet_name="BranchMatrix")
        ws = writer.sheets["BranchMatrix"]
        if lang == "AR": ws.sheet_view.rightToLeft = True
        hfill = PatternFill("solid", fgColor="060D0E")
        hfont = Font(bold=True, color="4AACB4", size=11, name="Calibri")
        halign = Alignment(horizontal="center", vertical="center")
        thin   = Side(border_style="thin", color="1A2A2C")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        afill  = PatternFill("solid", fgColor="0D1A1C")
        nfont  = Font(name="Calibri", size=10, color="8AACB0")
        num_a  = Alignment(horizontal="right",  vertical="center")
        ctr_a  = Alignment(horizontal="center", vertical="center")
        tfill  = PatternFill("solid", fgColor="060D0E")
        tfont  = Font(bold=True, color="D4A84B", name="Calibri")
        zfill  = PatternFill("solid", fgColor="1C1000")
        zfont  = Font(color="D4A84B", bold=True, name="Calibri")
        mr, mc = ws.max_row, ws.max_column
        cnames = [ws.cell(row=1, column=c).value for c in range(1, mc+1)]
        ws.row_dimensions[1].height = 28
        for c in range(1, mc+1):
            cell = ws.cell(row=1, column=c)
            cell.fill=hfill; cell.font=hfont; cell.alignment=halign; cell.border=border
        for ri in range(2, mr+1):
            for ci in range(1, mc+1):
                cell = ws.cell(row=ri, column=ci)
                cn   = cnames[ci-1]
                is_loc = cn not in (cm,cpr,cp,lp,None)
                cell.border=border; cell.font=nfont
                if ri%2==0: cell.fill=afill
                if is_loc and isinstance(cell.value,(int,float)) and cell.value==0:
                    cell.fill=zfill; cell.font=zfont
                cell.alignment = num_a if isinstance(cell.value,(int,float)) else ctr_a
            ws.row_dimensions[ri].height=18
        for c in range(1, mc+1):
            cl2 = get_column_letter(c)
            ml  = max((len(str(ws.cell(row=r,column=c).value or "")) for r in range(1,mr+1)), default=8)
            ws.column_dimensions[cl2].width = min(max(ml+3,12),50)
        ws.freeze_panes=f"A2"; ws.auto_filter.ref=f"A1:{get_column_letter(mc)}{mr}"
        tr = mr+1
        tc = ws.cell(row=tr,column=1,value=t("TOTAL","الإجمالي"))
        tc.font=tfont; tc.fill=tfill; tc.alignment=ctr_a
        ws.row_dimensions[tr].height=22
        for ci,cn in enumerate(cnames,start=1):
            if cn in (None,cm,cpr,cp): continue
            cl2 = get_column_letter(ci)
            tot = ws.cell(row=tr,column=ci)
            tot.value=f"=SUM({cl2}2:{cl2}{mr})"
            tot.font=tfont; tot.fill=tfill; tot.alignment=num_a
        ws.sheet_properties.tabColor="4AACB4"
        ws.page_setup.orientation="landscape"; ws.page_setup.fitToPage=True
        ws.page_setup.fitToWidth=1; ws.print_title_rows="1:1"
        ws.sheet_view.zoomScale=85
    return buf.getvalue()

def dl_name(tag, ext):
    return f"swag_{tag}_{datetime.now().strftime('%Y%m%d_%H%M')}.{ext}"

# ─────────────────────────────────────────────────────────────────────────────
# QTY DISPLAY
# ─────────────────────────────────────────────────────────────────────────────
def get_qty_display(qty, lang="EN"):
    try:
        v = float(qty)
        if pd.isna(v) or v == 0:
            return "Not Available" if lang == "EN" else "غير متوفر"
        return int(v)
    except Exception:
        return "Not Available" if lang == "EN" else "غير متوفر"

# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY DF
# ─────────────────────────────────────────────────────────────────────────────
def display_df(df, thresh=0, table_key="tbl"):
    if df is None or df.empty:
        st.info(t("No data.", "لا بيانات."))
        return pd.DataFrame()
    work    = df.copy()
    sys_col = t("System","النظام"); mc_col = t("Model Code","رمز الموديل")
    pr_col  = t("Product","المنتج"); br_col = t("Branch","الفرع")
    loc_col = t("Location","الموقع"); qc = t("On Hand","متوفر")
    pc      = t("Sale Price","سعر البيع")
    has_sys = sys_col in work.columns; has_br = br_col in work.columns
    fc = st.columns([2,2,2,1.5])
    if has_sys:
        all_sys = sorted(work[sys_col].dropna().unique().tolist())
        with fc[0]:
            sel_sys = st.multiselect(t("Company","الشركة"), options=all_sys,
                                     default=all_sys, key=f"{table_key}_sys")
        if sel_sys: work = work[work[sys_col].isin(sel_sys)]
    if has_br:
        all_br = sorted(work[br_col].dropna().unique().tolist())
        with fc[1]:
            sel_br = st.multiselect(t("Branch","الفرع"), options=all_br,
                                    default=all_br, key=f"{table_key}_br")
        if sel_br: work = work[work[br_col].isin(sel_br)]
    with fc[2]:
        q = st.text_input(t("Search model / product","بحث موديل / منتج"),
                          value="", placeholder=t("e.g. XP6013","مثال: XP6013"),
                          key=f"{table_key}_q").strip()
    if q:
        ql   = q.lower()
        mask = pd.Series([False]*len(work), index=work.index)
        for col in [mc_col,pr_col,loc_col]:
            if col in work.columns:
                mask = mask | work[col].fillna("").str.lower().str.contains(ql, regex=False)
        work = work[mask]
    with fc[3]:
        sortable = [c for c in work.columns if c != "_status"]
        sort_by  = st.selectbox(t("Sort by","ترتيب"), options=["—"]+sortable,
                                index=0, key=f"{table_key}_sort")
    if sort_by and sort_by != "—" and sort_by in work.columns:
        try:
            work = work.sort_values(
                by=sort_by,
                key=lambda s: pd.to_numeric(s,errors="coerce").fillna(0)
                              if pd.api.types.is_numeric_dtype(pd.to_numeric(s,errors="coerce"))
                              else s, ascending=True)
        except Exception:
            work = work.sort_values(by=sort_by)
    if work.empty:
        st.warning(t("No rows match your filters.","لا توجد نتائج بعد الفلتر."))
        return pd.DataFrame()
    if qc in work.columns:
        raw_q = pd.to_numeric(work[qc],errors="coerce")
        mn,mx = int(raw_q.min() or 0), int(raw_q.max() or 0)
        if mx > mn:
            qr    = st.slider(t("Qty range","نطاق الكمية"),
                              min_value=mn,max_value=mx,value=(mn,mx),
                              key=f"{table_key}_qrange")
            raw_q2 = pd.to_numeric(work[qc],errors="coerce")
            work   = work[(raw_q2>=qr[0])&(raw_q2<=qr[1])]
    ok_work = work[work["_status"]=="OK"] if "_status" in work.columns else work
    sm1,sm2,sm3,sm4 = st.columns(4)
    sm1.metric(t("Rows","الصفوف"), len(work))
    if qc in ok_work.columns:
        sm2.metric(t("Total Qty","إجمالي الكمية"),
                   int(pd.to_numeric(ok_work[qc],errors="coerce").fillna(0).sum()))
    if pc in ok_work.columns:
        vp = pd.to_numeric(ok_work[pc],errors="coerce")
        sm3.metric(t("Avg Price (SAR)","متوسط السعر ر.س"),
                   f"{vp[vp>0].mean():,.0f}" if not vp[vp>0].empty else "—")
    if has_sys and sys_col in ok_work.columns:
        sm4.metric(t("Companies","الشركات"), ok_work[sys_col].nunique())
    show     = work.drop(columns=["_status"],errors="ignore").copy()
    _raw_qty = (pd.to_numeric(work[qc],errors="coerce").fillna(0)
                if qc in work.columns else pd.Series(dtype=float,index=work.index))
    if pc in show.columns:
        show[pc] = pd.to_numeric(show[pc],errors="coerce").map(
            lambda v: f"{v:.2f} SAR" if pd.notna(v) else "—")
    if qc in show.columns:
        _lang = get_lang()
        show[qc] = pd.to_numeric(show[qc],errors="coerce").map(
            lambda v: get_qty_display(v,_lang))
    low_idx  = set()
    if thresh > 0 and qc in work.columns:
        raw_q3  = pd.to_numeric(work[qc],errors="coerce")
        low_idx = set(work.index[(raw_q3>0)&(raw_q3<=thresh)])
    _zero_set = set(_raw_qty.index[_raw_qty==0]) if not _raw_qty.empty else set()
    _na_en = "Not Available"; _na_ar = "غير متوفر"
    cols = show.columns.tolist()
    th_  = "".join(f"<th>{c}</th>" for c in cols)
    def _row(idx_row):
        i,row = idx_row
        is_zero = i in _zero_set
        cls = " na-row" if is_zero else (" rl" if i in low_idx else "")
        cells = "".join(
            f'<td class="cf">{v}</td>' if ci==0
            else (f'<td class="na-cell">{v}</td>'
                  if is_zero and isinstance(v,str) and v in (_na_en,_na_ar)
                  else f"<td>{v}</td>")
            for ci,v in enumerate(row))
        return f'<tr class="{cls}">{cells}<tr>'
    tbody = "".join(_row(x) for x in show.iterrows())
    st.markdown(
        f'{_TABLE_CSS}<div class="swag-wrap">'
        f'<table class="swag-tbl"><thead><tr>{th_}</tr></thead>'
        f'<tbody>{tbody}</tbody></table></div>',
        unsafe_allow_html=True)
    st.caption(f"{len(show)} {t('rows shown','صفوف معروضة')} / {len(df)} {t('total','إجمالي')}")
    return work.drop(columns=["_status"],errors="ignore").copy()

def _render_html_table(df_display):
    if df_display is None or df_display.empty:
        st.info(t("No data.","لا بيانات.")); return
    cols = df_display.columns.tolist()
    th_  = "".join(f"<th>{c}</th>" for c in cols)
    def _row(idx_row):
        _,row = idx_row
        cells = "".join(
            f'<td class="cf">{v}</td>' if ci==0 else f"<td>{v}</td>"
            for ci,v in enumerate(row))
        return f"<tr>{cells}</tr>"
    tbody = "".join(_row(x) for x in df_display.iterrows())
    st.markdown(
        f'{_TABLE_CSS}<div class="swag-wrap">'
        f'<table class="swag-tbl"><thead><tr>{th_}</tr></thead>'
        f'<tbody>{tbody}</tbody></table></div>',
        unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIZE BREAKDOWN HELPER
# ─────────────────────────────────────────────────────────────────────────────

# Canonical size order for columns
_SIZE_ORDER = ["2XS","XS","S","M","L","XL","XXL","2XL","3XL","4XL","5XL","OSFA"]

# Regex: extract size suffix from model code
import re as _re
_SIZE_RE = _re.compile(
    r'-?(2XS|XS|S|M|L|XL|XXL|2XL|3XL|4XL|5XL|OSFA|OS)$',
    _re.IGNORECASE
)

def _extract_size(code: str):
    """Return (base_model, size) from a model code like XP6013-M."""
    code = str(code).strip()
    m = _SIZE_RE.search(code)
    if m:
        size = m.group(0).lstrip("-").upper()
        base = code[:m.start()].rstrip("-").strip()
        return base, size
    return code, ""   # no recognisable size suffix

def build_size_pivot(df, mc_col, qc_col, sc_col, pc_col, thr=0):
    """
    Build size-breakdown pivot from the flat stock dataframe.
    Returns (pivot_df, size_cols_found) or (None, []) if not possible.

    Columns: System | Base Model | Price | S | M | L | XL | XXL | ... | Total
    Rows   : one per (system × base_model)
    Color  : applied via HTML in caller
    """
    if df is None or df.empty: return None, []
    if mc_col not in df.columns or qc_col not in df.columns: return None, []

    work = df.copy()
    work["_qty_num"] = pd.to_numeric(work[qc_col], errors="coerce").fillna(0)
    work[["_base","_size"]] = work[mc_col].apply(
        lambda c: pd.Series(_extract_size(str(c))))

    # Only rows that have a recognised size
    sized = work[work["_size"] != ""].copy()
    if sized.empty: return None, []

    # Pivot: index = (system, base_model), columns = size, values = sum qty
    idx_cols = [c for c in [sc_col, "_base"] if c in sized.columns]
    pivot = (sized
             .pivot_table(index=idx_cols, columns="_size",
                          values="_qty_num", aggfunc="sum", fill_value=0)
             .reset_index())
    pivot.columns.name = None

    # Add price (first price for that base model)
    if pc_col in sized.columns:
        price_map = (sized.groupby("_base")[pc_col]
                     .first().reset_index()
                     .rename(columns={"_base":"_base", pc_col:"_price"}))
        pivot = pivot.merge(price_map, on="_base", how="left")
    else:
        pivot["_price"] = 0.0

    # Add Total column
    size_cols_found = [s for s in _SIZE_ORDER if s in pivot.columns]
    # Also pick up any sizes NOT in our canonical list
    extra_sizes = [c for c in pivot.columns
                   if c not in idx_cols + ["_price","_base"]
                   and c not in _SIZE_ORDER]
    size_cols_found = size_cols_found + sorted(extra_sizes)

    pivot["Total"] = pivot[size_cols_found].sum(axis=1)

    # Final column order
    base_col_name  = t("Base Model","الموديل الأساسي")
    price_col_name = t("Unit Price","سعر الوحدة")
    sys_col_label  = sc_col if sc_col in pivot.columns else None

    rename_map = {"_base": base_col_name, "_price": price_col_name}
    pivot = pivot.rename(columns=rename_map)

    ordered = []
    if sys_col_label and sys_col_label in pivot.columns:
        ordered.append(sys_col_label)
    ordered += [base_col_name, price_col_name]
    ordered += size_cols_found + ["Total"]
    ordered  = [c for c in ordered if c in pivot.columns]
    pivot    = pivot[ordered].sort_values(
        [sys_col_label, base_col_name] if sys_col_label else [base_col_name]
    ).reset_index(drop=True)

    return pivot, size_cols_found


def render_size_pivot(pivot_df, size_cols, thr=0):
    """Render the pivot as a colour-coded HTML table."""
    if pivot_df is None or pivot_df.empty:
        return

    cols = pivot_df.columns.tolist()
    th   = "".join(f"<th>{c}</th>" for c in cols)

    def _cell(col, val):
        # Size columns — colour by qty
        if col in size_cols or col == "Total":
            try:
                v = float(val)
            except Exception:
                return f"<td>{val}</td>"
            if v == 0:
                return (f'<td style="color:rgba(255,80,80,0.5);'
                        f'font-size:11px;">0</td>')
            elif thr > 0 and v <= thr:
                return (f'<td style="color:#D4A84B;font-weight:600;">'
                        f'{int(v)}</td>')
            else:
                return (f'<td style="color:#7FCDD3;font-weight:500;">'
                        f'{int(v)}</td>')
        # Total column bold
        if col == "Total":
            return f'<td style="color:#fff;font-weight:600;">{int(float(val)) if val else 0}</td>'
        # Price column
        if "Price" in str(col) or "سعر" in str(col):
            try:
                return f'<td style="color:#D4A84B;font-family:Outfit,monospace;font-size:11px;">{float(val):.2f}</td>'
            except Exception:
                return f"<td>{val}</table>"
        # Base model — monospace
        return f'<td class="cf">{val}</td>'

    def _row(ir):
        _, row = ir
        cells = "".join(_cell(col, val) for col, val in row.items())
        return f"<tr>{cells}</tr>"

    tbody = "".join(_row(x) for x in pivot_df.iterrows())

    _SZ_CSS = """<style>
.sz-wrap{width:100%;overflow-x:auto;border:1px solid rgba(74,172,180,0.08);
  border-radius:4px;overflow:hidden;margin-bottom:4px;}
.sz-tbl{width:100%;border-collapse:collapse;
  font-family:'Outfit','Tajawal',sans-serif;}
.sz-tbl thead tr{background:rgba(74,172,180,0.08);
  border-bottom:1px solid rgba(74,172,180,0.15);}
.sz-tbl thead th{color:#4AACB4;font-family:'Outfit',sans-serif;
  font-size:8px;letter-spacing:3px;text-transform:uppercase;
  font-weight:600;padding:12px 14px;text-align:center;white-space:nowrap;}
.sz-tbl tbody tr{border-bottom:1px solid rgba(255,255,255,0.03);
  transition:background 0.15s;}
.sz-tbl tbody tr:hover td{background:rgba(74,172,180,0.04);}
.sz-tbl tbody td{padding:10px 14px;text-align:center;
  font-size:12px;color:rgba(255,255,255,0.5);}
.sz-tbl tbody td.cf{font-family:'Outfit',monospace;font-size:11px;
  letter-spacing:0.5px;color:#fff;font-weight:500;
  border-right:1px solid rgba(74,172,180,0.08);}
</style>"""

    st.markdown(
        f'{_SZ_CSS}<div class="sz-wrap">'
        f'<table class="sz-tbl"><thead></tr>{th}<tr></thead>'
        f'<tbody>{tbody}</tbody></table></div>',
        unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────────────────────
def show_login():
    # ── Language toggle — fixed top right, above animated bg ─────────────
    # Inject CSS to push the radio widget to fixed top-right corner
    st.markdown("""
    <style>
    /* Force language toggle to fixed top-right above everything */
    div[data-testid="stRadio"]:has(label[style*="display: none"]) {
      position: fixed !important;
      top: 16px !important;
      right: 20px !important;
      z-index: 9999 !important;
      background: rgba(6,13,14,0.85) !important;
      border: 1px solid rgba(74,172,180,0.3) !important;
      border-radius: 100px !important;
      padding: 4px 12px !important;
      backdrop-filter: blur(10px) !important;
    }
    div[data-testid="stRadio"]:has(label[style*="display: none"]) label {
      color: rgba(255,255,255,0.7) !important;
      font-family: Outfit, sans-serif !important;
      font-size: 10px !important;
      letter-spacing: 2px !important;
    }
    div[data-testid="stRadio"]:has(label[style*="display: none"]) label[data-checked="true"],
    div[data-testid="stRadio"]:has(label[style*="display: none"]) [aria-checked="true"] + div {
      color: #4AACB4 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    lg = st.radio("",["EN","AR"],horizontal=True,
                  index=0 if get_lang()=="EN" else 1,
                  label_visibility="collapsed", key="llr")
    if lg != get_lang():
        st.session_state.lang = lg
        st.rerun()

    # ── Animated background + form ────────────────────────────────────────
    st.markdown("""
<style>
@keyframes float1{0%,100%{transform:translateY(0) rotate(0deg);}50%{transform:translateY(-18px) rotate(5deg);}}
@keyframes float2{0%,100%{transform:translateY(0) rotate(45deg);}50%{transform:translateY(-24px) rotate(50deg);}}
@keyframes float3{0%,100%{transform:translateY(0) rotate(20deg);}50%{transform:translateY(-12px) rotate(15deg);}}
@keyframes float4{0%,100%{transform:translateY(0) rotate(70deg);}60%{transform:translateY(-20px) rotate(65deg);}}
@keyframes float5{0%,100%{transform:translateY(0) rotate(30deg);}40%{transform:translateY(-16px) rotate(35deg);}}
@keyframes glowPulse{0%,100%{box-shadow:0 0 40px rgba(74,172,180,0.15),0 0 80px rgba(74,172,180,0.06);}
  50%{box-shadow:0 0 60px rgba(74,172,180,0.3),0 0 120px rgba(74,172,180,0.12),0 0 180px rgba(212,168,75,0.06);}}
@keyframes logoSpin{0%{transform:rotate(0deg);}100%{transform:rotate(360deg);}}
@keyframes titleReveal{from{opacity:0;transform:translateY(20px);}to{opacity:1;transform:translateY(0);}}
@keyframes shimmerBtn{0%{background-position:-200% center;}100%{background-position:200% center;}}
@keyframes beamRotate{0%{transform:rotate(0deg);}100%{transform:rotate(360deg);}}
@keyframes fadeInUp{from{opacity:0;transform:translateY(30px);}to{opacity:1;transform:translateY(0);}}
@keyframes borderGlow{0%,100%{border-color:rgba(74,172,180,0.2);}50%{border-color:rgba(74,172,180,0.5);}}
@keyframes dotPulse{0%,100%{transform:scale(1);opacity:1;}50%{transform:scale(1.4);opacity:0.7;}}

.login-bg{
  position:fixed;inset:0;background:#060d0e;overflow:hidden;z-index:0;
  pointer-events:none;
}
.login-particle{
  position:absolute;opacity:0.06;
}
.login-particle svg path,.login-particle svg rect{stroke:#4AACB4;}

/* Radial glow blobs */
.login-glow-teal{
  position:absolute;width:600px;height:600px;border-radius:50%;
  background:radial-gradient(circle,rgba(74,172,180,0.12) 0%,transparent 70%);
  left:-150px;top:-150px;pointer-events:none;
}
.login-glow-gold{
  position:absolute;width:400px;height:400px;border-radius:50%;
  background:radial-gradient(circle,rgba(212,168,75,0.07) 0%,transparent 70%);
  right:-100px;bottom:-100px;pointer-events:none;
}

/* Grid lines */
.login-grid{
  position:absolute;inset:0;
  background-image:
    linear-gradient(rgba(74,172,180,0.03) 1px,transparent 1px),
    linear-gradient(90deg,rgba(74,172,180,0.03) 1px,transparent 1px);
  background-size:60px 60px;
}

.login-wrap{
  position:relative;z-index:1;
  display:flex;flex-direction:column;align-items:center;
  padding:40px 20px 24px;
  animation:fadeInUp 0.8s ease forwards;
}

/* Logo ring */
.login-logo-ring{
  position:relative;width:100px;height:100px;margin:0 auto 28px;
}
.ring-outer{
  position:absolute;inset:0;border-radius:50%;
  border:1px solid rgba(74,172,180,0.25);
  animation:glowPulse 3s ease-in-out infinite,borderGlow 3s ease-in-out infinite;
}
.ring-inner{
  position:absolute;inset:10px;border-radius:50%;
  border:1px dashed rgba(74,172,180,0.12);
  animation:logoSpin 20s linear infinite;
}
.ring-center{
  position:absolute;inset:20px;
  display:flex;align-items:center;justify-content:center;
}
.ring-dot{
  position:absolute;width:6px;height:6px;border-radius:50%;background:#D4A84B;
  animation:dotPulse 2s ease-in-out infinite;
}
.ring-dot.t{top:3px;left:50%;transform:translateX(-50%);}
.ring-dot.r{right:3px;top:50%;transform:translateY(-50%);animation-delay:0.5s;}
.ring-dot.b{bottom:3px;left:50%;transform:translateX(-50%);animation-delay:1s;}
.ring-dot.l{left:3px;top:50%;transform:translateY(-50%);animation-delay:1.5s;}

.login-title-big{
  font-family:'Cormorant Garamond',serif;
  font-size:52px;font-weight:300;color:#fff;
  text-align:center;letter-spacing:8px;
  margin-bottom:6px;
  text-shadow:0 0 40px rgba(74,172,180,0.3);
}
.login-eyebrow{
  font-family:'Outfit',sans-serif;font-size:9px;letter-spacing:5px;
  text-transform:uppercase;color:#4AACB4;text-align:center;
  margin-bottom:32px;
}

/* Glass card */
.login-glass{
  width:100%;max-width:380px;
  background:rgba(255,255,255,0.03);
  backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  border:1px solid rgba(74,172,180,0.15);
  border-radius:16px;padding:32px;
  box-shadow:0 24px 64px rgba(0,0,0,0.4),inset 0 1px 0 rgba(255,255,255,0.05);
  animation:fadeInUp 0.9s 0.2s ease both;
}

.login-footer{
  font-family:'Outfit',sans-serif;font-size:8px;
  letter-spacing:3px;color:rgba(255,255,255,0.1);
  text-align:center;margin-top:24px;text-transform:uppercase;
}
</style>

<div class="login-bg">
  <div class="login-glow-teal"></div>
  <div class="login-glow-gold"></div>
  <div class="login-grid"></div>

  <!-- Floating particles -->
  <div class="login-particle" style="top:8%;left:6%;animation:float1 7s ease-in-out infinite;">
    <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
      <path d="M24 4 L44 24 L24 44 L4 24 Z" stroke="#4AACB4" stroke-width="0.8" fill="none"/>
      <path d="M24 12 L36 24 L24 36 L12 24 Z" stroke="#4AACB4" stroke-width="0.5" fill="none" opacity="0.5"/>
    </svg>
  </div>
  <div class="login-particle" style="top:15%;right:8%;animation:float2 9s ease-in-out infinite;">
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
      <rect x="4" y="4" width="24" height="24" stroke="#D4A84B" stroke-width="0.6" fill="none" opacity="0.6"/>
    </svg>
  </div>
  <div class="login-particle" style="top:60%;left:4%;animation:float3 8s ease-in-out infinite;">
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <path d="M12 2 L22 12 L12 22 L2 12 Z" stroke="#4AACB4" stroke-width="0.8" fill="rgba(74,172,180,0.06)"/>
    </svg>
  </div>
  <div class="login-particle" style="bottom:20%;right:5%;animation:float4 10s ease-in-out infinite;">
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
      <path d="M20 3 L37 20 L20 37 L3 20 Z" stroke="#4AACB4" stroke-width="0.6" fill="none"/>
      <circle cx="20" cy="3" r="1.5" fill="#D4A84B"/>
      <circle cx="37" cy="20" r="1.5" fill="#D4A84B"/>
      <circle cx="20" cy="37" r="1.5" fill="#D4A84B"/>
      <circle cx="3" cy="20" r="1.5" fill="#D4A84B"/>
    </svg>
  </div>
  <div class="login-particle" style="top:40%;right:3%;animation:float5 6s ease-in-out infinite;">
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <rect x="2" y="2" width="16" height="16" stroke="#D4A84B" stroke-width="0.6" fill="none" opacity="0.5" transform="rotate(45 10 10)"/>
    </svg>
  </div>
  <div class="login-particle" style="bottom:35%;left:8%;animation:float2 11s ease-in-out infinite;">
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
      <path d="M14 2 L26 14 L14 26 L2 14 Z" stroke="#4AACB4" stroke-width="0.5" fill="none" opacity="0.4"/>
    </svg>
  </div>
</div>
""", unsafe_allow_html=True)

    _,col,_ = st.columns([1,1.2,1])
    with col:
        st.markdown("""
        <div class="login-wrap">
          <div class="login-logo-ring">
            <div class="ring-outer"></div>
            <div class="ring-inner"></div>
            <div class="ring-dot t"></div>
            <div class="ring-dot r"></div>
            <div class="ring-dot b"></div>
            <div class="ring-dot l"></div>
            <div class="ring-center">
              <svg width="44" height="44" viewBox="0 0 44 44" fill="none">
                <path d="M22 4 L38 22 L22 40 L6 22 Z" stroke="#4AACB4" stroke-width="1.2" fill="none"/>
                <path d="M22 10 L32 22 L22 34 L12 22 Z" stroke="#4AACB4" stroke-width="0.7" fill="none" opacity="0.5"/>
                <path d="M22 15 L28 22 L22 29 L16 22 Z" fill="#4AACB4" opacity="0.5"/>
              </svg>
            </div>
          </div>
          <div class="login-title-big">SWAG</div>
          <div class="login-eyebrow">Product Intelligence · 5 Systems</div>
        </div>
        """, unsafe_allow_html=True)

        # Style the Streamlit form container to look like glass card
        st.markdown("""
        <style>
        /* Target the form container directly */
        [data-testid="stForm"]{
          background:rgba(255,255,255,0.03) !important;
          backdrop-filter:blur(20px) !important;
          -webkit-backdrop-filter:blur(20px) !important;
          border:1px solid rgba(74,172,180,0.2) !important;
          border-radius:16px !important;
          padding:24px !important;
          box-shadow:0 24px 64px rgba(0,0,0,0.4),
                     inset 0 1px 0 rgba(255,255,255,0.05) !important;
          animation:fadeInUp 0.9s 0.2s ease both !important;
        }
        </style>
        """, unsafe_allow_html=True)

        with st.form("lf", clear_on_submit=False):
            em = st.text_input(
                t("Email","البريد الإلكتروني"),
                placeholder="you@swag.com.sa")
            pw = st.text_input(
                t("Password","كلمة المرور"),
                type="password", placeholder="••••••••")
            st.markdown("<br>", unsafe_allow_html=True)
            sub = st.form_submit_button(
                t("Sign In →","تسجيل الدخول →"),
                use_container_width=True, type="primary")

        # Fix 2: Footer — brighter so it's readable
        st.markdown("""
        <div style='text-align:center;margin-top:20px;
                    font-family:Outfit,sans-serif;font-size:9px;
                    letter-spacing:3px;text-transform:uppercase;
                    color:rgba(255,255,255,0.35);'>
          SWAG DASHBOARD · 2025 · POWERED BY ODOO
        </div>
        """, unsafe_allow_html=True)

        if sub:
            if not em or not pw:
                st.error(t("Fill in both fields.","يرجى ملء جميع الحقول.")); return
            if "LOGIN" not in st.secrets:
                st.error("LOGIN section missing in secrets.toml"); return
            cfg = st.secrets["LOGIN"]
            with st.spinner(t("Authenticating...","جارٍ التحقق...")):
                try:
                    _login_url = str(cfg.get("url","")).rstrip("/")
                    if _login_url.endswith("/odoo"):
                        _login_url = _login_url[:-len("/odoo")]
                    proxy = xmlrpc.client.ServerProxy(
                        f"{_login_url}/xmlrpc/2/common", allow_none=True)
                    uid = proxy.authenticate(cfg["db"], em, pw, {})
                    if uid:
                        token = _make_token(em)
                        st.query_params["u"] = em
                        st.query_params["t"] = token
                        st.session_state.authenticated = True
                        st.session_state.user_email    = em
                        time.sleep(0.3); st.rerun()
                    else:
                        st.error(t("Wrong email or password.",
                                   "بريد إلكتروني أو كلمة مرور خاطئة."))
                except Exception as e:
                    st.error(f"Connection error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────────────────────────────────────
def do_logout():
    try: st.query_params.clear()
    except Exception: pass
    st.session_state.authenticated = False
    st.session_state.user_email    = ""
    st.rerun()

# =============================================================================
# SEASON COMPARISON MODULE (merged from v10)
# =============================================================================

# ---- Season detection constants -------------------------------------------------
SEASON_NAME_HINTS = [
    "season", "saison", "collection", "mawsim", "fasil",
    "موسم", "الموسم", "فصل", "كولكشن",
    "x_season", "x_collection", "x_saison", "x_mawsim",
]

ARABIC_SEASON_WORDS = [
    "صيفي", "شتوي", "ربيعي", "خريفي",
    "صيف", "شتاء", "ربيع", "خريف",
    "موسم", "فصل",
]

SEASON_CODE_PATTERNS = [
    r"\b(SS|AW|FW|SP|FA|SU|WI)\s*\d{2,4}\b",
    r"\b(S|W|F|A)\s*\d{2}\b",
    r"\b\d{2,4}\s*(SS|AW|FW|SP|FA)\b",
    r"\b(summer|winter|spring|fall|autumn)\b",
    r"\b(صيفي|شتوي|ربيعي|خريفي)\b",
    r"\b(صيفي|شتوي|ربيعي|خريفي)\s*\d{1,2}\b",
    r"\b\d{2,4}\s*(صيفي|شتوي|ربيعي|خريفي)\b",
]
SEASON_VALUE_RE = re.compile("|".join(SEASON_CODE_PATTERNS), re.IGNORECASE | re.UNICODE)

BLACKLIST_RELATION_MODELS = {
    "res.users", "res.partner", "res.company", "res.currency",
    "res.country", "res.lang", "res.groups",
    "uom.uom", "uom.category",
    "account.tax", "account.account", "account.journal",
    "mail.activity.type", "mail.template", "mail.alias",
    "ir.attachment", "ir.model", "ir.model.fields",
    "ir.actions.act_window", "ir.ui.view", "ir.ui.menu",
    "ir.rule", "ir.sequence",
    "stock.location", "stock.warehouse", "stock.quant",
}

USEFUL_FIELD_TYPES = {"many2one", "selection", "char", "text", "integer", "float"}

ALWAYS_SKIP_FIELDS = {
    "__last_update", "write_date", "create_date", "write_uid", "create_uid",
    "display_name", "image_1920", "image_1024", "image_512", "image_256",
    "image_128", "image_small", "image_medium",
    "message_ids", "message_follower_ids", "message_channel_ids",
    "message_main_attachment_id", "message_has_error",
    "message_needaction", "message_attachment_count",
    "message_needaction_counter", "message_has_error_counter",
    "website_message_ids", "activity_ids", "activity_state", "activity_type_id",
    "activity_user_id", "activity_summary", "activity_date_deadline",
    "activity_exception_decoration", "activity_exception_icon",
    "can_image_1024_be_zoomed",
}

ALWAYS_SKIP_PREFIXES = ("mail_", "message_", "activity_", "website_", "image_", "rating_")

AUDIT_SAMPLE_LIMIT = 300
RELATION_SAMPLE_LIMIT = 20
TEMPLATE_FETCH_LIMIT = 50000
PRODUCT_FETCH_LIMIT = 200000
QUANT_FETCH_LIMIT = 200000
PID_CHUNK = 1000

PRICE_DIFF_THRESHOLD_PCT = 10.0

MAX_SEASON_DISTINCT = 80
MAX_BRANCH_COLS = 120
HEAVY_COMPUTE_ROW_CAP = 8000

PREFERRED_SEASON_FIELD_NAMES = {
    "season_id", "x_season_id", "x_studio_season_id", "x_studio_season",
    "x_season", "season",
}

# ---- Season helper functions -------------------------------------------------
def normalize_text(v):
    return re.sub(r"\s+", " ", str(v or "").strip()).lower()

def season_norm(v):
    s = normalize_text(v)
    return s.replace("-", "").replace("_", "").replace("/", "").replace(" ", "")

SEASON_TYPE_HINTS = [
    (("صيفي", "صيف", "summer", "ss", "su"), "SUMMER"),
    (("شتوي", "شتاء", "winter", "aw", "fw", "wi"), "WINTER"),
    (("ربيعي", "ربيع", "spring", "sp"), "SPRING"),
    (("خريفي", "خريف", "fall", "autumn", "fa"), "FALL"),
]

SEASON_TYPE_LABEL = {
    "SUMMER": "Summer / صيفي",
    "WINTER": "Winter / شتوي",
    "SPRING": "Spring / ربيعي",
    "FALL": "Fall / خريفي",
}

def season_type_only(label):
    s = normalize_text(label)
    for words, canon in SEASON_TYPE_HINTS:
        for w in words:
            if len(w) <= 2:
                if re.search(rf"\b{re.escape(w)}\b", s):
                    return canon
            elif w in s:
                return canon
    return None

def season_year(label):
    nums = re.findall(r"\d+", str(label or ""))
    if not nums:
        return ""
    n = nums[-1]
    if len(n) >= 4:
        return n[:4]
    if len(n) == 2:
        return "20" + n
    if len(n) == 1:
        return "200" + n
    return n

def season_signature(label):
    stype = season_type_only(label)
    if not stype:
        return None
    yr = season_year(label)
    return stype + (yr[-2:] if yr else "")

def should_skip_field(field_name, field_info):
    fn = field_name.lower()
    if field_name in ALWAYS_SKIP_FIELDS:
        return True
    for prefix in ALWAYS_SKIP_PREFIXES:
        if fn.startswith(prefix):
            return True
    if field_info.get("type", "") not in USEFUL_FIELD_TYPES:
        return True
    return False

def looks_like_season_value(val_str):
    if not val_str:
        return False
    val = str(val_str).strip()
    if any(word in val for word in ARABIC_SEASON_WORDS):
        return True
    return bool(SEASON_VALUE_RE.search(val))

def score_field_name(field_name, field_label):
    score = 0
    fn = field_name.lower()
    lbl = (field_label or "").lower()
    for hint in SEASON_NAME_HINTS:
        if hint in fn:
            score += 30
        if hint in lbl:
            score += 25
    if fn.startswith("x_studio"):
        score += 5
    elif fn.startswith("x_"):
        score += 3
    return score

def score_relation_model(relation):
    if not relation:
        return 0
    if relation in BLACKLIST_RELATION_MODELS:
        return -50
    rel = relation.lower()
    for hint in SEASON_NAME_HINTS:
        if hint in rel:
            return 30
    return 0

def safe_domain(conditions):
    result = []
    for c in conditions:
        if isinstance(c, (list, tuple)) and len(c) == 3:
            field, op, val = c
            result.append([field, op, val])
        else:
            result.append(c)
    return result

def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]

def _is_preferred_season_candidate(c):
    fn = (c.get("field_name") or "").lower()
    rel = (c.get("relation_model") or "").lower()
    if fn in PREFERRED_SEASON_FIELD_NAMES:
        return True
    if "season" in rel:
        return True
    return False

# ---- Core season detection functions -----------------------------------------
def _probe_relation_model(url, db, uid, api_key, relation_model, related_ids):
    result = {"sample_names": [], "season_like_count": 0, "total_fetched": 0, "error": None}
    if not related_ids or not relation_model:
        return result
    unique_ids = list({i for i in related_ids if isinstance(i, int)})[:RELATION_SAMPLE_LIMIT]
    if not unique_ids:
        return result
    try:
        recs = _x(url, db, uid, api_key, relation_model, "search_read",
                  safe_domain([["id", "in", unique_ids]]),
                  {"fields": ["id", "name", "display_name"], "limit": RELATION_SAMPLE_LIMIT})
        result["total_fetched"] = len(recs)
        for rec in recs:
            name = rec.get("display_name") or rec.get("name") or ""
            if isinstance(name, list):
                name = name[1] if len(name) > 1 else str(name)
            name = str(name).strip()
            if name:
                result["sample_names"].append(name)
                if looks_like_season_value(name):
                    result["season_like_count"] += 1
    except Exception as e:
        result["error"] = str(e)
    return result

def deep_season_audit_for_system(system_key):
    audit = {
        "system": system_key, "status": "pending", "error": None,
        "candidates": [], "best_field": None, "confident": False,
        "manual_pick_needed": False, "raw_field_count": 0,
        "eligible_field_count": 0, "sample_ids_loaded": 0,
        "product_records_loaded": 0, "fetch_errors": [],
    }
    cfg = get_system_config(system_key)
    if not cfg:
        audit["status"] = "no_config"; audit["error"] = "No configuration found in secrets."
        return audit
    auth_res = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth_res["ok"]:
        audit["status"] = "auth_failed"; audit["error"] = auth_res.get("error", "Authentication failed")
        return audit
    uid = auth_res["uid"]
    url, db, api_key = cfg["url"], cfg["db"], cfg["api_key"]
    candidates = []
    for model in ["product.template", "product.product"]:
        try:
            fields_meta = _x(url, db, uid, api_key, model, "fields_get", [],
                             {"attributes": ["string", "type", "relation", "store"]})
        except Exception as e:
            audit["fetch_errors"].append(f"fields_get/{model}: {e}")
            continue
        audit["raw_field_count"] += len(fields_meta)
        eligible_fields = {fn: fi for fn, fi in fields_meta.items() if not should_skip_field(fn, fi)}
        audit["eligible_field_count"] += len(eligible_fields)
        if not eligible_fields:
            continue
        sample_ids = []
        for domain_attempt in [[], [[1, "=", 1]]]:
            try:
                sample_recs = _x(url, db, uid, api_key, model, "search_read",
                                 domain_attempt, {"fields": ["id"], "limit": AUDIT_SAMPLE_LIMIT})
                if sample_recs:
                    sample_ids = [r["id"] for r in sample_recs]
                    break
            except Exception as e:
                audit["fetch_errors"].append(f"search_ids/{model}: {e}")
        audit["sample_ids_loaded"] += len(sample_ids)
        product_records = []
        if sample_ids:
            field_list = list(eligible_fields.keys())
            fetched_recs = {}
            for i in range(0, len(field_list), 60):
                chunk_fields = field_list[i:i + 60]
                try:
                    recs = _x(url, db, uid, api_key, model, "search_read",
                              safe_domain([["id", "in", sample_ids]]),
                              {"fields": chunk_fields, "limit": AUDIT_SAMPLE_LIMIT})
                    for rec in recs:
                        fetched_recs.setdefault(rec["id"], {}).update(rec)
                except Exception as e:
                    audit["fetch_errors"].append(f"search_read/{model}/chunk{i}: {e}")
            product_records = list(fetched_recs.values())
            audit["product_records_loaded"] += len(product_records)
        for fname, finfo in eligible_fields.items():
            ftype = finfo.get("type", "")
            relation = finfo.get("relation", "") or ""
            flabel = finfo.get("string", fname)
            name_score = score_field_name(fname, flabel)
            rel_score = score_relation_model(relation)
            candidate = {
                "field_name": fname, "field_label": flabel, "model": model,
                "field_type": ftype, "relation_model": relation,
                "name_score": name_score, "relation_model_score": rel_score,
                "data_score": 0, "total_score": 0, "non_empty_count": 0,
                "sample_raw_values": [], "season_like_direct_count": 0,
                "relation_probe": None, "rejection_reason": None,
            }
            if relation and relation in BLACKLIST_RELATION_MODELS:
                candidate["rejection_reason"] = f"Blacklisted relation: {relation}"
                candidate["total_score"] = name_score + rel_score
                candidates.append(candidate); continue
            if not product_records:
                candidate["rejection_reason"] = "No product records loaded (name-only score)"
                candidate["total_score"] = name_score + rel_score
                candidates.append(candidate); continue
            related_ids_seen = []
            for rec in product_records:
                val = rec.get(fname)
                if val is False or val is None:
                    continue
                if ftype == "many2one":
                    if isinstance(val, list) and len(val) >= 2:
                        related_ids_seen.append(val[0]); display = str(val[1])
                    elif isinstance(val, int) and val:
                        related_ids_seen.append(val); display = str(val)
                    else:
                        continue
                else:
                    display = str(val).strip()
                    if not display:
                        continue
                candidate["non_empty_count"] += 1
                if len(candidate["sample_raw_values"]) < 10:
                    candidate["sample_raw_values"].append(display)
                if looks_like_season_value(display):
                    candidate["season_like_direct_count"] += 1
            if candidate["non_empty_count"] == 0:
                candidate["rejection_reason"] = "No non-empty values in sample"
                candidate["total_score"] = name_score + rel_score
                candidates.append(candidate); continue
            if ftype == "many2one" and relation and related_ids_seen:
                probe = _probe_relation_model(url, db, uid, api_key, relation, related_ids_seen)
                candidate["relation_probe"] = probe
                candidate["season_like_direct_count"] += probe.get("season_like_count", 0)
                for rname in probe.get("sample_names", []):
                    if len(candidate["sample_raw_values"]) < 10:
                        candidate["sample_raw_values"].append("[rel] " + rname)
            ratio = candidate["season_like_direct_count"] / max(candidate["non_empty_count"], 1)
            candidate["data_score"] = ratio * 50
            candidate["total_score"] = name_score + rel_score + candidate["data_score"]
            if candidate["total_score"] <= 0:
                candidate["rejection_reason"] = "Score ≤ 0"
            candidates.append(candidate)
    candidates.sort(key=lambda c: c["total_score"], reverse=True)
    audit["candidates"] = candidates
    positive = [c for c in candidates if c["total_score"] > 0]
    if positive:
        best = positive[0]
        audit["best_field"] = best
        probe = best.get("relation_probe") or {}
        if (best["name_score"] >= 25 or best["season_like_direct_count"] > 0
                or probe.get("season_like_count", 0) > 0 or best["data_score"] > 0):
            audit["confident"] = True
        audit["status"] = "ok"
    elif candidates:
        audit["status"] = "no_confident_field"; audit["manual_pick_needed"] = True
        audit["error"] = "Fields found but none scored positively. Use manual override below."
    else:
        audit["status"] = "no_candidates"; audit["error"] = "No eligible fields at all."
    return audit

def fetch_distinct_seasons_from_field(system_key, model, field, ftype, relation):
    cfg = get_system_config(system_key)
    if not cfg:
        return []
    auth = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth["ok"]:
        return []
    uid = auth["uid"]
    url, db, api_key = cfg["url"], cfg["db"], cfg["api_key"]

    # Fast path: read_group
    try:
        groups = _x(url, db, uid, api_key, model, "read_group",
                    [safe_domain([[field, "!=", False]])], [field], [field], {"lazy": False})
        seasons = {}
        for g in groups or []:
            val = g.get(field)
            if val is False or val is None:
                continue
            if ftype == "many2one":
                if isinstance(val, list) and len(val) >= 2:
                    seasons[val[0]] = str(val[1]).strip()
                elif isinstance(val, int) and val:
                    seasons[val] = str(val)
            else:
                seasons[val] = str(val).strip()
        out = [(v, lbl) for v, lbl in seasons.items() if str(lbl).strip()]
        if out:
            out.sort(key=lambda x: str(x[1]))
            return out
    except Exception:
        pass

    # Fallback: full scan
    try:
        records = _x(url, db, uid, api_key, model, "search_read",
                     safe_domain([[field, "!=", False]]),
                     {"fields": [field], "limit": 50000})
        if not records:
            return []
        unique_vals = {}
        related_ids = []
        for rec in records:
            val = rec.get(field)
            if val is False or val is None:
                continue
            if ftype == "many2one":
                if isinstance(val, list) and len(val) >= 2:
                    unique_vals[val[0]] = str(val[1]).strip(); related_ids.append(val[0])
                elif isinstance(val, int) and val:
                    unique_vals[val] = str(val); related_ids.append(val)
            else:
                unique_vals[val] = str(val).strip()
        if ftype == "many2one" and relation and related_ids:
            try:
                rel_recs = _x(url, db, uid, api_key, relation, "search_read",
                              safe_domain([["id", "in", list(set(related_ids))]]),
                              {"fields": ["id", "name", "display_name"],
                               "limit": len(set(related_ids)) + 10})
                for r in rel_recs:
                    name = r.get("display_name") or r.get("name") or str(r["id"])
                    if isinstance(name, list):
                        name = name[1] if len(name) > 1 else str(name)
                    unique_vals[r["id"]] = str(name).strip()
            except Exception:
                pass
        seasons = [(v, unique_vals[v]) for v in unique_vals if str(unique_vals[v]).strip()]
        seasons.sort(key=lambda x: str(x[1]))
        return seasons
    except Exception:
        return []

def fetch_distinct_seasons_from_audit(system_key, audit):
    if not audit.get("confident") or not audit.get("best_field"):
        return []
    best = audit["best_field"]
    return fetch_distinct_seasons_from_field(
        system_key, best["model"], best["field_name"], best["field_type"], best["relation_model"]
    )

@st.cache_data(ttl=3600, show_spinner=False)
def run_full_discovery():
    audits = {}
    all_systems_info = {}

    def _work(sys):
        audit = deep_season_audit_for_system(sys)
        info = None
        try:
            cands = audit.get("candidates", [])

            # 1) Explicit shared season field
            preferred = next((c for c in cands if _is_preferred_season_candidate(c)), None)
            if preferred is not None:
                seasons = fetch_distinct_seasons_from_field(
                    sys, preferred["model"], preferred["field_name"],
                    preferred["field_type"], preferred["relation_model"])
                if seasons and len(seasons) <= MAX_SEASON_DISTINCT:
                    audit["best_field"] = preferred
                    audit["chosen_field"] = preferred["field_name"]
                    audit["confident"] = True
                    audit["status"] = "ok"
                    info = {"model": preferred["model"], "field": preferred["field_name"],
                            "ftype": preferred["field_type"], "relation": preferred["relation_model"],
                            "seasons": seasons}

            # 2) Name-based fallback
            if info is None:
                name_cand = next((c for c in cands
                                  if c.get("field_name") == "name" and c.get("field_type") == "char"), None)
                if name_cand is not None:
                    raw = fetch_distinct_seasons_from_field(
                        sys, name_cand["model"], "name", "char", "")
                    season_named = [(v, lbl) for v, lbl in raw if season_type_only(lbl)]
                    if season_named:
                        audit["best_field"] = name_cand
                        audit["chosen_field"] = "name (season-in-name)"
                        audit["confident"] = True
                        audit["status"] = "ok_name_fallback"
                        info = {"model": name_cand["model"], "field": "name",
                                "ftype": "char", "relation": "",
                                "seasons": season_named, "name_fallback": True}

            # 3) Last resort — auto best field, with distinct-value cap
            if info is None and audit.get("best_field") is not None:
                best = audit["best_field"]
                if not _is_preferred_season_candidate(best):
                    seasons = fetch_distinct_seasons_from_field(
                        sys, best["model"], best["field_name"],
                        best["field_type"], best["relation_model"])
                    if seasons and len(seasons) <= MAX_SEASON_DISTINCT:
                        audit["chosen_field"] = best["field_name"]
                        audit["confident"] = True
                        audit["status"] = "ok"
                        info = {"model": best["model"], "field": best["field_name"],
                                "ftype": best["field_type"], "relation": best["relation_model"],
                                "seasons": seasons}
                    elif seasons:
                        audit["status"] = "rejected_junk"
                        audit["confident"] = False
                        audit["manual_pick_needed"] = True
                        audit["rejected_too_many"] = [(best["field_name"], len(seasons))]
                        audit["error"] = (
                            f"Detected field '{best['field_name']}' has {len(seasons):,} distinct "
                            f"values (> {MAX_SEASON_DISTINCT}) — looks like category/product-name "
                            "data, not a season field. Excluded. Use manual override if a real "
                            "season field exists.")
        except Exception as e:
            audit["status"] = "discovery_error"
            audit["error"] = f"Season fetch failed: {e}"
        return sys, audit, info

    with ThreadPoolExecutor(max_workers=len(SYSTEM_KEYS)) as executor:
        for sys, audit, info in executor.map(_work, SYSTEM_KEYS):
            audits[sys] = audit
            if info:
                all_systems_info[sys] = info
    return all_systems_info, audits

def get_stock_context(cfg, include_archived=False):
    ctx = {}
    if include_archived:
        ctx["active_test"] = False
    if not cfg:
        return ctx
    try:
        if cfg.get("company_id"):
            cid = int(cfg["company_id"])
            ctx["allowed_company_ids"] = [cid]
            ctx["force_company"] = cid
    except Exception:
        pass
    return ctx

def get_internal_locations(system_key):
    """{location_id: location_name} for all internal, active locations."""
    cfg = get_system_config(system_key)
    if not cfg:
        return {}
    auth = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth["ok"]:
        return {}
    uid = auth["uid"]
    url, db, api_key = cfg["url"], cfg["db"], cfg["api_key"]
    try:
        locs = _x(url, db, uid, api_key, "stock.location", "search_read",
                  safe_domain([["usage", "=", "internal"], ["active", "=", True]]),
                  {"fields": ["id", "complete_name", "display_name", "name"],
                   "limit": 10000})
        out = {}
        for l in locs or []:
            nm = l.get("complete_name") or l.get("display_name") or l.get("name") or str(l["id"])
            if isinstance(nm, list):
                nm = nm[1] if len(nm) > 1 else str(nm)
            out[l["id"]] = str(nm).strip()
        return out
    except Exception:
        return {}

def resolve_season_values_for_system(query, sys_info, mode="type"):
    seasons = sys_info.get("seasons", [])
    if not seasons:
        return [], [], "No seasons available"
    out_vals, out_lbls, seen = [], [], set()

    def add(val, lbl):
        if (val, lbl) not in seen:
            seen.add((val, lbl)); out_vals.append(val); out_lbls.append(lbl)

    q_norm = season_norm(query)
    q_type = season_type_only(query)
    q_year = season_year(query)

    if mode == "type":
        if not q_type:
            return [], [], f"'{query}' is not a recognized season type"
        for val, lbl in seasons:
            if season_type_only(lbl) == q_type:
                add(val, lbl)
        return (out_vals, out_lbls, None) if out_vals else ([], [], f"No '{q_type}' seasons found")

    for val, lbl in seasons:
        if lbl == query:
            add(val, lbl)
    if out_vals:
        return out_vals, out_lbls, None
    for val, lbl in seasons:
        if season_norm(lbl) == q_norm:
            add(val, lbl)
    if out_vals:
        return out_vals, out_lbls, None
    if q_type and q_year:
        sig = season_signature(query)
        for val, lbl in seasons:
            if season_signature(lbl) == sig:
                add(val, lbl)
        return (out_vals, out_lbls, None) if out_vals else ([], [], f"Season not found: {query}")
    if q_type:
        for val, lbl in seasons:
            if season_type_only(lbl) == q_type:
                add(val, lbl)
        if out_vals:
            return out_vals, out_lbls, None
    return [], [], f"Season not found: {query}"

# ---- Fetch season products (quant-based) ------------------------------------
LONG_COLS = ["System", "Branch", "Match Key", "Model Code", "Product", "Season", "Year", "Qty", "Price"]

def fetch_season_products(system_key, sys_info, query, mode="type", include_archived=False):
    cfg = get_system_config(system_key)
    if not cfg:
        return pd.DataFrame(columns=LONG_COLS), {"error": "No config"}
    auth = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth["ok"]:
        return pd.DataFrame(columns=LONG_COLS), {"error": "Auth failed: " + str(auth.get("error"))}

    uid = auth["uid"]
    url, db, api_key = cfg["url"], cfg["db"], cfg["api_key"]
    model, field, ftype = sys_info["model"], sys_info["field"], sys_info["ftype"]
    ctx = get_stock_context(cfg, include_archived)

    stored_values, matched_labels, resolve_err = resolve_season_values_for_system(query, sys_info, mode)
    val_to_label = dict(zip(stored_values, matched_labels))

    debug = {
        "system": system_key, "model": model, "field": field, "mode": mode,
        "requested": query, "matched_labels": matched_labels,
        "matched_years": sorted({season_year(l) for l in matched_labels if season_year(l)}),
        "stored_values": stored_values, "resolve_error": resolve_err,
        "models_found": 0, "with_stock": 0, "branches": 0,
        "limit_hit": False, "error": None,
    }
    if resolve_err or not stored_values:
        debug["error"] = resolve_err or "No matching stored values"
        return pd.DataFrame(columns=LONG_COLS), debug

    prod_fields = ["default_code", "barcode", "display_name",
                   "list_price", "lst_price", "product_tmpl_id"]

    try:
        # ── 1. Master product list of the season ──
        if model == "product.template":
            tmpl_domain = (safe_domain([[field, "=", stored_values[0]]])
                           if len(stored_values) == 1
                           else safe_domain([[field, "in", stored_values]]))
            tmpl_recs = _x(url, db, uid, api_key, "product.template", "search_read",
                           tmpl_domain, {"fields": ["id", field],
                                         "limit": TEMPLATE_FETCH_LIMIT, "context": ctx}) or []
            if len(tmpl_recs) >= TEMPLATE_FETCH_LIMIT:
                debug["limit_hit"] = True
            tmpl_season = {}
            for tr in tmpl_recs:
                v = tr.get(field)
                if isinstance(v, list) and v:
                    v = v[0]
                tmpl_season[tr["id"]] = val_to_label.get(v, ", ".join(matched_labels))
            if not tmpl_season:
                return pd.DataFrame(columns=LONG_COLS), debug
            products = []
            for batch in _chunks(list(tmpl_season.keys()), 50):
                recs = _x(url, db, uid, api_key, "product.product", "search_read",
                          safe_domain([["product_tmpl_id", "in", batch]]),
                          {"fields": prod_fields, "limit": 20000, "context": ctx})
                if recs:
                    products.extend(recs)

            def season_of(p):
                tm = p.get("product_tmpl_id")
                tid = tm[0] if isinstance(tm, list) and tm else tm
                return tmpl_season.get(tid, ", ".join(matched_labels))
        else:
            prod_domain = (safe_domain([[field, "=", stored_values[0]]])
                           if len(stored_values) == 1
                           else safe_domain([[field, "in", stored_values]]))
            products = _x(url, db, uid, api_key, "product.product", "search_read",
                          prod_domain, {"fields": prod_fields + [field],
                                        "limit": PRODUCT_FETCH_LIMIT, "context": ctx}) or []
            if len(products) >= PRODUCT_FETCH_LIMIT:
                debug["limit_hit"] = True

            def season_of(p):
                v = p.get(field)
                if isinstance(v, list) and v:
                    v = v[0]
                return val_to_label.get(v, ", ".join(matched_labels))

        if not products:
            return pd.DataFrame(columns=LONG_COLS), debug

        pmap = {p["id"]: p for p in products}
        pids = list(pmap.keys())
        debug["models_found"] = len(pids)

        # ── 2. Internal locations + quants ──
        loc_map = get_internal_locations(system_key)
        loc_ids = list(loc_map.keys())

        quants = []
        if loc_ids:
            for chunk in _chunks(pids, PID_CHUNK):
                qs = _x(url, db, uid, api_key, "stock.quant", "search_read",
                        safe_domain([["product_id", "in", chunk],
                                     ["location_id", "in", loc_ids],
                                     ["quantity", ">", 0]]),
                        {"fields": ["product_id", "location_id", "quantity"],
                         "limit": QUANT_FETCH_LIMIT, "context": ctx})
                if qs:
                    quants.extend(qs)

        def meta(pid):
            p = pmap.get(pid, {})
            code = str(p.get("default_code") or "").strip()
            barcode = str(p.get("barcode") or "").strip()
            name = str(p.get("display_name") or "").strip()
            if code:
                mk = code
            elif barcode:
                mk = "bc::" + barcode
            else:
                mk = "name::" + normalize_text(name)
            price = p.get("lst_price")
            if price in (None, False):
                price = p.get("list_price")
            return mk, code, name, float(price or 0), season_of(p)

        rows = []
        seen_pids = set()
        branches = set()
        for q in quants:
            pr = q.get("product_id")
            pid = pr[0] if isinstance(pr, list) and pr else pr
            if pid not in pmap:
                continue
            loc = q.get("location_id")
            if isinstance(loc, list) and loc:
                bname = loc[1] if len(loc) > 1 else loc_map.get(loc[0], "—")
            else:
                bname = loc_map.get(loc, "—")
            bname = str(bname).strip() or "—"
            branches.add(bname)
            seen_pids.add(pid)
            mk, code, name, price, season_lbl = meta(pid)
            rows.append({
                "System": system_key, "Branch": bname, "Match Key": mk,
                "Model Code": code, "Product": name,
                "Season": season_lbl, "Year": season_year(season_lbl),
                "Qty": float(q.get("quantity") or 0), "Price": price,
            })

        # coverage: products with no stock anywhere
        for pid in pids:
            if pid not in seen_pids:
                mk, code, name, price, season_lbl = meta(pid)
                rows.append({
                    "System": system_key, "Branch": "—", "Match Key": mk,
                    "Model Code": code, "Product": name,
                    "Season": season_lbl, "Year": season_year(season_lbl),
                    "Qty": 0.0, "Price": price,
                })

        debug["with_stock"] = len(seen_pids)
        debug["branches"] = len(branches)

        df = pd.DataFrame(rows, columns=LONG_COLS)
        if df.empty:
            return df, debug
        df = (df.groupby(["System", "Branch", "Match Key", "Model Code",
                          "Product", "Season", "Year"], as_index=False)
                .agg({"Qty": "sum", "Price": "max"}))
        return df, debug

    except Exception as e:
        debug["error"] = str(e)
        return pd.DataFrame(columns=LONG_COLS), debug

# ---- Build matrices ---------------------------------------------------------
def _join_distinct(series):
    vals = []
    for x in series:
        x = str(x).strip()
        if x and x not in vals:
            vals.append(x)
    return ", ".join(sorted(vals))

def build_matrices(query, all_systems_info, mode="type", include_archived=False):
    """Returns (long_df, company_matrix, debug). Branch view is derived from long_df."""
    parts = {}
    debug = {}
    with ThreadPoolExecutor(max_workers=len(all_systems_info) or 1) as ex:
        futs = {ex.submit(fetch_season_products, sys, info, query, mode, include_archived): sys
                for sys, info in all_systems_info.items()}
        for fut in as_completed(futs):
            sys = futs[fut]
            try:
                df, dbg = fut.result()
                debug[sys] = dbg
                if not df.empty:
                    parts[sys] = df
            except Exception as e:
                debug[sys] = {"error": str(e)}

    if not parts:
        return pd.DataFrame(columns=LONG_COLS), pd.DataFrame(), debug

    long_df = pd.concat(parts.values(), ignore_index=True)

    # ── Company matrix: qty per system ──
    qty_pivot = long_df.pivot_table(index="Match Key", columns="System", values="Qty", aggfunc="sum", fill_value=0)
    price_pivot = long_df.pivot_table(index="Match Key", columns="System", values="Price", aggfunc="max", fill_value=0)
    systems_all = [s for s in SYSTEM_KEYS if s in all_systems_info]
    for s in systems_all:
        if s not in qty_pivot.columns:
            qty_pivot[s] = 0
        if s not in price_pivot.columns:
            price_pivot[s] = 0
    qty_pivot = qty_pivot[systems_all]
    price_pivot = price_pivot[systems_all]
    qty_pivot.columns = [f"{c} Qty" for c in qty_pivot.columns]
    price_pivot.columns = [f"{c} Price" for c in price_pivot.columns]

    code_map = long_df.groupby("Match Key")["Model Code"].agg(
        lambda s: next((x for x in s if str(x).strip()), "")).reset_index()
    prod_map = long_df.groupby("Match Key")["Product"].agg(
        lambda s: next((x for x in s if str(x).strip()), "")).reset_index()
    season_map = long_df.groupby("Match Key")["Season"].agg(_join_distinct).reset_index()
    year_map = long_df.groupby("Match Key")["Year"].agg(_join_distinct).reset_index()

    comp = (qty_pivot.join(price_pivot, how="outer").reset_index()
            .merge(code_map, on="Match Key", how="left")
            .merge(prod_map, on="Match Key", how="left")
            .merge(season_map, on="Match Key", how="left")
            .merge(year_map, on="Match Key", how="left"))

    qcols = [c for c in comp.columns if c.endswith(" Qty")]
    pcols = [c for c in comp.columns if c.endswith(" Price")]
    for c in qcols:
        comp[c] = pd.to_numeric(comp[c], errors="coerce").fillna(0).astype(int)
    for c in pcols:
        comp[c] = pd.to_numeric(comp[c], errors="coerce").fillna(0).round(2)
    comp["Model Code"] = comp["Model Code"].fillna("").astype(str)
    comp["Product"] = comp["Product"].fillna("").astype(str)
    comp["Year"] = comp["Year"].fillna("").astype(str)
    comp["Season"] = comp["Season"].fillna("").astype(str)
    comp["Total Qty"] = comp[qcols].sum(axis=1).astype(int)

    ordered = ["Model Code", "Product", "Year", "Season"]
    for sys in SYSTEM_KEYS:
        if f"{sys} Qty" in comp.columns:
            ordered.append(f"{sys} Qty")
        if f"{sys} Price" in comp.columns:
            ordered.append(f"{sys} Price")
    ordered.append("Total Qty")
    comp = comp[[c for c in ordered if c in comp.columns]]
    comp = comp.sort_values(["Total Qty", "Model Code"], ascending=[False, True]).reset_index(drop=True)
    return long_df, comp, debug

def build_branch_matrix(long_df):
    if long_df.empty:
        return pd.DataFrame()
    piv = long_df.pivot_table(index=["Model Code", "Product", "Year"],
                              columns=["System", "Branch"], values="Qty",
                              aggfunc="sum", fill_value=0)
    piv.columns = [f"{a} | {b}" for a, b in piv.columns]
    piv = piv.reset_index().copy()
    branch_cols = [c for c in piv.columns if " | " in c]
    for c in branch_cols:
        piv[c] = pd.to_numeric(piv[c], errors="coerce").fillna(0).astype(int)
    piv["Total"] = piv[branch_cols].sum(axis=1).astype(int)
    piv = piv.sort_values(["Total", "Model Code"], ascending=[False, True]).reset_index(drop=True)
    return piv

def build_size_pivot_season(long_df):
    """base_model x size pivot of qty (summed across all systems & branches)."""
    if long_df is None or long_df.empty:
        return pd.DataFrame(), []
    w = long_df.copy()
    w["_qty"] = pd.to_numeric(w["Qty"], errors="coerce").fillna(0)
    bs = w["Model Code"].apply(lambda c: pd.Series(_extract_size(str(c)), index=["_base", "_size"]))
    w = pd.concat([w, bs], axis=1)
    sized = w[w["_size"] != ""]
    if sized.empty:
        return pd.DataFrame(), []
    piv = sized.pivot_table(index="_base", columns="_size", values="_qty",
                            aggfunc="sum", fill_value=0).reset_index()
    piv.columns.name = None
    size_cols = [s for s in _SIZE_ORDER if s in piv.columns]
    extra = [c for c in piv.columns if c not in (["_base"] + _SIZE_ORDER)]
    size_cols = size_cols + sorted(extra)
    for c in size_cols:
        piv[c] = pd.to_numeric(piv[c], errors="coerce").fillna(0).astype(int)
    piv["Total"] = piv[size_cols].sum(axis=1).astype(int)
    prod_map = (sized.groupby("_base")["Product"]
                .agg(lambda s: next((x for x in s if str(x).strip()), "")).to_dict())
    piv.insert(1, "Product", piv["_base"].map(prod_map).fillna(""))
    piv = piv.rename(columns={"_base": "Base Model"})
    piv = piv[["Base Model", "Product"] + size_cols + ["Total"]]
    return piv.sort_values(["Total", "Base Model"], ascending=[False, True]).reset_index(drop=True), size_cols

def units_by_company(long_df):
    if long_df is None or long_df.empty:
        return pd.DataFrame()
    w = long_df.copy()
    w["_qty"] = pd.to_numeric(w["Qty"], errors="coerce").fillna(0)
    g = w.groupby("System", as_index=False)["_qty"].sum().rename(columns={"_qty": "Units"})
    g["Company"] = g["System"].map(get_system_name)
    return g.set_index("Company")[["Units"]].sort_values("Units", ascending=False)

def units_by_branch(long_df, top_n=20):
    if long_df is None or long_df.empty:
        return pd.DataFrame()
    w = long_df.copy()
    w["_qty"] = pd.to_numeric(w["Qty"], errors="coerce").fillna(0)
    w["Loc"] = w["System"].map(get_system_name) + " | " + w["Branch"].astype(str)
    g = (w.groupby("Loc", as_index=False)["_qty"].sum()
         .rename(columns={"_qty": "Units"}).sort_values("Units", ascending=False))
    return g.head(top_n).set_index("Loc")[["Units"]]

def stock_health(comp, active_systems):
    qcols = [f"{s} Qty" for s in active_systems if f"{s} Qty" in comp.columns]
    if not qcols:
        return {}
    in_n = (comp[qcols] > 0).sum(axis=1)
    return {
        "zero_all": int((comp["Total Qty"] == 0).sum()),
        "single_company": int(((in_n == 1)).sum()),
        "all_companies": int((in_n == len(qcols)).sum()),
    }

def compute_missing_analysis(df, active_systems):
    if df.empty or not active_systems:
        return pd.DataFrame()
    qty_cols = {s: f"{s} Qty" for s in active_systems if f"{s} Qty" in df.columns}
    swag_col = qty_cols.get("SWAG")
    if not qty_cols or not swag_col:
        return pd.DataFrame()
    has = df[swag_col] > 0
    has_year = "Year" in df.columns
    base = ["Model Code", "Product"] + (["Year"] if has_year else [])
    out = []
    for sys, col in qty_cols.items():
        if sys == "SWAG":
            continue
        f = df[has & (df[col] == 0)][base + [swag_col]].copy()
        if not f.empty:
            f["Missing In"] = get_system_name(sys)
            f.rename(columns={swag_col: "SWAG Qty"}, inplace=True)
            out.append(f[base + ["SWAG Qty", "Missing In"]])
    if not out:
        return pd.DataFrame()
    return pd.concat(out, ignore_index=True).sort_values("SWAG Qty", ascending=False).reset_index(drop=True)

def compute_price_alerts(df, active_systems):
    if df.empty:
        return pd.DataFrame()
    price_cols = {s: f"{s} Price" for s in active_systems if f"{s} Price" in df.columns}
    if len(price_cols) < 2:
        return pd.DataFrame()
    alerts = []
    for _, row in df.iterrows():
        prices = {s: float(row[c]) for s, c in price_cols.items() if float(row[c]) > 0}
        if len(prices) < 2:
            continue
        mn, mx = min(prices.values()), max(prices.values())
        if mn == 0:
            continue
        diff = ((mx - mn) / mn) * 100
        if diff >= PRICE_DIFF_THRESHOLD_PCT:
            alerts.append({"Model Code": row.get("Model Code", ""), "Product": row.get("Product", ""),
                           "Min Price": round(mn, 2), "Max Price": round(mx, 2), "Diff %": round(diff, 1),
                           "Cheapest In": get_system_name(min(prices, key=prices.get)),
                           "Highest In": get_system_name(max(prices, key=prices.get))})
    if not alerts:
        return pd.DataFrame()
    return pd.DataFrame(alerts).sort_values("Diff %", ascending=False).reset_index(drop=True)

def compute_stock_value(df, active_systems):
    out = {}
    for s in active_systems:
        q, p = f"{s} Qty", f"{s} Price"
        if q in df.columns and p in df.columns:
            out[get_system_name(s)] = float((df[q] * df[p]).sum())
    return out

def only_differences(df, active_systems):
    qcols = [f"{s} Qty" for s in active_systems if f"{s} Qty" in df.columns]
    if len(qcols) < 2:
        return df
    vals = df[qcols]
    mask = vals.max(axis=1) != vals.min(axis=1)
    return df[mask].reset_index(drop=True)

def compute_rebalancing(df, active_systems, min_surplus=2):
    qty_cols = {s: f"{s} Qty" for s in active_systems if f"{s} Qty" in df.columns}
    if len(qty_cols) < 2:
        return pd.DataFrame()
    out = []
    for _, row in df.iterrows():
        stocks = {s: int(row[c]) for s, c in qty_cols.items()}
        donors = {s: q for s, q in stocks.items() if q >= min_surplus}
        empties = [s for s, q in stocks.items() if q == 0]
        if not donors or not empties:
            continue
        src = max(donors, key=donors.get)
        src_qty = donors[src]
        move_each = max(1, src_qty // (len(empties) + 1))
        for dst in empties:
            out.append({
                "Model Code": row.get("Model Code", ""),
                "Product": row.get("Product", ""),
                "From (has stock)": get_system_name(src),
                "From Qty": src_qty,
                "To (0 stock)": get_system_name(dst),
                "Suggested Move": move_each,
            })
    if not out:
        return pd.DataFrame()
    return pd.DataFrame(out).sort_values("From Qty", ascending=False).reset_index(drop=True)

def zero_stock_models(df):
    if df.empty or "Total Qty" not in df.columns:
        return pd.DataFrame()
    z = df[df["Total Qty"] == 0]
    cols = [c for c in ["Model Code", "Product", "Year", "Season"] if c in z.columns]
    return z[cols].reset_index(drop=True)

def build_season_text_summary(comp, long_df, season_name, active_systems):
    lines = []
    lines.append(f"SWAG Season Report - {season_name}")
    lines.append(datetime.now().strftime("%Y-%m-%d %H:%M"))
    lines.append("")
    total_models = len(comp)
    total_units = int(comp["Total Qty"].sum()) if "Total Qty" in comp.columns else 0
    lines.append(f"Models: {total_models:,}")
    lines.append(f"Total units: {total_units:,}")
    n_branches = long_df["Branch"].nunique() if not long_df.empty else 0
    lines.append(f"Branches: {n_branches}")
    lines.append("")
    lines.append("Units by company:")
    for s in active_systems:
        col = f"{s} Qty"
        if col in comp.columns:
            lines.append(f"  - {get_system_name(s)}: {int(comp[col].sum()):,}")
    sv = compute_stock_value(comp, active_systems)
    if sv:
        lines.append("")
        lines.append("Stock value (SAR):")
        for nm, val in sv.items():
            lines.append(f"  - {nm}: {val:,.0f}")
    hs = stock_health(comp, active_systems)
    if hs:
        lines.append("")
        lines.append(f"Zero-stock models: {hs['zero_all']:,}")
        lines.append(f"Single-company only: {hs['single_company']:,}")
        lines.append(f"In all companies: {hs['all_companies']:,}")
    lines.append("")
    lines.append("- SWAG Season Dashboard")
    return "\n".join(lines)

def build_unified_season_list(all_systems_info):
    labels = set()
    for sys, info in all_systems_info.items():
        if info.get("name_fallback"):
            continue
        for val, lbl in info.get("seasons", []):
            if str(lbl).strip():
                labels.add(str(lbl).strip())

    def sk(lbl):
        st_ = season_type_only(lbl) or "ZZZ"
        yr = season_year(lbl)
        return (st_, -(int(yr) if yr else 0), lbl)
    return sorted(labels, key=sk)

def build_available_types(all_systems_info):
    found = set()
    for sys, info in all_systems_info.items():
        for val, lbl in info.get("seasons", []):
            tt = season_type_only(lbl)
            if tt:
                found.add(tt)
    return [t for t in ["SUMMER", "WINTER", "SPRING", "FALL"] if t in found]

def to_excel_generic_season(df, season_name, sheet="Sheet1"):
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet[:31])
        ws = writer.sheets[sheet[:31]]
        hdr_fill = PatternFill("solid", fgColor="060D0E")
        hdr_font = Font(bold=True, color="4AACB4", size=11, name="Calibri")
        h_align = Alignment(horizontal="center", vertical="center")
        thin = Side(border_style="thin", color="1A2A2C")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        alt_fill = PatternFill("solid", fgColor="0D1A1C")
        norm_font = Font(name="Calibri", size=10, color="8AACB0")
        num_align = Alignment(horizontal="right", vertical="center")
        txt_align = Alignment(horizontal="center", vertical="center")
        tot_fill = PatternFill("solid", fgColor="060D0E")
        tot_font = Font(bold=True, name="Calibri", color="D4A84B")
        mr, mc = ws.max_row, ws.max_column
        ws.row_dimensions[1].height = 26
        for c in range(1, mc + 1):
            cell = ws.cell(row=1, column=c)
            cell.fill = hdr_fill; cell.font = hdr_font; cell.alignment = h_align; cell.border = border
        if mr <= 4000:
            for row in ws.iter_rows(min_row=2, max_row=mr):
                for cell in row:
                    cell.border = border; cell.font = norm_font
                    if cell.row % 2 == 0:
                        cell.fill = alt_fill
                    cell.alignment = num_align if isinstance(cell.value, (int, float)) else txt_align
        for c in range(1, mc + 1):
            cl = get_column_letter(c)
            ml = max((len(str(ws.cell(row=r, column=c).value or "")) for r in range(1, min(mr, 201) + 1)), default=8)
            ws.column_dimensions[cl].width = min(max(ml + 3, 12), 45)
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(mc)}{mr}"
        tr = mr + 1
        tc = ws.cell(row=tr, column=1, value="TOTAL"); tc.font = tot_font; tc.fill = tot_fill; tc.alignment = h_align
        for ci, cn in enumerate(df.columns, start=1):
            if "Qty" in str(cn) or "Total" in str(cn) or " | " in str(cn) or "Price" in str(cn):
                cl = get_column_letter(ci)
                c2 = ws.cell(row=tr, column=ci, value=f"=SUM({cl}2:{cl}{mr})")
                c2.font = tot_font; c2.fill = tot_fill; c2.alignment = num_align
        ws.sheet_properties.tabColor = "4AACB4"
    return buf.getvalue()

def to_excel_workbook_season(sheets, season_name):
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for sheet, df in sheets:
            if df is None or df.empty:
                continue
            df.to_excel(writer, index=False, sheet_name=sheet[:31])
            ws = writer.sheets[sheet[:31]]
            hdr_fill = PatternFill("solid", fgColor="060D0E")
            hdr_font = Font(bold=True, color="4AACB4", size=11, name="Calibri")
            h_align = Alignment(horizontal="center", vertical="center")
            thin = Side(border_style="thin", color="1A2A2C")
            border = Border(left=thin, right=thin, top=thin, bottom=thin)
            alt_fill = PatternFill("solid", fgColor="0D1A1C")
            norm_font = Font(name="Calibri", size=10, color="8AACB0")
            num_align = Alignment(horizontal="right", vertical="center")
            txt_align = Alignment(horizontal="center", vertical="center")
            tot_fill = PatternFill("solid", fgColor="060D0E")
            tot_font = Font(bold=True, name="Calibri", color="D4A84B")
            mr, mc = ws.max_row, ws.max_column
            ws.row_dimensions[1].height = 26
            for c in range(1, mc + 1):
                cell = ws.cell(row=1, column=c)
                cell.fill = hdr_fill; cell.font = hdr_font; cell.alignment = h_align; cell.border = border
            if mr <= 4000:
                for row in ws.iter_rows(min_row=2, max_row=mr):
                    for cell in row:
                        cell.border = border; cell.font = norm_font
                        if cell.row % 2 == 0:
                            cell.fill = alt_fill
                        cell.alignment = num_align if isinstance(cell.value, (int, float)) else txt_align
            for c in range(1, mc + 1):
                cl = get_column_letter(c)
                ml = max((len(str(ws.cell(row=r, column=c).value or "")) for r in range(1, min(mr, 201) + 1)), default=8)
                ws.column_dimensions[cl].width = min(max(ml + 3, 12), 45)
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = f"A1:{get_column_letter(mc)}{mr}"
            tr = mr + 1
            tc = ws.cell(row=tr, column=1, value="TOTAL"); tc.font = tot_font; tc.fill = tot_fill; tc.alignment = h_align
            for ci, cn in enumerate(df.columns, start=1):
                if "Qty" in str(cn) or "Total" in str(cn) or " | " in str(cn):
                    cl = get_column_letter(ci)
                    c2 = ws.cell(row=tr, column=ci, value=f"=SUM({cl}2:{cl}{mr})")
                    c2.font = tot_font; c2.fill = tot_fill; c2.alignment = num_align
            ws.sheet_properties.tabColor = "4AACB4"
    return buf.getvalue()

def _register_manual_system(sys, candidate):
    seasons = fetch_distinct_seasons_from_field(
        sys, candidate["model"], candidate["field_name"],
        candidate["field_type"], candidate["relation_model"])
    if seasons:
        info = st.session_state.get("all_systems_info", {})
        info[sys] = {"model": candidate["model"], "field": candidate["field_name"],
                     "ftype": candidate["field_type"], "relation": candidate["relation_model"],
                     "seasons": seasons}
        st.session_state["all_systems_info"] = info
        st.session_state["unified_seasons"] = build_unified_season_list(info)
        st.session_state["available_types"] = build_available_types(info)
        return len(seasons)
    return 0

def render_audit_report(audits):
    st.markdown("<div class='section-tag'>Deep Season Field Audit Report</div>", unsafe_allow_html=True)
    for sys in SYSTEM_KEYS:
        audit = audits.get(sys)
        if not audit:
            st.markdown(f"**{get_system_name(sys)}** — not audited"); continue
        found = audit.get("confident", False)
        manual = audit.get("manual_pick_needed", False)
        icon = "✅" if found else ("⚠️" if manual else "❌")
        label = "Field Found" if found else ("Manual Pick Needed" if manual else "No Field Identified")
        with st.expander(f"{get_system_name(sys)}  —  {icon} {label}", expanded=not found):
            st.markdown(
                f"**Status:** `{audit['status']}` | Raw: **{audit.get('raw_field_count','?')}** | "
                f"Eligible: **{audit.get('eligible_field_count','?')}** | "
                f"Records: **{audit.get('product_records_loaded','?')}**")
            if audit.get("error"):
                st.warning(audit["error"])
            if audit.get("best_field"):
                best = audit["best_field"]
                st.success(f"Best: `{best['model']}.{best['field_name']}` | "
                           f"type: {best['field_type']} | label: **{best['field_label']}** | "
                           f"score: {round(best['total_score'],1)}")
            candidates = audit.get("candidates", [])
            pickable = [c for c in candidates if c["total_score"] > -49
                        and not (c.get("rejection_reason") or "").startswith("Blacklisted")]
            if pickable and not found:
                st.markdown("**🔧 Manual field override**")
                opts = {f"{c['model']}.{c['field_name']} [{c['field_label']}] (score {round(c['total_score'],1)})": c
                        for c in pickable[:20]}
                chosen = opts[st.selectbox("Choose the season field", list(opts.keys()), key=f"manual_{sys}")]
                if st.button(f"✓ Use this for {get_system_name(sys)}", key=f"use_{sys}"):
                    n = _register_manual_system(sys, chosen)
                    if n:
                        st.success(f"Set! Found {n} seasons."); st.rerun()
                    else:
                        st.error("No season values found.")
            if candidates:
                rows = [{"Field": c["field_name"], "Label": c["field_label"], "Type": c["field_type"],
                         "Relation": c["relation_model"] or "", "Non-Empty": c["non_empty_count"],
                         "Season-Like": c["season_like_direct_count"], "Total": round(c["total_score"], 1),
                         "Samples": "; ".join(str(v) for v in c["sample_raw_values"][:3]),
                         "Note": c["rejection_reason"] or "—"} for c in candidates[:40]]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, height=360)

# =============================================================================
# MAIN DASHBOARD (with integrated season tab)
# =============================================================================
def show_dashboard():

    # ── SIDEBAR ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"""
        <div style='padding:24px 0 20px;border-bottom:1px solid rgba(74,172,180,0.08);margin-bottom:20px;'>
          <div style='display:flex;align-items:center;gap:10px;'>
            <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
              <path d="M16 2 L28 16 L16 30 L4 16 Z" stroke="#4AACB4" stroke-width="1" fill="rgba(74,172,180,0.04)"/>
              <path d="M16 9 L23 16 L16 23 L9 16 Z" fill="#4AACB4" opacity="0.3"/>
              <circle cx="16" cy="2"  r="1.5" fill="#D4A84B"/>
              <circle cx="28" cy="16" r="1.5" fill="#D4A84B"/>
              <circle cx="16" cy="30" r="1.5" fill="#D4A84B"/>
              <circle cx="4"  cy="16" r="1.5" fill="#D4A84B"/>
            </svg>
            <div>
              <div style='font-family:Outfit,sans-serif;font-size:13px;font-weight:600;
                          color:#fff;letter-spacing:2px;text-transform:uppercase;'>SWAG</div>
              <div style='font-family:Outfit,sans-serif;font-size:7px;
                          letter-spacing:3px;color:#4AACB4;text-transform:uppercase;'>Dashboard</div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

        lc2 = st.radio(t("Language","اللغة"),["EN","AR"],
                       index=0 if get_lang()=="EN" else 1, horizontal=True)
        if lc2!=get_lang(): st.session_state.lang=lc2; st.rerun()

        st.markdown(f"""
        <div style='margin:16px 0 8px;font-family:Outfit,sans-serif;font-size:7px;
                    letter-spacing:3px;text-transform:uppercase;color:rgba(255,255,255,0.2);'>
          {st.session_state.user_email}
        </div>""", unsafe_allow_html=True)
        if st.button(t("Logout →","خروج →"), use_container_width=True, type="secondary"):
            do_logout()

        st.divider()
        st.markdown(f"<div class='section-tag'>{t('Search Mode','وضع البحث')}</div>",
                    unsafe_allow_html=True)
        et = st.toggle(t("Exact match","تطابق تام"), value=st.session_state.search_exact)
        if et!=st.session_state.search_exact:
            st.session_state.search_exact=et
            st.session_state.total_df=None
            st.session_state.branch_df=None
            st.session_state.transfers_df=None
            st.rerun()

        st.divider()
        st.markdown(f"<div class='section-tag'>{t('Low Stock Alert','تنبيه المخزون')}</div>",
                    unsafe_allow_html=True)
        thr = st.number_input(t("Threshold (qty ≤)","الحد (كمية ≤)"),
                              min_value=0, max_value=1000,
                              value=st.session_state.low_stock_thresh, step=1)
        if thr!=st.session_state.low_stock_thresh:
            st.session_state.low_stock_thresh = int(thr)

        st.divider()
        if st.session_state.last_run:
            st.markdown(f"<div class='section-tag'>{t('Last Run','آخر تشغيل')}</div>",
                        unsafe_allow_html=True)
            st.caption(st.session_state.last_run.get("time",""))

    # ── TODAY SNAPSHOT — shown before any search ─────────────────────────────
    _snap      = st.session_state.last_run
    _stats     = st.session_state.sys_stats
    _tdf_cache = st.session_state.total_df

    _email     = st.session_state.user_email or ""
    _firstname = _email.split("@")[0].split(".")[0].capitalize()

    _hour = datetime.now().hour
    if _hour < 12:   _greet = t("Good morning","صباح الخير")
    elif _hour < 17: _greet = t("Good afternoon","مساء الخير")
    else:            _greet = t("Good evening","مساء الخير")

    # System pills
    _sys_pills = ""
    for _k in SYSTEM_KEYS:
        _cfg_ok = bool(get_system_config(_k))
        _stat   = _stats.get(_k,"UNKNOWN") if _snap else ("CONFIGURED" if _cfg_ok else "NO_CONFIG")
        _dname  = get_system_name(_k)
        if not _cfg_ok:           _cls="offline"; _lbl=t("No Config","لا إعداد")
        elif _stat=="OK":         _cls="online";  _lbl=t("Online","متصل")
        elif _stat=="NOT_FOUND":  _cls="nodata";  _lbl=t("No Data","لا بيانات")
        elif _stat=="ERROR":      _cls="error";   _lbl=t("Error","خطأ")
        else:                     _cls="offline"; _lbl="—"
        _sys_pills += (
            f"<div class='sp sp-{_cls}'>"
            f"<div class='sd sd-{_cls}'></div>"
            f"<span class='sn sn-{_cls}'>{_dname}</span>"
            f"<span class='sb sb-{_cls}'>{_lbl}</span>"
            f"</div>")

    # Portfolio value + low stock count
    _port_val  = ""; _low_count = 0
    if _tdf_cache is not None and not _tdf_cache.empty:
        _qcx = t("On Hand","متوفر"); _pcx = t("Sale Price","سعر البيع")
        _okx = _tdf_cache[_tdf_cache["_status"]=="OK"] if "_status" in _tdf_cache.columns else _tdf_cache
        if _qcx in _okx.columns and _pcx in _okx.columns:
            _qv = pd.to_numeric(_okx[_qcx],errors="coerce").fillna(0)
            _pv = pd.to_numeric(_okx[_pcx],errors="coerce").fillna(0)
            _tv = (_qv*_pv).sum()
            _port_val  = f"{_tv/1000:,.0f}K SAR" if _tv>=1000 else f"{_tv:,.0f} SAR"
            _thr_x = st.session_state.low_stock_thresh
            if _thr_x>0: _low_count=int(((_qv>0)&(_qv<=_thr_x)).sum())

    # Last run info
    _last_html = ""
    _online_count = sum(1 for _k in SYSTEM_KEYS if _stats.get(_k)=="OK") if _snap else 0

    if _snap:
        _ago_s  = (datetime.now()-datetime.strptime(_snap["time"],"%Y-%m-%d %H:%M:%S")).total_seconds()
        _ago_str = (f"{int(_ago_s//3600)}h ago" if _ago_s>=3600
                    else f"{int(_ago_s//60)}m ago" if _ago_s>=60 else "just now")
        _last_html = (
            "<div class='snap-last'>"
            f"<div class='sl-label'>{t('Last Run','آخر تشغيل')}</div>"
            f"<div class='sl-val'>{_snap.get('models','—')} {t('model(s)','موديل')}</div>"
            f"<div class='sl-meta'>{_snap['time']}</div>"
            f"<div class='sl-ago'>{_ago_str}</div>"
            + (f"<div class='sl-rows'>→ {_snap.get('rows','?')} rows</div>" if _snap.get('rows') else "")
            + "</div>")

    _online_cls = "teal" if _online_count==len(SYSTEM_KEYS) else ("gold" if _online_count>0 else "red-v")

    # ── Part 1: CSS + greeting + KPI cards ──────────────────────────────────
    _port_card  = (
        "<div class='snap-card' style='animation-delay:.08s;"
        "border-color:rgba(212,168,75,.12)'>"
        f"<div class='sc-label'>{t('Portfolio','المحفظة')}</div>"
        f"<div class='sc-val gold'>{_port_val}</div>"
        f"<div class='sc-sub'>{t('last search','آخر بحث')}</div></div>"
    ) if _port_val else ""

    _low_card = (
        "<div class='snap-card' style='animation-delay:.12s;"
        "border-color:rgba(255,100,80,.1)'>"
        f"<div class='sc-label'>{t('Low Stock','مخزون منخفض')}</div>"
        f"<div class='sc-val red-v'>{_low_count}</div>"
        f"<div class='sc-sub'>{t('items','صنف')}</div></div>"
    ) if _low_count > 0 else ""

    _run_card = (
        "<div class='snap-card' style='animation-delay:.16s'>"
        f"<div class='sc-label'>{t('Last Run','آخر تشغيل')}</div>"
        f"<div class='sc-val' style='font-size:20px'>{_snap.get('rows','—')}</div>"
        f"<div class='sc-sub'>{t('rows','صفوف')}</div></div>"
    ) if _snap else ""

    _sub_online = ("All connected" if _online_count==len(SYSTEM_KEYS)
                   else f"{len(SYSTEM_KEYS)-_online_count} offline")
    _warn_html  = (
        f"<div class='snap-warn'>&#9888; {_low_count} "
        f"{t('items below low stock threshold','صنف تحت حد المخزون المنخفض')}</div>"
    ) if _low_count > 0 else ""

    st.markdown(f"""
    <style>
    @keyframes snapIn{{from{{opacity:0;transform:translateY(-14px)}}to{{opacity:1;transform:translateY(0)}}}}
    @keyframes cardIn{{from{{opacity:0;transform:translateX(-6px)}}to{{opacity:1;transform:translateX(0)}}}}
    @keyframes dotBlink{{0%,100%{{opacity:1}}50%{{opacity:0.25}}}}
    .snap-wrap{{padding:32px 0 20px;animation:snapIn .5s cubic-bezier(.22,.68,0,1.2) both}}
    .snap-greeting{{font-family:'Cormorant Garamond',serif;font-size:40px;font-weight:300;
      color:#fff;margin-bottom:4px;line-height:1.15}}
    .snap-greeting em{{font-style:normal;color:#4AACB4}}
    .snap-date{{font-family:'Outfit',sans-serif;font-size:9px;letter-spacing:4px;
      text-transform:uppercase;color:rgba(255,255,255,0.18);margin-bottom:24px}}
    .snap-cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));
      gap:10px;margin-bottom:22px}}
    .snap-card{{background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05);
      border-radius:12px;padding:16px 14px;animation:cardIn .5s ease both;
      transition:border-color .2s,background .2s}}
    .snap-card:hover{{border-color:rgba(74,172,180,0.2);background:rgba(74,172,180,0.03)}}
    .sc-label{{font-family:'Outfit',sans-serif;font-size:8px;letter-spacing:3px;
      text-transform:uppercase;color:rgba(255,255,255,0.18);margin-bottom:10px}}
    .sc-val{{font-family:'Cormorant Garamond',serif;font-size:32px;font-weight:300;
      color:#fff;line-height:1;margin-bottom:3px}}
    .sc-val.teal{{color:#4AACB4}}.sc-val.gold{{color:#D4A84B}}
    .sc-val.red-v{{color:rgba(255,100,80,.85)}}
    .sc-sub{{font-family:'Outfit',sans-serif;font-size:9px;
      color:rgba(255,255,255,0.18);letter-spacing:.5px}}
    .snap-sys-label{{font-family:'Outfit',sans-serif;font-size:8px;letter-spacing:3px;
      text-transform:uppercase;color:rgba(255,255,255,0.14);margin-bottom:10px}}
    .snap-sys-row{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}}
    .sp{{display:flex;align-items:center;gap:7px;border-radius:100px;padding:6px 14px}}
    .sp-online{{background:rgba(74,172,180,0.07);border:1px solid rgba(74,172,180,0.18)}}
    .sp-offline{{background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.05)}}
    .sp-error{{background:rgba(255,100,80,0.05);border:1px solid rgba(255,100,80,0.14)}}
    .sp-nodata{{background:rgba(212,168,75,0.05);border:1px solid rgba(212,168,75,0.14)}}
    .sd{{width:7px;height:7px;border-radius:50%;flex-shrink:0}}
    .sd-online{{background:#4AACB4;animation:dotBlink 2.5s ease-in-out infinite}}
    .sd-offline{{background:rgba(255,255,255,0.14)}}
    .sd-error{{background:rgba(255,100,80,.75)}}
    .sd-nodata{{background:#D4A84B}}
    .sn{{font-family:'Outfit',sans-serif;font-size:11px;font-weight:500;letter-spacing:.5px}}
    .sn-online{{color:rgba(74,172,180,.85)}}.sn-offline{{color:rgba(255,255,255,.22)}}
    .sn-error{{color:rgba(255,100,80,.7)}}.sn-nodata{{color:rgba(212,168,75,.7)}}
    .sb{{font-family:'Outfit',sans-serif;font-size:7px;letter-spacing:1.5px;
      text-transform:uppercase;padding:2px 6px;border-radius:100px}}
    .sb-online{{background:rgba(74,172,180,.1);color:rgba(74,172,180,.55)}}
    .sb-offline{{background:rgba(255,255,255,.03);color:rgba(255,255,255,.14)}}
    .sb-error{{background:rgba(255,100,80,.09);color:rgba(255,100,80,.55)}}
    .sb-nodata{{background:rgba(212,168,75,.09);color:rgba(212,168,75,.55)}}
    .snap-last{{display:flex;align-items:center;gap:14px;flex-wrap:wrap;
      background:rgba(74,172,180,0.04);border:1px solid rgba(74,172,180,0.09);
      border-left:3px solid rgba(74,172,180,0.35);
      border-radius:0 10px 10px 0;padding:12px 18px;margin-top:12px}}
    .sl-label{{font-family:'Outfit',sans-serif;font-size:8px;letter-spacing:3px;
      text-transform:uppercase;color:rgba(74,172,180,.5);flex-shrink:0}}
    .sl-val{{font-family:'Cormorant Garamond',serif;font-size:18px;
      font-weight:300;color:#fff;letter-spacing:1px}}
    .sl-meta{{font-family:'Outfit',sans-serif;font-size:10px;color:rgba(255,255,255,.22)}}
    .sl-ago{{font-family:'Outfit',sans-serif;font-size:10px;color:rgba(255,255,255,.28)}}
    .sl-rows{{font-family:'Outfit',sans-serif;font-size:11px;color:#4AACB4;font-weight:500}}
    .snap-warn{{display:inline-flex;align-items:center;gap:8px;
      background:rgba(212,168,75,.06);border:1px solid rgba(212,168,75,.18);
      border-radius:8px;padding:8px 14px;margin-top:8px;
      font-family:'Outfit',sans-serif;font-size:10px;
      letter-spacing:1px;color:rgba(212,168,75,.8)}}
    .snap-divider{{height:1px;margin:28px 0 20px;
      background:linear-gradient(90deg,rgba(74,172,180,.25),rgba(74,172,180,.06),transparent)}}
    </style>

    <div class='snap-wrap'>
      <div class='snap-greeting'>{_greet}, <em>{_firstname}</em></div>
      <div class='snap-date'>{datetime.now().strftime("%A, %d %B %Y")} &nbsp;·&nbsp; SWAG Product Intelligence</div>
      <div class='snap-cards'>
        <div class='snap-card' style='animation-delay:.04s'>
          <div class='sc-label'>{t("Systems Online","الأنظمة المتصلة")}</div>
          <div class='sc-val {_online_cls}'>{_online_count}/{len(SYSTEM_KEYS)}</div>
          <div class='sc-sub'>{_sub_online}</div>
        </div>
        {_port_card}{_low_card}{_run_card}
      </div>
      <div class='snap-sys-label'>{t("Connected Systems","الأنظمة المتصلة")}</div>
    """, unsafe_allow_html=True)

    # ── Part 2: sys_pills rendered separately ──
    st.markdown(
        "<div class='snap-sys-row'>" + _sys_pills + "</div>",
        unsafe_allow_html=True)

    # ── Part 3: warn + last run + divider ────────────────────────────────────
    st.markdown(
        _warn_html + _last_html +
        "</div><div class='snap-divider'></div>",
        unsafe_allow_html=True)

    # ── HERO ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="hero-section">
      <div class="hero-glow"></div>
      <div class="hero-gold-glow"></div>
      <svg class="hero-geo-bg" width="480" height="480" viewBox="0 0 480 480" fill="none">
        <rect x="40"  y="40"  width="400" height="400" stroke="#4AACB4" stroke-width="0.8" transform="rotate(45 240 240)"/>
        <rect x="90"  y="90"  width="300" height="300" stroke="#4AACB4" stroke-width="0.5" transform="rotate(45 240 240)"/>
        <rect x="140" y="140" width="200" height="200" stroke="#D4A84B" stroke-width="0.4" transform="rotate(45 240 240)"/>
        <rect x="190" y="190" width="100" height="100" stroke="#4AACB4" stroke-width="0.3" transform="rotate(45 240 240)"/>
      </svg>
      <div class="hero-inner" style="padding:0 2rem;">
        <div class="eyebrow">Real-time · 5 Odoo Systems · Live Data</div>
        <div class="hero-title">مقارنة <em>المنتجات</em> والمخزون</div>
        <div class="hero-subtitle">Product Comparison Dashboard</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='padding:0 2rem;'>", unsafe_allow_html=True)

    # ── PDF UPLOAD ────────────────────────────────────────────────────────────
    st.markdown(f"<div class='section-tag' style='margin-top:32px;'>{t('Upload Invoice PDF','رفع فاتورة PDF')}</div>",
                unsafe_allow_html=True)
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
            with st.spinner(t("Parsing PDF...","جاري قراءة الفاتورة...")):
                st.session_state[ck] = parse_invoice_pdf_cached(fbytes)
        raw = st.session_state[ck]
        if raw:
            is_main = emode is None or "Main" in emode or "رئيسية" in emode
            unique  = get_unique_base_models(raw) if is_main else list(
                dict.fromkeys([item["code"] for item in raw]))
            if isinstance(unique[0], dict):
                unique_sorted = sorted(unique, key=lambda x: x["sequence"])
                unique_codes  = [item["code"] for item in unique_sorted]
            else:
                unique_codes  = unique
                unique_sorted = [{"sequence":i+1,"code":c} for i,c in enumerate(unique_codes)]
            c1,c2 = st.columns(2)
            c1.metric(t("Raw codes","رموز مستخرجة"), len(raw))
            c2.metric(t("Unique models","موديلات فريدة"), len(unique_codes))
            with st.expander(t(f"{len(unique_codes)} codes found","الرموز المستخرجة"), expanded=False):
                st.code("\n".join(f"{item['sequence']:>3}. {item['code']}"
                                  for item in unique_sorted))
            ca,cb = st.columns(2)
            with ca:
                if st.button(t("Total Stock","مخزون إجمالي"),
                             type="primary", use_container_width=True, key="pt"):
                    st.session_state.pdf_codes = unique_codes
                    st.session_state.pdf_mode  = "total"; st.rerun()
            with cb:
                if st.button(t("Branch-wise","حسب الفرع"),
                             type="secondary", use_container_width=True, key="pb"):
                    st.session_state.pdf_codes = unique_codes
                    st.session_state.pdf_mode  = "branch"; st.rerun()
        else:
            st.warning(t("No codes found in PDF.","لم يتم العثور على رموز."))

    st.divider()

    # ── MANUAL SEARCH ─────────────────────────────────────────────────────────
    st.markdown(f"<div class='section-tag'>{t('Manual Search','بحث يدوي')}</div>",
                unsafe_allow_html=True)
    L,R = st.columns([1.5,1])
    with L:
        if not st.session_state.search_exact:
            st.markdown(f"<div class='info-banner'>{t('Variant mode — XP6013 finds all sizes','وضع المتغيرات — XP6013 يجد جميع المقاسات')}</div>",
                        unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='warn-banner'>{t('Exact match — identical codes only','تطابق تام — رموز مطابقة فقط')}</div>",
                        unsafe_allow_html=True)
        ms   = t("Single Model","موديل واحد")
        mm   = t("Multiple Models","موديلات متعددة")
        mode = st.radio(t("Mode","الوضع"),[ms,mm], horizontal=True,
                        label_visibility="collapsed")
        if mode==mm:
            rt    = st.text_area(t("Codes","الرموز"), height=120, placeholder="ABC123\nDEF456")
            codes = [c.strip() for c in rt.replace(",","\n").splitlines() if c.strip()]
        else:
            sg    = st.text_input(t("Model Code","رمز الموديل"), placeholder="e.g. XP6013")
            codes = [sg.strip()] if sg.strip() else []

        t1,t2,t3,t4 = st.columns(4)   # removed one column for zero-stock? original had 5, we keep 4: zero, branch, sort, transfers, but reorder remains.
        sz  = t1.toggle(t("Zero","الصفري"),     value=False)
        sb  = t2.toggle(t("Branch","فروع"),      value=False)
        ss  = t3.toggle(t("Sort","ترتيب"),       value=False)
        st_ = t4.toggle(t("Transfers","نقليات"), value=False)
        sr  = st.checkbox(t("Reorder","طلب"), value=st.session_state.show_reorder)
        if sr:
            with st.expander(t("Reorder Settings","إعدادات إعادة الطلب"), expanded=True):
                rx,ry = st.columns(2)
                with rx:
                    st.session_state.reorder_target_days = st.slider(
                        t("Target days cover","أيام التغطية"), 7, 180,
                        st.session_state.reorder_target_days)
                with ry:
                    st.session_state.reorder_point = st.number_input(
                        t("Reorder point","نقطة الطلب"), min_value=0, max_value=9999,
                        value=st.session_state.reorder_point, step=1)

        cbtn = st.button(t("Compare →","مقارنة →"), use_container_width=True, type="primary")

    with R:
        st.markdown(f"<div class='section-tag'>{t('Last Run','آخر تشغيل')}</div>",
                    unsafe_allow_html=True)
        snap  = st.session_state.last_run
        stats = st.session_state.sys_stats
        if not snap:
            st.markdown(f"<div class='info-banner'>{t('Run a comparison first.','قم بتشغيل مقارنة أولاً.')}</div>",
                        unsafe_allow_html=True)
        else:
            on = sum(1 for v in stats.values() if v=="OK")
            st.markdown(
                f"<div class='snap-card'>"
                f"<b>{t('Time','الوقت')}</b> &nbsp;{snap.get('time','—')}<br>"
                f"<b>{t('Models','الموديلات')}</b> &nbsp;{snap.get('models','—')}<br>"
                f"<b>{t('Online','متصل')}</b> &nbsp;{on}/{len(SYSTEM_KEYS)}<br>"
                f"<b>{t('Rows','الصفوف')}</b> &nbsp;{snap.get('rows','—')}"
                f"</div>", unsafe_allow_html=True)
            st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
            for key in SYSTEM_KEYS:
                s  = stats.get(key,"—")
                bc = "badge-ok" if s=="OK" else "badge-off" if s=="NOT_FOUND" else "badge-err"
                bt = "Online" if s=="OK" else "Offline" if s=="NOT_FOUND" else "Error"
                dn = get_system_name(key)
                st.markdown(
                    f"<div class='sys-row'>"
                    f"<span style='font-family:Outfit,sans-serif;font-size:11px;"
                    f"letter-spacing:1px;color:rgba(255,255,255,0.5);'>{dn}</span>"
                    f"<span class='{bc}'>{bt}</span></div>",
                    unsafe_allow_html=True)

    # ── TRIGGER RUN ───────────────────────────────────────────────────────────
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
        ct = tuple(run_codes)
        with st.spinner(t("Fetching from 5 systems...","جلب البيانات من 5 أنظمة...")):
            data = fetch_all_data(
                ct, exact=st.session_state.search_exact,
                need_branch=sb or force_branch,
                need_transfers=st_, need_reorder=sr,
                target_days=st.session_state.reorder_target_days,
                reorder_point=st.session_state.reorder_point)

        tdf  = prepare_df(data["total"])
        bdf  = prepare_df(data["branch"])
        trdf = prepare_df(data["transfers"])
        rdf  = prepare_df(data["reorder"])

        raw_tdf = data["total"]
        ns = {k:"NOT_FOUND" for k in SYSTEM_KEYS}
        if "_status" in raw_tdf.columns and "System" in raw_tdf.columns:
            for key in SYSTEM_KEYS:
                dn   = get_system_name(key)
                mask = (raw_tdf["System"] == key) | (raw_tdf["System"] == dn)
                if mask.any():
                    sv = raw_tdf.loc[mask,"_status"]
                    if   "OK"          in sv.values: ns[key]="OK"
                    elif "NOT_FOUND"   in sv.values: ns[key]="NOT_FOUND"
                    elif "ERROR"       in sv.values: ns[key]="ERROR"

        qc2     = t("On Hand","متوفر")
        sc2_loc = t("System","النظام")
        mc_loc  = t("Model Code","رمز الموديل")

        if qc2 in tdf.columns:
            zero_mask = pd.to_numeric(tdf[qc2],errors="coerce").fillna(0) == 0
            tdf.loc[zero_mask,"_status"] = "not_available"

        if ss and sc2_loc in tdf.columns:
            tdf = tdf.sort_values(sc2_loc).reset_index(drop=True)
        if not bdf.empty and ss and sc2_loc in bdf.columns:
            bdf = bdf.sort_values(sc2_loc).reset_index(drop=True)

        # Purchase Qty — fetch for SWAG + STOCK
        _PUR_SYSTEMS = ["SWAG", "STOCK"]
        tdf["Purchase Qty"] = 0

        ed = datetime.now().date(); sd = ed - timedelta(days=365)
        for _pur_key in _PUR_SYSTEMS:
            _pur_name = get_system_name(_pur_key)
            _pur_mask = (tdf[sc2_loc] == _pur_name)
            if not _pur_mask.any():
                continue
            _pur_models = tdf.loc[_pur_mask, mc_loc].dropna().unique().tolist()
            if not _pur_models:
                continue
            with st.spinner(t(
                f"Fetching purchase totals ({_pur_name})...",
                f"جلب إجمالي المشتريات ({_pur_name})...")):
                _pur_df = get_purchase_summary_by_model(
                    tuple(_pur_models),
                    sd.strftime("%Y-%m-%d"),
                    ed.strftime("%Y-%m-%d"),
                    system_key=_pur_key)
            if not _pur_df.empty:
                _pur_df2 = _pur_df.rename(columns={"Model Code": mc_loc})
                _tmp = tdf.merge(_pur_df2[[mc_loc,"Purchase Qty"]]
                                 .rename(columns={"Purchase Qty":"_pur_tmp"}),
                                 on=mc_loc, how="left")
                _fill = _tmp["_pur_tmp"].fillna(0).astype(int)
                tdf.loc[_pur_mask, "Purchase Qty"] = _fill[_pur_mask].values
                tdf = tdf.drop(columns=["_pur_tmp"], errors="ignore")

        pur_col = t("Purchase Qty","كمية المشتريات")
        tdf = tdf.rename(columns={"Purchase Qty":pur_col})
        desired = [sc2_loc,mc_loc,t("Product","المنتج"),
                   t("Sale Price","سعر البيع"),pur_col,qc2]
        existing = tdf.columns.tolist()
        final    = [c for c in desired if c in existing]
        for c in existing:
            if c not in final and not c.startswith("_"):
                final.append(c)
        if "_status" in tdf.columns and "_status" not in final:
            final.append("_status")
        tdf = tdf[final]

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
        st.rerun()

    # ── RESULTS ───────────────────────────────────────────────────────────────
    tdf  = st.session_state.total_df
    bdf  = st.session_state.branch_df
    trdf = st.session_state.transfers_df
    rdf  = st.session_state.reorder_df
    if tdf is None or tdf.empty:
        st.markdown("</div>", unsafe_allow_html=True)
        # Still show season tab even if no product search done?
        # We'll add season tab later after the regular tabs.
        # Actually season tab is part of tabs list, we'll build it after.
    else:
        st.divider()
        thr   = st.session_state.low_stock_thresh
        qc2   = t("On Hand","متوفر"); pc2 = t("Sale Price","سعر البيع")
        sc2   = t("System","النظام"); stats = st.session_state.sys_stats
        ok    = tdf[tdf["_status"]=="OK"] if "_status" in tdf.columns else tdf
        on    = sum(1 for v in stats.values() if v=="OK")

        # Low stock alert
        if thr>0 and qc2 in ok.columns:
            low = ok[(ok[qc2]>0)&(ok[qc2]<=thr)]
            if not low.empty:
                mc2 = t("Model Code","رمز الموديل")
                det = " · ".join(
                    f"{r.get(mc2,'?')} @ {r.get(sc2,'?')} ({r.get(qc2,0)})"
                    for _,r in low.head(6).iterrows())
                if len(low)>6: det += f" +{len(low)-6}"
                st.markdown(
                    f"<div class='alert-banner'>"
                    f"<div class='alert-dot'></div>"
                    f"<div class='alert-txt'>{t('Low Stock','مخزون منخفض')} — {len(low)} items ≤ {thr}</div>"
                    f"<div class='mono'>{det}</div></div>",
                    unsafe_allow_html=True)

        # Metrics — including stock value calculator
        _ok_qty   = pd.to_numeric(ok[qc2], errors="coerce").fillna(0) if qc2 in ok.columns else pd.Series(dtype=float)
        _ok_price = pd.to_numeric(ok[pc2], errors="coerce").fillna(0) if pc2 in ok.columns else pd.Series(dtype=float)

        _stock_value = 0.0
        if qc2 in ok.columns and pc2 in ok.columns:
            _stock_value = (_ok_qty * _ok_price).sum()

        _sys_values = {}
        if qc2 in ok.columns and pc2 in ok.columns and sc2 in ok.columns:
            for _sys in ok[sc2].dropna().unique():
                _mask = ok[sc2] == _sys
                _sv   = (_ok_qty[_mask] * _ok_price[_mask]).sum()
                _sys_values[_sys] = _sv

        m1,m2,m3,m4,m5,m6 = st.columns(6)
        m1.metric(t("Total Rows","إجمالي الصفوف"), len(tdf))
        m2.metric(t("Systems Online","الأنظمة"), f"{on}/{len(SYSTEM_KEYS)}")
        if qc2 in ok.columns:
            m3.metric(t("Total Qty","إجمالي الكمية"),
                      f"{int(_ok_qty.sum()):,}")
        if pc2 in ok.columns:
            vp = _ok_price[_ok_price>0]
            m4.metric(t("Avg Price (SAR)","متوسط السعر ر.س"),
                      f"{vp.mean():,.0f}" if not vp.empty else "—")
        m5.metric(
            t("Stock Value (SAR)","قيمة المخزون ر.س"),
            f"{_stock_value/1000:,.1f}K" if _stock_value >= 1000 else (f"{_stock_value:,.0f}" if _stock_value > 0 else "—"))
        _zero_val = int((_ok_qty == 0).sum()) if not _ok_qty.empty else 0
        m6.metric(t("Zero Stock Items","أصناف بلا مخزون"), _zero_val)

    # ── TABS ───────────────────────────────────────────────────────────────────
    # Build tab labels: Total Stock, Branch Stock, Transfers, Reorder, Dead Stock, Season Comparison
    tlabels = [t("Total Stock","المخزون الإجمالي")]
    if bdf is not None and not bdf.empty:
        tlabels.append(t("Branch Stock","مخزون الفروع"))
    if st.session_state.show_transfers and trdf is not None and not trdf.empty:
        tlabels.append(t("Transfers","النقليات"))
    if st.session_state.show_reorder and rdf is not None and not rdf.empty:
        tlabels.append(t("Reorder","إعادة الطلب"))
    tlabels.append(t("Dead Stock","المخزون الراكد"))
    tlabels.append(t("Season Comparison","مقارنة الموسم"))   # new tab

    tabs = st.tabs(tlabels)
    ti = 0

    # TAB: TOTAL STOCK
    with tabs[ti]:
        ti += 1
        if tdf is not None and not tdf.empty:
            st.markdown(f"<div class='section-tag' style='margin-top:20px;'>{t('Total Stock','المخزون الإجمالي')}</div>",
                        unsafe_allow_html=True)
            _ft = display_df(tdf, thr, table_key="total")
            d1,d2,d3,d4 = st.columns(4)
            d1.download_button("CSV ↓", to_csv(tdf), dl_name("total","csv"),
                               "text/csv", use_container_width=True)
            d2.download_button("Excel ↓", to_excel(tdf), dl_name("total","xlsx"),
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)
            d3.download_button(t("All Systems ↓","كل الأنظمة ↓"), to_excel_bulk(tdf),
                               dl_name("bulk","xlsx"),
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)
            if _ft is not None and not _ft.empty:
                d4.download_button(t("Filtered ↓","مفلتر ↓"), to_excel(_ft),
                                   dl_name("filtered","xlsx"),
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)
        else:
            st.info(t("No data. Run a product comparison first.", "لا بيانات. قم بمقارنة منتجات أولاً."))

    # TAB: BRANCH STOCK
    if len(tlabels) > ti and tlabels[ti] == t("Branch Stock","مخزون الفروع"):
        with tabs[ti]:
            ti += 1
            if bdf is not None and not bdf.empty:
                st.markdown(f"<div class='section-tag' style='margin-top:20px;'>{t('Branch-wise Stock','مخزون حسب الفرع')}</div>",
                            unsafe_allow_html=True)
                _fb = display_df(bdf, thr, table_key="branch")
                b1,b2,b3,b4 = st.columns(4)
                b1.download_button("CSV ↓", to_csv(bdf), dl_name("branch","csv"),
                                   "text/csv", use_container_width=True)
                b2.download_button("Excel ↓", to_excel(bdf), dl_name("branch","xlsx"),
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)
                if _fb is not None and not _fb.empty:
                    b3.download_button(t("Filtered ↓","مفلتر ↓"), to_excel(_fb),
                                       dl_name("filtered_branch","xlsx"),
                                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                       use_container_width=True)
                    b4.download_button(t("Matrix ↓","مصفوفة ↓"),
                                       to_excel_branch_matrix(_fb, get_lang()),
                                       dl_name("matrix","xlsx"),
                                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                       use_container_width=True)
            else:
                st.info(t("No branch data.","لا بيانات فروع."))

    # TAB: TRANSFERS
    if len(tlabels) > ti and tlabels[ti] == t("Transfers","النقليات"):
        with tabs[ti]:
            ti += 1
            if trdf is not None and not trdf.empty:
                st.markdown(f"<div class='section-tag' style='margin-top:20px;'>{t('Pending Transfers','النقليات المعلقة')}</div>",
                            unsafe_allow_html=True)
                display_df(trdf, thresh=0, table_key="transfers")
                x1,x2 = st.columns(2)
                x1.download_button("CSV ↓", to_csv(trdf), dl_name("transfers","csv"),
                                   "text/csv", use_container_width=True)
                x2.download_button("Excel ↓", to_excel(trdf), dl_name("transfers","xlsx"),
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)
            else:
                st.info(t("No transfers.","لا نقليات."))

    # TAB: REORDER
    if len(tlabels) > ti and tlabels[ti] == t("Reorder","إعادة الطلب"):
        with tabs[ti]:
            ti += 1
            if rdf is not None and not rdf.empty:
                st.markdown(f"<div class='section-tag' style='margin-top:20px;'>{t('Reorder Suggestions','اقتراحات إعادة الطلب')}</div>",
                            unsafe_allow_html=True)
                CPRI = t("Priority","الأولوية"); CSUGG = t("Suggest","المقترح")
                okr = rdf[rdf["_status"]=="OK"] if "_status" in rdf.columns else rdf
                if not okr.empty:
                    crit = okr[okr[CPRI].str.contains("Critical",na=False)].shape[0] if CPRI in okr.columns else 0
                    lo   = okr[okr[CPRI].str.contains("Low",na=False)].shape[0]      if CPRI in okr.columns else 0
                    okn  = okr[okr[CPRI].str.contains("OK",na=False)].shape[0]       if CPRI in okr.columns else 0
                    sg   = int(okr[CSUGG].sum()) if CSUGG in okr.columns else 0
                    r1,r2,r3,r4 = st.columns(4)
                    r1.metric(t("Critical","حرج"), crit)
                    r2.metric(t("Low","منخفض"), lo)
                    r3.metric(t("OK","كافٍ"), okn)
                    r4.metric(t("To Order","للطلب"), sg)
                    if crit+lo>0:
                        st.markdown(
                            f"<div class='warn-banner'>{crit+lo} {t('products need reordering','منتجات تحتاج إعادة طلب')}</div>",
                            unsafe_allow_html=True)
                    sa = st.toggle(t("Show all","عرض الكل"), value=False)
                    dr = (okr if sa else
                          okr[okr[CPRI].str.contains("Critical|Low",na=False)] if CPRI in okr.columns else okr)
                    display_df(dr.reset_index(drop=True), table_key="reorder")
                o1,o2 = st.columns(2)
                o1.download_button("CSV ↓", to_csv(rdf), dl_name("reorder","csv"),
                                   "text/csv", use_container_width=True)
                o2.download_button("Excel ↓", to_excel(rdf), dl_name("reorder","xlsx"),
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)
            else:
                st.info(t("No reorder data.","لا بيانات إعادة طلب."))

    # TAB: DEAD STOCK
    if len(tlabels) > ti and tlabels[ti] == t("Dead Stock","المخزون الراكد"):
        with tabs[ti]:
            ti += 1
            st.markdown(
                f"<div class='section-tag' style='margin-top:20px;'>"
                f"{t('Dead Stock Finder','كاشف المخزون الراكد')}</div>",
                unsafe_allow_html=True)

            # System selector
            _ds_sys_options = {get_system_name(k): k for k in SYSTEM_KEYS if get_system_config(k)}
            _ds_sys_labels  = list(_ds_sys_options.keys())
            _ds_sys_sel = st.selectbox(
                t("System","النظام"),
                options=_ds_sys_labels,
                index=0, key="ds_sys_sel")
            _ds_sys_key = _ds_sys_options.get(_ds_sys_sel, "SWAG")

            st.markdown(f"""
            <div class='info-banner'>
              <b>{t("Data Source:","مصدر البيانات:")}</b>
              <b>{_ds_sys_sel}</b> —
              {t(
                "Stock from product.product (qty > 0). Last sale from confirmed orders (sale/done). Dead = no sale in selected days OR never sold.",
                "المخزون من product.product (الكمية > 0). آخر بيع من الأوامر المؤكدة. الراكد = لا بيع خلال الأيام المحددة أو لم يُباع قط."
              )}
            </div>""", unsafe_allow_html=True)

            ds_col1, ds_col2, ds_col3 = st.columns([1, 1, 2])
            with ds_col1:
                ds_days = st.number_input(
                    t("Dead if no sale in (days)", "ميت إذا لم يُباع خلال (يوم)"),
                    min_value=7, max_value=365, value=60, step=1,
                    key="ds_days",
                    help=t(
                        "Item is flagged as dead stock if its last confirmed sale was more than this many days ago, or if it has never been sold.",
                        "يُصنَّف الصنف كمخزون راكد إذا كان آخر بيع مؤكد قبل أكثر من هذا العدد من الأيام، أو إذا لم يُباع قط."
                    ))
            with ds_col2:
                st.markdown("<br>", unsafe_allow_html=True)
                ds_run = st.button(
                    t("Find Dead Stock →", "ابحث عن المخزون الراكد →"),
                    type="primary", use_container_width=True, key="ds_run")
            with ds_col3:
                st.markdown(f"""
                <div style='padding:10px 0;font-family:Outfit,sans-serif;font-size:10px;
                            letter-spacing:1px;color:rgba(255,255,255,0.3);line-height:1.8;'>
                  {t(
                    "⚠️ This query scans ALL in-stock products and their full sale history. May take 30-60 seconds for large catalogs.",
                    "⚠️ هذا الاستعلام يفحص جميع المنتجات في المخزون وتاريخ مبيعاتها الكامل. قد يستغرق 30-60 ثانية."
                  )}
                </div>""", unsafe_allow_html=True)

            if ds_run:
                st.session_state["ds_trigger"] = int(ds_days)
                st.rerun()

            if st.session_state.get("ds_trigger"):
                _ds_days = st.session_state["ds_trigger"]
                _ds_prog_bar  = st.progress(0.0)
                _ds_stat_text = st.empty()
                _ds_stat_text.markdown(
                    f"<div class='info-banner' style='margin:4px 0;'>"
                    f"{t('Starting scan...','بدء الفحص...')}</div>",
                    unsafe_allow_html=True)

                ds_df, _ds_partial = fetch_dead_stock(
                    threshold_days=_ds_days,
                    system_key=_ds_sys_key,
                    _progress=_ds_prog_bar,
                    _status_text=_ds_stat_text)

                _ds_prog_bar.empty()
                _ds_stat_text.empty()

                if _ds_partial:
                    st.markdown(
                        f"<div class='warn-banner'>"
                        f"⚠️ {t('Partial results — some batches timed out or failed. Showing what was fetched. Try a smaller catalog or run again.','نتائج جزئية — بعض الدفعات فشلت. يتم عرض ما تم جلبه. جرب كتالوجاً أصغر أو أعد المحاولة.')}"
                        f"</div>", unsafe_allow_html=True)

                if ds_df is None or ds_df.empty:
                    st.markdown(
                        f"<div class='ok-banner'>"
                        f"{t('No dead stock found! All in-stock items have recent sales.','لا يوجد مخزون راكد! جميع الأصناف لديها مبيعات حديثة.')}"
                        f"</div>", unsafe_allow_html=True)
                else:
                    _never  = ds_df[ds_df["Status"]=="Never Sold"]
                    _dead   = ds_df[ds_df["Status"]=="Dead Stock"]
                    _total_frozen = ds_df["Frozen Value (SAR)"].sum()
                    _total_units  = ds_df["On Hand"].sum()

                    dm1,dm2,dm3,dm4 = st.columns(4)
                    dm1.metric(t("Total Dead SKUs","إجمالي الأصناف الراكدة"), len(ds_df))
                    dm2.metric(t("Never Sold","لم يُباع قط"), len(_never))
                    dm3.metric(t(f"No Sale {_ds_days}+ Days",f"لا بيع {_ds_days}+ يوم"), len(_dead))
                    dm4.metric(t("Total Units Frozen","إجمالي الوحدات المجمدة"), f"{int(_total_units):,}")

                    _never_val = _never["Frozen Value (SAR)"].sum()
                    _dead_val  = _dead["Frozen Value (SAR)"].sum()
                    st.markdown(f"""
                    <div style='background:rgba(212,168,75,0.06);
                                border:1px solid rgba(212,168,75,0.25);
                                border-radius:10px;padding:20px 24px;margin:12px 0;
                                display:flex;align-items:center;
                                justify-content:space-between;flex-wrap:wrap;gap:16px;'>
                      <div>
                        <div style='font-family:Outfit,sans-serif;font-size:8px;letter-spacing:4px;
                                    text-transform:uppercase;color:#D4A84B;margin-bottom:6px;'>
                          {t("Total Frozen Capital","إجمالي رأس المال المجمد")}
                        </div>
                        <div style='font-family:"Cormorant Garamond",serif;font-size:42px;
                                    font-weight:300;color:#fff;line-height:1;'>
                          {_total_frozen:,.0f}
                          <span style='font-size:18px;color:#D4A84B;letter-spacing:2px;'> SAR</span>
                        </div>
                      </div>
                      <div style='display:flex;gap:28px;flex-wrap:wrap;'>
                        <div style='text-align:center;'>
                          <div style='font-family:"Cormorant Garamond",serif;font-size:28px;
                                      font-weight:300;color:rgba(255,100,100,0.8);'>
                            {_never_val:,.0f}
                          </div>
                          <div style='font-family:Outfit,sans-serif;font-size:8px;letter-spacing:2px;
                                      text-transform:uppercase;color:rgba(255,255,255,0.25);margin-top:2px;'>
                            {t("Never Sold (SAR)","لم يُباع قط (ر.س)")}
                          </div>
                        </div>
                        <div style='text-align:center;'>
                          <div style='font-family:"Cormorant Garamond",serif;font-size:28px;
                                      font-weight:300;color:#D4A84B;'>
                            {_dead_val:,.0f}
                          </div>
                          <div style='font-family:Outfit,sans-serif;font-size:8px;letter-spacing:2px;
                                      text-transform:uppercase;color:rgba(255,255,255,0.25);margin-top:2px;'>
                            {t(f"Stale {_ds_days}+ Days (SAR)",f"راكد {_ds_days}+ يوم (ر.س)")}
                          </div>
                        </div>
                      </div>
                    </div>""", unsafe_allow_html=True)

                    ds_filter = st.radio(
                        t("Show","عرض"),
                        [t("All Dead Stock","كل المخزون الراكد"),
                         t("Never Sold","لم يُباع قط"),
                         t(f"No Sale {_ds_days}+ Days",f"لا بيع {_ds_days}+ يوم")],
                        horizontal=True, key="ds_filter")

                    if t("Never Sold","لم يُباع قط") in ds_filter:
                        _show_df = _never.copy()
                    elif t("No Sale","لا بيع") in ds_filter or str(_ds_days) in ds_filter:
                        _show_df = _dead.copy()
                    else:
                        _show_df = ds_df.copy()

                    if _show_df.empty:
                        st.info(t("No items in this category.","لا توجد أصناف في هذه الفئة."))
                    else:
                        _cats = sorted(_show_df["Category"].dropna().unique().tolist())
                        if len(_cats) > 1:
                            _sel_cats = st.multiselect(
                                t("Filter by Category","فلتر حسب الفئة"),
                                options=_cats, default=_cats, key="ds_cat_filter")
                            if _sel_cats:
                                _show_df = _show_df[_show_df["Category"].isin(_sel_cats)]

                        st.caption(
                            t(f"Showing {len(_show_df)} items — sorted by frozen value (highest first)",
                              f"عرض {len(_show_df)} صنف — مرتب حسب القيمة المجمدة (الأعلى أولاً)"))
                        _render_ds = _show_df.copy()
                        _render_ds["Days Since Sale"] = _render_ds["Days Since Sale"].apply(
                            lambda v: "Never" if v == 99999 else str(int(v)))
                        _render_ds["Frozen Value (SAR)"] = _render_ds["Frozen Value (SAR)"].map(
                            lambda v: f"{v:,.0f} SAR")
                        _render_ds["Unit Price"] = _render_ds["Unit Price"].map(
                            lambda v: f"{v:.2f} SAR")
                        _render_ds["On Hand"] = _render_ds["On Hand"].map(
                            lambda v: f"{int(v):,}")

                        _ds_cols = ["Model Code","Product","Category",
                                    "On Hand","Unit Price","Frozen Value (SAR)",
                                    "Last Sale Date","Days Since Sale","Status"]
                        _render_ds = _render_ds[[c for c in _ds_cols if c in _render_ds.columns]]

                        _th = "".join(f"<th>{c}</th>" for c in _render_ds.columns.tolist())
                        def _ds_row(ir):
                            idx, row = ir
                            is_never = str(row.get("Status","")) == "Never Sold"
                            cells = []
                            for ci, (col, val) in enumerate(row.items()):
                                if ci == 0:
                                    cells.append(f'<td class="cf">{val}</td>')
                                elif col == "Frozen Value (SAR)":
                                    cells.append(f'<td style="color:#D4A84B;font-weight:500;">{val}</td>')
                                elif col == "Status":
                                    clr = "rgba(255,100,100,0.8)" if is_never else "#D4A84B"
                                    cells.append(f'<td style="color:{clr};font-size:10px;letter-spacing:1px;">{val}</td>')
                                elif col == "Days Since Sale":
                                    clr = "rgba(255,100,100,0.8)" if val == "Never" else "#D4A84B"
                                    cells.append(f'<td style="color:{clr};font-weight:500;">{val}</td>')
                                else:
                                    cells.append(f"<td>{val}</td>")
                            return f'<tr>{"".join(cells)}</tr>'
                        _tbody = "".join(_ds_row(x) for x in _render_ds.iterrows())
                        _DS_CSS = """<style>
.swag-wrap{width:100%;overflow-x:auto;border:1px solid rgba(74,172,180,0.08);
  border-radius:4px;overflow:hidden;margin-bottom:4px;}
.swag-tbl{width:100%;border-collapse:collapse;
  font-family:'Outfit','Tajawal',sans-serif;}
.swag-tbl thead tr{background:rgba(74,172,180,0.05);
  border-bottom:1px solid rgba(74,172,180,0.1);}
.swag-tbl thead th{color:rgba(74,172,180,0.6);
  font-family:'Outfit',sans-serif;font-size:8px;letter-spacing:3px;
  text-transform:uppercase;font-weight:400;padding:13px 16px;
  text-align:center;white-space:nowrap;}
.swag-tbl tbody tr{border-bottom:1px solid rgba(255,255,255,0.03);
  transition:background 0.15s;}
.swag-tbl tbody tr:hover td{background:rgba(74,172,180,0.03);}
.swag-tbl tbody td{padding:11px 16px;text-align:center;
  font-size:12px;color:rgba(255,255,255,0.5);}
.swag-tbl tbody td.cf{font-family:'Outfit',monospace;font-size:11px;
  letter-spacing:0.5px;color:#fff;font-weight:500;
  border-right:1px solid rgba(74,172,180,0.08);}
</style>"""
                        st.markdown(
                            f'{_DS_CSS}<div class="swag-wrap">'
                            f'<table class="swag-tbl"><thead><tr>{_th}</tr></thead>'
                            f'<tbody>{_tbody}</tbody></table></div>',
                            unsafe_allow_html=True)
                        st.markdown("<br>", unsafe_allow_html=True)
                        _export_df = _show_df.copy()
                        _export_df["Days Since Sale"] = _export_df["Days Since Sale"].apply(
                            lambda v: "Never" if v == 99999 else int(v))
                        ex1, ex2 = st.columns([1, 3])
                        ex1.download_button(
                            t("Export Excel ↓","تصدير Excel ↓"),
                            _excel_generic(_export_df, t("Dead Stock","المخزون الراكد")),
                            dl_name("dead_stock","xlsx"),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="ds_excel_dl")
                        with ex2:
                            st.markdown(
                                f"<div class='warn-banner'>"
                                f"{t('Action recommended: review with purchasing team — discount, transfer to active branch, or write-off.','الإجراء المقترح: مراجعة مع فريق المشتريات — تخفيض السعر أو النقل لفرع نشط أو الشطب.')}"
                                f"</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style='background:rgba(74,172,180,0.03);border:1px solid rgba(74,172,180,0.1);
                            border-radius:12px;padding:40px;text-align:center;'>
                  <div style='font-family:Cormorant Garamond,serif;font-size:48px;
                              font-weight:300;color:rgba(255,255,255,0.1);margin-bottom:12px;'>
                    {t("Dead Stock","المخزون الراكد")}
                  </div>
                  <div style='font-family:Outfit,sans-serif;font-size:10px;letter-spacing:3px;
                              text-transform:uppercase;color:rgba(255,255,255,0.2);'>
                    {t("Set threshold days above and click Find Dead Stock","حدد عدد الأيام أعلاه واضغط ابحث عن المخزون الراكد")}
                  </div>
                </div>""", unsafe_allow_html=True)

    # TAB: SEASON COMPARISON (integrated from season dashboard)
    if len(tlabels) > ti and tlabels[ti] == t("Season Comparison","مقارنة الموسم"):
        with tabs[ti]:
            ti += 1
            # Season detection initialisation
            if not st.session_state.get("season_audit_done", False):
                with st.spinner("Loading seasons..."):
                    asi, audits = run_full_discovery()
                    st.session_state["season_all_systems_info"] = asi
                    st.session_state["season_audits"] = audits
                    st.session_state["season_audit_done"] = True
                    st.session_state["season_unified_seasons"] = build_unified_season_list(asi)
                    st.session_state["season_available_types"] = build_available_types(asi)
                    for k in ["season_long_df", "season_company_matrix", "season_name", "season_fetch_debug"]:
                        st.session_state.pop(k, None)

            season_all_systems_info = st.session_state.get("season_all_systems_info", {})
            season_audits = st.session_state.get("season_audits", {})
            season_fetch_debug = st.session_state.get("season_fetch_debug", {})
            unified_seasons = st.session_state.get("season_unified_seasons", [])
            available_types = st.session_state.get("season_available_types", [])

            # Diagnostics expander inside season tab
            with st.expander("🔧 Season Diagnostics (field audit / manual override)", expanded=False):
                render_audit_report(season_audits)

            # Company status (quick check)
            st.markdown("<div class='section-tag'>Company readiness</div>", unsafe_allow_html=True)
            loaded_companies = 0
            for sys in SYSTEM_KEYS:
                name = get_system_name(sys)
                if sys in season_all_systems_info:
                    loaded_companies += 1
                    st.markdown(f"✅ **{name}** — ready")
                else:
                    audit = season_audits.get(sys)
                    if audit and audit.get("status") == "no_config":
                        st.markdown(f"❌ **{name}** — config missing")
                    elif audit and audit.get("status") == "auth_failed":
                        st.markdown(f"❌ **{name}** — login failed")
                    else:
                        st.markdown(f"⚠️ **{name}** — no season field detected (use diagnostics above)")
            if not season_all_systems_info:
                st.warning("No season field detected for any company. Use Diagnostics to manually pick a field.")
            else:
                # Season selection UI
                st.markdown("<div class='section-tag'>Search Season</div>", unsafe_allow_html=True)
                search_mode = st.radio("Selection mode",
                                       ["🌦️ Season type — ALL years, ALL companies", "🎯 Exact season"],
                                       horizontal=True, label_visibility="collapsed")
                selected_query = ""
                resolve_mode = "type"
                if search_mode.startswith("🌦️"):
                    resolve_mode = "type"
                    if available_types:
                        picked = st.selectbox("Season type", options=[""] + available_types,
                                              format_func=lambda t: "— Choose a type —" if t == "" else SEASON_TYPE_LABEL.get(t, t),
                                              key="season_type_pick")
                        if picked:
                            selected_query = picked
                    else:
                        st.warning("No season types detected.")
                else:
                    resolve_mode = "exact"
                    if unified_seasons:
                        selected_query = st.selectbox("Season", options=[""] + unified_seasons,
                                                      format_func=lambda x: "— Choose a season —" if x == "" else x,
                                                      key="season_exact_pick")
                    else:
                        st.warning("No seasons loaded. Reload seasons using Reload button above.")

                if selected_query:
                    title = SEASON_TYPE_LABEL.get(selected_query, selected_query) if resolve_mode == "type" else selected_query
                    st.markdown(f"<div class='info-banner'>Will fetch: {title}</div>", unsafe_allow_html=True)
                    cols = st.columns(len(season_all_systems_info))
                    for i, (sys, info) in enumerate(season_all_systems_info.items()):
                        _, lbls, _ = resolve_season_values_for_system(selected_query, info, resolve_mode)
                        with cols[i]:
                            st.markdown(f"<div class='season-match-box'>"
                                        f"<div class='season-match-sys'>{get_system_name(sys)}</div>"
                                        f"<div class='season-match-label'>{'<br>'.join(lbls) if lbls else '—'}</div>"
                                        f"</div>", unsafe_allow_html=True)

                cbtn_season = st.button("Compare Season", type="primary", disabled=not bool(selected_query), key="season_compare_btn")

                if cbtn_season and selected_query:
                    include_archived = st.checkbox("Include archived products", value=False,
                                                   help="On = also include discontinued/archived items (maximum coverage). Off = active products only.",
                                                   key="season_include_archived")
                    with st.spinner("Fetching stock from every branch of every company..."):
                        long_df, comp, fdebug = build_matrices(selected_query, season_all_systems_info, resolve_mode, include_archived)
                    st.session_state["season_fetch_debug"] = fdebug
                    if comp.empty:
                        st.error("No products found for this season.")
                    else:
                        disp = SEASON_TYPE_LABEL.get(selected_query, selected_query) if resolve_mode == "type" else selected_query
                        st.session_state["season_long_df"] = long_df
                        st.session_state["season_company_matrix"] = comp
                        st.session_state["season_name"] = disp
                        st.rerun()

                # Display results if available
                if "season_company_matrix" in st.session_state:
                    comp = st.session_state["season_company_matrix"]
                    long_df = st.session_state.get("season_long_df", pd.DataFrame(columns=LONG_COLS))
                    season_name = st.session_state["season_name"]
                    active_systems = [s for s in SYSTEM_KEYS if f"{s} Qty" in comp.columns]

                    c1,c2,c3,c4 = st.columns(4)
                    c1.metric("Total Models", f"{len(comp):,}")
                    c2.metric("Total Units", f"{int(comp['Total Qty'].sum()):,}")
                    years = set()
                    if "Year" in comp.columns:
                        years = {y for v in comp["Year"] for y in str(v).split(", ") if y}
                    c3.metric("Years Covered", ", ".join(sorted(years)) or "—")
                    n_branches = long_df["Branch"].nunique() if not long_df.empty else 0
                    c4.metric("Branches", f"{n_branches:,}")

                    hs = stock_health(comp, active_systems)
                    if hs:
                        h1, h2, h3 = st.columns(3)
                        h1.metric("Zero-Stock Models", f"{hs['zero_all']:,}",
                                  help="Models in this season with 0 units everywhere")
                        h2.metric("Single-Company Only", f"{hs['single_company']:,}",
                                  help="Stocked in exactly one company — candidates for transfer/sync")
                        h3.metric("In All Companies", f"{hs['all_companies']:,}",
                                  help="Models carried by every company")

                    with st.expander("📊 Overview Charts (units by company / branch)", expanded=False):
                        ucol, bcol = st.columns(2)
                        with ucol:
                            st.caption("Units by Company")
                            ubc = units_by_company(long_df)
                            if not ubc.empty:
                                st.bar_chart(ubc, use_container_width=True)
                        with bcol:
                            st.caption("Top Branches by Units")
                            ubb = units_by_branch(long_df, top_n=15)
                            if not ubb.empty:
                                st.bar_chart(ubb, use_container_width=True)

                    sv = compute_stock_value(comp, active_systems)
                    if sv:
                        with st.expander("💵 Stock Value per System (qty × price)", expanded=False):
                            vc = st.columns(len(sv))
                            for i, (nm, val) in enumerate(sv.items()):
                                vc[i].metric(nm, f"{val:,.0f}")

                    miss = compute_missing_analysis(comp, active_systems)
                    if not miss.empty:
                        with st.expander(f"⚠️ Missing Products — {len(miss):,} items in SWAG but not in others", expanded=False):
                            st.dataframe(miss.head(200), use_container_width=True, height=320)
                            st.download_button("Download Missing Excel", to_excel_generic_season(miss, season_name, "Missing"),
                                               f"missing_{season_name}.xlsx",
                                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                               key="miss_dl_season")

                    _heavy_ok = len(comp) <= HEAVY_COMPUTE_ROW_CAP
                    if not _heavy_ok:
                        st.markdown(f"<div class='info-banner'>Large result ({len(comp):,} models) — "
                                    "Price Gap and Transfer Suggestions are skipped on screen to keep things "
                                    "fast. Use the matrix views and Excel exports below.</div>",
                                    unsafe_allow_html=True)

                    pa = compute_price_alerts(comp, active_systems) if _heavy_ok else pd.DataFrame()
                    if not pa.empty:
                        with st.expander(f"💰 Price Gap — {len(pa):,} products with {PRICE_DIFF_THRESHOLD_PCT:.0f}%+ difference", expanded=False):
                            st.dataframe(pa.head(200), use_container_width=True, height=320)
                            st.download_button("Download Price Alerts Excel", to_excel_generic_season(pa, season_name, "PriceGaps"),
                                               f"price_{season_name}.xlsx",
                                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                               key="price_dl_season")

                    rb = compute_rebalancing(comp, active_systems) if _heavy_ok else pd.DataFrame()
                    if not rb.empty:
                        with st.expander(f"🔄 Transfer Suggestions — {len(rb):,} rebalancing moves "
                                         "(model has stock in one company, 0 in another)", expanded=False):
                            st.dataframe(rb.head(300), use_container_width=True, height=340)
                            st.download_button("Download Transfer Suggestions Excel",
                                               to_excel_generic_season(rb, season_name, "Transfers"),
                                               f"transfers_{season_name}.xlsx",
                                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                               key="rebal_dl_season")

                    zs = zero_stock_models(comp)
                    if not zs.empty:
                        with st.expander(f"🪦 Zero-Stock Models — {len(zs):,} models with 0 units everywhere "
                                         "(clearance / discontinue review)", expanded=False):
                            st.dataframe(zs.head(300), use_container_width=True, height=320)
                            st.download_button("Download Zero-Stock Excel",
                                               to_excel_generic_season(zs, season_name, "ZeroStock"),
                                               f"zerostock_{season_name}.xlsx",
                                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                               key="zero_dl_season")

                    with st.expander("📝 Text Summary (copy → paste to WhatsApp / email)", expanded=False):
                        _summary = build_season_text_summary(comp, long_df, season_name, active_systems)
                        st.text_area("Season summary", value=_summary, height=300, key="season_summary",
                                     help="Select all → copy → paste anywhere.")
                        st.download_button("Download .txt", _summary.encode("utf-8"),
                                           f"season_summary_{season_name}.txt", "text/plain",
                                           key="summary_txt_dl_season")

                    st.markdown("<div class='section-tag'>Comparison Matrix</div>", unsafe_allow_html=True)
                    view = st.radio("View", ["🏢 Company-wise", "🏬 Branch-wise", "📏 Size-wise"],
                                    horizontal=True, label_visibility="collapsed", key="season_view_radio")
                    search_season = st.text_input("Search model / product", placeholder="e.g. XP6013", key="season_matrix_search").strip()

                    if view.startswith("🏢"):
                        show_df = comp.copy()
                        only_diff = st.checkbox("Only differences (systems disagree)", value=False, key="season_only_diff")
                        if only_diff:
                            show_df = only_differences(show_df, active_systems)
                        if search_season:
                            q = search_season.lower()
                            m = (show_df["Model Code"].astype(str).str.lower().str.contains(q, regex=False)
                                 | show_df["Product"].astype(str).str.lower().str.contains(q, regex=False))
                            show_df = show_df[m]
                        st.dataframe(show_df.head(200), use_container_width=True, height=560)
                        st.caption(f"Showing {min(len(show_df),200):,} of {len(show_df):,} models. Full data in Excel.")
                        dca, dcb = st.columns(2)
                        dca.download_button("Download Company-wise Excel", to_excel_generic_season(show_df, season_name, "Company"),
                                            f"season_company_{season_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                            key="comp_dl_season", use_container_width=True)
                        dcb.download_button("Download CSV", show_df.to_csv(index=False).encode("utf-8-sig"),
                                            f"season_company_{season_name}.csv", "text/csv",
                                            key="comp_csv_season", use_container_width=True)
                    elif view.startswith("🏬"):
                        branch_df = build_branch_matrix(long_df)
                        if branch_df.empty:
                            st.info("No branch data.")
                        else:
                            branch_cols = [c for c in branch_df.columns if " | " in c]
                            sys_options = sorted({c.split(" | ")[0] for c in branch_cols})
                            sel = st.multiselect("Filter companies", options=sys_options, default=sys_options, key="branch_sys_filter_season")
                            keep_cols = ["Model Code", "Product", "Year"] + [c for c in branch_cols if c.split(" | ")[0] in sel] + ["Total"]
                            view_df = branch_df[keep_cols].copy()
                            fbc = [c for c in keep_cols if " | " in c]
                            view_df["Total"] = view_df[fbc].sum(axis=1).astype(int)
                            if search_season:
                                q = search_season.lower()
                                m = (view_df["Model Code"].astype(str).str.lower().str.contains(q, regex=False)
                                     | view_df["Product"].astype(str).str.lower().str.contains(q, regex=False))
                                view_df = view_df[m]
                            view_df = view_df.sort_values(["Total", "Model Code"], ascending=[False, True]).reset_index(drop=True)
                            st.dataframe(view_df.head(200), use_container_width=True, height=560)
                            st.caption(f"Showing {min(len(view_df),200):,} of {len(view_df):,} models · "
                                       f"{len(fbc)} branch columns. Full data in Excel.")
                            dba, dbb = st.columns(2)
                            dba.download_button("Download Branch-wise Excel", to_excel_generic_season(view_df, season_name, "Branch"),
                                                f"season_branch_{season_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                                key="branch_dl_season", use_container_width=True)
                            dbb.download_button("Download CSV", view_df.to_csv(index=False).encode("utf-8-sig"),
                                                f"season_branch_{season_name}.csv", "text/csv",
                                                key="branch_csv_season", use_container_width=True)
                    else:
                        size_df, size_cols = build_size_pivot_season(long_df)
                        if size_df.empty:
                            st.info("No size suffixes detected in model codes (e.g. XP6013-M). Size view works when codes end with -S/-M/-L/-XL/-XXL etc.")
                        else:
                            sm1, sm2, sm3 = st.columns(3)
                            sm1.metric("Base Models", f"{size_df['Base Model'].nunique():,}")
                            sm2.metric("Total Units", f"{int(size_df['Total'].sum()):,}")
                            sm3.metric("Sizes Found", f"{len(size_cols)}")
                            sdf = size_df.copy()
                            if search_season:
                                q = search_season.lower()
                                m = (sdf["Base Model"].astype(str).str.lower().str.contains(q, regex=False)
                                     | sdf["Product"].astype(str).str.lower().str.contains(q, regex=False))
                                sdf = sdf[m]
                            st.dataframe(sdf.head(200), use_container_width=True, height=560)
                            st.caption(f"Showing {min(len(sdf),200):,} of {len(sdf):,} base models · sizes: {', '.join(size_cols)}")
                            dsa, dsb = st.columns(2)
                            dsa.download_button("Download Size-wise Excel", to_excel_generic_season(sdf, season_name, "Sizes"),
                                                f"season_sizes_{season_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                                key="size_dl_season", use_container_width=True)
                            dsb.download_button("Download CSV", sdf.to_csv(index=False).encode("utf-8-sig"),
                                                f"season_sizes_{season_name}.csv", "text/csv",
                                                key="size_csv_season", use_container_width=True)

                    # Full export workbook (season)
                    st.markdown("<div class='section-tag'>Full Export</div>", unsafe_allow_html=True)
                    if st.checkbox("Prepare combined workbook (Company + Branch + Size + Transfers + Zero-Stock) for this season",
                                   value=False, key="prep_full_season"):
                        with st.spinner("Building combined workbook..."):
                            _branch_full = build_branch_matrix(long_df)
                            _size_full, _ = build_size_pivot_season(long_df)
                            _rebal_full = compute_rebalancing(comp, active_systems) if len(comp) <= HEAVY_COMPUTE_ROW_CAP else pd.DataFrame()
                            _zero_full = zero_stock_models(comp)
                            _wb = to_excel_workbook_season(
                                [("Company", comp), ("Branch", _branch_full), ("Sizes", _size_full),
                                 ("Transfers", _rebal_full), ("ZeroStock", _zero_full)],
                                season_name)
                        st.download_button(
                            "⬇️ Download EVERYTHING (one Excel)",
                            _wb,
                            f"season_full_{season_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="full_dl_season", use_container_width=True)

                    if st.button("Clear Season Data", type="secondary", key="clear_season"):
                        for k in ["season_long_df", "season_company_matrix", "season_name", "season_fetch_debug"]:
                            st.session_state.pop(k, None)
                        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# ENTRY POINT
# =============================================================================
restore_session()
if not st.session_state.authenticated:
    show_login()
else:
    show_dashboard()
