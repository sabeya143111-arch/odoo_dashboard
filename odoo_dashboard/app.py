"""
SWAG Product Comparison Dashboard
Version 27.1 — Fixed bilingual Branch-wise Stock Export
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
# CSS (unchanged)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');
*,html,body,[class*="css"]{font-family:'IBM Plex Sans Arabic',sans-serif;box-sizing:border-box;}
.stApp{background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);min-height:100vh;}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#1a1a2e 0%,#16213e 100%)!important;border-right:1px solid #ffffff15;}
section[data-testid="stSidebar"] *,section[data-testid="stSidebar"] label,section[data-testid="stSidebar"] span,section[data-testid="stSidebar"] p,section[data-testid="stSidebar"] div{color:#e8e8ff!important;}
section[data-testid="stSidebar"] input{color:#1a1a2e!important;}
@keyframes fadeInUp{from{opacity:0;transform:translateY(40px)}to{opacity:1;transform:translateY(0)}}
@keyframes fadeInDown{from{opacity:0;transform:translateY(-30px)}to{opacity:1;transform:translateY(0)}}
@keyframes bounceIn{0%{transform:scale(0.2) rotate(-10deg);opacity:0}60%{transform:scale(1.2) rotate(5deg);opacity:1}80%{transform:scale(0.9)}100%{transform:scale(1);opacity:1}}
@keyframes shimmer{0%{background-position:-400% center}100%{background-position:400% center}}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 #7c3aed44}50%{box-shadow:0 0 20px 8px #7c3aed22}}
@keyframes glow{0%,100%{text-shadow:0 0 10px #667eea88}50%{text-shadow:0 0 30px #f093fbcc,0 0 60px #667eea88}}
@keyframes slideInLeft{from{opacity:0;transform:translateX(-40px)}to{opacity:1;transform:translateX(0)}}
@keyframes slideInRight{from{opacity:0;transform:translateX(40px)}to{opacity:1;transform:translateX(0)}}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}
@keyframes btnShine{0%{background-position:-200% center}100%{background-position:200% center}}
@keyframes borderGlow{0%,100%{border-color:#667eea;box-shadow:0 0 5px #667eea44}50%{border-color:#f093fb;box-shadow:0 0 15px #f093fb66}}
@keyframes countUp{from{opacity:0;transform:scale(0.5)}to{opacity:1;transform:scale(1)}}
.login-orb{width:120px;height:120px;border-radius:50%;background:linear-gradient(135deg,#667eea,#764ba2,#f093fb);display:flex;align-items:center;justify-content:center;font-size:3rem;margin:0 auto 20px;animation:float 3s ease-in-out infinite,bounceIn 1s ease forwards;box-shadow:0 8px 40px #667eea66,0 0 60px #f093fb33;}
.login-title{font-size:2.4rem;font-weight:700;background:linear-gradient(90deg,#667eea,#f093fb,#667eea);background-size:200% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:shimmer 3s linear infinite,fadeInDown 0.8s ease forwards;text-align:center;margin-bottom:6px;}
.login-subtitle{color:#c4b5fd!important;font-size:0.95rem;text-align:center;animation:fadeInUp 1s ease forwards;margin-bottom:28px;}
.login-card{background:linear-gradient(145deg,#1e1e3f,#2d2b55);border:1px solid #ffffff18;border-radius:20px;padding:32px 36px;width:100%;animation:fadeInUp 0.9s ease forwards,pulse 3s infinite;}
.welcome-banner{background:linear-gradient(135deg,#667eea22,#f093fb22);border:1px solid #667eea44;border-radius:12px;padding:14px 20px;text-align:center;margin-bottom:20px;font-size:0.95rem;color:#c4b5fd!important;animation:fadeInDown 0.7s ease forwards,borderGlow 3s infinite;}
.stTextInput input,.stNumberInput input,.stTextArea textarea{background:#1e1e3f!important;border:1px solid #667eea66!important;border-radius:10px!important;color:#e8e8ff!important;caret-color:#c4b5fd!important;transition:all 0.3s ease!important;}
.stTextInput input::placeholder,.stNumberInput input::placeholder,.stTextArea textarea::placeholder{color:#7070aa!important;}
.stTextInput input:focus,.stNumberInput input:focus,.stTextArea textarea:focus{border-color:#667eea!important;box-shadow:0 0 0 3px #667eea33!important;background:#252550!important;}
.stTextInput label,.stNumberInput label,.stTextArea label{color:#c4b5fd!important;font-weight:600!important;}
.stFormSubmitButton button,.stButton button[kind="primary"]{background:linear-gradient(90deg,#667eea,#764ba2,#f093fb,#667eea)!important;background-size:300% auto!important;border:none!important;border-radius:12px!important;color:white!important;font-weight:700!important;font-size:1rem!important;padding:12px!important;animation:btnShine 3s linear infinite!important;transition:transform 0.2s,box-shadow 0.2s!important;box-shadow:0 4px 20px #667eea55!important;}
.stFormSubmitButton button:hover,.stButton button[kind="primary"]:hover{transform:translateY(-2px) scale(1.02)!important;box-shadow:0 8px 30px #764ba299!important;}
.stButton button[kind="secondary"]{background:#1e1e3f!important;border:1px solid #667eea66!important;color:#c4b5fd!important;border-radius:10px!important;}
.stButton button[kind="secondary"]:hover{background:linear-gradient(135deg,#667eea,#764ba2)!important;color:white!important;}
.stButton button{color:#c4b5fd!important;}
.stDownloadButton button{background:linear-gradient(135deg,#1e1e3f,#2d2b55)!important;border:1px solid #667eea66!important;border-radius:10px!important;color:#c4b5fd!important;font-size:0.78rem!important;font-weight:600!important;padding:6px 14px!important;transition:all 0.25s ease!important;box-shadow:0 2px 8px #00000044!important;}
.stDownloadButton button:hover{background:linear-gradient(135deg,#667eea,#764ba2)!important;color:white!important;border-color:transparent!important;transform:translateY(-2px) scale(1.04)!important;box-shadow:0 6px 20px #667eea55!important;}
.dash-header{text-align:center;padding:16px 0 24px;animation:fadeInDown 0.6s ease forwards;}
.dash-title{font-size:2.4rem;font-weight:700;background:linear-gradient(90deg,#667eea,#f093fb,#43e97b,#667eea);background-size:300% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;animation:shimmer 4s linear infinite,glow 3s ease-in-out infinite;}
.dash-subtitle{color:#a0aec0;font-size:0.95rem;margin-top:-4px;}
[data-testid="stMetric"]{background:linear-gradient(135deg,#1e1e3f,#2d2b55)!important;border:1px solid #ffffff15!important;border-radius:16px!important;padding:16px 20px!important;animation:countUp 0.6s ease forwards;transition:transform 0.2s,box-shadow 0.2s;}
[data-testid="stMetric"]:hover{transform:translateY(-4px);box-shadow:0 8px 30px #667eea44;}
[data-testid="stMetricLabel"]{color:#a0aec0!important;font-size:0.82rem!important;}
[data-testid="stMetricValue"]{font-size:1.7rem!important;font-weight:700!important;background:linear-gradient(90deg,#667eea,#f093fb);-webkit-background-clip:text;-webkit-text-fill-color:transparent;}
.stTabs [data-baseweb="tab-list"]{background:linear-gradient(90deg,#1e1e3f,#2d2b55);border-radius:12px;padding:4px;gap:4px;}
.stTabs [data-baseweb="tab"]{color:#a0aec0!important;border-radius:10px!important;font-size:0.83rem!important;font-weight:600!important;padding:8px 16px!important;transition:all 0.2s ease!important;}
.stTabs [aria-selected="true"]{background:linear-gradient(90deg,#667eea,#764ba2)!important;color:white!important;box-shadow:0 4px 12px #667eea55!important;}
.info-banner{background:linear-gradient(135deg,#1e3a5f,#1e3a5f99);border-left:4px solid #3b82f6;border-radius:10px;padding:11px 16px;margin:8px 0 16px;font-size:0.85rem;color:#93c5fd!important;animation:slideInLeft 0.4s ease;}
.warn-banner{background:linear-gradient(135deg,#3b2a0a,#3b2a0a99);border-left:4px solid #f59e0b;border-radius:10px;padding:11px 16px;margin:8px 0 16px;font-size:0.85rem;color:#fcd34d!important;}
.alert-banner{background:linear-gradient(135deg,#3b0a1e,#3b0a1e99);border-left:4px solid #f43f5e;border-radius:10px;padding:11px 16px;margin:8px 0 16px;font-size:0.85rem;color:#fca5a5!important;animation:pulse 2s infinite;}
.ok-banner{background:linear-gradient(135deg,#0a3b1e,#0a3b1e99);border-left:4px solid #22c55e;border-radius:10px;padding:11px 16px;margin:8px 0 16px;font-size:0.85rem;color:#86efac!important;}
.snap-card{background:linear-gradient(145deg,#1e1e3f,#2d2b55);border:1px solid #ffffff18;border-radius:14px;padding:16px 20px;font-size:0.87rem;color:#e8e8ff!important;line-height:2;animation:slideInRight 0.5s ease;box-shadow:0 4px 20px #00000055;}
.snap-card b{color:#c4b5fd!important;}
.sys-row{display:flex;align-items:center;gap:8px;margin-bottom:6px;}
.sys-row span{color:#e8e8ff!important;}
.badge-ok{background:linear-gradient(90deg,#065f46,#047857);color:#d1fae5!important;border-radius:20px;padding:3px 12px;font-size:0.76rem;font-weight:700;}
.badge-off{background:linear-gradient(90deg,#991b1b,#b91c1c);color:#fee2e2!important;border-radius:20px;padding:3px 12px;font-size:0.76rem;font-weight:700;}
.badge-err{background:linear-gradient(90deg,#78350f,#92400e);color:#fef3c7!important;border-radius:20px;padding:3px 12px;font-size:0.76rem;font-weight:700;}
.stRadio label,.stRadio div[role="radiogroup"] label span,[data-testid="stToggle"] label,.stCheckbox label{color:#e8e8ff!important;}
div[data-testid="stRadio"] p{color:#e8e8ff!important;}
h1,h2,h3,h4,h5,h6{color:#e8e8ff!important;}
.stMarkdown p,.stMarkdown li{color:#c4b5fd!important;}
.stCaption,[data-testid="stCaptionContainer"] p{color:#8888bb!important;}
.stAlert p{color:#1a1a2e!important;font-weight:600;}
[data-testid="stExpander"]{background:linear-gradient(135deg,#1e1e3f,#2d2b55)!important;border:1px solid #ffffff18!important;border-radius:12px!important;}
[data-testid="stExpander"] summary,[data-testid="stExpander"] summary p{color:#c4b5fd!important;}
[data-testid="stFileUploader"]{background:linear-gradient(135deg,#1e1e3f,#2d2b55)!important;border:2px dashed #667eea66!important;border-radius:14px!important;}
[data-testid="stFileUploader"] p,[data-testid="stFileUploader"] span{color:#c4b5fd!important;}
hr{border:none!important;height:1px!important;background:linear-gradient(90deg,transparent,#667eea66,transparent)!important;margin:16px 0!important;}
[data-testid="stProgressBar"]>div{background:linear-gradient(90deg,#667eea,#f093fb)!important;border-radius:10px!important;}
::-webkit-scrollbar{width:6px;height:6px;}
::-webkit-scrollbar-track{background:#1a1a2e;}
::-webkit-scrollbar-thumb{background:linear-gradient(#667eea,#764ba2);border-radius:10px;}
::-webkit-scrollbar-thumb:hover{background:#f093fb;}
.stNumberInput button{color:#c4b5fd!important;background:#2d2b55!important;}
.mono{font-family:'IBM Plex Mono',monospace;font-size:0.82rem;color:#c4b5fd;}
footer{visibility:hidden;}
[data-baseweb="tag"]{background:#667eea33!important;color:#c4b5fd!important;}
[data-baseweb="select"] div{background:#1e1e3f!important;color:#e8e8ff!important;border-color:#667eea55!important;}
</style>
""", unsafe_allow_html=True)

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
        cell.fill = hdr_fill
        cell.font = hdr_font
        cell.alignment = hdr_align
        cell.border = border
    col_names = [ws.cell(row=1, column=c).value for c in range(1, max_col + 1)]
    on_hand_col    = None
    sale_price_col = None
    loc_col        = None
    branch_col     = None
    model_col      = None
    for i, name in enumerate(col_names, 1):
        if name in ("On Hand", "متوفر"):
            on_hand_col = i
        if name in ("Sale Price", "سعر البيع"):
            sale_price_col = i
        if name in ("Location", "الموقع"):
            loc_col = i
        if name in ("Branch", "الفرع"):
            branch_col = i
        if name in ("Model Code", "رمز الموديل"):
            model_col = i
    for row in ws.iter_rows(min_row=2, max_row=max_row):
        is_zero = False
        if on_hand_col:
            val = ws.cell(row=row[0].row, column=on_hand_col).value
            is_zero = (
                val is None or
                str(val).strip() in ['0', 'Not Available', 'غير متوفر', '—', '-', ''] or
                val == 0
            )
        for cell in row:
            cell.border = border
            cell.font = zero_font if is_zero else normal_font
            if is_zero:
                cell.fill = zero_fill
            elif cell.row % 2 == 0:
                cell.fill = alt_fill
            if isinstance(cell.value, (int, float)):
                cell.alignment = num_align
            else:
                cell.alignment = center_align
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
            DataBarRule(start_type="min", end_type="max", color="4472C4"),
        )
    if sale_price_col and max_row > 1:
        col_letter = get_column_letter(sale_price_col)
        ws.conditional_formatting.add(
            f"{col_letter}2:{col_letter}{max_row}",
            ColorScaleRule(
                start_type="min",        start_color="63BE7B",
                mid_type="percentile",   mid_value=50, mid_color="FFEB84",
                end_type="max",          end_color="F8696B",
            ),
        )
    if on_hand_col and max_row > 1:
        col_letter     = get_column_letter(on_hand_col)
        low_stock_fill = PatternFill("solid", fgColor="FFF2CC")
        low_stock_font = Font(color="7F6000", bold=True, name="Calibri")
        ws.conditional_formatting.add(
            f"{col_letter}2:{col_letter}{max_row}",
            CellIsRule(operator="lessThanOrEqual", formula=["3"],
                       fill=low_stock_fill, font=low_stock_font),
        )
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
    ws.cell(row=footer_row, column=1).font = Font(
        italic=True, color="888888", size=9, name="Calibri")
    ws.page_setup.orientation  = "landscape"
    ws.page_setup.fitToPage    = True
    ws.page_setup.fitToWidth   = 1
    ws.print_title_rows        = "1:1"
    ws.print_area              = f"A1:{get_column_letter(max_col)}{max_row}"
    ws.oddHeader.center.text   = "SWAG Product Report"
    ws.oddHeader.center.font   = "Calibri,Bold"
    ws.oddFooter.center.text   = "Page &P of &N  |  Generated: &D"
    ws.sheet_view.zoomScale = 85
    if loc_col:
        ws.column_dimensions[get_column_letter(loc_col)].width = 35
        for row_num in range(2, max_row + 1):
            ws.cell(row=row_num, column=loc_col).alignment = Alignment(
                wrap_text=True, vertical="center", horizontal="left")
            ws.row_dimensions[row_num].height = 28
    if on_hand_col and model_col and max_row > 2:
        chart = BarChart()
        chart.type              = "bar"
        chart.shape             = 4
        chart.title             = "Stock by Branch"
        chart.style             = 10
        chart.y_axis.title      = "On Hand"
        chart.x_axis.title      = "Branch"
        chart.width             = 20
        chart.height            = 12
        data_ref = Reference(ws, min_col=on_hand_col, min_row=1, max_row=max_row)
        cats_ref = Reference(ws, min_col=model_col,   min_row=2, max_row=max_row)
        chart.add_data(data_ref, titles_from_data=True)
        chart.set_categories(cats_ref)
        ws.add_chart(chart, f"A{max_row + 5}")

