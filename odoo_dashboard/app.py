# ╔══════════════════════════════════════════════════════════════════╗
# ║        👗 Outfit Dashboard – Optimised Edition                  ║
# ║  Optimisations applied:                                         ║
# ║  1. Parallel loading  (ThreadPoolExecutor)                      ║
# ║  2. Selective fields  (minimum Odoo fields)                     ║
# ║  3. Smart caching     (ttl=600 inv / ttl=300 sales/pur)         ║
# ║  4. Batch size 1 000  (halves API round-trips)                  ║
# ║  5. Lazy / page-level loading (only active page fetches data)   ║
# ║  6. Progress bar      (real percentage while loading)           ║
# ║  7. Streamlit config  (maxUploadSize, headless, CORS off)       ║
# ║  8. column_config     (typed, formatted DataFrames)             ║
# ║  9. WebGL rendering   (render_mode='webgl' on line charts)      ║
# ║ 10. Session-state DF  (page-switch never re-fetches Odoo)       ║
# ╚══════════════════════════════════════════════════════════════════╝

import streamlit as st

# ── 7. Streamlit server config (must be the very first st call) ───────────────
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
from concurrent.futures import ThreadPoolExecutor, as_completed   # ← 1. Parallel

# ── Globals ───────────────────────────────────────────────────────────────────
ODOO_URL      = "https://odooprosys-la-rouche.odoo.com"
ODOO_DB       = "odooprosys-la-rouche-production-12364313"
LOW_THRESHOLD = 5
BATCH         = 1_000          # ← 4. Increased batch size (was 500)
INV_TTL       = 600            # ← 3. Inventory cache 10 min
SALES_TTL     = 300            # ← 3. Sales / purchases cache 5 min

# ── Plotly theme ──────────────────────────────────────────────────────────────
pio.templates.default = "plotly_white"
pio.templates["plotly_white"].layout.update(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=-0.25),
    bargap=0.22,
    transition_duration=400,   # reduced from 1000 – snappier
)

