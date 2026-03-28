"""
SWAG Product Comparison Dashboard
Version 22.0 FIXED
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
[data-baseweb="tag"]{background:#667eea33!important;color:#c4b5fd!important;}
[data-baseweb="select"] div{background:#1e1e3f!important;color:#e8e8ff!important;border-color:#667eea55!important;}
footer{visibility:hidden;}
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
.swag-tbl tbody tr.out td{background:#2a0a0a!important;color:#ff8888!important;font-weight:700;}
</style>
""", unsafe_allow_html=True)

SYSTEM_KEYS   = ["SWAG", "LAROUCHE", "DIFFC", "FASHION_LIMITS"]
PAGE_SIZE     = 50
_COOKIE_SECRET = "swag_2025_secure"

def get_lang():
    return st.session_state.get("lang", "EN")

def t(en, ar):
    return ar if get_lang() == "AR" else en

def get_system_name(key):
    cfg = st.secrets.get(key, {})
    return cfg.get("name_ar", cfg.get("name", key)) if get_lang() == "AR" else cfg.get("name", key)

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
}
for k, v in _DEF.items():
    if k not in st.session_state:
        st.session_state[k] = v

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

def _domain(codes, exact):
    if exact:
        return [["default_code", "in", codes]]
    if len(codes) == 1:
        return [["default_code", "=like", f"{codes[0]}%"]]
    parts = [["default_code", "=like", f"{c}%"] for c in codes]
    return ["|"] * (len(parts) - 1) + parts

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
    for c in raw:
        b = extract_base_model(c)
        if b and b not in seen:
            seen.add(b); out.append(b)
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
    for c in raw:
        u = c.strip().upper()
        if _valid(u) and u not in seen:
            seen.add(u); out.append(u)
    return out