def to_csv(df):
    return df.drop(columns=["_status"], errors="ignore").to_csv(index=False).encode("utf-8-sig")

def to_excel(df):
    lang = st.session_state.get('lang', 'EN')
    buf = io.BytesIO()
    clean = df.drop(columns=['_status'], errors='ignore').copy()
    on_hand_col = 'On Hand' if 'On Hand' in clean.columns else (
        'متوفر' if 'متوفر' in clean.columns else None)
    if on_hand_col:
        na_text = 'غير متوفر' if lang == 'AR' else 'Not Available'
        clean[on_hand_col] = clean[on_hand_col].apply(
            lambda x: na_text if (pd.isna(x) or str(x).strip() in ['0', '']) or x == 0 else x
        )
    desired_order = [
        t("Model Code","رمز الموديل"), t("System","النظام"),
        t("Branch","الفرع"), t("Location","الموقع"),
        t("Sale Price","سعر البيع"), t("On Hand","متوفر"),
    ]
    ordered_cols = [c for c in desired_order if c in clean.columns]
    remaining = [c for c in clean.columns if c not in ordered_cols]
    clean = clean[ordered_cols + remaining]
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
        t("Branch","الفرع"), t("Location","الموقع"),
        t("Sale Price","سعر البيع"), t("On Hand","متوفر"),
    ]
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        def _ws(data, name):
            c = data.drop(columns=["_status"], errors="ignore").copy()
            on_hand_col = t("On Hand", "متوفر")
            if on_hand_col in c.columns:
                na_text = 'غير متوفر' if lang == 'AR' else 'Not Available'
                c[on_hand_col] = c[on_hand_col].apply(
                    lambda x: na_text if (pd.isna(x) or str(x).strip() in ['0', '']) or x == 0 else x
                )
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
# FIXED: BILINGUAL BRANCH-WISE STOCK EXPORT WITH PURCHASE QTY
# ─────────────────────────────────────────────────────────────────────────────
def to_excel_branch_location_stock_purchase(df_filtered, lang=None):
    """
    Export filtered branch dataframe to Excel with columns:
    Branch, Location, Model Code, Sale Price, Purchase Qty, On Hand.
    Purchase Qty is merged from SWAG purchase summary (last 365 days) by Model Code.
    Supports both English and Arabic modes automatically.
    """
    if df_filtered is None or df_filtered.empty:
        return b""

    lang = lang or get_lang()
    work = df_filtered.copy()

    # Get localized column names using the existing translation function
    branch_col = t("Branch", "الفرع")
    loc_col = t("Location", "الموقع")
    model_col = t("Model Code", "رمز الموديل")
    sale_price_col = t("Sale Price", "سعر البيع")
    on_hand_col = t("On Hand", "متوفر")

    # Ensure required columns exist (check against the actual dataframe columns)
    required = [branch_col, loc_col, model_col, sale_price_col, on_hand_col]
    missing = [c for c in required if c not in work.columns]
    if missing:
        st.error(f"Missing columns in branch data: {missing}")
        return b""

    # Keep only needed columns
    work = work[[branch_col, loc_col, model_col, sale_price_col, on_hand_col]].copy()

    # Convert numeric columns
    work[sale_price_col] = pd.to_numeric(work[sale_price_col], errors="coerce").fillna(0)
    work[on_hand_col] = pd.to_numeric(work[on_hand_col], errors="coerce").fillna(0)

    # --- Fetch purchase summary for visible model codes (using the Model Code column) ---
    unique_models = work[model_col].dropna().unique().tolist()
    purchase_map = {}
    if unique_models:
        try:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=365)
            date_from = start_date.strftime("%Y-%m-%d")
            date_to = end_date.strftime("%Y-%m-%d")
            pur_df = get_purchase_summary_by_model(tuple(unique_models), date_from, date_to)
            if not pur_df.empty:
                # pur_df has "Model Code" (English) and "Purchase Qty"
                # We need to map using the English model code, but our work has localized column name.
                # However, the model_code values are the same (English strings). So we map directly.
                purchase_map = dict(zip(pur_df["Model Code"], pur_df["Purchase Qty"]))
        except Exception as e:
            st.warning(f"Could not fetch purchase summary: {e}")

    # Add Purchase Qty column (localized name)
    purchase_qty_col = t("Purchase Qty", "كمية المشتريات")
    work[purchase_qty_col] = work[model_col].map(purchase_map).fillna(0).astype(int)

    # Reorder columns as required (all localized)
    final_columns = [branch_col, loc_col, model_col, sale_price_col, purchase_qty_col, on_hand_col]
    work = work[final_columns]

    # Sort by Branch, Location, Model Code (localized column names)
    work = work.sort_values(by=[branch_col, loc_col, model_col]).reset_index(drop=True)

    # --- Write Excel with styling, passing the current language for RTL support ---
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        work.to_excel(writer, index=False, sheet_name="BranchStock")
        ws = writer.sheets["BranchStock"]
        _style_worksheet(ws, work, lang=lang)
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────────────────────
# PURCHASE SUMMARY HELPER (unchanged)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def get_purchase_summary_by_model(model_codes_tuple, date_from, date_to):
    empty_df = pd.DataFrame(columns=["Model Code", "Purchase Qty"])
    cfg = st.secrets.get("SWAG")
    if not cfg:
        return empty_df

    uid = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not uid:
        return empty_df

    u  = cfg["url"]
    db = cfg["db"]
    ak = cfg["api_key"]

    try:
        date_from_dt = f"{date_from} 00:00:00"
        date_to_dt   = f"{date_to} 23:59:59"

        line_domain = [
            ["order_id.state", "in", ["purchase", "done"]],
            ["order_id.date_order", ">=", date_from_dt],
            ["order_id.date_order", "<=", date_to_dt],
        ]
        if model_codes_tuple:
            line_domain.append(["product_id.default_code", "in", list(model_codes_tuple)])

        lines = _x(u, db, uid, ak, "purchase.order.line", "search_read",
                   [line_domain],
                   {"fields": ["product_id", "product_qty"],
                    "limit": 10000,
                    "order": "id desc"})

        if not lines:
            return empty_df

        product_ids = list({l["product_id"][0] for l in lines if isinstance(l.get("product_id"), list)})

        products = _x(u, db, uid, ak, "product.product", "search_read",
                      [[["id", "in", product_ids]]],
                      {"fields": ["id", "default_code"], "limit": len(product_ids) + 10})
        prod_map = {p["id"]: p for p in products}

        agg = {}
        for line in lines:
            pid = line["product_id"][0] if isinstance(line.get("product_id"), list) else None
            prod = prod_map.get(pid, {})
            model_code = prod.get("default_code", "").strip()
            if not model_code:
                continue
            qty = float(line.get("product_qty") or 0)
            agg[model_code] = agg.get(model_code, 0) + qty

        if not agg:
            return empty_df

        df = pd.DataFrame([
            {"Model Code": mc, "Purchase Qty": qty}
            for mc, qty in agg.items()
        ])
        df = df.groupby("Model Code", as_index=False)["Purchase Qty"].sum()
        return df

    except Exception:
        return empty_df

