"""
SWAG Season Comparison Dashboard
Minimal – Only Season Comparison · Large Dataset Ready
"""

import io
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import xmlrpc.client

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Season Comparison",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# DARK THEME CSS (minimal, premium)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;1,300&family=Outfit:wght@300;400;500;600&display=swap');
* , html , body , [class*="css"] { font-family: 'Outfit', sans-serif; }
.stApp { background: #060d0e !important; }
.block-container { padding-top: 1rem !important; max-width: 100% !important; }

/* SIDEBAR */
section[data-testid="stSidebar"] {
    background: #060d0e !important;
    border-right: 1px solid rgba(74,172,180,0.1) !important;
}
section[data-testid="stSidebar"] * { color: rgba(255,255,255,0.6) !important; }
section[data-testid="stSidebar"] h1, h2, h3 {
    color: #4AACB4 !important;
    font-size: 9px !important;
    letter-spacing: 4px !important;
    text-transform: uppercase !important;
}

/* METRICS */
[data-testid="stMetric"] {
    background: rgba(74,172,180,0.03);
    border: 1px solid rgba(74,172,180,0.08);
    border-radius: 4px;
    padding: 20px 24px;
}
[data-testid="stMetricLabel"] {
    font-size: 8px; letter-spacing: 3px; text-transform: uppercase;
    color: rgba(255,255,255,0.25);
}
[data-testid="stMetricValue"] {
    font-family: 'Cormorant Garamond', serif;
    font-size: 44px; font-weight: 300; color: #fff;
}

/* BUTTONS */
.stButton button {
    font-size: 9px; letter-spacing: 2px; text-transform: uppercase;
    border-radius: 100px !important;
}
.stButton button[kind="primary"] {
    background: #4AACB4 !important; color: #060d0e !important;
    border: none !important; font-weight: 600 !important;
    padding: 10px 28px !important;
}
.stButton button[kind="primary"]:hover {
    background: #2E8A91 !important; transform: translateY(-1px);
}
.stButton button[kind="secondary"] {
    background: transparent !important;
    color: rgba(74,172,180,0.6) !important;
    border: 1px solid rgba(74,172,180,0.2) !important;
}

/* INFO / WARN BANNERS */
.info-banner {
    background: rgba(74,172,180,0.04);
    border-left: 2px solid #4AACB4;
    padding: 10px 16px;
    font-size: 9px; letter-spacing: 1.5px;
    text-transform: uppercase; color: rgba(74,172,180,0.7);
}
.warn-banner {
    background: rgba(212,168,75,0.04);
    border-left: 2px solid #D4A84B;
    padding: 10px 16px;
    font-size: 9px; letter-spacing: 1.5px;
    text-transform: uppercase; color: rgba(212,168,75,0.7);
}
.hero-title {
    font-family: 'Tajawal', sans-serif;
    font-size: 48px; font-weight: 700; color: #fff;
    letter-spacing: -1px; margin-bottom: 0;
}
.hero-title em { color: #4AACB4; font-style: normal; }
.section-tag {
    font-size: 9px; letter-spacing: 4px; text-transform: uppercase;
    color: #4AACB4; margin: 20px 0 12px 0;
    display: flex; align-items: center; gap: 10px;
}
.section-tag::before {
    content: ''; width: 20px; height: 1px; background: #4AACB4;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# CONSTANTS & LANGUAGE
# -----------------------------------------------------------------------------
SYSTEM_KEYS = ["SWAG", "STOCK", "LAROUCHE", "DIFFC", "FASHIONLIMITS"]
SEASON_FIELD_CANDIDATES = [
    "x_studio_season", "season_id", "x_season", "x_studio_season_name"
]

def get_lang():
    return st.session_state.get("lang", "EN")

def t(en, ar):
    return ar if get_lang() == "AR" else en

def get_system_name(key):
    cfg = get_system_config(key) or {}
    return cfg.get("name_ar", cfg.get("name", key)) if get_lang() == "AR" else cfg.get("name", key)

# -----------------------------------------------------------------------------
# SESSION STATE
# -----------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_email = ""
    st.session_state.lang = "EN"

# -----------------------------------------------------------------------------
# SESSION LOGIN RESTORE
# -----------------------------------------------------------------------------
import hashlib
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

# -----------------------------------------------------------------------------
# XML-RPC HELPERS (unchanged from original, exact same logic)
# -----------------------------------------------------------------------------
_KEY_ALIASES = {
    "FASHION_LIMITS": "FASHIONLIMITS",
    "FASHIONLIMITS": "FASHIONLIMITS",
}

def _canonical_key(key: str) -> str:
    return _KEY_ALIASES.get(key, key)

def get_system_config(key: str) -> dict | None:
    canonical = _canonical_key(key)
    cfg = st.secrets.get(canonical) or st.secrets.get(key)
    if not cfg:
        return None
    cfg = dict(cfg)
    url = str(cfg.get("url", "")).rstrip("/")
    if url.endswith("/odoo"):
        url = url[: -len("/odoo")]
    cfg["url"] = url
    return cfg

@st.cache_resource
def _proxy(url, ep):
    return xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/{ep}", allow_none=True)

def _auth(url, db, user, api_key):
    try:
        uid = _proxy(url, "common").authenticate(db, user, api_key, {})
        if uid:
            return {"ok": True, "uid": uid}
        return {"ok": False, "error": "BAD_CREDENTIALS"}
    except Exception as e:
        return {"ok": False, "error": f"AUTH_EXCEPTION: {e}"}

def _x(url, db, uid, key, model, method, domain, kw):
    return _proxy(url, "object").execute_kw(db, uid, key, model, method, domain, kw)

# -----------------------------------------------------------------------------
# SEASON COMPARISON CORE FUNCTIONS
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def detect_season_field(system_key):
    """Return field name on product.template that stores season, or None."""
    cfg = get_system_config(system_key)
    if not cfg:
        return None
    auth_res = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth_res["ok"]:
        return None
    uid = auth_res["uid"]
    try:
        fields = _x(cfg["url"], cfg["db"], uid, cfg["api_key"],
                    "product.template", "fields_get", [], {"attributes": ["string", "type", "relation"]})
        for cand in SEASON_FIELD_CANDIDATES:
            if cand in fields:
                return cand
        # fallback: any field with 'season' in name
        for fname, finfo in fields.items():
            if "season" in fname.lower():
                return fname
        return None
    except Exception:
        return None

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_distinct_seasons(system_key, season_field):
    """Return list of (value, label) for season field on product.template."""
    cfg = get_system_config(system_key)
    if not cfg or not season_field:
        return []
    auth_res = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth_res["ok"]:
        return []
    uid = auth_res["uid"]
    try:
        # read all templates with non-null season field
        templates = _x(cfg["url"], cfg["db"], uid, cfg["api_key"],
                       "product.template", "search_read",
                       [[[season_field, "!=", False]]],
                       {"fields": [season_field], "limit": 5000})
        if not templates:
            return []
        raw_values = set()
        for t in templates:
            val = t.get(season_field)
            if val is False or val is None:
                continue
            raw_values.add(val)
        # convert to label if many2one
        field_info = _x(cfg["url"], cfg["db"], uid, cfg["api_key"],
                        "product.template", "fields_get", [],
                        {"attributes": ["type", "relation"]})
        ftype = field_info.get(season_field, {}).get("type")
        if ftype == "many2one":
            # resolve names
            ids = [v for v in raw_values if isinstance(v, int)]
            if not ids:
                return []
            rel_model = field_info[season_field]["relation"]
            records = _x(cfg["url"], cfg["db"], uid, cfg["api_key"],
                         rel_model, "search_read",
                         [[["id", "in", ids]]],
                         {"fields": ["id", "display_name"], "limit": len(ids)+10})
            name_map = {r["id"]: r.get("display_name", str(r["id"])) for r in records}
            seasons = [(v, name_map.get(v, str(v))) for v in raw_values if isinstance(v, int)]
        else:
            seasons = [(v, str(v)) for v in raw_values]
        return sorted(set(seasons), key=lambda x: x[1])
    except Exception:
        return []

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_season_products(system_key, season_field, season_value, season_label):
    """Fetch all product.product records for a given season value.
       Returns DataFrame with columns: Model Code, Product, Qty, Price, Season.
    """
    cfg = get_system_config(system_key)
    if not cfg or not season_field:
        return pd.DataFrame(columns=["Model Code", "Product", "Qty", "Price", "Season"])
    auth_res = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth_res["ok"]:
        return pd.DataFrame(columns=["Model Code", "Product", "Qty", "Price", "Season"])
    uid = auth_res["uid"]
    try:
        # Step 1: fetch product.template ids with season condition
        domain = [[season_field, "=", season_value]]
        templates = _x(cfg["url"], cfg["db"], uid, cfg["api_key"],
                       "product.template", "search_read",
                       domain, {"fields": ["id"], "limit": 50000})
        if not templates:
            return pd.DataFrame(columns=["Model Code", "Product", "Qty", "Price", "Season"])
        tmpl_ids = [t["id"] for t in templates]
        # Step 2: fetch product.product linked to those templates
        products = _x(cfg["url"], cfg["db"], uid, cfg["api_key"],
                      "product.product", "search_read",
                      [[["product_tmpl_id", "in", tmpl_ids], ["sale_ok", "=", True]]],
                      {"fields": ["default_code", "display_name", "qty_available", "list_price"],
                       "limit": 200000})
        if not products:
            return pd.DataFrame(columns=["Model Code", "Product", "Qty", "Price", "Season"])
        rows = []
        for p in products:
            code = (p.get("default_code") or "").strip()
            if not code:
                continue
            qty = float(p.get("qty_available") or 0)
            price = float(p.get("list_price") or 0)
            rows.append({
                "Model Code": code,
                "Product": p.get("display_name") or "",
                "Qty": qty,
                "Price": price,
                "Season": season_label,
            })
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame(columns=["Model Code", "Product", "Qty", "Price", "Season"])

def build_season_comparison_matrix(selected_season_label, selected_season_value):
    """Parallel fetch for all systems, merge into one matrix.
       Returns DataFrame with columns:
       Model Code, Product, Season,
       SWAG Qty, SWAG Price, STOCK Qty, STOCK Price, ...
       Total Qty
    """
    all_data = {}
    # Pre-detect season field per system (cache)
    season_fields = {}
    for sys in SYSTEM_KEYS:
        sf = detect_season_field(sys)
        if sf:
            season_fields[sys] = sf

    # Fetch products in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for sys in SYSTEM_KEYS:
            if sys not in season_fields:
                continue
            sf = season_fields[sys]
            futures[executor.submit(fetch_season_products, sys, sf, selected_season_value, selected_season_label)] = sys
        for fut in as_completed(futures):
            sys = futures[fut]
            try:
                df = fut.result()
                if not df.empty:
                    all_data[sys] = df
            except Exception:
                pass

    if not all_data:
        return pd.DataFrame()

    # Merge row by model code
    merged = None
    for sys, df in all_data.items():
        # keep only needed columns
        sub = df[["Model Code", "Product", "Qty", "Price"]].copy()
        sub = sub.rename(columns={"Qty": f"{sys} Qty", "Price": f"{sys} Price"})
        if merged is None:
            merged = sub
        else:
            merged = pd.merge(merged, sub, on="Model Code", how="outer")
    if merged is None:
        return pd.DataFrame()

    # Add Total Qty column
    qty_cols = [c for c in merged.columns if c.endswith(" Qty")]
    merged["Total Qty"] = merged[qty_cols].sum(axis=1)

    # Determine Product and Season (use first non-null)
    merged["Product"] = merged[[c for c in merged.columns if c == "Product" and "x" not in c]].bfill(axis=1).iloc[:, 0]
    # Season column is same for all rows (selected label)
    merged["Season"] = selected_season_label

    # Final column order
    base_cols = ["Model Code", "Product", "Season"]
    sys_cols = []
    for sys in SYSTEM_KEYS:
        if f"{sys} Qty" in merged.columns and f"{sys} Price" in merged.columns:
            sys_cols.append(f"{sys} Qty")
            sys_cols.append(f"{sys} Price")
    final_cols = base_cols + sys_cols + ["Total Qty"]
    final_cols = [c for c in final_cols if c in merged.columns]
    merged = merged[final_cols].fillna(0).reset_index(drop=True)

    # Round numeric columns
    for col in merged.columns:
        if "Price" in col:
            merged[col] = merged[col].round(2)
        elif "Qty" in col:
            merged[col] = merged[col].astype(int)

    return merged

# -----------------------------------------------------------------------------
# EXCEL EXPORT (styled)
# -----------------------------------------------------------------------------
def to_excel_season_matrix(df, season_name):
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Season Comparison")
        ws = writer.sheets["Season Comparison"]
        # apply styling
        hdr_fill = PatternFill("solid", fgColor="060D0E")
        hdr_font = Font(bold=True, color="4AACB4", size=11, name="Calibri")
        halign = Alignment(horizontal="center", vertical="center")
        thin = Side(border_style="thin", color="1A2A2C")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        alt_fill = PatternFill("solid", fgColor="0D1A1C")
        norm_font = Font(name="Calibri", size=10, color="8AACB0")
        num_align = Alignment(horizontal="right", vertical="center")
        ctr_align = Alignment(horizontal="center", vertical="center")
        tot_fill = PatternFill("solid", fgColor="060D0E")
        tot_font = Font(bold=True, name="Calibri", color="D4A84B")

        max_row = ws.max_row
        max_col = ws.max_column
        ws.row_dimensions[1].height = 28
        for col_num in range(1, max_col + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = hdr_fill
            cell.font = hdr_font
            cell.alignment = halign
            cell.border = border

        for row in ws.iter_rows(min_row=2, max_row=max_row):
            for cell in row:
                cell.border = border
                cell.font = norm_font
                if cell.row % 2 == 0:
                    cell.fill = alt_fill
                cell.alignment = num_align if isinstance(cell.value, (int, float)) else ctr_align
            ws.row_dimensions[row[0].row].height = 18

        for col_num in range(1, max_col + 1):
            col_letter = get_column_letter(col_num)
            max_len = 0
            for r in range(1, max_row + 1):
                cell_val = ws.cell(row=r, column=col_num).value
                if cell_val:
                    max_len = max(max_len, len(str(cell_val)))
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(max_col)}{max_row}"
        # totals row
        total_row = max_row + 1
        ws.cell(row=total_row, column=1, value="TOTAL")
        ws.cell(row=total_row, column=1).font = tot_font
        ws.cell(row=total_row, column=1).fill = tot_fill
        ws.cell(row=total_row, column=1).alignment = ctr_align

        # sum for each numeric column (Qty and Price columns)
        for col_idx, col_name in enumerate(df.columns, start=1):
            if "Qty" in col_name or "Price" in col_name:
                col_letter = get_column_letter(col_idx)
                ws.cell(row=total_row, column=col_idx,
                        value=f"=SUM({col_letter}2:{col_letter}{max_row})")
                ws.cell(row=total_row, column=col_idx).font = tot_font
                ws.cell(row=total_row, column=col_idx).fill = tot_fill
                ws.cell(row=total_row, column=col_idx).alignment = num_align

        ws.sheet_properties.tabColor = "4AACB4"
        footer_row = total_row + 2
        ws.cell(row=footer_row, column=1,
                value=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Season: {season_name}")
        ws.cell(row=footer_row, column=1).font = Font(italic=True, color="4AACB4", size=9, name="Calibri")
    return buf.getvalue()

# -----------------------------------------------------------------------------
# LOGIN (unchanged from original)
# -----------------------------------------------------------------------------
def show_login():
    st.markdown("""
    <div style='position:fixed; top:16px; right:20px; z-index:9999;'>
    </div>
    """, unsafe_allow_html=True)
    lg = st.radio("", ["EN","AR"], horizontal=True,
                  index=0 if get_lang()=="EN" else 1,
                  label_visibility="collapsed", key="llr")
    if lg != get_lang():
        st.session_state.lang = lg
        st.rerun()

    st.markdown("""
    <div style='display:flex; flex-direction:column; align-items:center; justify-content:center;
                min-height:80vh;'>
      <div style='font-family:"Cormorant Garamond",serif; font-size:52px; color:#fff;
                  letter-spacing:8px; margin-bottom:8px;'>SWAG</div>
      <div style='font-family:Outfit,sans-serif; font-size:9px; letter-spacing:5px;
                  text-transform:uppercase; color:#4AACB4; margin-bottom:32px;'>
        Season Comparison
      </div>
    """, unsafe_allow_html=True)
    with st.form("login_form"):
        email = st.text_input(t("Email", "البريد الإلكتروني"), placeholder="you@company.com")
        password = st.text_input(t("Password", "كلمة المرور"), type="password")
        submit = st.form_submit_button(t("Sign In →", "تسجيل الدخول →"), type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    if submit:
        if not email or not password:
            st.error(t("Fill both fields.", "يرجى ملء جميع الحقول."))
            return
        if "LOGIN" not in st.secrets:
            st.error("Missing LOGIN section in secrets.toml")
            return
        cfg = st.secrets["LOGIN"]
        try:
            login_url = str(cfg.get("url", "")).rstrip("/")
            if login_url.endswith("/odoo"):
                login_url = login_url[:-len("/odoo")]
            proxy = xmlrpc.client.ServerProxy(f"{login_url}/xmlrpc/2/common", allow_none=True)
            uid = proxy.authenticate(cfg["db"], email, password, {})
            if uid:
                token = _make_token(email)
                st.query_params["u"] = email
                st.query_params["t"] = token
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.rerun()
            else:
                st.error(t("Wrong email or password.", "بريد إلكتروني أو كلمة مرور خاطئة."))
        except Exception as e:
            st.error(f"Connection error: {e}")

def do_logout():
    try:
        st.query_params.clear()
    except Exception:
        pass
    st.session_state.authenticated = False
    st.session_state.user_email = ""
    st.rerun()

# -----------------------------------------------------------------------------
# MAIN DASHBOARD – SEASON COMPARISON ONLY
# -----------------------------------------------------------------------------
def show_dashboard():
    # Sidebar: logout + language
    with st.sidebar:
        st.markdown(f"""
        <div style='padding:24px 0 20px;border-bottom:1px solid rgba(74,172,180,0.08);margin-bottom:20px;'>
          <div style='display:flex;align-items:center;gap:10px;'>
            <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
              <path d="M16 2 L28 16 L16 30 L4 16 Z" stroke="#4AACB4" stroke-width="1" fill="rgba(74,172,180,0.04)"/>
              <path d="M16 9 L23 16 L16 23 L9 16 Z" fill="#4AACB4" opacity="0.3"/>
            </svg>
            <div>
              <div style='font-family:Outfit;font-size:13px;font-weight:600;color:#fff;letter-spacing:2px;'>SWAG</div>
              <div style='font-family:Outfit;font-size:7px;letter-spacing:3px;color:#4AACB4;'>Season</div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)
        lc = st.radio(t("Language", "اللغة"), ["EN","AR"], horizontal=True,
                      index=0 if get_lang()=="EN" else 1)
        if lc != get_lang():
            st.session_state.lang = lc
            st.rerun()
        st.markdown(f"<div style='margin:16px 0 8px; font-size:7px; letter-spacing:3px;'>"
                    f"{st.session_state.user_email}</div>", unsafe_allow_html=True)
        if st.button(t("Logout →", "خروج →"), use_container_width=True, type="secondary"):
            do_logout()

    # Hero
    st.markdown("""
    <div style='padding:1rem 2rem 0 2rem;'>
      <div class='hero-title'>مقارنة <em>الموسم</em></div>
      <div class='hero-title' style='font-size:28px; margin-top:-8px;'>Season Comparison</div>
    </div>
    """, unsafe_allow_html=True)

    # System status pills (simple)
    st.markdown("<div class='section-tag'>Connected Systems</div>", unsafe_allow_html=True)
    sys_status = []
    for sys in SYSTEM_KEYS:
        cfg = get_system_config(sys)
        if cfg:
            auth_r = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
            ok = auth_r["ok"]
            status = "🟢 Online" if ok else "🔴 Offline"
        else:
            status = "⚫ No config"
        sys_status.append(f"<span style='background:rgba(74,172,180,0.1); padding:4px 12px; border-radius:100px; font-size:10px; letter-spacing:1px;'>{get_system_name(sys)}: {status}</span>")
    st.markdown(f"<div style='display:flex; gap:8px; flex-wrap:wrap; margin-bottom:20px;'>{' '.join(sys_status)}</div>", unsafe_allow_html=True)

    # Season selection
    st.markdown("<div class='section-tag'>Select Season</div>", unsafe_allow_html=True)
    all_seasons = {}
    for sys in SYSTEM_KEYS:
        sf = detect_season_field(sys)
        if sf:
            seasons = fetch_distinct_seasons(sys, sf)
            if seasons:
                all_seasons[sys] = seasons
    if not all_seasons:
        st.warning(t("No seasons found in any system. Check season field configuration.", "لم يتم العثور على مواسم في أي نظام. تحقق من إعدادات حقل الموسم."))
        return

    # Combine all seasons into a single unique set (by label)
    combined = {}
    for sys, seasons in all_seasons.items():
        for val, label in seasons:
            combined[label] = val   # keep first occurrence's value (should be same across systems if ids differ? but we use label for display)
    season_labels = sorted(combined.keys())
    selected_label = st.selectbox(t("Season", "الموسم"), season_labels, key="season_select")
    selected_value = combined[selected_label]

    # Comparison button
    if st.button(t("Compare Season →", "مقارنة الموسم →"), type="primary", use_container_width=False):
        with st.spinner(t("Fetching data from all systems...", "جلب البيانات من جميع الأنظمة...")):
            df_matrix = build_season_comparison_matrix(selected_label, selected_value)
        if df_matrix.empty:
            st.error(t("No products found for this season.", "لا توجد منتجات لهذا الموسم."))
        else:
            st.session_state["season_matrix"] = df_matrix
            st.session_state["season_name"] = selected_label
            st.rerun()

    # Display results
    if "season_matrix" in st.session_state:
        df = st.session_state["season_matrix"]
        season_name = st.session_state["season_name"]

        # Summary metrics
        total_models = df["Model Code"].nunique()
        total_qty = int(df["Total Qty"].sum())
        sys_qty_stats = {}
        for sys in SYSTEM_KEYS:
            col = f"{sys} Qty"
            if col in df.columns:
                sys_qty_stats[get_system_name(sys)] = int(df[col].sum())

        col1, col2, col3 = st.columns(3)
        col1.metric(t("Total Models", "إجمالي الموديلات"), f"{total_models:,}")
        col2.metric(t("Total Units", "إجمالي الوحدات"), f"{total_qty:,}")
        # Show systems with non-zero qty in a third metric
        non_zero_sys = [f"{k}: {v:,}" for k, v in sys_qty_stats.items() if v > 0]
        col3.metric(t("Systems with stock", "أنظمة بها مخزون"), ", ".join(non_zero_sys) if non_zero_sys else "—")

        st.markdown("---")
        st.markdown("<div class='section-tag'>Comparison Matrix Preview</div>", unsafe_allow_html=True)

        # Decide: if dataset large (>200 rows), show only metrics + download
        if len(df) > 200:
            st.info(t("More than 200 rows – displaying summary only. Download Excel for full view.",
                      "أكثر من 200 صف – يتم عرض الملخص فقط. حمّل Excel للعرض الكامل."))
            st.dataframe(df.head(10), use_container_width=True)
            st.caption(f"Showing first 10 of {len(df)} rows")
        else:
            st.dataframe(df, use_container_width=True)

        # Excel download
        excel_data = to_excel_season_matrix(df, season_name)
        st.download_button(
            label=t("Download Excel Matrix ↓", "تحميل ملف Excel ↓"),
            data=excel_data,
            file_name=f"season_comparison_{season_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="season_download"
        )

        # Option to clear
        if st.button(t("Clear Results", "مسح النتائج"), type="secondary"):
            del st.session_state["season_matrix"]
            del st.session_state["season_name"]
            st.rerun()

# -----------------------------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------------------------
restore_session()
if not st.session_state.authenticated:
    show_login()
else:
    show_dashboard()