def _style_worksheet(ws, df_clean):
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    hfill  = PatternFill("solid", fgColor="667EEA")
    afill  = PatternFill("solid", fgColor="F0F4FF")
    thin   = Side(border_style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for col_num, col_name in enumerate(df_clean.columns, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = hfill
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border
        col_vals = [str(v) for v in df_clean.iloc[:, col_num - 1]]
        max_len  = max(len(str(col_name)), max((len(v) for v in col_vals), default=0))
        ws.column_dimensions[get_column_letter(col_num)].width = min(max_len + 4, 40)
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(horizontal="center", vertical="center")
            if cell.row % 2 == 0:
                cell.fill = afill
    ws.row_dimensions[1].height = 22
    ws.freeze_panes = "A2"

def to_csv(df):
    return df.drop(columns=["_status"], errors="ignore").to_csv(index=False).encode("utf-8-sig")

def to_excel(df):
    buf   = io.BytesIO()
    clean = df.drop(columns=["_status"], errors="ignore")
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        clean.to_excel(w, index=False, sheet_name="Data")
        _style_worksheet(w.sheets["Data"], clean)
    return buf.getvalue()

def to_excel_bulk(df):
    buf     = io.BytesIO()
    sys_col = t("System", "النظام")
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        def _ws(data, name):
            c = data.drop(columns=["_status"], errors="ignore")
            c.to_excel(w, index=False, sheet_name=name[:31])
            _style_worksheet(w.sheets[name[:31]], c)
        _ws(df, t("All Systems", "كل الانظمة"))
        if sys_col in df.columns:
            for key in SYSTEM_KEYS:
                nm  = get_system_name(key)
                sub = df[df[sys_col] == nm]
                if not sub.empty:
                    _ws(sub, nm)
    return buf.getvalue()

def dl_name(tag, ext):
    return f"swag_{tag}_{datetime.now().strftime('%Y%m%d_%H%M')}.{ext}"

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

    CS=t("System","النظام"); CM=t("Model Code","رمز الموديل")
    CPR=t("Product","المنتج"); CP=t("Sale Price","سعر البيع")
    CQ=t("On Hand","متوفر"); CB=t("Branch","الفرع")
    CL=t("Location","الموقع"); CR=t("Reference","المرجع")
    CT=t("Type","النوع"); CST=t("State","الحالة")
    CF=t("From","من"); CTO=t("To","الى"); CQT=t("Qty","الكمية")
    CD=t("Scheduled","المجدول"); CSOLD=t("Sold(30d)","مباع(30ي)")
    CVEL=t("Daily Vel","معدل/يوم"); CDAY=t("Days Left","ايام متبقية")
    CSUGG=t("Suggest","المقترح"); CPRI=t("Priority","الاولوية")
    SM={
        "draft"    : t("Draft","مسودة"),
        "waiting"  : t("Waiting","انتظار"),
        "confirmed": t("Confirmed","مؤكد"),
        "assigned" : t("Ready","جاهز"),
    }

    def _one(key):
        cfg = st.secrets.get(key)
        sn  = get_system_name(key)
        R   = {"key":key,"total":[],"branch":[],"transfers":[],"reorder":[]}
        if not cfg:
            R["total"].append({CS:sn,CM:"--",CPR:"No config",CP:0.0,CQ:0,"_status":"ERROR"})
            return R
        uid = _auth(cfg["url"],cfg["db"],cfg["user"],cfg["api_key"])
        if not uid:
            R["total"].append({CS:sn,CM:"--",CPR:"Auth failed",CP:0.0,CQ:0,"_status":"ERROR"})
            return R
        u=cfg["url"]; db=cfg["db"]; ak=cfg["api_key"]
        try:
            prods = _x(u,db,uid,ak,"product.product","search_read",[dom],
                       {"fields":["id","display_name","default_code","qty_available","list_price"],
                        "limit":2000,"order":"default_code asc"})
            if not prods:
                R["total"].append({CS:sn,CM:"--",CPR:t("Not found","غير موجود"),
                                   CP:0.0,CQ:0,"_status":"NOT_FOUND"})
                return R
            pids = [p["id"] for p in prods]
            pmap = {p["id"]:p for p in prods}
            for p in prods:
                R["total"].append({
                    CS:sn, CM:p.get("default_code") or "--",
                    CPR:p.get("display_name") or "",
                    CP:float(p.get("list_price") or 0),
                    CQ:int(p.get("qty_available") or 0),
                    "_status":"OK"
                })
            if need_branch:
                qs = _x(u,db,uid,ak,"stock.quant","search_read",
                        [[["product_id","in",pids],["quantity",">",0]]],
                        {"fields":["product_id","location_id","quantity"],"limit":5000})
                for q in qs:
                    pid = q["product_id"][0] if isinstance(q.get("product_id"),list) else None
                    loc = q.get("location_id") or [None,"--"]
                    ln  = loc[1] if isinstance(loc,list) else str(loc)
                    pm  = pmap.get(pid,{})
                    R["branch"].append({
                        CS:sn, CB:ln.split("/")[0].strip(),
                        CM:pm.get("default_code") or "--", CL:ln,
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
                                v=_p.get(f); return v[1] if isinstance(v,list) else (v or "--")
                            sd = pk.get("scheduled_date") or "--"
                            if sd != "--":
                                try:
                                    sd = datetime.strptime(sd,"%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
                                except Exception:
                                    pass
                            pid2 = mv["product_id"][0] if isinstance(mv.get("product_id"),list) else None
                            pm2  = pmap.get(pid2,{})
                            R["transfers"].append({
                                CS:sn, CR:pk.get("name") or "--",
                                CT:_n("picking_type_id"),
                                CST:SM.get(pk.get("state",""),pk.get("state","")),
                                CF:_n("location_id"), CTO:_n("location_dest_id"),
                                CM:pm2.get("default_code") or "--",
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
                    if pid:
                        sm2[pid] = sm2.get(pid,0)+float(l.get("product_uom_qty") or 0)
                for p in prods:
                    pid  = p["id"]
                    cq   = int(p.get("qty_available") or 0)
                    sold = sm2.get(pid,0)
                    vel  = round(sold/DAYS,2)
                    dl   = str(round(cq/vel,1)) if vel>0 else "inf"
                    sg   = max(0,round(target_days*vel-cq)) if reorder_mode=="days_cover" else max(0,max_level-cq)
                    pr2  = (t("Critical","حرج") if cq<=0
                            else t("Low","منخفض") if cq<=reorder_point
                            else t("OK","كافٍ"))
                    R["reorder"].append({
                        CS:sn, CM:p.get("default_code") or "--",
                        CPR:p.get("display_name") or "",
                        CQ:cq, CSOLD:int(sold), CVEL:vel,
                        CDAY:dl, CSUGG:sg, CPRI:pr2, "_status":"OK"
                    })
        except Exception as e:
            R["total"].append({CS:sn,CM:"--",CPR:f"ERROR: {e}",CP:0.0,CQ:0,"_status":"ERROR"})
        return R

    at=[]; ab=[]; atr=[]; ar=[]
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(_one,k):k for k in SYSTEM_KEYS}
        for f in as_completed(futs):
            r = f.result()
            at.extend(r["total"]); ab.extend(r["branch"])
            atr.extend(r["transfers"]); ar.extend(r["reorder"])

    def _df(rows, cols):
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=cols)

    return {
        "total"    : _df(at,  [CS,CM,CPR,CP,CQ,"_status"]),
        "branch"   : _df(ab,  [CS,CB,CM,CL,CP,CQ,"_status"]),
        "transfers": _df(atr, [CS,CR,CT,CST,CF,CTO,CM,CQT,CD,"_status"]),
        "reorder"  : _df(ar,  [CS,CM,CPR,CQ,CSOLD,CVEL,CDAY,CSUGG,CPRI,"_status"]),
    }

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

def _add_status_badge(df, thresh):
    qc = t("On Hand","متوفر")
    sc = t("Stock Status","حالة المخزون")
    if qc not in df.columns:
        return df
    work = df.copy()
    raw  = pd.to_numeric(work[qc], errors="coerce").fillna(0)
    def _badge(q):
        if q <= 0:
            return "Out of Stock"
        if thresh > 0 and q <= thresh:
            return "Low Stock"
        return "In Stock"
    work[sc] = raw.map(_badge)
    cols = work.columns.tolist()
    qi   = cols.index(qc)
    cols.insert(qi+1, cols.pop(cols.index(sc)))
    return work[cols]

def build_price_diff_df(df):
    sc = t("System","النظام")
    mc = t("Model Code","رمز الموديل")
    pc = t("Sale Price","سعر البيع")
    if not all(c in df.columns for c in [sc,mc,pc]):
        return pd.DataFrame()
    ok = df[df["_status"]=="OK"].copy() if "_status" in df.columns else df.copy()
    ok[pc] = pd.to_numeric(ok[pc], errors="coerce")
    pivot  = ok.pivot_table(index=mc, columns=sc, values=pc, aggfunc="mean")
    if pivot.empty:
        return pd.DataFrame()
    pivot["Max SAR"]  = pivot.max(axis=1)
    pivot["Min SAR"]  = pivot.min(axis=1)
    pivot["Diff SAR"] = (pivot["Max SAR"] - pivot["Min SAR"]).round(2)
    pivot["Alert"]    = pivot["Diff SAR"].map(
        lambda d: "Big Diff" if d > 50 else ("Small Diff" if d > 0 else "Same Price"))
    pivot = pivot.sort_values("Diff SAR", ascending=False).reset_index()
    return pivot

def display_df(df, thresh=0, table_key="tbl"):
    if df is None or df.empty:
        st.info(t("No data.","لا بيانات."))
        return

    work    = _add_status_badge(df, thresh)
    sys_col = t("System","النظام")
    mc_col  = t("Model Code","رمز الموديل")
    pr_col  = t("Product","المنتج")
    br_col  = t("Branch","الفرع")
    loc_col = t("Location","الموقع")
    sc_col  = t("Stock Status","حالة المخزون")
    qc      = t("On Hand","متوفر")
    pc      = t("Sale Price","سعر البيع")

    fc = st.columns([2,2,2,1.5])

    if sys_col in work.columns:
        all_sys = sorted(work[sys_col].dropna().unique().tolist())
        with fc[0]:
            sel_sys = st.multiselect(
                t("Company","الشركة"),
                options=all_sys, default=all_sys,
                key=f"{table_key}_sys")
        if sel_sys:
            work = work[work[sys_col].isin(sel_sys)]

    if br_col in work.columns:
        all_br = sorted(work[br_col].dropna().unique().tolist())
        with fc[1]:
            sel_br = st.multiselect(
                t("Branch","الفرع"),
                options=all_br, default=all_br,
                key=f"{table_key}_br")
        if sel_br:
            work = work[work[br_col].isin(sel_br)]

    with fc[2]:
        q = st.text_input(
            t("Search","بحث"),
            value="",
            placeholder=t("Model / Product...","موديل / منتج..."),
            key=f"{table_key}_q"
        ).strip()
    if q:
        ql   = q.lower()
        mask = pd.Series([False]*len(work), index=work.index)
        for col in [mc_col, pr_col, loc_col]:
            if col in work.columns:
                mask = mask | work[col].fillna("").str.lower().str.contains(ql, regex=False)
        work = work[mask]

    with fc[3]:
        sortable = [c for c in work.columns if c != "_status"]
        sort_by  = st.selectbox(
            t("Sort","ترتيب"),
            options=["--"] + sortable,
            index=0,
            key=f"{table_key}_sort")
    if sort_by and sort_by != "--" and sort_by in work.columns:
        try:
            num = pd.to_numeric(work[sort_by], errors="coerce")
            if num.notna().sum() > len(work)*0.5:
                work = work.assign(_sk=num).sort_values("_sk", ascending=False).drop(columns=["_sk"])
            else:
                work = work.sort_values(sort_by)
        except Exception:
            pass

    if sc_col in work.columns:
        st.markdown(t("**Quick Filter:**","**فلتر سريع:**"))
        chip_options = [
            t("All","الكل"),
            t("Out of Stock","نفذ"),
            t("Low Stock","منخفض"),
            t("In Stock","متوفر"),
        ]
        chip_sel = st.radio(
            "",
            chip_options,
            horizontal=True,
            label_visibility="collapsed",
            key=f"{table_key}_chip")
        if chip_sel not in [t("All","الكل")]:
            if chip_sel == t("Out of Stock","نفذ"):
                work = work[work[sc_col] == "Out of Stock"]
            elif chip_sel == t("Low Stock","منخفض"):
                work = work[work[sc_col] == "Low Stock"]
            elif chip_sel == t("In Stock","متوفر"):
                work = work[work[sc_col] == "In Stock"]

    if work.empty:
        st.warning(t("No rows match filters.","لا توجد نتائج."))
        return

    ok_w = work[work["_status"]=="OK"] if "_status" in work.columns else work
    sm1,sm2,sm3,sm4 = st.columns(4)
    sm1.metric(t("Showing","معروض"), len(work))
    if qc in ok_w.columns:
        sm2.metric(t("Total Qty","اجمالي الكمية"),
                   int(pd.to_numeric(ok_w[qc], errors="coerce").sum()))
    if pc in ok_w.columns:
        vp = pd.to_numeric(ok_w[pc], errors="coerce")
        sm3.metric(t("Avg Price","متوسط السعر"),
                   f"{vp[vp>0].mean():.2f} SAR" if not vp[vp>0].empty else "--")
    if sys_col in ok_w.columns:
        sm4.metric(t("Companies","الشركات"), ok_w[sys_col].nunique())

    total_rows  = len(work)
    total_pages = max(1, -(-total_rows // PAGE_SIZE))
    pg_key      = f"{table_key}_page"
    if pg_key not in st.session_state:
        st.session_state[pg_key] = 1
    if st.session_state[pg_key] > total_pages:
        st.session_state[pg_key] = 1

    page  = st.session_state[pg_key]
    start = (page-1)*PAGE_SIZE
    end   = min(start+PAGE_SIZE, total_rows)
    page_df = work.iloc[start:end]

    if total_pages > 1:
        pc1,pc2,pc3,pc4,pc5 = st.columns([1,1,2,1,1])
        with pc1:
            if st.button("First", key=f"{table_key}_first",
                         disabled=page<=1, use_container_width=True):
                st.session_state[pg_key]=1; st.rerun()
        with pc2:
            if st.button("Prev", key=f"{table_key}_prev",
                         disabled=page<=1, use_container_width=True):
                st.session_state[pg_key]-=1; st.rerun()
        with pc3:
            st.markdown(
                f"<div style='text-align:center;color:#c4b5fd;padding:8px 0;font-weight:600;'>"
                f"{t('Page','صفحة')} {page} / {total_pages} "
                f"<span style='color:#8888bb;font-size:.8rem;'>"
                f"({start+1}-{end} {t('of','من')} {total_rows})</span></div>",
                unsafe_allow_html=True)
        with pc4:
            if st.button("Next", key=f"{table_key}_next",
                         disabled=page>=total_pages, use_container_width=True):
                st.session_state[pg_key]+=1; st.rerun()
        with pc5:
            if st.button("Last", key=f"{table_key}_last",
                         disabled=page>=total_pages, use_container_width=True):
                st.session_state[pg_key]=total_pages; st.rerun()

    show = page_df.drop(columns=["_status"], errors="ignore").copy()
    if pc in show.columns:
        show[pc] = pd.to_numeric(show[pc], errors="coerce").map(
            lambda v: f"{v:.2f} SAR" if pd.notna(v) else "--")
    if qc in show.columns:
        show[qc] = pd.to_numeric(show[qc], errors="coerce").map(
            lambda v: str(int(v)) if pd.notna(v) else "--")

    low_idx = set()
    out_idx = set()
    if qc in page_df.columns:
        raw_q   = pd.to_numeric(page_df[qc], errors="coerce")
        out_idx = set(page_df.index[raw_q <= 0])
        if thresh > 0:
            low_idx = set(page_df.index[(raw_q > 0) & (raw_q <= thresh)])

    cols = show.columns.tolist()
    th_  = "".join(f"<th>{c}</th>" for c in cols)

    def _row(idx_row):
        i, row = idx_row
        if i in out_idx:
            cls = " out"
        elif i in low_idx:
            cls = " rl"
        else:
            cls = ""
        cells = "".join(
            f'<td class="cf">{v}</td>' if ci==0 else f"<td>{v}</td>"
            for ci,v in enumerate(row))
        return f'<tr class="{cls}">{cells}</tr>'

    tbody = "".join(_row(x) for x in show.iterrows())
    st.markdown(
        f'<div class="swag-wrap">'
        f'<table class="swag-tbl"><thead><tr>{th_}</tr></thead>'
        f'<tbody>{tbody}</tbody></table></div>',
        unsafe_allow_html=True)
    st.caption(
        f"{t('Showing','عرض')} {start+1}-{end} "
        f"{t('of','من')} {total_rows} {t('rows','صفوف')}")

def show_company_chart(df):
    sc = t("System","النظام")
    qc = t("On Hand","متوفر")
    mc = t("Model Code","رمز الموديل")
    if sc not in df.columns or qc not in df.columns:
        return
    ok = df[df["_status"]=="OK"] if "_status" in df.columns else df
    if ok.empty:
        return
    ok    = ok.copy()
    ok[qc] = pd.to_numeric(ok[qc], errors="coerce").fillna(0)
    st.markdown(f"#### {t('Stock by Company','المخزون حسب الشركة')}")
    c1,c2 = st.columns(2)
    with c1:
        cg = ok.groupby(sc)[qc].sum().sort_values(ascending=False)
        st.markdown(f"**{t('Total Qty per Company','اجمالي الكمية')}**")
        st.bar_chart(cg, use_container_width=True)
    with c2:
        cm_ = ok.groupby(sc)[mc].nunique().sort_values(ascending=False)
        st.markdown(f"**{t('Products per Company','عدد المنتجات')}**")
        st.bar_chart(cm_, use_container_width=True)
        def show_login():
    _,_,lc = st.columns([2,1,0.5])
    with lc:
        lg = st.radio("", ["EN","AR"], horizontal=True,
                      index=0 if get_lang()=="EN" else 1,
                      label_visibility="collapsed", key="llr")
        if lg != get_lang():
            st.session_state.lang = lg
            st.rerun()

    _,col,_ = st.columns([1,1.1,1])
    with col:
        st.markdown("""
        <div style='display:flex;flex-direction:column;align-items:center;padding:20px 0 8px;'>
            <div class='login-orb'>&#128202;</div>
            <div class='login-title'>SWAG Dashboard</div>
            <div class='login-subtitle'>Real-time Stock and Price - 4 Odoo Systems</div>
        </div>""", unsafe_allow_html=True)
        wm = ("Welcome back! Sign in to continue." if get_lang()=="EN"
              else "مرحبا بك - سجل دخولك للمتابعة")
        st.markdown(f"<div class='welcome-banner'>{wm}</div>", unsafe_allow_html=True)
        st.markdown("<div class='login-card'>", unsafe_allow_html=True)
        with st.form("lf", clear_on_submit=False):
            em = st.text_input(
                "Email" if get_lang()=="EN" else "البريد الالكتروني",
                placeholder="you@swag.com.sa")
            pw = st.text_input(
                "Password" if get_lang()=="EN" else "كلمة المرور",
                type="password", placeholder="........")
            st.markdown("<br>", unsafe_allow_html=True)
            sub = st.form_submit_button(
                "Sign In" if get_lang()=="EN" else "تسجيل الدخول",
                use_container_width=True, type="primary")
        st.markdown("</div>", unsafe_allow_html=True)

        if sub:
            if not em or not pw:
                st.error(t("Fill in both fields.","يرجى ملء جميع الحقول."))
                return
            if "LOGIN" not in st.secrets:
                st.error("LOGIN section missing in secrets.toml")
                return
            cfg = st.secrets["LOGIN"]
            if "url" not in cfg or "db" not in cfg:
                st.error("LOGIN.url or LOGIN.db missing")
                return
            with st.spinner(t("Signing in...","جارٍ تسجيل الدخول...")):
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
                        st.error(t("Wrong email or password.",
                                   "بريد الكتروني او كلمة مرور خاطئة."))
                except Exception as e:
                    st.error(f"Connection error: {e}")
        st.markdown(
            "<p style='text-align:center;color:#4a4a6a;font-size:.75rem;margin-top:24px;'>"
            "2025 SWAG Fashion - Powered by Odoo</p>",
            unsafe_allow_html=True)


def do_logout():
    try:
        st.query_params.clear()
    except Exception:
        pass
    st.session_state.authenticated = False
    st.session_state.user_email    = ""
    st.rerun()


def show_dashboard():
    with st.sidebar:
        st.markdown(f"### {t('Settings','الاعدادات')}")
        lc2 = st.radio(
            t("Language","اللغة"), ["EN","AR"],
            index=0 if get_lang()=="EN" else 1, horizontal=True)
        if lc2 != get_lang():
            st.session_state.lang = lc2
            st.rerun()
        st.divider()
        st.markdown(f"User: **{st.session_state.user_email}**")
        if st.button(t("Logout","تسجيل الخروج"), use_container_width=True):
            do_logout()
        st.divider()
        st.markdown(f"##### {t('Search Mode','وضع البحث')}")
        et = st.toggle(
            t("Exact match only","تطابق تام فقط"),
            value=st.session_state.search_exact)
        if et != st.session_state.search_exact:
            st.session_state.search_exact  = et
            st.session_state.total_df      = None
            st.session_state.branch_df     = None
            st.session_state.transfers_df  = None
            st.rerun()
        st.caption(t("Exact","تطابق تام") if st.session_state.search_exact
                   else t("Variant wildcard","كل المتغيرات"))
        st.divider()
        st.markdown(f"##### {t('Low Stock Alert','تنبيه المخزون')}")
        thr = st.number_input(
            t("Threshold (qty <=)","الحد (كمية <=)"),
            min_value=0, max_value=1000,
            value=st.session_state.low_stock_thresh, step=1)
        if thr != st.session_state.low_stock_thresh:
            st.session_state.low_stock_thresh = int(thr)
        st.divider()
        if st.session_state.last_run:
            st.markdown(f"**{t('Last Run','اخر تشغيل')}**")
            st.caption(st.session_state.last_run.get("time",""))

    st.markdown(f"""
    <div class='dash-header'>
      <div class='dash-title'>{t('SWAG Product Comparison','مقارنة منتجات سواغ')}</div>
      <div class='dash-subtitle'>{t('Real-time stock and price across 4 Odoo systems',
                                     'المخزون والسعر الاني عبر 4 انظمة اودو')}</div>
    </div>""", unsafe_allow_html=True)
    st.divider()

    st.markdown(f"### {t('Upload Invoice PDF','رفع فاتورة PDF')}")
    p1,p2 = st.columns([2.5,1.5])
    with p1:
        updf = st.file_uploader(
            t("Upload PDF","رفع PDF"),
            type=["pdf"], label_visibility="collapsed")
    with p2:
        emode = None
        if updf:
            emode = st.radio(
                t("Extract mode","وضع الاستخراج"),
                [t("Main models","موديلات رئيسية"),
                 t("With sizes","مع المقاسات")],
                horizontal=True)
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
            unique  = get_unique_base_models(raw) if is_main else list(dict.fromkeys(raw))
            c1,c2,c3 = st.columns(3)
            c1.metric(t("Raw codes","رموز مستخرجة"), len(raw))
            c2.metric(t("Unique models","موديلات فريدة"), len(unique))
            c3.info(t("Main","رئيسية") if is_main else t("With sizes","مع المقاسات"))
            with st.expander(t("Codes","الرموز"), expanded=False):
                st.code("\n".join(unique))
            ca,cb = st.columns(2)
            with ca:
                if st.button(t("Total Stock","مخزون اجمالي"),
                             type="primary", use_container_width=True, key="pt"):
                    st.session_state.pdf_codes = unique
                    st.session_state.pdf_mode  = "total"
                    st.rerun()
            with cb:
                if st.button(t("Branch-wise","حسب الفرع"),
                             type="secondary", use_container_width=True, key="pb"):
                    st.session_state.pdf_codes = unique
                    st.session_state.pdf_mode  = "branch"
                    st.rerun()
        else:
            st.warning(t("No codes found in PDF.","لم يتم العثور على رموز."))

    st.divider()
    st.markdown(f"### {t('Manual Search','بحث يدوي')}")
    L,R = st.columns([1.5,1])
    with L:
        if not st.session_state.search_exact:
            st.markdown(
                "<div class='info-banner'>Variant mode - XP6013 finds XP6013-S/M/L</div>",
                unsafe_allow_html=True)
        else:
            st.markdown(
                "<div class='warn-banner'>Exact match mode - identical codes only.</div>",
                unsafe_allow_html=True)
        ms   = t("Single Model","موديل واحد")
        mm   = t("Multiple Models","موديلات متعددة")
        mode = st.radio(t("Mode","الوضع"), [ms,mm],
                        horizontal=True, label_visibility="collapsed")
        if mode == mm:
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
            with st.expander(t("Reorder Settings","اعدادات اعادة الطلب"), expanded=True):
                rx,ry = st.columns(2)
                with rx:
                    rm = st.radio(
                        t("Mode","الوضع"),
                        [t("Days cover","تغطية ايام"),
                         t("Max level","مستوى اقصى")],
                        horizontal=True,
                        index=0 if st.session_state.reorder_mode=="days_cover" else 1)
                    st.session_state.reorder_mode = (
                        "days_cover" if "Days" in rm or "تغطية" in rm else "max_level")
                with ry:
                    st.session_state.reorder_point = st.number_input(
                        t("Reorder point","نقطة الطلب"),
                        min_value=0, max_value=9999,
                        value=st.session_state.reorder_point, step=1)
                if st.session_state.reorder_mode == "days_cover":
                    st.session_state.reorder_target_days = st.slider(
                        t("Target days","ايام"), 7, 180,
                        st.session_state.reorder_target_days)
                else:
                    st.session_state.reorder_max_level = st.number_input(
                        t("Max level","الحد"),
                        min_value=1, max_value=99999,
                        value=st.session_state.reorder_max_level, step=1)

        cbtn = st.button(
            t("Compare","مقارنة"),
            use_container_width=True, type="primary")

    with R:
        st.markdown(f"#### {t('Last Run','اخر تشغيل')}")
        snap  = st.session_state.last_run
        stats = st.session_state.sys_stats
        if not snap:
            st.info(t("Run a comparison first.","قم بتشغيل مقارنة اولا."))
        else:
            on = sum(1 for v in stats.values() if v=="OK")
            st.markdown(
                f"<div class='snap-card'>"
                f"<b>{t('Time','الوقت')}:</b> {snap.get('time','--')}<br>"
                f"<b>{t('Models','الموديلات')}:</b> {snap.get('models','--')}<br>"
                f"<b>{t('Online','متصل')}:</b> {on}/4<br>"
                f"<b>{t('Rows','الصفوف')}:</b> {snap.get('rows','--')}"
                f"</div>", unsafe_allow_html=True)
            st.markdown("")
            for key in SYSTEM_KEYS:
                s  = stats.get(key,"--")
                bc = "badge-ok" if s=="OK" else "badge-off" if s=="NOT_FOUND" else "badge-err"
                bt = "OK"       if s=="OK" else "OFF"       if s=="NOT_FOUND" else "ERR"
                st.markdown(
                    f"<div class='sys-row'>"
                    f"<span style='font-size:.85rem;color:#e8e8ff'>"
                    f"<b>{get_system_name(key)}</b></span>"
                    f"<span class='{bc}'>{bt}</span></div>",
                    unsafe_allow_html=True)

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
            st.warning(t("Enter at least one model code.","ادخل رمزا واحدا."))
            st.stop()
        run_codes = list(dict.fromkeys([c.strip() for c in run_codes if c.strip()]))
        ct = tuple(run_codes)
        with st.spinner(t("Fetching from 4 systems...","جلب البيانات من 4 انظمة...")):
            data = fetch_all_data(
                ct,
                exact=st.session_state.search_exact,
                need_branch=sb or force_branch,
                need_transfers=st_,
                need_reorder=sr,
                reorder_mode=st.session_state.reorder_mode,
                target_days=st.session_state.reorder_target_days,
                max_level=st.session_state.reorder_max_level,
                reorder_point=st.session_state.reorder_point)
        tdf  = data["total"];  bdf  = data["branch"]
        trdf = data["transfers"]; rdf = data["reorder"]
        sc2  = t("System","النظام"); qc2 = t("On Hand","متوفر")
        ns   = {k:"NOT_FOUND" for k in SYSTEM_KEYS}
        if "_status" in tdf.columns and sc2 in tdf.columns:
            for key in SYSTEM_KEYS:
                nm   = get_system_name(key)
                mask = tdf[sc2] == nm
                if mask.any():
                    sv = tdf.loc[mask,"_status"]
                    if   "OK"    in sv.values: ns[key] = "OK"
                    elif "ERROR" in sv.values: ns[key] = "ERROR"
        if not sz and qc2 in tdf.columns:
            tdf = tdf[tdf[qc2] != 0].reset_index(drop=True)
        if ss and sc2 in tdf.columns:
            tdf = tdf.sort_values(sc2).reset_index(drop=True)
        if not bdf.empty and ss and sc2 in bdf.columns:
            bdf = bdf.sort_values(sc2).reset_index(drop=True)
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

    tdf  = st.session_state.total_df
    bdf  = st.session_state.branch_df
    trdf = st.session_state.transfers_df
    rdf  = st.session_state.reorder_df
    if tdf is None or tdf.empty:
        return

    st.divider()
    thr  = st.session_state.low_stock_thresh
    qc2  = t("On Hand","متوفر")
    pc2  = t("Sale Price","سعر البيع")
    sc2  = t("System","النظام")
    stats = st.session_state.sys_stats
    ok   = tdf[tdf["_status"]=="OK"] if "_status" in tdf.columns else tdf
    on   = sum(1 for v in stats.values() if v=="OK")

    if thr > 0 and qc2 in ok.columns:
        low = ok[(ok[qc2]>0) & (ok[qc2]<=thr)]
        if not low.empty:
            mc2 = t("Model Code","رمز الموديل")
            det = ", ".join(
                f"{r.get(mc2,'?')}@{r.get(sc2,'?')}({r.get(qc2,0)})"
                for _,r in low.head(8).iterrows())
            if len(low) > 8:
                det += f" +{len(low)-8}"
            st.markdown(
                f"<div class='alert-banner'>"
                f"<b>{t('Low Stock','مخزون منخفض')}:</b> "
                f"{len(low)} items at or below {thr} -- "
                f"<span class='mono'>{det}</span></div>",
                unsafe_allow_html=True)

    m1,m2,m3,m4 = st.columns(4)
    m1.metric(t("Total Rows","اجمالي الصفوف"), len(tdf))
    m2.metric(t("Systems Online","الانظمة"), f"{on}/4")
    if qc2 in ok.columns:
        m3.metric(t("Total Qty","اجمالي الكمية"), int(ok[qc2].sum()))
    if pc2 in ok.columns:
        vp = ok[ok[pc2]>0][pc2]
        m4.metric(t("Avg Price","متوسط السعر"),
                  f"{vp.mean():.2f} SAR" if not vp.empty else "--")

    hb = bdf  is not None and not bdf.empty
    ht = st.session_state.show_transfers and trdf is not None and not trdf.empty
    hr = st.session_state.show_reorder   and rdf  is not None and not rdf.empty

    tlabels = [
        t("Total Stock","المخزون الاجمالي"),
        t("Price Diff","فرق الاسعار"),
        t("Charts","الرسوم"),
        t("Price History","تاريخ الاسعار"),
    ]
    if hb: tlabels.append(t("Branch Stock","مخزون الفروع"))
    if ht: tlabels.append(t("Transfers","النقليات"))
    if hr: tlabels.append(t("Reorder","اعادة الطلب"))
    tabs = st.tabs(tlabels)
    ti   = 0

    with tabs[ti]:
        ti += 1
        st.markdown(f"### {t('Total Stock','المخزون الاجمالي')}")
        display_df(tdf, thr, table_key="total")
        st.markdown("<br>", unsafe_allow_html=True)
        d1,d2,d3,_ = st.columns([1,1,1,1])
        d1.download_button(
            "CSV", to_csv(tdf), dl_name("total","csv"), "text/csv",
            use_container_width=True)
        d2.download_button(
            "Excel", to_excel(tdf), dl_name("total","xlsx"),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)
        d3.download_button(
            "All Systems", to_excel_bulk(tdf), dl_name("bulk","xlsx"),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)

    with tabs[ti]:
        ti += 1
        st.markdown(f"### {t('Price Difference Across Systems','مقارنة الاسعار بين الانظمة')}")
        pdiff = build_price_diff_df(tdf)
        if pdiff.empty:
            st.info(t("Need data from 2+ systems for price comparison.",
                      "يلزم وجود بيانات من نظامين على الاقل."))
        else:
            big   = pdiff[pdiff["Alert"]=="Big Diff"]
            small = pdiff[pdiff["Alert"]=="Small Diff"]
            same  = pdiff[pdiff["Alert"]=="Same Price"]
            pp1,pp2,pp3 = st.columns(3)
            pp1.metric("Big Diff (>50 SAR)",  len(big))
            pp2.metric("Small Diff",           len(small))
            pp3.metric("Same Price",           len(same))
            if not big.empty:
                st.markdown(
                    f"<div class='alert-banner'>"
                    f"{len(big)} {t('products have big price difference!','منتج بفرق سعر كبير!')}"
                    f"</div>", unsafe_allow_html=True)
            pf = st.radio(
                t("Show","عرض"),
                [t("All","الكل"), t("Big Diff","فرق كبير"), t("Small Diff","فرق صغير")],
                horizontal=True, key="pdiff_filter")
            if t("Big Diff","فرق كبير") in pf:
                pdiff = big
            elif t("Small Diff","فرق صغير") in pf:
                pdiff = small
            cols_  = pdiff.columns.tolist()
            th__   = "".join(f"<th>{c}</th>" for c in cols_)
            def _pdrow(row):
                alert = str(row.get("Alert",""))
                cls   = " out" if "Big" in alert else (" rl" if "Small" in alert else "")
                cells = "".join(f"<td>{v}</td>" for v in row)
                return f'<tr class="{cls}">{cells}</tr>'
            tbody_ = "".join(_pdrow(r) for _,r in pdiff.iterrows())
            st.markdown(
                f'<div class="swag-wrap">'
                f'<table class="swag-tbl"><thead><tr>{th__}</tr></thead>'
                f'<tbody>{tbody_}</tbody></table></div>',
                unsafe_allow_html=True)
            st.caption(f"{len(pdiff)} {t('products','منتجات')}")
            st.download_button(
                "CSV", pdiff.to_csv(index=False).encode("utf-8-sig"),
                dl_name("price_diff","csv"), "text/csv")

    with tabs[ti]:
        ti += 1
        st.markdown(f"### {t('Stock Charts','رسوم المخزون')}")
        show_company_chart(tdf)
        mc2_ = t("Model Code","رمز الموديل")
        qc2_ = t("On Hand","متوفر")
        ok2  = tdf[tdf["_status"]=="OK"].copy() if "_status" in tdf.columns else tdf.copy()
        if mc2_ in ok2.columns and qc2_ in ok2.columns:
            ok2[qc2_] = pd.to_numeric(ok2[qc2_], errors="coerce").fillna(0)
            top10 = ok2.groupby(mc2_)[qc2_].sum().nlargest(10)
            bot10 = ok2.groupby(mc2_)[qc2_].sum().nsmallest(10)
            ch1,ch2 = st.columns(2)
            with ch1:
                st.markdown(f"**{t('Top 10 by Qty','اعلى 10 بالكمية')}**")
                st.bar_chart(top10, use_container_width=True)
            with ch2:
                st.markdown(f"**{t('Bottom 10 by Qty','اقل 10 بالكمية')}**")
                st.bar_chart(bot10, use_container_width=True)

    with tabs[ti]:
        ti += 1
        st.markdown(f"### {t('Price History','تاريخ الاسعار')}")
        hdf = build_price_history_df()
        if hdf.empty:
            st.info(t("Run multiple comparisons to track prices.",
                      "قم بتشغيل مقارنات متعددة لتتبع الاسعار."))
        else:
            st.line_chart(hdf, use_container_width=True)
            if st.button(t("Clear History","مسح السجل")):
                st.session_state.price_history = {}
                st.rerun()

    if hb:
        with tabs[ti]:
            ti += 1
            st.markdown(f"### {t('Branch-wise Stock','مخزون حسب الفرع')}")
            display_df(bdf, thr, table_key="branch")
            bc2 = t("Branch","الفرع")
            okb = bdf[bdf["_status"]=="OK"] if "_status" in bdf.columns else bdf
            if not okb.empty and bc2 in okb.columns and qc2 in okb.columns:
                chart = okb.groupby([sc2,bc2])[qc2].sum().reset_index()
                if not chart.empty:
                    st.markdown(f"#### {t('Qty by Branch','الكميات حسب الفرع')}")
                    st.bar_chart(chart.set_index(bc2)[qc2], use_container_width=True)
            b1,b2,_ = st.columns([1,1,2])
            b1.download_button(
                "CSV", to_csv(bdf), dl_name("branch","csv"), "text/csv",
                use_container_width=True)
            b2.download_button(
                "Excel", to_excel(bdf), dl_name("branch","xlsx"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)

    if ht:
        with tabs[ti]:
            ti += 1
            st.markdown(f"### {t('Pending Transfers','النقليات المعلقة')}")
            okt = trdf[trdf["_status"]=="OK"] if "_status" in trdf.columns else trdf
            if not okt.empty:
                k1,k2,k3 = st.columns(3)
                k1.metric(t("Total","اجمالي"), len(okt))
                qd = t("Qty","الكمية")
                if qd  in okt.columns:
                    k2.metric(t("Total Qty","اجمالي الكمية"), int(okt[qd].sum()))
                if sc2 in okt.columns:
                    k3.metric(t("Systems","الانظمة"), okt[sc2].nunique())
            display_df(trdf, thresh=0, table_key="transfers")
            x1,x2,_ = st.columns([1,1,2])
            x1.download_button(
                "CSV", to_csv(trdf), dl_name("transfers","csv"), "text/csv",
                use_container_width=True)
            x2.download_button(
                "Excel", to_excel(trdf), dl_name("transfers","xlsx"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)

    if hr:
        with tabs[ti]:
            CPRI  = t("Priority","الاولوية")
            CSUGG = t("Suggest","المقترح")
            st.markdown(f"### {t('Reorder Suggestions','اقتراحات اعادة الطلب')}")
            okr = rdf[rdf["_status"]=="OK"] if "_status" in rdf.columns else rdf
            if not okr.empty:
                crit = okr[okr[CPRI].str.startswith("Critical")].shape[0] if CPRI in okr.columns else 0
                lo   = okr[okr[CPRI].str.startswith("Low")].shape[0]      if CPRI in okr.columns else 0
                okn  = okr[okr[CPRI].str.startswith("OK")].shape[0]       if CPRI in okr.columns else 0
                sg   = int(okr[CSUGG].sum())                               if CSUGG in okr.columns else 0
                r1,r2,r3,r4 = st.columns(4)
                r1.metric(t("Critical","حرج"), crit)
                r2.metric(t("Low","منخفض"), lo)
                r3.metric(t("OK","كافٍ"), okn)
                r4.metric(t("To Order","للطلب"), sg)
                if crit+lo > 0:
                    st.markdown(
                        f"<div class='alert-banner'>"
                        f"{crit+lo} "
                        f"{t('products need reordering','منتجات تحتاج اعادة طلب')}"
                        f"</div>", unsafe_allow_html=True)
                sa = st.toggle(t("Show all","عرض الكل"), value=False)
                if sa:
                    dr = okr
                elif CPRI in okr.columns:
                    dr = okr[okr[CPRI].isin(["Critical","Low",
                                             t("Critical","حرج"), t("Low","منخفض")])]
                else:
                    dr = okr
                display_df(dr.reset_index(drop=True), table_key="reorder")
            else:
                st.info(t("No reorder data.","لا بيانات اعادة طلب."))
            o1,o2,_ = st.columns([1,1,2])
            o1.download_button(
                "CSV", to_csv(rdf), dl_name("reorder","csv"), "text/csv",
                use_container_width=True)
            o2.download_button(
                "Excel", to_excel(rdf), dl_name("reorder","xlsx"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
restore_session()

if not st.session_state.authenticated:
    show_login()
else:
    show_dashboard()
