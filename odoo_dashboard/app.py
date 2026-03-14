# ╔══════════════════════════════════════════════════════════════════╗
# ║        👗 Outfit Dashboard – v4 (CSV-Structure Aligned)         ║
# ║                                                                  ║
# ║  v4 changes (aligned to real Odoo CSV structures):              ║
# ║  CSV-1 : get_branch_code() — single location-name helper        ║
# ║  CSV-2 : load_warehouse_stock — real stock.quant fields         ║
# ║  CSV-3 : load_branch_sales — unified SO+POS with BranchCode     ║
# ║  CSV-4 : POS branch derived from order_id[1] name prefix        ║
# ║  CSV-5 : SO branch from warehouse_id name via get_branch_code   ║
# ║  CSV-6 : load_products — real product.product fields            ║
# ║  CSV-7 : normalize_product() helper attaches Brand & Category   ║
# ║  CSV-8 : 365-day NM lookback via _compute_non_moving()          ║
# ║  CSV-9 : PSI view build_psi_view() + aggregate_by_dim()         ║
# ║                                                                  ║
# ║  Prior fixes retained:                                          ║
# ║  FIX-1 : Non-moving 365-day lookback window                     ║
# ║  FIX-2 : Branch sales includes POS                              ║
# ║  FIX-3 : Consistent warehouse naming via helper                 ║
# ║  FIX-4 : UnitPrice + NetPrice                                   ║
# ║  NEW-A/B/C/D/E/F/G: PSI analytics                              ║
# ╚══════════════════════════════════════════════════════════════════╝

import streamlit as st

st.set_page_config(
    page_title="👗 Outfit Dashboard",
    page_icon="👗",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"Get help": None, "Report a bug": None, "About": None},
)

import requests
import pandas as pd
import plotly.express as px
import plotly.io as pio
from io import BytesIO
from datetime import datetime, timedelta
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Globals ───────────────────────────────────────────────────────────────────
ODOO_URL         = "https://odooprosys-la-rouche.odoo.com"
ODOO_DB          = "odooprosys-la-rouche-production-12364313"
LOW_THRESHOLD    = 5
BATCH            = 1_000
INV_TTL          = 600
SALES_TTL        = 300
NM_LOOKBACK_DAYS = 365   # CSV-8: fixed 365-day window for non-moving

# ── Plotly theme ──────────────────────────────────────────────────────────────
pio.templates.default = "plotly_white"
pio.templates["plotly_white"].layout.update(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=-0.25),
    bargap=0.22,
    transition_duration=400,
)

# ── Luxury CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp{background:radial-gradient(circle at top left,#1a1a1a 0%,#0d0d0d 45%,#000 100%);
       color:#f0e6d2;font-family:"Playfair Display",serif;}
