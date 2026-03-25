"""

SWAG Product Comparison Dashboard
Real-time Stock & Price Comparison across 4 Odoo Systems
Version 4.0 — with Low Stock Alerts, Price History, Bulk Export, Transfers Tab, Reorder Suggestions
"""

import io
import json
import re
import xmlrpc.client
from datetime import datetime, timedelta

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
.badge-ok  { background:#d1fae5; color:#065f46; border-radius:4px; padding:2px 8px; font-size:0.76rem; font-weight:700; }
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
# DOWNLOAD HELPERS
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
    """Export one sheet per system into a single Excel workbook."""
    buf = io.BytesIO()
    sys_col = t("System", "النظام")
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # Summary sheet — all systems
        summary = total_df.drop(columns=["_status"], errors="ignore")
        summary.to_excel(writer, index=False, sheet_name=t("All Systems", "كل الأنظمة"))
        # Per-system sheets
        if sys_col in total_df.columns:
            for key in SYSTEM_KEYS:
                name = get_system_name(key)
                subset = total_df[total_df[sys_col] == name].drop(columns=["_status"], errors="ignore")
                if not subset.empty:
                    sheet_name = name[:31]   # Excel sheet name max 31 chars
                    subset.to_excel(writer, index=False, sheet_name=sheet_name)
    return buf.getvalue()


def dl_filename(tag: str, ext: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    return f"swag_comparison_{tag}_{ts}.{ext}"


# ─────────────────────────────────────────────────────────────────────────────
# XML-RPC HELPERS
# ─────────────────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
# PDF INVOICE PARSING — FIX #1: Extract ONLY from Model Number column
# ─────────────────────────────────────────────────────────────────────────────

def extract_base_model(code: str) -> str:
    """Remove size suffixes and parenthetical content to get the base model code."""
    # Remove (parentheses) content
    code = re.sub(r'\([^)]*\)', '', code)

    # Remove size suffixes (at end only), longest first
    sizes = ['-2XL', '-3XL', '-XXL', '-XL', '-L', '-M', '-S', '-XS']
    for size in sizes:
        if code.upper().endswith(size):
            code = code[:-len(size)]
            break

    return code.strip()


def parse_invoice_pdf(uploaded_file) -> list:
    """
    Parse a Swag invoice PDF and extract product model codes.
    Extracts ONLY from the Model Number column (2nd column) to avoid duplicates
    from the Product Description column which repeats the code.
    Returns a list of unique extracted codes.
    """
    import re
    try:
        from pypdf import PdfReader
    except ImportError:
        st.error("pypdf is required. Add `pypdf>=3.0.0` to requirements.txt.")
        return []

    pdf_bytes = uploaded_file.read()
    reader = PdfReader(io.BytesIO(pdf_bytes))

    all_text = ""
    for page in reader.pages:
        all_text += (page.extract_text() or "") + "\n"

    if not all_text.strip():
        return []

    codes = []
    lines = all_text.split('\n')

    for line in lines:
        # Skip headers/footers
        if any(w in line.upper() for w in ['MODEL NUMBER', 'TOTAL', 'PAGE', 'SWAG TRADING']):
            continue

        # Pattern: line starts with a row number, then the model code (2nd column only)
        # e.g. "1  TS90-2-S     - TS90-2-S  20.00  12.00 SR"
        #       ^  ^^^^^^^^^  <- Extract this (Model Number column) only
        match = re.search(r'^\s*\d+\s+([A-Z]{2,6}\d+(?:-\d+)?(?:-[A-Z0-9]{1,6})?)\s', line)

        if match:
            code = match.group(1).strip()
            if len(code) >= 4 and any(c.isalpha() for c in code) and any(c.isdigit() for c in code):
                codes.append(code)

    return list(dict.fromkeys(codes))  # Remove duplicates while preserving order


# ─────────────────────────────────────────────────────────────────────────────
# FETCH: TOTAL STOCK — with VARIANT SUPPORT
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def fetch_total_stock(model_code: str, exact: bool = False) -> pd.DataFrame:
    COL_SYS   = t("System",     "النظام")
    COL_MOD   = t("Model Code", "رمز الموديل")
    COL_PROD  = t("Product",    "المنتج")
    COL_PRICE = t("Sale Price", "سعر البيع")
    COL_QTY   = t("On Hand",   "متوفر")

    operator = "=" if exact else "=like"
    pattern  = model_code if exact else f"{model_code}%"

    rows = []
    for key in SYSTEM_KEYS:
        cfg      = secrets.get(key)
        sys_name = get_system_name(key)

        if not cfg:
            rows.append({COL_SYS: sys_name, COL_MOD: model_code,
                         COL_PROD: "—", COL_PRICE: 0.0, COL_QTY: 0,
                         "_status": "ERROR"})
            continue

        uid = _authenticate(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
        if not uid:
            rows.append({COL_SYS: sys_name, COL_MOD: model_code,
                         COL_PROD: t("⚠️ Auth failed", "⚠️ فشل التحقق"),
                         COL_PRICE: 0.0, COL_QTY: 0, "_status": "ERROR"})
            continue

        try:
            prods = _exec(
                cfg["url"], cfg["db"], uid, cfg["api_key"],
                "product.product", "search_read",
                [[["default_code", operator, pattern]]],
                {"fields": ["id", "display_name", "default_code",
                            "qty_available", "list_price"]},
            )

            if not prods:
                rows.append({COL_SYS: sys_name, COL_MOD: model_code,
                             COL_PROD: t("Not found", "غير موجود"),
                             COL_PRICE: 0.0, COL_QTY: 0,
                             "_status": "NOT_FOUND"})
            else:
                for p in prods:
                    rows.append({
                        COL_SYS:   sys_name,
                        COL_MOD:   p.get("default_code") or model_code,
                        COL_PROD:  p.get("display_name") or "",
                        COL_PRICE: float(p.get("list_price") or 0),
                        COL_QTY:   int(p.get("qty_available") or 0),
                        "_status": "OK",
                    })
        except Exception as e:
            rows.append({COL_SYS: sys_name, COL_MOD: model_code,
                         COL_PROD: f"❌ {e}", COL_PRICE: 0.0, COL_QTY: 0,
                         "_status": "ERROR"})

    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=[COL_SYS, COL_MOD, COL_PROD, COL_PRICE, COL_QTY, "_status"])


# ─────────────────────────────────────────────────────────────────────────────
# FETCH: BRANCH STOCK — with VARIANT SUPPORT
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def fetch_branch_stock(model_code: str, exact: bool = False) -> pd.DataFrame:
    COL_QUERY  = t("Query",     "البحث")
    COL_SYS    = t("System",    "النظام")
    COL_BRANCH = t("Branch",    "الفرع")
    COL_LOC    = t("Location",  "الموقع")
    COL_PRICE  = t("Sale Price","سعر البيع")
    COL_QTY    = t("On Hand",   "متوفر")
    COL_MOD    = t("Model Code","رمز الموديل")

    operator = "=" if exact else "=like"
    pattern  = model_code if exact else f"{model_code}%"

    rows = []
    for key in SYSTEM_KEYS:
        cfg      = secrets.get(key)
        sys_name = get_system_name(key)

        if not cfg:
            continue

        uid = _authenticate(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
        if not uid:
            rows.append({
                COL_QUERY: model_code, COL_SYS: sys_name,
                COL_BRANCH: t("⚠️ Auth failed", "⚠️ فشل التحقق"),
                COL_MOD: "—", COL_LOC: "—", COL_PRICE: 0.0, COL_QTY: 0,
                "_status": "ERROR",
            })
            continue

        try:
            prods = _exec(
                cfg["url"], cfg["db"], uid, cfg["api_key"],
                "product.product", "search_read",
                [[["default_code", operator, pattern]]],
                {"fields": ["id", "default_code", "list_price"]},
            )

            if not prods:
                rows.append({
                    COL_QUERY: model_code, COL_SYS: sys_name,
                    COL_BRANCH: t("Not found", "غير موجود"),
                    COL_MOD: "—", COL_LOC: "—", COL_PRICE: 0.0, COL_QTY: 0,
                    "_status": "NOT_FOUND",
                })
                continue

            for prod in prods:
                prod_id    = prod["id"]
                sale_price = float(prod.get("list_price") or 0)
                prod_code  = prod.get("default_code") or model_code

                quants = _exec(
                    cfg["url"], cfg["db"], uid, cfg["api_key"],
                    "stock.quant", "search_read",
                    [[["product_id", "=", prod_id],
                      ["quantity",   ">", 0]]],
                    {"fields": ["location_id", "quantity"]},
                )

                if not quants:
                    rows.append({
                        COL_QUERY:  model_code,
                        COL_SYS:    sys_name,
                        COL_BRANCH: t("No stock", "لا مخزون"),
                        COL_MOD:    prod_code,
                        COL_LOC:    "—",
                        COL_PRICE:  sale_price,
                        COL_QTY:    0,
                        "_status":  "OK",
                    })
                else:
                    for q in quants:
                        loc_raw  = q.get("location_id") or [None, "—"]
                        loc_name = loc_raw[1] if isinstance(loc_raw, list) else str(loc_raw)
                        branch   = loc_name.split("/")[0].strip()
                        rows.append({
                            COL_QUERY:  model_code,
                            COL_SYS:    sys_name,
                            COL_BRANCH: branch,
                            COL_MOD:    prod_code,
                            COL_LOC:    loc_name,
                            COL_PRICE:  sale_price,
                            COL_QTY:    int(q.get("quantity") or 0),
                            "_status":  "OK",
                        })

        except Exception as e:
            rows.append({
                COL_QUERY: model_code, COL_SYS: sys_name,
                COL_BRANCH: f"❌ {e}", COL_MOD: "—", COL_LOC: "—",
                COL_PRICE: 0.0, COL_QTY: 0, "_status": "ERROR",
            })

    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=[COL_QUERY, COL_SYS, COL_BRANCH,
                 COL_MOD, COL_LOC, COL_PRICE, COL_QTY, "_status"])


# ─────────────────────────────────────────────────────────────────────────────
# FETCH: PENDING TRANSFERS (stock.picking)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def fetch_transfers(model_code: str, exact: bool = False) -> pd.DataFrame:
    """
    Fetch pending/ready stock.picking records that contain the searched product.
    States: draft, waiting, confirmed, assigned (i.e. not done/cancelled).
    """
    COL_SYS    = t("System",       "النظام")
    COL_REF    = t("Reference",    "المرجع")
    COL_TYPE   = t("Type",         "النوع")
    COL_STATE  = t("State",        "الحالة")
    COL_FROM   = t("From",         "من")
    COL_TO     = t("To",           "إلى")
    COL_MOD    = t("Model Code",   "رمز الموديل")
    COL_QTY    = t("Qty Demand",   "الكمية المطلوبة")
    COL_DATE   = t("Scheduled",    "المجدول")

    operator = "=" if exact else "=like"
    pattern  = model_code if exact else f"{model_code}%"

    PENDING_STATES = ["draft", "waiting", "confirmed", "assigned"]

    rows = []
    for key in SYSTEM_KEYS:
        cfg      = secrets.get(key)
        sys_name = get_system_name(key)

        if not cfg:
            continue

        uid = _authenticate(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
        if not uid:
            rows.append({
                COL_SYS: sys_name, COL_REF: t("⚠️ Auth failed", "⚠️ فشل التحقق"),
                COL_TYPE: "—", COL_STATE: "—", COL_FROM: "—", COL_TO: "—",
                COL_MOD: "—", COL_QTY: 0, COL_DATE: "—", "_status": "ERROR",
            })
            continue

        try:
            # Step 1: find matching product ids
            prods = _exec(
                cfg["url"], cfg["db"], uid, cfg["api_key"],
                "product.product", "search_read",
                [[["default_code", operator, pattern]]],
                {"fields": ["id", "default_code"]},
            )

            if not prods:
                rows.append({
                    COL_SYS: sys_name, COL_REF: t("Not found", "غير موجود"),
                    COL_TYPE: "—", COL_STATE: "—", COL_FROM: "—", COL_TO: "—",
                    COL_MOD: "—", COL_QTY: 0, COL_DATE: "—", "_status": "NOT_FOUND",
                })
                continue

            prod_ids   = [p["id"] for p in prods]
            prod_codes = {p["id"]: p.get("default_code") or model_code for p in prods}

            # Step 2: find stock.move lines for those products in pending pickings
            moves = _exec(
                cfg["url"], cfg["db"], uid, cfg["api_key"],
                "stock.move", "search_read",
                [[["product_id", "in", prod_ids],
                  ["state", "in", PENDING_STATES]]],
                {"fields": ["picking_id", "product_id",
                            "product_uom_qty", "state"]},
            )

            if not moves:
                rows.append({
                    COL_SYS: sys_name, COL_REF: t("No pending transfers", "لا نقليات معلقة"),
                    COL_TYPE: "—", COL_STATE: "—", COL_FROM: "—", COL_TO: "—",
                    COL_MOD: "—", COL_QTY: 0, COL_DATE: "—", "_status": "OK",
                })
                continue

            # Step 3: fetch picking details for the found pickings
            picking_ids = list({
                m["picking_id"][0]
                for m in moves
                if isinstance(m.get("picking_id"), list)
            })

            if not picking_ids:
                continue

            pickings = _exec(
                cfg["url"], cfg["db"], uid, cfg["api_key"],
                "stock.picking", "search_read",
                [[["id", "in", picking_ids]]],
                {"fields": ["id", "name", "picking_type_id",
                            "state", "location_id",
                            "location_dest_id", "scheduled_date"]},
            )
            picking_map = {p["id"]: p for p in pickings}

            for move in moves:
                pid_raw = move.get("picking_id")
                if not isinstance(pid_raw, list):
                    continue
                pid     = pid_raw[0]
                pick    = picking_map.get(pid, {})
                prod_id = move["product_id"][0] if isinstance(move.get("product_id"), list) else None

                def _name(field):
                    val = pick.get(field)
                    return val[1] if isinstance(val, list) else (val or "—")

                state_raw = pick.get("state", "—")
                state_map = {
                    "draft":     t("Draft",     "مسودة"),
                    "waiting":   t("Waiting",   "انتظار"),
                    "confirmed": t("Confirmed", "مؤكد"),
                    "assigned":  t("Ready",     "جاهز"),
                }
                state_label = state_map.get(state_raw, state_raw)

                sched = pick.get("scheduled_date") or "—"
                if sched != "—":
                    try:
                        sched = datetime.strptime(sched, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
                    except Exception:
                        pass

                rows.append({
                    COL_SYS:   sys_name,
                    COL_REF:   pick.get("name") or "—",
                    COL_TYPE:  _name("picking_type_id"),
                    COL_STATE: state_label,
                    COL_FROM:  _name("location_id"),
                    COL_TO:    _name("location_dest_id"),
                    COL_MOD:   prod_codes.get(prod_id, model_code),
                    COL_QTY:   int(move.get("product_uom_qty") or 0),
                    COL_DATE:  sched,
                    "_status": "OK",
                })

        except Exception as e:
            rows.append({
                COL_SYS: sys_name, COL_REF: f"❌ {e}",
                COL_TYPE: "—", COL_STATE: "—", COL_FROM: "—", COL_TO: "—",
                COL_MOD: "—", COL_QTY: 0, COL_DATE: "—", "_status": "ERROR",
            })

    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=[COL_SYS, COL_REF, COL_TYPE, COL_STATE,
                 COL_FROM, COL_TO, COL_MOD, COL_QTY, COL_DATE, "_status"])


# ─────────────────────────────────────────────────────────────────────────────
# FETCH: SALES VELOCITY (last 30 days) + REORDER SUGGESTIONS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def fetch_reorder_suggestions(
    model_code: str,
    exact: bool = False,
    reorder_mode: str = "days_cover",   # "days_cover" | "max_level"
    target_days: int = 30,
    max_level: int = 100,
    reorder_point: int = 10,
) -> pd.DataFrame:
    """
    For each product variant across all 4 systems:
      1. Fetch current qty_available
      2. Fetch sale.order.line qty from the last 30 days → daily velocity
      3. Calculate suggested reorder qty based on chosen mode
      4. Assign priority: Critical (0 stock), Low (≤ reorder_point), OK

    reorder_mode = "days_cover":
        suggested = max(0, (target_days * daily_velocity) - current_qty)
    reorder_mode = "max_level":
        suggested = max(0, max_level - current_qty)
    """
    VELOCITY_DAYS = 30
    date_from = (datetime.now() - timedelta(days=VELOCITY_DAYS)).strftime("%Y-%m-%d 00:00:00")

    COL_SYS    = t("System",           "النظام")
    COL_MOD    = t("Model Code",       "رمز الموديل")
    COL_PROD   = t("Product",          "المنتج")
    COL_QTY    = t("On Hand",          "متوفر")
    COL_SOLD   = t("Sold (30d)",       "مباع (30 يوم)")
    COL_VEL    = t("Daily Velocity",   "المعدل اليومي")
    COL_DAYS   = t("Days of Stock",    "أيام المخزون")
    COL_SUGG   = t("Suggested Reorder","الكمية المقترحة")
    COL_PRIOR  = t("Priority",         "الأولوية")

    operator = "=" if exact else "=like"
    pattern  = model_code if exact else f"{model_code}%"

    rows = []
    for key in SYSTEM_KEYS:
        cfg      = secrets.get(key)
        sys_name = get_system_name(key)

        if not cfg:
            continue

        uid = _authenticate(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
        if not uid:
            rows.append({
                COL_SYS: sys_name, COL_MOD: model_code,
                COL_PROD: t("⚠️ Auth failed", "⚠️ فشل التحقق"),
                COL_QTY: 0, COL_SOLD: 0, COL_VEL: 0.0,
                COL_DAYS: "—", COL_SUGG: 0, COL_PRIOR: "ERROR",
                "_status": "ERROR",
            })
            continue

        try:
            # Step 1: fetch matching products
            prods = _exec(
                cfg["url"], cfg["db"], uid, cfg["api_key"],
                "product.product", "search_read",
                [[["default_code", operator, pattern]]],
                {"fields": ["id", "display_name", "default_code", "qty_available"]},
            )

            if not prods:
                rows.append({
                    COL_SYS: sys_name, COL_MOD: model_code,
                    COL_PROD: t("Not found", "غير موجود"),
                    COL_QTY: 0, COL_SOLD: 0, COL_VEL: 0.0,
                    COL_DAYS: "—", COL_SUGG: 0, COL_PRIOR: "—",
                    "_status": "NOT_FOUND",
                })
                continue

            for prod in prods:
                prod_id   = prod["id"]
                prod_code = prod.get("default_code") or model_code
                curr_qty  = int(prod.get("qty_available") or 0)

                # Step 2: fetch confirmed/done sale order lines in last 30 days
                sol = _exec(
                    cfg["url"], cfg["db"], uid, cfg["api_key"],
                    "sale.order.line", "search_read",
                    [[["product_id", "=", prod_id],
                      ["order_id.state", "in", ["sale", "done"]],
                      ["order_id.date_order", ">=", date_from]]],
                    {"fields": ["product_uom_qty"]},
                )

                total_sold  = sum(float(l.get("product_uom_qty") or 0) for l in sol)
                daily_vel   = round(total_sold / VELOCITY_DAYS, 2)

                # Step 3: calculate days of stock remaining
                if daily_vel > 0:
                    days_remaining = round(curr_qty / daily_vel, 1)
                    days_label     = str(days_remaining)
                else:
                    days_remaining = None
                    days_label     = t("∞ (no sales)", "∞ (لا مبيعات)")

                # Step 4: suggested reorder quantity
                if reorder_mode == "days_cover":
                    target_stock = target_days * daily_vel
                    suggested    = max(0, round(target_stock - curr_qty))
                else:  # max_level
                    suggested = max(0, max_level - curr_qty)

                # Step 5: priority
                if curr_qty <= 0:
                    priority = t("🔴 Critical", "🔴 حرج")
                elif curr_qty <= reorder_point:
                    priority = t("🟡 Low",      "🟡 منخفض")
                else:
                    priority = t("🟢 OK",       "🟢 كافٍ")

                rows.append({
                    COL_SYS:   sys_name,
                    COL_MOD:   prod_code,
                    COL_PROD:  prod.get("display_name") or "",
                    COL_QTY:   curr_qty,
                    COL_SOLD:  int(total_sold),
                    COL_VEL:   daily_vel,
                    COL_DAYS:  days_label,
                    COL_SUGG:  suggested,
                    COL_PRIOR: priority,
                    "_status": "OK",
                })

        except Exception as e:
            rows.append({
                COL_SYS: sys_name, COL_MOD: model_code,
                COL_PROD: f"❌ {e}",
                COL_QTY: 0, COL_SOLD: 0, COL_VEL: 0.0,
                COL_DAYS: "—", COL_SUGG: 0, COL_PRIOR: "ERROR",
                "_status": "ERROR",
            })

    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=[COL_SYS, COL_MOD, COL_PROD, COL_QTY,
                 COL_SOLD, COL_VEL, COL_DAYS, COL_SUGG, COL_PRIOR, "_status"])


# ─────────────────────────────────────────────────────────────────────────────
# PRICE HISTORY HELPERS (in-memory, session-scoped)
# ─────────────────────────────────────────────────────────────────────────────
def record_price_snapshot(total_df: pd.DataFrame) -> None:
    """Append current prices to session-level price history."""
    price_col = t("Sale Price", "سعر البيع")
    sys_col   = t("System",     "النظام")
    mod_col   = t("Model Code", "رمز الموديل")

    if price_col not in total_df.columns:
        return

    ok = (total_df[total_df["_status"] == "OK"]
          if "_status" in total_df.columns else total_df)
    if ok.empty:
        return

    ts = datetime.now().strftime("%H:%M:%S")
    for _, row in ok.iterrows():
        key = f"{row.get(sys_col,'?')} | {row.get(mod_col,'?')}"
        entry = {"time": ts, "price": float(row.get(price_col, 0))}
        if key not in st.session_state.price_history:
            st.session_state.price_history[key] = []
        st.session_state.price_history[key].append(entry)


def build_price_history_df() -> pd.DataFrame:
    """Flatten price_history dict into a wide DataFrame for charting."""
    hist = st.session_state.price_history
    if not hist:
        return pd.DataFrame()

    # Collect all timestamps in order
    all_times = sorted({e["time"] for entries in hist.values() for e in entries})
    records = []
    for ts in all_times:
        row = {"time": ts}
        for key, entries in hist.items():
            prices_at_ts = [e["price"] for e in entries if e["time"] == ts]
            row[key] = prices_at_ts[-1] if prices_at_ts else None
        records.append(row)
    return pd.DataFrame(records).set_index("time")


# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY DATAFRAME
# ─────────────────────────────────────────────────────────────────────────────
def display_df(df: pd.DataFrame, low_stock_threshold: int = 0) -> None:
    if df is None or df.empty:
        st.info(t("No data to display.", "لا توجد بيانات للعرض."))
        return

    price_col = t("Sale Price", "سعر البيع")
    qty_col   = t("On Hand",   "متوفر")
    show      = df.drop(columns=["_status"], errors="ignore")
    cfg: dict = {}

    if price_col in show.columns:
        cfg[price_col] = st.column_config.NumberColumn(
            price_col, format="%.2f SAR", min_value=0)
    if qty_col in show.columns:
        cfg[qty_col] = st.column_config.NumberColumn(
            qty_col, format="%d", min_value=0)

    # Low stock highlighting — mark rows below threshold
    if low_stock_threshold > 0 and qty_col in show.columns:
        def _highlight_low(row):
            qty = row.get(qty_col, None)
            if qty is not None and isinstance(qty, (int, float)) and 0 < qty <= low_stock_threshold:
                return ["background-color: #fff1f2"] * len(row)
            return [""] * len(row)
        styled = show.style.apply(_highlight_low, axis=1)
        st.dataframe(styled, use_container_width=True,
                     column_config=cfg, hide_index=True)
    else:
        st.dataframe(show, use_container_width=True,
                     column_config=cfg, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE DEFAULTS
# ─────────────────────────────────────────────────────────────────────────────
_DEFAULTS = {
    "authenticated":     False,
    "user_email":        "",
    "lang":              "EN",
    "last_run":          None,
    "total_df":          None,
    "branch_df":         None,
    "transfers_df":      None,
    "sys_stats":         {},
    "search_exact":      False,
    "low_stock_thresh":  5,
    "price_history":     {},   # dict[str, list[{time, price}]]
    "show_transfers":    False,
    "reorder_df":        None,
    "show_reorder":      False,
    "reorder_mode":      "days_cover",
    "reorder_target_days": 30,
    "reorder_max_level":   100,
    "reorder_point":       10,
    "pdf_codes_to_search": None,   # NEW: holds codes extracted from PDF
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN PAGE
# ─────────────────────────────────────────────────────────────────────────────
def show_login() -> None:
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown("## 📊 SWAG Product Comparison")
        st.markdown(
            "<p style='color:#6c757d; margin-top:-10px;'>"
            "Real-time Stock &amp; Price across 4 Odoo Systems</p>",
            unsafe_allow_html=True)
        st.markdown("")

        with st.form("login_form"):
            email    = st.text_input("Email", placeholder="you@swag.com.sa")
            password = st.text_input("Password", type="password")
            submit   = st.form_submit_button("🔐 Sign In", use_container_width=True)

        if submit:
            if not email or not password:
                st.error("Please fill in both fields.")
                return
            try:
                cfg = secrets["LOGIN"]
                uid = _authenticate(cfg["url"], cfg["db"], email, password)
                if uid:
                    st.session_state.authenticated = True
                    st.session_state.user_email    = email
                    st.query_params["auth"] = "1"  # FIX #2: persist session across refresh
                    st.rerun()
                else:
                    st.error("Invalid credentials — please try again.")
            except Exception as e:
                st.error(f"Connection error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD PAGE
# ─────────────────────────────────────────────────────────────────────────────
def show_dashboard() -> None:

    # FIX #2: Restore session if query param exists (survives F5 refresh)
    if st.query_params.get("auth") == "1":
        st.session_state.authenticated = True

    # Check authentication
    if not st.session_state.get("authenticated"):
        st.stop()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"### ⚙️ {t('Settings', 'الإعدادات')}")

        lang_choice = st.radio(
            t("Language", "اللغة"),
            ["EN", "AR"],
            index=0 if get_lang() == "EN" else 1,
            horizontal=True,
        )
        if lang_choice != get_lang():
            st.session_state.lang = lang_choice
            st.rerun()

        st.divider()
        st.markdown(f"👤 `{st.session_state.user_email}`")
        if st.button(f"🚪 {t('Logout','تسجيل الخروج')}", use_container_width=True):
            for k, v in _DEFAULTS.items():
                st.session_state[k] = v
            st.query_params.clear()  # FIX #2: clear auth param on logout
            st.rerun()

        st.divider()

        # ── Search mode ───────────────────────────────────────────────────────
        st.markdown(f"##### 🔬 {t('Search Mode','وضع البحث')}")
        exact_toggle = st.toggle(
            t("Exact match only", "تطابق تام فقط"),
            value=st.session_state.search_exact,
            help=t(
                "OFF = wildcard match (XP6013 → XP6013-S, XP6013-M, XP6013-L …)\n"
                "ON  = exact code match only",
                "إيقاف = بحث بالبادئة\nتشغيل = تطابق تام بالرمز فقط"
            ),
        )
        if exact_toggle != st.session_state.search_exact:
            st.session_state.search_exact = exact_toggle
            st.session_state.total_df  = None
            st.session_state.branch_df = None
            st.session_state.transfers_df = None
            st.rerun()

        mode_label = (
            t("🎯 Exact match", "🎯 تطابق تام")
            if st.session_state.search_exact
            else t("🔍 Variant match (wildcard)", "🔍 مطابقة المتغيرات (بادئة)")
        )
        st.caption(mode_label)

        st.divider()

        # ── Low stock threshold ───────────────────────────────────────────────
        st.markdown(f"##### 🔴 {t('Low Stock Alert','تنبيه المخزون المنخفض')}")
        thresh = st.number_input(
            t("Alert threshold (qty ≤)", "حد التنبيه (الكمية ≤)"),
            min_value=0,
            max_value=1000,
            value=st.session_state.low_stock_thresh,
            step=1,
            help=t(
                "Rows with On Hand qty at or below this value will be highlighted red.",
                "الصفوف التي تساوي أو تقل عن هذه الكمية ستُظلَّل باللون الأحمر."
            ),
        )
        if thresh != st.session_state.low_stock_thresh:
            st.session_state.low_stock_thresh = int(thresh)

        if thresh > 0:
            st.caption(f"🔴 {t('Highlighting qty ≤','تظليل الكمية ≤')} {thresh}")
        else:
            st.caption(t("⚪ Alerts disabled (threshold = 0)", "⚪ التنبيهات معطّلة (الحد = 0)"))

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        f"## 📊 {t('SWAG Product Comparison','مقارنة منتجات سواغ')}")
    st.markdown(
        f"<p style='color:#6c757d; margin-top:-12px;'>"
        f"{t('Real-time stock & price across 4 Odoo systems','المخزون والسعر الفوري عبر 4 أنظمة أودو')}"
        f"</p>", unsafe_allow_html=True)
    st.divider()

    # ═══════════════════════════════════════════════════════════════════════════
    # PDF UPLOAD SECTION — NEW FEATURE
    # ═══════════════════════════════════════════════════════════════════════════
    st.markdown(f"### 📄 {t('Quick Upload: Invoice PDF', 'رفع سريع: PDF الفاتورة')}")

    pdf_col1, pdf_col2 = st.columns([2.5, 1.5])

    with pdf_col1:
        uploaded_pdf = st.file_uploader(
            t("Upload Swag invoice PDF (English or Arabic supported):",
              "ارفع PDF فاتورة سواغ (إنجليزي أو عربي):"),
            type=["pdf"],
            help=t("System will auto-extract all model codes from invoice",
                   "سيستخرج النظام كل رموز الموديل من الفاتورة تلقائيًا"),
            label_visibility="collapsed",
        )

    extract_mode = None
    with pdf_col2:
        if uploaded_pdf:
            extract_mode = st.radio(
                t("Mode:", "الوضع:"),
                [t("Main models", "رئيسي"),
                 t("With sizes", "مع المقاسات")],
                horizontal=True,
            )

    if uploaded_pdf:
        with st.spinner(t("📖 Parsing invoice...", "📖 جاري القراءة...")):
            raw_extracted = parse_invoice_pdf(uploaded_pdf)

        if raw_extracted:
            # Process based on mode
            is_main = (extract_mode is None
                       or "Main" in extract_mode
                       or "رئيسي" in extract_mode)

            if is_main:
                processed = [extract_base_model(c) for c in raw_extracted]
            else:
                processed = raw_extracted

            # Remove duplicates while preserving order
            unique_codes = list(dict.fromkeys(processed))

            # Show summary
            sum_col1, sum_col2 = st.columns(2)
            with sum_col1:
                st.metric(
                    t("Codes Found", "الرموز"),
                    f"{len(raw_extracted)} → {len(unique_codes)}"
                )
            with sum_col2:
                mode_txt = (
                    t("Main models", "موديلات رئيسية")
                    if is_main
                    else t("With sizes", "مع المقاسات")
                )
                st.info(f"📌 {mode_txt}")

            # Show codes in expander
            with st.expander(
                t(f"📋 View {len(unique_codes)} Extracted Codes",
                  f"📋 عرض {len(unique_codes)} رمز"),
                expanded=False,
            ):
                st.code("\n".join(unique_codes))

            # Auto-compare button
            if st.button(
                f"🚀 {t('Compare All in 4 Odoo Systems', 'مقارنة الكل في 4 أنظمة')}",
                type="primary",
                use_container_width=True,
                key="pdf_auto_compare",
            ):
                st.session_state["pdf_codes_to_search"] = unique_codes
                st.rerun()
        else:
            st.warning(t(
                "⚠️ No codes found. Upload a valid Swag invoice PDF.",
                "⚠️ لا رموز. ارفع فاتورة سواغ صحيحة."
            ))

    st.divider()
    st.markdown(f"### ✍️ {t('Or Enter Manually', 'أو أدخل يدويًا')}")
    # ═══════════════════════════════════════════════════════════════════════════
    # END PDF UPLOAD SECTION
    # ═══════════════════════════════════════════════════════════════════════════

    # ── Two-column layout ─────────────────────────────────────────────────────
    left, right = st.columns([1.5, 1])

    with left:
        st.markdown(f"#### 🔍 {t('Search','البحث')}")

        if not st.session_state.search_exact:
            st.markdown(
                f"<div class='info-banner'>"
                f"{'🔍 <b>Variant mode active</b> — entering <span class=\"mono\">XP6013</span> will match '
                   '<span class=\"mono\">XP6013-S</span>, <span class=\"mono\">XP6013-M</span>, '
                   '<span class=\"mono\">XP6013-L</span> and all other variants automatically.'
                   if get_lang() == 'EN' else
                   '🔍 <b>وضع المتغيرات مفعّل</b> — إدخال <span class=\"mono\">XP6013</span> سيجلب '
                   '<span class=\"mono\">XP6013-S</span> و <span class=\"mono\">XP6013-M</span> '
                   'وكل المقاسات تلقائيًا.'}"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='warn-banner'>"
                f"{'🎯 <b>Exact match mode</b> — only products with an identical code will be returned.'
                   if get_lang() == 'EN' else
                   '🎯 <b>وضع التطابق التام</b> — سيتم إرجاع المنتجات ذات الرمز المطابق تمامًا فقط.'}"
                f"</div>",
                unsafe_allow_html=True,
            )

        mode_single = t("Single Model",    "موديل واحد")
        mode_multi  = t("Multiple Models", "موديلات متعددة")
        mode = st.radio(t("Mode","الوضع"), [mode_single, mode_multi],
                        horizontal=True, label_visibility="collapsed")
        is_multi = (mode == mode_multi)

        if is_multi:
            raw = st.text_area(
                t("Model codes (one per line or comma-separated):",
                  "رموز الموديل (سطر لكل رمز أو مفصولة بفاصلة):"),
                height=130,
                placeholder="ABC123\nDEF456, GHI789",
            )
            codes = [c.strip()
                     for c in raw.replace(",", "\n").splitlines()
                     if c.strip()]
        else:
            single = st.text_input(
                t("Model Code:", "رمز الموديل:"),
                placeholder=t("e.g. XP6013  (matches all variants)", "مثال: XP6013  (يجلب كل المقاسات)"))
            codes = [single.strip()] if single.strip() else []

        st.caption(
            t("Use the Internal Reference (default_code), not the product display name.",
              "استخدم المرجع الداخلي (default_code)، وليس اسم المنتج."))

        tc1, tc2, tc3, tc4, tc5 = st.columns(5)
        with tc1:
            show_zero   = st.toggle(t("Show zero qty",  "إظهار الصفري"),   value=False)
        with tc2:
            show_branch = st.toggle(t("Branch details", "تفاصيل الفروع"),  value=False)
        with tc3:
            sort_sys    = st.toggle(t("Sort by system", "ترتيب بالنظام"),  value=False)
        with tc4:
            show_transfers = st.toggle(t("Transfers",   "النقليات"),        value=False)
        with tc5:
            show_reorder   = st.toggle(t("Reorder",     "إعادة الطلب"),     value=False)

        compare_btn = st.button(
            f"🔍 {t('Compare','مقارنة')}",
            use_container_width=True, type="primary")

        # ── Reorder config (shown when toggle is ON) ──────────────────────────
        if show_reorder:
            with st.expander(f"⚙️ {t('Reorder Settings','إعدادات إعادة الطلب')}", expanded=True):
                rc1, rc2 = st.columns(2)
                with rc1:
                    r_mode = st.radio(
                        t("Calculation mode","طريقة الحساب"),
                        [t("Days cover","تغطية أيام"), t("Max level","مستوى أقصى")],
                        horizontal=True,
                        index=0 if st.session_state.reorder_mode == "days_cover" else 1,
                    )
                    st.session_state.reorder_mode = (
                        "days_cover" if r_mode == t("Days cover","تغطية أيام") else "max_level"
                    )
                with rc2:
                    st.session_state.reorder_point = st.number_input(
                        t("Reorder point (flag if qty ≤)","نقطة إعادة الطلب (تنبيه إذا كانت الكمية ≤)"),
                        min_value=0, max_value=9999,
                        value=st.session_state.reorder_point, step=1,
                    )

                if st.session_state.reorder_mode == "days_cover":
                    st.session_state.reorder_target_days = st.slider(
                        t("Target days of stock cover","أيام تغطية المخزون المستهدفة"),
                        min_value=7, max_value=180,
                        value=st.session_state.reorder_target_days, step=1,
                    )
                    st.caption(t(
                        f"Suggested qty = (target days × daily velocity) − current stock",
                        f"الكمية المقترحة = (الأيام المستهدفة × المعدل اليومي) − المخزون الحالي",
                    ))
                else:
                    st.session_state.reorder_max_level = st.number_input(
                        t("Max stock level (target)","مستوى المخزون الأقصى (الهدف)"),
                        min_value=1, max_value=99999,
                        value=st.session_state.reorder_max_level, step=1,
                    )
                    st.caption(t(
                        f"Suggested qty = max level − current stock",
                        f"الكمية المقترحة = المستوى الأقصى − المخزون الحالي",
                    ))

    with right:
        st.markdown(f"#### 📋 {t('Last Run Snapshot','ملخص آخر تشغيل')}")
        snap  = st.session_state.last_run
        stats = st.session_state.sys_stats

        if snap and not all(k in snap for k in ("time", "models", "rows")):
            st.session_state.last_run = None
            snap = None

        if not snap:
            st.info(t("Run a comparison to see results here.",
                      "قم بتشغيل مقارنة لرؤية النتائج هنا."))
        else:
            online     = sum(1 for v in stats.values() if v == "OK")
            match_mode = (t("Exact", "تطابق تام")
                          if snap.get("exact_mode")
                          else t("Variant (wildcard)", "متغيرات (بادئة)"))

            st.markdown(
                f"<div class='snap-card'>"
                f"🕒 <b>{t('Time','الوقت')}:</b> {snap.get('time','—')}<br>"
                f"📦 <b>{t('Models','الموديلات')}:</b> {snap.get('models','—')}<br>"
                f"🌐 <b>{t('Systems online','الأنظمة')}:</b> {online}/4<br>"
                f"📊 <b>{t('Total rows','الصفوف')}:</b> {snap.get('rows','—')}<br>"
                f"🔍 <b>{t('Match mode','وضع البحث')}:</b> {match_mode}"
                f"</div>", unsafe_allow_html=True)
            st.markdown("")

            for key in SYSTEM_KEYS:
                status = stats.get(key, "—")
                badge_cls  = ("badge-ok"  if status == "OK"
                               else "badge-off" if status == "NOT_FOUND"
                               else "badge-err")
                badge_text = ("✅ OK"   if status == "OK"
                               else "🔴 OFF" if status == "NOT_FOUND"
                               else "⚠️ ERR")
                st.markdown(
                    f"<div class='sys-row'>"
                    f"<span style='font-size:0.85rem'><b>{get_system_name(key)}</b></span>"
                    f"<span class='{badge_cls}'>{badge_text}</span>"
                    f"</div>", unsafe_allow_html=True)

    # ── Run comparison ────────────────────────────────────────────────────────
    if compare_btn or st.session_state.get("pdf_codes_to_search"):

        # Use PDF codes if available, otherwise use manual input
        if st.session_state.get("pdf_codes_to_search"):
            codes = st.session_state["pdf_codes_to_search"]
            st.session_state["pdf_codes_to_search"] = None  # Clear after use
        # else: codes already set from the manual input section above

        if not codes:
            st.warning(t("Please enter at least one model code or upload a PDF.",
                          "الرجاء إدخال رمز موديل واحد على الأقل أو رفع PDF."))
            st.stop()

        exact          = st.session_state.search_exact
        total_parts    = []
        branch_parts   = []
        transfer_parts = []
        reorder_parts  = []
        new_stats      = {k: "NOT_FOUND" for k in SYSTEM_KEYS}
        sys_col        = t("System", "النظام")
        qty_col        = t("On Hand","متوفر")

        bar = st.progress(0, text=t("Fetching data…","جلب البيانات…"))

        for i, code in enumerate(codes):
            tf = fetch_total_stock(code, exact=exact)
            total_parts.append(tf)

            if show_branch:
                bf = fetch_branch_stock(code, exact=exact)
                branch_parts.append(bf)

            if show_transfers:
                xf = fetch_transfers(code, exact=exact)
                transfer_parts.append(xf)

            if show_reorder:
                rf = fetch_reorder_suggestions(
                    code,
                    exact=exact,
                    reorder_mode=st.session_state.reorder_mode,
                    target_days=st.session_state.reorder_target_days,
                    max_level=st.session_state.reorder_max_level,
                    reorder_point=st.session_state.reorder_point,
                )
                reorder_parts.append(rf)

            if "_status" in tf.columns and sys_col in tf.columns:
                for key in SYSTEM_KEYS:
                    name = get_system_name(key)
                    mask = tf[sys_col] == name
                    if mask.any():
                        row_st = tf.loc[mask, "_status"].iloc[0]
                        if row_st == "OK":
                            new_stats[key] = "OK"
                        elif row_st == "ERROR" and new_stats[key] != "OK":
                            new_stats[key] = "ERROR"

            bar.progress(
                (i + 1) / len(codes),
                text=f"{t('Processed','تمت معالجة')} {i+1}/{len(codes)}")

        bar.empty()

        total_df    = pd.concat(total_parts,    ignore_index=True) if total_parts    else pd.DataFrame()
        branch_df   = pd.concat(branch_parts,   ignore_index=True) if branch_parts   else pd.DataFrame()
        transfer_df = pd.concat(transfer_parts, ignore_index=True) if transfer_parts else pd.DataFrame()
        reorder_df  = pd.concat(reorder_parts,  ignore_index=True) if reorder_parts  else pd.DataFrame()

        # Apply show-zero filter
        if not show_zero and qty_col in total_df.columns:
            total_df = total_df[total_df[qty_col] != 0].reset_index(drop=True)
        if show_branch and not show_zero and qty_col in branch_df.columns:
            branch_df = branch_df[branch_df[qty_col] > 0].reset_index(drop=True)

        # Apply sort
        if sort_sys and sys_col in total_df.columns:
            total_df = total_df.sort_values(sys_col).reset_index(drop=True)
        if show_branch and sort_sys and sys_col in branch_df.columns:
            branch_df = branch_df.sort_values(sys_col).reset_index(drop=True)

        st.session_state.total_df      = total_df
        st.session_state.branch_df     = branch_df
        st.session_state.transfers_df  = transfer_df
        st.session_state.reorder_df    = reorder_df
        st.session_state.show_transfers = show_transfers
        st.session_state.show_reorder   = show_reorder
        st.session_state.sys_stats    = new_stats
        st.session_state.last_run     = {
            "time":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "models":     len(codes),
            "rows":       len(total_df),
            "exact_mode": exact,
        }

        # Record price snapshot for history
        record_price_snapshot(total_df)

        st.rerun()

    # ── Display results ───────────────────────────────────────────────────────
    total_df    = st.session_state.total_df
    branch_df   = st.session_state.branch_df
    transfer_df = st.session_state.transfers_df
    reorder_df  = st.session_state.reorder_df

    if total_df is None or total_df.empty:
        return

    st.divider()

    qty_col   = t("On Hand",   "متوفر")
    price_col = t("Sale Price","سعر البيع")
    stats     = st.session_state.sys_stats
    online    = sum(1 for v in stats.values() if v == "OK")
    thresh    = st.session_state.low_stock_thresh

    # ── Low stock alert banner ────────────────────────────────────────────────
    if thresh > 0 and "_status" in total_df.columns and qty_col in total_df.columns:
        ok_rows_all = total_df[total_df["_status"] == "OK"]
        low_mask    = (ok_rows_all[qty_col] > 0) & (ok_rows_all[qty_col] <= thresh)
        low_count   = low_mask.sum()
        if low_count > 0:
            mod_col = t("Model Code","رمز الموديل")
            sys_col = t("System","النظام")
            low_codes = ok_rows_all[low_mask][[sys_col, mod_col, qty_col]].to_dict("records")
            details = ", ".join(
                f"{r.get(mod_col,'?')} @ {r.get(sys_col,'?')} ({r.get(qty_col,0)} {t('pcs','قطعة')})"
                for r in low_codes[:8]
            )
            if low_count > 8:
                details += f" … +{low_count - 8} {t('more','أخرى')}"
            st.markdown(
                f"<div class='alert-banner'>"
                f"🔴 <b>{t('Low Stock Alert','تنبيه مخزون منخفض')}:</b> "
                f"{low_count} {t('variant(s) at or below threshold of','متغيرات عند أو أقل من الحد')} {thresh}. "
                f"<span class='mono'>{details}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ── KPI metrics row ───────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(t("Total Rows",     "إجمالي الصفوف"),   len(total_df))
    m2.metric(t("Systems Online", "الأنظمة المتصلة"), f"{online}/4")

    ok_rows = (total_df[total_df["_status"] == "OK"]
               if "_status" in total_df.columns else total_df)

    if qty_col in ok_rows.columns:
        m3.metric(t("Total Qty","إجمالي الكمية"), int(ok_rows[qty_col].sum()))

    if price_col in ok_rows.columns:
        valid = ok_rows[ok_rows[price_col] > 0][price_col]
        avg   = valid.mean() if not valid.empty else 0.0
        m4.metric(t("Avg Sale Price","متوسط سعر البيع"), f"{avg:,.2f} SAR")

    # ── TABS ──────────────────────────────────────────────────────────────────
    tab_labels = [
        f"📦 {t('Total Stock','المخزون الإجمالي')}",
        f"📊 {t('Price History','تاريخ الأسعار')}",
    ]
    if branch_df is not None and not branch_df.empty:
        tab_labels.append(f"🗺️ {t('Branch Stock','مخزون الفروع')}")
    if st.session_state.show_transfers and transfer_df is not None and not transfer_df.empty:
        tab_labels.append(f"🚚 {t('Transfers','النقليات')}")
    if st.session_state.show_reorder and reorder_df is not None and not reorder_df.empty:
        tab_labels.append(f"📦 {t('Reorder Suggestions','اقتراحات إعادة الطلب')}")

    tabs = st.tabs(tab_labels)
    tab_idx = 0

    # ── Tab 1: Total Stock ────────────────────────────────────────────────────
    with tabs[tab_idx]:
        tab_idx += 1
        st.markdown(f"### 📦 {t('Total Stock View','عرض المخزون الإجمالي')}")
        display_df(total_df, low_stock_threshold=thresh)

        dl1, dl2, dl3, _ = st.columns([1, 1, 1, 1])
        with dl1:
            st.download_button(
                f"⬇️ {t('Download CSV','تحميل CSV')}",
                data=to_csv_arabic(total_df),
                file_name=dl_filename("total", "csv"),
                mime="text/csv",
                use_container_width=True)
        with dl2:
            st.download_button(
                f"⬇️ {t('Download Excel','تحميل Excel')}",
                data=to_excel_arabic(total_df),
                file_name=dl_filename("total", "xlsx"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)
        with dl3:
            st.download_button(
                f"📥 {t('Bulk Export (all systems)','تصدير كامل (كل الأنظمة)')}",
                data=to_excel_bulk(total_df),
                file_name=dl_filename("bulk_all_systems", "xlsx"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                help=t(
                    "One sheet per system + a summary sheet.",
                    "ورقة لكل نظام + ورقة ملخص."
                ),
            )

    # ── Tab 2: Price History ──────────────────────────────────────────────────
    with tabs[tab_idx]:
        tab_idx += 1
        st.markdown(f"### 📈 {t('Price History (this session)','تاريخ الأسعار (هذه الجلسة)')}")

        hist_df = build_price_history_df()
        if hist_df.empty:
            st.info(t(
                "No price history yet. Run multiple comparisons to track price changes over time.",
                "لا يوجد تاريخ أسعار بعد. قم بتشغيل مقارنات متعددة لتتبع تغييرات الأسعار."
            ))
        else:
            if len(hist_df) < 2:
                st.markdown(
                    f"<div class='info-banner'>"
                    f"{'ℹ️ Only one snapshot so far. Run another comparison to see price changes.'
                       if get_lang() == 'EN' else
                       'ℹ️ لقطة واحدة حتى الآن. قم بتشغيل مقارنة أخرى لرؤية التغييرات.'}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            # Price change summary
            if len(hist_df) >= 2:
                first_row = hist_df.iloc[0]
                last_row  = hist_df.iloc[-1]
                changed   = []
                for col in hist_df.columns:
                    f_val = first_row.get(col)
                    l_val = last_row.get(col)
                    if f_val is not None and l_val is not None and f_val != l_val:
                        diff = l_val - f_val
                        pct  = (diff / f_val * 100) if f_val != 0 else 0
                        changed.append((col, f_val, l_val, diff, pct))

                if changed:
                    st.markdown(f"#### 🔄 {t('Price Changes Detected','تغييرات الأسعار المرصودة')}")
                    change_records = []
                    for col, fv, lv, diff, pct in changed:
                        arrow = "⬆️" if diff > 0 else "⬇️"
                        change_records.append({
                            t("Product / System","المنتج / النظام"): col,
                            t("First Price","السعر الأول"): f"{fv:,.2f} SAR",
                            t("Latest Price","أحدث سعر"): f"{lv:,.2f} SAR",
                            t("Change","التغيير"): f"{arrow} {abs(diff):,.2f} SAR ({pct:+.1f}%)",
                        })
                    st.dataframe(pd.DataFrame(change_records), hide_index=True, use_container_width=True)
                else:
                    st.markdown(
                        f"<div class='success-banner'>"
                        f"{'✅ No price changes detected across all runs this session.'
                           if get_lang() == 'EN' else
                           '✅ لم يتم رصد أي تغييرات في الأسعار خلال هذه الجلسة.'}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

            st.markdown(f"#### 📊 {t('Price Over Time','الأسعار عبر الزمن')}")
            st.line_chart(hist_df, use_container_width=True)

            # Raw snapshot table
            with st.expander(t("📋 Raw snapshot data", "📋 بيانات اللقطات الخام")):
                st.dataframe(hist_df.reset_index(), hide_index=True, use_container_width=True)

            if st.button(f"🗑️ {t('Clear price history','مسح تاريخ الأسعار')}", type="secondary"):
                st.session_state.price_history = {}
                st.rerun()

    # ── Tab 3: Branch Stock (conditional) ─────────────────────────────────────
    if branch_df is not None and not branch_df.empty:
        with tabs[tab_idx]:
            tab_idx += 1
            st.markdown(f"### 🗺️ {t('Branch-wise Stock View','عرض مخزون الفروع')}")
            display_df(branch_df, low_stock_threshold=thresh)

            branch_col = t("Branch", "الفرع")
            sys_col    = t("System", "النظام")
            ok_branch  = (branch_df[branch_df["_status"] == "OK"]
                          if "_status" in branch_df.columns else branch_df)

            if (not ok_branch.empty
                    and branch_col in ok_branch.columns
                    and qty_col in ok_branch.columns):
                chart = (ok_branch
                         .groupby([sys_col, branch_col])[qty_col]
                         .sum()
                         .reset_index())
                if not chart.empty:
                    st.markdown(f"#### 📊 {t('Qty by Branch','الكميات حسب الفرع')}")
                    st.bar_chart(chart.set_index(branch_col)[qty_col],
                                 use_container_width=True)

            dl3, dl4, _ = st.columns([1, 1, 2])
            with dl3:
                st.download_button(
                    f"⬇️ {t('Branch CSV','CSV الفروع')}",
                    data=to_csv_arabic(branch_df),
                    file_name=dl_filename("branch", "csv"),
                    mime="text/csv",
                    use_container_width=True)
            with dl4:
                st.download_button(
                    f"⬇️ {t('Branch Excel','Excel الفروع')}",
                    data=to_excel_arabic(branch_df),
                    file_name=dl_filename("branch", "xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True)

    # ── Tab 4: Transfers (conditional) ────────────────────────────────────────
    if st.session_state.show_transfers and transfer_df is not None and not transfer_df.empty:
        with tabs[tab_idx]:
            tab_idx += 1
            st.markdown(f"### 🚚 {t('Pending Transfers','النقليات المعلقة')}")

            st.markdown(
                f"<div class='info-banner'>"
                f"{'ℹ️ Shows <b>draft, waiting, confirmed, and ready</b> stock transfers '
                   'that include the searched product(s). Does not include completed or cancelled transfers.'
                   if get_lang() == 'EN' else
                   'ℹ️ يعرض نقليات المخزون <b>المسودة والمنتظرة والمؤكدة والجاهزة</b> '
                   'التي تتضمن المنتج/المنتجات المبحوثة. لا يشمل النقليات المكتملة أو الملغاة.'}"
                f"</div>",
                unsafe_allow_html=True,
            )

            ok_trans = (transfer_df[transfer_df["_status"] == "OK"]
                        if "_status" in transfer_df.columns else transfer_df)

            if not ok_trans.empty:
                state_col = t("State", "الحالة")
                qty_d_col = t("Qty Demand", "الكمية المطلوبة")
                sys_col   = t("System", "النظام")

                k1, k2, k3 = st.columns(3)
                k1.metric(t("Total Transfers","إجمالي النقليات"), len(ok_trans))
                if qty_d_col in ok_trans.columns:
                    k2.metric(t("Total Qty Demanded","إجمالي الكميات المطلوبة"),
                              int(ok_trans[qty_d_col].sum()))
                if sys_col in ok_trans.columns:
                    k3.metric(t("Systems with Transfers","أنظمة بنقليات"),
                              ok_trans[sys_col].nunique())

            display_df(transfer_df)

            dl5, dl6, _ = st.columns([1, 1, 2])
            with dl5:
                st.download_button(
                    f"⬇️ {t('Transfers CSV','CSV النقليات')}",
                    data=to_csv_arabic(transfer_df),
                    file_name=dl_filename("transfers", "csv"),
                    mime="text/csv",
                    use_container_width=True)
            with dl6:
                st.download_button(
                    f"⬇️ {t('Transfers Excel','Excel النقليات')}",
                    data=to_excel_arabic(transfer_df),
                    file_name=dl_filename("transfers", "xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True)

    # ── Tab 5: Reorder Suggestions (conditional) ──────────────────────────────
    if st.session_state.show_reorder and reorder_df is not None and not reorder_df.empty:
        with tabs[tab_idx]:
            COL_PRIOR  = t("Priority",          "الأولوية")
            COL_SUGG   = t("Suggested Reorder", "الكمية المقترحة")
            COL_QTY    = t("On Hand",           "متوفر")
            COL_SOLD   = t("Sold (30d)",        "مباع (30 يوم)")
            COL_VEL    = t("Daily Velocity",    "المعدل اليومي")
            COL_DAYS   = t("Days of Stock",     "أيام المخزون")
            sys_col    = t("System",            "النظام")

            st.markdown(f"### 📦 {t('Reorder Suggestions','اقتراحات إعادة الطلب')}")

            # Mode reminder banner
            mode_label = (
                t(f"Days cover — target {st.session_state.reorder_target_days} days of stock",
                  f"تغطية أيام — الهدف {st.session_state.reorder_target_days} يومًا من المخزون")
                if st.session_state.reorder_mode == "days_cover"
                else t(f"Max level — target stock level {st.session_state.reorder_max_level} units",
                       f"مستوى أقصى — الهدف {st.session_state.reorder_max_level} وحدة")
            )
            st.markdown(
                f"<div class='info-banner'>"
                f"📐 <b>{t('Calculation mode','طريقة الحساب')}:</b> {mode_label} &nbsp;|&nbsp; "
                f"🔴 {t('Reorder point','نقطة الطلب')}: ≤ {st.session_state.reorder_point} &nbsp;|&nbsp; "
                f"📅 {t('Velocity window','نافذة الحساب')}: {t('Last 30 days','آخر 30 يومًا')}"
                f"</div>",
                unsafe_allow_html=True,
            )

            ok_reorder = (reorder_df[reorder_df["_status"] == "OK"]
                          if "_status" in reorder_df.columns else reorder_df)

            if not ok_reorder.empty:
                # KPI summary
                critical_n = ok_reorder[ok_reorder[COL_PRIOR].str.startswith("🔴")].shape[0] if COL_PRIOR in ok_reorder.columns else 0
                low_n      = ok_reorder[ok_reorder[COL_PRIOR].str.startswith("🟡")].shape[0] if COL_PRIOR in ok_reorder.columns else 0
                ok_n       = ok_reorder[ok_reorder[COL_PRIOR].str.startswith("🟢")].shape[0] if COL_PRIOR in ok_reorder.columns else 0
                total_sugg = int(ok_reorder[COL_SUGG].sum()) if COL_SUGG in ok_reorder.columns else 0

                rk1, rk2, rk3, rk4 = st.columns(4)
                rk1.metric(t("🔴 Critical","🔴 حرج"),       critical_n)
                rk2.metric(t("🟡 Low Stock","🟡 مخزون منخفض"), low_n)
                rk3.metric(t("🟢 OK","🟢 كافٍ"),             ok_n)
                rk4.metric(t("Total Units to Order","إجمالي الوحدات للطلب"), total_sugg)

                # Alert banner for critical/low items
                needs_action = critical_n + low_n
                if needs_action > 0:
                    st.markdown(
                        f"<div class='alert-banner'>"
                        f"🔴 <b>{needs_action} {t('product(s) need reordering','منتجات تحتاج إعادة طلب')}:</b> "
                        f"{critical_n} {t('critical (zero stock)','حرجة (صفر مخزون)')} · "
                        f"{low_n} {t('low (at or below reorder point)','منخفضة (عند أو أقل من نقطة الطلب)')}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<div class='success-banner'>"
                        f"✅ {t('All products are above the reorder point. No immediate action needed.','جميع المنتجات فوق نقطة إعادة الطلب. لا إجراء فوري مطلوب.')}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                # Filter toggle: show only items that need reorder
                show_all_r = st.toggle(
                    t("Show all products (including OK)", "عرض كل المنتجات (بما فيها الكافية)"),
                    value=False,
                )
                display_reorder = ok_reorder if show_all_r else ok_reorder[
                    ok_reorder[COL_PRIOR].str.startswith(("🔴", "🟡"))
                ] if COL_PRIOR in ok_reorder.columns else ok_reorder

                # Style: highlight critical rows
                show_r = display_reorder.drop(columns=["_status"], errors="ignore")

                def _style_reorder(row):
                    p = row.get(COL_PRIOR, "")
                    if str(p).startswith("🔴"):
                        return ["background-color: #fff1f2"] * len(row)
                    if str(p).startswith("🟡"):
                        return ["background-color: #fffbeb"] * len(row)
                    return [""] * len(row)

                r_cfg = {}
                if COL_QTY  in show_r.columns: r_cfg[COL_QTY]  = st.column_config.NumberColumn(COL_QTY,  format="%d")
                if COL_SOLD in show_r.columns: r_cfg[COL_SOLD] = st.column_config.NumberColumn(COL_SOLD, format="%d")
                if COL_VEL  in show_r.columns: r_cfg[COL_VEL]  = st.column_config.NumberColumn(COL_VEL,  format="%.2f")
                if COL_SUGG in show_r.columns: r_cfg[COL_SUGG] = st.column_config.NumberColumn(COL_SUGG, format="%d")

                st.dataframe(
                    show_r.style.apply(_style_reorder, axis=1),
                    use_container_width=True,
                    column_config=r_cfg,
                    hide_index=True,
                )

                # Velocity chart: top 10 fastest-moving
                if COL_VEL in ok_reorder.columns and not ok_reorder[ok_reorder[COL_VEL] > 0].empty:
                    st.markdown(f"#### 🚀 {t('Top 10 Fastest-Moving Products','أسرع 10 منتجات حركةً')}")
                    mod_col = t("Model Code", "رمز الموديل")
                    vel_chart = (
                        ok_reorder[ok_reorder[COL_VEL] > 0]
                        .groupby([sys_col, mod_col])[COL_VEL]
                        .max()
                        .reset_index()
                        .sort_values(COL_VEL, ascending=False)
                        .head(10)
                    )
                    if not vel_chart.empty:
                        vel_chart["label"] = vel_chart[mod_col] + " @ " + vel_chart[sys_col]
                        st.bar_chart(vel_chart.set_index("label")[COL_VEL], use_container_width=True)

            else:
                st.info(t("No reorder data to display.", "لا توجد بيانات إعادة طلب للعرض."))

            # Downloads
            dl7, dl8, _ = st.columns([1, 1, 2])
            with dl7:
                st.download_button(
                    f"⬇️ {t('Reorder CSV','CSV إعادة الطلب')}",
                    data=to_csv_arabic(reorder_df),
                    file_name=dl_filename("reorder", "csv"),
                    mime="text/csv",
                    use_container_width=True)
            with dl8:
                st.download_button(
                    f"⬇️ {t('Reorder Excel','Excel إعادة الطلب')}",
                    data=to_excel_arabic(reorder_df),
                    file_name=dl_filename("reorder", "xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.authenticated:
    show_login()
else:
    show_dashboard()