# ─────────────────────────────────────────────────────────────────────────────
# PURCHASE HISTORY (detailed) - unchanged
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_swag_purchase_history(model_code, date_from, date_to):
    empty_cols = ["Date", "PO", "Vendor", "Brand Category", "Category",
                  "Model Code", "Product", "Qty", "Unit Price", "Subtotal"]
    empty_df = pd.DataFrame(columns=empty_cols)

    cfg = st.secrets.get("SWAG")
    if not cfg:
        return empty_df

    uid = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not uid:
        return empty_df

    u  = cfg["url"]
    db = cfg["db"]
    ak = cfg["api_key"]

    try:
        date_from_dt = f"{date_from} 00:00:00"
        date_to_dt   = f"{date_to} 23:59:59"

        line_domain = [
            ["order_id.state", "in", ["purchase", "done"]],
            ["order_id.date_order", ">=", date_from_dt],
            ["order_id.date_order", "<=", date_to_dt],
        ]
        if model_code and model_code.strip():
            line_domain.append(["product_id.default_code", "=", model_code.strip()])

        lines = _x(u, db, uid, ak, "purchase.order.line", "search_read",
                   [line_domain],
                   {"fields": ["order_id", "product_id", "product_qty", "price_unit"],
                    "limit": 5000,
                    "order": "order_id desc"})

        if not lines:
            return empty_df

        order_ids   = list({l["order_id"][0] for l in lines if isinstance(l.get("order_id"), list)})
        product_ids = list({l["product_id"][0] for l in lines if isinstance(l.get("product_id"), list)})

        orders = _x(u, db, uid, ak, "purchase.order", "search_read",
                    [[["id", "in", order_ids]]],
                    {"fields": ["id", "name", "partner_id", "date_order"], "limit": len(order_ids) + 10})
        order_map = {o["id"]: o for o in orders}

        products = _x(u, db, uid, ak, "product.product", "search_read",
                      [[["id", "in", product_ids]]],
                      {"fields": ["id", "default_code", "display_name", "categ_id", "product_tmpl_id"],
                       "limit": len(product_ids) + 10})
        prod_map = {p["id"]: p for p in products}

        tmpl_ids = list({p["product_tmpl_id"][0] for p in products
                         if isinstance(p.get("product_tmpl_id"), list)})
        tmpl_map = {}
        if tmpl_ids:
            try:
                tmpls = _x(u, db, uid, ak, "product.template", "search_read",
                           [[["id", "in", tmpl_ids]]],
                           {"fields": ["id", "x_brand_category_id"], "limit": len(tmpl_ids) + 10})
                tmpl_map = {t_["id"]: t_ for t_ in tmpls}
            except Exception:
                tmpl_map = {}

        rows = []
        for line in lines:
            oid = line["order_id"][0] if isinstance(line.get("order_id"), list) else None
            pid = line["product_id"][0] if isinstance(line.get("product_id"), list) else None

            order = order_map.get(oid, {})
            prod  = prod_map.get(pid, {})

            raw_date = order.get("date_order") or ""
            try:
                date_str = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
            except Exception:
                date_str = raw_date[:10] if raw_date else "—"

            partner = order.get("partner_id")
            vendor  = partner[1] if isinstance(partner, list) else (str(partner) if partner else "—")

            categ    = prod.get("categ_id")
            category = categ[1] if isinstance(categ, list) else (str(categ) if categ else "")

            brand_category = ""
            tmpl_ref = prod.get("product_tmpl_id")
            if isinstance(tmpl_ref, list) and tmpl_ref:
                tmpl = tmpl_map.get(tmpl_ref[0], {})
                bc   = tmpl.get("x_brand_category_id")
                if isinstance(bc, list):
                    brand_category = bc[1] if len(bc) > 1 else ""
                elif bc:
                    brand_category = str(bc)

            model_code_val = prod.get("default_code") or ""
            product_name   = prod.get("display_name") or ""
            qty            = float(line.get("product_qty") or 0)
            unit_price     = float(line.get("price_unit") or 0)
            subtotal       = round(qty * unit_price, 2)

            rows.append({
                "Date"          : date_str,
                "PO"            : order.get("name") or "—",
                "Vendor"        : vendor,
                "Brand Category": brand_category,
                "Category"      : category,
                "Model Code"    : model_code_val,
                "Product"       : product_name,
                "Qty"           : qty,
                "Unit Price"    : unit_price,
                "Subtotal"      : subtotal,
            })

        if not rows:
            return empty_df

        df = pd.DataFrame(rows)
        df = df.sort_values(by="Date", ascending=False).reset_index(drop=True)
        return df

    except Exception:
        return empty_df


# ─────────────────────────────────────────────────────────────────────────────
# SWAG SALES HISTORY (unchanged)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_swag_sales_history(model_code=None, date_from=None, date_to=None):
    empty = pd.DataFrame(columns=[
        "Date", "SO", "Customer", "Branch", "Brand Category", "Category",
        "Model Code", "Product", "Qty", "Unit Price", "Subtotal"
    ])
    cfg = st.secrets.get("SWAG")
    if not cfg:
        return empty
    uid = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not uid:
        return empty
    u, db, ak = cfg["url"], cfg["db"], cfg["api_key"]
    try:
        domain = [
            ["order_id.state", "in", ["sale", "done"]],
            ["order_id.date_order", ">=", f"{date_from} 00:00:00"],
            ["order_id.date_order", "<=", f"{date_to} 23:59:59"],
        ]
        if model_code:
            domain.append(["product_id.default_code", "=like", f"{model_code}%"])

        lines = _x(u, db, uid, ak, "sale.order.line", "search_read",
                   [domain],
                   {"fields": ["order_id", "product_id", "product_uom_qty",
                               "price_unit", "price_subtotal"],
                    "limit": 15000, "order": "order_id desc"})
        if not lines:
            return empty

        order_ids = list({l["order_id"][0] for l in lines if isinstance(l.get("order_id"), list)})
        orders    = _x(u, db, uid, ak, "sale.order", "search_read",
                       [[["id", "in", order_ids]]],
                       {"fields": ["id", "name", "partner_id", "date_order", "branch_id"],
                        "limit": len(order_ids) + 10})
        order_map = {o["id"]: o for o in orders}

        prod_ids = list({l["product_id"][0] for l in lines if isinstance(l.get("product_id"), list)})
        products = _x(u, db, uid, ak, "product.product", "search_read",
                      [[["id", "in", prod_ids]]],
                      {"fields": ["id", "default_code", "name", "categ_id", "product_tmpl_id"],
                       "limit": len(prod_ids) + 10})
        prod_map = {p["id"]: p for p in products}

        tmpl_ids = list({p["product_tmpl_id"][0] for p in products
                         if isinstance(p.get("product_tmpl_id"), list)})
        tmpl_map = {}
        if tmpl_ids:
            try:
                tmpls = _x(u, db, uid, ak, "product.template", "search_read",
                           [[["id", "in", tmpl_ids]]],
                           {"fields": ["id", "x_studio_brand_category"],
                            "limit": len(tmpl_ids) + 10})
                tmpl_map = {tt["id"]: tt for tt in tmpls}
            except Exception:
                tmpl_map = {}

        rows = []
        for line in lines:
            oid  = line["order_id"][0] if isinstance(line.get("order_id"), list) else None
            pid  = line["product_id"][0] if isinstance(line.get("product_id"), list) else None
            o    = order_map.get(oid, {})
            p    = prod_map.get(pid, {})

            tmpl_ref = p.get("product_tmpl_id")
            tid      = tmpl_ref[0] if isinstance(tmpl_ref, list) else tmpl_ref
            tmpl     = tmpl_map.get(tid, {})

            branch_obj = o.get("branch_id")
            if isinstance(branch_obj, list) and len(branch_obj) > 1:
                branch = branch_obj[1]
            elif branch_obj:
                branch = str(branch_obj)
            else:
                branch = "Unknown"

            categ_obj = p.get("categ_id")
            if isinstance(categ_obj, list) and len(categ_obj) > 1:
                categ = categ_obj[1]
            elif categ_obj:
                categ = str(categ_obj)
            else:
                categ = ""

            brand_cat_raw = tmpl.get("x_studio_brand_category", "")
            if isinstance(brand_cat_raw, list):
                brand_cat = brand_cat_raw[1] if len(brand_cat_raw) > 1 else ""
            else:
                brand_cat = str(brand_cat_raw) if brand_cat_raw else ""

            partner_obj = o.get("partner_id")
            if isinstance(partner_obj, list) and len(partner_obj) > 1:
                customer = partner_obj[1]
            elif partner_obj:
                customer = str(partner_obj)
            else:
                customer = ""

            prod_name_ref = line.get("product_id")
            if isinstance(prod_name_ref, list) and len(prod_name_ref) > 1:
                product_display = prod_name_ref[1]
            else:
                product_display = p.get("name", "")

            raw_date = str(o.get("date_order", ""))
            date_val = raw_date[:10] if raw_date else ""

            rows.append({
                "Date"          : date_val,
                "SO"            : o.get("name", ""),
                "Customer"      : customer,
                "Branch"        : branch,
                "Brand Category": brand_cat or "(No Brand)",
                "Category"      : categ or "(No Category)",
                "Model Code"    : str(p.get("default_code", "")).strip(),
                "Product"       : product_display,
                "Qty"           : float(line.get("product_uom_qty") or 0),
                "Unit Price"    : float(line.get("price_unit") or 0),
                "Subtotal"      : float(line.get("price_subtotal") or 0),
            })

        df = pd.DataFrame(rows)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.sort_values("Date", ascending=False).reset_index(drop=True)
        return df
    except Exception:
        return empty


# ─────────────────────────────────────────────────────────────────────────────
# COLUMN MAPS (unchanged)
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
    if df is None or df.empty:
        return df
    col_map = _COL_MAP_AR if get_lang() == "AR" else _COL_MAP_EN
    return df.rename(columns=col_map)

def prepare_df(df):
    df = localize_columns(df)
    df = translate_system_names(df)
    return df

