"""
SWAG Product Comparison Dashboard
Version 11.0 — Fixed Invoice Dedup + Dark Theme + Full Parallel
"""

import io
import re
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
# CSS + ANIMATIONS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

*, html, body, [class*="css"] {
    font-family: 'IBM Plex Sans Arabic', sans-serif;
    box-sizing: border-box;
}
.stApp {
    background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
    min-height: 100vh;
}
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%) !important;
    border-right: 1px solid #ffffff15;
}
section[data-testid="stSidebar"] *,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] div { color: #e8e8ff !important; }
section[data-testid="stSidebar"] input { color: #1a1a2e !important; }

@keyframes fadeInUp {
    from { opacity:0; transform:translateY(40px); }
    to   { opacity:1; transform:translateY(0); }
}
@keyframes fadeInDown {
    from { opacity:0; transform:translateY(-30px); }
    to   { opacity:1; transform:translateY(0); }
}
@keyframes bounceIn {
    0%   { transform:scale(0.2) rotate(-10deg); opacity:0; }
    60%  { transform:scale(1.2) rotate(5deg); opacity:1; }
    80%  { transform:scale(0.9); }
    100% { transform:scale(1); opacity:1; }
}
@keyframes shimmer {
    0%   { background-position:-400% center; }
    100% { background-position: 400% center; }
}
@keyframes pulse {
    0%,100% { box-shadow:0 0 0 0 #7c3aed44; }
    50%      { box-shadow:0 0 20px 8px #7c3aed22; }
}
@keyframes glow {
    0%,100% { text-shadow:0 0 10px #667eea88; }
    50%      { text-shadow:0 0 30px #f093fbcc, 0 0 60px #667eea88; }
}
@keyframes slideInLeft {
    from { opacity:0; transform:translateX(-40px); }
    to   { opacity:1; transform:translateX(0); }
}
@keyframes slideInRight {
    from { opacity:0; transform:translateX(40px); }
    to   { opacity:1; transform:translateX(0); }
}
@keyframes float {
    0%,100% { transform:translateY(0px); }
    50%      { transform:translateY(-8px); }
}
@keyframes btnShine {
    0%   { background-position:-200% center; }
    100% { background-position: 200% center; }
}
@keyframes borderGlow {
    0%,100% { border-color:#667eea; box-shadow:0 0 5px #667eea44; }
    50%      { border-color:#f093fb; box-shadow:0 0 15px #f093fb66; }
}
@keyframes countUp {
    from { opacity:0; transform:scale(0.5); }
    to   { opacity:1; transform:scale(1); }
}

/* ── LOGIN ── */
.login-orb {
    width:120px; height:120px; border-radius:50%;
    background:linear-gradient(135deg,#667eea,#764ba2,#f093fb);
    display:flex; align-items:center; justify-content:center;
    font-size:3rem; margin:0 auto 20px;
    animation:float 3s ease-in-out infinite, bounceIn 1s ease forwards;
    box-shadow:0 8px 40px #667eea66, 0 0 60px #f093fb33;
}
.login-title {
    font-size:2.4rem; font-weight:700;
    background:linear-gradient(90deg,#667eea,#f093fb,#667eea);
    background-size:200% auto;
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    animation:shimmer 3s linear infinite, fadeInDown 0.8s ease forwards;
    text-align:center; margin-bottom:6px;
}
.login-subtitle {
    color:#c4b5fd !important; font-size:0.95rem; text-align:center;
    animation:fadeInUp 1s ease forwards; margin-bottom:28px;
}
.login-card {
    background:linear-gradient(145deg,#1e1e3f,#2d2b55);
    border:1px solid #ffffff18; border-radius:20px;
    padding:32px 36px; width:100%;
    animation:fadeInUp 0.9s ease forwards, pulse 3s infinite;
}
.welcome-banner {
    background:linear-gradient(135deg,#667eea22,#f093fb22);
    border:1px solid #667eea44; border-radius:12px;
    padding:14px 20px; text-align:center; margin-bottom:20px;
    font-size:0.95rem; color:#c4b5fd !important;
    animation:fadeInDown 0.7s ease forwards, borderGlow 3s infinite;
}

/* ── INPUTS ── */
.stTextInput input, .stNumberInput input, .stTextArea textarea {
    background:#1e1e3f !important;
    border:1px solid #667eea66 !important;
    border-radius:10px !important;
    color:#e8e8ff !important;
    caret-color:#c4b5fd !important;
    transition:all 0.3s ease !important;
}
.stTextInput input::placeholder,
.stNumberInput input::placeholder,
.stTextArea textarea::placeholder { color:#7070aa !important; }
.stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
    border-color:#667eea !important;
    box-shadow:0 0 0 3px #667eea33 !important;
    background:#252550 !important;
}
.stTextInput label, .stNumberInput label, .stTextArea label {
    color:#c4b5fd !important; font-weight:600 !important;
}

/* ── BUTTONS ── */
.stFormSubmitButton button, .stButton button[kind="primary"] {
    background:linear-gradient(90deg,#667eea,#764ba2,#f093fb,#667eea) !important;
    background-size:300% auto !important;
    border:none !important; border-radius:12px !important;
    color:white !important; font-weight:700 !important;
    font-size:1rem !important; padding:12px !important;
    animation:btnShine 3s linear infinite !important;
    transition:transform 0.2s, box-shadow 0.2s !important;
    box-shadow:0 4px 20px #667eea55 !important;
}
.stFormSubmitButton button:hover, .stButton button[kind="primary"]:hover {
    transform:translateY(-2px) scale(1.02) !important;
    box-shadow:0 8px 30px #764ba299 !important;
}
.stButton button[kind="secondary"] {
    background:#1e1e3f !important; border:1px solid #667eea66 !important;
    color:#c4b5fd !important; border-radius:10px !important;
}
.stButton button[kind="secondary"]:hover {
    background:linear-gradient(135deg,#667eea,#764ba2) !important;
    color:white !important;
}
.stButton button { color:#c4b5fd !important; }

/* ── DOWNLOAD BUTTONS ── */
.stDownloadButton button {
    background:linear-gradient(135deg,#1e1e3f,#2d2b55) !important;
    border:1px solid #667eea66 !important; border-radius:10px !important;
    color:#c4b5fd !important; font-size:0.78rem !important;
    font-weight:600 !important; padding:6px 14px !important;
    transition:all 0.25s ease !important;
    box-shadow:0 2px 8px #00000044 !important;
}
.stDownloadButton button:hover {
    background:linear-gradient(135deg,#667eea,#764ba2) !important;
    color:white !important; border-color:transparent !important;
    transform:translateY(-2px) scale(1.04) !important;
    box-shadow:0 6px 20px #667eea55 !important;
}
.stDownloadButton button:active { transform:scale(0.97) !important; }

/* ── DASHBOARD HEADER ── */
.dash-header { text-align:center; padding:16px 0 24px; animation:fadeInDown 0.6s ease forwards; }
.dash-title {
    font-size:2.4rem; font-weight:700;
    background:linear-gradient(90deg,#667eea,#f093fb,#43e97b,#667eea);
    background-size:300% auto;
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    animation:shimmer 4s linear infinite, glow 3s ease-in-out infinite;
}
.dash-subtitle { color:#a0aec0; font-size:0.95rem; margin-top:-4px; }

/* ── METRIC CARDS ── */
[data-testid="stMetric"] {
    background:linear-gradient(135deg,#1e1e3f,#2d2b55) !important;
    border:1px solid #ffffff15 !important; border-radius:16px !important;
    padding:16px 20px !important; animation:countUp 0.6s ease forwards;
    transition:transform 0.2s, box-shadow 0.2s;
}
[data-testid="stMetric"]:hover { transform:translateY(-4px); box-shadow:0 8px 30px #667eea44; }
[data-testid="stMetricLabel"] { color:#a0aec0 !important; font-size:0.82rem !important; }
[data-testid="stMetricValue"] {
    font-size:1.7rem !important; font-weight:700 !important;
    background:linear-gradient(90deg,#667eea,#f093fb);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
}

/* ── TABLE ── */
[data-testid="stDataFrame"] {
    border-radius:16px !important; overflow:hidden !important;
    border:1px solid #ffffff15 !important;
    box-shadow:0 4px 24px #0000005a !important;
    animation:fadeInUp 0.5s ease forwards;
}
[data-testid="stDataFrame"] thead tr th {
    background:linear-gradient(90deg,#667eea,#764ba2) !important;
    color:white !important; font-weight:700 !important;
    font-size:0.84rem !important; text-align:center !important;
    padding:12px 8px !important;
}
[data-testid="stDataFrame"] tbody tr td {
    color:#1a1a2e !important; font-size:0.85rem !important;
    text-align:center !important; padding:8px !important;
    font-weight:500 !important;
}
[data-testid="stDataFrame"] tbody tr:nth-child(even) td { background:#f0f4ff !important; }
[data-testid="stDataFrame"] tbody tr:nth-child(odd)  td { background:#ffffff !important; }
[data-testid="stDataFrame"] tbody tr:hover td {
    background:#e8eeff !important; transition:background 0.2s ease !important;
}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
    background:linear-gradient(90deg,#1e1e3f,#2d2b55);
    border-radius:12px; padding:4px; gap:4px;
}
.stTabs [data-baseweb="tab"] {
    color:#a0aec0 !important; border-radius:10px !important;
    font-size:0.83rem !important; font-weight:600 !important;
    padding:8px 16px !important; transition:all 0.2s ease !important;
}
.stTabs [aria-selected="true"] {
    background:linear-gradient(90deg,#667eea,#764ba2) !important;
    color:white !important; box-shadow:0 4px 12px #667eea55 !important;
}

/* ── BANNERS ── */
.info-banner {
    background:linear-gradient(135deg,#1e3a5f,#1e3a5f99);
    border-left:4px solid #3b82f6; border-radius:10px;
    padding:11px 16px; margin:8px 0 16px;
    font-size:0.85rem; color:#93c5fd !important; animation:slideInLeft 0.4s ease;
}
.warn-banner {
    background:linear-gradient(135deg,#3b2a0a,#3b2a0a99);
    border-left:4px solid #f59e0b; border-radius:10px;
    padding:11px 16px; margin:8px 0 16px;
    font-size:0.85rem; color:#fcd34d !important;
}
.alert-banner {
    background:linear-gradient(135deg,#3b0a1e,#3b0a1e99);
    border-left:4px solid #f43f5e; border-radius:10px;
    padding:11px 16px; margin:8px 0 16px;
    font-size:0.85rem; color:#fca5a5 !important; animation:pulse 2s infinite;
}
.ok-banner {
    background:linear-gradient(135deg,#0a3b1e,#0a3b1e99);
    border-left:4px solid #22c55e; border-radius:10px;
    padding:11px 16px; margin:8px 0 16px;
    font-size:0.85rem; color:#86efac !important;
}

/* ── SNAP CARD & BADGES ── */
.snap-card {
    background:linear-gradient(145deg,#1e1e3f,#2d2b55);
    border:1px solid #ffffff18; border-radius:14px;
    padding:16px 20px; font-size:0.87rem;
    color:#e8e8ff !important; line-height:2;
    animation:slideInRight 0.5s ease; box-shadow:0 4px 20px #00000055;
}
.snap-card b { color:#c4b5fd !important; }
.sys-row { display:flex; align-items:center; gap:8px; margin-bottom:6px; }
.sys-row span { color:#e8e8ff !important; }
.badge-ok  { background:linear-gradient(90deg,#065f46,#047857); color:#d1fae5 !important; border-radius:20px; padding:3px 12px; font-size:0.76rem; font-weight:700; }
.badge-off { background:linear-gradient(90deg,#991b1b,#b91c1c); color:#fee2e2 !important; border-radius:20px; padding:3px 12px; font-size:0.76rem; font-weight:700; }
.badge-err { background:linear-gradient(90deg,#78350f,#92400e); color:#fef3c7 !important; border-radius:20px; padding:3px 12px; font-size:0.76rem; font-weight:700; }

/* ── RADIO / TOGGLE ── */
.stRadio label, .stRadio div[role="radiogroup"] label span,
[data-testid="stToggle"] label, .stCheckbox label { color:#e8e8ff !important; }
div[data-testid="stRadio"] p { color:#e8e8ff !important; }

/* ── HEADINGS & TEXT ── */
h1,h2,h3,h4,h5,h6 { color:#e8e8ff !important; }
.stMarkdown p, .stMarkdown li { color:#c4b5fd !important; }
.stCaption, [data-testid="stCaptionContainer"] p { color:#8888bb !important; }
.stAlert p { color:#1a1a2e !important; font-weight:600; }

/* ── EXPANDER ── */
[data-testid="stExpander"] {
    background:linear-gradient(135deg,#1e1e3f,#2d2b55) !important;
    border:1px solid #ffffff18 !important; border-radius:12px !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p { color:#c4b5fd !important; }

/* ── FILE UPLOADER ── */
[data-testid="stFileUploader"] {
    background:linear-gradient(135deg,#1e1e3f,#2d2b55) !important;
    border:2px dashed #667eea66 !important; border-radius:14px !important;
    transition:border-color 0.3s, box-shadow 0.3s !important;
}
[data-testid="stFileUploader"]:hover {
    border-color:#f093fb !important; box-shadow:0 0 20px #f093fb33 !important;
}
[data-testid="stFileUploader"] p,
[data-testid="stFileUploader"] span { color:#c4b5fd !important; }

/* ── DIVIDER ── */
hr {
    border:none !important; height:1px !important;
    background:linear-gradient(90deg,transparent,#667eea66,transparent) !important;
    margin:16px 0 !important;
}

/* ── PROGRESS BAR ── */
[data-testid="stProgressBar"] > div {
    background:linear-gradient(90deg,#667eea,#f093fb) !important;
    border-radius:10px !important;
}

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width:6px; height:6px; }
::-webkit-scrollbar-track { background:#1a1a2e; }
::-webkit-scrollbar-thumb { background:linear-gradient(#667eea,#764ba2); border-radius:10px; }
::-webkit-scrollbar-thumb:hover { background:#f093fb; }

.stNumberInput button { color:#c4b5fd !important; background:#2d2b55 !important; }
.mono { font-family:'IBM Plex Mono',monospace; font-size:0.82rem; color:#c4b5fd; }
footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SECRETS & CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
secrets     = st.secrets
SYSTEM_KEYS = ["SWAG", "LAROUCHE", "DIFFC", "FASHION_LIMITS"]

# ─────────────────────────────────────────────────────────────────────────────
# LANGUAGE
# ─────────────────────────────────────────────────────────────────────────────
def get_lang() -> str:
    return st.session_state.get("lang", "EN")

def t(en: str, ar: str) -> str:
    return ar if get_lang() == "AR" else en

def get_system_name(key: str) -> str:
    cfg = secrets.get(key, {})
    return cfg.get("name_ar", cfg.get("name", key)) if get_lang() == "AR" else cfg.get("name", key)

# ─────────────────────────────────────────────────────────────────────────────
# EXCEL HELPERS — STYLED
# ─────────────────────────────────────────────────────────────────────────────
def _style_worksheet(ws, df_clean):
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    hfill  = PatternFill("solid", fgColor="667EEA")
    afill  = PatternFill("solid", fgColor="F0F4FF")
    thin   = Side(border_style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for col_num, col_name in enumerate(df_clean.columns, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill      = hfill
        cell.font      = Font(bold=True, color="FFFFFF", size=11)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border    = border
        col_vals = [str(v) for v in df_clean.iloc[:, col_num - 1]]
        max_len  = max(len(str(col_name)), max((len(v) for v in col_vals), default=0))
        ws.column_dimensions[get_column_letter(col_num)].width = min(max_len + 4, 40)
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for cell in row:
            cell.border    = border
            cell.alignment = Alignment(horizontal="center", vertical="center")
            if cell.row % 2 == 0:
                cell.fill = afill
    ws.row_dimensions[1].height = 22
    ws.freeze_panes = "A2"

def to_csv(df: pd.DataFrame) -> bytes:
    return df.drop(columns=["_status"], errors="ignore").to_csv(index=False).encode("utf-8-sig")

def to_excel(df: pd.DataFrame) -> bytes:
    buf   = io.BytesIO()
    clean = df.drop(columns=["_status"], errors="ignore")
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        clean.to_excel(w, index=False, sheet_name="Data")
        _style_worksheet(w.sheets["Data"], clean)
    return buf.getvalue()

def to_excel_bulk(df: pd.DataFrame) -> bytes:
    buf     = io.BytesIO()
    sys_col = t("System", "النظام")
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        def _ws(data, name):
            c = data.drop(columns=["_status"], errors="ignore")
            c.to_excel(w, index=False, sheet_name=name[:31])
            _style_worksheet(w.sheets[name[:31]], c)
        _ws(df, t("All Systems", "كل الأنظمة"))
        if sys_col in df.columns:
            for key in SYSTEM_KEYS:
                nm  = get_system_name(key)
                sub = df[df[sys_col] == nm]
                if not sub.empty:
                    _ws(sub, nm)
    return buf.getvalue()

def dl_name(tag: str, ext: str) -> str:
    return f"swag_{tag}_{datetime.now().strftime('%Y%m%d_%H%M')}.{ext}"

# ─────────────────────────────────────────────────────────────────────────────
# XML-RPC — CACHED PROXY + AUTH
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def _get_proxy(url: str, endpoint: str):
    return xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/{endpoint}", allow_none=True)

@st.cache_data(ttl=3600, show_spinner=False)
def _auth_cached(url: str, db: str, user: str, api_key: str):
    try:
        uid = _get_proxy(url, "common").authenticate(db, user, api_key, {})
        return uid or None
    except Exception:
        return None

def _exec(url, db, uid, api_key, model, method, domain, kwargs):
    return _get_proxy(url, "object").execute_kw(db, uid, api_key, model, method, domain, kwargs)

# ─────────────────────────────────────────────────────────────────────────────
# DOMAIN BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def _build_domain(codes: list, exact: bool) -> list:
    if exact:
        return [["default_code", "in", codes]]
    if len(codes) == 1:
        return [["default_code", "=like", f"{codes[0]}%"]]
    or_parts = [["default_code", "=like", f"{c}%"] for c in codes]
    return ["|"] * (len(or_parts) - 1) + or_parts

# ─────────────────────────────────────────────────────────────────────────────
# PDF PARSING — FIXED DEDUP
# ─────────────────────────────────────────────────────────────────────────────
def extract_base_model(code: str) -> str:
    code = re.sub(r'\([^)]*\)', '', code)
    for size in ['-2XL','-3XL','-4XL','-XXL','-XL','-L','-M','-S','-XS',
                 '-2xl','-3xl','-xxl','-xl','-2X','-3X']:
        if code.upper().endswith(size.upper()):
            code = code[:-len(size)]
            break
    code = re.sub(r'-\d{2,3}$', '', code)
    return code.strip()

def get_unique_base_models(raw_codes: list) -> list:
    """XP6013-S, XP6013-M, XP6013-L → [XP6013]  (only 1, not 3)"""
    seen, result = set(), []
    for code in raw_codes:
        base = extract_base_model(code)
        if base and base not in seen:
            seen.add(base)
            result.append(base)
    return result

def parse_invoice_pdf(uploaded_file) -> list:
    try:
        from pypdf import PdfReader
    except ImportError:
        st.error("Add pypdf>=3.0.0 to requirements.txt"); return []
    full_text = ""
    for page in PdfReader(io.BytesIO(uploaded_file.read())).pages:
        full_text += (page.extract_text() or "") + "\n"
    if not full_text.strip(): return []

    EXCLUDE = {'SR','VAT','TAX','PCS','QTY','NO','REF','INV','PO','SO','DO','ID',
               'EN','AR','PDF','AED','SAR','USD','KWD','OMR','BHD','JOD','EGP','TRY'}

    def is_valid(code):
        code = code.strip().upper()
        if not re.search(r'[A-Z]', code): return False
        if not re.search(r'\d', code):    return False
        if len(code) < 4 or len(code) > 25: return False
        if code in EXCLUDE: return False
        return True

    s1 = re.findall(r'\[([A-Za-z0-9\-_()]{3,30})\]', full_text)
    s2 = []
    for m in re.finditer(
        r'(?:^|\s)([A-Z]{2,6}\d+(?:-\d+)?(?:-[A-Z0-9()]{1,10})?)\s+.{0,80}?\d+\.?\d*\s+SR',
        full_text, re.MULTILINE):
        s2.append(m.group(1))
    s3 = re.findall(
        r'\b([A-Z]{2,6}\d+(?:-\d+)?(?:-[A-Z0-9]{1,4})?(?:\([^)]{1,15}\))?)\b', full_text)

    all_codes = [c.strip().upper() for c in (s1 + s2 + s3) if is_valid(c.strip())]
    seen, unique = set(), []
    for code in all_codes:
        if code not in seen:
            seen.add(code); unique.append(code)
    return unique

# ─────────────────────────────────────────────────────────────────────────────
# FETCH ALL DATA — FULLY PARALLEL
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def fetch_all_data(
    codes_tuple: tuple, exact: bool = False,
    need_branch: bool = False, need_transfers: bool = False, need_reorder: bool = False,
    reorder_mode: str = "days_cover", target_days: int = 30,
    max_level: int = 100, reorder_point: int = 10,
) -> dict:
    DAYS  = 30
    dfrom = (datetime.now() - timedelta(days=DAYS)).strftime("%Y-%m-%d 00:00:00")
    codes  = list(codes_tuple)
    domain = _build_domain(codes, exact)

    CS=t("System","النظام"); CM=t("Model Code","رمز الموديل"); CPR=t("Product","المنتج")
    CP=t("Sale Price","سعر البيع"); CQ=t("On Hand","متوفر"); CB=t("Branch","الفرع")
    CL=t("Location","الموقع"); CR=t("Reference","المرجع"); CT=t("Type","النوع")
    CST=t("State","الحالة"); CF=t("From","من"); CTO=t("To","إلى")
    CQT=t("Qty","الكمية"); CD=t("Scheduled","المجدول")
    CSOLD=t("Sold(30d)","مباع(30ي)"); CVEL=t("Daily Vel","معدل/يوم")
    CDAY=t("Days Left","أيام متبقية"); CSUGG=t("Suggest","المقترح")
    CPRI=t("Priority","الأولوية")
    state_map={"draft":t("Draft","مسودة"),"waiting":t("Waiting","انتظار"),
               "confirmed":t("Confirmed","مؤكد"),"assigned":t("Ready","جاهز")}

    def _fetch_system(key):
        cfg=secrets.get(key); sn=get_system_name(key)
        result={"key":key,"total":[],"branch":[],"transfers":[],"reorder":[]}
        if not cfg:
            result["total"].append({CS:sn,CM:"—",CPR:"No config",CP:0.0,CQ:0,"_status":"ERROR"})
            return result
        uid=_auth_cached(cfg["url"],cfg["db"],cfg["user"],cfg["api_key"])
        if not uid:
            result["total"].append({CS:sn,CM:"—",CPR:t("⚠️ Auth failed","⚠️ فشل التحقق"),
                                     CP:0.0,CQ:0,"_status":"ERROR"})
            return result
        url=cfg["url"]; db=cfg["db"]; ak=cfg["api_key"]
        try:
            prods=_exec(url,db,uid,ak,"product.product","search_read",[domain],
                        {"fields":["id","display_name","default_code","qty_available","list_price"],
                         "limit":2000})
            if not prods:
                result["total"].append({CS:sn,CM:"—",CPR:t("Not found","غير موجود"),
                                         CP:0.0,CQ:0,"_status":"NOT_FOUND"})
                return result
            prod_ids=[p["id"] for p in prods]
            prod_map={p["id"]:p for p in prods}

            for p in prods:
                result["total"].append({
                    CS:sn, CM:p.get("default_code") or "—",
                    CPR:p.get("display_name") or "",
                    CP:float(p.get("list_price") or 0),
                    CQ:int(p.get("qty_available") or 0), "_status":"OK"})

            if need_branch:
                quants=_exec(url,db,uid,ak,"stock.quant","search_read",
                             [[["product_id","in",prod_ids],["quantity",">",0]]],
                             {"fields":["product_id","location_id","quantity"],"limit":5000})
                for q in quants:
                    pid=q["product_id"][0] if isinstance(q.get("product_id"),list) else None
                    loc=q.get("location_id") or [None,"—"]
                    loc_name=loc[1] if isinstance(loc,list) else str(loc)
                    branch=loc_name.split("/")[0].strip()
                    pm=prod_map.get(pid,{})
                    result["branch"].append({
                        CS:sn, CB:branch, CM:pm.get("default_code") or "—",
                        CL:loc_name, CP:float(pm.get("list_price") or 0),
                        CQ:int(q.get("quantity") or 0), "_status":"OK"})

            if need_transfers:
                moves=_exec(url,db,uid,ak,"stock.move","search_read",
                            [[["product_id","in",prod_ids],
                              ["state","in",["draft","waiting","confirmed","assigned"]]]],
                            {"fields":["picking_id","product_id","product_uom_qty","state"],
                             "limit":2000})
                if moves:
                    pick_ids=list({m["picking_id"][0] for m in moves
                                   if isinstance(m.get("picking_id"),list)})
                    if pick_ids:
                        picks=_exec(url,db,uid,ak,"stock.picking","search_read",
                                    [[["id","in",pick_ids]]],
                                    {"fields":["id","name","picking_type_id","state",
                                               "location_id","location_dest_id","scheduled_date"]})
                        pick_map={p["id"]:p for p in picks}
                        for move in moves:
                            pr=move.get("picking_id")
                            if not isinstance(pr,list): continue
                            pick=pick_map.get(pr[0],{})
                            def _n(f,_p=pick):
                                v=_p.get(f); return v[1] if isinstance(v,list) else (v or "—")
                            sched=pick.get("scheduled_date") or "—"
                            if sched!="—":
                                try: sched=datetime.strptime(sched,"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
                                except: pass
                            pid2=move["product_id"][0] if isinstance(move.get("product_id"),list) else None
                            pm2=prod_map.get(pid2,{})
                            result["transfers"].append({
                                CS:sn, CR:pick.get("name") or "—", CT:_n("picking_type_id"),
                                CST:state_map.get(pick.get("state",""),pick.get("state","")),
                                CF:_n("location_id"), CTO:_n("location_dest_id"),
                                CM:pm2.get("default_code") or "—",
                                CQT:int(move.get("product_uom_qty") or 0),
                                CD:sched, "_status":"OK"})

            if need_reorder:
                sol_all=_exec(url,db,uid,ak,"sale.order.line","search_read",
                              [[["product_id","in",prod_ids],
                                ["order_id.state","in",["sale","done"]],
                                ["order_id.date_order",">=",dfrom]]],
                              {"fields":["product_id","product_uom_qty"],"limit":10000})
                sold_map={}
                for l in sol_all:
                    pid=l["product_id"][0] if isinstance(l.get("product_id"),list) else None
                    if pid: sold_map[pid]=sold_map.get(pid,0)+float(l.get("product_uom_qty") or 0)
                for p in prods:
                    pid=p["id"]; cq=int(p.get("qty_available") or 0)
                    sold=sold_map.get(pid,0); vel=round(sold/DAYS,2)
                    days_lbl=str(round(cq/vel,1)) if vel>0 else t("∞","∞")
                    sugg=max(0,round(target_days*vel-cq)) if reorder_mode=="days_cover" else max(0,max_level-cq)
                    pri=(t("🔴 Critical","🔴 حرج") if cq<=0
                         else t("🟡 Low","🟡 منخفض") if cq<=reorder_point
                         else t("🟢 OK","🟢 كافٍ"))
                    result["reorder"].append({
                        CS:sn, CM:p.get("default_code") or "—",
                        CPR:p.get("display_name") or "",
                        CQ:cq, CSOLD:int(sold), CVEL:vel,
                        CDAY:days_lbl, CSUGG:sugg, CPRI:pri, "_status":"OK"})
        except Exception as e:
            result["total"].append({CS:sn,CM:"—",CPR:f"❌ {e}",CP:0.0,CQ:0,"_status":"ERROR"})
        return result

    all_total=[]; all_branch=[]; all_transfers=[]; all_reorder=[]
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures={ex.submit(_fetch_system,key):key for key in SYSTEM_KEYS}
        for fut in as_completed(futures):
            res=fut.result()
            all_total.extend(res["total"]); all_branch.extend(res["branch"])
            all_transfers.extend(res["transfers"]); all_reorder.extend(res["reorder"])

    def _df(rows,cols):
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=cols)
    return {
        "total":     _df(all_total,    [CS,CM,CPR,CP,CQ,"_status"]),
        "branch":    _df(all_branch,   [CS,CB,CM,CL,CP,CQ,"_status"]),
        "transfers": _df(all_transfers,[CS,CR,CT,CST,CF,CTO,CM,CQT,CD,"_status"]),
        "reorder":   _df(all_reorder,  [CS,CM,CPR,CQ,CSOLD,CVEL,CDAY,CSUGG,CPRI,"_status"]),
    }

# ─────────────────────────────────────────────────────────────────────────────
# PRICE HISTORY
# ─────────────────────────────────────────────────────────────────────────────
def record_price_snapshot(df):
    pc=t("Sale Price","سعر البيع"); sc=t("System","النظام"); mc=t("Model Code","رمز الموديل")
    if pc not in df.columns: return
    ok=df[df["_status"]=="OK"] if "_status" in df.columns else df
    if ok.empty: return
    ts=datetime.now().strftime("%H:%M:%S")
    for _,row in ok.iterrows():
        k=f"{row.get(sc,'?')} | {row.get(mc,'?')}"
        if k not in st.session_state.price_history: st.session_state.price_history[k]=[]
        st.session_state.price_history[k].append({"time":ts,"price":float(row.get(pc,0))})

def build_price_history_df():
    hist=st.session_state.price_history
    if not hist: return pd.DataFrame()
    all_times=sorted({e["time"] for v in hist.values() for e in v})
    records=[]
    for ts in all_times:
        row={"time":ts}
        for k,entries in hist.items():
            px=[e["price"] for e in entries if e["time"]==ts]
            row[k]=px[-1] if px else None
        records.append(row)
    return pd.DataFrame(records).set_index("time")

# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY DF
# ─────────────────────────────────────────────────────────────────────────────
def display_df(df, thresh=0):
    if df is None or df.empty:
        st.info(t("No data.","لا بيانات.")); return
    pc=t("Sale Price","سعر البيع"); qc=t("On Hand","متوفر")
    show=df.drop(columns=["_status"],errors="ignore")
    cfg={}
    if pc in show.columns: cfg[pc]=st.column_config.NumberColumn(pc,format="%.2f SAR",min_value=0)
    if qc in show.columns: cfg[qc]=st.column_config.NumberColumn(qc,format="%d",      min_value=0)
    if thresh>0 and qc in show.columns:
        def _hl(row):
            q=row.get(qc)
            if q is not None and isinstance(q,(int,float)) and 0<q<=thresh:
                return ["background-color:#ffe4e6"]*len(row)
            return [""]*len(row)
        st.dataframe(show.style.apply(_hl,axis=1),
                     use_container_width=True,column_config=cfg,hide_index=True)
    else:
        st.dataframe(show,use_container_width=True,column_config=cfg,hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE — PERSISTENT
# ─────────────────────────────────────────────────────────────────────────────
_DEFAULTS={
    "authenticated":False,"user_email":"","lang":"EN",
    "last_run":None,"total_df":None,"branch_df":None,
    "transfers_df":None,"reorder_df":None,"sys_stats":{},
    "search_exact":False,"low_stock_thresh":5,"price_history":{},
    "show_transfers":False,"show_reorder":False,
    "reorder_mode":"days_cover","reorder_target_days":30,
    "reorder_max_level":100,"reorder_point":10,
    "pdf_codes":None,"pdf_mode":"total",
}
for _k,_v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k]=_v

# ─────────────────────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────────────────────
def show_login():
    _,_,lcol=st.columns([2,1,0.5])
    with lcol:
        lang_login=st.radio("",["EN","AR"],horizontal=True,
                            index=0 if get_lang()=="EN" else 1,
                            label_visibility="collapsed",key="lang_login_radio")
        if lang_login!=get_lang():
            st.session_state.lang=lang_login; st.rerun()

    _,col,_=st.columns([1,1.1,1])
    with col:
        st.markdown("""
        <div style='display:flex;flex-direction:column;align-items:center;padding:20px 0 8px;'>
            <div class='login-orb'>📊</div>
            <div class='login-title'>SWAG Dashboard</div>
            <div class='login-subtitle'>Real-time Stock &amp; Price · 4 Odoo Systems</div>
        </div>
        """,unsafe_allow_html=True)

        welcome_msg=("🌙 مرحباً بك — سجّل دخولك للمتابعة"
                     if get_lang()=="AR" else
                     "👋 Welcome back! Sign in to continue.")
        st.markdown(f"<div class='welcome-banner'>{welcome_msg}</div>",
                    unsafe_allow_html=True)

        st.markdown("<div class='login-card'>",unsafe_allow_html=True)
        with st.form("login_form",clear_on_submit=False):
            email_lbl="📧 البريد الإلكتروني" if get_lang()=="AR" else "📧 Email"
            pass_lbl ="🔑 كلمة المرور"        if get_lang()=="AR" else "🔑 Password"
            btn_lbl  ="🚀 تسجيل الدخول"       if get_lang()=="AR" else "🚀 Sign In"
            email   =st.text_input(email_lbl,placeholder="you@swag.com.sa")
            password=st.text_input(pass_lbl, type="password",placeholder="••••••••")
            st.markdown("<br>",unsafe_allow_html=True)
            submit  =st.form_submit_button(btn_lbl,use_container_width=True,type="primary")
        st.markdown("</div>",unsafe_allow_html=True)

        if submit:
            if not email or not password:
                st.error(t("Please fill in both fields.","يرجى ملء جميع الحقول.")); return
            with st.spinner(t("⚡ Signing in…","⚡ جارٍ تسجيل الدخول…")):
                try:
                    cfg=secrets["LOGIN"]
                    uid=_auth_cached(cfg["url"],cfg["db"],email,password)
                    if uid:
                        st.session_state.authenticated=True
                        st.session_state.user_email=email
                        st.balloons(); st.rerun()
                    else:
                        st.error(t("❌ Invalid credentials.","❌ بيانات غير صحيحة."))
                except Exception as e:
                    st.error(f"Connection error: {e}")

        st.markdown("""
        <p style='text-align:center;color:#4a4a6a;font-size:0.75rem;margin-top:24px;'>
        © 2025 SWAG Fashion · Powered by Odoo · Built with ❤️
        </p>""",unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def show_dashboard():

    with st.sidebar:
        st.markdown(f"### ⚙️ {t('Settings','الإعدادات')}")
        lang_choice=st.radio(t("🌐 Language","🌐 اللغة"),["EN","AR"],
                             index=0 if get_lang()=="EN" else 1,horizontal=True)
        if lang_choice!=get_lang():
            st.session_state.lang=lang_choice; st.rerun()
        st.divider()
        st.markdown(f"👤 **{st.session_state.user_email}**")
        if st.button(f"🚪 {t('Logout','تسجيل الخروج')}",use_container_width=True):
            st.session_state.authenticated=False
            st.session_state.user_email=""
            st.rerun()
        st.divider()
        st.markdown(f"##### 🔬 {t('Search Mode','وضع البحث')}")
        exact_tog=st.toggle(t("Exact match only","تطابق تام فقط"),
                            value=st.session_state.search_exact)
        if exact_tog!=st.session_state.search_exact:
            st.session_state.search_exact=exact_tog
            st.session_state.total_df=st.session_state.branch_df=st.session_state.transfers_df=None
            st.rerun()
        st.caption(t("🎯 Exact","🎯 تطابق تام") if st.session_state.search_exact
                   else t("🔍 Variant wildcard","🔍 كل المتغيرات"))
        st.divider()
        st.markdown(f"##### 🔴 {t('Low Stock Alert','تنبيه المخزون')}")
        thresh=st.number_input(t("Threshold (qty ≤)","الحد (كمية ≤)"),
                               min_value=0,max_value=1000,
                               value=st.session_state.low_stock_thresh,step=1)
        if thresh!=st.session_state.low_stock_thresh:
            st.session_state.low_stock_thresh=int(thresh)

    st.markdown(f"""
    <div class='dash-header'>
        <div class='dash-title'>📊 {t('SWAG Product Comparison','مقارنة منتجات سواغ')}</div>
        <div class='dash-subtitle'>{t('Real-time stock & price across 4 Odoo systems',
                                       'المخزون والسعر الآني عبر 4 أنظمة أودو')}</div>
    </div>
    """,unsafe_allow_html=True)
    st.divider()

    # ── PDF Upload ────────────────────────────────────────────────────────────
    st.markdown(f"### 📄 {t('Upload Invoice PDF','رفع فاتورة PDF')}")
    pc1,pc2=st.columns([2.5,1.5])
    with pc1:
        uploaded_pdf=st.file_uploader(t("Upload PDF","رفع PDF"),
                                      type=["pdf"],label_visibility="collapsed")
    with pc2:
        extract_mode=None
        if uploaded_pdf:
            extract_mode=st.radio(t("Extract mode","وضع الاستخراج"),
                [t("Main models (remove sizes)","موديلات رئيسية (بدون مقاسات)"),
                 t("With sizes (exact as invoice)","مع المقاسات (كما في الفاتورة)")],
                horizontal=True)

    if uploaded_pdf:
        with st.spinner(t("Parsing invoice...","جاري قراءة الفاتورة...")):
            raw=parse_invoice_pdf(uploaded_pdf)
        if raw:
            is_main=extract_mode is None or "Main" in extract_mode or "رئيسية" in extract_mode

            if is_main:
                # ✅ FIXED: deduplicate AFTER base model extraction
                unique=get_unique_base_models(raw)
            else:
                seen_r,unique=set(),[]
                for c in raw:
                    if c not in seen_r:
                        seen_r.add(c); unique.append(c)

            c1,c2,c3=st.columns(3)
            c1.metric(t("Raw codes","رموز مستخرجة"),len(raw))
            c2.metric(t("Unique models","موديلات فريدة"),len(unique))
            c3.info(f"📌 {t('Main models','موديلات رئيسية') if is_main else t('With sizes','مع المقاسات')}")

            with st.expander(t(f"📋 View all {len(unique)} codes","📋 الرموز"),expanded=False):
                st.code("\n".join(unique))

            ca,cb=st.columns(2)
            with ca:
                if st.button(f"🚀 {t('Total Stock','مخزون إجمالي')}",
                             type="primary",use_container_width=True,key="pdf_total"):
                    st.session_state.pdf_codes=unique
                    st.session_state.pdf_mode="total"; st.rerun()
            with cb:
                if st.button(f"🗺️ {t('Branch-wise','حسب الفرع')}",
                             type="secondary",use_container_width=True,key="pdf_branch"):
                    st.session_state.pdf_codes=unique
                    st.session_state.pdf_mode="branch"; st.rerun()
        else:
            st.warning(t("No codes found in PDF.","لم يتم العثور على رموز."))

    st.divider()

    # ── Manual Search ─────────────────────────────────────────────────────────
    st.markdown(f"### ✍️ {t('Manual Search','بحث يدوي')}")
    left,right=st.columns([1.5,1])

    with left:
        if not st.session_state.search_exact:
            st.markdown("<div class='info-banner'>🔍 <b>Variant mode</b> — XP6013 matches XP6013-S, XP6013-M etc.</div>",
                        unsafe_allow_html=True)
        else:
            st.markdown("<div class='warn-banner'>🎯 <b>Exact match mode</b> — only identical codes returned.</div>",
                        unsafe_allow_html=True)

        mode_s=t("Single Model","موديل واحد")
        mode_m=t("Multiple Models","موديلات متعددة")
        mode=st.radio(t("Mode","الوضع"),[mode_s,mode_m],
                      horizontal=True,label_visibility="collapsed")
        if mode==mode_m:
            raw_txt=st.text_area(t("Codes (one per line or comma-separated)","الرموز"),
                                 height=130,placeholder="ABC123\nDEF456, GHI789")
            codes=[c.strip() for c in raw_txt.replace(",","\n").splitlines() if c.strip()]
        else:
            single=st.text_input(t("Model Code","رمز الموديل"),placeholder="e.g. XP6013")
            codes=[single.strip()] if single.strip() else []

        t1,t2,t3,t4,t5=st.columns(5)
        show_zero     =t1.toggle(t("Zero qty","الصفري"),   value=False)
        show_branch   =t2.toggle(t("Branch","فروع"),        value=False)
        sort_sys      =t3.toggle(t("Sort","ترتيب"),         value=False)
        show_transfers=t4.toggle(t("Transfers","نقليات"),   value=False)
        show_reorder  =t5.toggle(t("Reorder","إعادة طلب"), value=False)

        if show_reorder:
            with st.expander(f"⚙️ {t('Reorder Settings','إعدادات')}",expanded=True):
                r1,r2=st.columns(2)
                with r1:
                    rm=st.radio(t("Mode","الوضع"),
                                [t("Days cover","تغطية أيام"),t("Max level","مستوى أقصى")],
                                horizontal=True,
                                index=0 if st.session_state.reorder_mode=="days_cover" else 1)
                    st.session_state.reorder_mode="days_cover" if rm==t("Days cover","تغطية أيام") else "max_level"
                with r2:
                    st.session_state.reorder_point=st.number_input(
                        t("Reorder point","نقطة الطلب"),min_value=0,max_value=9999,
                        value=st.session_state.reorder_point,step=1)
                if st.session_state.reorder_mode=="days_cover":
                    st.session_state.reorder_target_days=st.slider(
                        t("Target days","الأيام"),7,180,st.session_state.reorder_target_days)
                else:
                    st.session_state.reorder_max_level=st.number_input(
                        t("Max level","الحد الأقصى"),min_value=1,max_value=99999,
                        value=st.session_state.reorder_max_level,step=1)

        compare_btn=st.button(f"🔍 {t('Compare','مقارنة')}",
                              use_container_width=True,type="primary")

    with right:
        st.markdown(f"#### 📋 {t('Last Run','آخر تشغيل')}")
        snap=st.session_state.last_run; stats=st.session_state.sys_stats
        if not snap:
            st.info(t("Run a comparison first.","قم بتشغيل مقارنة أولاً."))
        else:
            online=sum(1 for v in stats.values() if v=="OK")
            st.markdown(
                f"<div class='snap-card'>"
                f"🕒 <b>{t('Time','الوقت')}:</b> {snap.get('time','—')}<br>"
                f"📦 <b>{t('Models','الموديلات')}:</b> {snap.get('models','—')}<br>"
                f"🌐 <b>{t('Online','متصل')}:</b> {online}/4<br>"
                f"📊 <b>{t('Rows','الصفوف')}:</b> {snap.get('rows','—')}"
                f"</div>",unsafe_allow_html=True)
            st.markdown("")
            for key in SYSTEM_KEYS:
                s=stats.get(key,"—")
                bc="badge-ok" if s=="OK" else "badge-off" if s=="NOT_FOUND" else "badge-err"
                bt="✅ OK"    if s=="OK" else "🔴 OFF"    if s=="NOT_FOUND" else "⚠️ ERR"
                st.markdown(
                    f"<div class='sys-row'>"
                    f"<span style='font-size:0.85rem;color:#e8e8ff'><b>{get_system_name(key)}</b></span>"
                    f"<span class='{bc}'>{bt}</span></div>",unsafe_allow_html=True)

    # ── Trigger ───────────────────────────────────────────────────────────────
    run_codes=None; force_branch=False
    if st.session_state.get("pdf_codes"):
        run_codes=st.session_state.pdf_codes
        force_branch=st.session_state.get("pdf_mode","total")=="branch"
        show_branch=True
        st.session_state.pdf_codes=None; st.session_state.pdf_mode="total"
    elif compare_btn:
        run_codes=codes

    if run_codes is not None:
        if not run_codes:
            st.warning(t("Enter at least one model code.","أدخل رمزاً واحداً.")); st.stop()
        exact=st.session_state.search_exact
        run_codes=list(dict.fromkeys([c.strip() for c in run_codes if c.strip()]))
        codes_tuple=tuple(run_codes)

        with st.spinner(t("⚡ Fetching from all 4 systems in parallel…",
                          "⚡ جلب البيانات من 4 أنظمة بالتوازي…")):
            data=fetch_all_data(
                codes_tuple,exact=exact,
                need_branch=show_branch or force_branch,
                need_transfers=show_transfers,need_reorder=show_reorder,
                reorder_mode=st.session_state.reorder_mode,
                target_days=st.session_state.reorder_target_days,
                max_level=st.session_state.reorder_max_level,
                reorder_point=st.session_state.reorder_point)

        total_df=data["total"]; branch_df=data["branch"]
        transfer_df=data["transfers"]; reorder_df=data["reorder"]
        sys_col=t("System","النظام"); qty_col=t("On Hand","متوفر")
        new_stats={k:"NOT_FOUND" for k in SYSTEM_KEYS}
        if "_status" in total_df.columns and sys_col in total_df.columns:
            for key in SYSTEM_KEYS:
                nm=get_system_name(key); mask=total_df[sys_col]==nm
                if mask.any():
                    sv=total_df.loc[mask,"_status"]
                    if   "OK"    in sv.values: new_stats[key]="OK"
                    elif "ERROR" in sv.values: new_stats[key]="ERROR"

        if not show_zero and qty_col in total_df.columns:
            total_df=total_df[total_df[qty_col]!=0].reset_index(drop=True)
        if sort_sys and sys_col in total_df.columns:
            total_df=total_df.sort_values(sys_col).reset_index(drop=True)
        if not branch_df.empty and sort_sys and sys_col in branch_df.columns:
            branch_df=branch_df.sort_values(sys_col).reset_index(drop=True)

        st.session_state.total_df=total_df; st.session_state.branch_df=branch_df
        st.session_state.transfers_df=transfer_df; st.session_state.reorder_df=reorder_df
        st.session_state.show_transfers=show_transfers; st.session_state.show_reorder=show_reorder
        st.session_state.sys_stats=new_stats
        st.session_state.last_run={"time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                   "models":len(run_codes),"rows":len(total_df)}
        record_price_snapshot(total_df); st.rerun()

    # ── Show Results ──────────────────────────────────────────────────────────
    total_df=st.session_state.total_df; branch_df=st.session_state.branch_df
    transfer_df=st.session_state.transfers_df; reorder_df=st.session_state.reorder_df
    if total_df is None or total_df.empty: return

    st.divider()
    thresh=st.session_state.low_stock_thresh
    qty_col=t("On Hand","متوفر"); pc_col=t("Sale Price","سعر البيع")
    sys_col=t("System","النظام"); stats=st.session_state.sys_stats
    ok_rows=total_df[total_df["_status"]=="OK"] if "_status" in total_df.columns else total_df
    online=sum(1 for v in stats.values() if v=="OK")

    if thresh>0 and qty_col in ok_rows.columns:
        low=ok_rows[(ok_rows[qty_col]>0)&(ok_rows[qty_col]<=thresh)]
        if not low.empty:
            mc=t("Model Code","رمز الموديل")
            details=", ".join(f"{r.get(mc,'?')} @ {r.get(sys_col,'?')} ({r.get(qty_col,0)})"
                              for _,r in low.head(8).iterrows())
            if len(low)>8: details+=f" +{len(low)-8} {t('more','أخرى')}"
            st.markdown(
                f"<div class='alert-banner'>🔴 <b>{t('Low Stock','مخزون منخفض')}:</b> "
                f"{len(low)} {t('variants','متغيرات')} ≤ {thresh} — "
                f"<span class='mono'>{details}</span></div>",unsafe_allow_html=True)

    m1,m2,m3,m4=st.columns(4)
    m1.metric(t("Total Rows","إجمالي الصفوف"),  len(total_df))
    m2.metric(t("Systems Online","الأنظمة"),     f"{online}/4")
    if qty_col in ok_rows.columns:
        m3.metric(t("Total Qty","إجمالي الكمية"),int(ok_rows[qty_col].sum()))
    if pc_col in ok_rows.columns:
        valid=ok_rows[ok_rows[pc_col]>0][pc_col]
        m4.metric(t("Avg Price","متوسط السعر"),
                  f"{valid.mean():.2f} SAR" if not valid.empty else "—")

    has_branch   =branch_df   is not None and not branch_df.empty
    has_transfers=st.session_state.show_transfers and transfer_df is not None and not transfer_df.empty
    has_reorder  =st.session_state.show_reorder   and reorder_df  is not None and not reorder_df.empty

    tab_labels=[f"📦 {t('Total Stock','المخزون الإجمالي')}",
                f"📊 {t('Price History','تاريخ الأسعار')}"]
    if has_branch:    tab_labels.append(f"🗺️ {t('Branch Stock','مخزون الفروع')}")
    if has_transfers: tab_labels.append(f"🚚 {t('Transfers','النقليات')}")
    if has_reorder:   tab_labels.append(f"📦 {t('Reorder','إعادة الطلب')}")
    tabs=st.tabs(tab_labels); ti=0

    # Tab 1 — Total Stock
    with tabs[ti]:
        ti+=1
        st.markdown(f"### 📦 {t('Total Stock','المخزون الإجمالي')}")
        display_df(total_df,thresh)
        st.markdown("<br>",unsafe_allow_html=True)
        d1,d2,d3,_=st.columns([1,1,1,1])
        d1.download_button("⬇️ CSV",        to_csv(total_df),       dl_name("total","csv"), "text/csv",use_container_width=True)
        d2.download_button("⬇️ Excel",      to_excel(total_df),     dl_name("total","xlsx"),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
        d3.download_button("📥 All Systems",to_excel_bulk(total_df),dl_name("bulk","xlsx"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)

    # Tab 2 — Price History
    with tabs[ti]:
        ti+=1
        st.markdown(f"### 📈 {t('Price History','تاريخ الأسعار')}")
        hist_df=build_price_history_df()
        if hist_df.empty:
            st.info(t("Run multiple comparisons to track prices.","قم بتشغيل مقارنات متعددة."))
        else:
            st.line_chart(hist_df,use_container_width=True)
            if st.button(f"🗑️ {t('Clear','مسح')}"):
                st.session_state.price_history={}; st.rerun()

    # Tab 3 — Branch Stock
    if has_branch:
        with tabs[ti]:
            ti+=1
            st.markdown(f"### 🗺️ {t('Branch-wise Stock','مخزون حسب الفرع')}")
            display_df(branch_df,thresh)
            bc=t("Branch","الفرع")
            ok_b=branch_df[branch_df["_status"]=="OK"] if "_status" in branch_df.columns else branch_df
            if not ok_b.empty and bc in ok_b.columns and qty_col in ok_b.columns:
                chart=ok_b.groupby([sys_col,bc])[qty_col].sum().reset_index()
                if not chart.empty:
                    st.markdown(f"#### 📊 {t('Qty by Branch','الكميات حسب الفرع')}")
                    st.bar_chart(chart.set_index(bc)[qty_col],use_container_width=True)
            st.markdown("<br>",unsafe_allow_html=True)
            b1,b2,_=st.columns([1,1,2])
            b1.download_button("⬇️ CSV",  to_csv(branch_df), dl_name("branch","csv"), "text/csv",use_container_width=True)
            b2.download_button("⬇️ Excel",to_excel(branch_df),dl_name("branch","xlsx"),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)

    # Tab 4 — Transfers
    if has_transfers:
        with tabs[ti]:
            ti+=1
            st.markdown(f"### 🚚 {t('Pending Transfers','النقليات المعلقة')}")
            ok_t=transfer_df[transfer_df["_status"]=="OK"] if "_status" in transfer_df.columns else transfer_df
            if not ok_t.empty:
                k1,k2,k3=st.columns(3)
                k1.metric(t("Total","إجمالي"),len(ok_t))
                qd=t("Qty","الكمية")
                if qd in ok_t.columns: k2.metric(t("Total Qty","إجمالي الكمية"),int(ok_t[qd].sum()))
                if sys_col in ok_t.columns: k3.metric(t("Systems","الأنظمة"),ok_t[sys_col].nunique())
            display_df(transfer_df)
            st.markdown("<br>",unsafe_allow_html=True)
            x1,x2,_=st.columns([1,1,2])
            x1.download_button("⬇️ CSV",  to_csv(transfer_df), dl_name("transfers","csv"), "text/csv",use_container_width=True)
            x2.download_button("⬇️ Excel",to_excel(transfer_df),dl_name("transfers","xlsx"),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)

    # Tab 5 — Reorder
    if has_reorder:
        with tabs[ti]:
            CPRI=t("Priority","الأولوية"); CSUGG=t("Suggest","المقترح")
            st.markdown(f"### 📦 {t('Reorder Suggestions','اقتراحات إعادة الطلب')}")
            ok_r=reorder_df[reorder_df["_status"]=="OK"] if "_status" in reorder_df.columns else reorder_df
            if not ok_r.empty:
                crit=ok_r[ok_r[CPRI].str.startswith("🔴")].shape[0] if CPRI in ok_r.columns else 0
                low =ok_r[ok_r[CPRI].str.startswith("🟡")].shape[0] if CPRI in ok_r.columns else 0
                okn =ok_r[ok_r[CPRI].str.startswith("🟢")].shape[0] if CPRI in ok_r.columns else 0
                sugg=int(ok_r[CSUGG].sum()) if CSUGG in ok_r.columns else 0
                r1,r2,r3,r4=st.columns(4)
                r1.metric(t("🔴 Critical","🔴 حرج"),crit)
                r2.metric(t("🟡 Low","🟡 منخفض"),low)
                r3.metric(t("🟢 OK","🟢 كافٍ"),okn)
                r4.metric(t("To Order","للطلب"),sugg)
                if crit+low>0:
                    st.markdown(
                        f"<div class='alert-banner'>🔴 {crit+low} "
                        f"{t('products need reordering','منتجات تحتاج إعادة طلب')}</div>",
                        unsafe_allow_html=True)
                show_all=st.toggle(t("Show all (incl. OK)","عرض الكل"),value=False)
                disp_r=(ok_r if show_all
                        else ok_r[ok_r[CPRI].str.startswith(("🔴","🟡"))]
                        if CPRI in ok_r.columns else ok_r)
                def _style_r(row):
                    p=str(row.get(CPRI,""))
                    if p.startswith("🔴"): return ["background-color:#ffe4e6"]*len(row)
                    if p.startswith("🟡"): return ["background-color:#fef9c3"]*len(row)
                    return [""]*len(row)
                st.dataframe(
                    disp_r.drop(columns=["_status"],errors="ignore").style.apply(_style_r,axis=1),
                    use_container_width=True,hide_index=True)
            else:
                st.info(t("No reorder data.","لا بيانات إعادة طلب."))
            st.markdown("<br>",unsafe_allow_html=True)
            o1,o2,_=st.columns([1,1,2])
            o1.download_button("⬇️ CSV",  to_csv(reorder_df), dl_name("reorder","csv"), "text/csv",use_container_width=True)
            o2.download_button("⬇️ Excel",to_excel(reorder_df),dl_name("reorder","xlsx"),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.authenticated:
    show_login()
else:
    show_dashboard()
