"""
SWAG Season Comparison Dashboard – Fixed Season Mapping & Domain Building
Only Season Comparison · Large Dataset Ready
"""

import io
from datetime import datetime
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
.debug-box {
    background: rgba(0,0,0,0.2);
    border: 1px solid rgba(74,172,180,0.1);
    border-radius: 8px;
    padding: 12px 16px;
    font-family: monospace;
    font-size: 11px;
    color: rgba(255,255,255,0.6);
    margin-top: 20px;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# CONSTANTS & LANGUAGE
# -----------------------------------------------------------------------------
SYSTEM_KEYS = ["SWAG", "STOCK", "LAROUCHE", "DIFFC", "FASHIONLIMITS"]
SEASON_FIELD_CANDIDATES = [
    "x_studio_season",
    "season_id",
    "x_season",
    "x_studio_season_name",
    "season",
    "x_season_id"
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
    st.session_state.season_debug = {}

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
# XML-RPC HELPERS (unchanged)
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
# SEASON DETECTION (stores value -> label mapping and field info)
# -----------------------------------------------------------------------------
def detect_season_field_and_model(system_key):
    """Returns (model, field_name, field_type, relation) or (None, None, None, None)."""
    cfg = get_system_config(system_key)
    if not cfg:
        return None, None, None, None
    auth_res = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth_res["ok"]:
        return None, None, None, None
    uid = auth_res["uid"]
    for model in ["product.template", "product.product"]:
        try:
            fields = _x(cfg["url"], cfg["db"], uid, cfg["api_key"],
                        model, "fields_get", [],
                        {"attributes": ["string", "type", "relation"]})
            for cand in SEASON_FIELD_CANDIDATES:
                if cand in fields:
                    ftype = fields[cand]["type"]
                    relation = fields[cand].get("relation") if ftype == "many2one" else None
                    return model, cand, ftype, relation
            for fname, finfo in fields.items():
                if "season" in fname.lower():
                    ftype = finfo["type"]
                    relation = finfo.get("relation") if ftype == "many2one" else None
                    return model, fname, ftype, relation
        except Exception:
            continue
    return None, None, None, None

def fetch_distinct_seasons(system_key, model, field, ftype, relation):
    """Return list of (value, label) for season field."""
    if not model or not field:
        return []
    cfg = get_system_config(system_key)
    if not cfg:
        return []
    auth_res = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth_res["ok"]:
        return []
    uid = auth_res["uid"]
    try:
        domain = [[field, "!=", False]]
        records = _x(cfg["url"], cfg["db"], uid, cfg["api_key"],
                     model, "search_read", [domain],
                     {"fields": [field], "limit": 10000})
        if not records:
            return []
        unique_vals = {}
        for rec in records:
            val = rec.get(field)
            if val is False or val is None:
                continue
            if ftype == "many2one":
                # val can be [id, name] or just id
                if isinstance(val, list) and len(val) >= 2:
                    val_id, val_name = val[0], val[1]
                    unique_vals[val_id] = val_name
                else:
                    unique_vals[val] = str(val)
            else:
                # Char / Selection
                unique_vals[val] = str(val)
        # resolve many2one names if we only have IDs
        if ftype == "many2one" and relation:
            ids = [k for k in unique_vals.keys() if isinstance(k, int)]
            if ids and any(isinstance(v, int) for v in unique_vals.values()):
                rel_recs = _x(cfg["url"], cfg["db"], uid, cfg["api_key"],
                              relation, "search_read",
                              [[["id", "in", ids]]],
                              {"fields": ["id", "display_name"], "limit": len(ids)+10})
                name_map = {r["id"]: r.get("display_name", str(r["id"])) for r in rel_recs}
                for vid in ids:
                    if vid in name_map:
                        unique_vals[vid] = name_map[vid]
        seasons = [(v, unique_vals[v]) for v in unique_vals]
        seasons.sort(key=lambda x: x[1])
        return seasons
    except Exception:
        return []

def get_all_seasons_across_systems():
    """
    Returns dict: system_key -> {
        "model": str,
        "field": str,
        "ftype": str,
        "relation": str | None,
        "seasons": list of (value, label),
        "label_to_value": dict label->value
    }
    Also stores debug in st.session_state.season_debug
    """
    debug_info = {}
    all_info = {}
    for sys in SYSTEM_KEYS:
        model, field, ftype, relation = detect_season_field_and_model(sys)
        if not model or not field:
            debug_info[sys] = {
                "status": "no_field",
                "model": None,
                "field": None,
                "seasons_count": 0,
                "error": None
            }
            continue
        seasons = fetch_distinct_seasons(sys, model, field, ftype, relation)
        label_to_value = {label: value for value, label in seasons}
        debug_info[sys] = {
            "status": "ok" if seasons else "no_seasons",
            "model": model,
            "field": field,
            "ftype": ftype,
            "relation": relation,
            "seasons_count": len(seasons),
            "sample_seasons": seasons[:5]
        }
        if seasons:
            all_info[sys] = {
                "model": model,
                "field": field,
                "ftype": ftype,
                "relation": relation,
                "seasons": seasons,
                "label_to_value": label_to_value
            }
    st.session_state.season_debug = debug_info
    return all_info

# -----------------------------------------------------------------------------
# HELPER: resolve stored value for a system given a season label
# -----------------------------------------------------------------------------
def resolve_season_value_for_system(season_label, sys_info):
    """Return (stored_value, matched_label) or (None, None) if not found."""
    label_to_value = sys_info["label_to_value"]
    # exact match
    if season_label in label_to_value:
        return label_to_value[season_label], season_label
    # normalized match (trim, lower, remove extra spaces)
    norm_label = season_label.strip().lower()
    for label, value in label_to_value.items():
        if label.strip().lower() == norm_label:
            return value, label
    # if still not found, try to match by any contained substring (loose)
    for label, value in label_to_value.items():
        if norm_label in label.lower() or label.lower() in norm_label:
            return value, label
    return None, None

# -----------------------------------------------------------------------------
# FETCH PRODUCTS FOR A GIVEN SEASON (FIXED DOMAIN)
# -----------------------------------------------------------------------------
def fetch_season_products(system_key, sys_info, season_label):
    """
    Fetch product.product records for the given season label.
    Returns DataFrame and debug dict.
    """
    cfg = get_system_config(system_key)
    if not cfg:
        return pd.DataFrame(), {"error": "No config"}
    auth_res = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth_res["ok"]:
        return pd.DataFrame(), {"error": f"Auth failed: {auth_res.get('error')}"}
    uid = auth_res["uid"]
    model = sys_info["model"]
    field = sys_info["field"]
    ftype = sys_info["ftype"]
    stored_value, matched_label = resolve_season_value_for_system(season_label, sys_info)
    debug = {
        "model": model,
        "field": field,
        "ftype": ftype,
        "requested_label": season_label,
        "matched_label": matched_label,
        "stored_value": stored_value,
        "templates_found": 0,
        "products_found": 0,
        "error": None,
        "domain_used": None
    }
    if stored_value is None:
        debug["error"] = f"Season label '{season_label}' not found in system"
        return pd.DataFrame(), debug
    try:
        if model == "product.template":
            # Build domain for templates (use "in" with list for many2one, "=" for others)
            if ftype == "many2one":
                domain = [[field, "in", [stored_value]]]
            else:
                domain = [[field, "=", stored_value]]
            debug["domain_used"] = domain
            templates = _x(cfg["url"], cfg["db"], uid, cfg["api_key"],
                           "product.template", "search_read",
                           domain, {"fields": ["id"], "limit": 50000})
            if not templates:
                debug["templates_found"] = 0
                return pd.DataFrame(), debug
            tmpl_ids = [t["id"] for t in templates]
            debug["templates_found"] = len(tmpl_ids)
            # IMPORTANT: Always use list for "in"
            products = _x(cfg["url"], cfg["db"], uid, cfg["api_key"],
                          "product.product", "search_read",
                          [[["product_tmpl_id", "in", tmpl_ids], ["sale_ok", "=", True]]],
                          {"fields": ["default_code", "display_name", "qty_available", "list_price", "product_tmpl_id"],
                           "limit": 200000})
        else:  # product.product
            if ftype == "many2one":
                domain = [[field, "in", [stored_value]], ["sale_ok", "=", True]]
            else:
                domain = [[field, "=", stored_value], ["sale_ok", "=", True]]
            debug["domain_used"] = domain
            products = _x(cfg["url"], cfg["db"], uid, cfg["api_key"],
                          "product.product", "search_read",
                          domain,
                          {"fields": ["default_code", "display_name", "qty_available", "list_price", "product_tmpl_id"],
                           "limit": 200000})
        if not products:
            debug["products_found"] = 0
            return pd.DataFrame(), debug
        debug["products_found"] = len(products)
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
        return pd.DataFrame(rows), debug
    except Exception as e:
        debug["error"] = str(e)
        return pd.DataFrame(), debug

def build_season_comparison_matrix(selected_season_label, all_systems_info):
    """
    Parallel fetch for all systems, merge into matrix.
    Returns (df, debug_dict).
    """
    all_data = {}
    debug_info = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {}
        for sys, info in all_systems_info.items():
            futures[executor.submit(fetch_season_products, sys, info, selected_season_label)] = sys
        for fut in as_completed(futures):
            sys = futures[fut]
            try:
                df, dbg = fut.result()
                debug_info[sys] = dbg
                if not df.empty:
                    all_data[sys] = df
            except Exception as e:
                debug_info[sys] = {"error": str(e)}
    if not all_data:
        return pd.DataFrame(), debug_info
    # Merge row by model code
    merged = None
    for sys, df in all_data.items():
        sub = df[["Model Code", "Product", "Qty", "Price"]].copy()
        sub = sub.rename(columns={"Qty": f"{sys} Qty", "Price": f"{sys} Price"})
        if merged is None:
            merged = sub
        else:
            merged = pd.merge(merged, sub, on="Model Code", how="outer")
    if merged is None:
        return pd.DataFrame(), debug_info
    # Total Qty
    qty_cols = [c for c in merged.columns if c.endswith(" Qty")]
    merged["Total Qty"] = merged[qty_cols].sum(axis=1)
    # Fill product name from first non-null
    product_cols = [c for c in merged.columns if c == "Product"]
    if product_cols:
        merged["Product"] = merged[product_cols].bfill(axis=1).iloc[:, 0]
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
    for col in merged.columns:
        if "Price" in col:
            merged[col] = merged[col].round(2)
        elif "Qty" in col:
            merged[col] = merged[col].astype(int)
    return merged, debug_info

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
        # styling
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
        total_row = max_row + 1
        ws.cell(row=total_row, column=1, value="TOTAL")
        ws.cell(row=total_row, column=1).font = tot_font
        ws.cell(row=total_row, column=1).fill = tot_fill
        ws.cell(row=total_row, column=1).alignment = ctr_align
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
# LOGIN (unchanged)
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
        st.markdown(f"<div style='margin:16px 0 8px; font-size:7px; letter-spacing:3px;'>{st.session_state.user_email}</div>", unsafe_allow_html=True)
        if st.button(t("Logout →", "خروج →"), use_container_width=True, type="secondary"):
            do_logout()

    st.markdown("""
    <div style='padding:1rem 2rem 0 2rem;'>
      <div class='hero-title'>مقارنة <em>الموسم</em></div>
      <div class='hero-title' style='font-size:28px; margin-top:-8px;'>Season Comparison</div>
    </div>
    """, unsafe_allow_html=True)

    # System status (simple)
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

    # Detect all seasons across systems
    all_systems_info = get_all_seasons_across_systems()
    if not all_systems_info:
        st.error(t("No seasons found in any system. Check debug info below.", "لم يتم العثور على مواسم في أي نظام. تحقق من معلومات التصحيح أدناه."))
        with st.expander("🔍 Debug: Season Detection Results", expanded=True):
            for sys, info in st.session_state.season_debug.items():
                st.markdown(f"**{get_system_name(sys)}**")
                if info["status"] == "no_field":
                    st.write(f"❌ No season field found (checked candidates: {', '.join(SEASON_FIELD_CANDIDATES)})")
                elif info["status"] == "no_seasons":
                    st.write(f"⚠️ Found field `{info['field']}` on `{info['model']}` but no non-empty season values.")
                else:
                    st.write(f"✅ Field `{info['field']}` on `{info['model']}` → {info['seasons_count']} seasons")
                    if info.get("sample_seasons"):
                        st.write(f"   Sample: {info['sample_seasons'][:3]}")
                st.write("---")
        return

    # Build global season dropdown (union of all seasons from all systems)
    # Use label as key, but store also the original system mapping for debug
    global_seasons_set = set()
    for sys, info in all_systems_info.items():
        for value, label in info["seasons"]:
            global_seasons_set.add(label)
    season_labels = sorted(global_seasons_set)
    selected_label = st.selectbox(t("Season", "الموسم"), season_labels, key="season_select")

    # Comparison button
    if st.button(t("Compare Season →", "مقارنة الموسم →"), type="primary", use_container_width=False):
        with st.spinner(t("Fetching data from all systems...", "جلب البيانات من جميع الأنظمة...")):
            df_matrix, debug_info = build_season_comparison_matrix(selected_label, all_systems_info)
        if df_matrix.empty:
            st.error(t("No products found for this season.", "لا توجد منتجات لهذا الموسم."))
            # Show detailed fetch debug
            with st.expander("🔍 Season Product Fetch Debug", expanded=True):
                for sys, dbg in debug_info.items():
                    st.markdown(f"**{get_system_name(sys)}**")
                    if "error" in dbg:
                        st.write(f"❌ Error: {dbg['error']}")
                    else:
                        st.write(f"Model: {dbg.get('model')}")
                        st.write(f"Field: {dbg.get('field')} (type: {dbg.get('ftype')})")
                        st.write(f"Requested season label: '{dbg.get('requested_label')}'")
                        st.write(f"Matched label: '{dbg.get('matched_label')}'")
                        st.write(f"Stored value used for filter: {dbg.get('stored_value')}")
                        st.write(f"Domain used: {dbg.get('domain_used')}")
                        st.write(f"Templates found: {dbg.get('templates_found', 0)}")
                        st.write(f"Products found: {dbg.get('products_found', 0)}")
                    st.write("---")
        else:
            st.session_state["season_matrix"] = df_matrix
            st.session_state["season_name"] = selected_label
            st.session_state["fetch_debug"] = debug_info
            st.rerun()

    # Display results if available
    if "season_matrix" in st.session_state:
        df = st.session_state["season_matrix"]
        season_name = st.session_state["season_name"]
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
        non_zero_sys = [f"{k}: {v:,}" for k, v in sys_qty_stats.items() if v > 0]
        col3.metric(t("Systems with stock", "أنظمة بها مخزون"), ", ".join(non_zero_sys) if non_zero_sys else "—")
        st.markdown("---")
        st.markdown("<div class='section-tag'>Comparison Matrix Preview</div>", unsafe_allow_html=True)
        if len(df) > 200:
            st.info(t("More than 200 rows – displaying summary only. Download Excel for full view.",
                      "أكثر من 200 صف – يتم عرض الملخص فقط. حمّل Excel للعرض الكامل."))
            st.dataframe(df.head(10), use_container_width=True)
            st.caption(f"Showing first 10 of {len(df)} rows")
        else:
            st.dataframe(df, use_container_width=True)
        excel_data = to_excel_season_matrix(df, season_name)
        st.download_button(
            label=t("Download Excel Matrix ↓", "تحميل ملف Excel ↓"),
            data=excel_data,
            file_name=f"season_comparison_{season_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="season_download"
        )
        # Optional: show fetch debug again (collapsed)
        with st.expander("🔍 Debug: Product Fetch Details"):
            for sys, dbg in st.session_state.get("fetch_debug", {}).items():
                st.markdown(f"**{get_system_name(sys)}**")
                if "error" in dbg:
                    st.write(f"❌ {dbg['error']}")
                else:
                    st.write(f"Model: {dbg.get('model')} | Field: {dbg.get('field')} ({dbg.get('ftype')})")
                    st.write(f"Season: '{dbg.get('requested_label')}' → matched: '{dbg.get('matched_label')}' → value: {dbg.get('stored_value')}")
                    st.write(f"Domain: {dbg.get('domain_used')}")
                    st.write(f"Templates: {dbg.get('templates_found', 0)} → Products: {dbg.get('products_found', 0)}")
                st.write("---")
        if st.button(t("Clear Results", "مسح النتائج"), type="secondary"):
            del st.session_state["season_matrix"]
            del st.session_state["season_name"]
            if "fetch_debug" in st.session_state:
                del st.session_state["fetch_debug"]
            st.rerun()

    # Always show season detection debug (collapsed)
    with st.expander("🔍 Debug: Season Field Detection"):
        for sys, info in st.session_state.season_debug.items():
            st.markdown(f"**{get_system_name(sys)}**")
            if info["status"] == "no_field":
                st.write(f"❌ No season field found. Candidates: {', '.join(SEASON_FIELD_CANDIDATES)}")
            elif info["status"] == "no_seasons":
                st.write(f"⚠️ Found field `{info['field']}` on `{info['model']}` but no season values.")
            else:
                st.write(f"✅ Field `{info['field']}` on `{info['model']}` (type: {info.get('ftype')}) → {info['seasons_count']} seasons")
                if info.get("sample_seasons"):
                    st.write("Sample (value, label):")
                    for v, lbl in info["sample_seasons"]:
                        st.write(f"   - {lbl} (value: {v})")
            st.write("---")

# -----------------------------------------------------------------------------
# ENTRY POINT
# -----------------------------------------------------------------------------
restore_session()
if not st.session_state.authenticated:
    show_login()
else:
    show_dashboard()