# ─────────────────────────────────────────────────────────────────────────────
# FETCH ALL DATA (unchanged)
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

    CS="System"; CM="Model Code"
    CPR="Product"; CP="Sale Price"
    CQ="On Hand"; CB="Branch"
    CL="Location"; CR="Reference"
    CT="Type"; CST="State"
    CF="From"; CTO="To"; CQT="Qty"
    CD="Scheduled"; CSOLD="Sold(30d)"
    CVEL="Daily Vel"; CDAY="Days Left"
    CSUGG="Suggest"; CPRI="Priority"
    SM={
        "draft"    : "Draft",
        "waiting"  : "Waiting",
        "confirmed": "Confirmed",
        "assigned" : "Ready",
    }

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
                R["total"].append({CS:sn,CM:"—",CPR:"Not found",
                                   CP:0.0,CQ:0,"_status":"NOT_FOUND"})
                return R
            pids = [p["id"] for p in prods]
            pmap = {p["id"]:p for p in prods}

            for p in prods:
                R["total"].append({
                    CS:sn, CM:p.get("default_code") or "—",
                    CPR:p.get("display_name") or "",
                    CP:float(p.get("list_price") or 0),
                    CQ:int(p.get("qty_available") or 0),
                    "_status":"OK"
                })

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
                        CS:sn, CB:ln.split("/")[0].strip(),
                        CM:pm.get("default_code") or "—", CL:ln,
                        CP:float(pm.get("list_price") or 0),
                        CQ:int(q.get("quantity") or 0), "_status":"OK"
                    })

            if need_transfers:
                mvs = _x(u,db,uid,ak,"stock.move","search_read",
                         [[["product_id","in",pids],
                           ["state","in",["draft","waiting","confirmed","assigned"]]]],
                         {"fields":["picking_id","product_id","product_uom_qty"],"limit":2000})
                if mvs:
                    pkids = list({m["picking_id"][0] for m in mvs
                                  if isinstance(m.get("picking_id"),list)})
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
                                CD:sd, "_status":"OK"
                            })

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
                    pr2  = ("🔴 Critical" if cq<=0
                            else "🟡 Low" if cq<=reorder_point
                            else "🟢 OK")
                    R["reorder"].append({
                        CS:sn, CM:p.get("default_code") or "—",
                        CPR:p.get("display_name") or "",
                        CQ:cq, CSOLD:int(sold), CVEL:vel,
                        CDAY:dl, CSUGG:sg, CPRI:pr2, "_status":"OK"
                    })
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
        "branch"   : _df(ab,  ["System","Branch","Model Code","Location","Sale Price","On Hand","_status"]),
        "transfers": _df(atr, ["System","Reference","Type","State","From","To","Model Code","Qty","Scheduled","_status"]),
        "reorder"  : _df(ar,  ["System","Model Code","Product","On Hand","Sold(30d)","Daily Vel","Days Left","Suggest","Priority","_status"]),
    }

# ─────────────────────────────────────────────────────────────────────────────
# EXCEL PURCHASE EXPORT (unchanged)
# ─────────────────────────────────────────────────────────────────────────────
def to_excel_purchase(df):
    buf = io.BytesIO()
    clean = df.copy()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        clean.to_excel(w, index=False, sheet_name="SWAG Purchase")
        ws = w.sheets["SWAG Purchase"]
        from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        hdr_fill    = PatternFill("solid", fgColor="4B0082")
        hdr_font    = Font(bold=True, color="FFFFFF", size=11, name="Calibri")
        hdr_align   = Alignment(horizontal="center", vertical="center")
        thin        = Side(border_style="thin", color="D0D0D0")
        border      = Border(left=thin, right=thin, top=thin, bottom=thin)
        alt_fill    = PatternFill("solid", fgColor="F3EFFF")
        normal_font = Font(name="Calibri", size=10)
        num_align   = Alignment(horizontal="right", vertical="center")
        ctr_align   = Alignment(horizontal="center", vertical="center")
        total_fill  = PatternFill("solid", fgColor="2E2E2E")
        total_font  = Font(bold=True, name="Calibri", color="FFFFFF")
        max_row = ws.max_row
        max_col = ws.max_column
        ws.row_dimensions[1].height = 28
        for col_num in range(1, max_col + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill      = hdr_fill
            cell.font      = hdr_font
            cell.alignment = hdr_align
            cell.border    = border
        for row in ws.iter_rows(min_row=2, max_row=max_row):
            for cell in row:
                cell.border = border
                cell.font   = normal_font
                if cell.row % 2 == 0:
                    cell.fill = alt_fill
                if isinstance(cell.value, (int, float)):
                    cell.alignment = num_align
                else:
                    cell.alignment = ctr_align
            ws.row_dimensions[row[0].row].height = 18
        for col_num in range(1, max_col + 1):
            col_letter = get_column_letter(col_num)
            max_len = max(
                (len(str(ws.cell(row=r, column=col_num).value or ""))
                 for r in range(1, max_row + 1)),
                default=8
            )
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 50)
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(max_col)}{max_row}"
        total_row = max_row + 1
        ws.cell(row=total_row, column=1, value="TOTAL")
        ws.cell(row=total_row, column=1).font      = total_font
        ws.cell(row=total_row, column=1).fill      = total_fill
        ws.cell(row=total_row, column=1).alignment = Alignment(horizontal="center")
        col_names = [ws.cell(row=1, column=c).value for c in range(1, max_col + 1)]
        for summary_col_name in ("Qty", "Subtotal"):
            if summary_col_name in col_names:
                ci = col_names.index(summary_col_name) + 1
                cl = get_column_letter(ci)
                ws.cell(row=total_row, column=ci, value=f"=SUM({cl}2:{cl}{max_row})")
                ws.cell(row=total_row, column=ci).font      = total_font
                ws.cell(row=total_row, column=ci).fill      = total_fill
                ws.cell(row=total_row, column=ci).alignment = Alignment(horizontal="center")
        ws.row_dimensions[total_row].height = 20
        ws.sheet_properties.tabColor = "667EEA"
        footer_row = total_row + 2
        ws.cell(row=footer_row, column=1,
                value=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  SWAG Purchase History")
        ws.cell(row=footer_row, column=1).font = Font(italic=True, color="888888", size=9, name="Calibri")
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToPage   = True
        ws.page_setup.fitToWidth  = 1
        ws.print_title_rows       = "1:1"
        ws.sheet_view.zoomScale   = 85
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# EXCEL SALES EXPORT (unchanged)
# ─────────────────────────────────────────────────────────────────────────────
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
        hdr_fill   = PatternFill("solid", fgColor="1a6b3c")
        hdr_font   = Font(bold=True, color="FFFFFF", size=11, name="Calibri")
        hdr_align  = Alignment(horizontal="center", vertical="center")
        thin       = Side(border_style="thin", color="D0D0D0")
        border     = Border(left=thin, right=thin, top=thin, bottom=thin)
        alt_fill   = PatternFill("solid", fgColor="E8F5E9")
        norm_font  = Font(name="Calibri", size=10)
        num_align  = Alignment(horizontal="right",  vertical="center")
        ctr_align  = Alignment(horizontal="center", vertical="center")
        tot_fill   = PatternFill("solid", fgColor="2E2E2E")
        tot_font   = Font(bold=True, name="Calibri", color="FFFFFF")
        max_row, max_col = ws.max_row, ws.max_column
        ws.row_dimensions[1].height = 28
        for c in range(1, max_col + 1):
            cell = ws.cell(row=1, column=c)
            cell.fill, cell.font, cell.alignment, cell.border = hdr_fill, hdr_font, hdr_align, border
        for row in ws.iter_rows(min_row=2, max_row=max_row):
            for cell in row:
                cell.border = border
                cell.font   = norm_font
                cell.fill   = alt_fill if cell.row % 2 == 0 else PatternFill()
                cell.alignment = num_align if isinstance(cell.value, (int, float)) else ctr_align
            ws.row_dimensions[row[0].row].height = 18
        for c in range(1, max_col + 1):
            cl  = get_column_letter(c)
            mxl = max((len(str(ws.cell(row=r, column=c).value or "")) for r in range(1, max_row + 1)), default=8)
            ws.column_dimensions[cl].width = min(max(mxl + 3, 12), 50)
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(max_col)}{max_row}"
        tot_row = max_row + 1
        tot_cell = ws.cell(row=tot_row, column=1, value="TOTAL")
        tot_cell.font = tot_font
        tot_cell.fill = tot_fill
        tot_cell.alignment = ctr_align
        col_names = [ws.cell(row=1, column=c).value for c in range(1, max_col + 1)]
        for cname in ("Qty", "Subtotal"):
            if cname in col_names:
                ci = col_names.index(cname) + 1
                cl = get_column_letter(ci)
                ws.cell(row=tot_row, column=ci, value=f"=SUM({cl}2:{cl}{max_row})")
                ws.cell(row=tot_row, column=ci).font      = tot_font
                ws.cell(row=tot_row, column=ci).fill      = tot_fill
                ws.cell(row=tot_row, column=ci).alignment = ctr_align
        ws.sheet_properties.tabColor = "43e97b"
    return buf.getvalue()


def dl_name(tag, ext):
    return f"swag_{tag}_{datetime.now().strftime('%Y%m%d_%H%M')}.{ext}"

