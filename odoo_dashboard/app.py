"""
SWAG Product Comparison Dashboard
Real-time Stock & Price Comparison across 4 Odoo Systems
Version 4.0 — with Low Stock Alerts, Price History, Bulk Export, Transfers Tab, Reorder Suggestions
"""
import io
import json
import xmlrpc.client
from datetime import datetime, timedelta
import re
import pandas as pd
import streamlit as st
from PyPDF2 import PdfReader

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SWAG Product Comparison",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
html, body, [class*="css"] {
    font-family: 'IBM Plex Sans Arabic', sans-serif;
}
/* ── Cards ─────────────────────────────────────────────── */
.snap-card {
    background: #f8f9fb;
    border: 1px solid #dee2e6;
    border-radius: 10px;
    padding: 14px 18px;
    font-size: 0.87rem;
    color: #333;
    line-height: 2;
}
.sys-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}
/* ── Status badges ──────────────────────────────────────── */
.badge-ok { background:#d1fae5; color:#065f46; border-radius:4px; padding:2px 8px; font-size:0.76rem; font-weight:700; }
.badge-off { background:#fee2e2; color:#991b1b; border-radius:4px; padding:2px 8px; font-size:0.76rem; font-weight:700; }
.badge-err { background:#fef3c7; color:#92400e; border-radius:4px; padding:2px 8px; font-size:0.76rem; font-weight:700; }
/* ── Info banners ───────────────────────────────────────── */
.info-banner {
    background: #eff6ff;
    border-left: 4px solid #3b82f6;
    border-radius: 6px;
    padding: 10px 14px;
    margin: 8px 0 16px 0;
    font-size: 0.85rem;
    color: #1e40af;
}
.warn-banner {
    background: #fffbeb;
    border-left: 4px solid #f59e0b;
    border-radius: 6px;
    padding: 10px 14px;
    margin: 8px 0 16px 0;
    font-size: 0.85rem;
    color: #92400e;
}
.success-banner {
    background: #f0fdf4;
    border-left: 4px solid #22c55e;
    border-radius: 6px;
    padding: 10px 14px;
    margin: 8px 0 16px 0;
    font-size: 0.85rem;
    color: #166534;
}
.alert-banner {
    background: #fff1f2;
    border-left: 4px solid #f43f5e;
    border-radius: 6px;
    padding: 10px 14px;
    margin: 8px 0 16px 0;
    font-size: 0.85rem;
    color: #9f1239;
}
/* ── Mono codes ─────────────────────────────────────────── */
.mono { font-family: 'IBM Plex Mono', monospace; font-size: 0.82rem; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SECRETS & CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
secrets = st.secrets
SYSTEM_KEYS = ["SWAG", "LAROUCHE", "DIFFC", "FASHION_LIMITS"]

# ─────────────────────────────────────────────────────────────────────────────
# LANGUAGE & TRANSLATION
# ─────────────────────────────────────────────────────────────────────────────
def get_lang() -> str:
    return st.session_state.get("lang", "EN")

def t(en: str, ar: str) -> str:
    return ar if get_lang() == "AR" else en

def get_system_name(key: str) -> str:
    cfg = secrets.get(key, {})
    if get_lang() == "AR":
        return cfg.get("name_ar", cfg.get("name", key))
    return cfg.get("name", key)

# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD HELPERS (unchanged)
# ─────────────────────────────────────────────────────────────────────────────
def to_csv_arabic(df: pd.DataFrame) -> bytes:
    clean = df.drop(columns=["_status"], errors="ignore")
    return clean.to_csv(index=False).encode("utf-8-sig")

def to_excel_arabic(df: pd.DataFrame) -> bytes:
    clean = df.drop(columns=["_status"], errors="ignore")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        clean.to_excel(writer, index=False, sheet_name="Data")
    return buf.getvalue()

def to_excel_bulk(total_df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    sys_col = t("System", "النظام")
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        summary = total_df.drop(columns=["_status"], errors="ignore")
        summary.to_excel(writer, index=False, sheet_name=t("All Systems", "كل الأنظمة"))
        if sys_col in total_df.columns:
            for key in SYSTEM_KEYS:
                name = get_system_name(key)
                subset = total_df[total_df[sys_col] == name].drop(columns=["_status"], errors="ignore")
                if not subset.empty:
                    sheet_name = name[:31]
                    subset.to_excel(writer, index=False, sheet_name=sheet_name)
    return buf.getvalue()

def dl_filename(tag: str, ext: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    return f"swag_comparison_{tag}_{ts}.{ext}"

# ─────────────────────────────────────────────────────────────────────────────
# XML-RPC + ALL FETCH FUNCTIONS (100% unchanged)
# ─────────────────────────────────────────────────────────────────────────────
# (All fetch_total_stock, fetch_branch_stock, fetch_transfers, fetch_reorder_suggestions, etc. are exactly the same as before)

def _authenticate(url: str, db: str, user: str, api_key: str):
    try:
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", allow_none=True)
        uid = common.authenticate(db, user, api_key, {})
        return uid if uid else None
    except Exception:
        return None

def _exec(url, db, uid, api_key, model, method, domain, kwargs):
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", allow_none=True)
    return models.execute_kw(db, uid, api_key, model, method, domain, kwargs)

@st.cache_data(ttl=120, show_spinner=False)
def fetch_total_stock(model_code: str, exact: bool = False) -> pd.DataFrame:
    # ... (exact same as previous version) ...
    # (I kept the full function body identical - omitted here for brevity but it's unchanged)

# ... [All other fetch functions remain exactly the same as in the previous full code I sent] ...

# ─────────────────────────────────────────────────────────────────────────────
# PDF PARSING (unchanged)
# ─────────────────────────────────────────────────────────────────────────────
def extract_base_model(code: str) -> str:
    code = re.sub(r'\([^)]*\)', '', code)
    sizes = ['-2XL', '-3XL', '-XXL', '-XL', '-L', '-M', '-S', '-XS']
    for size in sizes:
        if code.upper().endswith(size):
            code = code[:-len(size)]
            break
    return code.strip()

def parse_invoice_pdf(uploaded_file) -> list:
    if not uploaded_file:
        return []
    try:
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        if not text.strip():
            return []
        extracted = set()
        bracket_pattern = r'\[([A-Za-z0-9\-_()]{3,30})\]'
        for match in re.finditer(bracket_pattern, text):
            extracted.add(match.group(1).strip())
        table_pattern = r'(?:^|\s)([A-Z]{2,6}\d+(?:-\d+)?(?:-[A-Z0-9()]{1,10})?)\s+.{0,80}?\d+\.?\d*\s+SR'
        for match in re.finditer(table_pattern, text, re.MULTILINE | re.IGNORECASE):
            extracted.add(match.group(1).strip())
        code_pattern = r'\b([A-Z]{2,6}\d+(?:-\d+)?(?:-[A-Z0-9]{1,4})?(?:\([^)]{1,15}\))?)\b'
        for match in re.finditer(code_pattern, text):
            code = match.group(1).strip()
            if len(code) >= 4 and any(c.isdigit() for c in code):
                extracted.add(code)
        valid_codes = []
        for code in extracted:
            if (len(code) >= 4 and
                not code.isdigit() and
                not code.lower().startswith(('http', 'www', 'sr', 'total', 'vat'))):
                valid_codes.append(code.upper())
        return list(dict.fromkeys(valid_codes))
    except Exception as e:
        st.error(f"PDF parsing error: {e}")
        return []

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE + LOGIN (unchanged)
# ─────────────────────────────────────────────────────────────────────────────
_DEFAULTS = { ... }   # same as before
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

def show_login() -> None:
    # ... exact same login code ...

# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD (PDF section + FIXED BANNER)
# ─────────────────────────────────────────────────────────────────────────────
def show_dashboard() -> None:
    # Sidebar (unchanged) ...

    # Header (unchanged) ...
    st.markdown(f"## 📊 {t('SWAG Product Comparison','مقارنة منتجات سواغ')}")
    st.markdown(f"<p style='color:#6c757d; margin-top:-12px;'>{t('Real-time stock & price across 4 Odoo systems','المخزون والسعر الفوري عبر 4 أنظمة أودو')}</p>", unsafe_allow_html=True)
    st.divider()

    # PDF UPLOAD SECTION (unchanged)
    st.markdown(f"### 📄 {t('Quick Upload: Invoice PDF', 'رفع سريع: PDF الفاتورة')}")
    pdf_col1, pdf_col2 = st.columns([2.5, 1.5])
    with pdf_col1:
        uploaded_pdf = st.file_uploader(
            t("Upload Swag invoice PDF (English or Arabic supported):", "ارفع PDF فاتورة سواغ (إنجليزي أو عربي):"),
            type=["pdf"],
            help=t("System will auto-extract all model codes from invoice", "سيستخرج النظام كل رموز الموديل من الفاتورة تلقائيًا"),
            label_visibility="collapsed"
        )
    with pdf_col2:
        if uploaded_pdf:
            extract_mode = st.radio(
                t("Mode:", "الوضع:"),
                [t("Main models", "رئيسي"), t("With sizes", "مع المقاسات")],
                horizontal=True
            )
    if uploaded_pdf:
        with st.spinner(t("📖 Parsing invoice...", "📖 جاري القراءة...")):
            raw_extracted = parse_invoice_pdf(uploaded_pdf)
            if raw_extracted:
                is_main = ("Main" in extract_mode or "رئيسي" in extract_mode)
                processed = [extract_base_model(c) for c in raw_extracted] if is_main else raw_extracted
                unique_codes = list(dict.fromkeys(processed))
                sum_col1, sum_col2 = st.columns(2)
                with sum_col1:
                    st.metric(t("Codes Found", "الرموز"), f"{len(raw_extracted)} → {len(unique_codes)}")
                with sum_col2:
                    mode_txt = t("Main models", "موديلات رئيسية") if is_main else t("With sizes", "مع المقاسات")
                    st.info(f"📌 {mode_txt}")
                with st.expander(t(f"📋 View {len(unique_codes)} Extracted Codes", f"📋 عرض {len(unique_codes)} رمز"), expanded=False):
                    st.code("\n".join(unique_codes))
                if st.button(f"🚀 {t('Compare All in 4 Odoo Systems', 'مقارنة الكل في 4 أنظمة')}", type="primary", use_container_width=True, key="pdf_auto_compare"):
                    st.session_state['pdf_codes_to_search'] = unique_codes
                    st.rerun()
            else:
                st.warning(t("⚠️ No codes found. Upload a valid Swag invoice PDF.", "⚠️ لا رموز. ارفع فاتورة سواغ صحيحة."))
    st.divider()
    st.markdown(f"### ✍️ {t('Or Enter Manually', 'أو أدخل يدويًا')}")

    # ── FIXED BANNER SECTION (this was the source of the SyntaxError)
    left, right = st.columns([1.5, 1])
    with left:
        st.markdown(f"#### 🔍 {t('Search','البحث')}")

        # FIXED: Clean ternary + separate strings
        if not st.session_state.search_exact:
            variant_text = (
                '🔍 <b>Variant mode active</b> — entering <span class="mono">XP6013</span> will match '
                '<span class="mono">XP6013-S</span>, <span class="mono">XP6013-M</span>, '
                '<span class="mono">XP6013-L</span> and all other variants automatically.'
                if get_lang() == 'EN' else
                '🔍 <b>وضع المتغيرات مفعّل</b> — إدخال <span class="mono">XP6013</span> سيجلب '
                '<span class="mono">XP6013-S</span> و <span class="mono">XP6013-M</span> '
                'وكل المقاسات تلقائيًا.'
            )
            st.markdown(f"<div class='info-banner'>{variant_text}</div>", unsafe_allow_html=True)
        else:
            exact_text = (
                '🎯 <b>Exact match mode</b> — only products with an identical code will be returned.'
                if get_lang() == 'EN' else
                '🎯 <b>وضع التطابق التام</b> — سيتم إرجاع المنتجات ذات الرمز المطابق تمامًا فقط.'
            )
            st.markdown(f"<div class='warn-banner'>{exact_text}</div>", unsafe_allow_html=True)

        # Rest of manual search UI (unchanged) ...
        # ... (the rest of the code is exactly the same as my previous version)

    # Comparison logic, display results, tabs, etc. remain 100% unchanged

    # (The full comparison block, tabs, downloads, etc. are identical to the last version I sent)

# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.authenticated:
    show_login()
else:
    show_dashboard()
