"""
SWAG Product Comparison Dashboard
Version 3.0 — Ultra Premium Dark Design
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
SYSTEM_KEYS = ["SWAG", "STOCK", "LAROUCHE", "DIFFC", "FASHION_LIMITS"]

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
    "so_analytics_df": None, "so_last_model": "",
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
    cfg = st.secrets.get(system_key)
    if not cfg: return empty
    uid = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not uid: return empty
    u = cfg["url"]; db = cfg["db"]; ak = cfg["api_key"]
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
# PURCHASE HISTORY
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_swag_purchase_history(model_code, date_from, date_to, system_key="SWAG"):
    cols = ["Date","PO","Vendor","Brand Category","Category",
            "Model Code","Product","Qty","Unit Price","Subtotal"]
    empty = pd.DataFrame(columns=cols)
    cfg = st.secrets.get(system_key)
    if not cfg: return empty
    uid = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not uid: return empty
    u = cfg["url"]; db = cfg["db"]; ak = cfg["api_key"]
    try:
        dom = [
            ["order_id.state", "in", ["purchase", "done"]],
            ["order_id.date_order", ">=", f"{date_from} 00:00:00"],
            ["order_id.date_order", "<=", f"{date_to} 23:59:59"],
        ]
        if model_code and model_code.strip():
            dom.append(["product_id.default_code", "=", model_code.strip()])
        lines = _x(u, db, uid, ak, "purchase.order.line", "search_read", [dom],
                   {"fields": ["order_id","product_id","product_qty","price_unit"],
                    "limit": 5000, "order": "order_id desc"})
        if not lines: return empty
        oids = list({l["order_id"][0] for l in lines if isinstance(l.get("order_id"), list)})
        pids = list({l["product_id"][0] for l in lines if isinstance(l.get("product_id"), list)})
        orders  = _x(u, db, uid, ak, "purchase.order", "search_read",
                     [[["id","in",oids]]],
                     {"fields":["id","name","partner_id","date_order"],"limit":len(oids)+10})
        omap    = {o["id"]: o for o in orders}
        prods   = _x(u, db, uid, ak, "product.product", "search_read",
                     [[["id","in",pids]]],
                     {"fields":["id","default_code","display_name","categ_id","product_tmpl_id"],
                      "limit":len(pids)+10})
        pmap    = {p["id"]: p for p in prods}
        tids    = list({p["product_tmpl_id"][0] for p in prods
                        if isinstance(p.get("product_tmpl_id"), list)})
        tmap    = {}
        if tids:
            try:
                tmpls = _x(u, db, uid, ak, "product.template", "search_read",
                           [[["id","in",tids]]],
                           {"fields":["id","x_brand_category_id"],"limit":len(tids)+10})
                tmap = {t_["id"]: t_ for t_ in tmpls}
            except Exception:
                pass
        rows = []
        for line in lines:
            oid   = line["order_id"][0] if isinstance(line.get("order_id"), list) else None
            pid   = line["product_id"][0] if isinstance(line.get("product_id"), list) else None
            order = omap.get(oid, {})
            prod  = pmap.get(pid, {})
            raw_d = order.get("date_order") or ""
            try:    ds = datetime.strptime(raw_d, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
            except: ds = raw_d[:10] if raw_d else "—"
            partner = order.get("partner_id")
            vendor  = partner[1] if isinstance(partner, list) else (str(partner) if partner else "—")
            categ   = prod.get("categ_id")
            category = categ[1] if isinstance(categ, list) else (str(categ) if categ else "")
            brand_category = ""
            tr = prod.get("product_tmpl_id")
            if isinstance(tr, list) and tr:
                tmpl = tmap.get(tr[0], {})
                bc   = tmpl.get("x_brand_category_id")
                if isinstance(bc, list): brand_category = bc[1] if len(bc) > 1 else ""
                elif bc: brand_category = str(bc)
            qty   = float(line.get("product_qty") or 0)
            price = float(line.get("price_unit") or 0)
            rows.append({
                "Date": ds, "PO": order.get("name") or "—",
                "Vendor": vendor, "Brand Category": brand_category,
                "Category": category,
                "Model Code": prod.get("default_code") or "",
                "Product": prod.get("display_name") or "",
                "Qty": qty, "Unit Price": price,
                "Subtotal": round(qty * price, 2),
            })
        if not rows: return empty
        return pd.DataFrame(rows).sort_values(by="Date", ascending=False).reset_index(drop=True)
    except Exception:
        return empty

# ─────────────────────────────────────────────────────────────────────────────
# SALES HISTORY
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_swag_sales_history(model_code=None, date_from=None, date_to=None, system_key="SWAG"):
    empty = pd.DataFrame(columns=[
        "Date","SO","Customer","Branch","Brand Category","Category",
        "Model Code","Product","Qty","Unit Price","Subtotal"])
    cfg = st.secrets.get(system_key)
    if not cfg: return empty
    uid = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not uid: return empty
    u, db, ak = cfg["url"], cfg["db"], cfg["api_key"]
    try:
        dom = [
            ["order_id.state","in",["sale","done"]],
            ["order_id.date_order",">=",f"{date_from} 00:00:00"],
            ["order_id.date_order","<=",f"{date_to} 23:59:59"],
        ]
        if model_code:
            dom.append(["product_id.default_code","=like",f"{model_code}%"])
        lines = _x(u, db, uid, ak, "sale.order.line", "search_read", [dom],
                   {"fields":["order_id","product_id","product_uom_qty","price_unit","price_subtotal"],
                    "limit":15000,"order":"order_id desc"})
        if not lines: return empty
        oids  = list({l["order_id"][0] for l in lines if isinstance(l.get("order_id"), list)})
        orders = _x(u, db, uid, ak, "sale.order", "search_read",
                    [[["id","in",oids]]],
                    {"fields":["id","name","partner_id","date_order","branch_id"],
                     "limit":len(oids)+10})
        omap  = {o["id"]: o for o in orders}
        pids  = list({l["product_id"][0] for l in lines if isinstance(l.get("product_id"), list)})
        prods = _x(u, db, uid, ak, "product.product", "search_read",
                   [[["id","in",pids]]],
                   {"fields":["id","default_code","name","categ_id","product_tmpl_id"],
                    "limit":len(pids)+10})
        pmap  = {p["id"]: p for p in prods}
        tids  = list({p["product_tmpl_id"][0] for p in prods
                      if isinstance(p.get("product_tmpl_id"), list)})
        tmap  = {}
        if tids:
            try:
                tmpls = _x(u, db, uid, ak, "product.template", "search_read",
                           [[["id","in",tids]]],
                           {"fields":["id","x_studio_brand_category"],"limit":len(tids)+10})
                tmap = {tt["id"]: tt for tt in tmpls}
            except Exception:
                pass
        rows = []
        for line in lines:
            oid = line["order_id"][0] if isinstance(line.get("order_id"), list) else None
            pid = line["product_id"][0] if isinstance(line.get("product_id"), list) else None
            o   = omap.get(oid, {})
            p   = pmap.get(pid, {})
            tr  = p.get("product_tmpl_id")
            tid = tr[0] if isinstance(tr, list) else tr
            tmpl = tmap.get(tid, {})
            br   = o.get("branch_id")
            branch = br[1] if isinstance(br, list) and len(br)>1 else (str(br) if br else "Unknown")
            cat  = p.get("categ_id")
            categ = cat[1] if isinstance(cat, list) and len(cat)>1 else (str(cat) if cat else "")
            bcr  = tmpl.get("x_studio_brand_category", "")
            brand_cat = bcr[1] if isinstance(bcr, list) and len(bcr)>1 else (str(bcr) if bcr else "")
            partner = o.get("partner_id")
            customer = partner[1] if isinstance(partner, list) and len(partner)>1 else (str(partner) if partner else "")
            pname = line.get("product_id")
            pdisplay = pname[1] if isinstance(pname, list) and len(pname)>1 else p.get("name","")
            raw_d = str(o.get("date_order",""))
            rows.append({
                "Date": raw_d[:10] if raw_d else "",
                "SO": o.get("name",""), "Customer": customer,
                "Branch": branch, "Brand Category": brand_cat or "(No Brand)",
                "Category": categ or "(No Category)",
                "Model Code": str(p.get("default_code","")).strip(),
                "Product": pdisplay,
                "Qty": float(line.get("product_uom_qty") or 0),
                "Unit Price": float(line.get("price_unit") or 0),
                "Subtotal": float(line.get("price_subtotal") or 0),
            })
        df = pd.DataFrame(rows)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        return df.sort_values("Date", ascending=False).reset_index(drop=True)
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
def fetch_dead_stock(threshold_days=60, system_key="SWAG"):
    empty_cols = [
        "Model Code","Product","Category","On Hand",
        "Unit Price","Frozen Value (SAR)",
        "Last Sale Date","Days Since Sale","Status"
    ]
    empty = pd.DataFrame(columns=empty_cols)

    cfg = st.secrets.get(system_key)
    if not cfg: return empty
    uid = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not uid: return empty
    u, db, ak = cfg["url"], cfg["db"], cfg["api_key"]

    today  = datetime.now().date()
    cutoff = (today - timedelta(days=threshold_days)).strftime("%Y-%m-%d")

    try:
        # ── Step 1: All products with qty_available > 0 ──────────────────
        # product.product has qty_available as computed field — fast, no quant scan
        all_prods = _x(u, db, uid, ak, "product.product", "search_read",
                       [[["qty_available",">",0],
                         ["sale_ok","=",True]]],
                       {"fields": ["id","default_code","display_name",
                                   "categ_id","list_price","qty_available"],
                        "limit": 10000,
                        "order": "default_code asc"})

        if not all_prods:
            return empty

        all_pids  = [p["id"] for p in all_prods]
        prod_map  = {p["id"]: p for p in all_prods}

        # ── Step 2: Find products that HAVE sold recently (after cutoff) ──
        # One single call — get all product_ids that had a sale after cutoff
        # This is MUCH faster than fetching all history
        recent_sol = _x(u, db, uid, ak, "sale.order.line", "search_read",
                        [[["product_id","in", all_pids],
                          ["order_id.state","in",["sale","done"]],
                          ["order_id.date_order",">=", f"{cutoff} 00:00:00"]]],
                        {"fields": ["product_id"],
                         "limit": 50000})

        recently_sold_pids = set()
        for line in (recent_sol or []):
            pid = line["product_id"][0] if isinstance(line.get("product_id"),list) else None
            if pid: recently_sold_pids.add(pid)

        # ── Step 3: Dead candidates = in stock but NOT recently sold ──────
        dead_pids = [p for p in all_pids if p not in recently_sold_pids]

        if not dead_pids:
            return empty

        # ── Step 4: For dead candidates, find their actual last sale date ─
        # Only fetch history for dead items (much smaller set)
        last_sale_map = {}  # pid -> date

        CHUNK = 500
        for i in range(0, len(dead_pids), CHUNK):
            chunk = dead_pids[i:i+CHUNK]

            sol_chunk = _x(u, db, uid, ak, "sale.order.line", "search_read",
                           [[["product_id","in", chunk],
                             ["order_id.state","in",["sale","done"]]]],
                           {"fields": ["product_id","order_id"],
                            "limit": 50000,
                            "order": "id desc"})

            if not sol_chunk: continue

            oids = list({ln["order_id"][0] for ln in sol_chunk
                         if isinstance(ln.get("order_id"),list)})
            if not oids: continue

            orders_ch = _x(u, db, uid, ak, "sale.order", "search_read",
                           [[["id","in",oids]]],
                           {"fields":["id","date_order"],
                            "limit": len(oids)+5})

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

        # ── Step 5: Build result rows ────────────────────────────────────
        rows = []
        for pid in dead_pids:
            prod  = prod_map.get(pid, {})
            code  = str(prod.get("default_code") or "").strip()
            name  = prod.get("display_name") or ""
            cat   = prod.get("categ_id")
            categ = cat[1] if isinstance(cat,list) and len(cat)>1 else ""
            price = float(prod.get("list_price") or 0)
            qty   = float(prod.get("qty_available") or 0)
            if qty <= 0: continue
            frozen_val = round(qty * price, 2)

            last_sale  = last_sale_map.get(pid)  # date or None

            if last_sale is None:
                days_since = 99999
                status     = "Never Sold"
            else:
                days_since = (today - last_sale).days
                # double-check — should be >= threshold since we filtered above
                status = "Dead Stock"

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
            return empty

        df = pd.DataFrame(rows)
        df = df.sort_values("Frozen Value (SAR)", ascending=False).reset_index(drop=True)
        return df

    except Exception as e:
        st.error(f"Dead Stock error: {e}")
        return empty

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
        cfg = st.secrets.get(key)
        sn  = key
        R   = {"key":key,"total":[],"branch":[],"transfers":[],"reorder":[]}
        if not cfg:
            R["total"].append({CS:sn,CM:"—",CPR:"No config",CP:0.0,CQ:0,"_status":"ERROR"})
            return R
        uid = _auth(cfg["url"],cfg["db"],cfg["user"],cfg["api_key"])
        if not uid:
            R["total"].append({CS:sn,CM:"—",CPR:"Auth failed",CP:0.0,CQ:0,"_status":"ERROR"})
            return R
        u=cfg["url"];db=cfg["db"];ak=cfg["api_key"]
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
# PRICE HISTORY
# ─────────────────────────────────────────────────────────────────────────────


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
        sm3.metric(t("Avg Price","متوسط السعر"),
                   f"{vp[vp>0].mean():.2f} SAR" if not vp[vp>0].empty else "—")
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
        return f'<tr class="{cls}">{cells}</tr>'
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
        <div style='text-align:center;padding:60px 0 8px;'>
          <div style='display:flex;justify-content:center;margin-bottom:28px;'>
            <svg width="72" height="72" viewBox="0 0 72 72" fill="none">
              <rect width="72" height="72" fill="rgba(74,172,180,0.04)" rx="2"/>
              <path d="M36 8 L60 36 L36 64 L12 36 Z" stroke="#4AACB4" stroke-width="1" fill="none"/>
              <path d="M36 16 L54 36 L36 56 L18 36 Z" stroke="#4AACB4" stroke-width="0.6" fill="none" opacity="0.5"/>
              <path d="M36 24 L48 36 L36 48 L24 36 Z" fill="#4AACB4" opacity="0.3"/>
              <circle cx="36" cy="8"  r="3" fill="#D4A84B"/>
              <circle cx="60" cy="36" r="3" fill="#D4A84B"/>
              <circle cx="36" cy="64" r="3" fill="#D4A84B"/>
              <circle cx="12" cy="36" r="3" fill="#D4A84B"/>
            </svg>
          </div>
          <div class="login-title">SWAG</div>
          <div class="login-sub">Product Intelligence · 4 Systems</div>
        </div>""", unsafe_allow_html=True)

        st.markdown("<div class='login-card'>", unsafe_allow_html=True)
        with st.form("lf", clear_on_submit=False):
            em = st.text_input(t("Email","البريد الإلكتروني"),
                               placeholder="you@swag.com.sa")
            pw = st.text_input(t("Password","كلمة المرور"),
                               type="password", placeholder="••••••••")
            st.markdown("<br>", unsafe_allow_html=True)
            sub = st.form_submit_button(
                t("Sign In →","تسجيل الدخول →"),
                use_container_width=True, type="primary")
        st.markdown("</div>", unsafe_allow_html=True)

        if sub:
            if not em or not pw:
                st.error(t("Fill in both fields.","يرجى ملء جميع الحقول.")); return
            if "LOGIN" not in st.secrets:
                st.error("LOGIN section missing in secrets.toml"); return
            cfg = st.secrets["LOGIN"]
            with st.spinner(t("Authenticating...","جارٍ التحقق...")):
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
                        time.sleep(0.3); st.rerun()
                    else:
                        st.error(t("Wrong email or password.",
                                   "بريد إلكتروني أو كلمة مرور خاطئة."))
                except Exception as e:
                    st.error(f"Connection error: {e}")

        st.markdown("""
        <p style='text-align:center;font-family:Outfit,sans-serif;font-size:8px;
                  letter-spacing:3px;color:rgba(255,255,255,0.1);margin-top:28px;
                  text-transform:uppercase;'>
          SWAG Dashboard · 2025
        </p>""", unsafe_allow_html=True)

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
        <div class="eyebrow">Real-time · 4 Odoo Systems · Live Data</div>
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

        t1,t2,t3,t4,t5 = st.columns(5)
        sz  = t1.toggle(t("Zero","الصفري"),     value=False)
        sb  = t2.toggle(t("Branch","فروع"),      value=False)
        ss  = t3.toggle(t("Sort","ترتيب"),       value=False)
        st_ = t4.toggle(t("Transfers","نقليات"), value=False)
        sr  = t5.toggle(t("Reorder","طلب"),      value=False)

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
        with st.spinner(t("Fetching from 4 systems...","جلب البيانات من 4 أنظمة...")):
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
                mask = raw_tdf["System"] == key
                if mask.any():
                    sv = raw_tdf.loc[mask,"_status"]
                    if   "OK"    in sv.values: ns[key]="OK"
                    elif "ERROR" in sv.values: ns[key]="ERROR"

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

        # Purchase Qty — fetch for SWAG + STOCK (both have purchase orders)
        # Other systems (LAROUCHE, DIFFC, FASHION_LIMITS) get 0
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
                # Merge into tdf
                _tmp = tdf.merge(_pur_df2[[mc_loc,"Purchase Qty"]]
                                 .rename(columns={"Purchase Qty":"_pur_tmp"}),
                                 on=mc_loc, how="left")
                # Only update rows for this system
                _fill = _tmp["_pur_tmp"].fillna(0).astype(int)
                tdf.loc[_pur_mask, "Purchase Qty"] = _fill[_pur_mask].values

        pur_col = t("Purchase Qty","كمية المشتريات")
        tdf = tdf.rename(columns={"Purchase Qty":pur_col})
        desired = [sc2_loc,mc_loc,t("Product","المنتج"),
                   t("Sale Price","سعر البيع"),pur_col,qc2]
        existing = tdf.columns.tolist()
        final    = [c for c in desired if c in existing]
        for c in existing:
            if c not in final: final.append(c)
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
        return

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

    # Stock value = qty * price per row, summed
    _stock_value = 0.0
    if qc2 in ok.columns and pc2 in ok.columns:
        _stock_value = (_ok_qty * _ok_price).sum()

    # Per-system stock value
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
        m4.metric(t("Avg Price","متوسط السعر"),
                  f"{vp.mean():.2f} SAR" if not vp.empty else "—")
    m5.metric(
        t("Total Stock Value","إجمالي قيمة المخزون"),
        f"{_stock_value:,.0f} SAR" if _stock_value > 0 else "—")
    _zero_val = int((_ok_qty == 0).sum()) if not _ok_qty.empty else 0
    m6.metric(t("Zero Stock Items","أصناف بلا مخزون"), _zero_val)

    hb = bdf  is not None and not bdf.empty
    ht = st.session_state.show_transfers and trdf is not None and not trdf.empty
    hr = st.session_state.show_reorder   and rdf  is not None and not rdf.empty

    tlabels = [t("Total Stock","المخزون الإجمالي")]
    if hb: tlabels.append(t("Branch Stock","مخزون الفروع"))
    if ht: tlabels.append(t("Transfers","النقليات"))
    if hr: tlabels.append(t("Reorder","إعادة الطلب"))
    tlabels += [t("SWAG Purchase","مشتريات سواغ"), t("SWAG Sales","مبيعات سواغ"), t("Dead Stock","المخزون الراكد"), t("Barcode Scanner","ماسح الباركود")]

    tabs = st.tabs(tlabels); ti = 0

    # TAB: TOTAL STOCK
    with tabs[ti]:
        ti += 1
        st.markdown(f"<div class='section-tag' style='margin-top:20px;'>{t('Total Stock','المخزون الإجمالي')}</div>",
                    unsafe_allow_html=True)
        _ft = display_df(tdf, thr, table_key="total")

        # ── STOCK VALUE BREAKDOWN ─────────────────────────────────────────
        st.markdown(f"<div class='section-tag'>{t('Stock Value by System','قيمة المخزون حسب النظام')}</div>",
                    unsafe_allow_html=True)

        _qc = t("On Hand","متوفر"); _pc = t("Sale Price","سعر البيع"); _sc = t("System","النظام")
        _mc = t("Model Code","رمز الموديل"); _prc = t("Product","المنتج")

        if _qc in tdf.columns and _pc in tdf.columns:
            _ok2  = tdf[tdf["_status"]=="OK"].copy() if "_status" in tdf.columns else tdf.copy()
            _ok2["_qty"]   = pd.to_numeric(_ok2[_qc], errors="coerce").fillna(0)
            _ok2["_price"] = pd.to_numeric(_ok2[_pc], errors="coerce").fillna(0)
            _ok2["_value"] = _ok2["_qty"] * _ok2["_price"]

            # ── per-system value cards ────────────────────────────────────
            if _sc in _ok2.columns:
                _sys_list = sorted(_ok2[_sc].dropna().unique().tolist())
                _cols = st.columns(len(_sys_list)) if _sys_list else []
                for _i, _sn in enumerate(_sys_list):
                    _smask  = _ok2[_sc] == _sn
                    _sval   = _ok2.loc[_smask, "_value"].sum()
                    _sqty   = int(_ok2.loc[_smask, "_qty"].sum())
                    _scount = _smask.sum()
                    _cols[_i].markdown(f"""
                    <div style='background:rgba(74,172,180,0.04);border:1px solid rgba(74,172,180,0.12);
                                border-radius:10px;padding:16px;text-align:center;'>
                      <div style='font-family:Outfit,sans-serif;font-size:8px;letter-spacing:3px;
                                  text-transform:uppercase;color:#4AACB4;margin-bottom:8px;'>{_sn}</div>
                      <div style='font-family:"Cormorant Garamond",serif;font-size:28px;font-weight:300;
                                  color:#fff;line-height:1;margin-bottom:4px;'>
                        {_sval:,.0f}
                      </div>
                      <div style='font-family:Outfit,sans-serif;font-size:9px;letter-spacing:2px;
                                  color:rgba(255,255,255,0.3);margin-bottom:8px;'>SAR</div>
                      <div style='display:flex;justify-content:center;gap:12px;'>
                        <div style='font-family:Outfit,sans-serif;font-size:9px;color:rgba(255,255,255,0.25);'>
                          {_sqty:,} {t("units","وحدة")}
                        </div>
                        <div style='font-family:Outfit,sans-serif;font-size:9px;color:rgba(255,255,255,0.25);'>
                          {_scount} {t("SKUs","صنف")}
                        </div>
                      </div>
                    </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── top 10 models by value ────────────────────────────────────
            st.markdown(f"<div class='section-tag'>{t('Top 10 Models by Stock Value','أعلى 10 موديلات بقيمة المخزون')}</div>",
                        unsafe_allow_html=True)

            _top_cols = [c for c in [_mc, _prc, _sc, "_qty", "_price", "_value"]
                         if c in _ok2.columns]
            _top = (_ok2[_ok2["_qty"]>0][_top_cols]
                    .sort_values("_value", ascending=False)
                    .head(10)
                    .reset_index(drop=True))

            if not _top.empty:
                _display_top = _top.copy()
                _display_top["_qty"]   = _display_top["_qty"].astype(int).map(lambda v: f"{v:,}")
                _display_top["_price"] = _display_top["_price"].map(lambda v: f"{v:.2f} SAR")
                _display_top["_value"] = _display_top["_value"].map(lambda v: f"{v:,.0f} SAR")
                _display_top = _display_top.rename(columns={
                    "_qty"  : t("Qty","الكمية"),
                    "_price": t("Unit Price","سعر الوحدة"),
                    "_value": t("Stock Value","قيمة المخزون"),
                })
                # remove internal cols
                _display_top = _display_top[[c for c in _display_top.columns
                                             if not c.startswith("_")]]

                # render as html table
                _cols_t = _display_top.columns.tolist()
                _th     = "".join(f"<th>{c}</th>" for c in _cols_t)
                def _tr(ir):
                    _, row = ir
                    cells = "".join(
                        f'<td class="cf">{v}</td>' if ci==0 else
                        (f'<td style="color:#D4A84B;font-family:Outfit,monospace;">{v}</td>'
                         if ci == len(row)-1 else f"<td>{v}</td>")
                        for ci,v in enumerate(row))
                    return f"<tr>{cells}</tr>"
                _tbody = "".join(_tr(x) for x in _display_top.iterrows())
                _TABLE_CSS2 = """<style>
.swag-wrap{width:100%;overflow-x:auto;border:1px solid rgba(74,172,180,0.08);border-radius:4px;overflow:hidden;margin-bottom:4px;}
.swag-tbl{width:100%;border-collapse:collapse;font-family:'Outfit','Tajawal',sans-serif;}
.swag-tbl thead tr{background:rgba(74,172,180,0.05);border-bottom:1px solid rgba(74,172,180,0.1);}
.swag-tbl thead th{color:rgba(74,172,180,0.6);font-family:'Outfit',sans-serif;font-size:8px;letter-spacing:3px;text-transform:uppercase;font-weight:400;padding:13px 16px;text-align:center;white-space:nowrap;}
.swag-tbl tbody tr{border-bottom:1px solid rgba(255,255,255,0.03);transition:background 0.15s;}
.swag-tbl tbody tr:hover td{background:rgba(74,172,180,0.03);}
.swag-tbl tbody td{padding:12px 16px;text-align:center;font-size:12px;color:rgba(255,255,255,0.45);}
.swag-tbl tbody td.cf{font-family:'Outfit',monospace;font-size:11px;letter-spacing:0.5px;color:#fff;font-weight:500;border-right:1px solid rgba(74,172,180,0.08);}
</style>"""
                st.markdown(
                    f'{_TABLE_CSS2}<div class="swag-wrap">'
                    f'<table class="swag-tbl"><thead><tr>{_th}</tr></thead>'
                    f'<tbody>{_tbody}</tbody></table></div>',
                    unsafe_allow_html=True)

            # ── total value summary bar ───────────────────────────────────
            _total_val  = _ok2["_value"].sum()
            _zero_val2  = int((_ok2["_qty"]==0).sum())
            _avail_val  = _ok2.loc[_ok2["_qty"]>0,"_value"].sum()

            st.markdown(f"""
            <div style='background:rgba(212,168,75,0.06);border:1px solid rgba(212,168,75,0.2);
                        border-radius:10px;padding:20px 24px;margin-top:16px;
                        display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px;'>
              <div>
                <div style='font-family:Outfit,sans-serif;font-size:8px;letter-spacing:4px;
                            text-transform:uppercase;color:#D4A84B;margin-bottom:6px;'>
                  {t("Total Portfolio Value","إجمالي قيمة المحفظة")}
                </div>
                <div style='font-family:"Cormorant Garamond",serif;font-size:42px;
                            font-weight:300;color:#fff;line-height:1;'>
                  {_total_val:,.0f}
                  <span style='font-size:18px;color:#D4A84B;letter-spacing:2px;'> SAR</span>
                </div>
              </div>
              <div style='display:flex;gap:28px;flex-wrap:wrap;'>
                <div style='text-align:center;'>
                  <div style='font-family:"Cormorant Garamond",serif;font-size:24px;
                              font-weight:300;color:#4AACB4;'>{_avail_val:,.0f}</div>
                  <div style='font-family:Outfit,sans-serif;font-size:8px;letter-spacing:2px;
                              text-transform:uppercase;color:rgba(255,255,255,0.3);margin-top:2px;'>
                    {t("In-Stock Value","قيمة المتوفر")} SAR
                  </div>
                </div>
                <div style='text-align:center;'>
                  <div style='font-family:"Cormorant Garamond",serif;font-size:24px;
                              font-weight:300;color:#D4A84B;'>{_zero_val2}</div>
                  <div style='font-family:Outfit,sans-serif;font-size:8px;letter-spacing:2px;
                              text-transform:uppercase;color:rgba(255,255,255,0.3);margin-top:2px;'>
                    {t("Zero-Stock SKUs","أصناف بلا مخزون")}
                  </div>
                </div>
                <div style='text-align:center;'>
                  <div style='font-family:"Cormorant Garamond",serif;font-size:24px;
                              font-weight:300;color:rgba(255,255,255,0.6);'>
                    {int(_ok2.loc[_ok2["_qty"]>0,"_qty"].sum()):,}
                  </div>
                  <div style='font-family:Outfit,sans-serif;font-size:8px;letter-spacing:2px;
                              text-transform:uppercase;color:rgba(255,255,255,0.3);margin-top:2px;'>
                    {t("Total Units","إجمالي الوحدات")}
                  </div>
                </div>
              </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
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



    # TAB: BRANCH STOCK
    if hb:
        with tabs[ti]:
            ti += 1
            st.markdown(f"<div class='section-tag' style='margin-top:20px;'>{t('Branch-wise Stock','مخزون حسب الفرع')}</div>",
                        unsafe_allow_html=True)
            _fb = display_df(bdf, thr, table_key="branch")
            bc2 = t("Branch","الفرع")
            okb = bdf[bdf["_status"]=="OK"] if "_status" in bdf.columns else bdf
            if not okb.empty and bc2 in okb.columns and qc2 in okb.columns:
                chart = okb.groupby([sc2,bc2])[qc2].sum().reset_index()
                if not chart.empty:
                    st.markdown(f"<div class='section-tag'>{t('Qty by Branch','الكميات حسب الفرع')}</div>",
                                unsafe_allow_html=True)
                    st.bar_chart(chart.set_index(bc2)[qc2], use_container_width=True)
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

    # TAB: TRANSFERS
    if ht:
        with tabs[ti]:
            ti += 1
            st.markdown(f"<div class='section-tag' style='margin-top:20px;'>{t('Pending Transfers','النقليات المعلقة')}</div>",
                        unsafe_allow_html=True)
            okt = trdf[trdf["_status"]=="OK"] if "_status" in trdf.columns else trdf
            if not okt.empty:
                k1,k2,k3 = st.columns(3)
                k1.metric(t("Total","إجمالي"), len(okt))
                qd = t("Qty","الكمية")
                if qd in okt.columns: k2.metric(t("Total Qty","إجمالي الكمية"), int(okt[qd].sum()))
                if sc2 in okt.columns: k3.metric(t("Systems","الأنظمة"), okt[sc2].nunique())
            display_df(trdf, thresh=0, table_key="transfers")
            x1,x2 = st.columns([1,1])
            x1.download_button("CSV ↓", to_csv(trdf), dl_name("transfers","csv"),
                               "text/csv", use_container_width=True)
            x2.download_button("Excel ↓", to_excel(trdf), dl_name("transfers","xlsx"),
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)

    # TAB: REORDER
    if hr:
        with tabs[ti]:
            ti += 1
            CPRI  = t("Priority","الأولوية"); CSUGG = t("Suggest","المقترح")
            st.markdown(f"<div class='section-tag' style='margin-top:20px;'>{t('Reorder Suggestions','اقتراحات إعادة الطلب')}</div>",
                        unsafe_allow_html=True)
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
            o1,o2 = st.columns([1,1])
            o1.download_button("CSV ↓", to_csv(rdf), dl_name("reorder","csv"),
                               "text/csv", use_container_width=True)
            o2.download_button("Excel ↓", to_excel(rdf), dl_name("reorder","xlsx"),
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)

    # TAB: PURCHASE HISTORY
    with tabs[ti]:
        ti += 1
        st.markdown(f"<div class='section-tag' style='margin-top:20px;'>{t('Purchase History','سجل المشتريات')}</div>",
                    unsafe_allow_html=True)

        # System selector — only systems that have purchase orders
        _po_sys_options = {get_system_name(k): k for k in ["SWAG","STOCK"]
                           if st.secrets.get(k)}
        _po_sys_labels  = list(_po_sys_options.keys())
        pf0,pf1,pf2,pf3 = st.columns([1,1.5,1,1])
        with pf0:
            _po_sys_sel = st.selectbox(
                t("System","النظام"),
                options=_po_sys_labels,
                index=0, key="po_sys_sel")
        _po_sys_key = _po_sys_options.get(_po_sys_sel, "SWAG")
        st.markdown(
            f"<div class='info-banner'>"
            f"{t('Purchase orders','أوامر الشراء')}: <b>{_po_sys_sel}</b> — state: purchase / done"
            f"</div>", unsafe_allow_html=True)
        with pf1:
            po_mc = st.text_input(t("Model Code","رمز الموديل"),
                                  placeholder=t("e.g. RVT196 — blank for all","مثال: RVT196"),
                                  key="po_mc").strip()
        df_  = datetime.now().date() - timedelta(days=365)
        dt_  = datetime.now().date()
        with pf2: po_from = st.date_input(t("From","من"), value=df_, key="po_from")
        with pf3: po_to   = st.date_input(t("To","إلى"), value=dt_, key="po_to")
        if st.button(t("Fetch Purchase Analytics","جلب تحليلات المشتريات"),
                     type="primary", key="fetch_po"):
            with st.spinner(t("Fetching...","جلب...")):
                po_df = fetch_swag_purchase_history(
                    model_code=po_mc.upper() if po_mc else None,
                    date_from=po_from.strftime("%Y-%m-%d"),
                    date_to=po_to.strftime("%Y-%m-%d"),
                    system_key=_po_sys_key)
            if po_df is None or po_df.empty:
                st.info(t("No purchases found.","لا توجد مشتريات."))
            else:
                km1,km2,km3,km4 = st.columns(4)
                km1.metric(t("Total Qty","إجمالي الكمية"), f"{float(po_df['Qty'].sum()):,.0f}")
                km2.metric(t("Total Amount","إجمالي المبلغ"), f"{float(po_df['Subtotal'].sum()):,.2f} SAR")
                km3.metric(t("Products","المنتجات"), int(po_df["Model Code"].nunique()))
                km4.metric(t("Vendors","الموردين"), int(po_df["Vendor"].nunique()))
                st.divider()
                st.markdown(f"<div class='section-tag'>{t('Top 10 by Qty','أعلى 10 بالكمية')}</div>",
                            unsafe_allow_html=True)
                pg = (po_df.fillna({"Model Code":"(No Code)","Product":"(No Product)"})
                      .groupby(["Model Code","Product"],as_index=False)["Qty"].sum()
                      .sort_values("Qty",ascending=False).head(10).reset_index(drop=True))
                c1,c2 = st.columns([1.4,1])
                with c1: st.bar_chart(pg.set_index("Model Code")["Qty"], use_container_width=True)
                with c2:
                    pg["Total Qty"] = pg["Qty"].map(lambda v: f"{v:,.0f}")
                    _render_html_table(pg[["Model Code","Product","Total Qty"]])
                st.divider()
                st.markdown(f"<div class='section-tag'>{t('Full Purchase Detail','تفاصيل المشتريات')}</div>",
                            unsafe_allow_html=True)
                sp = po_df.copy()
                sp["Unit Price"] = sp["Unit Price"].map(lambda v: f"{v:.2f} SAR")
                sp["Subtotal"]   = sp["Subtotal"].map(lambda v: f"{v:,.2f} SAR")
                sp["Qty"]        = sp["Qty"].map(lambda v: f"{v:,.0f}")
                _render_html_table(sp)
                st.markdown("<br>", unsafe_allow_html=True)
                dl1,dl2 = st.columns([1,1])
                dl1.download_button("CSV ↓", po_df.to_csv(index=False).encode("utf-8-sig"),
                                    dl_name("purchase","csv"), "text/csv", use_container_width=True)
                dl2.download_button("Excel ↓", to_excel_purchase(po_df),
                                    dl_name("purchase","xlsx"),
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True)

    # TAB: SALES ANALYTICS
    with tabs[ti]:
        ti += 1
        st.markdown(f"<div class='section-tag' style='margin-top:20px;'>{t('Sales Analytics','تحليلات المبيعات')}</div>",
                    unsafe_allow_html=True)

        # System selector
        _so_sys_options = {get_system_name(k): k for k in SYSTEM_KEYS
                           if st.secrets.get(k)}
        _so_sys_labels  = list(_so_sys_options.keys())
        _so_col0, sc1, sc2_, sc3_, sc4_ = st.columns([1,1,1,1.5,0.8])
        with _so_col0:
            _so_sys_sel = st.selectbox(
                t("System","النظام"),
                options=_so_sys_labels,
                index=0, key="so_sys_sel")
        _so_sys_key = _so_sys_options.get(_so_sys_sel, "SWAG")
        st.markdown(
            f"<div class='info-banner'>"
            f"{t('Sales orders','أوامر البيع')}: <b>{_so_sys_sel}</b> — state: sale / done"
            f"</div>", unsafe_allow_html=True)
        _td = datetime.now().date(); _fm = _td.replace(day=1)
        with sc1: so_from = st.date_input(t("From","من"), value=_fm, key="so_from")
        with sc2_: so_to  = st.date_input(t("To","إلى"), value=_td, key="so_to")
        with sc3_:
            so_mc = st.text_input(t("Model Code (optional)","رمز الموديل (اختياري)"),
                                  placeholder=t("e.g. XP6013 — blank for all","مثال: XP6013"),
                                  key="so_mc").strip()
        with sc4_:
            fetch_so = st.button(t("Fetch Sales","جلب المبيعات"),
                                 type="primary", use_container_width=True, key="fetch_so")
        if fetch_so:
            with st.spinner(t("Fetching...","جلب...")):
                _so = fetch_swag_sales_history(
                    model_code=so_mc.upper() if so_mc else None,
                    date_from=so_from.strftime("%Y-%m-%d"),
                    date_to=so_to.strftime("%Y-%m-%d"),
                    system_key=_so_sys_key)
            st.session_state["so_analytics_df"] = _so

        so_df = st.session_state.get("so_analytics_df")
        if so_df is None or (isinstance(so_df,pd.DataFrame) and so_df.empty):
            _so_msg = t("Click 'Fetch Sales' to load.", "اضغط 'جلب المبيعات' لتحميل البيانات.")
            st.markdown(f"<div class='info-banner'>{_so_msg}</div>",
                        unsafe_allow_html=True)
        else:
            sk1,sk2,sk3,sk4 = st.columns(4)
            sk1.metric(t("Total Qty Sold","إجمالي الكمية"), f"{float(so_df['Qty'].sum()):,.0f}")
            sk2.metric(t("Total Revenue","إجمالي الإيراد"), f"{float(so_df['Subtotal'].sum()):,.2f} SAR")
            sk3.metric(t("Customers","العملاء"), int(so_df["Customer"].nunique()))
            sk4.metric(t("Products","المنتجات"), int(so_df["Model Code"].nunique()))
            st.divider()

            def _at(df_t):
                cols_t = df_t.columns.tolist()
                th_t   = "".join(f"<th>{c}</th>" for c in cols_t)
                def _tr(ir):
                    _,row = ir
                    cells = "".join(
                        f'<td class="cf">{v}</td>' if ci==0 else f"<td>{v}</td>"
                        for ci,v in enumerate(row))
                    return f"<tr>{cells}</tr>"
                tbody_t = "".join(_tr(x) for x in df_t.iterrows())
                st.markdown(
                    f'{_TABLE_CSS}<div class="swag-wrap">'
                    f'<table class="swag-tbl"><thead><tr>{th_t}</tr></thead>'
                    f'<tbody>{tbody_t}</tbody></table></div>', unsafe_allow_html=True)

            st.markdown(f"<div class='section-tag'>{t('Top 10 by Qty Sold','أعلى 10 بالكمية')}</div>",
                        unsafe_allow_html=True)
            pqg = (so_df.fillna({"Model Code":"(No Code)","Product":"(No Product)"})
                   .groupby(["Model Code","Product"],as_index=False)["Qty"].sum()
                   .sort_values("Qty",ascending=False).head(10).reset_index(drop=True))
            pqg["Total Qty"] = pqg["Qty"].map(lambda v: f"{v:,.0f}")
            s1,s2 = st.columns([1.4,1])
            with s1: st.bar_chart(pqg.set_index("Model Code")["Qty"], use_container_width=True)
            with s2: _at(pqg[["Model Code","Product","Total Qty"]])

            st.divider()
            st.markdown(f"<div class='section-tag'>{t('Top 10 by Revenue','أعلى 10 بالإيراد')}</div>",
                        unsafe_allow_html=True)
            prg = (so_df.fillna({"Model Code":"(No Code)","Product":"(No Product)"})
                   .groupby(["Model Code","Product"],as_index=False)["Subtotal"].sum()
                   .sort_values("Subtotal",ascending=False).head(10).reset_index(drop=True))
            prg["Revenue (SAR)"] = prg["Subtotal"].map(lambda v: f"{v:,.2f}")
            r1,r2 = st.columns([1.4,1])
            with r1: st.bar_chart(prg.set_index("Model Code")["Subtotal"], use_container_width=True)
            with r2: _at(prg[["Model Code","Product","Revenue (SAR)"]])

            st.divider()
            st.markdown(f"<div class='section-tag'>{t('Branch Performance','أداء الفروع')}</div>",
                        unsafe_allow_html=True)
            bg = (so_df.fillna({"Branch":"Unknown"})
                  .groupby("Branch",as_index=False)
                  .agg(Qty=("Qty","sum"),Subtotal=("Subtotal","sum"))
                  .sort_values("Qty",ascending=False).head(10).reset_index(drop=True))
            bx1,bx2 = st.columns(2)
            with bx1: st.bar_chart(bg.set_index("Branch")["Qty"], use_container_width=True)
            with bx2: st.bar_chart(bg.set_index("Branch")["Subtotal"], use_container_width=True)

            st.divider()
            st.markdown(f"<div class='section-tag'>{t('Daily Sales Trend','اتجاه المبيعات اليومي')}</div>",
                        unsafe_allow_html=True)
            td = so_df.copy()
            td["Date"] = pd.to_datetime(td["Date"],errors="coerce")
            td = td.dropna(subset=["Date"])
            if not td.empty:
                daily = (td.groupby(td["Date"].dt.date,as_index=False)
                         .agg(Qty=("Qty","sum"),Revenue=("Subtotal","sum"))
                         .sort_values("date" if "date" in td.columns else "Date")
                         .set_index(td.groupby(td["Date"].dt.date,as_index=False)
                                    .agg(Qty=("Qty","sum"),Revenue=("Subtotal","sum")).columns[0]))
                st.line_chart(daily[["Qty","Revenue"]], use_container_width=True)

            st.divider()
            st.markdown(f"<div class='section-tag'>{t('Full Sales Detail','تفاصيل المبيعات')}</div>",
                        unsafe_allow_html=True)
            ss2 = so_df.copy()
            ss2["Date"]       = ss2["Date"].astype(str).str[:10]
            ss2["Unit Price"] = ss2["Unit Price"].map(lambda v: f"{v:.2f} SAR")
            ss2["Subtotal"]   = ss2["Subtotal"].map(lambda v: f"{v:,.2f} SAR")
            ss2["Qty"]        = ss2["Qty"].map(lambda v: f"{v:,.0f}")
            _render_html_table(ss2)
            st.markdown("<br>", unsafe_allow_html=True)
            sdl1,sdl2 = st.columns([1,1])
            sdl1.download_button("CSV ↓",
                so_df.assign(Date=so_df["Date"].astype(str).str[:10])
                    .to_csv(index=False).encode("utf-8-sig"),
                dl_name("sales","csv"), "text/csv",
                use_container_width=True, key="so_csv_dl")
            sdl2.download_button("Excel ↓",
                to_excel_sales(so_df), dl_name("sales","xlsx"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True, key="so_excel_dl")


    # TAB: DEAD STOCK FINDER
    with tabs[ti]:
        ti += 1

        st.markdown(
            f"<div class='section-tag' style='margin-top:20px;'>"
            f"{t('Dead Stock Finder','كاشف المخزون الراكد')}</div>",
            unsafe_allow_html=True)

        # ── System selector ───────────────────────────────────────────────
        _ds_sys_options = {get_system_name(k): k for k in SYSTEM_KEYS
                           if st.secrets.get(k)}
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

        # ── Settings ─────────────────────────────────────────────────────
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

        # ── Results ───────────────────────────────────────────────────────
        if st.session_state.get("ds_trigger"):
            _ds_days = st.session_state["ds_trigger"]

            with st.spinner(
                t(f"Scanning {_ds_sys_sel} stock & sale history (threshold: {_ds_days} days)...",
                  f"فحص مخزون {_ds_sys_sel} وتاريخ المبيعات (الحد: {_ds_days} يوم)...")):
                ds_df = fetch_dead_stock(threshold_days=_ds_days, system_key=_ds_sys_key)

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

                # ── Summary metrics ───────────────────────────────────────
                dm1,dm2,dm3,dm4 = st.columns(4)
                dm1.metric(
                    t("Total Dead SKUs","إجمالي الأصناف الراكدة"),
                    len(ds_df))
                dm2.metric(
                    t("Never Sold","لم يُباع قط"),
                    len(_never))
                dm3.metric(
                    t(f"No Sale {_ds_days}+ Days",f"لا بيع {_ds_days}+ يوم"),
                    len(_dead))
                dm4.metric(
                    t("Total Units Frozen","إجمالي الوحدات المجمدة"),
                    f"{int(_total_units):,}")

                # ── Frozen value banner ───────────────────────────────────
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

                # ── Filter tabs ───────────────────────────────────────────
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
                    # ── Category filter ───────────────────────────────────
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

                    # ── Render table ──────────────────────────────────────
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

                    # ── Excel Export ──────────────────────────────────────
                    st.markdown("<br>", unsafe_allow_html=True)
                    _export_df = _show_df.copy()
                    _export_df["Days Since Sale"] = _export_df["Days Since Sale"].apply(
                        lambda v: "Never" if v == 99999 else int(v))
                    ex1, ex2 = st.columns([1, 3])
                    ex1.download_button(
                        t("Export Excel ↓","تصدير Excel ↓"),
                        _excel_generic(
                            _export_df,
                            t("Dead Stock","المخزون الراكد")),
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


    # TAB: BARCODE SCANNER
    with tabs[ti]:
        ti += 1

        st.markdown(
            f"<div class='section-tag' style='margin-top:20px;'>"
            f"{t('Barcode Scanner','ماسح الباركود')}</div>",
            unsafe_allow_html=True)

        # ── HOW IT WORKS ──────────────────────────────────────────────────
        st.markdown(f"""
        <div style='background:rgba(74,172,180,0.04);border:1px solid rgba(74,172,180,0.15);
                    border-radius:12px;padding:20px 24px;margin-bottom:16px;'>
          <div style='font-family:Outfit,sans-serif;font-size:8px;letter-spacing:4px;
                      text-transform:uppercase;color:#4AACB4;margin-bottom:14px;'>
            {t("How it works","كيف يعمل")}
          </div>
          <div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;'>
            <div style='text-align:center;'>
              <div style='font-size:28px;margin-bottom:6px;'>📷</div>
              <div style='font-family:Outfit,sans-serif;font-size:10px;font-weight:600;
                          color:#fff;margin-bottom:3px;'>{t("Step 1","الخطوة 1")}</div>
              <div style='font-family:Outfit,sans-serif;font-size:10px;
                          color:rgba(255,255,255,0.35);'>
                {t("Open phone camera or scanner app","افتح كاميرا الجوال أو تطبيق الماسح")}
              </div>
            </div>
            <div style='text-align:center;'>
              <div style='font-size:28px;margin-bottom:6px;'>🔍</div>
              <div style='font-family:Outfit,sans-serif;font-size:10px;font-weight:600;
                          color:#fff;margin-bottom:3px;'>{t("Step 2","الخطوة 2")}</div>
              <div style='font-family:Outfit,sans-serif;font-size:10px;
                          color:rgba(255,255,255,0.35);'>
                {t("Scan the product barcode","امسح باركود المنتج")}
              </div>
            </div>
            <div style='text-align:center;'>
              <div style='font-size:28px;margin-bottom:6px;'>📋</div>
              <div style='font-family:Outfit,sans-serif;font-size:10px;font-weight:600;
                          color:#fff;margin-bottom:3px;'>{t("Step 3","الخطوة 3")}</div>
              <div style='font-family:Outfit,sans-serif;font-size:10px;
                          color:rgba(255,255,255,0.35);'>
                {t("Paste code below & search","الصق الرمز أدناه وابحث")}
              </div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

        # ── WHY NO IN-APP CAMERA ──────────────────────────────────────────
        st.markdown(f"""
        <div class='warn-banner'>
          <b>{t("Note:","ملاحظة:")}</b>
          {t(
            "Browser security blocks camera access inside embedded iframes (which Streamlit uses). Use your phone's built-in camera or any QR/barcode scanner app — they automatically copy the code to clipboard.",
            "أمان المتصفح يمنع الوصول للكاميرا داخل الإطارات المضمنة. استخدم كاميرا هاتفك المدمجة أو أي تطبيق ماسح — فهي تنسخ الرمز تلقائياً للحافظة."
          )}
        </div>""", unsafe_allow_html=True)

        # ── SCANNER APPS SUGGESTION ───────────────────────────────────────
        st.markdown(f"<div class='section-tag'>{t('Recommended Scanner Apps','تطبيقات الماسح المقترحة')}</div>",
                    unsafe_allow_html=True)

        a1, a2, a3 = st.columns(3)
        with a1:
            st.markdown(f"""
            <div style='background:rgba(74,172,180,0.04);border:1px solid rgba(74,172,180,0.12);
                        border-radius:10px;padding:14px;text-align:center;'>
              <div style='font-size:24px;margin-bottom:6px;'>📱</div>
              <div style='font-family:Outfit,sans-serif;font-size:11px;font-weight:600;
                          color:#fff;margin-bottom:3px;'>iPhone Camera</div>
              <div style='font-family:Outfit,sans-serif;font-size:10px;
                          color:rgba(255,255,255,0.3);'>
                {t("Built-in — just open camera","مدمج — افتح الكاميرا فقط")}
              </div>
            </div>""", unsafe_allow_html=True)
        with a2:
            st.markdown(f"""
            <div style='background:rgba(74,172,180,0.04);border:1px solid rgba(74,172,180,0.12);
                        border-radius:10px;padding:14px;text-align:center;'>
              <div style='font-size:24px;margin-bottom:6px;'>🤖</div>
              <div style='font-family:Outfit,sans-serif;font-size:11px;font-weight:600;
                          color:#fff;margin-bottom:3px;'>Google Lens</div>
              <div style='font-family:Outfit,sans-serif;font-size:10px;
                          color:rgba(255,255,255,0.3);'>
                {t("Android — long press home","أندرويد — اضغط مطولاً")}
              </div>
            </div>""", unsafe_allow_html=True)
        with a3:
            st.markdown(f"""
            <div style='background:rgba(74,172,180,0.04);border:1px solid rgba(74,172,180,0.12);
                        border-radius:10px;padding:14px;text-align:center;'>
              <div style='font-size:24px;margin-bottom:6px;'>⚡</div>
              <div style='font-family:Outfit,sans-serif;font-size:11px;font-weight:600;
                          color:#fff;margin-bottom:3px;'>QR & Barcode Scanner</div>
              <div style='font-family:Outfit,sans-serif;font-size:10px;
                          color:rgba(255,255,255,0.3);'>
                {t("Free app — App Store / Play","مجاني — متجر التطبيقات")}
              </div>
            </div>""", unsafe_allow_html=True)

        st.divider()

        # ── SEARCH BOX ────────────────────────────────────────────────────
        st.markdown(
            f"<div class='section-tag'>"
            f"{t('Paste Code & Search All 4 Systems','الصق الرمز وابحث في 4 أنظمة')}</div>",
            unsafe_allow_html=True)

        mc1, mc2 = st.columns([3, 1])
        with mc1:
            manual_code = st.text_input(
                t("Paste barcode number or model code here",
                  "الصق رقم الباركود أو رمز الموديل هنا"),
                placeholder=t(
                    "e.g.  6281234567890   or   XP6013-M",
                    "مثال:  6281234567890   أو   XP6013-M"),
                key="bc_manual_input"
            ).strip().upper()
        with mc2:
            st.markdown("<br>", unsafe_allow_html=True)
            manual_go = st.button(
                t("Search →","بحث →"),
                type="primary", use_container_width=True, key="bc_manual_go")

        if manual_go and manual_code:
            st.session_state["bc_trigger_search"] = manual_code
            st.rerun()

        # ── RESULTS ───────────────────────────────────────────────────────
        if st.session_state.get("bc_trigger_search"):
            bc_code = st.session_state.pop("bc_trigger_search")
            st.markdown(
                f"<div class='section-tag'>"
                f"{t('Result for','نتيجة لـ')}: <span class='mono'>{bc_code}</span></div>",
                unsafe_allow_html=True)

            with st.spinner(t("Fetching from 4 systems...","جلب من 4 أنظمة...")):
                bc_data = fetch_all_data(
                    (bc_code,), exact=False,
                    target_days=st.session_state.reorder_target_days,
                    reorder_point=st.session_state.reorder_point)

            bc_tdf = prepare_df(bc_data["total"])

            if bc_tdf is not None and not bc_tdf.empty:
                qcc   = t("On Hand","متوفر")
                pcc   = t("Sale Price","سعر البيع")
                bc_ok = bc_tdf[bc_tdf["_status"]=="OK"] if "_status" in bc_tdf.columns else bc_tdf

                r1, r2, r3 = st.columns(3)
                r1.metric(t("Results","النتائج"), len(bc_tdf))
                if qcc in bc_ok.columns:
                    r2.metric(t("Total Qty","إجمالي الكمية"),
                              int(pd.to_numeric(bc_ok[qcc],errors="coerce").fillna(0).sum()))
                if pcc in bc_ok.columns:
                    vp = pd.to_numeric(bc_ok[pcc],errors="coerce")
                    r3.metric(t("Avg Price","متوسط السعر"),
                              f"{vp[vp>0].mean():.2f} SAR" if not vp[vp>0].empty else "—")

                display_df(bc_tdf,
                           thresh=st.session_state.low_stock_thresh,
                           table_key="bc_result")

                st.download_button(
                    t("Export Excel ↓","تصدير Excel ↓"),
                    to_excel(bc_tdf),
                    dl_name(f"bc_{bc_code}","xlsx"),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="bc_excel_dl")
            else:
                st.markdown(
                    f"<div class='warn-banner'>"
                    f"{t('No results found for','لا نتائج لـ')} "
                    f"<span class='mono'>{bc_code}</span>. "
                    f"{t('Try exact match mode in sidebar.','جرب وضع التطابق التام من الشريط الجانبي.')}"
                    f"</div>",
                    unsafe_allow_html=True)

        # ── SUPPORTED BARCODES ────────────────────────────────────────────
        st.divider()
        st.markdown(f"<div class='section-tag'>{t('Supported Barcode Types','أنواع الباركود المدعومة')}</div>",
                    unsafe_allow_html=True)
        st.markdown(f"""
        <div style='display:grid;grid-template-columns:repeat(3,1fr);gap:8px;'>
          {''.join([
            f"<div style='background:rgba(74,172,180,0.04);border:1px solid rgba(74,172,180,0.1);"
            f"border-radius:8px;padding:10px 12px;font-family:Outfit,monospace;font-size:11px;"
            f"color:rgba(255,255,255,0.5);text-align:center;'>{b}</div>"
            for b in ["EAN-13","EAN-8","Code 128","Code 39","UPC-A","UPC-E"]
          ])}
        </div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
restore_session()
if not st.session_state.authenticated:
    show_login()
else:
    show_dashboard()