# ─────────────────────────────────────────────────────────────────────────────
# PRICE HISTORY (unchanged)
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
# QTY DISPLAY HELPER (unchanged)
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
# HTML TABLE CSS (unchanged)
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
</style>"""

# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY DF (returns filtered DataFrame)
# ─────────────────────────────────────────────────────────────────────────────
def display_df(df, thresh=0, table_key="tbl"):
    """
    Render the styled HTML table with inline filters.
    Returns the post-filter, post-sort DataFrame (columns without _status)
    so callers can use it for exports.  Returns pd.DataFrame() on empty/no data.
    """
    if df is None or df.empty:
        st.info(t("No data.","لا بيانات."))
        return pd.DataFrame()

    work = df.copy()
    sys_col = t("System","النظام")
    mc_col  = t("Model Code","رمز الموديل")
    pr_col  = t("Product","المنتج")
    br_col  = t("Branch","الفرع")
    loc_col = t("Location","الموقع")
    qc      = t("On Hand","متوفر")
    pc      = t("Sale Price","سعر البيع")

    has_sys = sys_col in work.columns
    has_br  = br_col  in work.columns

    fc = st.columns([2, 2, 2, 1.5])

    if has_sys:
        all_sys = sorted(work[sys_col].dropna().unique().tolist())
        with fc[0]:
            sel_sys = st.multiselect(
                f"🏢 {t('Company','الشركة')}",
                options=all_sys,
                default=all_sys,
                key=f"{table_key}_sys"
            )
        if sel_sys:
            work = work[work[sys_col].isin(sel_sys)]

    if has_br:
        all_br = sorted(work[br_col].dropna().unique().tolist())
        with fc[1]:
            sel_br = st.multiselect(
                f"🏪 {t('Branch','الفرع')}",
                options=all_br,
                default=all_br,
                key=f"{table_key}_br"
            )
        if sel_br:
            work = work[work[br_col].isin(sel_br)]

    with fc[2]:
        q = st.text_input(
            f"🔍 {t('Search model / product','بحث موديل / منتج')}",
            value="",
            placeholder=t("e.g. XP6013 or Shirt","مثال: XP6013"),
            key=f"{table_key}_q"
        ).strip()
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
            f"↕️ {t('Sort by','ترتيب')}",
            options=["—"] + sortable,
            index=0,
            key=f"{table_key}_sort"
        )
    if sort_by and sort_by != "—" and sort_by in work.columns:
        try:
            work = work.sort_values(
                by=sort_by,
                key=lambda s: pd.to_numeric(s, errors="coerce").fillna(0)
                              if pd.api.types.is_numeric_dtype(pd.to_numeric(s, errors="coerce"))
                              else s,
                ascending=True
            )
        except Exception:
            work = work.sort_values(by=sort_by)

    if work.empty:
        st.warning(t("⚠️ No rows match your filters.","لا توجد نتائج بعد الفلتر."))
        return pd.DataFrame()

    if qc in work.columns:
        raw_q = pd.to_numeric(work[qc], errors="coerce")
        mn, mx = int(raw_q.min() or 0), int(raw_q.max() or 0)
        if mx > mn:
            qr = st.slider(
                f"📦 {t('Qty range','نطاق الكمية')}",
                min_value=mn, max_value=mx,
                value=(mn, mx),
                key=f"{table_key}_qrange"
            )
            raw_q2 = pd.to_numeric(work[qc], errors="coerce")
            work   = work[(raw_q2 >= qr[0]) & (raw_q2 <= qr[1])]

    ok_work = work[work["_status"]=="OK"] if "_status" in work.columns else work
    sm1, sm2, sm3, sm4 = st.columns(4)
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

    show = work.drop(columns=["_status"], errors="ignore").copy()

    _raw_qty = (
        pd.to_numeric(work[qc], errors="coerce").fillna(0)
        if qc in work.columns else pd.Series(dtype=float, index=work.index)
    )

    if pc in show.columns:
        show[pc] = pd.to_numeric(show[pc], errors="coerce").map(
            lambda v: f"{v:.2f} SAR" if pd.notna(v) else "—")

    if qc in show.columns:
        _lang = get_lang()
        show[qc] = pd.to_numeric(show[qc], errors="coerce").map(
            lambda v: get_qty_display(v, _lang))

    low_idx = set()
    if thresh > 0 and qc in work.columns:
        raw_q3  = pd.to_numeric(work[qc], errors="coerce")
        low_idx = set(work.index[(raw_q3 > 0) & (raw_q3 <= thresh)])

    _zero_set    = set(_raw_qty.index[_raw_qty == 0]) if not _raw_qty.empty else set()
    _na_label_en = "❌ Not Available"
    _na_label_ar = "❌ لا يوجد"

    cols = show.columns.tolist()
    th_  = "".join(f"<th>{c}</th>" for c in cols)

    def _row(idx_row):
        i, row = idx_row
        is_zero = i in _zero_set
        if is_zero:
            cls = " na-row"
        elif i in low_idx:
            cls = " rl"
        else:
            cls = ""
        cells = "".join(
            f'<td class="cf">{v}</td>'
            if ci == 0
            else (
                f'<td class="na-cell">{v}</td>'
                if is_zero and isinstance(v, str) and v in (_na_label_en, _na_label_ar)
                else f"<td>{v}</td>"
            )
            for ci, v in enumerate(row)
        )
        return f'<tr class="{cls}">{cells}</tr>'

    tbody = "".join(_row(x) for x in show.iterrows())
    st.markdown(
        f'{_TABLE_CSS}<div class="swag-wrap">'
        f'<table class="swag-tbl"><thead><tr>{th_}</tr></thead>'
        f'<tbody>{tbody}</tbody></table></div>',
        unsafe_allow_html=True
    )
    st.caption(f"📊 {len(show)} {t('rows shown','صفوف معروضة')} "
               f"/ {len(df)} {t('total','إجمالي')}")

    # Return the clean filtered DataFrame for export use
    return work.drop(columns=["_status"], errors="ignore").copy()


# ─────────────────────────────────────────────────────────────────────────────
# RENDER HTML TABLE HELPER (generic, for analytics sections)
# ─────────────────────────────────────────────────────────────────────────────
def _render_html_table(df_display):
    """Render a DataFrame as styled HTML table."""
    if df_display is None or df_display.empty:
        st.info(t("No data.","لا بيانات."))
        return
    cols = df_display.columns.tolist()
    th_  = "".join(f"<th>{c}</th>" for c in cols)
    def _row(idx_row):
        _, row = idx_row
        cells = "".join(
            f'<td class="cf">{v}</td>' if ci == 0 else f"<td>{v}</td>"
            for ci, v in enumerate(row)
        )
        return f"<tr>{cells}</tr>"
    tbody = "".join(_row(x) for x in df_display.iterrows())
    st.markdown(
        f'{_TABLE_CSS}<div class="swag-wrap">'
        f'<table class="swag-tbl"><thead><tr>{th_}<tr></thead>'
        f'<tbody>{tbody}</tbody></table></div>',
        unsafe_allow_html=True
    )


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN (unchanged)
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
                st.error(t("Fill in both fields.","يرجى ملء جميع الحقول."))
                return
            if "LOGIN" not in st.secrets:
                st.error("❌ [LOGIN] section missing in secrets.toml")
                return
            cfg = st.secrets["LOGIN"]
            if "url" not in cfg or "db" not in cfg:
                st.error("❌ LOGIN.url or LOGIN.db missing in secrets.toml")
                return
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
                        time.sleep(0.3)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(t(
                            "❌ Wrong email or password.",
                            "❌ بريد إلكتروني أو كلمة مرور خاطئة."))
                except Exception as e:
                    st.error(f"❌ Connection error: {e}")

        st.markdown("""<p style='text-align:center;color:#4a4a6a;font-size:.75rem;margin-top:24px;'>
        © 2025 SWAG Fashion · Powered by Odoo · Built with ❤️</p>""",
                    unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# LOGOUT (unchanged)
# ─────────────────────────────────────────────────────────────────────────────
def do_logout():
    try: st.query_params.clear()
    except Exception: pass
    st.session_state.authenticated = False
    st.session_state.user_email    = ""
    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD (modified only in Branch-wise Stock tab to add the new button)
# ─────────────────────────────────────────────────────────────────────────────
def show_dashboard():
    with st.sidebar:
        st.markdown(f"### ⚙️ {t('Settings','الإعدادات')}")
        lc2 = st.radio(t("🌐 Language","🌐 اللغة"),["EN","AR"],
                       index=0 if get_lang()=="EN" else 1, horizontal=True)
        if lc2!=get_lang(): st.session_state.lang=lc2; st.rerun()
        st.divider()
        st.markdown(f"👤 **{st.session_state.user_email}**")
        if st.button(f"🚪 {t('Logout','تسجيل الخروج')}", use_container_width=True):
            do_logout()
        st.divider()
        st.markdown(f"##### 🔬 {t('Search Mode','وضع البحث')}")
        et = st.toggle(t("Exact match only","تطابق تام فقط"),
                       value=st.session_state.search_exact)
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
        st.divider()
        if st.session_state.last_run:
            st.markdown(f"🕒 **{t('Last Run','آخر تشغيل')}**")
            st.caption(st.session_state.last_run.get("time",""))

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
        updf = st.file_uploader(t("Upload PDF","رفع PDF"),
                                type=["pdf"], label_visibility="collapsed")
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
                        seen_ws.add(item["code"])
                        unique.append(item)

            unique_sorted = sorted(unique, key=lambda x: x["sequence"])
            unique_codes  = [item["code"] for item in unique_sorted]

            c1,c2,c3 = st.columns(3)
            c1.metric(t("Raw codes","رموز مستخرجة"), len(raw))
            c2.metric(t("Unique models","موديلات فريدة"), len(unique_codes))
            c3.info(f"📌 {t('Main','رئيسية') if is_main else t('With sizes','مع المقاسات')}")

            with st.expander(t(f"📋 {len(unique_codes)} codes","📋 الرموز"), expanded=False):
                st.code("\n".join(
                    f"{item['sequence']:>3}. {item['code']}"
                    for item in unique_sorted
                ))

            ca,cb = st.columns(2)
            with ca:
                if st.button(f"🚀 {t('Total Stock','مخزون إجمالي')}",
                             type="primary", use_container_width=True, key="pt"):
                    st.session_state.pdf_codes = unique_codes
                    st.session_state.pdf_mode  = "total"
                    st.rerun()
            with cb:
                if st.button(f"🗺️ {t('Branch-wise','حسب الفرع')}",
                             type="secondary", use_container_width=True, key="pb"):
                    st.session_state.pdf_codes = unique_codes
                    st.session_state.pdf_mode  = "branch"
                    st.rerun()
        else:
            st.warning(t("No codes found in PDF.","لم يتم العثور على رموز."))

    st.divider()

    # ── Manual Search ─────────────────────────────────────────────────────────
    st.markdown(f"### ✍️ {t('Manual Search','بحث يدوي')}")
    L,R = st.columns([1.5,1])
    with L:
        if not st.session_state.search_exact:
            st.markdown(
                "<div class='info-banner'>🔍 <b>Variant mode</b> — XP6013 → XP6013-S/M/L</div>",
                unsafe_allow_html=True)
        else:
            st.markdown(
                "<div class='warn-banner'>🎯 <b>Exact match mode</b> — identical codes only.</div>",
                unsafe_allow_html=True)
        ms   = t("Single Model","موديل واحد")
        mm   = t("Multiple Models","موديلات متعددة")
        mode = st.radio(t("Mode","الوضع"),[ms,mm],
                        horizontal=True, label_visibility="collapsed")
        if mode==mm:
            rt    = st.text_area(t("Codes","الرموز"), height=130,
                                 placeholder="ABC123\nDEF456")
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
                        t("Target days","أيام"), 7, 180,
                        st.session_state.reorder_target_days)
                else:
                    st.session_state.reorder_max_level = st.number_input(
                        t("Max level","الحد"), min_value=1, max_value=99999,
                        value=st.session_state.reorder_max_level, step=1)

        cbtn = st.button(f"🔍 {t('Compare','مقارنة')}",
                         use_container_width=True, type="primary")

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
                st.sidebar.info(
                    t(f"ℹ️ {zero_count} rows have zero qty (shown as ❌ Not Available)",
                      f"ℹ️ {zero_count} صف بكمية صفر (معروض كـ ❌ لا يوجد)"))

        swag_system_name = get_system_name("SWAG")
        swag_mask = (tdf[sc2_loc] == swag_system_name)

        if swag_mask.any():
            model_codes_swag = (
                tdf.loc[swag_mask, mc_loc]
                .dropna()
                .unique()
                .tolist()
            )
            if model_codes_swag:
                end_date   = datetime.now().date()
                start_date = end_date - timedelta(days=365)
                date_from  = start_date.strftime("%Y-%m-%d")
                date_to    = end_date.strftime("%Y-%m-%d")

                with st.spinner(t("📦 Fetching purchase totals for SWAG models…",
                                  "📦 جلب إجمالي المشتريات لموديلات سواغ…")):
                    pur_summary = get_purchase_summary_by_model(
                        tuple(model_codes_swag), date_from, date_to
                    )

                if not pur_summary.empty:
                    pur_renamed = pur_summary.rename(columns={"Model Code": mc_loc})
                    tdf = tdf.merge(
                        pur_renamed[[mc_loc, "Purchase Qty"]],
                        on=mc_loc,
                        how="left"
                    )
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

        desired_cols = [
            sc2_loc,
            mc_loc,
            t("Product","المنتج"),
            t("Sale Price","سعر البيع"),
            pur_col_name,
            qc2,
        ]
        existing_cols = tdf.columns.tolist()
        final_cols    = [c for c in desired_cols if c in existing_cols]
        for c in existing_cols:
            if c not in final_cols:
                final_cols.append(c)
        tdf = tdf[final_cols]

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
    if hb: tlabels.append(f"🗺️ {t('Branch Stock','مخزون الفروع')}")
    if ht: tlabels.append(f"🚚 {t('Transfers','النقليات')}")
    if hr: tlabels.append(f"📦 {t('Reorder','إعادة الطلب')}")
    tlabels.append(f"🛒 {t('SWAG Purchase','مشتريات سواغ')}")
    tlabels.append(f"🛍️ {t('SWAG Sales','مبيعات سواغ')}")

    tabs = st.tabs(tlabels)
    ti   = 0

    # ── Tab: Total Stock (unchanged) ─────────────────────────────────────────
    with tabs[ti]:
        ti += 1
        st.markdown(f"### 📦 {t('Total Stock','المخزون الإجمالي')}")
        _filtered_total = display_df(tdf, thr, table_key="total")
        st.markdown("<br>", unsafe_allow_html=True)

        d1, d2, d3, d4 = st.columns([1, 1, 1, 1])
        d1.download_button(
            "⬇️ CSV",
            to_csv(tdf),
            dl_name("total", "csv"),
            "text/csv",
            use_container_width=True,
        )
        d2.download_button(
            "⬇️ Excel",
            to_excel(tdf),
            dl_name("total", "xlsx"),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        d3.download_button(
            "📥 All Systems",
            to_excel_bulk(tdf),
            dl_name("bulk", "xlsx"),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        if _filtered_total is not None and not _filtered_total.empty:
            d4.download_button(
                f"🔍 {t('Filtered Excel','Excel المفلتر')}",
                to_excel(_filtered_total),
                dl_name("filtered_total", "xlsx"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                help=t(
                    "Exports only the rows currently visible after all active filters "
                    "(company, branch, search, qty range, sort order).",
                    "يصدّر الصفوف المعروضة فقط بعد تطبيق جميع الفلاتر النشطة "
                    "(الشركة، الفرع، البحث، نطاق الكمية، الترتيب)."
                ),
            )
        else:
            d4.markdown("")

    # ── Tab: Price History (unchanged) ───────────────────────────────────────
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

    # ── Tab: Branch Stock (with bilingual export button) ─────────────────────
    if hb:
        with tabs[ti]:
            ti += 1
            st.markdown(f"### 🗺️ {t('Branch-wise Stock','مخزون حسب الفرع')}")

            # Capture filtered branch dataframe from display_df
            _filtered_branch = display_df(bdf, thr, table_key="branch")

            bc2 = t("Branch","الفرع")
            okb = bdf[bdf["_status"]=="OK"] if "_status" in bdf.columns else bdf
            if not okb.empty and bc2 in okb.columns and qc2 in okb.columns:
                chart = okb.groupby([sc2,bc2])[qc2].sum().reset_index()
                if not chart.empty:
                    st.markdown(f"#### 📊 {t('Qty by Branch','الكميات حسب الفرع')}")
                    st.bar_chart(chart.set_index(bc2)[qc2], use_container_width=True)

            # Create 4 columns for buttons (CSV, Excel, Filtered Excel, New Export)
            b1, b2, b3, b4 = st.columns([1, 1, 1, 1])
            b1.download_button(
                "⬇️ CSV",
                to_csv(bdf),
                dl_name("branch", "csv"),
                "text/csv",
                use_container_width=True,
            )
            b2.download_button(
                "⬇️ Excel",
                to_excel(bdf),
                dl_name("branch", "xlsx"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
            if _filtered_branch is not None and not _filtered_branch.empty:
                b3.download_button(
                    f"🔍 {t('Filtered Excel','Excel المفلتر')}",
                    to_excel(_filtered_branch),
                    dl_name("filtered_branch", "xlsx"),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    help=t(
                        "Exports only the rows currently visible after all active filters "
                        "(branch, search, qty range, sort order).",
                        "يصدّر الصفوف المعروضة فقط بعد تطبيق جميع الفلاتر النشطة "
                        "(الفرع، البحث، نطاق الكمية، الترتيب)."
                    ),
                )
                # NEW BUTTON: Export Branch Stock with Purchase Qty (bilingual)
                b4.download_button(
                    f"📦 {t('Branch Stock + Purchase','مخزون الفروع + المشتريات')}",
                    to_excel_branch_location_stock_purchase(_filtered_branch, get_lang()),
                    dl_name("branch_purchase", "xlsx"),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    help=t(
                        "Exports the currently visible branch rows with added Purchase Qty (last 365 days). "
                        "Columns: Branch, Location, Model Code, Sale Price, Purchase Qty, On Hand.",
                        "يصدّر صفوف الفروع المعروضة مع إضافة كمية المشتريات (آخر 365 يومًا). "
                        "الأعمدة: الفرع، الموقع، رمز الموديل، سعر البيع، كمية المشتريات، المتوفر."
                    ),
                )
            else:
                b3.markdown("")
                b4.markdown("")

    # ── Tab: Transfers (unchanged) ───────────────────────────────────────────
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
            x1.download_button("⬇️ CSV",
                to_csv(trdf), dl_name("transfers","csv"), "text/csv",
                use_container_width=True)
            x2.download_button("⬇️ Excel",
                to_excel(trdf), dl_name("transfers","xlsx"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)

    # ── Tab: Reorder (unchanged) ─────────────────────────────────────────────
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
            o1.download_button("⬇️ CSV",
                to_csv(rdf), dl_name("reorder","csv"), "text/csv",
                use_container_width=True)
            o2.download_button("⬇️ Excel",
                to_excel(rdf), dl_name("reorder","xlsx"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)

    # ── Tab: SWAG Purchase (unchanged) ───────────────────────────────────────
    with tabs[ti]:
        ti += 1
        st.markdown(f"### 🛒 {t('SWAG Purchase History','سجل مشتريات سواغ')}")
        st.markdown(
            "<div class='info-banner'>📌 "
            + t("Purchase orders from the <b>SWAG</b> system only (state: purchase / done).",
                "أوامر الشراء من نظام <b>سواغ</b> فقط (الحالة: مشترى / منجز).")
            + "</div>",
            unsafe_allow_html=True
        )

        pf1, pf2, pf3 = st.columns([1.5, 1, 1])
        with pf1:
            po_model_code = st.text_input(
                f"🔖 {t('Model Code (Internal Ref)','رمز الموديل (المرجع الداخلي)')}",
                placeholder=t("e.g. RVT196 — leave blank for all",
                              "مثال: RVT196 — اتركه فارغاً للكل"),
                key="po_model_code"
            ).strip()

        default_from = datetime.now().date() - timedelta(days=365)
        default_to   = datetime.now().date()

        with pf2:
            po_date_from = st.date_input(
                f"📅 {t('From','من')}", value=default_from, key="po_date_from")
        with pf3:
            po_date_to = st.date_input(
                f"📅 {t('To','إلى')}", value=default_to, key="po_date_to")

        fetch_po_btn = st.button(
            f"🔍 {t('Fetch Purchase Analytics','جلب تحليلات المشتريات')}",
            type="primary", use_container_width=False, key="fetch_po_btn"
        )

        if fetch_po_btn:
            date_from_str = po_date_from.strftime("%Y-%m-%d")
            date_to_str   = po_date_to.strftime("%Y-%m-%d")
            po_model_norm = po_model_code.upper() if po_model_code else None

            with st.spinner(t("⚡ Fetching purchase analytics from SWAG…",
                               "⚡ جلب تحليلات المشتريات من نظام سواغ…")):
                po_df = fetch_swag_purchase_history(
                    model_code=po_model_norm,
                    date_from=date_from_str,
                    date_to=date_to_str,
                )

            if po_df is None or po_df.empty:
                st.info(t("No purchases found for this period / model.",
                          "لا توجد مشتريات لهذه الفترة / الموديل."))
            else:
                total_qty      = float(po_df["Qty"].sum())
                total_amount   = float(po_df["Subtotal"].sum())
                distinct_prods = int(po_df["Model Code"].nunique())
                num_vendors    = int(po_df["Vendor"].nunique())

                km1, km2, km3, km4 = st.columns(4)
                km1.metric(t("Total Qty Purchased","إجمالي الكمية المشتراة"),
                           f"{total_qty:,.0f}")
                km2.metric(t("Total Purchase Amount","إجمالي مبلغ الشراء"),
                           f"{total_amount:,.2f} SAR")
                km3.metric(t("Distinct Products","عدد المنتجات"), distinct_prods)
                km4.metric(t("Distinct Vendors","عدد الموردين"), num_vendors)

                st.divider()

                def _top10_table(top_df):
                    cols_t = top_df.columns.tolist()
                    th_t   = "".join(f"<th>{c}</th>" for c in cols_t)
                    def _tr(idx_row):
                        _, row = idx_row
                        cells = "".join(
                            f'<td class="cf">{v}</td>' if ci == 0 else f"<td>{v}</td>"
                            for ci, v in enumerate(row)
                        )
                        return f"<tr>{cells}</tr>"
                    tbody_t = "".join(_tr(x) for x in top_df.iterrows())
                    st.markdown(
                        f'{_TABLE_CSS}<div class="swag-wrap">'
                        f'<table class="swag-tbl"><thead><tr>{th_t}</table></thead>'
                        f'<tbody>{tbody_t}</tbody></table></div>',
                        unsafe_allow_html=True
                    )

                st.markdown(f"#### 🏆 {t('Top 10 Products by Qty','أعلى 10 منتجات حسب الكمية')}")
                prod_grp = (
                    po_df.fillna({"Model Code": "(No Code)", "Product": "(No Product)"})
                    .groupby(["Model Code", "Product"], as_index=False)["Qty"]
                    .sum()
                    .sort_values("Qty", ascending=False)
                    .head(10)
                    .reset_index(drop=True)
                )
                prod_grp["Total Qty"] = prod_grp["Qty"].map(lambda v: f"{v:,.0f}")
                ch1, ch2 = st.columns([1.4, 1])
                with ch1:
                    st.bar_chart(prod_grp.set_index("Model Code")["Qty"], use_container_width=True)
                with ch2:
                    _top10_table(prod_grp[["Model Code", "Product", "Total Qty"]])

                st.divider()

                st.markdown(f"#### 🗂️ {t('Top 10 Categories by Qty','أعلى 10 فئات حسب الكمية')}")
                cat_grp = (
                    po_df.copy()
                    .assign(Category=po_df["Category"].replace("", "(No Category)").fillna("(No Category)"))
                    .groupby("Category", as_index=False)["Qty"]
                    .sum()
                    .sort_values("Qty", ascending=False)
                    .head(10)
                    .reset_index(drop=True)
                )
                cat_grp["Total Qty"] = cat_grp["Qty"].map(lambda v: f"{v:,.0f}")
                cc1, cc2 = st.columns([1.4, 1])
                with cc1:
                    st.bar_chart(cat_grp.set_index("Category")["Qty"], use_container_width=True)
                with cc2:
                    _top10_table(cat_grp[["Category", "Total Qty"]])

                st.divider()

                st.markdown(f"#### 🏷️ {t('Top 10 Brand Categories by Qty','أعلى 10 فئات علامة تجارية حسب الكمية')}")
                bc_grp = (
                    po_df.copy()
                    .assign(**{"Brand Category": po_df["Brand Category"].replace("", "(No Brand)").fillna("(No Brand)")})
                    .groupby("Brand Category", as_index=False)["Qty"]
                    .sum()
                    .sort_values("Qty", ascending=False)
                    .head(10)
                    .reset_index(drop=True)
                )
                bc_grp["Total Qty"] = bc_grp["Qty"].map(lambda v: f"{v:,.0f}")
                bc1, bc2 = st.columns([1.4, 1])
                with bc1:
                    st.bar_chart(bc_grp.set_index("Brand Category")["Qty"], use_container_width=True)
                with bc2:
                    _top10_table(bc_grp[["Brand Category", "Total Qty"]])

                st.divider()
                st.markdown(f"#### 🏪 {t('Branch-wise Purchase Summary','ملخص المشتريات حسب الفرع')}")

                if "Vendor" in po_df.columns and "Qty" in po_df.columns and "Subtotal" in po_df.columns:
                    st.markdown(
                        "<div class='info-banner'>📌 "
                        + t("Purchase orders are not branch-specific. Showing vendor summary as proxy.",
                            "أوامر الشراء غير مرتبطة بفروع. يتم عرض ملخص الموردين بدلاً من ذلك.")
                        + "</div>",
                        unsafe_allow_html=True
                    )
                    vendor_pivot = (
                        po_df.groupby("Vendor", as_index=False)
                        .agg(
                            Total_Qty=("Qty", "sum"),
                            Total_Amount=("Subtotal", "sum"),
                            Order_Count=("PO", "nunique"),
                            Products=("Model Code", "nunique"),
                        )
                        .sort_values("Total_Qty", ascending=False)
                        .reset_index(drop=True)
                    )
                    vendor_pivot.columns = [
                        t("Vendor","المورد"),
                        t("Total Qty","إجمالي الكمية"),
                        t("Total Amount (SAR)","إجمالي المبلغ (ر.س)"),
                        t("PO Count","عدد أوامر الشراء"),
                        t("Products","المنتجات"),
                    ]
                    amt_col = t("Total Amount (SAR)","إجمالي المبلغ (ر.س)")
                    qty_col = t("Total Qty","إجمالي الكمية")
                    vendor_pivot[amt_col] = vendor_pivot[amt_col].map(lambda v: f"{v:,.2f}")
                    vendor_pivot[qty_col] = vendor_pivot[qty_col].map(lambda v: f"{v:,.0f}")
                    _render_html_table(vendor_pivot)
                    st.caption(f"📊 {len(vendor_pivot)} {t('vendors','موردين')}")

                st.divider()

                st.markdown(f"#### 📋 {t('Full Purchase Detail','تفاصيل المشتريات الكاملة')}")
                show_po = po_df.copy()
                show_po["Unit Price"] = show_po["Unit Price"].map(lambda v: f"{v:.2f} SAR")
                show_po["Subtotal"]   = show_po["Subtotal"].map(lambda v: f"{v:,.2f} SAR")
                show_po["Qty"]        = show_po["Qty"].map(lambda v: f"{v:,.0f}")

                cols_po = show_po.columns.tolist()
                th_po   = "".join(f"<th>{c}</th>" for c in cols_po)

                def _po_row(idx_row):
                    _, row = idx_row
                    cells = "".join(
                        f'<td class="cf">{v}</td>' if ci == 0 else f"<td>{v}</td>"
                        for ci, v in enumerate(row)
                    )
                    return f"<tr>{cells}</tr>"

                tbody_po = "".join(_po_row(x) for x in show_po.iterrows())
                st.markdown(
                    f'{_TABLE_CSS}<div class="swag-wrap">'
                    f'<table class="swag-tbl"><thead><tr>{th_po}</table></thead>'
                    f'<tbody>{tbody_po}</tbody></table></div>',
                    unsafe_allow_html=True
                )
                st.caption(f"📊 {len(show_po)} {t('rows','صفوف')}")

                display_df_purchase = po_df.copy()

                st.markdown("<br>", unsafe_allow_html=True)
                dl1, dl2, _ = st.columns([1, 1, 2])
                dl1.download_button(
                    "⬇️ CSV",
                    display_df_purchase.to_csv(index=False).encode("utf-8-sig"),
                    dl_name("purchase", "csv"), "text/csv",
                    use_container_width=True
                )
                dl2.download_button(
                    "⬇️ Excel",
                    to_excel_purchase(display_df_purchase),
                    dl_name("purchase", "xlsx"),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

    # ── Tab: SWAG Sales (unchanged) ──────────────────────────────────────────
    with tabs[ti]:
        ti += 1
        st.markdown(f"### 🛍️ {t('SWAG Sales Analytics','تحليلات مبيعات سواغ')}")
        st.markdown(
            "<div class='info-banner'>📌 "
            + t("Sales orders from the <b>SWAG</b> system only (state: sale / done).",
                "أوامر البيع من نظام <b>سواغ</b> فقط (الحالة: مباع / منجز).")
            + "</div>",
            unsafe_allow_html=True
        )

        so_col1, so_col2, so_col3, so_col4 = st.columns([1, 1, 1.5, 0.8])

        _today       = datetime.now().date()
        _first_month = _today.replace(day=1)

        with so_col1:
            so_date_from = st.date_input(
                f"📅 {t('From','من')}",
                value=_first_month,
                key="so_date_from"
            )
        with so_col2:
            so_date_to = st.date_input(
                f"📅 {t('To','إلى')}",
                value=_today,
                key="so_date_to"
            )
        with so_col3:
            so_model_filter = st.text_input(
                f"🔖 {t('Model Code (optional)','رمز الموديل (اختياري)')}",
                placeholder=t("e.g. XP6013 — leave blank for all","مثال: XP6013 — اتركه فارغاً للكل"),
                key="so_model_filter"
            ).strip()
        with so_col4:
            fetch_so_btn = st.button(
                f"🔍 {t('Fetch Sales','جلب المبيعات')}",
                type="primary",
                use_container_width=True,
                key="fetch_so_btn"
            )

        if fetch_so_btn:
            _date_from_str = so_date_from.strftime("%Y-%m-%d")
            _date_to_str   = so_date_to.strftime("%Y-%m-%d")
            _model_norm    = so_model_filter.upper() if so_model_filter else None
            with st.spinner(t("⚡ Fetching sales from SWAG…","⚡ جلب بيانات المبيعات من سواغ…")):
                _so_df = fetch_swag_sales_history(
                    model_code=_model_norm,
                    date_from=_date_from_str,
                    date_to=_date_to_str,
                )
            st.session_state["so_analytics_df"] = _so_df
            st.session_state["so_last_model"]   = so_model_filter

        so_df = st.session_state.get("so_analytics_df")

        if so_df is None or (isinstance(so_df, pd.DataFrame) and so_df.empty):
            st.info(t("Click 'Fetch Sales' to load data.", "اضغط 'جلب المبيعات' لتحميل البيانات."))
        else:
            total_qty_sold   = float(so_df["Qty"].sum())
            total_sales_amt  = float(so_df["Subtotal"].sum())
            distinct_custs   = int(so_df["Customer"].nunique())
            distinct_prods_s = int(so_df["Model Code"].nunique())

            sk1, sk2, sk3, sk4 = st.columns(4)
            sk1.metric(t("Total Qty Sold","إجمالي الكميات المباعة"),    f"{total_qty_sold:,.0f}")
            sk2.metric(t("Total Sales Amount","إجمالي مبلغ المبيعات"), f"{total_sales_amt:,.2f} SAR")
            sk3.metric(t("Distinct Customers","عدد العملاء"),           distinct_custs)
            sk4.metric(t("Distinct Products","عدد المنتجات"),          distinct_prods_s)

            st.divider()

            def _analytics_table(df_t):
                cols_t = df_t.columns.tolist()
                th_t   = "".join(f"<th>{c}</th>" for c in cols_t)
                def _tr(idx_row):
                    _, row = idx_row
                    cells = "".join(
                        f'<td class="cf">{v}</td>' if ci == 0 else f"<td>{v}</td>"
                        for ci, v in enumerate(row)
                    )
                    return f"<tr>{cells}</tr>"
                tbody_t = "".join(_tr(x) for x in df_t.iterrows())
                st.markdown(
                    f'{_TABLE_CSS}<div class="swag-wrap">'
                    f'<table class="swag-tbl"><thead><tr>{th_t}</tr></thead>'
                    f'<tbody>{tbody_t}</tbody></tr></div>',
                    unsafe_allow_html=True
                )

            st.markdown(f"#### 🏆 {t('Top 10 Products by Qty Sold','أعلى 10 منتجات حسب الكمية المباعة')}")
            prod_qty_grp = (
                so_df.fillna({"Model Code": "(No Code)", "Product": "(No Product)"})
                .groupby(["Model Code", "Product"], as_index=False)["Qty"]
                .sum()
                .sort_values("Qty", ascending=False)
                .head(10)
                .reset_index(drop=True)
            )
            prod_qty_grp["Total Qty"] = prod_qty_grp["Qty"].map(lambda v: f"{v:,.0f}")
            sq1, sq2 = st.columns([1.4, 1])
            with sq1:
                st.bar_chart(prod_qty_grp.set_index("Model Code")["Qty"], use_container_width=True)
            with sq2:
                _analytics_table(prod_qty_grp[["Model Code", "Product", "Total Qty"]])

            st.divider()

            st.markdown(f"#### 💰 {t('Top 10 Products by Revenue','أعلى 10 منتجات حسب الإيراد')}")
            prod_rev_grp = (
                so_df.fillna({"Model Code": "(No Code)", "Product": "(No Product)"})
                .groupby(["Model Code", "Product"], as_index=False)["Subtotal"]
                .sum()
                .sort_values("Subtotal", ascending=False)
                .head(10)
                .reset_index(drop=True)
            )
            prod_rev_grp["Revenue (SAR)"] = prod_rev_grp["Subtotal"].map(lambda v: f"{v:,.2f}")
            sr1, sr2 = st.columns([1.4, 1])
            with sr1:
                st.bar_chart(prod_rev_grp.set_index("Model Code")["Subtotal"], use_container_width=True)
            with sr2:
                _analytics_table(prod_rev_grp[["Model Code", "Product", "Revenue (SAR)"]])

            st.divider()

            st.markdown(f"#### 🏷️ {t('Top 10 Brand Categories by Qty','أعلى 10 فئات علامة تجارية حسب الكمية')}")
            brand_qty_grp = (
                so_df.copy()
                .assign(**{"Brand Category": so_df["Brand Category"].fillna("(No Brand)").replace("", "(No Brand)")})
                .groupby("Brand Category", as_index=False)["Qty"]
                .sum()
                .sort_values("Qty", ascending=False)
                .head(10)
                .reset_index(drop=True)
            )
            brand_qty_grp["Total Qty"] = brand_qty_grp["Qty"].map(lambda v: f"{v:,.0f}")
            sb1, sb2 = st.columns([1.4, 1])
            with sb1:
                st.bar_chart(brand_qty_grp.set_index("Brand Category")["Qty"], use_container_width=True)
            with sb2:
                _analytics_table(brand_qty_grp[["Brand Category", "Total Qty"]])

            st.divider()

            st.markdown(f"#### 🗂️ {t('Top 10 Categories by Qty','أعلى 10 فئات حسب الكمية')}")
            cat_qty_grp = (
                so_df.copy()
                .assign(Category=so_df["Category"].fillna("(No Category)").replace("", "(No Category)"))
                .groupby("Category", as_index=False)["Qty"]
                .sum()
                .sort_values("Qty", ascending=False)
                .head(10)
                .reset_index(drop=True)
            )
            cat_qty_grp["Total Qty"] = cat_qty_grp["Qty"].map(lambda v: f"{v:,.0f}")
            sc1, sc2 = st.columns([1.4, 1])
            with sc1:
                st.bar_chart(cat_qty_grp.set_index("Category")["Qty"], use_container_width=True)
            with sc2:
                _analytics_table(cat_qty_grp[["Category", "Total Qty"]])

            st.divider()

            st.markdown(f"#### 👥 {t('Top 10 Customers by Revenue','أعلى 10 عملاء حسب الإيراد')}")
            cust_rev_grp = (
                so_df.fillna({"Customer": "(Unknown)"})
                .groupby("Customer", as_index=False)["Subtotal"]
                .sum()
                .sort_values("Subtotal", ascending=False)
                .head(10)
                .reset_index(drop=True)
            )
            cust_rev_grp["Revenue (SAR)"] = cust_rev_grp["Subtotal"].map(lambda v: f"{v:,.2f}")
            cu1, cu2 = st.columns([1.4, 1])
            with cu1:
                st.bar_chart(cust_rev_grp.set_index("Customer")["Subtotal"], use_container_width=True)
            with cu2:
                _analytics_table(cust_rev_grp[["Customer", "Revenue (SAR)"]])

            st.divider()

            st.markdown(f"#### 🏪 {t('Branch Performance','أداء الفروع')}")
            branch_grp = (
                so_df.fillna({"Branch": "Unknown"})
                .groupby("Branch", as_index=False)
                .agg(Qty=("Qty","sum"), Subtotal=("Subtotal","sum"))
                .sort_values("Qty", ascending=False)
                .head(10)
                .reset_index(drop=True)
            )
            bx1, bx2 = st.columns(2)
            with bx1:
                st.markdown(f"**📦 {t('By Qty','حسب الكمية')}**")
                st.bar_chart(branch_grp.set_index("Branch")["Qty"], use_container_width=True)
            with bx2:
                st.markdown(f"**💰 {t('By Revenue','حسب الإيراد')}**")
                st.bar_chart(branch_grp.set_index("Branch")["Subtotal"], use_container_width=True)

            branch_tbl = branch_grp.copy()
            branch_tbl["Total Qty"]     = branch_tbl["Qty"].map(lambda v: f"{v:,.0f}")
            branch_tbl["Revenue (SAR)"] = branch_tbl["Subtotal"].map(lambda v: f"{v:,.2f}")
            _analytics_table(branch_tbl[["Branch", "Total Qty", "Revenue (SAR)"]])

            st.divider()

            try:
                import plotly.express as px

                def _sales_pie(df_p, col, val_col, title):
                    grp = df_p.groupby(col, as_index=False)[val_col].sum()
                    grp = grp.sort_values(val_col, ascending=False)
                    if len(grp) > 10:
                        top    = grp.head(9).copy()
                        others = pd.DataFrame([{col: "Others", val_col: grp.iloc[9:][val_col].sum()}])
                        grp    = pd.concat([top, others], ignore_index=True)
                    fig = px.pie(grp, names=col, values=val_col, title=title,
                                 hole=0.4,
                                 color_discrete_sequence=px.colors.sequential.Plasma_r)
                    fig.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font_color="#e8e8ff",
                        legend=dict(font=dict(color="#c4b5fd")),
                        title_font_color="#c4b5fd",
                    )
                    fig.update_traces(textfont_color="#ffffff")
                    return fig

                st.markdown(f"#### 🥧 {t('Sales Share (Revenue)','حصص المبيعات (الإيراد)')}")
                pie1, pie2, pie3 = st.columns(3)
                with pie1:
                    fig1 = _sales_pie(so_df, "Brand Category", "Subtotal",
                                      t("By Brand Category","حسب فئة العلامة"))
                    st.plotly_chart(fig1, use_container_width=True)
                with pie2:
                    fig2 = _sales_pie(so_df, "Category", "Subtotal",
                                      t("By Category","حسب الفئة"))
                    st.plotly_chart(fig2, use_container_width=True)
                with pie3:
                    fig3 = _sales_pie(so_df, "Customer", "Subtotal",
                                      t("By Customer","حسب العميل"))
                    st.plotly_chart(fig3, use_container_width=True)
                st.divider()

            except ImportError:
                st.info(t("Install plotly for pie charts: pip install plotly",
                          "ثبّت plotly لعرض الرسوم الدائرية: pip install plotly"))

            st.markdown(f"#### 📈 {t('Sales Trend (Daily)','اتجاه المبيعات (يومي)')}")
            trend_df = so_df.copy()
            trend_df["Date"] = pd.to_datetime(trend_df["Date"], errors="coerce")
            trend_df = trend_df.dropna(subset=["Date"])
            if not trend_df.empty:
                daily = (
                    trend_df.groupby(trend_df["Date"].dt.date, as_index=False)
                    .agg(Qty=("Qty","sum"), Revenue=("Subtotal","sum"))
                    .rename(columns={"Date":"date"})
                    .sort_values("date")
                )
                daily = daily.set_index("date")
                st.line_chart(daily[["Qty", "Revenue"]], use_container_width=True)
            else:
                st.info(t("No date data available for trend.","لا تتوفر بيانات للاتجاه الزمني."))

            st.divider()

            with st.expander(f"🔍 {t('Single Model Sales Detail','تفاصيل مبيعات موديل محدد')}"):
                detail_model = st.text_input(
                    t("Filter by Model Code","فلترة حسب رمز الموديل"),
                    placeholder="e.g. XP6013",
                    key="so_detail_model"
                ).strip().upper()

                detail_df = so_df.copy()
                if detail_model:
                    detail_df = detail_df[
                        detail_df["Model Code"].str.upper().str.startswith(detail_model)
                    ]

                if detail_df.empty:
                    st.info(t("No data for this model.","لا بيانات لهذا الموديل."))
                else:
                    dq = float(detail_df["Qty"].sum())
                    da = float(detail_df["Subtotal"].sum())
                    dc = int(detail_df["Customer"].nunique())
                    dd1, dd2, dd3 = st.columns(3)
                    dd1.metric(t("Total Qty","إجمالي الكمية"),    f"{dq:,.0f}")
                    dd2.metric(t("Total Amount","إجمالي المبلغ"), f"{da:,.2f} SAR")
                    dd3.metric(t("Customers","العملاء"),          dc)

                    cust_d = (
                        detail_df.groupby("Customer", as_index=False)["Subtotal"]
                        .sum().sort_values("Subtotal", ascending=False).head(10)
                    )
                    if not cust_d.empty:
                        st.markdown(f"**{t('Top Customers','أهم العملاء')}**")
                        st.bar_chart(cust_d.set_index("Customer")["Subtotal"],
                                     use_container_width=True)

                    time_d = detail_df.copy()
                    time_d["Date"] = pd.to_datetime(time_d["Date"], errors="coerce")
                    time_d = time_d.dropna(subset=["Date"])
                    if not time_d.empty:
                        daily_d = (
                            time_d.groupby(time_d["Date"].dt.date, as_index=False)
                            .agg(Qty=("Qty","sum"))
                            .set_index("Date")
                        )
                        st.markdown(f"**{t('Sales Over Time','المبيعات عبر الزمن')}**")
                        st.line_chart(daily_d, use_container_width=True)

                    try:
                        import plotly.express as px
                        cust_pie_df = (
                            detail_df.groupby("Customer", as_index=False)["Subtotal"].sum()
                            .sort_values("Subtotal", ascending=False)
                        )
                        if len(cust_pie_df) > 8:
                            top_c  = cust_pie_df.head(7).copy()
                            oth_c  = pd.DataFrame([{"Customer":"Others",
                                                     "Subtotal": cust_pie_df.iloc[7:]["Subtotal"].sum()}])
                            cust_pie_df = pd.concat([top_c, oth_c], ignore_index=True)
                        fig_cp = px.pie(cust_pie_df, names="Customer", values="Subtotal",
                                        title=t("Customer Revenue Share","حصة إيراد العملاء"),
                                        hole=0.4,
                                        color_discrete_sequence=px.colors.sequential.Plasma_r)
                        fig_cp.update_layout(
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            font_color="#e8e8ff",
                            legend=dict(font=dict(color="#c4b5fd")),
                            title_font_color="#c4b5fd",
                        )
                        fig_cp.update_traces(textfont_color="#ffffff")
                        st.plotly_chart(fig_cp, use_container_width=True)
                    except ImportError:
                        pass

            st.divider()

            st.markdown(f"#### 📋 {t('Full Sales Detail','تفاصيل المبيعات الكاملة')}")

            _so_detail_model = st.session_state.get("so_detail_model", "").strip().upper()
            if _so_detail_model:
                display_df_sales = so_df[
                    so_df["Model Code"].str.upper().str.startswith(_so_detail_model)
                ].copy()
            else:
                display_df_sales = so_df.copy()

            show_so = display_df_sales.copy()
            show_so["Date"]       = show_so["Date"].astype(str).str[:10]
            show_so["Unit Price"] = show_so["Unit Price"].map(lambda v: f"{v:.2f} SAR")
            show_so["Subtotal"]   = show_so["Subtotal"].map(lambda v: f"{v:,.2f} SAR")
            show_so["Qty"]        = show_so["Qty"].map(lambda v: f"{v:,.0f}")

            cols_so = show_so.columns.tolist()
            th_so   = "".join(f"<th>{c}</th>" for c in cols_so)

            def _so_row(idx_row):
                _, row = idx_row
                cells = "".join(
                    f'<td class="cf">{v}</td>' if ci == 0 else f"<td>{v}</td>"
                    for ci, v in enumerate(row)
                )
                return f"<tr>{cells}<tr>"

            tbody_so = "".join(_so_row(x) for x in show_so.iterrows())
            st.markdown(
                f'{_TABLE_CSS}<div class="swag-wrap">'
                f'<table class="swag-tbl"><thead><tr>{th_so}</tr></thead>'
                f'<tbody>{tbody_so}</tbody></table></div>',
                unsafe_allow_html=True
            )
            st.caption(f"📊 {len(show_so)} {t('rows','صفوف')}")

            st.markdown("<br>", unsafe_allow_html=True)
            sdl1, sdl2, _ = st.columns([1, 1, 2])
            sdl1.download_button(
                "⬇️ CSV",
                display_df_sales.assign(Date=display_df_sales["Date"].astype(str).str[:10])
                    .to_csv(index=False).encode("utf-8-sig"),
                dl_name("sales", "csv"), "text/csv",
                use_container_width=True,
                key="so_csv_dl"
            )
            sdl2.download_button(
                "⬇️ Excel",
                to_excel_sales(display_df_sales),
                dl_name("sales", "xlsx"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="so_excel_dl"
            )


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
restore_session()

if not st.session_state.authenticated:
    show_login()
else:
    show_dashboard()