.block-container{padding-top:1.2rem;padding-bottom:1.5rem;}
h1,h2,h3,h4{color:#d4af37;text-shadow:0 0 5px rgba(212,175,55,.5);}
.glass-card{background:rgba(10,10,10,.85);border-radius:20px;padding:20px 22px;
    border:1px solid rgba(212,175,55,.3);box-shadow:0 20px 50px rgba(0,0,0,.7);
    backdrop-filter:blur(16px);animation:fadeInUp .6s ease-out;margin-bottom:16px;}
.kpi-card{background:linear-gradient(135deg,rgba(212,175,55,.15),rgba(184,134,11,.1));
    border-radius:18px;padding:16px 20px;border:1px solid rgba(212,175,55,.6);
    box-shadow:0 14px 35px rgba(0,0,0,.6);backdrop-filter:blur(14px);
    transition:all .3s ease-out;animation:pulseGlow 2s infinite alternate;}
.kpi-card:hover{transform:translateY(-5px) scale(1.05);box-shadow:0 20px 45px rgba(212,175,55,.3);}
.kpi-title{font-size:.8rem;letter-spacing:.1em;text-transform:uppercase;color:#c0c0c0;}
.kpi-value{font-size:1.4rem;font-weight:700;color:#f0e6d2;}
.kpi-sub{font-size:.8rem;color:#a9a9a9;}
.status-pill{border-radius:999px;padding:3px 12px;font-size:.75rem;font-weight:600;animation:glow 1.5s infinite alternate;}
.status-OK {background:rgba(0,128,0,.15);  color:#90ee90;border:1px solid rgba(0,128,0,.6);}
.status-LOW{background:rgba(255,165,0,.15); color:#ffd700;border:1px solid rgba(255,165,0,.6);}
.status-OUT{background:rgba(139,0,0,.15);   color:#ff6347;border:1px solid rgba(139,0,0,.6);}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#0d0d0d 0%,#000 60%,#1a1a1a 100%);
    border-right:1px solid rgba(212,175,55,.4);}
section[data-testid="stSidebar"] .block-container{padding-top:1.6rem;}
[data-testid="stDataFrame"]{border-radius:12px;overflow:hidden;border:1px solid rgba(212,175,55,.4);}
.stDownloadButton button{border-radius:999px;
    background:linear-gradient(135deg,#d4af37,#b8860b) !important;
    color:#000 !important;border:none;font-weight:600;transition:all .3s;}
.stDownloadButton button:hover{filter:brightness(1.1);transform:scale(1.05);}
.stTabs [data-baseweb="tab-list"]{gap:.6rem;}
.stTabs [data-baseweb="tab"]{background-color:rgba(10,10,10,.9);border-radius:999px;
    padding:7px 12px;border:1px solid rgba(212,175,55,.4);transition:all .3s;}
.stTabs [data-baseweb="tab"][aria-selected="true"]{
    background:linear-gradient(135deg,#d4af37,#b8860b);color:#000;border-color:transparent;}
.stTabs [data-baseweb="tab"]:hover{transform:scale(1.05);}
@keyframes fadeInUp {from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulseGlow{from{box-shadow:0 14px 35px rgba(0,0,0,.6)}to{box-shadow:0 14px 35px rgba(212,175,55,.2)}}
@keyframes glow     {from{text-shadow:0 0 3px currentColor}to{text-shadow:0 0 8px currentColor}}
</style>
""", unsafe_allow_html=True)

STATUS_COLORS = {"OK": "#90ee90", "LOW": "#ffd700", "OUT": "#ff6347"}
_GOLD_SCALE   = [[0, "#1a1a1a"], [0.5, "#b8860b"], [1, "#d4af37"]]


# ═════════════════════════════════════════════════════════════════════════════
# CSV-1  BRANCH / LOCATION HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def get_branch_code(location_name: str) -> str:
    """
    CSV-1: Canonical branch-code extractor.
    'B402/لمسات استايل-1' → 'B402'
    'W102/استلام بضاعة'  → 'W102'
    '101/Stock'           → '101'
    'WH'                  → 'WH'
    Any non-string / None → 'Unknown'
    """
    if isinstance(location_name, str) and location_name.strip():
        if "/" in location_name:
            return location_name.split("/")[0].strip()
        return location_name.strip()
    return "Unknown"


def _parse_m2o(field_val, fallback=""):
    """
    Safely parse a many2one field returned by Odoo JSON-RPC.
    It may be [id, 'name'], False, or None.
    Returns (id, name) tuple.
    """
    if isinstance(field_val, (list, tuple)) and len(field_val) >= 2:
        return int(field_val[0]), str(field_val[1])
    return 0, fallback


# ═════════════════════════════════════════════════════════════════════════════
# ODOO RPC HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def odoo_rpc(endpoint, method, *args):
    payload = {
        "jsonrpc": "2.0", "method": "call",
        "params": {"service": endpoint, "method": method, "args": list(args)},
    }
    r   = requests.post(f"{ODOO_URL}/jsonrpc", json=payload, timeout=60)
    res = r.json()
    if "error" in res:
        raise Exception(res["error"].get("data", {}).get("message", str(res["error"])))
    return res["result"]


def odoo_login(u, k):
    uid = odoo_rpc("common", "authenticate", ODOO_DB, u, k, {})
    if not uid:
        raise Exception("Login failed – check email and API key.")
    return uid


def _search_read(uid, k, model, domain, fields, limit=BATCH, offset=0):
    return odoo_rpc(
        "object", "execute_kw", ODOO_DB, uid, k,
        model, "search_read",
        [domain],
        {"fields": fields, "limit": limit, "offset": offset, "order": "id asc"},
    )


def fetch_all(uid, k, model, domain, fields):
    all_recs, offset = [], 0
    while True:
        recs = _search_read(uid, k, model, domain, fields,
                            limit=BATCH, offset=offset)
        if not recs:
            break
        all_recs.extend(recs)
        if len(recs) < BATCH:
            break
        offset += BATCH
    return all_recs


# ═════════════════════════════════════════════════════════════════════════════
# SESSION-STATE CACHE
# ═════════════════════════════════════════════════════════════════════════════

def _ss_key(uid, full_history, from_date, to_date, nm_days, page):
    return f"df|{uid}|{full_history}|{from_date}|{to_date}|{nm_days}|{page}"

def _ss_get(key):      return st.session_state.get(key)
def _ss_put(key, val): st.session_state[key] = val


# ═════════════════════════════════════════════════════════════════════════════
# CSV-6  PRODUCT MASTER
# ═════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False, ttl=INV_TTL)
def load_products(_uid, _k):
    """
    CSV-6: Fields confirmed from product_product_structure.csv:
      id, default_code, name, categ_id, brand_id, type, active
    Only active stockable products (type='product').
    """
    recs = fetch_all(
        _uid, _k, "product.product",
        [["active", "=", True], ["type", "=", "product"]],
        ["id", "default_code", "name", "categ_id", "brand_id",
         "qty_available", "virtual_available", "standard_price"],
    )
    rows = []
    for p in recs:
        _, cat_name  = _parse_m2o(p.get("categ_id"),  "-")
        _, brand_name= _parse_m2o(p.get("brand_id"),  "-")
        qty  = max(0, p.get("qty_available") or 0)
        cost = p.get("standard_price") or 0
        rows.append({
            "PID"     : p["id"],
            "Ref"     : p.get("default_code") or "",
            "Product" : p.get("name") or "",
            "Category": cat_name,
            "Brand"   : brand_name,
            "Qty"     : qty,
            "Forecast": p.get("virtual_available") or 0,
            "Cost"    : cost,
            "Value"   : round(qty * cost, 2),
            "Status"  : "OUT" if qty <= 0 else ("LOW" if qty <= LOW_THRESHOLD else "OK"),
        })
    return pd.DataFrame(rows)


# CSV-7: reusable helper – merge Brand & Category from product master onto any df
def normalize_product(df: pd.DataFrame, df_prod: pd.DataFrame) -> pd.DataFrame:
    """CSV-7: attach Brand and Category to any dataframe that has a PID column."""
    if df.empty:
        return df
    meta = df_prod[["PID", "Category", "Brand"]].drop_duplicates("PID")
    out  = df.merge(meta, on="PID", how="left", suffixes=("", "_prod"))
    # if the df already had Category/Brand columns, prefer the product master's
    for col in ("Category", "Brand"):
        prod_col = col + "_prod"
        if prod_col in out.columns:
            out[col] = out[col].where(out[col].notna() & (out[col] != "-"),
                                      out[prod_col])
            out.drop(columns=[prod_col], inplace=True)
    out["Category"] = out.get("Category", pd.Series(dtype=str)).fillna("-")
    out["Brand"]    = out.get("Brand",    pd.Series(dtype=str)).fillna("-")
    return out


# ═════════════════════════════════════════════════════════════════════════════
# SALE ORDER (SO) LOADER
# ═════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False, ttl=SALES_TTL)
def load_sal(_uid, _k, _full_history, _from_date, _to_date):
    """
    CSV: sale_order_structure + sale_order_line_structure.
    Fields used:
      sale.order      : id, date_order, team_id, warehouse_id, state
      sale.order.line : id, order_id, product_id, product_uom_qty,
                        price_unit, price_subtotal
    """
    domain = [["state", "in", ["sale", "done"]]]
    if not _full_history:
        domain += [["date_order", ">=", str(_from_date)],
                   ["date_order", "<",  str(_to_date + timedelta(days=1))]]
    orders = fetch_all(_uid, _k, "sale.order", domain,
                       ["id", "name", "date_order", "team_id", "warehouse_id"])
    if not orders:
        return pd.DataFrame()

    order_ids = [o["id"] for o in orders]
    date_map  = {o["id"]: o["date_order"] for o in orders}
    # CSV-5: SO branch from warehouse_id — apply get_branch_code to WH name
    wh_map    = {}
    for o in orders:
        _, wh_name = _parse_m2o(o.get("warehouse_id"), "WH")
        wh_map[o["id"]] = get_branch_code(wh_name)   # CSV-5

    lines = fetch_all(_uid, _k, "sale.order.line",
                      [["order_id", "in", order_ids]],
                      ["id", "order_id", "product_id",
                       "product_uom_qty", "price_unit", "price_subtotal"])
    rows = []
    for r in lines:
        oid    = _parse_m2o(r.get("order_id"))[0]
        pid, prod_name = _parse_m2o(r.get("product_id"))
        date   = date_map.get(oid)
        if not date or not oid:
            continue
        qty = r.get("product_uom_qty") or 0
        amt = r.get("price_subtotal")  or 0
        rows.append({
            "PID"       : pid,
            "Product"   : prod_name,
            "Qty"       : qty,
            "Amount"    : amt,
            "UnitPrice" : r.get("price_unit") or 0,
            "NetPrice"  : round(amt / qty, 2) if qty else 0,
            "Date"      : pd.to_datetime(date),
            "BranchCode": wh_map.get(oid, "WH"),
            "Branch"    : wh_map.get(oid, "WH"),
            "Source"    : "SO",
            "OrderID"   : oid,
        })
    return pd.DataFrame(rows)


# ═════════════════════════════════════════════════════════════════════════════
# POS ORDER LOADER
# ═════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False, ttl=SALES_TTL)
def load_pos_sales(_uid, _k, _full_history, _from_date, _to_date):
    """
    CSV: pos_order_line_structure.
    Fields used:
      pos.order      : id, name, date_order, state
      pos.order.line : id, order_id, product_id, qty, price_unit, price_subtotal

    CSV-4: Branch is derived from the POS order name (order_id[1]).
    Example: order name 'العليا اوت فت/0181' → Branch = 'العليا اوت فت'
             which is everything BEFORE the last '/' separator in the order name.
    BranchCode is the same string (Arabic store names are used as-is because
    there is no numeric prefix in POS order names; a mapping table can be
    added later when a stock-move link is available).
    """
    domain = [["state", "in", ["paid", "invoiced", "done"]]]
    if not _full_history:
        domain += [["date_order", ">=", str(_from_date)],
                   ["date_order", "<",  str(_to_date + timedelta(days=1))]]
    orders = fetch_all(_uid, _k, "pos.order", domain,
                       ["id", "name", "date_order"])
    if not orders:
        return pd.DataFrame()

    order_ids = [o["id"] for o in orders]
    date_map  = {o["id"]: o["date_order"] for o in orders}

    # CSV-4: derive branch from POS order name prefix (before last '/')
    def _pos_branch(order_name: str) -> str:
        if isinstance(order_name, str) and "/" in order_name:
            return order_name.rsplit("/", 1)[0].strip()
        return order_name or "POS"

    branch_map = {o["id"]: _pos_branch(o.get("name", "")) for o in orders}

    lines = fetch_all(_uid, _k, "pos.order.line",
                      [["order_id", "in", order_ids]],
                      ["id", "order_id", "product_id",
                       "qty", "price_unit", "price_subtotal"])
    rows = []
    for r in lines:
        oid          = _parse_m2o(r.get("order_id"))[0]
        pid, prod_nm = _parse_m2o(r.get("product_id"))
        date         = date_map.get(oid)
        if not date or not oid:
            continue
        qty    = r.get("qty")            or 0
        amt    = r.get("price_subtotal") or 0
        branch = branch_map.get(oid, "POS")
        rows.append({
            "PID"       : pid,
            "Product"   : prod_nm,
            "Qty"       : qty,
            "Amount"    : amt,
            "UnitPrice" : r.get("price_unit") or 0,
            "NetPrice"  : round(amt / qty, 2) if qty else 0,
            "Date"      : pd.to_datetime(date),
            "BranchCode": branch,   # CSV-4: Arabic branch name from order name
            "Branch"    : branch,
            "Source"    : "POS",
            "OrderID"   : oid,
        })
    return pd.DataFrame(rows)


# ═════════════════════════════════════════════════════════════════════════════
# PURCHASE ORDER LOADER
# ═════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False, ttl=SALES_TTL)
def load_pur(_uid, _k, _full_history, _from_date, _to_date):
    domain = [["state", "in", ["purchase", "done"]]]
    if not _full_history:
        domain += [["date_order", ">=", str(_from_date)],
                   ["date_order", "<",  str(_to_date + timedelta(days=1))]]
    orders = fetch_all(_uid, _k, "purchase.order", domain,
                       ["id", "date_order", "partner_id"])
    if not orders:
        return pd.DataFrame()
    order_ids = [o["id"] for o in orders]
    date_map  = {o["id"]: o["date_order"] for o in orders}
    supp_map  = {o["id"]: _parse_m2o(o.get("partner_id"), "-")[1] for o in orders}

    lines = fetch_all(_uid, _k, "purchase.order.line",
                      [["order_id", "in", order_ids]],
                      ["id", "order_id", "product_id",
                       "product_qty", "price_subtotal"])
    rows = []
    for r in lines:
        oid          = _parse_m2o(r.get("order_id"))[0]
        pid, prod_nm = _parse_m2o(r.get("product_id"))
        date         = date_map.get(oid)
        if not date:
            continue
        rows.append({
            "PID"     : pid,
            "Product" : prod_nm,
            "Qty"     : r.get("product_qty")    or 0,
            "Amount"  : r.get("price_subtotal") or 0,
            "Date"    : pd.to_datetime(date),
            "Supplier": supp_map.get(oid, "-"),
        })
    return pd.DataFrame(rows)


# ═════════════════════════════════════════════════════════════════════════════
# CSV-3  BRANCH SALES – unified SO + POS with BranchCode
# ═════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False, ttl=SALES_TTL)
def load_branch_sales(_uid, _k, _full_history, _from_date, _to_date):
    """
    CSV-3: Combines SO and POS lines into a single branch-sales frame.
    BranchCode on SO  : get_branch_code(warehouse_id name)  — CSV-5
    BranchCode on POS : prefix of order name before last '/' — CSV-4
    Both channels use the same column schema.
    """
    # ── SO ────────────────────────────────────────────────────────────────────
    so_domain = [["state", "in", ["sale", "done"]]]
    if not _full_history:
        so_domain += [["date_order", ">=", str(_from_date)],
                      ["date_order", "<",  str(_to_date + timedelta(days=1))]]
    so_orders = fetch_all(_uid, _k, "sale.order", so_domain,
                          ["id", "name", "date_order", "warehouse_id"])
    so_rows = []
    if so_orders:
        so_ids    = [o["id"] for o in so_orders]
        so_dt_map = {o["id"]: o["date_order"] for o in so_orders}
        so_wh_map = {}
        for o in so_orders:
            _, wh_name = _parse_m2o(o.get("warehouse_id"), "WH")
            # CSV-5: branch code = first segment of warehouse display name
            so_wh_map[o["id"]] = get_branch_code(wh_name)

        so_lines = fetch_all(_uid, _k, "sale.order.line",
                             [["order_id", "in", so_ids]],
                             ["id", "order_id", "product_id",
                              "product_uom_qty", "price_unit", "price_subtotal"])
        for r in so_lines:
            oid          = _parse_m2o(r.get("order_id"))[0]
            pid, prod_nm = _parse_m2o(r.get("product_id"))
            date         = so_dt_map.get(oid)
            if not date or not oid:
                continue
            qty  = r.get("product_uom_qty") or 0
            amt  = r.get("price_subtotal")  or 0
            bc   = so_wh_map.get(oid, "WH")
            so_rows.append({
                "OrderID"   : oid,
                "Date"      : pd.to_datetime(date),
                "BranchCode": bc,
                "Branch"    : bc,          # SO has no friendlier name; use code
                "Warehouse" : bc,
                "PID"       : pid,
                "Product"   : prod_nm,
                "Qty"       : qty,
                "Amount"    : amt,
                "UnitPrice" : r.get("price_unit") or 0,
                "NetPrice"  : round(amt / qty, 2) if qty else 0,
                "Source"    : "SO",
            })

    # ── POS ───────────────────────────────────────────────────────────────────
    pos_domain = [["state", "in", ["paid", "invoiced", "done"]]]
    if not _full_history:
        pos_domain += [["date_order", ">=", str(_from_date)],
                       ["date_order", "<",  str(_to_date + timedelta(days=1))]]
    pos_orders = fetch_all(_uid, _k, "pos.order", pos_domain,
                           ["id", "name", "date_order"])
    pos_rows = []
    if pos_orders:
        pos_ids    = [o["id"] for o in pos_orders]
        pos_dt_map = {o["id"]: o["date_order"] for o in pos_orders}

        def _pos_branch(name: str) -> str:
            # CSV-4: 'العليا اوت فت/0181' → 'العليا اوت فت'
            if isinstance(name, str) and "/" in name:
                return name.rsplit("/", 1)[0].strip()
            return name or "POS"

        pos_br_map = {o["id"]: _pos_branch(o.get("name", ""))
                      for o in pos_orders}

        pos_lines = fetch_all(_uid, _k, "pos.order.line",
                              [["order_id", "in", pos_ids]],
                              ["id", "order_id", "product_id",
                               "qty", "price_unit", "price_subtotal"])
        for r in pos_lines:
            oid          = _parse_m2o(r.get("order_id"))[0]
            pid, prod_nm = _parse_m2o(r.get("product_id"))
            date         = pos_dt_map.get(oid)
            if not date or not oid:
                continue
            qty    = r.get("qty")            or 0
            amt    = r.get("price_subtotal") or 0
            branch = pos_br_map.get(oid, "POS")
            pos_rows.append({
                "OrderID"   : oid,
                "Date"      : pd.to_datetime(date),
                "BranchCode": branch,   # CSV-4
                "Branch"    : branch,
                "Warehouse" : branch,
                "PID"       : pid,
                "Product"   : prod_nm,
                "Qty"       : qty,
                "Amount"    : amt,
                "UnitPrice" : r.get("price_unit") or 0,
                "NetPrice"  : round(amt / qty, 2) if qty else 0,
                "Source"    : "POS",
            })

    return pd.concat([pd.DataFrame(so_rows), pd.DataFrame(pos_rows)],
                     ignore_index=True)


# ═════════════════════════════════════════════════════════════════════════════
# CSV-2  WAREHOUSE STOCK  (stock.quant – real fields)
# ═════════════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False, ttl=INV_TTL)
def load_warehouse_stock(_uid, _k):
    """
    CSV-2: Fields confirmed from stock_quant_structure.csv:
      product_id, location_id, quantity, reserved_quantity, value
    Domain: internal locations only, quantity > 0.
    BranchCode = get_branch_code(LocationName).

    Returns:
      df_long  — long-form: PID, Product, BranchCode, LocationName, Qty, Value
      df_pivot — wide:  PID, Product, <BranchCode cols>, TOTAL, Value
    """
    quants = fetch_all(
        _uid, _k, "stock.quant",
        [["location_id.usage", "=", "internal"], ["quantity", ">", 0]],
        ["product_id", "location_id", "quantity", "reserved_quantity", "value"],
    )
    if not quants:
        return pd.DataFrame(), pd.DataFrame()

    rows = []
    for q in quants:
        pid, prod_nm  = _parse_m2o(q.get("product_id"))
        _,   loc_full = _parse_m2o(q.get("location_id"))
        # CSV-2: BranchCode from location name
        branch_code   = get_branch_code(loc_full)
        qty = max(0, q.get("quantity") or 0)
        val = q.get("value") or 0
        rows.append({
            "PID"        : pid,
            "Product"    : prod_nm,
            "BranchCode" : branch_code,
            "LocationName": loc_full,
            "Qty"        : qty,
            "Value"      : round(val, 2),
        })

    df_long = pd.DataFrame(rows)
    if df_long.empty:
        return df_long, pd.DataFrame()

    # Aggregate to BranchCode level (collapse bin locations within same branch)
    df_agg = (df_long
              .groupby(["PID", "Product", "BranchCode"], as_index=False)
              .agg(Qty=("Qty", "sum"), Value=("Value", "sum")))

    # Wide pivot: rows = product, columns = BranchCode
    pivot = (df_agg
             .pivot_table(index=["PID", "Product"], columns="BranchCode",
                          values="Qty", aggfunc="sum", fill_value=0)
             .reset_index())
    pivot.columns.name = None
    bc_cols = [c for c in pivot.columns if c not in ("PID", "Product")]
    pivot["TOTAL"] = pivot[bc_cols].sum(axis=1)
    # Value column: total per product across all branches
    val_map        = df_agg.groupby(["PID", "Product"])["Value"].sum()
    pivot["Value"] = pivot.set_index(["PID", "Product"]).index.map(val_map).values
    pivot          = pivot.sort_values("TOTAL", ascending=False)

    return df_agg, pivot


# ═════════════════════════════════════════════════════════════════════════════
# CSV-8  NON-MOVING COMPUTATION (365-day lookback)
# ═════════════════════════════════════════════════════════════════════════════

def _compute_non_moving(df_inv: pd.DataFrame,
                         df_sales_full: pd.DataFrame,
                         non_moving_days: int):
    """
    CSV-8: Uses the last NM_LOOKBACK_DAYS (365) days of combined SO+POS sales
    to compute LastSaleDate per product. A product is Non-Moving if:
      - Qty > 0, AND
      - LastSaleDate is NaT  OR  LastSaleDate < today - non_moving_days

    Returns enriched df_inv plus summary scalars.
    """
    today_dt  = pd.to_datetime(datetime.today().date())
    nm_cutoff = today_dt - timedelta(days=non_moving_days)
    lkb_start = today_dt - timedelta(days=NM_LOOKBACK_DAYS)

    if not df_sales_full.empty:
        recent = df_sales_full[df_sales_full["Date"] >= lkb_start]
        ls     = recent.groupby("PID")["Date"].max().reset_index(name="LastSaleDate")
        df_inv = df_inv.merge(ls, on="PID", how="left")
    else:
        df_inv["LastSaleDate"] = pd.NaT

    # Only in-stock items can be non-moving
    mask = df_inv["Qty"] > 0
    df_inv["NonMoving"] = False
    df_inv.loc[mask, "NonMoving"] = (
        df_inv.loc[mask, "LastSaleDate"].isna() |
        (df_inv.loc[mask, "LastSaleDate"] < nm_cutoff)
    )

    has_val     = df_inv["Value"] > 0
    nm_mask     = df_inv["NonMoving"] & has_val
    tot_val     = df_inv.loc[has_val,  "Value"].sum()
    nm_val      = df_inv.loc[nm_mask,  "Value"].sum()
    nm_pct      = round((nm_val / tot_val * 100) if tot_val else 0, 2)

    sold        = ~df_inv["LastSaleDate"].isna() & has_val
    nm_sold     = df_inv[sold & df_inv["NonMoving"]]["Value"].sum()
    tot_sold    = df_inv[sold]["Value"].sum()
    nm_pct_sold = round((nm_sold / tot_sold * 100) if tot_sold else 0, 2)

    ns_df  = df_inv[df_inv["LastSaleDate"].isna() & has_val]
    return df_inv, nm_pct, nm_val, nm_pct_sold, ns_df["Value"].sum(), len(ns_df)


# ═════════════════════════════════════════════════════════════════════════════
# CSV-9  PSI VIEW  (Purchase / Sales / Inventory join)
# ═════════════════════════════════════════════════════════════════════════════

def build_psi_view(df_pur: pd.DataFrame,
                   df_sales: pd.DataFrame,
                   df_inv: pd.DataFrame) -> pd.DataFrame:
    """CSV-9: Per-product join of purchases, sales and current inventory."""
    pur_agg = (df_pur.groupby("PID", as_index=False)
               .agg(PurQty=("Qty","sum"), PurValue=("Amount","sum"))
               if not df_pur.empty
               else pd.DataFrame(columns=["PID","PurQty","PurValue"]))

    sal_agg = (df_sales.groupby("PID", as_index=False)
               .agg(SalesQty=("Qty","sum"), SalesValue=("Amount","sum"))
               if not df_sales.empty
               else pd.DataFrame(columns=["PID","SalesQty","SalesValue"]))

    keep = ["PID","Product","Brand","Category","Qty","Value","NonMoving"]
    keep = [c for c in keep if c in df_inv.columns]
    inv_sub = (df_inv[keep]
               .rename(columns={"Qty":"StockQty","Value":"StockValue"}))

    df = (inv_sub
          .merge(pur_agg, on="PID", how="left")
          .merge(sal_agg, on="PID", how="left"))
    for col in ("PurQty","PurValue","SalesQty","SalesValue"):
        df[col] = df[col].fillna(0)
    df["NonMoving"] = df["NonMoving"].fillna(False)

    df["SellThrough"] = np.where(
        df["PurQty"] > 0,
        (df["SalesQty"] / df["PurQty"] * 100).clip(upper=999),
        np.nan)
    df["NM_Qty"]   = np.where(df["NonMoving"], df["StockQty"],   0)
    df["NM_Value"] = np.where(df["NonMoving"], df["StockValue"], 0)
    return df


def aggregate_by_dim(df_psi: pd.DataFrame, dim: str) -> pd.DataFrame:
    """Roll up PSI view by Brand or Category."""
    if df_psi.empty or dim not in df_psi.columns:
        return pd.DataFrame()
    grp = (df_psi.groupby(dim, as_index=False)
           .agg(PurQty    =("PurQty",    "sum"),
                PurValue  =("PurValue",  "sum"),
                SalesQty  =("SalesQty",  "sum"),
                SalesValue=("SalesValue","sum"),
                StockQty  =("StockQty",  "sum"),
                StockValue=("StockValue","sum"),
                NM_Qty    =("NM_Qty",    "sum"),
                NM_Value  =("NM_Value",  "sum")))
    grp["SellThrough"] = np.where(
        grp["PurQty"] > 0,
        (grp["SalesQty"] / grp["PurQty"] * 100).clip(upper=999),
        np.nan)
    grp["NM_Pct"] = np.where(
        grp["StockValue"] > 0,
        grp["NM_Value"] / grp["StockValue"] * 100, 0)
    return grp.sort_values("StockValue", ascending=False)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE DATA LOADER  (parallel + lazy + progress-bar)
# ═════════════════════════════════════════════════════════════════════════════

def _ensure_nm_sales(uid, key, full_history, from_date, to_date, df_sales):
    """Guarantee we have at least NM_LOOKBACK_DAYS of sales for NM computation."""
    today_dt  = pd.to_datetime(datetime.today().date())
    lkb_start = today_dt - timedelta(days=NM_LOOKBACK_DAYS)
    if not df_sales.empty and df_sales["Date"].min() <= lkb_start:
        return df_sales
    lkb_from = today_dt.date() - timedelta(days=NM_LOOKBACK_DAYS)
    so_lkb   = load_sal(uid, key, False, lkb_from, today_dt.date())
    pos_lkb  = load_pos_sales(uid, key, False, lkb_from, today_dt.date())
    return pd.concat([so_lkb, pos_lkb], ignore_index=True)


def _build_ageing(df_inv, uid, key, from_date, to_date):
    today_dt = pd.to_datetime(datetime.today().date())
    pur_full = load_pur(uid, key, True, from_date, to_date)
    if not pur_full.empty:
        fi     = pur_full.groupby("PID")["Date"].min().reset_index(name="FirstInDate")
        df_inv = df_inv.merge(fi, on="PID", how="left")
    else:
        df_inv["FirstInDate"] = pd.NaT
    df_inv["DaysInStock"] = (
        (today_dt - df_inv["FirstInDate"]).dt.days
        .where(df_inv["Qty"] > 0, np.nan))
    return df_inv


def load_page_data(uid, key, full_history, from_date, to_date,
                   non_moving_days, page, prog):
    ss_k   = _ss_key(uid, full_history, from_date, to_date, non_moving_days, page)
    cached = _ss_get(ss_k)
    if cached is not None:
        prog.progress(100, text="✅ Loaded from cache (instant)")
        return cached

    prog.progress(5, text="🔗 Connecting to Odoo…")

    # ── Branch Sales page ─────────────────────────────────────────────────────
    if page == "🏢 Branch Sales":
        with ThreadPoolExecutor(max_workers=3) as pool:
            f_br   = pool.submit(load_branch_sales,   uid, key, full_history, from_date, to_date)
            f_prod = pool.submit(load_products,        uid, key)
            f_wh   = pool.submit(load_warehouse_stock, uid, key)
            prog.progress(30, text="📡 Branch SO+POS + products + WH stock…")
            df_br          = f_br.result()
            df_prod        = f_prod.result()
            df_wh_long, _  = f_wh.result()

        df_br = normalize_product(df_br, df_prod)   # CSV-7
        if not df_br.empty:
            mv    = df_br.groupby("PID")["Qty"].sum()
            df_br = df_br[df_br["PID"].isin(mv[mv > 0].index)]
        prog.progress(100, text="✅ Branch data ready")
        result = {"branch": df_br, "products": df_prod, "wh_long": df_wh_long}
        _ss_put(ss_k, result); return result

    # ── Purchase page ─────────────────────────────────────────────────────────
    if page == "🏪 Purchase":
        with ThreadPoolExecutor(max_workers=5) as pool:
            f_prod = pool.submit(load_products,        uid, key)
            f_pur  = pool.submit(load_pur,             uid, key, full_history, from_date, to_date)
            f_so   = pool.submit(load_sal,             uid, key, full_history, from_date, to_date)
            f_pos  = pool.submit(load_pos_sales,       uid, key, full_history, from_date, to_date)
            f_wh   = pool.submit(load_warehouse_stock, uid, key)
            prog.progress(30, text="📡 Products + purchases + sales + WH stock…")
            df_prod          = f_prod.result()
            df_pur           = f_pur.result()
            df_so            = f_so.result()
            df_pos           = f_pos.result()
            df_wh_long, _    = f_wh.result()

        df_pur   = normalize_product(df_pur,   df_prod)   # CSV-7
        df_sales = pd.concat([df_so, df_pos], ignore_index=True)
        df_sales = normalize_product(df_sales, df_prod)

        df_inv = df_prod.copy()
        df_nm  = _ensure_nm_sales(uid, key, full_history, from_date, to_date, df_sales)
        df_inv, nm_pct, nm_val, nm_ps, ns_val, ns_cnt = _compute_non_moving(
            df_inv, df_nm, non_moving_days)
        df_psi = build_psi_view(df_pur, df_sales, df_inv)

        prog.progress(100, text="✅ Purchase data ready")
        result = {"products": df_prod, "purchases": df_pur, "sales": df_sales,
                  "inventory": df_inv, "wh_long": df_wh_long, "psi": df_psi,
                  "nm_pct": nm_pct, "nonmoving_pct": nm_pct}
        _ss_put(ss_k, result); return result

    # ── Sales page ────────────────────────────────────────────────────────────
    if page == "🛒 Sales":
        with ThreadPoolExecutor(max_workers=3) as pool:
            f_so   = pool.submit(load_sal,       uid, key, full_history, from_date, to_date)
            f_pos  = pool.submit(load_pos_sales, uid, key, full_history, from_date, to_date)
            f_prod = pool.submit(load_products,  uid, key)
            prog.progress(30, text="📡 SO + POS + Products…")
            df_so   = f_so.result()
            df_pos  = f_pos.result()
            df_prod = f_prod.result()
        df_sales = pd.concat([df_so, df_pos], ignore_index=True)
        df_sales = normalize_product(df_sales, df_prod)
        prog.progress(100, text="✅ Sales data ready")
        result = {"sales": df_sales, "products": df_prod}
        _ss_put(ss_k, result); return result

    # ── Inventory page ────────────────────────────────────────────────────────
    if page == "📦 Inventory":
        prog.progress(8, text="📡 Launching 5 parallel fetches…")
        with ThreadPoolExecutor(max_workers=5) as pool:
            f_prod = pool.submit(load_products,        uid, key)
            f_so   = pool.submit(load_sal,             uid, key, full_history, from_date, to_date)
            f_pos  = pool.submit(load_pos_sales,       uid, key, full_history, from_date, to_date)
            f_pur  = pool.submit(load_pur,             uid, key, full_history, from_date, to_date)
            f_wh   = pool.submit(load_warehouse_stock, uid, key)
            names  = {f_prod:"Products", f_so:"SO", f_pos:"POS",
                      f_pur:"Purchases", f_wh:"WH stock"}
            done, res = 0, {}
            for fut in as_completed([f_prod, f_so, f_pos, f_pur, f_wh]):
                done += 1
                prog.progress(8 + int(done/5*45),
                              text=f"✅ {names[fut]} loaded ({done}/5)")
                res[fut] = fut.result()

        df_prod = res[f_prod];  df_so = res[f_so];  df_pos = res[f_pos]
        df_pur  = res[f_pur];   df_wh_long, df_wh_pivot = res[f_wh]

        df_sales = normalize_product(pd.concat([df_so, df_pos], ignore_index=True), df_prod)
        df_pur   = normalize_product(df_pur, df_prod)

        df_inv = df_prod.copy()
        prog.progress(56, text="🔧 Non-moving + ageing…")
        df_nm  = _ensure_nm_sales(uid, key, full_history, from_date, to_date, df_sales)
        df_inv, nm_pct, nm_val, nm_ps, ns_val, ns_cnt = _compute_non_moving(
            df_inv, df_nm, non_moving_days)
        df_inv  = _build_ageing(df_inv, uid, key, from_date, to_date)
        tot_val = df_inv.loc[df_inv["Value"] > 0, "Value"].sum()
        df_psi  = build_psi_view(df_pur, df_sales, df_inv)
        prog.progress(100, text="✅ All data ready")
        result = {
            "products": df_prod, "inventory": df_inv,
            "sales": df_sales,   "purchases": df_pur,
            "nonmoving_pct": nm_pct, "total_products": len(df_inv),
            "total_value": tot_val,  "nm_value": nm_val,
            "never_sold_value": ns_val, "never_sold_count": ns_cnt,
            "nm_pct_sold": nm_ps,
            "wh_long": df_wh_long, "wh_pivot": df_wh_pivot,
            "psi": df_psi,
        }
        _ss_put(ss_k, result); return result

    # ── All other pages (Category, Brand, Combined, Power BI) ─────────────────
    prog.progress(8, text="📡 Launching 4 parallel fetches…")
    with ThreadPoolExecutor(max_workers=4) as pool:
        f_prod = pool.submit(load_products,  uid, key)
        f_so   = pool.submit(load_sal,       uid, key, full_history, from_date, to_date)
        f_pos  = pool.submit(load_pos_sales, uid, key, full_history, from_date, to_date)
        f_pur  = pool.submit(load_pur,       uid, key, full_history, from_date, to_date)
        names  = {f_prod:"Products", f_so:"SO", f_pos:"POS", f_pur:"Purchases"}
        done, res = 0, {}
        for fut in as_completed([f_prod, f_so, f_pos, f_pur]):
            done += 1
            prog.progress(8 + int(done/4*55),
                          text=f"✅ {names[fut]} loaded ({done}/4)")
            res[fut] = fut.result()

    df_prod = res[f_prod];  df_pur = res[f_pur]
    df_sales = normalize_product(
        pd.concat([res[f_so], res[f_pos]], ignore_index=True), df_prod)
    df_pur   = normalize_product(df_pur, df_prod)

    df_inv = df_prod.copy()
    prog.progress(66, text="🔧 Non-moving…")
    df_nm  = _ensure_nm_sales(uid, key, full_history, from_date, to_date, df_sales)
    df_inv, nm_pct, nm_val, nm_ps, ns_val, ns_cnt = _compute_non_moving(
        df_inv, df_nm, non_moving_days)
    df_inv  = _build_ageing(df_inv, uid, key, from_date, to_date)
    tot_val = df_inv.loc[df_inv["Value"] > 0, "Value"].sum()
    df_psi  = build_psi_view(df_pur, df_sales, df_inv)
    prog.progress(100, text="✅ All data ready")
    result = {
        "products": df_prod, "inventory": df_inv,
        "sales": df_sales,   "purchases": df_pur,
        "nonmoving_pct": nm_pct, "total_products": len(df_inv),
        "total_value": tot_val,  "nm_value": nm_val,
        "never_sold_value": ns_val, "never_sold_count": ns_cnt,
        "nm_pct_sold": nm_ps,
        "wh_long": pd.DataFrame(), "wh_pivot": pd.DataFrame(),
        "psi": df_psi,
    }
    _ss_put(ss_k, result); return result


# ═════════════════════════════════════════════════════════════════════════════
# UTILITIES
# ═════════════════════════════════════════════════════════════════════════════

def get_validation_checks(df_inv):
    return {
        "Negative Cost"      : df_inv[df_inv["Cost"] < 0],
        "Zero Cost with Qty" : df_inv[(df_inv["Cost"] == 0) & (df_inv["Qty"] > 0)],
        "High Cost Outliers" : (df_inv[df_inv["Cost"] > df_inv["Cost"].quantile(0.99)]
                                if not df_inv.empty else pd.DataFrame()),
    }

def to_excel(dfs: dict) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, df in dfs.items():
            df.to_excel(w, sheet_name=name[:31], index=False)
    return buf.getvalue()

def to_excel_idx(dfs_flat: dict, dfs_idx: dict | None = None) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, df in dfs_flat.items():
            df.to_excel(w, sheet_name=name[:31], index=False)
        if dfs_idx:
            for name, df in dfs_idx.items():
                df.to_excel(w, sheet_name=name[:31], index=True)
    return buf.getvalue()

def _money(label="SAR"):  return st.column_config.NumberColumn(label, format="%.0f")
def _qty(label="Qty"):    return st.column_config.NumberColumn(label, format="%d")
def _pct(label="%"):      return st.column_config.NumberColumn(label, format="%.1f%%")
def _dt(label="Date"):    return st.column_config.DatetimeColumn(label, format="DD MMM YYYY")
def _price(label="Price"):return st.column_config.NumberColumn(label, format="%.2f")

def kpi(title, value, sub=""):
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">{title}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-sub">{sub}</div></div>',
        unsafe_allow_html=True)

def _psi_col_cfg():
    return {
        "PurQty"     : _qty("Pur Qty"),
        "PurValue"   : _money("Pur Value"),
        "SalesQty"   : _qty("Sales Qty"),
        "SalesValue" : _money("Sales Value"),
        "StockQty"   : _qty("Stock Qty"),
        "StockValue" : _money("Stock Value"),
        "NM_Qty"     : _qty("NM Qty"),
        "NM_Value"   : _money("NM Value"),
        "SellThrough": _pct("Sell-Through %"),
        "NM_Pct"     : _pct("NM %"),
    }

def _multiselect_filter(df, col, label, key):
    """Sidebar-style multi-value filter returning filtered df."""
    vals = sorted(df[col].dropna().unique().tolist())
    sel  = st.selectbox(label, ["All"] + vals, key=key)
    return df if sel == "All" else df[df[col] == sel]


# ═════════════════════════════════════════════════════════════════════════════
# LOGIN
# ═════════════════════════════════════════════════════════════════════════════

for _sk, _sv in {"uid": None, "api_key": None, "uname": None}.items():
    if _sk not in st.session_state:
        st.session_state[_sk] = _sv

def login_page():
    st.markdown(
        "<div style='text-align:center;padding:40px 0 20px'>"
        "<h1 style='color:#d4af37'>👗 Outfit Dashboard</h1>"
        "<p style='color:#a9a9a9'>Live Odoo insights for Outfit Company</p>"
        "</div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        with st.container(border=True):
            st.markdown("#### 🔗 Connect to Odoo")
            st.text_input("URL",      value=ODOO_URL, disabled=True)
            st.text_input("Database", value=ODOO_DB,  disabled=True)
            user = st.text_input("Email",   placeholder="your@email.com")
            apik = st.text_input("API Key", type="password",
                                 placeholder="Settings → API Keys → New")
            if st.button("Connect", type="primary", use_container_width=True):
                if not user or not apik:
                    st.error("Email and API Key required")
                else:
                    with st.spinner("Connecting…"):
                        try:
                            uid = odoo_login(user, apik)
                            st.session_state.uid     = uid
                            st.session_state.api_key = apik
                            st.session_state.uname   = user
                            st.rerun()
                        except Exception as e:
                            st.error(f"Connection failed: {e}")
        st.caption("API Key: Odoo → Preferences → Account Security → API Keys → New")


# ═════════════════════════════════════════════════════════════════════════════
# DASHBOARD SHELL
# ═════════════════════════════════════════════════════════════════════════════

def dashboard():
    uid = st.session_state.uid
    key = st.session_state.api_key

    st.markdown("""
    <div style="text-align:center;padding:12px;
    background:linear-gradient(90deg,#1a1a1a,#d4af37,#1a1a1a);
    border-radius:15px;margin-bottom:20px;box-shadow:0 0 20px rgba(212,175,55,.3);">
    <h2 style="color:#000;margin:0;font-size:1.1rem;">
    👗 Outfit Company – Live Odoo Insights</h2></div>""", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown(f"### 👗 Outfit Company\n👤 {st.session_state.uname}")
        st.divider()
        page = st.radio("Navigation", [
            "📦 Inventory", "🛒 Sales", "🏪 Purchase",
            "📁 Category", "🏷️ Brand", "📊 Combined",
            "🏢 Branch Sales", "💼 Power BI",
        ])
        st.divider()
        from_date       = st.date_input("From Date",
                                        value=datetime.today().date() - timedelta(days=90))
        to_date         = st.date_input("To Date", value=datetime.today().date())
        full_history    = st.toggle("Full History", value=False)
        non_moving_days = st.selectbox("Non-Moving Days", [30, 60, 90, 180], index=2)
        debug           = st.toggle("Debug Mode", value=False)

        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            for sk in [k for k in st.session_state if k.startswith("df|")]:
                del st.session_state[sk]
            st.rerun()
        if st.button("Logout", use_container_width=True):
            st.session_state.uid = st.session_state.api_key = None
            st.rerun()

    date_info = "Full History" if full_history else f"{from_date} → {to_date}"
    if not full_history and (to_date - from_date).days < 30:
        st.warning("Selected range < 30 days – some KPIs may be misleading.")

    prog = st.progress(0, text="⏳ Initialising…")
    try:
        data = load_page_data(uid, key, full_history, from_date, to_date,
                              non_moving_days, page, prog)
    except Exception as e:
        prog.empty()
        st.error(f"Data load failed: {e}")
        st.stop()
    prog.empty()

    if   page == "📦 Inventory":    page_inventory(data, date_info, debug, non_moving_days)
    elif page == "🛒 Sales":        page_sales(data, date_info)
    elif page == "🏪 Purchase":     page_purchase(data, date_info)
    elif page == "📁 Category":     page_category(data, date_info)
    elif page == "🏷️ Brand":       page_brand(data, date_info)
    elif page == "📊 Combined":     page_combined(data, date_info)
    elif page == "🏢 Branch Sales": page_branch_sales(data, date_info)
    elif page == "💼 Power BI":     page_powerbi(data)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: INVENTORY
# ═════════════════════════════════════════════════════════════════════════════

def page_inventory(data, date_info, debug, non_moving_days):
    df_inv      = data["inventory"]
    df_sal      = data["sales"]
    df_pur      = data["purchases"]
    nm_pct      = data["nonmoving_pct"]
    nm_val      = data["nm_value"]
    ns_val      = data["never_sold_value"]
    ns_cnt      = data["never_sold_count"]
    nm_ps       = data["nm_pct_sold"]
    df_wh_long  = data.get("wh_long",  pd.DataFrame())
    df_wh_pivot = data.get("wh_pivot", pd.DataFrame())

    st.markdown(f"### 👗 Outfit Inventory Overview ({date_info})")
    st.caption(
        f"ℹ️ Non-moving = in stock AND no sale in the last **{NM_LOOKBACK_DAYS} days** "
        f"(lookback) or within the last **{non_moving_days} days** (threshold).")

    if debug:
        st.info(f"Products: {data['total_products']:,} | "
                f"Value: {data['total_value']:,.0f} | NM value: {nm_val:,.0f}")

    sv = df_inv.Value.sum()
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    with c1: kpi("TOTAL STYLES",  f"{data['total_products']:,}", "Stockable")
    with c2: kpi("IN STOCK (OK)", f"{(df_inv.Status=='OK').sum():,}", "Healthy")
    with c3: kpi("LOW STOCK",     f"{(df_inv.Status=='LOW').sum():,}", f"≤{LOW_THRESHOLD}")
    with c4: kpi("OUT OF STOCK",  f"{(df_inv.Status=='OUT').sum():,}", "Zero")
    with c5: kpi("TOTAL VALUE",   f"{sv:,.0f}", "SAR")
    with c6: kpi("NON MOVING %",  f"{nm_pct}%", f"Last {NM_LOOKBACK_DAYS}d lookback")

    col1, col2 = st.columns(2)
    with col1:
        sc = df_inv.Status.value_counts().reset_index()
        sc.columns = ["Status","Count"]
        st.plotly_chart(
            px.pie(sc, names="Status", values="Count", color="Status",
                   color_discrete_map=STATUS_COLORS, hole=0.4, title="Stock Status"),
            use_container_width=True)
    with col2:
        t10 = df_inv.nlargest(10,"Value")
        fig = px.bar(t10, x="Value", y="Product", orientation="h",
                     color="Status", color_discrete_map=STATUS_COLORS,
                     title="Top 10 Styles by Value")
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    # ── Stock by BranchCode ───────────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("🏬 Stock by Branch / Warehouse")
    if df_wh_long.empty:
        st.info("No warehouse stock data. Check stock.quant access.")
    else:
        bc_totals = (df_wh_long.groupby("BranchCode")
                     .agg(Qty=("Qty","sum"), Value=("Value","sum"))
                     .sort_values("Value", ascending=False))
        kpi_cols = st.columns(min(len(bc_totals), 6))
        for i, (bc, row_bc) in enumerate(bc_totals.iterrows()):
            if i >= len(kpi_cols): break
            with kpi_cols[i % len(kpi_cols)]:
                kpi(bc, f"{row_bc['Qty']:,.0f} pcs", f"{row_bc['Value']:,.0f} SAR")

        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(
                px.bar(bc_totals.reset_index(), x="BranchCode", y="Qty",
                       title="Units on Hand by Branch",
                       color="Qty", color_continuous_scale=_GOLD_SCALE)
                .update_layout(coloraxis_showscale=False, xaxis_tickangle=-45),
                use_container_width=True)
        with col_b:
            st.plotly_chart(
                px.pie(bc_totals.reset_index(), names="BranchCode", values="Value",
                       title="Stock Value Share by Branch", hole=0.4),
                use_container_width=True)

        sel_bc = st.selectbox("Drill-down Branch",
                              ["All Branches"] + sorted(df_wh_long["BranchCode"].unique().tolist()),
                              key="inv_bc_sel")
        df_drill = df_wh_long if sel_bc == "All Branches" \
                   else df_wh_long[df_wh_long["BranchCode"] == sel_bc]
        df_drill_agg = (df_drill.groupby(["PID","Product","BranchCode"], as_index=False)
                        .agg(Qty=("Qty","sum"), Value=("Value","sum"))
                        .sort_values("Value", ascending=False))
        st.caption(f"{len(df_drill_agg):,} rows | "
                   f"Total: {df_drill_agg['Qty'].sum():,.0f} pcs, "
                   f"{df_drill_agg['Value'].sum():,.0f} SAR")
        st.dataframe(df_drill_agg.drop(columns=["PID"]),
                     use_container_width=True,
                     column_config={"Qty":_qty("On Hand"),"Value":_money("Value SAR")})

        if not df_wh_pivot.empty:
            st.markdown("##### Product × Branch pivot (Qty)")
            st.dataframe(df_wh_pivot.drop(columns=["PID"], errors="ignore"),
                         use_container_width=True)

        st.download_button("📥 Export Branch Stock",
                           to_excel_idx(
                               {"WH_Detail": df_wh_long.drop(columns=["PID"],errors="ignore")},
                               {"WH_Pivot": (df_wh_pivot.drop(columns=["PID"],errors="ignore")
                                             .set_index("Product")
                                             if "Product" in df_wh_pivot.columns
                                             else df_wh_pivot)}),
                           "branch_stock.xlsx")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Low Stock ─────────────────────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Low Stock Alert")
    low_df = df_inv[df_inv.Status.isin(["LOW","OUT"])].sort_values("Qty").head(50)
    if low_df.empty:
        st.info("No low / out-of-stock styles.")
    else:
        st.dataframe(low_df.drop(columns=["PID"]), use_container_width=True,
                     column_config={"Qty":_qty("On Hand"),"Value":_money(),"Cost":_money()})
        st.download_button("Export Low Stock",
                           to_excel({"Low_Stock": low_df.drop(columns=["PID"])}),
                           "low_stock.xlsx")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Stock Ageing ──────────────────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Stock Ageing")
    if "DaysInStock" in df_inv.columns:
        df_inv["AgeBucket"] = pd.cut(df_inv["DaysInStock"],
                                     bins=[0,90,180,365,np.inf],
                                     labels=["0-90","91-180","181-365","365+"])
        age = (df_inv.groupby("AgeBucket", observed=True)
               .agg(Count=("PID","count"), Value=("Value","sum")).reset_index())
        st.plotly_chart(px.bar(age, x="AgeBucket", y="Value",
                               title="Stock Value by Age Bucket"),
                        use_container_width=True)
        st.dataframe(age, use_container_width=True,
                     column_config={"Value":_money("Value SAR")})
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Full Inventory table ──────────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Full Inventory")
    fc = st.columns([2,1,1,1,1,1])
    with fc[0]: srch    = st.text_input("Search Ref / Style")
    with fc[1]: fstat   = st.selectbox("Status",   ["All","OK","LOW","OUT"])
    with fc[2]: fcat    = st.selectbox("Category", ["All"]+sorted(df_inv.Category.unique().tolist()))
    with fc[3]: fbrd    = st.selectbox("Brand",    ["All"]+sorted(df_inv.Brand.unique().tolist()))
    with fc[4]: fmov    = st.selectbox("Movement", ["All","Moving","Non-Moving"])
    with fc[5]: min_qty = st.number_input("Min Qty", min_value=0, value=0)
    df_f = df_inv.copy()
    if srch:  df_f = df_f[df_f.Product.str.contains(srch,case=False,na=False)|
                          df_f.Ref.str.contains(srch,case=False,na=False)]
    if fstat!="All": df_f=df_f[df_f.Status==fstat]
    if fcat !="All": df_f=df_f[df_f.Category==fcat]
    if fbrd !="All": df_f=df_f[df_f.Brand==fbrd]
    if fmov=="Non-Moving": df_f=df_f[df_f.NonMoving]
    elif fmov=="Moving":   df_f=df_f[~df_f.NonMoving]
    df_f = df_f[df_f.Qty >= min_qty]
    st.caption(f"Showing {len(df_f):,} styles")
    st.dataframe(df_f.drop(columns=["PID"]), use_container_width=True,
                 column_config={"Qty":_qty("On Hand"),"Value":_money(),"Cost":_money(),
                                "LastSaleDate":_dt("Last Sale")})
    st.download_button("Export Inventory",
                       to_excel({"Inventory": df_f.drop(columns=["PID"])}),
                       "inventory.xlsx")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Style Detail ──────────────────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Style Detail View")
    if not df_inv.empty:
        opts = [f"{r.Ref} | {r.Product}" for _,r in df_inv.iterrows()]
        sel  = st.selectbox("Select Style", opts)
        row  = df_inv[(df_inv["Ref"]+' | '+df_inv["Product"]) == sel].iloc[0]
        today_dt = pd.to_datetime(datetime.today().date())
        s12  = df_sal[(df_sal.PID==row.PID)&(df_sal.Date>=today_dt-timedelta(days=365))]
        s6   = s12[s12.Date>=today_dt-timedelta(days=180)].copy()
        monthly = pd.DataFrame()
        if not s6.empty:
            s6["Month"] = s6["Date"].dt.strftime("%Y-%m")
            monthly = s6.groupby("Month").agg(Qty=("Qty","sum"),Amount=("Amount","sum")).reset_index()
        c1,c2,c3,c4 = st.columns(4)
        with c1: st.metric("Current Stock", f"{row.Qty:,}")
        with c2: st.metric("Stock Value",   f"{row.Value:,.0f}")
        with c3: st.metric("Last Sale", row.LastSaleDate.strftime("%d %b %Y")
                            if pd.notna(row.LastSaleDate) else "Never")
        with c4: st.metric("12m Sales",
                            f"{s12.Qty.sum():.0f} pcs / {s12.Amount.sum():,.0f}")
        st.markdown(f"**Status**: <span class='status-pill status-{row.Status}'>{row.Status}</span>",
                    unsafe_allow_html=True)
        if not df_wh_long.empty:
            style_bc = df_wh_long[df_wh_long["PID"] == row.PID]
            if not style_bc.empty:
                st.markdown("**Branch breakdown:**")
                st.dataframe(style_bc[["BranchCode","LocationName","Qty","Value"]],
                             use_container_width=True,
                             column_config={"Qty":_qty(),"Value":_money()})
        st.subheader("Last 6 Months Sales")
        if not monthly.empty:
            st.dataframe(monthly, use_container_width=True,
                         column_config={"Amount":_money(),"Qty":_qty()})
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Non-Moving ────────────────────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Non-Moving Styles")
    nm_df = df_inv[df_inv["NonMoving"]]
    st.caption(f"Styles: {len(nm_df):,} | Value: {nm_val:,.0f} SAR ({nm_pct}%)")
    st.caption(f"NM% (sold styles only): {nm_ps}% | "
               f"Never sold (last {NM_LOOKBACK_DAYS}d): {ns_cnt} styles, {ns_val:,.0f} SAR")
    st.dataframe(nm_df.drop(columns=["PID"]), use_container_width=True,
                 column_config={"Value":_money(),"Qty":_qty()})
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Never Sold ────────────────────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader(f"Top 20 Never-Sold High-Value Styles (last {NM_LOOKBACK_DAYS}d)")
    ns = df_inv[df_inv["LastSaleDate"].isna()].nlargest(20,"Value")
    if ns.empty: st.info("None found.")
    else: st.dataframe(ns.drop(columns=["PID"]), use_container_width=True,
                       column_config={"Value":_money(),"Qty":_qty()})
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Validation ────────────────────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Validation Checks")
    for name, dv in get_validation_checks(df_inv).items():
        st.caption(f"{name}: {len(dv)} items")
        if not dv.empty:
            st.dataframe(dv.drop(columns=["PID"]), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Sell-Through ──────────────────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Sell-Through Rates")
    if not df_sal.empty and not df_pur.empty:
        sq = df_sal.groupby("PID")["Qty"].sum().reset_index(name="SalesQty")
        pq = df_pur.groupby("PID")["Qty"].sum().reset_index(name="PurQty")
        df_st = (df_inv.merge(sq,on="PID",how="left")
                       .merge(pq,on="PID",how="left").fillna(0))
        df_st["OEst"] = (df_st["Qty"]+df_st["SalesQty"]-df_st["PurQty"]).clip(lower=0)
        df_st["ST"]   = np.where((df_st["OEst"]+df_st["PurQty"])>0,
                                  df_st["SalesQty"]/(df_st["OEst"]+df_st["PurQty"])*100, 0)
        c1,c2 = st.columns(2)
        with c1:
            st.subheader("Top Styles")
            st.dataframe(df_st.nlargest(10,"ST")[["Product","ST"]],
                         column_config={"ST":_pct("Sell-Through %")})
        with c2:
            st.subheader("Bottom Styles")
            st.dataframe(df_st.nsmallest(10,"ST")[["Product","ST"]],
                         column_config={"ST":_pct("Sell-Through %")})
    else:
        st.info("Insufficient data.")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Trend ─────────────────────────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Sales Trend Over Time")
    if not df_sal.empty:
        ts = (df_sal.groupby(df_sal["Date"].dt.date)["Amount"]
              .sum().reset_index(name="Amount").sort_values("Date"))
        ts["MA7"]  = ts["Amount"].rolling(7,  min_periods=1).mean()
        ts["MA30"] = ts["Amount"].rolling(30, min_periods=1).mean()
        st.plotly_chart(
            px.line(ts, x="Date", y=["Amount","MA7","MA30"],
                    title="Daily Sales (SAR) with Moving Averages",
                    render_mode="webgl"),
            use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: SALES
# ═════════════════════════════════════════════════════════════════════════════

def page_sales(data, date_info):
    df_s = data["sales"]
    st.markdown(f"### 🛒 Outfit Sales Analysis ({date_info})")
    if df_s.empty:
        st.warning("No sales data."); return

    c1,c2,c3 = st.columns(3)
    with c1: ch = st.selectbox("Channel",  ["Both","SO","POS"])
    with c2: cf = st.selectbox("Category", ["All"]+sorted(df_s.Category.dropna().unique().tolist()))
    with c3: bf = st.selectbox("Brand",    ["All"]+sorted(df_s.Brand.dropna().unique().tolist()))
    if ch!="Both": df_s=df_s[df_s.Source==ch]
    if cf!="All":  df_s=df_s[df_s.Category==cf]
    if bf!="All":  df_s=df_s[df_s.Brand==bf]

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: kpi("TOTAL SALES",    f"{df_s.Amount.sum():,.0f}", "SAR")
    with c2: kpi("UNITS SOLD",     f"{df_s.Qty.sum():,.0f}",   "pcs")
    with c3: kpi("AVG BILL",
                 f"{df_s.groupby('OrderID')['Amount'].sum().mean():,.0f}", "SAR/order")
    with c4: kpi("SO SALES",  f"{df_s[df_s.Source=='SO']['Amount'].sum():,.0f}",  "SAR")
    with c5: kpi("POS SALES", f"{df_s[df_s.Source=='POS']['Amount'].sum():,.0f}", "SAR")

    col1,col2 = st.columns(2)
    with col1:
        t20 = (df_s.groupby(["PID","Product"])
               .agg(Amount=("Amount","sum"), Qty=("Qty","sum"),
                    UnitPrice=("UnitPrice","mean"), NetPrice=("NetPrice","mean"))
               .nlargest(20,"Amount").reset_index())
        st.plotly_chart(
            px.bar(t20, x="Amount", y="Product", orientation="h",
                   title="Top 20 Styles by Revenue")
            .update_layout(yaxis=dict(autorange="reversed")),
            use_container_width=True)
        st.dataframe(t20[["Product","Qty","Amount","UnitPrice","NetPrice"]],
                     use_container_width=True,
                     column_config={"Amount":_money("Revenue"),"Qty":_qty(),
                                    "UnitPrice":_price("List Price"),
                                    "NetPrice":_price("Net Price")})
    with col2:
        tb = df_s.groupby("Brand")["Amount"].sum().nlargest(10).reset_index()
        st.plotly_chart(px.bar(tb, x="Amount", y="Brand", title="Top 10 Brands"),
                        use_container_width=True)

    ts = (df_s.groupby(df_s["Date"].dt.date)["Amount"]
          .sum().reset_index(name="Amount").sort_values("Date"))
    st.plotly_chart(px.line(ts, x="Date", y="Amount", title="Daily Sales Trend",
                            render_mode="webgl"),
                    use_container_width=True)
    st.download_button("Export Sales", to_excel({"Sales": df_s}), "sales_export.xlsx")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: PURCHASE  (fully enriched)
# ═════════════════════════════════════════════════════════════════════════════

def page_purchase(data, date_info):
    df_pur   = data["purchases"]
    df_sales = data["sales"]
    df_inv   = data["inventory"]
    df_psi   = data.get("psi", pd.DataFrame())
    df_wh    = data.get("wh_long", pd.DataFrame())

    st.markdown(f"### 🏪 Outfit Purchase Analysis ({date_info})")
    if df_pur.empty:
        st.warning("No purchase data."); return

    c1,c2,c3,c4 = st.columns(4)
    with c1: kpi("TOTAL PURCHASES", f"{df_pur.Amount.sum():,.0f}", "SAR")
    with c2: kpi("UNITS PURCHASED", f"{df_pur.Qty.sum():,.0f}",   "pcs")
    with c3: kpi("SUPPLIERS",       f"{df_pur.Supplier.nunique()}", "Distinct")
    with c4:
        overall_st = df_psi["SalesQty"].sum() / max(df_psi["PurQty"].sum(),1)*100
        kpi("OVERALL SELL-THROUGH", f"{overall_st:.1f}%", "Sales / Purchased")

    col1,col2 = st.columns(2)
    with col1:
        tp = df_pur.groupby(df_pur["Date"].dt.date)["Amount"].sum().reset_index(name="Amount")
        st.plotly_chart(px.line(tp, x="Date", y="Amount",
                                title="Purchases Over Time", render_mode="webgl"),
                        use_container_width=True)
    with col2:
        ts = df_pur.groupby("Supplier")["Amount"].sum().nlargest(10).reset_index()
        st.plotly_chart(px.bar(ts, x="Amount", y="Supplier",
                               title="Top 10 Suppliers"), use_container_width=True)

    # ── Brand × Category PSI table ────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("📊 Brand × Category – Purchase / Sales / Inventory")
    tab_br, tab_cat, tab_prod = st.tabs(["By Brand","By Category","By Product"])
    with tab_br:
        grp = aggregate_by_dim(df_psi, "Brand")
        st.dataframe(grp, use_container_width=True, column_config=_psi_col_cfg())
        st.download_button("📥 Export by Brand",
                           to_excel({"By_Brand": grp}), "pur_by_brand.xlsx")
    with tab_cat:
        grp = aggregate_by_dim(df_psi, "Category")
        st.dataframe(grp, use_container_width=True, column_config=_psi_col_cfg())
        st.download_button("📥 Export by Category",
                           to_excel({"By_Category": grp}), "pur_by_category.xlsx")
    with tab_prod:
        pc = ["Product","Brand","Category",
              "PurQty","PurValue","SalesQty","SalesValue",
              "StockQty","StockValue","NM_Qty","NM_Value","SellThrough"]
        pc = [c for c in pc if c in df_psi.columns]
        st.dataframe(df_psi[pc].sort_values("StockValue", ascending=False),
                     use_container_width=True, column_config=_psi_col_cfg())
        st.download_button("📥 Export by Product",
                           to_excel({"By_Product": df_psi[pc]}), "pur_by_product.xlsx")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Top 10 Sell-Through ───────────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("🏆 Top 10 Purchased Products by Sell-Through %")
    df_top = (df_psi[df_psi["PurQty"] > 0]
              .dropna(subset=["SellThrough"])
              .nlargest(10,"SellThrough"))
    if not df_top.empty:
        st.plotly_chart(
            px.bar(df_top, x="SellThrough", y="Product", orientation="h",
                   title="Top 10 Sell-Through %",
                   color="SellThrough", color_continuous_scale=_GOLD_SCALE)
            .update_layout(yaxis=dict(autorange="reversed"), coloraxis_showscale=False),
            use_container_width=True)
        tc = ["Product","Brand","Category","PurQty","SalesQty","StockQty","SellThrough"]
        tc = [c for c in tc if c in df_top.columns]
        st.dataframe(df_top[tc], use_container_width=True,
                     column_config={"PurQty":_qty(),"SalesQty":_qty(),
                                    "StockQty":_qty(),"SellThrough":_pct()})
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Non-Moving by Brand & Category ────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("🚦 Non-Moving by Brand & Category")
    ne1, ne2 = st.tabs(["By Brand","By Category"])
    for tab, dim in [(ne1,"Brand"),(ne2,"Category")]:
        with tab:
            g = aggregate_by_dim(df_psi, dim)
            if g.empty: st.info("No data."); continue
            gp = g[g["NM_Value"]>0].sort_values("NM_Value",ascending=False)
            ca,cb = st.columns(2)
            with ca:
                st.plotly_chart(
                    px.bar(gp, x=dim, y="NM_Value",
                           title=f"NM Value by {dim}",
                           color="NM_Value", color_continuous_scale=_GOLD_SCALE)
                    .update_layout(coloraxis_showscale=False, xaxis_tickangle=-35),
                    use_container_width=True)
            with cb:
                st.plotly_chart(
                    px.bar(gp, x=dim, y="NM_Pct",
                           title=f"NM % by {dim}",
                           color="NM_Pct", color_continuous_scale=_GOLD_SCALE)
                    .update_layout(coloraxis_showscale=False, xaxis_tickangle=-35),
                    use_container_width=True)
            st.dataframe(g[[dim,"StockValue","NM_Value","NM_Qty","NM_Pct"]],
                         use_container_width=True,
                         column_config={"StockValue":_money(),"NM_Value":_money(),
                                        "NM_Qty":_qty(),"NM_Pct":_pct()})
    st.markdown("</div>", unsafe_allow_html=True)

    # ── WH / Branch Sell-Through ──────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("🏬 Branch / Warehouse Sell-Through")
    if df_wh.empty:
        st.info("No warehouse stock data available.")
    else:
        _render_wh_sellthrough(df_wh, df_psi, df_sales, key_prefix="pur")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Raw lines ─────────────────────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Raw Purchase Lines")
    st.dataframe(df_pur, use_container_width=True,
                 column_config={"Amount":_money(),"Qty":_qty(),"Date":_dt()})
    st.download_button("Export Purchases",
                       to_excel({"Purchases": df_pur}), "purchases.xlsx")
    st.markdown("</div>", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# WH / BRANCH SELL-THROUGH WIDGET  (reusable on Purchase + Branch Sales pages)
# ═════════════════════════════════════════════════════════════════════════════

def _render_wh_sellthrough(df_wh_long, df_psi, df_sales, key_prefix="wh"):
    """
    For each BranchCode:
      StockQty / StockValue — from stock.quant (df_wh_long)
      SalesQty / SalesValue — from df_sales filtered to matching BranchCode
      PurQty                — from df_psi
      UnsoldQty = StockQty  (current remaining)
    """
    branches = sorted(df_wh_long["BranchCode"].unique().tolist())
    sel_bc   = st.selectbox("Select Branch / Warehouse",
                             ["All Branches"] + branches,
                             key=f"{key_prefix}_bc_st_sel")

    # filter stock
    df_stock = df_wh_long if sel_bc=="All Branches" \
               else df_wh_long[df_wh_long["BranchCode"]==sel_bc]
    stock_agg = (df_stock.groupby("PID", as_index=False)
                 .agg(StockQty=("Qty","sum"), StockValue=("Value","sum")))

    # filter sales by BranchCode if present
    sal_col = "BranchCode" if "BranchCode" in df_sales.columns else None
    if sal_col and not df_sales.empty and sel_bc!="All Branches":
        df_sal_wh = df_sales[df_sales[sal_col]==sel_bc]
    else:
        df_sal_wh = df_sales

    sal_agg = (df_sal_wh.groupby("PID", as_index=False)
               .agg(SalesQty=("Qty","sum"), SalesValue=("Amount","sum"))
               if not df_sal_wh.empty
               else pd.DataFrame(columns=["PID","SalesQty","SalesValue"]))

    pur_sub = df_psi[["PID","Product","Brand","Category","PurQty","PurValue"]].copy()

    df_view = (pur_sub
               .merge(stock_agg, on="PID", how="outer")
               .merge(sal_agg,   on="PID", how="left"))
    for c in ("PurQty","StockQty","StockValue","SalesQty","SalesValue"):
        df_view[c] = df_view[c].fillna(0)
    df_view["UnsoldQty"]   = df_view["StockQty"]
    df_view["UnsoldValue"] = df_view["StockValue"]
    df_view["SellThrough"] = np.where(
        df_view["PurQty"] > 0,
        (df_view["SalesQty"]/df_view["PurQty"]*100).clip(upper=999),
        np.nan)

    k1,k2,k3,k4 = st.columns(4)
    with k1: kpi("STOCK QTY",   f"{df_view['StockQty'].sum():,.0f}",  "pcs on hand")
    with k2: kpi("STOCK VALUE", f"{df_view['StockValue'].sum():,.0f}", "SAR")
    with k3: kpi("SALES QTY",   f"{df_view['SalesQty'].sum():,.0f}",  "pcs sold")
    with k4:
        st_pct = df_view["SalesQty"].sum()/max(df_view["PurQty"].sum(),1)*100
        kpi("SELL-THROUGH", f"{st_pct:.1f}%", "Sales / Purchased")

    top_u = df_view[df_view["UnsoldValue"]>0].nlargest(10,"UnsoldValue")
    if not top_u.empty:
        ca,cb = st.columns(2)
        with ca:
            st.plotly_chart(
                px.bar(top_u, x="UnsoldValue", y="Product", orientation="h",
                       title="Top 10 Unsold (by Value)",
                       color="UnsoldValue", color_continuous_scale=_GOLD_SCALE)
                .update_layout(yaxis=dict(autorange="reversed"),
                               coloraxis_showscale=False),
                use_container_width=True)
        with cb:
            top_st = df_view[df_view["PurQty"]>0].nlargest(10,"SellThrough")
            st.plotly_chart(
                px.bar(top_st, x="SellThrough", y="Product", orientation="h",
                       title="Top 10 by Sell-Through %",
                       color="SellThrough", color_continuous_scale=_GOLD_SCALE)
                .update_layout(yaxis=dict(autorange="reversed"),
                               coloraxis_showscale=False),
                use_container_width=True)

    vc = ["Product","Brand","Category",
          "PurQty","SalesQty","StockQty","UnsoldQty","UnsoldValue","SellThrough"]
    vc = [c for c in vc if c in df_view.columns]
    df_disp = df_view[vc].sort_values("UnsoldValue", ascending=False)
    st.caption(f"{len(df_disp):,} products | "
               f"Total unsold: {df_view['UnsoldValue'].sum():,.0f} SAR")
    st.dataframe(df_disp, use_container_width=True,
                 column_config={"PurQty":_qty(),"SalesQty":_qty(),"StockQty":_qty(),
                                "UnsoldQty":_qty(),"UnsoldValue":_money(),
                                "SellThrough":_pct()})
    st.download_button("📥 Export",
                       to_excel({"WH_SellThrough": df_disp}),
                       f"wh_st_{sel_bc.replace(' ','_')}.xlsx",
                       key=f"{key_prefix}_wh_dl")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: CATEGORY
# ═════════════════════════════════════════════════════════════════════════════

def page_category(data, date_info):
    df_psi = data.get("psi", pd.DataFrame())
    df_s   = data["sales"]
    st.markdown(f"### 📁 Category Dashboard ({date_info})")
    grp = aggregate_by_dim(df_psi, "Category")
    if grp.empty: st.info("No category data."); return

    col1,col2 = st.columns(2)
    with col1:
        st.plotly_chart(px.bar(grp, x="Category", y="StockValue",
                               title="Stock Value by Category"), use_container_width=True)
    with col2:
        st.plotly_chart(px.pie(grp, names="Category", values="SalesValue",
                               title="Sales by Category"), use_container_width=True)
    col3,col4 = st.columns(2)
    with col3:
        gp = grp[grp["NM_Value"]>0].sort_values("NM_Value",ascending=False)
        st.plotly_chart(
            px.bar(gp, x="Category", y="NM_Value",
                   title="Non-Moving Value by Category",
                   color="NM_Value", color_continuous_scale=_GOLD_SCALE)
            .update_layout(coloraxis_showscale=False, xaxis_tickangle=-35),
            use_container_width=True)
    with col4:
        st.plotly_chart(
            px.bar(grp, x="Category", y="SellThrough",
                   title="Sell-Through % by Category",
                   color="SellThrough", color_continuous_scale=_GOLD_SCALE)
            .update_layout(coloraxis_showscale=False, xaxis_tickangle=-35),
            use_container_width=True)
    st.dataframe(grp, use_container_width=True, column_config=_psi_col_cfg())
    st.download_button("📥 Export", to_excel({"Categories": grp}), "categories.xlsx")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: BRAND
# ═════════════════════════════════════════════════════════════════════════════

def page_brand(data, date_info):
    df_psi = data.get("psi", pd.DataFrame())
    df_s   = data["sales"]
    st.markdown(f"### 🏷️ Brand Dashboard ({date_info})")
    grp = aggregate_by_dim(df_psi, "Brand")
    if grp.empty: st.info("No brand data."); return

    today_dt = pd.to_datetime(datetime.today().date())
    b90 = (df_s[df_s.Date>=today_dt-timedelta(days=90)]
           .groupby("Brand")["Amount"].sum().reset_index(name="Sales_Last90d"))
    grp90 = grp.merge(b90, on="Brand", how="left").fillna(0)

    col1,col2 = st.columns(2)
    with col1:
        st.plotly_chart(px.bar(grp, x="Brand", y="StockValue",
                               title="Stock Value by Brand"), use_container_width=True)
    with col2:
        st.plotly_chart(px.bar(grp90, x="Brand", y="Sales_Last90d",
                               title="Sales Last 90 Days by Brand"),
                        use_container_width=True)
    col3,col4 = st.columns(2)
    with col3:
        gp = grp[grp["NM_Value"]>0].sort_values("NM_Value",ascending=False)
        st.plotly_chart(
            px.bar(gp, x="Brand", y="NM_Value",
                   title="Non-Moving Value by Brand",
                   color="NM_Value", color_continuous_scale=_GOLD_SCALE)
            .update_layout(coloraxis_showscale=False, xaxis_tickangle=-35),
            use_container_width=True)
    with col4:
        st.plotly_chart(
            px.bar(grp, x="Brand", y="SellThrough",
                   title="Sell-Through % by Brand",
                   color="SellThrough", color_continuous_scale=_GOLD_SCALE)
            .update_layout(coloraxis_showscale=False, xaxis_tickangle=-35),
            use_container_width=True)
    st.dataframe(grp, use_container_width=True, column_config=_psi_col_cfg())
    st.download_button("📥 Export", to_excel({"Brands": grp}), "brands.xlsx")


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: COMBINED
# ═════════════════════════════════════════════════════════════════════════════

def page_combined(data, date_info):
    df_inv = data["inventory"]
    df_s   = data["sales"]
    df_pur = data["purchases"]
    df_psi = data.get("psi", pd.DataFrame())
    st.markdown(f"### 📊 Combined Overview ({date_info})")
    sv = df_inv.Value.sum()
    today_dt = pd.to_datetime(datetime.today().date())
    s30 = df_s[df_s.Date>=today_dt-timedelta(days=30)]["Amount"].sum()
    trn = df_s.Amount.sum()/sv if sv else 0
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("Stock Value",       f"{sv:,.0f} SAR")
    with c2: st.metric("Sales Last 30 Days",f"{s30:,.0f} SAR")
    with c3: st.metric("Non-Moving %",      f"{data['nonmoving_pct']}%")
    with c4: st.metric("Turnover",          f"{trn:.2f}x")
    if not df_s.empty or not df_pur.empty:
        st_t = df_s.groupby(df_s["Date"].dt.date)["Amount"].sum().reset_index(name="Sales")
        pt   = df_pur.groupby(df_pur["Date"].dt.date)["Amount"].sum().reset_index(name="Purchases")
        td   = pd.merge(st_t, pt, on="Date", how="outer").fillna(0).sort_values("Date")
        st.plotly_chart(px.line(td, x="Date", y=["Sales","Purchases"],
                                title="Sales vs Purchases", render_mode="webgl"),
                        use_container_width=True)
    if not df_psi.empty:
        st.subheader("PSI Summary")
        t1, t2 = st.tabs(["Brand","Category"])
        with t1: st.dataframe(aggregate_by_dim(df_psi,"Brand"),
                              use_container_width=True, column_config=_psi_col_cfg())
        with t2: st.dataframe(aggregate_by_dim(df_psi,"Category"),
                              use_container_width=True, column_config=_psi_col_cfg())


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: BRANCH SALES  (CSV-3: unified SO+POS with BranchCode)
# ═════════════════════════════════════════════════════════════════════════════

def page_branch_sales(data, date_info):
    df_raw   = data.get("branch",  pd.DataFrame())
    df_psi   = data.get("psi",     pd.DataFrame())
    df_wh    = data.get("wh_long", pd.DataFrame())

    st.markdown(f"### 🏢 Branch Sales Analysis ({date_info})")
    st.caption(
        "Source: sale.order (SO) + pos.order (POS) combined. "
        "Branch codes for SO = warehouse prefix; for POS = order-name prefix.")

    if df_raw.empty:
        st.warning("No branch sales data in the selected period."); return

    # ── Filters ───────────────────────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    fc1,fc2,fc3,fc4,fc5 = st.columns(5)
    with fc1: f_bc  = st.selectbox("BranchCode",
                                   ["All"]+sorted(df_raw.BranchCode.dropna().unique().tolist()),
                                   key="bs_bc")
    with fc2: f_br  = st.selectbox("Branch",
                                   ["All"]+sorted(df_raw.Branch.dropna().unique().tolist()),
                                   key="bs_br")
    with fc3: f_cat = st.selectbox("Category",
                                   ["All"]+sorted(df_raw.Category.dropna().unique().tolist()),
                                   key="bs_cat")
    with fc4: f_brd = st.selectbox("Brand",
                                   ["All"]+sorted(df_raw.Brand.dropna().unique().tolist()),
                                   key="bs_brd")
    with fc5: f_src = st.selectbox("Source", ["All","SO","POS"], key="bs_src")
    st.markdown("</div>", unsafe_allow_html=True)

    df = df_raw.copy()
    if f_bc !="All": df=df[df.BranchCode==f_bc]
    if f_br !="All": df=df[df.Branch==f_br]
    if f_cat!="All": df=df[df.Category==f_cat]
    if f_brd!="All": df=df[df.Brand==f_brd]
    if f_src!="All": df=df[df.Source==f_src]
    if df.empty:
        st.warning("No data after filters."); return

    k1,k2,k3,k4,k5 = st.columns(5)
    with k1: kpi("TOTAL SALES",     f"{df.Amount.sum():,.0f}", "SAR")
    with k2: kpi("UNITS SOLD",      f"{df.Qty.sum():,.0f}",   "pcs")
    with k3: kpi("BRANCHES",        f"{df.BranchCode.nunique()}", "BranchCodes")
    with k4: kpi("UNIQUE PRODUCTS", f"{df.PID.nunique():,}", "Moving Styles")
    with k5:
        kpi("SO / POS",
            f"{df[df.Source=='SO']['Amount'].sum():,.0f} / "
            f"{df[df.Source=='POS']['Amount'].sum():,.0f}", "SAR")

    # ── Sales by BranchCode ───────────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Sales by BranchCode")
    bagg = (df.groupby("BranchCode")
            .agg(Sales_SAR=("Amount","sum"), Units=("Qty","sum"))
            .reset_index().sort_values("Sales_SAR",ascending=False))
    ca,cb = st.columns(2)
    with ca:
        st.plotly_chart(
            px.bar(bagg, x="BranchCode", y="Sales_SAR",
                   title="Revenue (SAR) by BranchCode",
                   color="Sales_SAR", color_continuous_scale=_GOLD_SCALE)
            .update_layout(coloraxis_showscale=False, xaxis_tickangle=-45),
            use_container_width=True)
    with cb:
        st.plotly_chart(
            px.bar(bagg, x="BranchCode", y="Units",
                   title="Units Sold by BranchCode",
                   color="Units", color_continuous_scale=_GOLD_SCALE)
            .update_layout(coloraxis_showscale=False, xaxis_tickangle=-45),
            use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── SO vs POS mix ─────────────────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("SO vs POS Mix by BranchCode")
    src_mix = (df.groupby(["BranchCode","Source"])["Amount"]
               .sum().reset_index(name="Sales_SAR"))
    st.plotly_chart(
        px.bar(src_mix, x="BranchCode", y="Sales_SAR", color="Source",
               barmode="stack", title="SO vs POS Revenue per BranchCode")
        .update_layout(xaxis_tickangle=-45),
        use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Daily trend by BranchCode ─────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Daily Sales Trend by BranchCode")
    daily = (df.groupby([df["Date"].dt.date,"BranchCode"])["Amount"]
             .sum().reset_index(name="Sales_SAR")
             .rename(columns={"Date":"Day"}))
    fig_tr = px.line(daily, x="Day", y="Sales_SAR", color="BranchCode",
                     title="Daily Sales (SAR) per BranchCode",
                     render_mode="webgl")
    fig_tr.update_traces(mode="lines+markers", marker=dict(size=3))
    st.plotly_chart(fig_tr, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Top 20 per BranchCode ─────────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Top 20 Products per BranchCode")
    sel_bc = st.selectbox("Select BranchCode",
                          sorted(df.BranchCode.unique().tolist()), key="bs_dd")
    top20  = (df[df.BranchCode==sel_bc].groupby("Product")
              .agg(Sales_SAR=("Amount","sum"), Units=("Qty","sum"),
                   UnitPrice=("UnitPrice","mean"), NetPrice=("NetPrice","mean"))
              .reset_index().nlargest(20,"Sales_SAR"))
    metric = st.radio("Metric", ["Sales (SAR)","Units"], horizontal=True, key="bs_met")
    yc     = "Sales_SAR" if metric=="Sales (SAR)" else "Units"
    st.plotly_chart(
        px.bar(top20, x=yc, y="Product", orientation="h",
               title=f"Top 20 – {sel_bc} ({metric})",
               color=yc, color_continuous_scale=_GOLD_SCALE)
        .update_layout(yaxis=dict(autorange="reversed"), coloraxis_showscale=False),
        use_container_width=True)
    st.dataframe(top20[["Product","Units","Sales_SAR","UnitPrice","NetPrice"]],
                 use_container_width=True,
                 column_config={"Sales_SAR":_money("Revenue SAR"),"Units":_qty(),
                                "UnitPrice":_price("List Price"),
                                "NetPrice":_price("Net Price")})
    st.markdown("</div>", unsafe_allow_html=True)

    # ── BranchCode × Product pivot ────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("BranchCode × Product Pivot")
    pv_m = st.radio("Pivot Value",["Qty","Amount (SAR)"],horizontal=True,key="bs_pv")
    pv_c = "Qty" if pv_m=="Qty" else "Amount"
    pivot = (df.groupby(["Product","BranchCode"])[pv_c].sum()
             .reset_index()
             .pivot(index="Product", columns="BranchCode", values=pv_c)
             .fillna(0))
    pivot["TOTAL"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("TOTAL",ascending=False)
    st.caption(f"Rows: {len(pivot):,} · Values: {pv_m}")
    st.dataframe(pivot, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── WH Sell-Through (reused widget) ──────────────────────────────────────
    if not df_wh.empty and not df_psi.empty:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("🏬 Branch / Warehouse Sell-Through")
        _render_wh_sellthrough(df_wh, df_psi, df, key_prefix="bs")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Raw + export ──────────────────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Raw Sales Data")
    dcols = ["Date","BranchCode","Branch","Source","Product","Category","Brand",
             "Qty","Amount","UnitPrice","NetPrice","OrderID"]
    dcols = [c for c in dcols if c in df.columns]
    st.dataframe(df[dcols].sort_values("Date",ascending=False),
                 use_container_width=True,
                 column_config={"Date":_dt(),"Qty":_qty(),"Amount":_money(),
                                "UnitPrice":_price(),"NetPrice":_price()})
    st.download_button(
        "📥 Export Branch Sales",
        to_excel_idx(
            {"Raw_Data": df[dcols].sort_values("Date",ascending=False)},
            {"Pivot_BC_Product": pivot.reset_index()}),
        "branch_sales_export.xlsx")
    st.markdown("</div>", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# PAGE: POWER BI
# ═════════════════════════════════════════════════════════════════════════════

def page_powerbi(data):
    df_inv  = data.get("inventory",  pd.DataFrame())
    df_s    = data.get("sales",      pd.DataFrame())
    df_pur  = data.get("purchases",  pd.DataFrame())
    df_wh   = data.get("wh_long",    pd.DataFrame())
    df_br   = data.get("branch",     pd.DataFrame())
    df_psi  = data.get("psi",        pd.DataFrame())

    st.markdown("### 💼 Power BI Export Helper")
    st.markdown("""
**How to use:**  Download a file → Power BI → Get Data → Excel.
All sheets share the **PID** key for relationships.
""")
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.download_button("📦 Inventory",
                                 to_excel({"Inventory": df_inv.drop(columns=["PID"],errors="ignore")}),
                                 "outfit_inventory.xlsx")
    with c2: st.download_button("🛒 Sales",     to_excel({"Sales": df_s}),      "outfit_sales.xlsx")
    with c3: st.download_button("🏪 Purchases", to_excel({"Purchases": df_pur}), "outfit_purchases.xlsx")
    with c4: st.download_button("🏬 WH Stock",
                                 to_excel({"WH_Detail": df_wh.drop(columns=["PID"],errors="ignore")}),
                                 "outfit_wh.xlsx")
    c5,c6 = st.columns(2)
    with c5: st.download_button("🏢 Branch Sales",
                                 to_excel({"Branch_Sales": df_br}),
                                 "outfit_branch_sales.xlsx")
    with c6:
        psi_br  = aggregate_by_dim(df_psi,"Brand")
        psi_cat = aggregate_by_dim(df_psi,"Category")
        st.download_button("📊 PSI Summary",
                           to_excel({"PSI_Brand": psi_br,"PSI_Category": psi_cat}),
                           "outfit_psi.xlsx")

    st.download_button("📁 ALL DATA",
                       to_excel({
                           "Inventory"   : df_inv.drop(columns=["PID"],errors="ignore"),
                           "Sales"       : df_s,
                           "Purchases"   : df_pur,
                           "WH_Detail"   : df_wh.drop(columns=["PID"],errors="ignore"),
                           "Branch_Sales": df_br,
                           "PSI_Brand"   : psi_br,
                           "PSI_Category": psi_cat,
                           "PSI_Product" : df_psi.drop(columns=["PID"],errors="ignore"),
                       }),
                       "outfit_full_export.xlsx")


# ═════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

if st.session_state.get("uid") is None:
    login_page()
else:
    dashboard()
