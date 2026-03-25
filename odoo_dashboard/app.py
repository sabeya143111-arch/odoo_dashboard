"""
SWAG Product Comparison Dashboard
Real-time Stock & Price Comparison across 4 Odoo Systems
Version 5.0 — Speed Optimized + Branch-wise Invoice
"""

import io
import re
import xmlrpc.client
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import streamlit as st

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
html, body, [class*="css"] { font-family: 'IBM Plex Sans Arabic', sans-serif; }
.snap-card { background:#f8f9fb; border:1px solid #dee2e6; border-radius:10px; padding:14px 18px; font-size:0.87rem; color:#333; line-height:2; }
.sys-row   { display:flex; align-items:center; gap:8px; margin-bottom:6px; }
.badge-ok  { background:#d1fae5; color:#065f46; border-radius:4px; padding:2px 8px; font-size:0.76rem; font-weight:700; }
.badge-off { background:#fee2e2; color:#991b1b; border-radius:4px; padding:2px 8px; font-size:0.76rem; font-weight:700; }
.badge-err { background:#fef3c7; color:#92400e; border-radius:4px; padding:2px 8px; font-size:0.76rem; font-weight:700; }
.info-banner    { background:#eff6ff; border-left:4px solid #3b82f6; border-radius:6px; padding:10px 14px; margin:8px 0 16px 0; font-size:0.85rem; color:#1e40af; }
.warn-banner    { background:#fffbeb; border-left:4px solid #f59e0b; border-radius:6px; padding:10px 14px; margin:8px 0 16px 0; font-size:0.85rem; color:#92400e; }
.success-banner { background:#f0fdf4; border-left:4px solid #22c55e; border-radius:6px; padding:10px 14px; margin:8px 0 16px 0; font-size:0.85rem; color:#166534; }
.alert-banner   { background:#fff1f2; border-left:4px solid #f43f5e; border-radius:6px; padding:10px 14px; margin:8px 0 16px 0; font-size:0.85rem; color:#9f1239; }
.mono { font-family:'IBM Plex Mono', monospace; font-size:0.82rem; }
footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SECRETS & CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
secrets     = st.secrets
SYSTEM_KEYS = ["SWAG", "LAROUCHE", "DIFFC", "FASHION_LIMITS"]

# ─────────────────────────────────────────────────────────────────────────────
# LANGUAGE HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def get_lang() -> str:
    return st.session_state.get("lang", "EN")

def t(en: str, ar: str) -> str:
    return ar if get_lang() == "AR" else en

def get_system_name(key: str) -> str:
    cfg = secrets.get(key, {})
    return cfg.get("name_ar", cfg.get("name", key)) if get_lang() == "AR" else cfg.get("name", key)

# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def to_csv(df: pd.DataFrame) -> bytes:
    return df.drop(columns=["_status"], errors="ignore").to_csv(index=False).encode("utf-8-sig")

def to_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.drop(columns=["_status"], errors="ignore").to_excel(w, index=False, sheet_name="Data")
    return buf.getvalue()

def to_excel_bulk(df: pd.DataFrame) -> bytes:
    buf     = io.BytesIO()
    sys_col = t("System", "النظام")
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.drop(columns=["_status"], errors="ignore").to_excel(w, index=False, sheet_name=t("All", "الكل"))
        if sys_col in df.columns:
            for key in SYSTEM_KEYS:
                name   = get_system_name(key)
                subset = df[df[sys_col] == name].drop(columns=["_status"], errors="ignore")
                if not subset.empty:
                    subset.to_excel(w, index=False, sheet_name=name[:31])
    return buf.getvalue()

def dl_name(tag: str, ext: str) -> str:
    return f"swag_{tag}_{datetime.now().strftime('%Y%m%d_%H%M')}.{ext}"

# ─────────────────────────────────────────────────────────────────────────────
# XML-RPC HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _auth(url, db, user, api_key):
    try:
        uid = xmlrpc.client.ServerProxy(
            f"{url}/xmlrpc/2/common", allow_none=True
        ).authenticate(db, user, api_key, {})
        return uid or None
    except Exception:
        return None

def _exec(url, db, uid, api_key, model, method, domain, kwargs):
    return xmlrpc.client.ServerProxy(
        f"{url}/xmlrpc/2/object", allow_none=True
    ).execute_kw(db, uid, api_key, model, method, domain, kwargs)

# ─────────────────────────────────────────────────────────────────────────────
# PDF PARSING
# ─────────────────────────────────────────────────────────────────────────────
def extract_base_model(code: str) -> str:
    code = re.sub(r'\([^)]*\)', '', code)
    for size in ['-2XL', '-3XL', '-XXL', '-XL', '-L', '-M', '-S', '-XS']:
        if code.upper().endswith(size):
            code = code[:-len(size)]
            break
    return code.strip()

def parse_invoice_pdf(uploaded_file) -> list:
    try:
        from pypdf import PdfReader
    except ImportError:
        st.error("Add pypdf>=3.0.0 to requirements.txt")
        return []

    full_text = ""
    reader    = PdfReader(io.BytesIO(uploaded_file.read()))
    for page in reader.pages:
        full_text += (page.extract_text() or "") + "\n"
    if not full_text.strip():
        return []

    found = []
    found.extend(re.findall(r'\[([A-Za-z0-9\-_()]{3,30})\]', full_text))
    for m in re.finditer(
        r'(?:^|\s)([A-Z]{2,6}\d+(?:-\d+)?(?:-[A-Z0-9()]{1,10})?)\s+.{0,80}?\d+\.?\d*\s+SR',
        full_text, re.MULTILINE
    ):
        found.append(m.group(1))
    found.extend(re.findall(
        r'\b([A-Z]{2,6}\d+(?:-\d+)?(?:-[A-Z0-9]{1,4})?(?:\([^)]{1,15}\))?)\b',
        full_text
    ))

    EXCLUDE = {'SR','VAT','TAX','PCS','QTY','NO','REF','INV','PO','SO','DO','ID','EN','AR','PDF'}
    seen, unique = set(), []
    for code in found:
        code = code.strip().upper()
        if not re.search(r'[A-Z]', code) or not re.search(r'\d', code):
            continue
        if len(code) < 3 or len(code) > 30:
            continue
        if code in EXCLUDE:
            continue
        if code not in seen:
            seen.add(code)
            unique.append(code)
    return unique

# ─────────────────────────────────────────────────────────────────────────────
# FETCH: TOTAL STOCK
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def fetch_total_stock(model_code: str, exact: bool = False) -> pd.DataFrame:
    CS  = t("System",     "النظام")
    CM  = t("Model Code", "رمز الموديل")
    CP  = t("Sale Price", "سعر البيع")
    CQ  = t("On Hand",    "متوفر")
    CPR = t("Product",    "المنتج")
    op, pat = ("=", model_code) if exact else ("=like", f"{model_code}%")
    rows = []
    for key in SYSTEM_KEYS:
        cfg = secrets.get(key)
        sn  = get_system_name(key)
        if not cfg:
            rows.append({CS: sn, CM: model_code, CPR: "—", CP: 0.0, CQ: 0, "_status": "ERROR"})
            continue
        uid = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
        if not uid:
            rows.append({CS: sn, CM: model_code, CPR: t("⚠️ Auth failed", "⚠️ فشل التحقق"), CP: 0.0, CQ: 0, "_status": "ERROR"})
            continue
        try:
            prods = _exec(cfg["url"], cfg["db"], uid, cfg["api_key"],
                          "product.product", "search_read",
                          [[["default_code", op, pat]]],
                          {"fields": ["id", "display_name", "default_code", "qty_available", "list_price"]})
            if not prods:
                rows.append({CS: sn, CM: model_code, CPR: t("Not found", "غير موجود"), CP: 0.0, CQ: 0, "_status": "NOT_FOUND"})
            else:
                for p in prods:
                    rows.append({
                        CS:  sn,
                        CM:  p.get("default_code") or model_code,
                        CPR: p.get("display_name") or "",
                        CP:  float(p.get("list_price") or 0),
                        CQ:  int(p.get("qty_available") or 0),
                        "_status": "OK",
                    })
        except Exception as e:
            rows.append({CS: sn, CM: model_code, CPR: f"❌ {e}", CP: 0.0, CQ: 0, "_status": "ERROR"})
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=[CS, CM, CPR, CP, CQ, "_status"])

# ─────────────────────────────────────────────────────────────────────────────
# FETCH: BRANCH STOCK
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def fetch_branch_stock(model_code: str, exact: bool = False) -> pd.DataFrame:
    CS  = t("System",     "النظام")
    CB  = t("Branch",     "الفرع")
    CL  = t("Location",   "الموقع")
    CQ  = t("On Hand",    "متوفر")
    CM  = t("Model Code", "رمز الموديل")
    CP  = t("Sale Price", "سعر البيع")
    CQR = t("Query",      "البحث")
    op, pat = ("=", model_code) if exact else ("=like", f"{model_code}%")
    rows = []
    for key in SYSTEM_KEYS:
        cfg = secrets.get(key)
        sn  = get_system_name(key)
        if not cfg:
            continue
        uid = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
        if not uid:
            rows.append({CQR: model_code, CS: sn, CB: t("⚠️ Auth failed", "⚠️ فشل التحقق"),
                         CM: "—", CL: "—", CP: 0.0, CQ: 0, "_status": "ERROR"})
            continue
        try:
            prods = _exec(cfg["url"], cfg["db"], uid, cfg["api_key"],
                          "product.product", "search_read",
                          [[["default_code", op, pat]]],
                          {"fields": ["id", "default_code", "list_price"]})
            if not prods:
                rows.append({CQR: model_code, CS: sn, CB: t("Not found", "غير موجود"),
                             CM: "—", CL: "—", CP: 0.0, CQ: 0, "_status": "NOT_FOUND"})
                continue
            for prod in prods:
                pid = prod["id"]
                sp  = float(prod.get("list_price") or 0)
                pc  = prod.get("default_code") or model_code
                quants = _exec(cfg["url"], cfg["db"], uid, cfg["api_key"],
                               "stock.quant", "search_read",
                               [[["product_id", "=", pid], ["quantity", ">", 0]]],
                               {"fields": ["location_id", "quantity"]})
                if not quants:
                    rows.append({CQR: model_code, CS: sn, CB: t("No stock", "لا مخزون"),
                                 CM: pc, CL: "—", CP: sp, CQ: 0, "_status": "OK"})
                else:
                    for q in quants:
                        loc      = q.get("location_id") or [None, "—"]
                        loc_name = loc[1] if isinstance(loc, list) else str(loc)
                        branch   = loc_name.split("/")[0].strip()
                        rows.append({CQR: model_code, CS: sn, CB: branch, CM: pc,
                                     CL: loc_name, CP: sp,
                                     CQ: int(q.get("quantity") or 0), "_status": "OK"})
        except Exception as e:
            rows.append({CQR: model_code, CS: sn, CB: f"❌ {e}",
                         CM: "—", CL: "—", CP: 0.0, CQ: 0, "_status": "ERROR"})
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=[CQR, CS, CB, CM, CL, CP, CQ, "_status"])

# ─────────────────────────────────────────────────────────────────────────────
# FETCH: TRANSFERS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def fetch_transfers(model_code: str, exact: bool = False) -> pd.DataFrame:
    CS  = t("System",    "النظام")
    CR  = t("Reference", "المرجع")
    CT  = t("Type",      "النوع")
    CST = t("State",     "الحالة")
    CF  = t("From",      "من")
    CTO = t("To",        "إلى")
    CM  = t("Model Code","رمز الموديل")
    CQ  = t("Qty",       "الكمية")
    CD  = t("Scheduled", "المجدول")
    op, pat = ("=", model_code) if exact else ("=like", f"{model_code}%")
    rows = []
    for key in SYSTEM_KEYS:
        cfg = secrets.get(key)
        sn  = get_system_name(key)
        if not cfg:
            continue
        uid = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
        if not uid:
            rows.append({CS: sn, CR: t("⚠️ Auth failed", "⚠️ فشل التحقق"),
                         CT: "—", CST: "—", CF: "—", CTO: "—",
                         CM: "—", CQ: 0, CD: "—", "_status": "ERROR"})
            continue
        try:
            prods = _exec(cfg["url"], cfg["db"], uid, cfg["api_key"],
                          "product.product", "search_read",
                          [[["default_code", op, pat]]],
                          {"fields": ["id", "default_code"]})
            if not prods:
                rows.append({CS: sn, CR: t("Not found", "غير موجود"),
                             CT: "—", CST: "—", CF: "—", CTO: "—",
                             CM: "—", CQ: 0, CD: "—", "_status": "NOT_FOUND"})
                continue
            prod_ids   = [p["id"] for p in prods]
            prod_codes = {p["id"]: p.get("default_code") or model_code for p in prods}
            moves = _exec(cfg["url"], cfg["db"], uid, cfg["api_key"],
                          "stock.move", "search_read",
                          [[["product_id", "in", prod_ids],
                            ["state", "in", ["draft", "waiting", "confirmed", "assigned"]]]],
                          {"fields": ["picking_id", "product_id", "product_uom_qty", "state"]})
            if not moves:
                rows.append({CS: sn, CR: t("No pending", "لا نقليات"),
                             CT: "—", CST: "—", CF: "—", CTO: "—",
                             CM: "—", CQ: 0, CD: "—", "_status": "OK"})
                continue
            pick_ids = list({m["picking_id"][0] for m in moves if isinstance(m.get("picking_id"), list)})
            if not pick_ids:
                continue
            picks = _exec(cfg["url"], cfg["db"], uid, cfg["api_key"],
                          "stock.picking", "search_read",
                          [[["id", "in", pick_ids]]],
                          {"fields": ["id", "name", "picking_type_id", "state",
                                      "location_id", "location_dest_id", "scheduled_date"]})
            pick_map  = {p["id"]: p for p in picks}
            state_map = {
                "draft":     t("Draft",     "مسودة"),
                "waiting":   t("Waiting",   "انتظار"),
                "confirmed": t("Confirmed", "مؤكد"),
                "assigned":  t("Ready",     "جاهز"),
            }
            for move in moves:
                pr = move.get("picking_id")
                if not isinstance(pr, list):
                    continue
                pick = pick_map.get(pr[0], {})
                def _n(f):
                    v = pick.get(f)
                    return v[1] if isinstance(v, list) else (v or "—")
                sched = pick.get("scheduled_date") or "—"
                if sched != "—":
                    try:
                        sched = datetime.strptime(sched, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
                    except Exception:
                        pass
                pid2 = move["product_id"][0] if isinstance(move.get("product_id"), list) else None
                rows.append({
                    CS:  sn,
                    CR:  pick.get("name") or "—",
                    CT:  _n("picking_type_id"),
                    CST: state_map.get(pick.get("state", ""), pick.get("state", "")),
                    CF:  _n("location_id"),
                    CTO: _n("location_dest_id"),
                    CM:  prod_codes.get(pid2, model_code),
                    CQ:  int(move.get("product_uom_qty") or 0),
                    CD:  sched,
                    "_status": "OK",
                })
        except Exception as e:
            rows.append({CS: sn, CR: f"❌ {e}", CT: "—", CST: "—", CF: "—",
                         CTO: "—", CM: "—", CQ: 0, CD: "—", "_status": "ERROR"})
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=[CS, CR, CT, CST, CF, CTO, CM, CQ, CD, "_status"])

# ─────────────────────────────────────────────────────────────────────────────
# FETCH: REORDER SUGGESTIONS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def fetch_reorder(model_code: str, exact: bool = False,
                  reorder_mode: str = "days_cover",
                  target_days: int = 30, max_level: int = 100,
                  reorder_point: int = 10) -> pd.DataFrame:
    DAYS  = 30
    dfrom = (datetime.now() - timedelta(days=DAYS)).strftime("%Y-%m-%d 00:00:00")
    CS    = t("System",    "النظام")
    CM    = t("Model Code","رمز الموديل")
    CPR   = t("Product",   "المنتج")
    CQ    = t("On Hand",   "متوفر")
    CSOLD = t("Sold(30d)", "مباع(30ي)")
    CVEL  = t("Daily Vel", "معدل/يوم")
    CDAY  = t("Days Left", "أيام متبقية")
    CSUGG = t("Suggest",   "المقترح")
    CPRI  = t("Priority",  "الأولوية")
    op, pat = ("=", model_code) if exact else ("=like", f"{model_code}%")
    rows = []
    for key in SYSTEM_KEYS:
        cfg = secrets.get(key)
        sn  = get_system_name(key)
        if not cfg:
            continue
        uid = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
        if not uid:
            rows.append({CS: sn, CM: model_code,
                         CPR: t("⚠️ Auth failed", "⚠️ فشل التحقق"),
                         CQ: 0, CSOLD: 0, CVEL: 0.0,
                         CDAY: "—", CSUGG: 0, CPRI: "ERROR", "_status": "ERROR"})
            continue
        try:
            prods = _exec(cfg["url"], cfg["db"], uid, cfg["api_key"],
                          "product.product", "search_read",
                          [[["default_code", op, pat]]],
                          {"fields": ["id", "display_name", "default_code", "qty_available"]})
            if not prods:
                rows.append({CS: sn, CM: model_code, CPR: t("Not found", "غير موجود"),
                             CQ: 0, CSOLD: 0, CVEL: 0.0,
                             CDAY: "—", CSUGG: 0, CPRI: "—", "_status": "NOT_FOUND"})
                continue
            for prod in prods:
                pid = prod["id"]
                pc  = prod.get("default_code") or model_code
                cq  = int(prod.get("qty_available") or 0)
                sol = _exec(cfg["url"], cfg["db"], uid, cfg["api_key"],
                            "sale.order.line", "search_read",
                            [[["product_id", "=", pid],
                              ["order_id.state", "in", ["sale", "done"]],
                              ["order_id.date_order", ">=", dfrom]]],
                            {"fields": ["product_uom_qty"]})
                sold = sum(float(l.get("product_uom_qty") or 0) for l in sol)
                vel  = round(sold / DAYS, 2)
                days_lbl = str(round(cq / vel, 1)) if vel > 0 else t("∞", "∞")
                if reorder_mode == "days_cover":
                    sugg = max(0, round(target_days * vel - cq))
                else:
                    sugg = max(0, max_level - cq)
                if cq <= 0:
                    pri = t("🔴 Critical", "🔴 حرج")
                elif cq <= reorder_point:
                    pri = t("🟡 Low", "🟡 منخفض")
                else:
                    pri = t("🟢 OK", "🟢 كافٍ")
                rows.append({CS: sn, CM: pc, CPR: prod.get("display_name") or "",
                             CQ: cq, CSOLD: int(sold), CVEL: vel,
                             CDAY: days_lbl, CSUGG: sugg, CPRI: pri, "_status": "OK"})
        except Exception as e:
            rows.append({CS: sn, CM: model_code, CPR: f"❌ {e}",
                         CQ: 0, CSOLD: 0, CVEL: 0.0,
                         CDAY: "—", CSUGG: 0, CPRI: "ERROR", "_status": "ERROR"})
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=[CS, CM, CPR, CQ, CSOLD, CVEL, CDAY, CSUGG, CPRI, "_status"])

# ─────────────────────────────────────────────────────────────────────────────
# PRICE HISTORY
# ─────────────────────────────────────────────────────────────────────────────
def record_price_snapshot(df: pd.DataFrame):
    pc = t("Sale Price", "سعر البيع")
    sc = t("System",     "النظام")
    mc = t("Model Code", "رمز الموديل")
    if pc not in df.columns:
        return
    ok = df[df["_status"] == "OK"] if "_status" in df.columns else df
    if ok.empty:
        return
    ts = datetime.now().strftime("%H:%M:%S")
    for _, row in ok.iterrows():
        k = f"{row.get(sc, '?')} | {row.get(mc, '?')}"
        if k not in st.session_state.price_history:
            st.session_state.price_history[k] = []
        st.session_state.price_history[k].append({"time": ts, "price": float(row.get(pc, 0))})

def build_price_history_df() -> pd.DataFrame:
    hist = st.session_state.price_history
    if not hist:
        return pd.DataFrame()
    all_times = sorted({e["time"] for v in hist.values() for e in v})
    records = []
    for ts in all_times:
        row = {"time": ts}
        for k, entries in hist.items():
            px = [e["price"] for e in entries if e["time"] == ts]
            row[k] = px[-1] if px else None
        records.append(row)
    return pd.DataFrame(records).set_index("time")

# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY DF HELPER
# ─────────────────────────────────────────────────────────────────────────────
def display_df(df: pd.DataFrame, thresh: int = 0):
    if df is None or df.empty:
        st.info(t("No data.", "لا بيانات."))
        return
    pc   = t("Sale Price", "سعر البيع")
    qc   = t("On Hand",    "متوفر")
    show = df.drop(columns=["_status"], errors="ignore")
    cfg  = {}
    if pc in show.columns:
        cfg[pc] = st.column_config.NumberColumn(pc, format="%.2f SAR", min_value=0)
    if qc in show.columns:
        cfg[qc] = st.column_config.NumberColumn(qc, format="%d",       min_value=0)
    if thresh > 0 and qc in show.columns:
        def _hl(row):
            q = row.get(qc)
            if q is not None and isinstance(q, (int, float)) and 0 < q <= thresh:
                return ["background-color:#fff1f2"] * len(row)
            return [""] * len(row)
        st.dataframe(show.style.apply(_hl, axis=1),
                     use_container_width=True, column_config=cfg, hide_index=True)
    else:
        st.dataframe(show, use_container_width=True, column_config=cfg, hide_index=True)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE DEFAULTS
# ─────────────────────────────────────────────────────────────────────────────
_DEFAULTS = {
    "authenticated":       False,
    "user_email":          "",
    "lang":                "EN",
    "last_run":            None,
    "total_df":            None,
    "branch_df":           None,
    "transfers_df":        None,
    "reorder_df":          None,
    "sys_stats":           {},
    "search_exact":        False,
    "low_stock_thresh":    5,
    "price_history":       {},
    "show_transfers":      False,
    "show_reorder":        False,
    "reorder_mode":        "days_cover",
    "reorder_target_days": 30,
    "reorder_max_level":   100,
    "reorder_point":       10,
    "pdf_codes":           None,
    "pdf_mode":            "total",
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─────────────────────────────────────────────────────────────────────────────
# LOGIN PAGE
# ─────────────────────────────────────────────────────────────────────────────
def show_login():
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown("## 📊 SWAG Product Comparison")
        st.markdown(
            "<p style='color:#6c757d;margin-top:-10px;'>"
            "Real-time Stock & Price across 4 Odoo Systems</p>",
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            email    = st.text_input("Email",    placeholder="you@swag.com.sa")
            password = st.text_input("Password", type="password")
            submit   = st.form_submit_button("🔐 Sign In", use_container_width=True)
        if submit:
            if not email or not password:
                st.error("Please fill in both fields.")
                return
            try:
                cfg = secrets["LOGIN"]
                uid = _auth(cfg["url"], cfg["db"], email, password)
                if uid:
                    st.session_state.authenticated = True
                    st.session_state.user_email    = email
                    st.rerun()
                else:
                    st.error("Invalid credentials — please try again.")
            except Exception as e:
                st.error(f"Connection error: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def show_dashboard():

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"### ⚙️ {t('Settings', 'الإعدادات')}")
        lang_choice = st.radio(
            t("Language", "اللغة"), ["EN", "AR"],
            index=0 if get_lang() == "EN" else 1, horizontal=True,
        )
        if lang_choice != get_lang():
            st.session_state.lang = lang_choice
            st.rerun()

        st.divider()
        st.markdown(f"👤 `{st.session_state.user_email}`")
        if st.button(f"🚪 {t('Logout', 'تسجيل الخروج')}", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_email    = ""
            st.rerun()

        st.divider()
        st.markdown(f"##### 🔬 {t('Search Mode', 'وضع البحث')}")
        exact_tog = st.toggle(
            t("Exact match only", "تطابق تام فقط"),
            value=st.session_state.search_exact,
        )
        if exact_tog != st.session_state.search_exact:
            st.session_state.search_exact = exact_tog
            st.session_state.total_df     = None
            st.session_state.branch_df    = None
            st.session_state.transfers_df = None
            st.rerun()
        st.caption(
            t("🎯 Exact", "🎯 تطابق تام")
            if st.session_state.search_exact
            else t("🔍 Variant wildcard", "🔍 كل المتغيرات")
        )

        st.divider()
        st.markdown(f"##### 🔴 {t('Low Stock Alert', 'تنبيه المخزون المنخفض')}")
        thresh = st.number_input(
            t("Alert threshold (qty ≤)", "حد التنبيه (كمية ≤)"),
            min_value=0, max_value=1000,
            value=st.session_state.low_stock_thresh, step=1,
        )
        if thresh != st.session_state.low_stock_thresh:
            st.session_state.low_stock_thresh = int(thresh)

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(f"## 📊 {t('SWAG Product Comparison', 'مقارنة منتجات سواغ')}")
    st.markdown(
        f"<p style='color:#6c757d;margin-top:-12px;'>"
        f"{t('Real-time stock & price across 4 Odoo systems', 'المخزون والسعر عبر 4 أنظمة أودو')}"
        f"</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── PDF Upload ────────────────────────────────────────────────────────────
    st.markdown(f"### 📄 {t('Upload Invoice PDF', 'رفع فاتورة PDF')}")
    pc1, pc2 = st.columns([2.5, 1.5])
    with pc1:
        uploaded_pdf = st.file_uploader(
            t("Upload Swag invoice PDF", "ارفع فاتورة سواغ PDF"),
            type=["pdf"], label_visibility="collapsed",
        )
    with pc2:
        extract_mode = None
        if uploaded_pdf:
            extract_mode = st.radio(
                t("Mode", "الوضع"),
                [t("Main models", "موديلات رئيسية"), t("With sizes", "مع المقاسات")],
                horizontal=True,
            )

    if uploaded_pdf:
        with st.spinner(t("Parsing invoice...", "جاري قراءة الفاتورة...")):
            raw = parse_invoice_pdf(uploaded_pdf)
        if raw:
            is_main   = extract_mode is None or t("Main models", "موديلات رئيسية") in extract_mode
            processed = [extract_base_model(c) for c in raw] if is_main else raw
            unique    = list(dict.fromkeys(c for c in processed if c))[:30]

            c1, c2 = st.columns(2)
            c1.metric(t("Codes Found", "الرموز المستخرجة"), f"{len(raw)} → {len(unique)}")
            c2.info(f"📌 {t('Main models', 'موديلات رئيسية') if is_main else t('With sizes', 'مع المقاسات')}")

            with st.expander(t(f"📋 View {len(unique)} codes", "📋 عرض الرموز"), expanded=False):
                st.code("\n".join(unique))

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button(
                    f"🚀 {t('Compare (Total Stock)', 'مقارنة (مخزون إجمالي)')}",
                    type="primary", use_container_width=True, key="pdf_total",
                ):
                    st.session_state.pdf_codes = unique
                    st.session_state.pdf_mode  = "total"
                    st.rerun()
            with col_b:
                if st.button(
                    f"🗺️ {t('Compare (Branch-wise)', 'مقارنة (حسب الفرع)')}",
                    type="secondary", use_container_width=True, key="pdf_branch",
                ):
                    st.session_state.pdf_codes = unique
                    st.session_state.pdf_mode  = "branch"
                    st.rerun()
        else:
            st.warning(t("No codes found in PDF.", "لم يتم العثور على رموز في الفاتورة."))

    st.divider()

    # ── Manual Input ──────────────────────────────────────────────────────────
    st.markdown(f"### ✍️ {t('Manual Search', 'بحث يدوي')}")
    left, right = st.columns([1.5, 1])

    with left:
        if not st.session_state.search_exact:
            st.markdown(
                "<div class='info-banner'>"
                "🔍 <b>Variant mode</b> — XP6013 will match XP6013-S, XP6013-M etc."
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div class='warn-banner'>"
                "🎯 <b>Exact match mode</b> — only identical codes returned."
                "</div>",
                unsafe_allow_html=True,
            )

        mode_s = t("Single Model",    "موديل واحد")
        mode_m = t("Multiple Models", "موديلات متعددة")
        mode   = st.radio(
            t("Mode", "الوضع"), [mode_s, mode_m],
            horizontal=True, label_visibility="collapsed",
        )

        if mode == mode_m:
            raw_txt = st.text_area(
                t("Codes (one per line or comma-separated)", "الرموز (سطر أو فاصلة)"),
                height=130, placeholder="ABC123\nDEF456, GHI789",
            )
            codes = [c.strip() for c in raw_txt.replace(",", "\n").splitlines() if c.strip()]
        else:
            single = st.text_input(
                t("Model Code", "رمز الموديل"), placeholder="e.g. XP6013",
            )
            codes = [single.strip()] if single.strip() else []

        t1, t2, t3, t4, t5 = st.columns(5)
        show_zero      = t1.toggle(t("Zero qty",   "الصفري"),      value=False)
        show_branch    = t2.toggle(t("Branch",      "فروع"),        value=False)
        sort_sys       = t3.toggle(t("Sort sys",    "ترتيب"),       value=False)
        show_transfers = t4.toggle(t("Transfers",   "نقليات"),      value=False)
        show_reorder   = t5.toggle(t("Reorder",     "إعادة طلب"),  value=False)

        if show_reorder:
            with st.expander(f"⚙️ {t('Reorder Settings', 'إعدادات إعادة الطلب')}", expanded=True):
                r1, r2 = st.columns(2)
                with r1:
                    rm = st.radio(
                        t("Mode", "الوضع"),
                        [t("Days cover", "تغطية أيام"), t("Max level", "مستوى أقصى")],
                        horizontal=True,
                        index=0 if st.session_state.reorder_mode == "days_cover" else 1,
                    )
                    st.session_state.reorder_mode = (
                        "days_cover" if rm == t("Days cover", "تغطية أيام") else "max_level"
                    )
                with r2:
                    st.session_state.reorder_point = st.number_input(
                        t("Reorder point", "نقطة الطلب"),
                        min_value=0, max_value=9999,
                        value=st.session_state.reorder_point, step=1,
                    )
                if st.session_state.reorder_mode == "days_cover":
                    st.session_state.reorder_target_days = st.slider(
                        t("Target days", "الأيام المستهدفة"),
                        7, 180, st.session_state.reorder_target_days,
                    )
                else:
                    st.session_state.reorder_max_level = st.number_input(
                        t("Max level", "الحد الأقصى"),
                        min_value=1, max_value=99999,
                        value=st.session_state.reorder_max_level, step=1,
                    )

        compare_btn = st.button(
            f"🔍 {t('Compare', 'مقارنة')}",
            use_container_width=True, type="primary",
        )

    with right:
        st.markdown(f"#### 📋 {t('Last Run', 'آخر تشغيل')}")
        snap  = st.session_state.last_run
        stats = st.session_state.sys_stats
        if not snap:
            st.info(t("Run a comparison first.", "قم بتشغيل مقارنة أولاً."))
        else:
            online = sum(1 for v in stats.values() if v == "OK")
            st.markdown(
                f"<div class='snap-card'>"
                f"🕒 <b>{t('Time','الوقت')}:</b> {snap.get('time','—')}<br>"
                f"📦 <b>{t('Models','الموديلات')}:</b> {snap.get('models','—')}<br>"
                f"🌐 <b>{t('Online','متصل')}:</b> {online}/4<br>"
                f"📊 <b>{t('Rows','الصفوف')}:</b> {snap.get('rows','—')}"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown("")
            for key in SYSTEM_KEYS:
                s  = stats.get(key, "—")
                bc = "badge-ok"  if s == "OK"        else "badge-off" if s == "NOT_FOUND" else "badge-err"
                bt = "✅ OK"     if s == "OK"        else "🔴 OFF"    if s == "NOT_FOUND" else "⚠️ ERR"
                st.markdown(
                    f"<div class='sys-row'>"
                    f"<span style='font-size:0.85rem'><b>{get_system_name(key)}</b></span>"
                    f"<span class='{bc}'>{bt}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── Trigger Comparison ────────────────────────────────────────────────────
    run_codes    = None
    force_branch = False

    if st.session_state.get("pdf_codes"):
        run_codes    = st.session_state.pdf_codes
        force_branch = st.session_state.get("pdf_mode", "total") == "branch"
        show_branch  = True
        st.session_state.pdf_codes = None
        st.session_state.pdf_mode  = "total"
    elif compare_btn:
        run_codes = codes

    if run_codes is not None:
        if not run_codes:
            st.warning(t("Enter at least one model code.", "أدخل رمزاً واحداً على الأقل."))
            st.stop()

        exact     = st.session_state.search_exact
        run_codes = list(dict.fromkeys([c.strip() for c in run_codes if c.strip()]))[:30]

        total_parts    = []
        branch_parts   = []
        transfer_parts = []
        reorder_parts  = []

        sys_col   = t("System", "النظام")
        new_stats = {k: "NOT_FOUND" for k in SYSTEM_KEYS}
        bar       = st.progress(0, text=t("Fetching data…", "جلب البيانات…"))

        def _process(code):
            r = {
                "code":     code,
                "total":    fetch_total_stock(code, exact=exact),
                "branch":   None,
                "transfer": None,
                "reorder":  None,
            }
            if show_branch or force_branch:
                r["branch"]   = fetch_branch_stock(code, exact=exact)
            if show_transfers:
                r["transfer"] = fetch_transfers(code, exact=exact)
            if show_reorder:
                r["reorder"]  = fetch_reorder(
                    code, exact=exact,
                    reorder_mode=st.session_state.reorder_mode,
                    target_days=st.session_state.reorder_target_days,
                    max_level=st.session_state.reorder_max_level,
                    reorder_point=st.session_state.reorder_point,
                )
            return r

        done = 0
        with ThreadPoolExecutor(max_workers=min(8, len(run_codes))) as ex:
            futures = {ex.submit(_process, c): c for c in run_codes}
            for fut in as_completed(futures):
                res = fut.result()
                tf  = res["total"]
                total_parts.append(tf)
                if "_status" in tf.columns and sys_col in tf.columns:
                    for key in SYSTEM_KEYS:
                        nm   = get_system_name(key)
                        mask = tf[sys_col] == nm
                        if mask.any():
                            sv = tf.loc[mask, "_status"]
                            if "OK"    in sv.values: new_stats[key] = "OK"
                            elif "ERROR" in sv.values and new_stats[key] != "OK":
                                new_stats[key] = "ERROR"
                if res["branch"]   is not None: branch_parts.append(res["branch"])
                if res["transfer"] is not None: transfer_parts.append(res["transfer"])
                if res["reorder"]  is not None: reorder_parts.append(res["reorder"])
                done += 1
                bar.progress(
                    done / len(run_codes),
                    text=f"{t('Processed', 'تمت معالجة')} {done}/{len(run_codes)}",
                )
        bar.empty()

        total_df    = pd.concat(total_parts,    ignore_index=True) if total_parts    else pd.DataFrame()
        branch_df   = pd.concat(branch_parts,   ignore_index=True) if branch_parts   else pd.DataFrame()
        transfer_df = pd.concat(transfer_parts, ignore_index=True) if transfer_parts else pd.DataFrame()
        reorder_df  = pd.concat(reorder_parts,  ignore_index=True) if reorder_parts  else pd.DataFrame()

        qty_col = t("On Hand", "متوفر")
        if not show_zero and qty_col in total_df.columns:
            total_df = total_df[total_df[qty_col] != 0].reset_index(drop=True)
        if sort_sys and sys_col in total_df.columns:
            total_df = total_df.sort_values(sys_col).reset_index(drop=True)
        if not branch_df.empty and sort_sys and sys_col in branch_df.columns:
            branch_df = branch_df.sort_values(sys_col).reset_index(drop=True)

        st.session_state.total_df       = total_df
        st.session_state.branch_df      = branch_df
        st.session_state.transfers_df   = transfer_df
        st.session_state.reorder_df     = reorder_df
        st.session_state.show_transfers = show_transfers
        st.session_state.show_reorder   = show_reorder
        st.session_state.sys_stats      = new_stats
        st.session_state.last_run       = {
            "time":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "models": len(run_codes),
            "rows":   len(total_df),
        }
        record_price_snapshot(total_df)
        st.rerun()

    # ── Show Results ──────────────────────────────────────────────────────────
    total_df    = st.session_state.total_df
    branch_df   = st.session_state.branch_df
    transfer_df = st.session_state.transfers_df
    reorder_df  = st.session_state.reorder_df

    if total_df is None or total_df.empty:
        return

    st.divider()
    thresh   = st.session_state.low_stock_thresh
    qty_col  = t("On Hand",    "متوفر")
    pc_col   = t("Sale Price", "سعر البيع")
    sys_col  = t("System",     "النظام")
    stats    = st.session_state.sys_stats
    online   = sum(1 for v in stats.values() if v == "OK")
    ok_rows  = total_df[total_df["_status"] == "OK"] if "_status" in total_df.columns else total_df

    # Low stock alert banner
    if thresh > 0 and qty_col in ok_rows.columns:
        low = ok_rows[(ok_rows[qty_col] > 0) & (ok_rows[qty_col] <= thresh)]
        if not low.empty:
            mc      = t("Model Code", "رمز الموديل")
            details = ", ".join(
                f"{r.get(mc,'?')} @ {r.get(sys_col,'?')} ({r.get(qty_col,0)})"
                for _, r in low.head(8).iterrows()
            )
            if len(low) > 8:
                details += f" +{len(low)-8} {t('more','أخرى')}"
            st.markdown(
                f"<div class='alert-banner'>🔴 <b>{t('Low Stock Alert','تنبيه مخزون منخفض')}:</b> "
                f"{len(low)} {t('variants','متغيرات')} ≤ {thresh} — "
                f"<span class='mono'>{details}</span></div>",
                unsafe_allow_html=True,
            )

    # KPIs
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(t("Total Rows",     "إجمالي الصفوف"),   len(total_df))
    m2.metric(t("Systems Online", "الأنظمة"),          f"{online}/4")
    if qty_col in ok_rows.columns:
        m3.metric(t("Total Qty", "إجمالي الكمية"), int(ok_rows[qty_col].sum()))
    if pc_col in ok_rows.columns:
        valid = ok_rows[ok_rows[pc_col] > 0][pc_col]
        m4.metric(
            t("Avg Price", "متوسط السعر"),
            f"{valid.mean():.2f} SAR" if not valid.empty else "—",
        )

    # Tabs
    has_branch    = branch_df   is not None and not branch_df.empty
    has_transfers = st.session_state.show_transfers and transfer_df is not None and not transfer_df.empty
    has_reorder   = st.session_state.show_reorder   and reorder_df  is not None and not reorder_df.empty

    tab_labels = [
        f"📦 {t('Total Stock',   'المخزون الإجمالي')}",
        f"📊 {t('Price History', 'تاريخ الأسعار')}",
    ]
    if has_branch:    tab_labels.append(f"🗺️ {t('Branch Stock', 'مخزون الفروع')}")
    if has_transfers: tab_labels.append(f"🚚 {t('Transfers',    'النقليات')}")
    if has_reorder:   tab_labels.append(f"📦 {t('Reorder',      'إعادة الطلب')}")

    tabs = st.tabs(tab_labels)
    ti   = 0

    # ── Tab 1 : Total Stock ───────────────────────────────────────────────────
    with tabs[ti]:
        ti += 1
        st.markdown(f"### 📦 {t('Total Stock View', 'عرض المخزون الإجمالي')}")
        display_df(total_df, thresh)
        d1, d2, d3, _ = st.columns([1, 1, 1, 1])
        d1.download_button(
            f"⬇️ CSV",  to_csv(total_df),
            dl_name("total","csv"),  "text/csv", use_container_width=True,
        )
        d2.download_button(
            f"⬇️ Excel", to_excel(total_df),
            dl_name("total","xlsx"),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        d3.download_button(
            f"📥 Bulk", to_excel_bulk(total_df),
            dl_name("bulk","xlsx"),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    # ── Tab 2 : Price History ─────────────────────────────────────────────────
    with tabs[ti]:
        ti += 1
        st.markdown(f"### 📈 {t('Price History', 'تاريخ الأسعار')}")
        hist_df = build_price_history_df()
        if hist_df.empty:
            st.info(t(
                "Run multiple comparisons to track price changes.",
                "قم بتشغيل مقارنات متعددة لتتبع الأسعار.",
            ))
        else:
            st.line_chart(hist_df, use_container_width=True)
            if st.button(f"🗑️ {t('Clear history', 'مسح التاريخ')}"):
                st.session_state.price_history = {}
                st.rerun()

    # ── Tab 3 : Branch Stock ──────────────────────────────────────────────────
    if has_branch:
        with tabs[ti]:
            ti += 1
            st.markdown(f"### 🗺️ {t('Branch-wise Stock', 'مخزون حسب الفرع')}")
            display_df(branch_df, thresh)
            bc    = t("Branch", "الفرع")
            ok_b  = branch_df[branch_df["_status"] == "OK"] if "_status" in branch_df.columns else branch_df
            if not ok_b.empty and bc in ok_b.columns and qty_col in ok_b.columns:
                chart = ok_b.groupby([sys_col, bc])[qty_col].sum().reset_index()
                if not chart.empty:
                    st.markdown(f"#### 📊 {t('Qty by Branch', 'الكميات حسب الفرع')}")
                    st.bar_chart(chart.set_index(bc)[qty_col], use_container_width=True)
            b1, b2, _ = st.columns([1, 1, 2])
            b1.download_button(
                f"⬇️ CSV",  to_csv(branch_df),
                dl_name("branch","csv"),  "text/csv", use_container_width=True,
            )
            b2.download_button(
                f"⬇️ Excel", to_excel(branch_df),
                dl_name("branch","xlsx"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    # ── Tab 4 : Transfers ─────────────────────────────────────────────────────
    if has_transfers:
        with tabs[ti]:
            ti += 1
            st.markdown(f"### 🚚 {t('Pending Transfers', 'النقليات المعلقة')}")
            st.markdown(
                "<div class='info-banner'>"
                "Shows draft, waiting, confirmed, and ready transfers."
                "</div>",
                unsafe_allow_html=True,
            )
            ok_t = transfer_df[transfer_df["_status"] == "OK"] if "_status" in transfer_df.columns else transfer_df
            if not ok_t.empty:
                k1, k2, k3 = st.columns(3)
                k1.metric(t("Total", "إجمالي"), len(ok_t))
                qd = t("Qty", "الكمية")
                if qd in ok_t.columns:
                    k2.metric(t("Total Qty", "إجمالي الكمية"), int(ok_t[qd].sum()))
                if sys_col in ok_t.columns:
                    k3.metric(t("Systems", "الأنظمة"), ok_t[sys_col].nunique())
            display_df(transfer_df)
            x1, x2, _ = st.columns([1, 1, 2])
            x1.download_button(
                f"⬇️ CSV",  to_csv(transfer_df),
                dl_name("transfers","csv"),  "text/csv", use_container_width=True,
            )
            x2.download_button(
                f"⬇️ Excel", to_excel(transfer_df),
                dl_name("transfers","xlsx"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    # ── Tab 5 : Reorder ───────────────────────────────────────────────────────
    if has_reorder:
        with tabs[ti]:
            CPRI  = t("Priority", "الأولوية")
            CSUGG = t("Suggest",  "المقترح")
            st.markdown(f"### 📦 {t('Reorder Suggestions', 'اقتراحات إعادة الطلب')}")
            ok_r = reorder_df[reorder_df["_status"] == "OK"] if "_status" in reorder_df.columns else reorder_df
            if not ok_r.empty:
                crit = ok_r[ok_r[CPRI].str.startswith("🔴")].shape[0] if CPRI in ok_r.columns else 0
                low  = ok_r[ok_r[CPRI].str.startswith("🟡")].shape[0] if CPRI in ok_r.columns else 0
                okn  = ok_r[ok_r[CPRI].str.startswith("🟢")].shape[0] if CPRI in ok_r.columns else 0
                sugg = int(ok_r[CSUGG].sum())                          if CSUGG in ok_r.columns else 0
                r1, r2, r3, r4 = st.columns(4)
                r1.metric(t("🔴 Critical", "🔴 حرج"),    crit)
                r2.metric(t("🟡 Low",      "🟡 منخفض"),  low)
                r3.metric(t("🟢 OK",       "🟢 كافٍ"),   okn)
                r4.metric(t("To Order",    "للطلب"),      sugg)
                if crit + low > 0:
                    st.markdown(
                        f"<div class='alert-banner'>"
                        f"🔴 {crit+low} {t('products need reordering','منتجات تحتاج إعادة طلب')}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                show_all = st.toggle(t("Show all (incl. OK)", "عرض الكل"), value=False)
                disp_r   = (
                    ok_r if show_all
                    else ok_r[ok_r[CPRI].str.startswith(("🔴", "🟡"))]
                    if CPRI in ok_r.columns else ok_r
                )
                def _style_r(row):
                    p = str(row.get(CPRI, ""))
                    if p.startswith("🔴"): return ["background-color:#fff1f2"] * len(row)
                    if p.startswith("🟡"): return ["background-color:#fffbeb"] * len(row)
                    return [""] * len(row)
                st.dataframe(
                    disp_r.drop(columns=["_status"], errors="ignore").style.apply(_style_r, axis=1),
                    use_container_width=True, hide_index=True,
                )
            else:
                st.info(t("No reorder data.", "لا بيانات إعادة طلب."))
            o1, o2, _ = st.columns([1, 1, 2])
            o1.download_button(
                f"⬇️ CSV",  to_csv(reorder_df),
                dl_name("reorder","csv"),  "text/csv", use_container_width=True,
            )
            o2.download_button(
                f"⬇️ Excel", to_excel(reorder_df),
                dl_name("reorder","xlsx"),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.authenticated:
    show_login()
else:
    show_dashboard()
