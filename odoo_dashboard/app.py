## What Was Repaired

1. **OCR corruption** in Arabic string literals (malformed quotes, broken parentheses, reversed characters)
2. **Broken f-strings** with mismatched braces and Arabic mixed inside
3. **Syntax errors** in `translate_system_names` — unclosed parenthesis in `t("System", "النظام("`
4. **`_render_html_table`** had `</table>` inside a `<td>` tag
5. **`display_df` caption** had broken f-string
6. **`_style_worksheet`** had a list `['']` inside an `or` expression
7. **`_COL_AR` dict** had misplaced comma and broken key order
8. **`to_excel`/`to_excel_bulk`** had unterminated Arabic string fragments
9. **`to_excel_branch_matrix`** had semicolons used as statement separators in wrong places
10. **Added complete Season Comparison feature** as requested (new tab, auto-fetch seasons, company-wise matrix, Excel export)

---

```python
"""
SWAG Product Comparison Dashboard
Version 5.0 — Ultra Premium Dark Design · Season/Company/Category Comparisons
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

# ─── SEASON FIELD CONFIGURATION ───────────────────────────────────────────────
# Try these fields in order on product.template; first one that returns data wins
SEASON_FIELD_CANDIDATES = [
    "x_studio_season",
    "x_studio_season_name",
    "season_id",
    "x_season",
    "x_studio_field_season",
]
# ──────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;1,300&family=Tajawal:wght@300;400;700&family=Outfit:wght@300;400;500;600&display=swap');
*,html,body,[class*="css"]{font-family:'Outfit','Tajawal',sans-serif;box-sizing:border-box;}
.stApp{background:#060d0e !important;}
.stApp > header{background:transparent !important;}
.block-container{padding-top:0 !important;padding-bottom:0 !important;max-width:100% !important;}
.main .block-container{padding:0 !important;}
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
.stTextInput label,.stNumberInput label,.stTextArea label,
.stSelectbox label,.stMultiSelect label{
    font-family:'Outfit',sans-serif !important;
    font-size:8px !important;letter-spacing:3px !important;
    text-transform:uppercase !important;color:rgba(74,172,180,0.7) !important;
    font-weight:400 !important;
}
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
.stButton button{
    font-family:'Outfit',sans-serif !important;
    font-size:9px !important;letter-spacing:2px !important;
    text-transform:uppercase !important;border-radius:100px !important;
    transition:all 0.2s !important;
}
.stButton button[kind="primary"],.stFormSubmitButton button{
    background:#4AACB4 !important;color:#060d0e !important;
    border:none !important;font-weight:600 !important;
    padding:10px 28px !important;border-radius:100px !important;
}
.stButton button[kind="primary"]:hover,.stFormSubmitButton button:hover{
    background:#2E8A91 !important;transform:translateY(-1px) !important;
}
.stButton button[kind="secondary"]{
    background:transparent !important;color:rgba(74,172,180,0.6) !important;
    border:1px solid rgba(74,172,180,0.2) !important;border-radius:100px !important;
}
.stButton button[kind="secondary"]:hover{
    border-color:#4AACB4 !important;color:#4AACB4 !important;
}
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
.stToggle label,.stCheckbox label,.stRadio label,
div[data-testid="stRadio"] p{
    color:rgba(255,255,255,0.5) !important;
    font-family:'Outfit',sans-serif !important;
    font-size:9px !important;letter-spacing:2px !important;
    text-transform:uppercase !important;
}
[data-testid="stToggle"] span[data-checked="true"]{background:#4AACB4 !important;}
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
[data-testid="stProgressBar"]>div{
    background:linear-gradient(90deg,#4AACB4,#D4A84B) !important;
    border-radius:0 !important;
}
[data-testid="stProgressBar"]{
    background:rgba(74,172,180,0.08) !important;
    border-radius:0 !important;height:1px !important;
}
[data-testid="stSlider"] label{
    color:rgba(74,172,180,0.7) !important;
    font-family:'Outfit',sans-serif !important;
    font-size:8px !important;letter-spacing:3px !important;
    text-transform:uppercase !important;
}
hr{
    border:none !important;height:1px !important;
    background:rgba(74,172,180,0.08) !important;
    margin:20px 0 !important;
}
.stCaption,[data-testid="stCaptionContainer"] p{
    color:rgba(255,255,255,0.15) !important;
    font-family:'Outfit',sans-serif !important;
    font-size:8px !important;letter-spacing:2px !important;
}
h1,h2,h3,h4,h5,h6{color:#fff !important;font-family:'Tajawal',sans-serif !important;}
.stMarkdown p,.stMarkdown li{color:rgba(255,255,255,0.5) !important;}
p,div,span,label{color:rgba(255,255,255,0.5);}
.stNumberInput button{
    color:#4AACB4 !important;
    background:rgba(74,172,180,0.06) !important;
    border-color:rgba(74,172,180,0.1) !important;
}
::-webkit-scrollbar{width:2px;height:2px;}
::-webkit-scrollbar-track{background:#060d0e;}
::-webkit-scrollbar-thumb{background:#4AACB4;border-radius:0;}
.hero-section{
    padding:48px 0 36px;
    border-bottom:1px solid rgba(74,172,180,0.08);
    position:relative;overflow:hidden;
}
.hero-glow{
    position:absolute;left:-150px;top:-150px;
    width:500px;height:500px;border-radius:50%;
    background:rgba(74,172,180,0.05);
    filter:blur(100px);pointer-events:none;z-index:0;
}
.hero-gold-glow{
    position:absolute;right:50px;bottom:-100px;
    width:350px;height:350px;border-radius:50%;
    background:rgba(212,168,75,0.03);
    filter:blur(80px);pointer-events:none;z-index:0;
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

# TABLE CSS
_TABLE_CSS = """<style>
.swag-wrap{width:100%;overflow-x:auto;border:1px solid rgba(74,172,180,0.08);border-radius:4px;margin-bottom:4px;}
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
.swag-tbl tbody td.zero-cell{color:rgba(212,168,75,0.6);font-size:11px;}
.swag-tbl tbody td.qty-cell{color:#4AACB4;font-weight:500;}
.swag-tbl tbody td.price-cell{color:rgba(255,255,255,0.6);}
.swag-tbl tbody td.total-cell{color:#D4A84B;font-weight:600;border-left:1px solid rgba(74,172,180,0.1);}
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
    "season_cache": {},
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
_KEY_ALIASES = {
    "FASHION_LIMITS": "FASHIONLIMITS",
    "FASHIONLIMITS": "FASHIONLIMITS",
}

def _canonical_key(key):
    return _KEY_ALIASES.get(key, key)

def get_system_config(key):
    canonical = _canonical_key(key)
    cfg = st.secrets.get(canonical) or st.secrets.get(key)
    if not cfg:
        return None
    cfg = dict(cfg)
    url = str(cfg.get("url", "")).rstrip("/")
    if url.endswith("/odoo"):
        url = url[:-len("/odoo")]
    cfg["url"] = url
    return cfg

@st.cache_resource
def _proxy(url, ep):
    return xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/{ep}", allow_none=True)

@st.cache_data(ttl=28800, show_spinner=False)
def _auth(url, db, user, api_key):
    try:
        uid = _proxy(url, "common").authenticate(db, user, api_key, {})
        if uid:
            return {"ok": True, "uid": uid}
        return {"ok": False, "error": "BAD_CREDENTIALS: uid=False"}
    except ConnectionRefusedError as e:
        return {"ok": False, "error": f"NO_RESPONSE: {e}"}
    except Exception as e:
        return {"ok": False, "error": f"AUTH_EXCEPTION: {e}"}

def _auth_uid(url, db, user, api_key):
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
    'SR', 'VAT', 'TAX', 'PCS', 'QTY', 'NO', 'REF', 'INV', 'PO', 'SO',
    'DO', 'ID', 'EN', 'AR', 'PDF', 'AED', 'SAR', 'USD', 'KWD', 'OMR',
    'BHD', 'JOD', 'EGP', 'TRY'
])

def _valid(code):
    c = code.strip().upper()
    return (bool(re.search(r'[A-Z]', c)) and bool(re.search(r'\d', c))
            and 4 <= len(c) <= 25 and c not in _EXCLUDE)

def extract_base_model(code):
    code = re.sub(r'\([^)]*\)', '', code)
    for s in ['-2XL', '-3XL', '-4XL', '-XXL', '-XL', '-L', '-M', '-S', '-XS', '-2X', '-3X']:
        if code.upper().endswith(s.upper()):
            code = code[:-len(s)]
            break
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

    hdr_fill = PatternFill("solid", fgColor="060D0E")
    hdr_font = Font(bold=True, color="4AACB4", size=11, name="Calibri")
    hdr_align = Alignment(horizontal="center", vertical="center")
    thin = Side(border_style="thin", color="1A2A2C")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    alt_fill = PatternFill("solid", fgColor="0D1A1C")
    zero_fill = PatternFill("solid", fgColor="1C1000")
    zero_font = Font(color="D4A84B", bold=True, name="Calibri")
    norm_font = Font(name="Calibri", size=10, color="8AACB0")
    num_align = Alignment(horizontal="right", vertical="center")
    ctr_align = Alignment(horizontal="center", vertical="center")
    tot_fill = PatternFill("solid", fgColor="060D0E")
    tot_font = Font(bold=True, name="Calibri", color="4AACB4")

    max_row = ws.max_row
    max_col = ws.max_column
    ws.row_dimensions[1].height = 28

    for col_num in range(1, max_col + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = hdr_fill
        cell.font = hdr_font
        cell.alignment = hdr_align
        cell.border = border

    col_names = [ws.cell(row=1, column=c).value for c in range(1, max_col + 1)]
    on_hand_col = None
    for i, name in enumerate(col_names, 1):
        if name in ("On Hand", "متوفر"):
            on_hand_col = i

    for row in ws.iter_rows(min_row=2, max_row=max_row):
        is_zero = False
        if on_hand_col:
            val = ws.cell(row=row[0].row, column=on_hand_col).value
            is_zero = (val is None or
                       str(val).strip() in ['0', 'Not Available', '—', '-', ''] or
                       val == 0)
        for cell in row:
            cell.border = border
            cell.font = zero_font if is_zero else norm_font
            if is_zero:
                cell.fill = zero_fill
            elif cell.row % 2 == 0:
                cell.fill = alt_fill
            cell.alignment = num_align if isinstance(cell.value, (int, float)) else ctr_align
        ws.row_dimensions[row[0].row].height = 18

    for col_num in range(1, max_col + 1):
        col_letter = get_column_letter(col_num)
        max_len = 0
        for r in ws.iter_rows(min_col=col_num, max_col=col_num):
            for cell in r:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(max_col)}{max_row}"

    if on_hand_col and max_row > 1:
        col_letter = get_column_letter(on_hand_col)
        ws.conditional_formatting.add(
            f"{col_letter}2:{col_letter}{max_row}",
            DataBarRule(start_type="min", end_type="max", color="4AACB4"))

    total_row = max_row + 1
    tc = ws.cell(row=total_row, column=1, value="TOTAL")
    tc.font = tot_font
    tc.fill = tot_fill
    tc.alignment = ctr_align

    if on_hand_col:
        col = get_column_letter(on_hand_col)
        tc2 = ws.cell(row=total_row, column=on_hand_col,
                      value=f"=SUM({col}2:{col}{max_row})")
        tc2.font = tot_font
        tc2.fill = tot_fill
        tc2.alignment = ctr_align

    ws.row_dimensions[total_row].height = 20
    ws.sheet_properties.tabColor = "4AACB4"

    footer_row = total_row + 2
    fc = ws.cell(row=footer_row, column=1,
                 value=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | SWAG Dashboard")
    fc.font = Font(italic=True, color="4AACB4", size=9, name="Calibri")
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.print_title_rows = "1:1"
    ws.sheet_view.zoomScale = 85

def to_csv(df):
    return df.drop(columns=["_status"], errors="ignore").to_csv(index=False).encode("utf-8-sig")

def to_excel(df):
    lang = st.session_state.get('lang', 'EN')
    buf = io.BytesIO()
    clean = df.drop(columns=['_status'], errors='ignore').copy()
    oh = 'On Hand' if 'On Hand' in clean.columns else ('متوفر' if 'متوفر' in clean.columns else None)
    if oh:
        na = 'غير متوفر' if lang == 'AR' else 'Not Available'
        clean[oh] = clean[oh].apply(
            lambda x: na if (pd.isna(x) or str(x).strip() in ['0', '']) or x == 0 else x)
    desired = [
        t("Model Code", "رمز الموديل"), t("System", "النظام"),
        t("Branch", "الفرع"), t("Location", "الموقع"),
        t("Sale Price", "سعر البيع"), t("On Hand", "متوفر")
    ]
    ordered = [c for c in desired if c in clean.columns]
    remaining = [c for c in clean.columns if c not in ordered]
    clean = clean[ordered + remaining]
    with pd.ExcelWriter(buf, engine='openpyxl') as w:
        clean.to_excel(w, index=False, sheet_name='Data')
        _style_worksheet(w.sheets['Data'], clean, lang=lang)
    return buf.getvalue()

def to_excel_bulk(df):
    lang = st.session_state.get("lang", "EN")
    buf = io.BytesIO()
    sys_col = t("System", "النظام")
    desired = [
        t("Model Code", "رمز الموديل"), t("System", "النظام"),
        t("Branch", "الفرع"), t("Location", "الموقع"),
        t("Sale Price", "سعر البيع"), t("On Hand", "متوفر")
    ]
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        def _ws(data, name):
            c = data.drop(columns=["_status"], errors="ignore").copy()
            oh = t("On Hand", "متوفر")
            if oh in c.columns:
                na = 'غير متوفر' if lang == 'AR' else 'Not Available'
                c[oh] = c[oh].apply(
                    lambda x: na if (pd.isna(x) or str(x).strip() in ['0', '']) or x == 0 else x)
            ordered = [col for col in desired if col in c.columns]
            remaining = [col for col in c.columns if col not in ordered]
            c = c[ordered + remaining]
            c.to_excel(w, index=False, sheet_name=name[:31])
            _style_worksheet(w.sheets[name[:31]], c, lang=lang)

        _ws(df, t("All Systems", "كل الأنظمة"))
        if sys_col in df.columns:
            for key in SYSTEM_KEYS:
                nm = get_system_name(key)
                sub = df[df[sys_col] == nm]
                if not sub.empty:
                    _ws(sub, nm[:31])
    return buf.getvalue()

def _excel_generic(df, sheet_name, hdr_color="060D0E", hdr_txt="4AACB4"):
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    buf = io.BytesIO()
    clean = df.copy()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        clean.to_excel(w, index=False, sheet_name=sheet_name)
        ws = w.sheets[sheet_name]
        hfill = PatternFill("solid", fgColor=hdr_color)
        hfont = Font(bold=True, color=hdr_txt, size=11, name="Calibri")
        halign = Alignment(horizontal="center", vertical="center")
        thin = Side(border_style="thin", color="1A2A2C")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        afill = PatternFill("solid", fgColor="0D1A1C")
        nfont = Font(name="Calibri", size=10, color="8AACB0")
        num_a = Alignment(horizontal="right", vertical="center")
        ctr_a = Alignment(horizontal="center", vertical="center")
        tfill = PatternFill("solid", fgColor="060D0E")
        tfont = Font(bold=True, name="Calibri", color="D4A84B")
        mr, mc = ws.max_row, ws.max_column
        ws.row_dimensions[1].height = 28
        for c in range(1, mc + 1):
            cell = ws.cell(row=1, column=c)
            cell.fill = hfill
            cell.font = hfont
            cell.alignment = halign
            cell.border = border
        for row in ws.iter_rows(min_row=2, max_row=mr):
            for cell in row:
                cell.border = border
                cell.font = nfont
                if cell.row % 2 == 0:
                    cell.fill = afill
                cell.alignment = num_a if isinstance(cell.value, (int, float)) else ctr_a
            ws.row_dimensions[row[0].row].height = 18
        for c in range(1, mc + 1):
            cl = get_column_letter(c)
            ml = max(
                (len(str(ws.cell(row=r, column=c).value or "")) for r in range(1, mr + 1)),
                default=8
            )
            ws.column_dimensions[cl].width = min(max(ml + 3, 12), 50)
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(mc)}{mr}"
        tr = mr + 1
        tc = ws.cell(row=tr, column=1, value="TOTAL")
        tc.font = tfont
        tc.fill = tfill
        tc.alignment = ctr_a
        cnames = [ws.cell(row=1, column=c).value for c in range(1, mc + 1)]
        for cn in ("Qty", "Subtotal"):
            if cn in cnames:
                ci = cnames.index(cn) + 1
                cl = get_column_letter(ci)
                tc2 = ws.cell(row=tr, column=ci, value=f"=SUM({cl}2:{cl}{mr})")
                tc2.font = tfont
                tc2.fill = tfill
                tc2.alignment = ctr_a
        ws.sheet_properties.tabColor = "4AACB4"
    return buf.getvalue()

def dl_name(tag, ext):
    return f"swag_{tag}_{datetime.now().strftime('%Y%m%d_%H%M')}.{ext}"

# ─────────────────────────────────────────────────────────────────────────────
# PURCHASE SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def get_purchase_summary_by_model(model_codes_tuple, date_from, date_to, system_key="SWAG"):
    empty = pd.DataFrame(columns=["Model Code", "Purchase Qty"])
    cfg = get_system_config(system_key)
    if not cfg:
        return empty
    ar = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not ar["ok"]:
        return empty
    uid = ar["uid"]
    u = cfg["url"]
    db = cfg["db"]
    ak = cfg["api_key"]
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
        if not lines:
            return empty
        pids = list({l["product_id"][0] for l in lines if isinstance(l.get("product_id"), list)})
        prods = _x(u, db, uid, ak, "product.product", "search_read",
                   [[["id", "in", pids]]],
                   {"fields": ["id", "default_code"], "limit": len(pids) + 10})
        pmap = {p["id"]: p for p in prods}
        agg = {}
        for line in lines:
            pid = line["product_id"][0] if isinstance(line.get("product_id"), list) else None
            mc = pmap.get(pid, {}).get("default_code", "").strip()
            if not mc:
                continue
            agg[mc] = agg.get(mc, 0) + float(line.get("product_qty") or 0)
        if not agg:
            return empty
        df = pd.DataFrame([{"Model Code": mc, "Purchase Qty": qty} for mc, qty in agg.items()])
        return df.groupby("Model Code", as_index=False)["Purchase Qty"].sum()
    except Exception:
        return empty

# ─────────────────────────────────────────────────────────────────────────────
# SALES HISTORY
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_swag_sales_history(model_code=None, date_from=None, date_to=None, system_key="SWAG"):
    empty = pd.DataFrame(columns=[
        "Date", "SO", "Customer", "Branch", "Brand Category", "Category",
        "Model Code", "Product", "Qty", "Unit Price", "Subtotal"])
    cfg = get_system_config(system_key)
    if not cfg:
        return empty
    ar = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not ar["ok"]:
        return empty
    uid = ar["uid"]
    u, db, ak = cfg["url"], cfg["db"], cfg["api_key"]
    try:
        dom = [
            ["order_id.state", "in", ["sale", "done"]],
            ["order_id.date_order", ">=", f"{date_from} 00:00:00"],
            ["order_id.date_order", "<=", f"{date_to} 23:59:59"],
        ]
        if model_code:
            dom.append(["product_id.default_code", "=like", f"{model_code}%"])
        lines = _x(u, db, uid, ak, "sale.order.line", "search_read", [dom],
                   {"fields": ["order_id", "product_id", "product_uom_qty", "price_unit", "price_subtotal"],
                    "limit": 15000, "order": "order_id desc"})
        if not lines:
            return empty
        oids = list({l["order_id"][0] for l in lines if isinstance(l.get("order_id"), list)})
        orders = _x(u, db, uid, ak, "sale.order", "search_read",
                    [[["id", "in", oids]]],
                    {"fields": ["id", "name", "partner_id", "date_order", "branch_id"],
                     "limit": len(oids) + 10})
        omap = {o["id"]: o for o in orders}
        pids = list({l["product_id"][0] for l in lines if isinstance(l.get("product_id"), list)})
        prods = _x(u, db, uid, ak, "product.product", "search_read",
                   [[["id", "in", pids]]],
                   {"fields": ["id", "default_code", "name", "categ_id", "product_tmpl_id"],
                    "limit": len(pids) + 10})
        pmap = {p["id"]: p for p in prods}
        tids = list({p["product_tmpl_id"][0] for p in prods
                     if isinstance(p.get("product_tmpl_id"), list)})
        tmap = {}
        if tids:
            try:
                tmpls = _x(u, db, uid, ak, "product.template", "search_read",
                           [[["id", "in", tids]]],
                           {"fields": ["id", "x_studio_brand_category"], "limit": len(tids) + 10})
                tmap = {tt["id"]: tt for tt in tmpls}
            except Exception:
                pass
        rows = []
        for line in lines:
            oid = line["order_id"][0] if isinstance(line.get("order_id"), list) else None
            pid = line["product_id"][0] if isinstance(line.get("product_id"), list) else None
            o = omap.get(oid, {})
            p = pmap.get(pid, {})
            tr = p.get("product_tmpl_id")
            tid = tr[0] if isinstance(tr, list) else tr
            tmpl = tmap.get(tid, {})
            br = o.get("branch_id")
            branch = br[1] if isinstance(br, list) and len(br) > 1 else (str(br) if br else "Unknown")
            cat = p.get("categ_id")
            categ = cat[1] if isinstance(cat, list) and len(cat) > 1 else (str(cat) if cat else "")
            bcr = tmpl.get("x_studio_brand_category", "")
            brand_cat = bcr[1] if isinstance(bcr, list) and len(bcr) > 1 else (str(bcr) if bcr else "")
            partner = o.get("partner_id")
            customer = partner[1] if isinstance(partner, list) and len(partner) > 1 else (str(partner) if partner else "")
            pname = line.get("product_id")
            pdisplay = pname[1] if isinstance(pname, list) and len(pname) > 1 else p.get("name", "")
            raw_d = str(o.get("date_order", ""))
            rows.append({
                "Date": raw_d[:10] if raw_d else "",
                "SO": o.get("name", ""), "Customer": customer,
                "Branch": branch, "Brand Category": brand_cat or "(No Brand)",
                "Category": categ or "(No Category)",
                "Model Code": str(p.get("default_code", "")).strip(),
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
# DEAD STOCK FINDER
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def fetch_dead_stock(threshold_days=60, system_key="SWAG",
                     _progress=None, _status_text=None):
    empty_cols = [
        "Model Code", "Product", "Category", "On Hand",
        "Unit Price", "Frozen Value (SAR)",
        "Last Sale Date", "Days Since Sale", "Status"
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
    uid = ar["uid"]
    u, db, ak = cfg["url"], cfg["db"], cfg["api_key"]
    today = datetime.now().date()
    cutoff = (today - timedelta(days=threshold_days)).strftime("%Y-%m-%d")
    rows = []
    is_partial = False
    last_sale_map = {}
    try:
        _prog(0.05, "Step 1/4 — Loading in-stock products...")
        all_prods = _x(u, db, uid, ak, "product.product", "search_read",
                       [[["qty_available", ">", 0], ["sale_ok", "=", True]]],
                       {"fields": ["id", "default_code", "display_name",
                                   "categ_id", "list_price", "qty_available"],
                        "limit": 10000, "order": "default_code asc"})
        if not all_prods:
            _prog(1.0, "No in-stock products found.")
            return empty, False
        all_pids = [p["id"] for p in all_prods]
        prod_map = {p["id"]: p for p in all_prods}
        _prog(0.15, f"Step 1/4 — Found {len(all_pids):,} in-stock products.")

        _prog(0.20, f"Step 2/4 — Checking recent sales (last {threshold_days} days)...")
        recent_sol = _x(u, db, uid, ak, "sale.order.line", "search_read",
                        [[["product_id", "in", all_pids],
                          ["order_id.state", "in", ["sale", "done"]],
                          ["order_id.date_order", ">=", f"{cutoff} 00:00:00"]]],
                        {"fields": ["product_id"], "limit": 50000})
        recently_sold = set()
        for ln in (recent_sol or []):
            pid = ln["product_id"][0] if isinstance(ln.get("product_id"), list) else None
            if pid:
                recently_sold.add(pid)
        dead_pids = [p for p in all_pids if p not in recently_sold]
        _prog(0.35, f"Step 2/4 — {len(dead_pids):,} items have no recent sale.")
        if not dead_pids:
            _prog(1.0, "All products sold recently — no dead stock!")
            return empty, False

        CHUNK = 200
        n_chunks = max(1, (len(dead_pids) + CHUNK - 1) // CHUNK)
        prog_start = 0.35
        prog_end = 0.85
        _prog(prog_start, f"Step 3/4 — Fetching sale history for {len(dead_pids):,} items...")

        for batch_idx, i in enumerate(range(0, len(dead_pids), CHUNK)):
            chunk = dead_pids[i:i + CHUNK]
            batch_num = batch_idx + 1
            pct = prog_start + (prog_end - prog_start) * (batch_idx / n_chunks)
            _prog(pct, f"Step 3/4 — Batch {batch_num}/{n_chunks}...")
            try:
                sol_chunk = _x(u, db, uid, ak, "sale.order.line", "search_read",
                               [[["product_id", "in", chunk],
                                 ["order_id.state", "in", ["sale", "done"]]]],
                               {"fields": ["product_id", "order_id"],
                                "limit": 50000, "order": "id desc"})
            except Exception as chunk_err:
                is_partial = True
                _prog(pct, f"Batch {batch_num} failed ({chunk_err}) — continuing.")
                continue
            if not sol_chunk:
                continue
            oids = list({ln["order_id"][0] for ln in sol_chunk
                         if isinstance(ln.get("order_id"), list)})
            if not oids:
                continue
            try:
                orders_ch = _x(u, db, uid, ak, "sale.order", "search_read",
                               [[["id", "in", oids]]],
                               {"fields": ["id", "date_order"],
                                "limit": len(oids) + 5})
            except Exception:
                is_partial = True
                continue
            odate = {}
            for o in orders_ch:
                raw = o.get("date_order", "")
                if raw:
                    try:
                        odate[o["id"]] = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S").date()
                    except Exception:
                        pass
            for ln in sol_chunk:
                pid = ln["product_id"][0] if isinstance(ln.get("product_id"), list) else None
                oid = ln["order_id"][0] if isinstance(ln.get("order_id"), list) else None
                if pid is None or oid is None:
                    continue
                d = odate.get(oid)
                if d is None:
                    continue
                if pid not in last_sale_map or d > last_sale_map[pid]:
                    last_sale_map[pid] = d

        _prog(0.90, "Step 4/4 — Building results...")
        for pid in dead_pids:
            prod = prod_map.get(pid, {})
            code = str(prod.get("default_code") or "").strip()
            name = prod.get("display_name") or ""
            cat = prod.get("categ_id")
            categ = cat[1] if isinstance(cat, list) and len(cat) > 1 else ""
            price = float(prod.get("list_price") or 0)
            qty = float(prod.get("qty_available") or 0)
            if qty <= 0:
                continue
            frozen_val = round(qty * price, 2)
            last_sale = last_sale_map.get(pid)
            if last_sale is None:
                days_since = 99999
                status = "Never Sold"
            else:
                days_since = (today - last_sale).days
                status = "Dead Stock"
            rows.append({
                "Model Code": code if code else "—",
                "Product": name,
                "Category": categ,
                "On Hand": int(qty),
                "Unit Price": price,
                "Frozen Value (SAR)": frozen_val,
                "Last Sale Date": last_sale.strftime("%Y-%m-%d") if last_sale else "Never",
                "Days Since Sale": days_since,
                "Status": status,
            })
        if not rows:
            _prog(1.0, "No dead stock found.")
            return empty, False
        df = pd.DataFrame(rows)
        df = df.sort_values("Frozen Value (SAR)", ascending=False).reset_index(drop=True)
        _prog(1.0, f"Done — {len(df):,} dead stock items found.")
        return df, is_partial
    except Exception as e:
        is_partial = True
        _prog(1.0, f"Error: {e}")
        if rows:
            df = pd.DataFrame(rows)
            df = df.sort_values("Frozen Value (SAR)", ascending=False).reset_index(drop=True)
            return df, is_partial
        return empty, is_partial

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN MAPS
# ─────────────────────────────────────────────────────────────────────────────
_COL_EN = {
    "System": "System", "Model Code": "Model Code", "Product": "Product",
    "Sale Price": "Sale Price", "On Hand": "On Hand", "Branch": "Branch",
    "Location": "Location", "Reference": "Reference", "Type": "Type",
    "State": "State", "From": "From", "To": "To", "Qty": "Qty",
    "Scheduled": "Scheduled", "Sold(30d)": "Sold(30d)", "Daily Vel": "Daily Vel",
    "Days Left": "Days Left", "Suggest": "Suggest", "Priority": "Priority",
    "Purchase Qty": "Purchase Qty",
}
_COL_AR = {
    "System": "النظام", "Model Code": "رمز الموديل", "Product": "المنتج",
    "Sale Price": "سعر البيع", "On Hand": "متوفر", "Branch": "الفرع",
    "Location": "الموقع", "Reference": "المرجع", "Type": "النوع",
    "State": "الحالة", "From": "من", "To": "إلى", "Qty": "الكمية",
    "Scheduled": "المجدول", "Sold(30d)": "مباع(30ي)", "Daily Vel": "معدل/يوم",
    "Days Left": "أيام متبقية", "Suggest": "المقترح", "Priority": "الأولوية",
    "Purchase Qty": "كمية المشتريات",
}

def localize_columns(df):
    if df is None or df.empty:
        return df
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
    DAYS = 30
    dfrom = (datetime.now() - timedelta(days=DAYS)).strftime("%Y-%m-%d 00:00:00")
    codes = list(codes_tuple)
    dom = _domain(codes, exact)
    CS = "System"
    CM = "Model Code"
    CPR = "Product"
    CP = "Sale Price"
    CQ = "On Hand"
    CB = "Branch"
    CR = "Reference"
    CT = "Type"
    CST = "State"
    CF = "From"
    CTO = "To"
    CQT = "Qty"
    CD = "Scheduled"
    CSOLD = "Sold(30d)"
    CVEL = "Daily Vel"
    CDAY = "Days Left"
    CSUGG = "Suggest"
    CPRI = "Priority"
    SM = {"draft": "Draft", "waiting": "Waiting", "confirmed": "Confirmed", "assigned": "Ready"}

    def _one(key):
        cfg = get_system_config(key)
        sn = key
        R = {"key": key, "total": [], "branch": [], "transfers": [], "reorder": []}
        if not cfg:
            R["total"].append({CS: sn, CM: "—",
                               CPR: f"No config — add [{_canonical_key(key)}] to secrets.toml",
                               CP: 0.0, CQ: 0, "_status": "ERROR"})
            return R
        auth_r = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
        if not auth_r["ok"]:
            err_short = auth_r["error"].split(":")[0]
            R["total"].append({CS: sn, CM: "—",
                               CPR: f"{err_short} — {auth_r['error']}",
                               CP: 0.0, CQ: 0, "_status": "ERROR"})
            return R
        uid = auth_r["uid"]
        u = cfg["url"]
        db = cfg["db"]
        ak = cfg["api_key"]
        try:
            prods = _x(u, db, uid, ak, "product.product", "search_read", [dom],
                       {"fields": ["id", "display_name", "default_code", "qty_available", "list_price"],
                        "limit": 2000, "order": "default_code asc"})
            if not prods:
                R["total"].append({CS: sn, CM: "—", CPR: "Not found", CP: 0.0, CQ: 0, "_status": "NOT_FOUND"})
                return R
            pids = [p["id"] for p in prods]
            pmap = {p["id"]: p for p in prods}
            for p in prods:
                R["total"].append({
                    CS: sn, CM: p.get("default_code") or "—",
                    CPR: p.get("display_name") or "",
                    CP: float(p.get("list_price") or 0),
                    CQ: int(p.get("qty_available") or 0),
                    "_status": "OK"})
            if need_branch:
                locs = _x(u, db, uid, ak, "stock.location", "search_read",
                          [[["usage", "=", "internal"], ["active", "=", True]]],
                          {"fields": ["id"], "limit": 10000})
                loc_ids = {l["id"] for l in locs}
                qs = _x(u, db, uid, ak, "stock.quant", "search_read",
                        [[["product_id", "in", pids],
                          ["location_id", "in", list(loc_ids)],
                          ["quantity", ">", 0]]],
                        {"fields": ["product_id", "location_id", "quantity"], "limit": 5000})
                for q in qs:
                    pid = q["product_id"][0] if isinstance(q.get("product_id"), list) else None
                    loc = q.get("location_id") or [None, "—"]
                    ln = loc[1] if isinstance(loc, list) else str(loc)
                    pm = pmap.get(pid, {})
                    R["branch"].append({
                        CS: sn, CB: ln, CM: pm.get("default_code") or "—",
                        CP: float(pm.get("list_price") or 0),
                        CQ: int(q.get("quantity") or 0), "_status": "OK"})
            if need_transfers:
                mvs = _x(u, db, uid, ak, "stock.move", "search_read",
                         [[["product_id", "in", pids],
                           ["state", "in", ["draft", "waiting", "confirmed", "assigned"]]]],
                         {"fields": ["picking_id", "product_id", "product_uom_qty"], "limit": 2000})
                if mvs:
                    pkids = list({m["picking_id"][0] for m in mvs if isinstance(m.get("picking_id"), list)})
                    if pkids:
                        pks = _x(u, db, uid, ak, "stock.picking", "search_read",
                                 [[["id", "in", pkids]]],
                                 {"fields": ["id", "name", "picking_type_id", "state",
                                             "location_id", "location_dest_id", "scheduled_date"]})
                        pkmap = {p["id"]: p for p in pks}
                        for mv in mvs:
                            pr = mv.get("picking_id")
                            if not isinstance(pr, list):
                                continue
                            pk = pkmap.get(pr[0], {})

                            def _n(f, _p=pk):
                                v = _p.get(f)
                                return v[1] if isinstance(v, list) else (v or "—")

                            sd = pk.get("scheduled_date") or "—"
                            if sd != "—":
                                try:
                                    sd = datetime.strptime(sd, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
                                except Exception:
                                    pass
                            pid2 = mv["product_id"][0] if isinstance(mv.get("product_id"), list) else None
                            pm2 = pmap.get(pid2, {})
                            R["transfers"].append({
                                CS: sn, CR: pk.get("name") or "—",
                                CT: _n("picking_type_id"),
                                CST: SM.get(pk.get("state", ""), pk.get("state", "")),
                                CF: _n("location_id"), CTO: _n("location_dest_id"),
                                CM: pm2.get("default_code") or "—",
                                CQT: int(mv.get("product_uom_qty") or 0),
                                CD: sd, "_status": "OK"})
            if need_reorder:
                sl = _x(u, db, uid, ak, "sale.order.line", "search_read",
                        [[["product_id", "in", pids],
                          ["order_id.state", "in", ["sale", "done"]],
                          ["order_id.date_order", ">=", dfrom]]],
                        {"fields": ["product_id", "product_uom_qty"], "limit": 10000})
                sm2 = {}
                for l in sl:
                    pid = l["product_id"][0] if isinstance(l.get("product_id"), list) else None
                    if pid:
                        sm2[pid] = sm2.get(pid, 0) + float(l.get("product_uom_qty") or 0)
                for p in prods:
                    pid = p["id"]
                    cq = int(p.get("qty_available") or 0)
                    sold = sm2.get(pid, 0)
                    vel = round(sold / DAYS, 2)
                    dl = str(round(cq / vel, 1)) if vel > 0 else "∞"
                    sg = max(0, round(target_days * vel - cq))
                    pr2 = ("Critical" if cq <= 0 else "Low" if cq <= reorder_point else "OK")
                    R["reorder"].append({
                        CS: sn, CM: p.get("default_code") or "—",
                        CPR: p.get("display_name") or "",
                        CQ: cq, CSOLD: int(sold), CVEL: vel,
                        CDAY: dl, CSUGG: sg, CPRI: pr2, "_status": "OK"})
        except Exception as e:
            R["total"].append({CS: sn, CM: "—", CPR: f"Error: {e}", CP: 0.0, CQ: 0, "_status": "ERROR"})
        return R

    at, ab, atr, ar = [], [], [], []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(_one, k): k for k in SYSTEM_KEYS}
        for f in as_completed(futs):
            r = f.result()
            at.extend(r["total"])
            ab.extend(r["branch"])
            atr.extend(r["transfers"])
            ar.extend(r["reorder"])

    def _df(rows, cols):
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=cols)

    return {
        "total": _df(at, ["System", "Model Code", "Product", "Sale Price", "On Hand", "_status"]),
        "branch": _df(ab, ["System", "Branch", "Model Code", "Sale Price", "On Hand", "_status"]),
        "transfers": _df(atr, ["System", "Reference", "Type", "State", "From", "To",
                                "Model Code", "Qty", "Scheduled", "_status"]),
        "reorder": _df(ar, ["System", "Model Code", "Product", "On Hand",
                             "Sold(30d)", "Daily Vel", "Days Left", "Suggest", "Priority", "_status"]),
    }

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

def display_df(df, thresh=0, table_key="tbl"):
    if df is None or df.empty:
        st.info(t("No data.", "لا بيانات."))
        return pd.DataFrame()
    work = df.copy()
    sys_col = t("System", "النظام")
    mc_col = t("Model Code", "رمز الموديل")
    pr_col = t("Product", "المنتج")
    br_col = t("Branch", "الفرع")
    loc_col = t("Location", "الموقع")
    qc = t("On Hand", "متوفر")
    pc = t("Sale Price", "سعر البيع")
    has_sys = sys_col in work.columns
    has_br = br_col in work.columns
    fc = st.columns([2, 2, 2, 1.5])
    if has_sys:
        all_sys = sorted(work[sys_col].dropna().unique().tolist())
        with fc[0]:
            sel_sys = st.multiselect(t("Company", "الشركة"), options=all_sys,
                                     default=all_sys, key=f"{table_key}_sys")
        if sel_sys:
            work = work[work[sys_col].isin(sel_sys)]
    if has_br:
        all_br = sorted(work[br_col].dropna().unique().tolist())
        with fc[1]:
            sel_br = st.multiselect(t("Branch", "الفرع"), options=all_br,
                                    default=all_br, key=f"{table_key}_br")
        if sel_br:
            work = work[work[br_col].isin(sel_br)]
    with fc[2]:
        q = st.text_input(t("Search model / product", "بحث موديل / منتج"),
                          value="", placeholder=t("e.g. XP6013", "مثال: XP6013"),
                          key=f"{table_key}_q").strip()
    if q:
        ql = q.lower()
        mask = pd.Series([False] * len(work), index=work.index)
        for col in [mc_col, pr_col, loc_col]:
            if col in work.columns:
                mask = mask | work[col].fillna("").str.lower().str.contains(ql, regex=False)
        work = work[mask]
    with fc[3]:
        sortable = [c for c in work.columns if c != "_status"]
        sort_by = st.selectbox(t("Sort by", "ترتيب"), options=["—"] + sortable,
                               index=0, key=f"{table_key}_sort")
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
        st.warning(t("No rows match your filters.", "لا توجد نتائج بعد الفلتر."))
        return pd.DataFrame()
    if qc in work.columns:
        raw_q = pd.to_numeric(work[qc], errors="coerce")
        mn, mx = int(raw_q.min() or 0), int(raw_q.max() or 0)
        if mx > mn:
            qr = st.slider(t("Qty range", "نطاق الكمية"),
                           min_value=mn, max_value=mx, value=(mn, mx),
                           key=f"{table_key}_qrange")
            raw_q2 = pd.to_numeric(work[qc], errors="coerce")
            work = work[(raw_q2 >= qr[0]) & (raw_q2 <= qr[1])]
    ok_work = work[work["_status"] == "OK"] if "_status" in work.columns else work
    sm1, sm2, sm3, sm4 = st.columns(4)
    sm1.metric(t("Rows", "الصفوف"), len(work))
    if qc in ok_work.columns:
        sm2.metric(t("Total Qty", "إجمالي الكمية"),
                   int(pd.to_numeric(ok_work[qc], errors="coerce").fillna(0).sum()))
    if pc in ok_work.columns:
        vp = pd.to_numeric(ok_work[pc], errors="coerce")
        sm3.metric(t("Avg Price (SAR)", "متوسط السعر س.ر"),
                   f"{vp[vp > 0].mean():,.0f}" if not vp[vp > 0].empty else "—")
    if has_sys and sys_col in ok_work.columns:
        sm4.metric(t("Companies", "الشركات"), ok_work[sys_col].nunique())
    show = work.drop(columns=["_status"], errors="ignore").copy()
    _raw_qty = (pd.to_numeric(work[qc], errors="coerce").fillna(0)
                if qc in work.columns else pd.Series(dtype=float, index=work.index))
    if pc in show.columns:
        show[pc] = pd.to_numeric(show[pc], errors="coerce").map(
            lambda v: f"{v:.2f} SAR" if pd.notna(v) else "—")
    if qc in show.columns:
        _lang = get_lang()
        show[qc] = pd.to_numeric(show[qc], errors="coerce").map(
            lambda v: get_qty_display(v, _lang))
    low_idx = set()
    if thresh > 0 and qc in work.columns:
        raw_q3 = pd.to_numeric(work[qc], errors="coerce")
        low_idx = set(work.index[(raw_q3 > 0) & (raw_q3 <= thresh)])
    _zero_set = set(_raw_qty.index[_raw_qty == 0]) if not _raw_qty.empty else set()
    _na_en = "Not Available"
    _na_ar = "غير متوفر"
    cols = show.columns.tolist()
    th_ = "".join(f"<th>{c}</th>" for c in cols)

    def _row(idx_row):
        i, row = idx_row
        is_zero = i in _zero_set
        cls = " na-row" if is_zero else (" rl" if i in low_idx else "")
        cells = "".join(
            f'<td class="cf">{v}</td>' if ci == 0
            else (f'<td class="na-cell">{v}</td>'
                  if is_zero and isinstance(v, str) and v in (_na_en, _na_ar)
                  else f"<td>{v}</td>")
            for ci, v in enumerate(row))
        return f'<tr class="{cls}">{cells}</tr>'

    tbody = "".join(_row(x) for x in show.iterrows())
    st.markdown(
        f'{_TABLE_CSS}<div class="swag-wrap">'
        f'<table class="swag-tbl"><thead><tr>{th_}</tr></thead>'
        f'<tbody>{tbody}</tbody></table></div>',
        unsafe_allow_html=True)
    st.caption(f"{len(show)} {t('rows shown', 'صفوف معروضة')} / {len(df)} {t('total', 'إجمالي')}")
    return work.drop(columns=["_status"], errors="ignore").copy()

def _render_html_table(df_display):
    if df_display is None or df_display.empty:
        st.info(t("No data.", "لا بيانات."))
        return
    cols = df_display.columns.tolist()
    th_ = "".join(f"<th>{c}</th>" for c in cols)

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
# SIZE BREAKDOWN HELPER
# ─────────────────────────────────────────────────────────────────────────────
_SIZE_ORDER = ["2XS", "XS", "S", "M", "L", "XL", "XXL", "2XL", "3XL", "4XL", "5XL", "OSFA"]
_SIZE_RE = re.compile(
    r'-?(2XS|XS|S|M|L|XL|XXL|2XL|3XL|4XL|5XL|OSFA|OS)$',
    re.IGNORECASE
)

def _extract_size(code):
    code = str(code).strip()
    m = _SIZE_RE.search(code)
    if m:
        size = m.group(0).lstrip("-").upper()
        base = code[:m.start()].rstrip("-").strip()
        return base, size
    return code, ""

def build_size_pivot(df, mc_col, qc_col, sc_col, pc_col, thr=0):
    if df is None or df.empty:
        return None, []
    tmp = df.copy()
    tmp["_base"], tmp["_size"] = zip(*tmp[mc_col].apply(_extract_size))
    tmp[qc_col] = pd.to_numeric(tmp[qc_col], errors="coerce").fillna(0)
    if thr > 0:
        tmp = tmp[tmp[qc_col] > thr]
    if tmp.empty:
        return None, []
    sizes = [s for s in _SIZE_ORDER if s in tmp["_size"].unique()]
    extra = sorted(s for s in tmp["_size"].unique() if s not in _SIZE_ORDER and s)
    all_sizes = sizes + extra
    pivot = tmp.pivot_table(index="_base", columns="_size", values=qc_col,
                            aggfunc="sum", fill_value=0).reset_index()
    pivot.columns.name = None
    ordered_cols = ["_base"] + [s for s in all_sizes if s in pivot.columns]
    remaining = [c for c in pivot.columns if c not in ordered_cols]
    pivot = pivot[ordered_cols + remaining]
    pivot["Total"] = pivot[[c for c in pivot.columns if c in all_sizes]].sum(axis=1)
    if pc_col in tmp.columns:
        pm = tmp.groupby("_base")[pc_col].first().reset_index()
        pivot = pivot.merge(pm, on="_base", how="left")
    pivot = pivot.rename(columns={"_base": mc_col})
    return pivot, all_sizes

# ─────────────────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
#  SEASON COMPARISON — NEW FEATURE
# ══════════════════════════════════════════════════════════════════════════════
# ─────────────────────────────────────────────────────────────────────────────

def _detect_season_field(url, db, uid, api_key):
    """
    Try each candidate field on product.template.
    Return the first one that exists and has data.
    """
    for field in SEASON_FIELD_CANDIDATES:
        try:
            result = _x(url, db, uid, api_key, "product.template", "search_read",
                        [[[(field, "!=", False)]]],
                        {"fields": [field], "limit": 1})
            if result:
                return field
        except Exception:
            continue
    return None


@st.cache_data(ttl=600, show_spinner=False)
def fetch_available_seasons(system_key="SWAG"):
    """
    Fetch all unique season values from the first configured system that works.
    Returns (list_of_seasons, detected_field_name)
    """
    cfg = get_system_config(system_key)
    if not cfg:
        return [], None
    ar = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not ar["ok"]:
        return [], None
    uid = ar["uid"]
    u, db, ak = cfg["url"], cfg["db"], cfg["api_key"]

    field = _detect_season_field(u, db, uid, ak)
    if not field:
        return [], None

    try:
        records = _x(u, db, uid, ak, "product.template", "search_read",
                     [[(field, "!=", False)]],
                     {"fields": [field], "limit": 10000})
        seasons = set()
        for r in records:
            val = r.get(field)
            if val is False or val is None:
                continue
            if isinstance(val, list):
                # Many2one returns [id, name]
                seasons.add(val[1] if len(val) > 1 else str(val[0]))
            elif isinstance(val, str) and val.strip():
                seasons.add(val.strip())
        return sorted(seasons), field
    except Exception:
        return [], None


def _fetch_season_products_one_system(system_key, season_value, season_field):
    """
    Fetch products for a given season from one system.
    Returns list of dicts with model_code, name, qty, price, season.
    """
    empty = []
    if not season_field:
        return empty
    cfg = get_system_config(system_key)
    if not cfg:
        return empty
    try:
        ar = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
        if not ar["ok"]:
            return empty
        uid = ar["uid"]
        u, db, ak = cfg["url"], cfg["db"], cfg["api_key"]

        # Search templates where season matches
        # Handle both char/selection fields and Many2one
        try:
            tmpls = _x(u, db, uid, ak, "product.template", "search_read",
                       [[(season_field, "=", season_value)]],
                       {"fields": ["id", "name", season_field, "default_code",
                                   "list_price", "type"],
                        "limit": 5000})
        except Exception:
            # Try ilike for text fields
            try:
                tmpls = _x(u, db, uid, ak, "product.template", "search_read",
                           [[(season_field, "ilike", season_value)]],
                           {"fields": ["id", "name", season_field, "default_code",
                                       "list_price", "type"],
                            "limit": 5000})
            except Exception:
                return empty

        if not tmpls:
            return empty

        tmpl_ids = [t["id"] for t in tmpls]
        tmpl_map = {t["id"]: t for t in tmpls}

        # Get product.product variants for qty
        prods = _x(u, db, uid, ak, "product.product", "search_read",
                   [[["product_tmpl_id", "in", tmpl_ids]]],
                   {"fields": ["id", "default_code", "display_name",
                               "qty_available", "list_price", "product_tmpl_id"],
                    "limit": 10000})

        rows = []
        for p in prods:
            tmpl_id = p.get("product_tmpl_id")
            if isinstance(tmpl_id, list):
                tmpl_id = tmpl_id[0]
            tmpl = tmpl_map.get(tmpl_id, {})
            season_raw = tmpl.get(season_field, "")
            if isinstance(season_raw, list):
                season_label = season_raw[1] if len(season_raw) > 1 else str(season_raw[0])
            else:
                season_label = str(season_raw) if season_raw else ""

            code = str(p.get("default_code") or tmpl.get("default_code") or "").strip()
            rows.append({
                "system": system_key,
                "model_code": code if code else "—",
                "product_name": p.get("display_name") or tmpl.get("name") or "",
                "qty_available": float(p.get("qty_available") or 0),
                "list_price": float(p.get("list_price") or tmpl.get("list_price") or 0),
                "season": season_label,
            })
        return rows
    except Exception:
        return empty


@st.cache_data(ttl=300, show_spinner=False)
def fetch_season_products(season_value, season_field):
    """
    Fetch season products from ALL configured systems in parallel.
    Returns a flat DataFrame.
    """
    all_rows = []
    errors = {}

    def _task(key):
        try:
            return key, _fetch_season_products_one_system(key, season_value, season_field), None
        except Exception as e:
            return key, [], str(e)

    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(_task, k): k for k in SYSTEM_KEYS}
        for f in as_completed(futs):
            key, rows, err = f.result()
            if err:
                errors[key] = err
            else:
                all_rows.extend(rows)

    if errors:
        for k, e in errors.items():
            st.warning(f"⚠ {k}: {e}")

    if not all_rows:
        return pd.DataFrame(columns=["system", "model_code", "product_name",
                                     "qty_available", "list_price", "season"])
    return pd.DataFrame(all_rows)


def build_season_comparison_matrix(df_flat):
    """
    Pivot the flat DataFrame into a company-wise comparison matrix.
    Columns: Model Code | Product | Season | {SYS}_Qty | {SYS}_Price | ... | Total Qty
    """
    if df_flat is None or df_flat.empty:
        return pd.DataFrame()

    # Aggregate by model_code + system (sum qty, mean price per system)
    agg = df_flat.groupby(["model_code", "product_name", "season", "system"]).agg(
        qty=("qty_available", "sum"),
        price=("list_price", "mean")
    ).reset_index()

    # Build pivot for qty
    qty_pivot = agg.pivot_table(
        index=["model_code", "product_name", "season"],
        columns="system",
        values="qty",
        aggfunc="sum",
        fill_value=0
    ).reset_index()
    qty_pivot.columns.name = None

    # Build pivot for price
    price_pivot = agg.pivot_table(
        index=["model_code", "product_name", "season"],
        columns="system",
        values="price",
        aggfunc="mean",
        fill_value=0
    ).reset_index()
    price_pivot.columns.name = None

    # Rename columns
    qty_cols = {k: f"{k} Qty" for k in SYSTEM_KEYS if k in qty_pivot.columns}
    price_cols = {k: f"{k} Price" for k in SYSTEM_KEYS if k in price_pivot.columns}
    qty_pivot = qty_pivot.rename(columns=qty_cols)
    price_pivot = price_pivot.rename(columns=price_cols)

    # Merge qty and price
    merge_on = ["model_code", "product_name", "season"]
    matrix = qty_pivot.merge(price_pivot[merge_on + list(price_cols.values())],
                             on=merge_on, how="outer")

    # Ensure all system columns exist
    for k in SYSTEM_KEYS:
        if f"{k} Qty" not in matrix.columns:
            matrix[f"{k} Qty"] = 0
        if f"{k} Price" not in matrix.columns:
            matrix[f"{k} Price"] = 0.0

    # Total qty
    qty_col_names = [f"{k} Qty" for k in SYSTEM_KEYS]
    matrix["Total Qty"] = matrix[qty_col_names].sum(axis=1)

    # Interleave qty/price columns per system
    ordered_cols = ["model_code", "product_name", "season"]
    for k in SYSTEM_KEYS:
        ordered_cols.append(f"{k} Qty")
        ordered_cols.append(f"{k} Price")
    ordered_cols.append("Total Qty")

    # Keep only columns that exist
    final_cols = [c for c in ordered_cols if c in matrix.columns]
    matrix = matrix[final_cols]

    # Clean numeric types
    for c in matrix.columns:
        if c.endswith(" Qty"):
            matrix[c] = pd.to_numeric(matrix[c], errors="coerce").fillna(0).astype(int)
        elif c.endswith(" Price"):
            matrix[c] = pd.to_numeric(matrix[c], errors="coerce").fillna(0.0).round(2)

    matrix = matrix.sort_values("Total Qty", ascending=False).reset_index(drop=True)
    return matrix


def to_excel_season_matrix(matrix_df, season_name):
    """
    Export the season comparison matrix to a polished Excel file.
    """
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    if matrix_df is None or matrix_df.empty:
        return b""

    buf = io.BytesIO()

    # Rename columns for display
    display_df_ex = matrix_df.copy()
    display_df_ex = display_df_ex.rename(columns={
        "model_code": "Model Code",
        "product_name": "Product",
        "season": "Season",
    })

    sheet_name = f"Season_{season_name[:20]}"

    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        display_df_ex.to_excel(writer, index=False, sheet_name=sheet_name)
        ws = writer.sheets[sheet_name]

        # Styles
        hdr_fill = PatternFill("solid", fgColor="060D0E")
        hdr_font = Font(bold=True, color="4AACB4", size=11, name="Calibri")
        qty_hdr_fill = PatternFill("solid", fgColor="0D2A2C")
        qty_hdr_font = Font(bold=True, color="7FCDD3", size=10, name="Calibri")
        price_hdr_fill = PatternFill("solid", fgColor="1A1A0D")
        price_hdr_font = Font(bold=True, color="D4A84B", size=10, name="Calibri")
        total_hdr_fill = PatternFill("solid", fgColor="1A0D0D")
        total_hdr_font = Font(bold=True, color="FF6B6B", size=11, name="Calibri")

        thin = Side(border_style="thin", color="1A2A2C")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        alt_fill = PatternFill("solid", fgColor="0D1A1C")
        zero_fill = PatternFill("solid", fgColor="1C1000")
        zero_font = Font(color="555555", name="Calibri", size=10)
        norm_font = Font(name="Calibri", size=10, color="8AACB0")
        qty_font = Font(name="Calibri", size=10, color="4AACB4", bold=True)
        price_font = Font(name="Calibri", size=10, color="D4A84B")
        total_font = Font(name="Calibri", size=11, color="FF6B6B", bold=True)
        num_align = Alignment(horizontal="right", vertical="center")
        ctr_align = Alignment(horizontal="center", vertical="center")
        tot_fill_row = PatternFill("solid", fgColor="060D0E")
        tot_font_row = Font(bold=True, name="Calibri", color="4AACB4", size=11)

        mr = ws.max_row
        mc = ws.max_column

        col_names = [ws.cell(row=1, column=c).value for c in range(1, mc + 1)]

        # Style header row
        ws.row_dimensions[1].height = 30
        for ci, cname in enumerate(col_names, 1):
            cell = ws.cell(row=1, column=ci)
            cell.border = border
            cell.alignment = ctr_align
            if cname in ("Model Code", "Product", "Season"):
                cell.fill = hdr_fill
                cell.font = hdr_font
            elif cname == "Total Qty":
                cell.fill = total_hdr_fill
                cell.font = total_hdr_font
            elif cname and cname.endswith(" Qty"):
                cell.fill = qty_hdr_fill
                cell.font = qty_hdr_font
            elif cname and cname.endswith(" Price"):
                cell.fill = price_hdr_fill
                cell.font = price_hdr_font
            else:
                cell.fill = hdr_fill
                cell.font = hdr_font

        # Style data rows
        for ri in range(2, mr + 1):
            ws.row_dimensions[ri].height = 18
            for ci, cname in enumerate(col_names, 1):
                cell = ws.cell(row=ri, column=ci)
                cell.border = border
                val = cell.value
                is_zero_qty = (cname and cname.endswith(" Qty") and
                               (val is None or val == 0))
                if cname == "Total Qty":
                    cell.font = total_font
                    cell.alignment = num_align
                    if ri % 2 == 0:
                        cell.fill = PatternFill("solid", fgColor="1A0505")
                elif cname and cname.endswith(" Qty"):
                    if is_zero_qty:
                        cell.font = zero_font
                        cell.fill = zero_fill
                    else:
                        cell.font = qty_font
                        if ri % 2 == 0:
                            cell.fill = PatternFill("solid", fgColor="0A1F20")
                    cell.alignment = num_align
                elif cname and cname.endswith(" Price"):
                    cell.font = price_font if (val and val > 0) else zero_font
                    if ri % 2 == 0:
                        cell.fill = alt_fill
                    cell.alignment = num_align
                    if val is not None and isinstance(val, (int, float)):
                        cell.number_format = '#,##0.00'
                else:
                    cell.font = norm_font
                    if ri % 2 == 0:
                        cell.fill = alt_fill
                    cell.alignment = ctr_align if not isinstance(val, (int, float)) else num_align

        # Auto width
        for ci in range(1, mc + 1):
            cl = get_column_letter(ci)
            ml = max(
                (len(str(ws.cell(row=r, column=ci).value or "")) for r in range(1, mr + 1)),
                default=8
            )
            cname = col_names[ci - 1] or ""
            if cname in ("Model Code", "Product"):
                ws.column_dimensions[cl].width = min(max(ml + 4, 16), 40)
            elif cname == "Season":
                ws.column_dimensions[cl].width = min(max(ml + 3, 14), 30)
            elif cname == "Total Qty":
                ws.column_dimensions[cl].width = 14
            else:
                ws.column_dimensions[cl].width = min(max(ml + 3, 12), 22)

        # Freeze top row
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(mc)}{mr}"

        # Totals row
        tr = mr + 1
        ws.row_dimensions[tr].height = 22
        tc = ws.cell(row=tr, column=1, value="TOTAL")
        tc.font = tot_font_row
        tc.fill = tot_fill_row
        tc.alignment = ctr_align
        tc.border = border

        for ci, cname in enumerate(col_names, 1):
            if ci == 1:
                continue
            cl = get_column_letter(ci)
            cell = ws.cell(row=tr, column=ci)
            cell.border = border
            cell.fill = tot_fill_row
            cell.alignment = num_align
            if cname and (cname.endswith(" Qty") or cname == "Total Qty"):
                cell.value = f"=SUM({cl}2:{cl}{mr})"
                cell.font = tot_font_row
            elif cname and cname.endswith(" Price"):
                cell.value = f"=AVERAGE({cl}2:{cl}{mr})"
                cell.font = Font(bold=True, name="Calibri", color="D4A84B")
            else:
                cell.value = ""

        # Footer
        footer_row = tr + 2
        fc_cell = ws.cell(row=footer_row, column=1,
                          value=f"Season: {season_name} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | SWAG Dashboard")
        fc_cell.font = Font(italic=True, color="4AACB4", size=9, name="Calibri")

        # Page setup
        ws.sheet_properties.tabColor = "4AACB4"
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.print_title_rows = "1:1"
        ws.sheet_view.zoomScale = 85

    return buf.getvalue()


def render_season_comparison_matrix(matrix_df):
    """
    Render the season comparison matrix as a styled HTML table.
    """
    if matrix_df is None or matrix_df.empty:
        st.info("No products found for this season.")
        return

    display = matrix_df.copy()
    display = display.rename(columns={
        "model_code": "Model Code",
        "product_name": "Product",
        "season": "Season",
    })

    cols = display.columns.tolist()
    th_parts = []
    for c in cols:
        if c.endswith(" Qty"):
            th_parts.append(f'<th style="color:#7FCDD3">{c}</th>')
        elif c.endswith(" Price"):
            th_parts.append(f'<th style="color:#D4A84B">{c}</th>')
        elif c == "Total Qty":
            th_parts.append(f'<th style="color:#FF6B6B">{c}</th>')
        else:
            th_parts.append(f'<th>{c}</th>')
    th_ = "".join(th_parts)

    def _fmt_cell(col_name, val, ci):
        if ci == 0:
            return f'<td class="cf">{val}</td>'
        if col_name == "Total Qty":
            color = "#FF6B6B" if val > 0 else "rgba(255,255,255,0.2)"
            return f'<td class="total-cell" style="color:{color}">{val}</td>'
        if col_name and col_name.endswith(" Qty"):
            if val == 0:
                return '<td class="zero-cell">—</td>'
            return f'<td class="qty-cell">{int(val)}</td>'
        if col_name and col_name.endswith(" Price"):
            if val == 0:
                return '<td class="zero-cell">—</td>'
            return f'<td class="price-cell">{val:.2f}</td>'
        return f'<td>{val}</td>'

    def _row(idx_row):
        _, row = idx_row
        cells = "".join(
            _fmt_cell(cols[ci], v, ci)
            for ci, v in enumerate(row)
        )
        return f"<tr>{cells}</tr>"

    tbody = "".join(_row(x) for x in display.iterrows())
    st.markdown(
        f'{_TABLE_CSS}<div class="swag-wrap">'
        f'<table class="swag-tbl"><thead><tr>{th_}</tr></thead>'
        f'<tbody>{tbody}</tbody></table></div>',
        unsafe_allow_html=True)


def tab_season_comparison():
    """
    Render the full Season Comparison tab UI.
    """
    st.markdown("""
    <div style="padding:32px 0 20px;">
        <div class="section-tag">Season Comparison</div>
        <h2 style="color:#fff;font-family:'Tajawal',sans-serif;font-size:28px;font-weight:700;margin:0 0 6px;">
            Company-Wide Season Analysis
        </h2>
        <p style="color:rgba(255,255,255,0.3);font-size:12px;letter-spacing:1px;">
            Select a season to compare on-hand quantity and sale price across all companies
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Step 1: Fetch seasons ──────────────────────────────────────────────
    with st.spinner("Fetching available seasons from Odoo..."):
        # Try each system until we get seasons
        seasons = []
        detected_field = None
        for sys_key in SYSTEM_KEYS:
            seasons, detected_field = fetch_available_seasons(sys_key)
            if seasons:
                break

    if not seasons:
        st.markdown("""
        <div class="warn-banner">
            ⚠ No seasons found. Check that SEASON_FIELD_CANDIDATES contains the correct
            field name for your Odoo instance. Current candidates are listed at the top of the code.
        </div>
        """, unsafe_allow_html=True)
        st.markdown("**Configured candidates:**")
        for f in SEASON_FIELD_CANDIDATES:
            st.code(f)

        st.markdown("**Manual override:** Enter season field name:")
        manual_field = st.text_input("Season field name", value="x_studio_season",
                                     key="manual_season_field")
        if manual_field:
            st.info(f"Add `{manual_field}` to SEASON_FIELD_CANDIDATES at the top of the code.")
        return

    # ── Step 2: Season selector ────────────────────────────────────────────
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        selected_season = st.selectbox(
            "Select Season",
            options=seasons,
            index=0,
            key="season_selector"
        )
    with col2:
        min_total_qty = st.number_input(
            "Min Total Qty Filter",
            min_value=0, value=0, step=1,
            key="season_min_qty",
            help="Hide products with total quantity below this value"
        )
    with col3:
        search_term = st.text_input(
            "Search Model / Product",
            value="",
            placeholder="e.g. XP6013",
            key="season_search"
        ).strip().lower()

    if detected_field:
        st.caption(f"Season field detected: `{detected_field}`")

    st.markdown("---")

    # ── Step 3: Fetch & Build Matrix ───────────────────────────────────────
    with st.spinner(f"Loading products for season: {selected_season} from all companies..."):
        flat_df = fetch_season_products(selected_season, detected_field)

    if flat_df is None or flat_df.empty:
        st.warning(f"No products found for season: **{selected_season}**")
        return

    matrix = build_season_comparison_matrix(flat_df)

    if matrix is None or matrix.empty:
        st.warning("Could not build comparison matrix.")
        return

    # ── Step 4: Apply filters ──────────────────────────────────────────────
    if min_total_qty > 0:
        matrix = matrix[matrix["Total Qty"] >= min_total_qty]

    if search_term:
        mask = (
            matrix["model_code"].fillna("").str.lower().str.contains(search_term, regex=False) |
            matrix["product_name"].fillna("").str.lower().str.contains(search_term, regex=False)
        )
        matrix = matrix[mask]

    matrix = matrix.reset_index(drop=True)

    # ── Step 5: Summary metrics ────────────────────────────────────────────
    m_cols = st.columns(len(SYSTEM_KEYS) + 2)
    m_cols[0].metric("Products", len(matrix))
    m_cols[1].metric("Total Qty (All)", int(matrix["Total Qty"].sum()) if "Total Qty" in matrix.columns else 0)
    for i, sk in enumerate(SYSTEM_KEYS):
        col_name = f"{sk} Qty"
        if col_name in matrix.columns:
            val = int(matrix[col_name].sum())
            m_cols[i + 2].metric(f"{sk}", val)

    st.markdown("---")

    # ── Step 6: Render table ───────────────────────────────────────────────
    if matrix.empty:
        st.info("No data matches your filters.")
    else:
        render_season_comparison_matrix(matrix)
        st.caption(f"{len(matrix)} products shown for season: {selected_season}")

    # ── Step 7: Download buttons ───────────────────────────────────────────
    st.markdown("---")
    dl_col1, dl_col2 = st.columns(2)

    with dl_col1:
        if not matrix.empty:
            excel_data = to_excel_season_matrix(matrix, selected_season)
            if excel_data:
                ts = datetime.now().strftime("%Y%m%d_%H%M")
                safe_season = re.sub(r'[^\w\-]', '_', selected_season)
                st.download_button(
                    label=f"⬇ Download Excel — Season {selected_season}",
                    data=excel_data,
                    file_name=f"swag_season_{safe_season}_{ts}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_season_excel"
                )

    with dl_col2:
        if not matrix.empty:
            csv_display = matrix.rename(columns={
                "model_code": "Model Code",
                "product_name": "Product",
                "season": "Season",
            })
            ts = datetime.now().strftime("%Y%m%d_%H%M")
            safe_season = re.sub(r'[^\w\-]', '_', selected_season)
            st.download_button(
                label=f"⬇ Download CSV — Season {selected_season}",
                data=csv_display.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"swag_season_{safe_season}_{ts}.csv",
                mime="text/csv",
                key="dl_season_csv"
            )

    # ── Step 8: Per-company breakdown (optional expander) ──────────────────
    with st.expander("Per-Company Raw Data", expanded=False):
        for sk in SYSTEM_KEYS:
            company_df = flat_df[flat_df["system"] == sk].copy()
            if company_df.empty:
                st.caption(f"{sk}: no data")
                continue
            st.markdown(f"**{sk}** — {len(company_df)} products")
            display_company = company_df[["model_code", "product_name", "qty_available",
                                          "list_price", "season"]].copy()
            display_company.columns = ["Model Code", "Product", "Qty", "Price", "Season"]
            display_company["Qty"] = display_company["Qty"].astype(int)
            display_company["Price"] = display_company["Price"].round(2)
            _render_html_table(display_company.head(50))

# ─────────────────────────────────────────────────────────────────────────────
# LOGIN PAGE
# ─────────────────────────────────────────────────────────────────────────────
def login_page():
    _, c, _ = st.columns([1, 1.6, 1])
    with c:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">SWAG</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Intelligence Dashboard · دخول</div>', unsafe_allow_html=True)

        with st.form("login_form"):
            email = st.text_input("Email", placeholder="your@email.com")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Enter Dashboard", use_container_width=True)

        if submitted:
            try:
                valid_users = st.secrets.get("AUTH", {})
                if email in valid_users and valid_users[email] == password:
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    token = _make_token(email)
                    st.query_params["u"] = email
                    st.query_params["t"] = token
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
            except Exception as e:
                st.error(f"Auth error: {e}")

        st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("### SWAG")
        st.markdown("---")

        # Language
        lang_choice = st.radio("Language / اللغة", ["EN", "AR"],
                               index=0 if get_lang() == "EN" else 1,
                               horizontal=True, key="lang_radio")
        if lang_choice != get_lang():
            st.session_state.lang = lang_choice
            st.rerun()

        st.markdown("---")

        # System status
        st.markdown("### Systems")
        for key in SYSTEM_KEYS:
            cfg = get_system_config(key)
            if not cfg:
                st.markdown(f'<div class="sys-row"><span>{key}</span> '
                            f'<span class="badge-off">NOT CONFIGURED</span></div>',
                            unsafe_allow_html=True)
                continue
            ar = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
            badge = 'badge-ok">ONLINE' if ar["ok"] else 'badge-err">OFFLINE'
            st.markdown(f'<div class="sys-row"><span>{key}</span> '
                        f'<span class="{badge}</span></div>',
                        unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(f"<div class='mono'>{st.session_state.user_email}</div>", unsafe_allow_html=True)
        if st.button("Logout", key="logout_btn"):
            st.session_state.authenticated = False
            st.session_state.user_email = ""
            st.query_params.clear()
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# HERO HEADER
# ─────────────────────────────────────────────────────────────────────────────
def render_hero():
    st.markdown("""
    <div class="hero-section">
        <div class="hero-glow"></div>
        <div class="hero-gold-glow"></div>
        <div class="hero-inner" style="padding:0 48px;">
            <div class="eyebrow">SWAG Intelligence Platform</div>
            <div class="hero-title">Product <em>Comparison</em></div>
            <div class="hero-subtitle">Multi-Company · Real-Time · Season Analytics</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────────────────────────
def main():
    restore_session()

    if not st.session_state.get("authenticated"):
        login_page()
        return

    render_sidebar()
    render_hero()

    # ── Tabs ──────────────────────────────────────────────────────────────
    tabs = st.tabs([
        t("🔍 Search", "🔍 بحث"),
        t("📊 Season Comparison", "📊 مقارنة الموسم"),
        t("🌿 Branch View", "🌿 عرض الفروع"),
        t("📦 Transfers", "📦 التحويلات"),
        t("🔄 Reorder", "🔄 إعادة الطلب"),
        t("💀 Dead Stock", "💀 المخزون الراكد"),
        t("📈 Sales Analytics", "📈 تحليل المبيعات"),
    ])

    tab_search, tab_season, tab_branch, tab_transfers, tab_reorder, tab_dead, tab_sales = tabs

    # ── Search Tab ─────────────────────────────────────────────────────────
    with tab_search:
        st.markdown("<div style='padding:24px 0 16px;'>", unsafe_allow_html=True)
        st.markdown('<div class="section-tag">Product Search</div>', unsafe_allow_html=True)

        col1, col2 = st.columns([3, 1])
        with col1:
            raw_input = st.text_area(
                t("Enter model codes (one per line or comma-separated)", "أدخل رموز الموديل"),
                height=100,
                placeholder="XP6013\nAB1234, CD5678",
                key="search_codes_input"
            )
        with col2:
            exact = st.checkbox(t("Exact match", "مطابقة تامة"), key="exact_match_cb")
            need_branch = st.checkbox(t("Branch breakdown", "توزيع الفروع"), key="need_branch_cb")
            need_transfers = st.checkbox(t("Transfers", "التحويلات"), key="need_transfers_cb")
            need_reorder = st.checkbox(t("Reorder analysis", "تحليل الطلب"), key="need_reorder_cb")
            thresh = st.number_input(t("Low stock alert", "تنبيه المخزون المنخفض"),
                                     min_value=0, value=st.session_state.low_stock_thresh,
                                     key="thresh_input")

        search_clicked = st.button(t("Search All Companies", "البحث في كل الشركات"),
                                   key="search_btn", type="primary", use_container_width=True)

        if search_clicked and raw_input.strip():
            codes_raw = [c.strip().upper() for c in re.split(r'[\n,;]+', raw_input) if c.strip()]
            codes_raw = list(dict.fromkeys(codes_raw))
            if codes_raw:
                st.session_state.low_stock_thresh = thresh
                with st.spinner(t("Fetching from all companies...", "جلب البيانات من كل الشركات...")):
                    result = fetch_all_data(
                        tuple(codes_raw), exact=exact,
                        need_branch=need_branch,
                        need_transfers=need_transfers,
                        need_reorder=need_reorder,
                        target_days=st.session_state.reorder_target_days,
                        reorder_point=st.session_state.reorder_point,
                    )
                st.session_state.total_df = prepare_df(result["total"])
                st.session_state.branch_df = prepare_df(result["branch"])
                st.session_state.transfers_df = prepare_df(result["transfers"])
                st.session_state.reorder_df = prepare_df(result["reorder"])
                st.session_state.last_run = datetime.now()

        if st.session_state.total_df is not None:
            df = st.session_state.total_df
            if st.session_state.last_run:
                st.caption(f"Last updated: {st.session_state.last_run.strftime('%H:%M:%S')}")

            filtered = display_df(df, thresh=thresh, table_key="total_tbl")

            if filtered is not None and not filtered.empty:
                dc1, dc2 = st.columns(2)
                with dc1:
                    st.download_button(
                        t("⬇ Download Excel", "⬇ تحميل Excel"),
                        data=to_excel(df),
                        file_name=dl_name("search", "xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_total_excel"
                    )
                with dc2:
                    st.download_button(
                        t("⬇ Download CSV", "⬇ تحميل CSV"),
                        data=to_csv(df),
                        file_name=dl_name("search", "csv"),
                        mime="text/csv",
                        key="dl_total_csv"
                    )

        st.markdown("</div>", unsafe_allow_html=True)

    # ── Season Comparison Tab ─────────────────────────────────────────────
    with tab_season:
        tab_season_comparison()

    # ── Branch View Tab ────────────────────────────────────────────────────
    with tab_branch:
        if st.session_state.branch_df is not None and not st.session_state.branch_df.empty:
            st.markdown("<div style='padding:24px 0 16px;'>", unsafe_allow_html=True)
            st.markdown('<div class="section-tag">Branch View</div>', unsafe_allow_html=True)
            bdf = display_df(st.session_state.branch_df, table_key="branch_tbl")
            if bdf is not None and not bdf.empty:
                st.download_button(
                    t("⬇ Download Branch Excel", "⬇ تحميل Excel الفروع"),
                    data=to_excel(st.session_state.branch_df),
                    file_name=dl_name("branch", "xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_branch_excel"
                )
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info(t("Run a search with 'Branch breakdown' enabled to see branch data.",
                      "قم بالبحث مع تفعيل 'توزيع الفروع' لرؤية بيانات الفروع."))

    # ── Transfers Tab ──────────────────────────────────────────────────────
    with tab_transfers:
        if st.session_state.transfers_df is not None and not st.session_state.transfers_df.empty:
            st.markdown("<div style='padding:24px 0 16px;'>", unsafe_allow_html=True)
            st.markdown('<div class="section-tag">Pending Transfers</div>', unsafe_allow_html=True)
            display_df(st.session_state.transfers_df, table_key="transfers_tbl")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info(t("Run a search with 'Transfers' enabled.", "قم بالبحث مع تفعيل 'التحويلات'."))

    # ── Reorder Tab ────────────────────────────────────────────────────────
    with tab_reorder:
        if st.session_state.reorder_df is not None and not st.session_state.reorder_df.empty:
            st.markdown("<div style='padding:24px 0 16px;'>", unsafe_allow_html=True)
            st.markdown('<div class="section-tag">Reorder Analysis</div>', unsafe_allow_html=True)
            display_df(st.session_state.reorder_df, table_key="reorder_tbl")
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info(t("Run a search with 'Reorder analysis' enabled.", "قم بالبحث مع تفعيل 'تحليل الطلب'."))

    # ── Dead Stock Tab ─────────────────────────────────────────────────────
    with tab_dead:
        st.markdown("<div style='padding:24px 0 16px;'>", unsafe_allow_html=True)
        st.markdown('<div class="section-tag">Dead Stock Finder</div>', unsafe_allow_html=True)

        col1, col2 = st.columns([2, 1])
        with col1:
            ds_sys = st.selectbox("Select Company", SYSTEM_KEYS, key="dead_sys")
        with col2:
            ds_days = st.number_input("Days threshold", min_value=7, max_value=730,
                                      value=60, key="dead_days")

        if st.button("Find Dead Stock", key="dead_btn", type="primary"):
            prog = st.progress(0.0)
            status = st.empty()
            df_dead, partial = fetch_dead_stock(
                threshold_days=ds_days,
                system_key=ds_sys,
                _progress=prog,
                _status_text=status
            )
            if df_dead is not None and not df_dead.empty:
                if partial:
                    st.warning("⚠ Partial results — some batches failed.")
                _render_html_table(df_dead)
                st.download_button(
                    "⬇ Download Dead Stock Excel",
                    data=_excel_generic(df_dead, "DeadStock"),
                    file_name=dl_name("dead_stock", "xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_dead_excel"
                )
            else:
                st.success("No dead stock found!")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Sales Analytics Tab ────────────────────────────────────────────────
    with tab_sales:
        st.markdown("<div style='padding:24px 0 16px;'>", unsafe_allow_html=True)
        st.markdown('<div class="section-tag">Sales Analytics</div>', unsafe_allow_html=True)

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            sa_model = st.text_input("Model Code (optional)", key="sa_model",
                                     placeholder="Leave blank for all")
        with col2:
            sa_sys = st.selectbox("Company", SYSTEM_KEYS, key="sa_sys")
        with col3:
            sa_days = st.number_input("Last N days", min_value=1, max_value=365,
                                      value=30, key="sa_days")

        if st.button("Load Sales", key="sa_btn", type="primary"):
            ed = datetime.now().date()
            sd = ed - timedelta(days=int(sa_days))
            with st.spinner("Loading sales history..."):
                sa_df = fetch_swag_sales_history(
                    model_code=sa_model.strip() or None,
                    date_from=sd.strftime("%Y-%m-%d"),
                    date_to=ed.strftime("%Y-%m-%d"),
                    system_key=sa_sys
                )
            st.session_state.so_analytics_df = sa_df

        if st.session_state.so_analytics_df is not None:
            sa_df = st.session_state.so_analytics_df
            if not sa_df.empty:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Orders", sa_df["SO"].nunique() if "SO" in sa_df.columns else 0)
                c2.metric("Lines", len(sa_df))
                c3.metric("Total Qty", int(sa_df["Qty"].sum()) if "Qty" in sa_df.columns else 0)
                c4.metric("Total Revenue",
                          f"{sa_df['Subtotal'].sum():,.0f} SAR" if "Subtotal" in sa_df.columns else "—")
                _render_html_table(sa_df.head(200))
                st.download_button(
                    "⬇ Download Sales Excel",
                    data=_excel_generic(sa_df, "Sales"),
                    file_name=dl_name("sales", "xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_sales_excel"
                )
            else:
                st.info("No sales data found for the selected criteria.")
        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