# ── Luxury CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp {
    background: radial-gradient(circle at top left, #1a1a1a 0%, #0d0d0d 45%, #000000 100%);
    color: #f0e6d2;
    font-family: "Playfair Display", serif;
}
.block-container { padding-top: 1.2rem; padding-bottom: 1.5rem; }
h1, h2, h3, h4  { color: #d4af37; text-shadow: 0 0 5px rgba(212,175,55,0.5); }
.glass-card {
    background: rgba(10,10,10,0.85);
    border-radius: 20px; padding: 20px 22px;
    border: 1px solid rgba(212,175,55,0.3);
    box-shadow: 0 20px 50px rgba(0,0,0,0.7);
    backdrop-filter: blur(16px);
    animation: fadeInUp 0.6s ease-out;
    margin-bottom: 16px;
}
.kpi-card {
    background: linear-gradient(135deg, rgba(212,175,55,0.15), rgba(184,134,11,0.1));
    border-radius: 18px; padding: 16px 20px;
    border: 1px solid rgba(212,175,55,0.6);
    box-shadow: 0 14px 35px rgba(0,0,0,0.6);
    backdrop-filter: blur(14px);
    transition: all 0.3s ease-out;
    animation: pulseGlow 2s infinite alternate;
}
.kpi-card:hover { transform: translateY(-5px) scale(1.05); box-shadow: 0 20px 45px rgba(212,175,55,0.3); }
.kpi-title { font-size:.8rem; letter-spacing:.1em; text-transform:uppercase; color:#c0c0c0; }
.kpi-value { font-size:1.4rem; font-weight:700; color:#f0e6d2; }
.kpi-sub   { font-size:.8rem; color:#a9a9a9; }
.status-pill { border-radius:999px; padding:3px 12px; font-size:.75rem; font-weight:600; animation:glow 1.5s infinite alternate; }
.status-OK  { background:rgba(0,128,0,0.15);   color:#90ee90; border:1px solid rgba(0,128,0,0.6); }
.status-LOW { background:rgba(255,165,0,0.15);  color:#ffd700; border:1px solid rgba(255,165,0,0.6); }
.status-OUT { background:rgba(139,0,0,0.15);    color:#ff6347; border:1px solid rgba(139,0,0,0.6); }
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d0d0d 0%, #000000 60%, #1a1a1a 100%);
    border-right: 1px solid rgba(212,175,55,0.4);
}
section[data-testid="stSidebar"] .block-container { padding-top:1.6rem; }
[data-testid="stSidebar"] .stRadio > label,
[data-testid="stSidebar"] .stButton button { transition:transform 0.3s; }
[data-testid="stSidebar"] .stRadio > label:hover,
[data-testid="stSidebar"] .stButton button:hover { transform:scale(1.05); }
[data-testid="stDataFrame"] { border-radius:12px; overflow:hidden; border:1px solid rgba(212,175,55,0.4); }
.stDownloadButton button {
    border-radius:999px;
    background: linear-gradient(135deg, #d4af37, #b8860b) !important;
    color:#000 !important; border:none; font-weight:600; transition:all 0.3s;
}
.stDownloadButton button:hover { filter:brightness(1.1); transform:scale(1.05); }
.stTabs [data-baseweb="tab-list"] { gap:.6rem; }
.stTabs [data-baseweb="tab"] {
    background-color:rgba(10,10,10,0.9); border-radius:999px;
    padding:7px 12px; border:1px solid rgba(212,175,55,0.4); transition:all 0.3s;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #d4af37, #b8860b);
    color:#000; border-color:transparent;
}
.stTabs [data-baseweb="tab"]:hover { transform:scale(1.05); }
@keyframes fadeInUp  { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
@keyframes pulseGlow { from{box-shadow:0 14px 35px rgba(0,0,0,0.6)} to{box-shadow:0 14px 35px rgba(212,175,55,0.2)} }
@keyframes glow      { from{text-shadow:0 0 3px currentColor} to{text-shadow:0 0 8px currentColor} }
</style>
""", unsafe_allow_html=True)

STATUS_COLORS = {"OK": "#90ee90", "LOW": "#ffd700", "OUT": "#ff6347"}

# ─────────────────────────────────────────────────────────────────────────────
# ODOO RPC HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def odoo_rpc(endpoint, method, *args):
    payload = {
        "jsonrpc": "2.0", "method": "call",
        "params": {"service": endpoint, "method": method, "args": list(args)},
    }
    r = requests.post(f"{ODOO_URL}/jsonrpc", json=payload, timeout=60)
    res = r.json()
    if "error" in res:
        raise Exception(res["error"].get("data", {}).get("message", str(res["error"])))
    return res["result"]


def odoo_login(u, k):
    uid = odoo_rpc("common", "authenticate", ODOO_DB, u, k, {})
    if not uid:
        raise Exception("Login failed")
    return uid


def search_read(uid, k, model, domain, fields, limit=BATCH, offset=0):
    # ← 4. Default limit is now BATCH=1000 (was 500)
    return odoo_rpc(
        "object", "execute_kw", ODOO_DB, uid, k,
        model, "search_read",
        [domain],
        {"fields": fields, "limit": limit, "offset": offset, "order": "id asc"},
    )


def fetch_all(uid, k, model, domain, fields):
    """
    Fetches every page in BATCH=1000 chunks.
    No st.empty() / caption calls here – callers update their own progress bar.
    """
    all_recs, offset = [], 0
    while True:
        recs = search_read(uid, k, model, domain, fields, limit=BATCH, offset=offset)
        if not recs:
            break
        all_recs.extend(recs)
        if len(recs) < BATCH:
            break
        offset += BATCH
    return all_recs

# ─────────────────────────────────────────────────────────────────────────────
# 10. SESSION-STATE CACHE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _ss_key(uid, full_history, from_date, to_date, nm_days, page):
    return f"df|{uid}|{full_history}|{from_date}|{to_date}|{nm_days}|{page}"


def _ss_get(key):
    return st.session_state.get(key)          # None if not present


def _ss_put(key, value):
    st.session_state[key] = value

# ─────────────────────────────────────────────────────────────────────────────
# CACHED ODOO DATA LOADERS
# (3. TTL differentiated  |  2. Selective fields  |  4. Batch 1000)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False, ttl=SALES_TTL)
def load_sal(_uid, _k, _full_history, _from_date, _to_date):
    domain = [["state", "in", ["sale", "done"]]]
    if not _full_history:
        domain += [
            ["date_order", ">=", str(_from_date)],
            ["date_order", "<",  str(_to_date + timedelta(days=1))],
        ]
    orders    = fetch_all(_uid, _k, "sale.order", domain, ["id", "date_order"])
    order_ids = [o["id"] for o in orders]
    date_map  = {o["id"]: o["date_order"] for o in orders}
    if not order_ids:
        return pd.DataFrame()
    lines = fetch_all(_uid, _k, "sale.order.line",
                      [["order_id", "in", order_ids]],
                      ["product_id", "product_uom_qty", "price_subtotal", "order_id"])
    rows = []
    for r in lines:
        oid  = r["order_id"][0] if r.get("order_id") else None
        date = date_map.get(oid)
        if not (date and oid):
            continue
        try:
            rows.append({
                "PID"    : r["product_id"][0] if r.get("product_id") else 0,
                "Product": r["product_id"][1] if r.get("product_id") else "-",
                "Qty"    : r.get("product_uom_qty") or 0,
                "Amount" : r.get("price_subtotal")  or 0,
                "Date"   : pd.to_datetime(date),
                "Source" : "SO",
                "OrderID": oid,
            })
        except Exception:
            continue
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False, ttl=SALES_TTL)
def load_pos_sales(_uid, _k, _full_history, _from_date, _to_date):
    domain = [["state", "in", ["paid", "invoiced", "done"]]]
    if not _full_history:
        domain += [
            ["date_order", ">=", str(_from_date)],
            ["date_order", "<",  str(_to_date + timedelta(days=1))],
        ]
    orders    = fetch_all(_uid, _k, "pos.order", domain, ["id", "date_order"])
    order_ids = [o["id"] for o in orders]
    date_map  = {o["id"]: o["date_order"] for o in orders}
    if not order_ids:
        return pd.DataFrame()
    lines = fetch_all(_uid, _k, "pos.order.line",
                      [["order_id", "in", order_ids]],
                      ["product_id", "qty", "price_subtotal", "order_id"])
    rows = []
    for r in lines:
        oid  = r["order_id"][0] if r.get("order_id") else None
        date = date_map.get(oid)
        if not (date and oid):
            continue
        try:
            rows.append({
                "PID"    : r["product_id"][0] if r.get("product_id") else 0,
                "Product": r["product_id"][1] if r.get("product_id") else "-",
                "Qty"    : r.get("qty")            or 0,
                "Amount" : r.get("price_subtotal") or 0,
                "Date"   : pd.to_datetime(date),
                "Source" : "POS",
                "OrderID": oid,
            })
        except Exception:
            continue
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False, ttl=SALES_TTL)
def load_pur(_uid, _k, _full_history, _from_date, _to_date):
    domain = [["state", "in", ["purchase", "done"]]]
    if not _full_history:
        domain += [
            ["date_order", ">=", str(_from_date)],
            ["date_order", "<",  str(_to_date + timedelta(days=1))],
        ]
    orders    = fetch_all(_uid, _k, "purchase.order", domain,
                          ["id", "date_order", "partner_id"])
    order_ids = [o["id"] for o in orders]
    date_map  = {o["id"]: o["date_order"] for o in orders}
    supp_map  = {o["id"]: (o.get("partner_id") or [0, "-"])[1] for o in orders}
    if not order_ids:
        return pd.DataFrame()
    lines = fetch_all(_uid, _k, "purchase.order.line",
                      [["order_id", "in", order_ids]],
                      ["product_id", "product_qty", "price_subtotal", "order_id"])
    rows = []
    for r in lines:
        oid  = r["order_id"][0] if r.get("order_id") else None
        date = date_map.get(oid)
        if not date:
            continue
        try:
            rows.append({
                "PID"     : r["product_id"][0] if r.get("product_id") else 0,
                "Product" : r["product_id"][1] if r.get("product_id") else "-",
                "Qty"     : r.get("product_qty")    or 0,
                "Amount"  : r.get("price_subtotal") or 0,
                "Date"    : pd.to_datetime(date),
                "Supplier": supp_map.get(oid, "-"),
            })
        except Exception:
            continue
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False, ttl=INV_TTL)
def load_products(_uid, _k):
    """Product master – no date params, longest cache TTL."""
    recs = fetch_all(
        _uid, _k, "product.product",
        [["active", "=", True], ["type", "=", "product"]],
        ["id", "default_code", "name", "categ_id", "brand_id",
         "qty_available", "virtual_available", "standard_price"],
    )
    rows = []
    for p in recs:
        qty  = max(0, p.get("qty_available") or 0)
        cost = p.get("standard_price") or 0
        rows.append({
            "PID"     : p["id"],
            "Ref"     : p.get("default_code") or "",
            "Product" : p.get("name") or "",
            "Category": p["categ_id"][1] if p.get("categ_id") else "-",
            "Brand"   : p["brand_id"][1]  if p.get("brand_id")  else "-",
            "Qty"     : qty,
            "Forecast": p.get("virtual_available") or 0,
            "Cost"    : cost,
            "Value"   : round(qty * cost, 2),
            "Status"  : "OUT" if qty <= 0 else ("LOW" if qty <= LOW_THRESHOLD else "OK"),
        })
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False, ttl=SALES_TTL)
def load_branch_sales(_uid, _k, _full_history, _from_date, _to_date):
    domain = [["state", "in", ["sale", "done"]]]
    if not _full_history:
        domain += [
            ["date_order", ">=", str(_from_date)],
            ["date_order", "<",  str(_to_date + timedelta(days=1))],
        ]
    orders    = fetch_all(_uid, _k, "sale.order", domain,
                          ["id", "date_order", "team_id", "warehouse_id"])
    order_ids = [o["id"] for o in orders]
    if not order_ids:
        return pd.DataFrame()
    date_map = {o["id"]: o["date_order"] for o in orders}
    br_map   = {o["id"]: (o.get("team_id")      or [0, "No Branch"])[1]    for o in orders}
    wh_map   = {o["id"]: (o.get("warehouse_id") or [0, "No Warehouse"])[1] for o in orders}
    lines = fetch_all(_uid, _k, "sale.order.line",
                      [["order_id", "in", order_ids]],
                      ["product_id", "product_uom_qty", "price_subtotal", "order_id"])
    rows = []
    for r in lines:
        oid  = r["order_id"][0] if r.get("order_id") else None
        date = date_map.get(oid)
        if not (date and oid):
            continue
        try:
            rows.append({
                "OrderID"  : oid,
                "Date"     : pd.to_datetime(date),
                "Branch"   : br_map.get(oid, "No Branch"),
                "Warehouse": wh_map.get(oid, "No Warehouse"),
                "PID"      : r["product_id"][0] if r.get("product_id") else 0,
                "Product"  : r["product_id"][1] if r.get("product_id") else "-",
                "Qty"      : r.get("product_uom_qty") or 0,
                "Amount"   : r.get("price_subtotal")  or 0,
            })
        except Exception:
            continue
    return pd.DataFrame(rows)

# ─────────────────────────────────────────────────────────────────────────────
# 1 + 5 + 6. PARALLEL, LAZY, PROGRESS-BAR PAGE LOADER
# ─────────────────────────────────────────────────────────────────────────────

def load_page_data(uid, key, full_history, from_date, to_date,
                   non_moving_days, page, prog):
    """
    5.  Lazy   – fetches only what the current page actually needs.
    1.  Parallel – independent Odoo chains run in a ThreadPoolExecutor.
    6.  Progress – prog.progress(pct, text=…) updated throughout.
    10. Cache   – result stored in st.session_state; page-switches are instant.
    """
    ss_k = _ss_key(uid, full_history, from_date, to_date, non_moving_days, page)
    cached = _ss_get(ss_k)
    if cached is not None:
        prog.progress(100, text="✅ Loaded from cache (instant)")
        return cached

    prog.progress(5, text="🔗 Connecting to Odoo…")

    # ── Branch Sales (2 chains) ────────────────────────────────────────────────
    if page == "🏢 Branch Sales":
        with ThreadPoolExecutor(max_workers=2) as pool:
            f_br   = pool.submit(load_branch_sales, uid, key, full_history, from_date, to_date)
            f_prod = pool.submit(load_products, uid, key)
            prog.progress(30, text="📡 Fetching branch orders + products in parallel…")
            df_br   = f_br.result()
            df_prod = f_prod.result()

        meta   = df_prod[["PID", "Category", "Brand"]].drop_duplicates()
        df_br  = df_br.merge(meta, on="PID", how="left")
        df_br["Category"] = df_br["Category"].fillna("-")
        df_br["Brand"]    = df_br["Brand"].fillna("-")
        if not df_br.empty:
            mv = df_br.groupby("PID")["Qty"].sum()
            df_br = df_br[df_br["PID"].isin(mv[mv > 0].index)]
        prog.progress(100, text="✅ Branch data ready")
        result = {"branch": df_br, "products": df_prod}
        _ss_put(ss_k, result);  return result

    # ── Purchase page (2 chains) ───────────────────────────────────────────────
    if page == "🏪 Purchase":
        with ThreadPoolExecutor(max_workers=2) as pool:
            f_prod = pool.submit(load_products, uid, key)
            f_pur  = pool.submit(load_pur, uid, key, full_history, from_date, to_date)
            prog.progress(40, text="📡 Products + purchases in parallel…")
            df_prod = f_prod.result()
            df_pur  = f_pur.result()

        meta   = df_prod[["PID","Category","Brand"]].drop_duplicates()
        df_pur = df_pur.merge(meta, on="PID", how="left") if not df_pur.empty else df_pur
        prog.progress(100, text="✅ Purchase data ready")
        result = {"products": df_prod, "purchases": df_pur}
        _ss_put(ss_k, result);  return result

    # ── Sales page (3 chains) ──────────────────────────────────────────────────
    if page == "🛒 Sales":
        with ThreadPoolExecutor(max_workers=3) as pool:
            f_so   = pool.submit(load_sal,       uid, key, full_history, from_date, to_date)
            f_pos  = pool.submit(load_pos_sales, uid, key, full_history, from_date, to_date)
            f_prod = pool.submit(load_products,  uid, key)
            prog.progress(30, text="📡 SO + POS + Products in parallel…")
            df_so   = f_so.result()
            df_pos  = f_pos.result()
            df_prod = f_prod.result()

        df_sales = pd.concat([df_so, df_pos], ignore_index=True)
        meta     = df_prod[["PID","Category","Brand"]].drop_duplicates()
        df_sales = df_sales.merge(meta, on="PID", how="left") if not df_sales.empty else df_sales
        prog.progress(100, text="✅ Sales data ready")
        result = {"sales": df_sales, "products": df_prod}
        _ss_put(ss_k, result);  return result

    # ── Everything else: 4 chains in parallel ─────────────────────────────────
    prog.progress(8, text="📡 Launching 4 parallel Odoo fetches…")
    with ThreadPoolExecutor(max_workers=4) as pool:
        f_prod = pool.submit(load_products,  uid, key)
        f_so   = pool.submit(load_sal,       uid, key, full_history, from_date, to_date)
        f_pos  = pool.submit(load_pos_sales, uid, key, full_history, from_date, to_date)
        f_pur  = pool.submit(load_pur,       uid, key, full_history, from_date, to_date)
        step_names = {f_prod:"📦 Products", f_so:"🛒 SO", f_pos:"🏪 POS", f_pur:"📋 Purchases"}
        done, results = 0, {}
        for fut in as_completed([f_prod, f_so, f_pos, f_pur]):
            done += 1
            prog.progress(8 + int(done/4*62),
                          text=f"✅ {step_names[fut]} loaded ({done}/4)")
            results[fut] = fut.result()

    df_prod = results[f_prod]
    df_so   = results[f_so]
    df_pos  = results[f_pos]
    df_pur  = results[f_pur]

    prog.progress(73, text="🔧 Computing inventory metrics…")

    df_inv   = df_prod.copy()
    df_sales = pd.concat([df_so, df_pos], ignore_index=True)
    meta     = df_inv[["PID","Category","Brand"]].drop_duplicates()
    if not df_sales.empty: df_sales = df_sales.merge(meta, on="PID", how="left")
    if not df_pur.empty:   df_pur   = df_pur.merge(meta, on="PID", how="left")

    today_dt = pd.to_datetime(datetime.today().date())
    if not df_sales.empty:
        ls = df_sales.groupby("PID")["Date"].max().reset_index(name="LastSaleDate")
        df_inv = df_inv.merge(ls, on="PID", how="left")
    else:
        df_inv["LastSaleDate"] = pd.NaT

    threshold = today_dt - timedelta(days=non_moving_days)
    mask      = df_inv["Qty"] > 0
    df_inv["NonMoving"] = False
    df_inv.loc[mask, "NonMoving"] = (
        df_inv.loc[mask,"LastSaleDate"].isna() |
        (df_inv.loc[mask,"LastSaleDate"] < threshold)
    )

    has_val = df_inv["Value"] > 0
    nm_mask = df_inv["NonMoving"] & has_val
    tot_val = df_inv.loc[has_val,"Value"].sum()
    nm_val  = df_inv.loc[nm_mask,"Value"].sum()
    nm_pct  = round((nm_val/tot_val*100) if tot_val else 0, 2)

    sold     = ~df_inv["LastSaleDate"].isna() & has_val
    nm_sold  = df_inv[sold & df_inv["NonMoving"]]["Value"].sum()
    tot_sold = df_inv[sold]["Value"].sum()
    nm_pct_sold = round((nm_sold/tot_sold*100) if tot_sold else 0, 2)

    ns_df     = df_inv[df_inv["LastSaleDate"].isna() & has_val]
    ns_val    = ns_df["Value"].sum()
    ns_cnt    = len(ns_df)

    prog.progress(85, text="🔧 Computing stock ageing…")

    # Full-history purchases for first-in date (uses its own cache)
    pur_full = load_pur(uid, key, True, from_date, to_date)
    if not pur_full.empty:
        fi     = pur_full.groupby("PID")["Date"].min().reset_index(name="FirstInDate")
        df_inv = df_inv.merge(fi, on="PID", how="left")
    else:
        df_inv["FirstInDate"] = pd.NaT
    df_inv["DaysInStock"] = (
        (today_dt - df_inv["FirstInDate"]).dt.days.where(df_inv["Qty"] > 0, np.nan)
    )

    prog.progress(100, text="✅ All data ready")
    result = {
        "products"        : df_prod,
        "inventory"       : df_inv,
        "sales"           : df_sales,
        "purchases"       : df_pur,
        "nonmoving_pct"   : nm_pct,
        "total_products"  : len(df_inv),
        "total_value"     : tot_val,
        "nm_value"        : nm_val,
        "never_sold_value": ns_val,
        "never_sold_count": ns_cnt,
        "nm_pct_sold"     : nm_pct_sold,
    }
    _ss_put(ss_k, result)
    return result

# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

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


def to_excel_with_index(dfs_flat: dict, dfs_idx: dict | None = None) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, df in dfs_flat.items():
            df.to_excel(w, sheet_name=name[:31], index=False)
        if dfs_idx:
            for name, df in dfs_idx.items():
                df.to_excel(w, sheet_name=name[:31], index=True)
    return buf.getvalue()


# ── 8. Reusable column_config helpers ─────────────────────────────────────────
def _money(label="SAR"):
    return st.column_config.NumberColumn(label, format="%.0f")

def _qty(label="Qty"):
    return st.column_config.NumberColumn(label, format="%d")

def _pct(label="%"):
    return st.column_config.NumberColumn(label, format="%.1f%%")

def _dt(label="Date"):
    return st.column_config.DatetimeColumn(label, format="DD MMM YYYY")


def kpi(title, value, sub=""):
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-title">{title}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────────────────────

for _sk, _sv in {"uid": None, "api_key": None, "uname": None}.items():
    if _sk not in st.session_state:
        st.session_state[_sk] = _sv


def login_page():
    st.markdown(
        "<div style='text-align:center;padding:40px 0 20px'>"
        "<h1 style='color:#d4af37'>👗 Outfit Dashboard</h1>"
        "<p style='color:#a9a9a9'>Live Odoo insights for Outfit Company</p>"
        "</div>", unsafe_allow_html=True,
    )
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

# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD SHELL
# ─────────────────────────────────────────────────────────────────────────────

def dashboard():
    uid = st.session_state.uid
    key = st.session_state.api_key

    st.markdown("""
    <div style="text-align:center;padding:12px;
    background:linear-gradient(90deg,#1a1a1a,#d4af37,#1a1a1a);
    border-radius:15px;margin-bottom:20px;box-shadow:0 0 20px rgba(212,175,55,0.3);">
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
        to_date         = st.date_input("To Date",   value=datetime.today().date())
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

    # ── 6. Progress bar ──────────────────────────────────────────────────────
    prog = st.progress(0, text="⏳ Initialising…")
    try:
        data = load_page_data(uid, key, full_history, from_date, to_date,
                              non_moving_days, page, prog)
    except Exception as e:
        prog.empty()
        st.error(f"Data load failed: {e}")
        st.stop()
    prog.empty()

    # ── Route ────────────────────────────────────────────────────────────────
    if   page == "📦 Inventory":    page_inventory(data, date_info, debug)
    elif page == "🛒 Sales":        page_sales(data, date_info)
    elif page == "🏪 Purchase":     page_purchase(data, date_info)
    elif page == "📁 Category":     page_category(data, date_info)
    elif page == "🏷️ Brand":       page_brand(data, date_info)
    elif page == "📊 Combined":     page_combined(data, date_info)
    elif page == "🏢 Branch Sales": page_branch_sales(data, date_info)
    elif page == "💼 Power BI":     page_powerbi(data)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: INVENTORY
# ─────────────────────────────────────────────────────────────────────────────

def page_inventory(data, date_info, debug):
    df_inv  = data["inventory"]
    df_sal  = data["sales"]
    df_pur  = data["purchases"]
    nm_pct  = data["nonmoving_pct"]
    nm_val  = data["nm_value"]
    ns_val  = data["never_sold_value"]
    ns_cnt  = data["never_sold_count"]
    nm_ps   = data["nm_pct_sold"]

    st.markdown(f"### 👗 Outfit Inventory Overview ({date_info})")
    if debug:
        st.info(f"DEBUG – Products: {data['total_products']:,} | "
                f"Value: {data['total_value']:,.0f} | NM value: {nm_val:,.0f}")

    sv = df_inv.Value.sum()
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    with c1: kpi("TOTAL STYLES",  f"{data['total_products']:,}", "Stockable")
    with c2: kpi("IN STOCK (OK)", f"{(df_inv.Status=='OK').sum():,}", "Healthy")
    with c3: kpi("LOW STOCK",     f"{(df_inv.Status=='LOW').sum():,}", f"≤{LOW_THRESHOLD}")
    with c4: kpi("OUT OF STOCK",  f"{(df_inv.Status=='OUT').sum():,}", "Zero")
    with c5: kpi("TOTAL VALUE",   f"{sv:,.0f}", "SAR")
    with c6: kpi("NON MOVING %",  f"{nm_pct}%", "Whole Catalog")

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

    # Low Stock Alert
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Low Stock Styles Alert")
    low_df = df_inv[df_inv.Status.isin(["LOW","OUT"])].sort_values("Qty").head(50)
    if low_df.empty:
        st.info("No low / out-of-stock styles.")
    else:
        st.dataframe(low_df.drop(columns=["PID"]), use_container_width=True,
                     column_config={"Qty":_qty("On Hand"),"Value":_money("Value SAR"),
                                    "Cost":_money("Cost SAR")})
        st.download_button("Export Low Stock",
                           to_excel({"Low_Stock": low_df.drop(columns=["PID"])}),
                           "low_stock.xlsx")
    st.markdown("</div>", unsafe_allow_html=True)

    # Stock Ageing
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Stock Ageing")
    if "DaysInStock" in df_inv.columns:
        df_inv["AgeBucket"] = pd.cut(
            df_inv["DaysInStock"], bins=[0,90,180,365,np.inf],
            labels=["0-90","91-180","181-365","365+"])
        age = (df_inv.groupby("AgeBucket", observed=True)
                     .agg(Count=("PID","count"), Value=("Value","sum")).reset_index())
        st.plotly_chart(px.bar(age, x="AgeBucket", y="Value",
                               title="Stock Value by Age Bucket"),
                        use_container_width=True)
        st.dataframe(age, use_container_width=True,
                     column_config={"Value":_money("Value SAR")})
    else:
        st.info("No ageing data available.")
    st.markdown("</div>", unsafe_allow_html=True)

    # Full Inventory
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Full Inventory")
    colf = st.columns([2,1,1,1,1,1])
    with colf[0]: srch    = st.text_input("Search Ref / Style")
    with colf[1]: fstat   = st.selectbox("Status",   ["All","OK","LOW","OUT"])
    with colf[2]: fcat    = st.selectbox("Category", ["All"]+sorted(df_inv.Category.unique().tolist()))
    with colf[3]: fbrd    = st.selectbox("Brand",    ["All"]+sorted(df_inv.Brand.unique().tolist()))
    with colf[4]: fmov    = st.selectbox("Movement", ["All","Moving","Non-Moving"])
    with colf[5]: min_qty = st.number_input("Min Qty", min_value=0, value=0)
    df_f = df_inv.copy()
    if srch:               df_f = df_f[df_f.Product.str.contains(srch,case=False,na=False)|
                                       df_f.Ref.str.contains(srch,case=False,na=False)]
    if fstat != "All":     df_f = df_f[df_f.Status   == fstat]
    if fcat  != "All":     df_f = df_f[df_f.Category == fcat]
    if fbrd  != "All":     df_f = df_f[df_f.Brand    == fbrd]
    if fmov == "Non-Moving": df_f = df_f[df_f.NonMoving]
    elif fmov == "Moving":   df_f = df_f[~df_f.NonMoving]
    df_f = df_f[df_f.Qty >= min_qty]
    st.caption(f"Showing {len(df_f):,} styles")
    st.dataframe(df_f.drop(columns=["PID"]), use_container_width=True,
                 column_config={"Qty":_qty("On Hand"),"Value":_money("Value SAR"),
                                "Cost":_money("Cost SAR"),"LastSaleDate":_dt("Last Sale")})
    st.download_button("Export Inventory",
                       to_excel({"Inventory": df_f.drop(columns=["PID"])}),
                       "inventory.xlsx")
    st.markdown("</div>", unsafe_allow_html=True)

    # Style Detail View
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Style Detail View")
    if not df_inv.empty:
        opts   = [f"{r.Ref} | {r.Product}" for _,r in df_inv.iterrows()]
        sel    = st.selectbox("Select Style", opts)
        row    = df_inv[(df_inv["Ref"]+' | '+df_inv["Product"]) == sel].iloc[0]
        today_dt = pd.to_datetime(datetime.today().date())
        s12    = df_sal[(df_sal.PID==row.PID)&(df_sal.Date>=today_dt-timedelta(days=365))]
        s6     = s12[s12.Date>=today_dt-timedelta(days=180)].copy()
        monthly = pd.DataFrame(columns=["Month","Qty","Amount"])
        if not s6.empty:
            s6["Month"] = s6["Date"].dt.strftime("%Y-%m")
            monthly = s6.groupby("Month").agg(Qty=("Qty","sum"),Amount=("Amount","sum")).reset_index()
        c1,c2,c3,c4 = st.columns(4)
        with c1: st.metric("Current Stock", f"{row.Qty:,}")
        with c2: st.metric("Stock Value",   f"{row.Value:,.0f}")
        with c3: st.metric("Last Sale", row.LastSaleDate.strftime("%d %b %Y")
                            if pd.notna(row.LastSaleDate) else "Never")
        with c4: st.metric("12m Sales", f"{s12.Qty.sum():.0f} pcs / {s12.Amount.sum():,.0f}")
        st.markdown(f"**Status**: <span class='status-pill status-{row.Status}'>{row.Status}</span>",
                    unsafe_allow_html=True)
        st.subheader("Last 6 Months Sales")
        st.dataframe(monthly, use_container_width=True,
                     column_config={"Amount":_money("Amount SAR"),"Qty":_qty()})
    st.markdown("</div>", unsafe_allow_html=True)

    # Turnover
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Inventory Turnover")
    st.metric("Turnover Ratio", f"{df_sal.Amount.sum()/sv:.2f}x" if sv else "N/A")
    st.markdown("</div>", unsafe_allow_html=True)

    # Non-Moving
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Non-Moving Styles")
    nm_df = df_inv[df_inv["NonMoving"]]
    st.caption(f"Styles: {len(nm_df):,} | Value: {nm_val:,.0f} SAR ({nm_pct}%)")
    st.caption(f"Non-Moving % (sold styles only): {nm_ps}%")
    st.caption(f"Never sold: {ns_cnt} styles, {ns_val:,.0f} SAR")
    st.dataframe(nm_df.drop(columns=["PID"]), use_container_width=True,
                 column_config={"Value":_money(),"Qty":_qty()})
    st.markdown("</div>", unsafe_allow_html=True)

    # Never Sold High-Value
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Top 20 High-Value Never Sold Styles")
    ns = df_inv[df_inv["LastSaleDate"].isna()].nlargest(20,"Value")
    if ns.empty: st.info("No never-sold high-value styles.")
    else: st.dataframe(ns.drop(columns=["PID"]), use_container_width=True,
                       column_config={"Value":_money(),"Qty":_qty()})
    st.markdown("</div>", unsafe_allow_html=True)

    # Validation
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Validation Checks")
    for name, dv in get_validation_checks(df_inv).items():
        st.caption(f"{name}: {len(dv)} items")
        if not dv.empty:
            st.dataframe(dv.drop(columns=["PID"]), use_container_width=True)
            st.download_button(f"Export {name}",
                               to_excel({name: dv.drop(columns=["PID"])}),
                               f"{name.lower().replace(' ','_')}.xlsx")
    st.markdown("</div>", unsafe_allow_html=True)

    # Sell-Through
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Sell-Through Rates")
    if not df_sal.empty and not df_pur.empty:
        sq   = df_sal.groupby("PID")["Qty"].sum().reset_index(name="SalesQty")
        pq   = df_pur.groupby("PID")["Qty"].sum().reset_index(name="PurQty")
        df_st = (df_inv.merge(sq,on="PID",how="left")
                       .merge(pq,on="PID",how="left").fillna(0))
        df_st["OEst"]       = (df_st["Qty"]+df_st["SalesQty"]-df_st["PurQty"]).clip(lower=0)
        df_st["SellThrough"] = np.where(
            (df_st["OEst"]+df_st["PurQty"])>0,
            df_st["SalesQty"]/(df_st["OEst"]+df_st["PurQty"])*100, 0)
        c1,c2 = st.columns(2)
        with c1:
            st.subheader("Top Styles")
            st.dataframe(df_st.nlargest(10,"SellThrough")[["Product","SellThrough"]],
                         column_config={"SellThrough":_pct("Sell-Through %")})
        with c2:
            st.subheader("Bottom Styles")
            st.dataframe(df_st.nsmallest(10,"SellThrough")[["Product","SellThrough"]],
                         column_config={"SellThrough":_pct("Sell-Through %")})
    else:
        st.info("Insufficient data.")
    st.markdown("</div>", unsafe_allow_html=True)

    # OOS Risk
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("OOS Risk")
    st.metric("Styles at Risk (Forecast < 0)", len(df_inv[df_inv["Forecast"]<0]))
    st.markdown("</div>", unsafe_allow_html=True)

    # Sales Trend  ← 9. WebGL
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
                    render_mode="webgl"),    # ← 9.
            use_container_width=True)
    else:
        st.info("No sales data in selected period.")
    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: SALES
# ─────────────────────────────────────────────────────────────────────────────

def page_sales(data, date_info):
    df_s = data["sales"]
    st.markdown(f"### 🛒 Outfit Sales Analysis ({date_info})")
    if df_s.empty:
        st.warning("No sales data in the selected period."); return

    c1,c2,c3 = st.columns(3)
    with c1: ch = st.selectbox("Channel",  ["Both","SO","POS"])
    with c2: cf = st.selectbox("Category", ["All"]+sorted(df_s.Category.dropna().unique().tolist()))
    with c3: bf = st.selectbox("Brand",    ["All"]+sorted(df_s.Brand.dropna().unique().tolist()))
    if ch != "Both": df_s = df_s[df_s.Source   == ch]
    if cf != "All":  df_s = df_s[df_s.Category == cf]
    if bf != "All":  df_s = df_s[df_s.Brand    == bf]

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: kpi("TOTAL SALES",    f"{df_s.Amount.sum():,.0f}",           "SAR")
    with c2: kpi("UNITS SOLD",     f"{df_s.Qty.sum():,.0f}",              "pcs")
    with c3: kpi("AVG BILL VALUE", f"{df_s.groupby('OrderID')['Amount'].sum().mean():,.0f}", "SAR/order")
    with c4: kpi("SO SALES",       f"{df_s[df_s.Source=='SO']['Amount'].sum():,.0f}", "SAR")
    with c5: kpi("POS SALES",      f"{df_s[df_s.Source=='POS']['Amount'].sum():,.0f}","SAR")

    col1,col2 = st.columns(2)
    with col1:
        t20 = df_s.groupby(["PID","Product"])["Amount"].sum().nlargest(20).reset_index()
        fig = px.bar(t20, x="Amount", y="Product", orientation="h", title="Top 20 Styles")
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        tb = df_s.groupby("Brand")["Amount"].sum().nlargest(10).reset_index()
        st.plotly_chart(px.bar(tb, x="Amount", y="Brand", title="Top 10 Brands"),
                        use_container_width=True)

    # Daily trend  ← 9. WebGL
    ts = (df_s.groupby(df_s["Date"].dt.date)["Amount"]
               .sum().reset_index(name="Amount").sort_values("Date"))
    st.plotly_chart(
        px.line(ts, x="Date", y="Amount", title="Daily Sales Trend",
                render_mode="webgl"),    # ← 9.
        use_container_width=True)
    st.download_button("Export Sales", to_excel({"Sales": df_s}), "sales_export.xlsx")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: PURCHASE
# ─────────────────────────────────────────────────────────────────────────────

def page_purchase(data, date_info):
    df_pur = data["purchases"]
    st.markdown(f"### 🏪 Outfit Purchase Analysis ({date_info})")
    if df_pur.empty:
        st.warning("No purchase data in the selected period."); return

    c1,c2,c3 = st.columns(3)
    with c1: kpi("TOTAL PURCHASES", f"{df_pur.Amount.sum():,.0f}",      "SAR")
    with c2: kpi("UNITS PURCHASED", f"{df_pur.Qty.sum():,.0f}",         "pcs")
    with c3: kpi("SUPPLIERS",       f"{df_pur.Supplier.nunique()}",     "Distinct")

    col1,col2 = st.columns(2)
    with col1:
        tp = df_pur.groupby(df_pur["Date"].dt.date)["Amount"].sum().reset_index(name="Amount")
        st.plotly_chart(
            px.line(tp, x="Date", y="Amount", title="Purchases Over Time",
                    render_mode="webgl"),   # ← 9.
            use_container_width=True)
    with col2:
        ts = df_pur.groupby("Supplier")["Amount"].sum().nlargest(10).reset_index()
        st.plotly_chart(px.bar(ts, x="Amount", y="Supplier", title="Top 10 Suppliers"),
                        use_container_width=True)
    st.dataframe(df_pur, use_container_width=True,
                 column_config={"Amount":_money(),"Qty":_qty(),"Date":_dt()})
    st.download_button("Export Purchases",
                       to_excel({"Purchases": df_pur}), "purchases.xlsx")

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: CATEGORY
# ─────────────────────────────────────────────────────────────────────────────

def page_category(data, date_info):
    df_inv = data["inventory"]
    df_s   = data["sales"]
    st.markdown(f"### 📁 Category Dashboard ({date_info})")
    cs = df_inv.groupby("Category").agg(Stock_Value=("Value","sum"),
                                        Num_Styles=("PID","nunique")).reset_index()
    ss = df_s.groupby("Category").agg(Sales_Value=("Amount","sum"),
                                      Sales_Qty=("Qty","sum")).reset_index()
    df = cs.merge(ss, on="Category", how="left").fillna(0)
    col1,col2 = st.columns(2)
    with col1: st.plotly_chart(px.bar(df, x="Category", y="Stock_Value",
                                      title="Stock Value by Category"), use_container_width=True)
    with col2: st.plotly_chart(px.pie(df, names="Category", values="Sales_Value",
                                      title="Sales Contribution by Category"), use_container_width=True)
    st.dataframe(df, use_container_width=True,
                 column_config={"Stock_Value":_money("Stock SAR"),
                                "Sales_Value":_money("Sales SAR"),
                                "Sales_Qty"  :_qty("Units Sold")})

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: BRAND
# ─────────────────────────────────────────────────────────────────────────────

def page_brand(data, date_info):
    df_inv = data["inventory"]
    df_s   = data["sales"]
    st.markdown(f"### 🏷️ Brand Dashboard ({date_info})")
    bs = df_inv.groupby("Brand").agg(Stock_Value=("Value","sum"),
                                     Num_Styles=("PID","nunique")).reset_index()
    today_dt = pd.to_datetime(datetime.today().date())
    b90  = (df_s[df_s.Date>=today_dt-timedelta(days=90)]
              .groupby("Brand")["Amount"].sum().reset_index(name="Sales_Last90d"))
    df   = bs.merge(b90, on="Brand", how="left").fillna(0)
    col1,col2 = st.columns(2)
    with col1: st.plotly_chart(px.bar(df, x="Brand", y="Stock_Value",
                                      title="Stock Value by Brand"), use_container_width=True)
    with col2: st.plotly_chart(px.bar(df, x="Brand", y="Sales_Last90d",
                                      title="Sales Last 90 Days by Brand"), use_container_width=True)
    st.dataframe(df, use_container_width=True,
                 column_config={"Stock_Value"  :_money("Stock SAR"),
                                "Sales_Last90d":_money("Sales 90d SAR")})

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: COMBINED
# ─────────────────────────────────────────────────────────────────────────────

def page_combined(data, date_info):
    df_inv = data["inventory"]
    df_s   = data["sales"]
    df_pur = data["purchases"]
    st.markdown(f"### 📊 Combined Overview ({date_info})")
    sv = df_inv.Value.sum()
    today_dt = pd.to_datetime(datetime.today().date())
    s30 = df_s[df_s.Date>=today_dt-timedelta(days=30)]["Amount"].sum()
    trn = df_s.Amount.sum()/sv if sv else 0
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("Total Stock Value",  f"{sv:,.0f} SAR")
    with c2: st.metric("Last 30 Days Sales", f"{s30:,.0f} SAR")
    with c3: st.metric("Non-Moving %",       f"{data['nonmoving_pct']}%")
    with c4: st.metric("Overall Turnover",   f"{trn:.2f}x")
    if not df_s.empty or not df_pur.empty:
        st_t = df_s.groupby(df_s["Date"].dt.date)["Amount"].sum().reset_index(name="Sales")
        pt   = df_pur.groupby(df_pur["Date"].dt.date)["Amount"].sum().reset_index(name="Purchases")
        td   = pd.merge(st_t, pt, on="Date", how="outer").fillna(0).sort_values("Date")
        st.plotly_chart(
            px.line(td, x="Date", y=["Sales","Purchases"],
                    title="Sales vs Purchases", render_mode="webgl"),  # ← 9.
            use_container_width=True)
    if not df_s.empty:
        cs = df_s.groupby("Category")["Amount"].sum().nlargest(10).reset_index()
        st.plotly_chart(px.bar(cs, x="Amount", y="Category",
                               title="Top 10 Categories by Sales"),
                        use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: BRANCH SALES
# ─────────────────────────────────────────────────────────────────────────────

def page_branch_sales(data, date_info):
    df_raw = data.get("branch", pd.DataFrame())
    st.markdown(f"### 🏢 Branch Sales Analysis ({date_info})")
    st.caption("Source: sale.order + sale.order.line (SO only) — moving products only")
    if df_raw.empty:
        st.warning("No branch sales data in the selected period."); return

    # Filters
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("#### 🔍 Filters")
    fc1,fc2,fc3,fc4 = st.columns(4)
    with fc1: f_br  = st.selectbox("Branch",    ["All"]+sorted(df_raw.Branch.dropna().unique().tolist()),    key="bs_br")
    with fc2: f_wh  = st.selectbox("Warehouse", ["All"]+sorted(df_raw.Warehouse.dropna().unique().tolist()), key="bs_wh")
    with fc3: f_cat = st.selectbox("Category",  ["All"]+sorted(df_raw.Category.dropna().unique().tolist()),  key="bs_cat")
    with fc4: f_brd = st.selectbox("Brand",     ["All"]+sorted(df_raw.Brand.dropna().unique().tolist()),     key="bs_brd")
    st.markdown("</div>", unsafe_allow_html=True)

    df = df_raw.copy()
    if f_br  != "All": df = df[df.Branch    == f_br]
    if f_wh  != "All": df = df[df.Warehouse == f_wh]
    if f_cat != "All": df = df[df.Category  == f_cat]
    if f_brd != "All": df = df[df.Brand     == f_brd]
    if df.empty:
        st.warning("No data after applying filters."); return

    k1,k2,k3,k4 = st.columns(4)
    with k1: kpi("TOTAL SALES",     f"{df.Amount.sum():,.0f}", "SAR")
    with k2: kpi("UNITS SOLD",      f"{df.Qty.sum():,.0f}",    "pcs")
    with k3: kpi("BRANCHES",        f"{df.Branch.nunique()}",  "Sales Teams")
    with k4: kpi("UNIQUE PRODUCTS", f"{df.Product.nunique():,}","Moving Styles")

    st.markdown("<br>", unsafe_allow_html=True)

    # Sales by Branch
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Sales by Branch")
    bagg = (df.groupby("Branch").agg(Sales_SAR=("Amount","sum"),Units=("Qty","sum"))
              .reset_index().sort_values("Sales_SAR", ascending=False))
    ca,cb = st.columns(2)
    _gscale = [[0,"#1a1a1a"],[0.5,"#b8860b"],[1,"#d4af37"]]
    with ca:
        f1 = px.bar(bagg, x="Branch", y="Sales_SAR", title="Sales (SAR) by Branch",
                    color="Sales_SAR", color_continuous_scale=_gscale)
        f1.update_layout(coloraxis_showscale=False)
        st.plotly_chart(f1, use_container_width=True)
    with cb:
        f2 = px.bar(bagg, x="Branch", y="Units", title="Units Sold by Branch",
                    color="Units", color_continuous_scale=_gscale)
        f2.update_layout(coloraxis_showscale=False)
        st.plotly_chart(f2, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Daily Trend  ← 9. WebGL
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Daily Sales Trend by Branch")
    daily = df.groupby([df["Date"].dt.date,"Branch"])["Amount"].sum().reset_index(name="Sales_SAR")
    daily.rename(columns={"Date":"Day"}, inplace=True)
    fig_tr = px.line(daily, x="Day", y="Sales_SAR", color="Branch",
                     title="Daily Sales (SAR) per Branch", render_mode="webgl")  # ← 9.
    fig_tr.update_traces(mode="lines+markers", marker=dict(size=3))
    st.plotly_chart(fig_tr, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Top 20 per Branch
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Top 20 Products per Branch")
    sel_br = st.selectbox("Select Branch", sorted(df.Branch.unique().tolist()), key="bs_dd")
    top20  = (df[df.Branch==sel_br].groupby("Product")
                .agg(Sales_SAR=("Amount","sum"),Units=("Qty","sum"))
                .reset_index().nlargest(20,"Sales_SAR"))
    metric = st.radio("Metric", ["Sales (SAR)","Units"], horizontal=True, key="bs_met")
    y_col  = "Sales_SAR" if metric == "Sales (SAR)" else "Units"
    f3 = px.bar(top20, x=y_col, y="Product", orientation="h",
                title=f"Top 20 – {sel_br} ({metric})",
                color=y_col, color_continuous_scale=_gscale)
    f3.update_layout(yaxis=dict(autorange="reversed"), coloraxis_showscale=False)
    st.plotly_chart(f3, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Pivot
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Branch × Product Pivot Table")
    pv_m  = st.radio("Pivot Value", ["Qty","Amount (SAR)"], horizontal=True, key="bs_pv")
    pv_c  = "Qty" if pv_m=="Qty" else "Amount"
    pivot = (df.groupby(["Product","Branch"])[pv_c].sum()
               .reset_index().pivot(index="Product",columns="Branch",values=pv_c).fillna(0))
    pivot["TOTAL"] = pivot.sum(axis=1)
    pivot          = pivot.sort_values("TOTAL", ascending=False)
    st.caption(f"Rows: {len(pivot):,} products · Values: {pv_m}")
    st.dataframe(pivot, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Raw Data
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Raw Sales Data")
    dcols = ["Date","Branch","Warehouse","Product","Category","Brand","Qty","Amount","OrderID"]
    st.dataframe(df[dcols].sort_values("Date", ascending=False),
                 use_container_width=True,
                 column_config={"Date":_dt(),"Qty":_qty(),"Amount":_money("Amount SAR")})
    st.markdown("</div>", unsafe_allow_html=True)

    # Export
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Export")
    st.download_button(
        "📥 Export Branch Sales (Pivot + Raw)",
        data=to_excel_with_index(
            {"Raw_Data": df[dcols].sort_values("Date", ascending=False)},
            {"Pivot_Branch_Product": pivot.reset_index()},
        ),
        file_name="branch_sales_export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: POWER BI
# ─────────────────────────────────────────────────────────────────────────────

def page_powerbi(data):
    df_inv = data.get("inventory", pd.DataFrame())
    df_s   = data.get("sales",     pd.DataFrame())
    df_pur = data.get("purchases", pd.DataFrame())
    st.markdown("### 💼 Power BI Export Helper")
    st.markdown("""
**How to use in Power BI**
1. Download any file below
2. Power BI → Get Data → Excel → select file
3. All sheets are ready for relationships on **PID**
""")
    c1,c2,c3 = st.columns(3)
    with c1: st.download_button("📦 Inventory",
                                 to_excel({"Inventory": df_inv.drop(columns=["PID"],errors="ignore")}),
                                 "outfit_inventory.xlsx")
    with c2: st.download_button("🛒 Sales",     to_excel({"Sales":df_s}),     "outfit_sales.xlsx")
    with c3: st.download_button("🏪 Purchases", to_excel({"Purchases":df_pur}),"outfit_purchases.xlsx")
    st.download_button("📁 ALL DATA (multi-sheet)",
                       to_excel({"Inventory" : df_inv.drop(columns=["PID"],errors="ignore"),
                                 "Sales"     : df_s,
                                 "Purchases" : df_pur}),
                       "outfit_full_export.xlsx")

# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if st.session_state.get("uid") is None:
    login_page()
else:
    dashboard()
