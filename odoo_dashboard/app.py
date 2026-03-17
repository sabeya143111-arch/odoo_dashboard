# ╔══════════════════════════════════════════════════════════════════╗
# ║         👗 Outfit Dashboard – Minimal v1                        ║
# ║         Pages: Overview · Stock by Branch                       ║
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
from io import BytesIO
from datetime import datetime, timedelta
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─────────────────────────────────────────────────────────────────────────────
# GLOBALS
# ─────────────────────────────────────────────────────────────────────────────

ODOO_URL  = "https://db.swag.com.sa"
ODOO_DB   = "db2"  # isko exact DB name se replace karna hoga
BATCH     = 1_000
INV_TTL   = 600
SALES_TTL = 300

# ─────────────────────────────────────────────────────────────────────────────
# STYLING  – refined dark / gold theme, minimal CSS
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    color: #e8dcc8;
}
.stApp {
    background: #0c0c0c;
}
.block-container { padding-top: 1.4rem; padding-bottom: 2rem; }

h1, h2, h3, h4 {
    font-family: 'Cormorant Garamond', serif;
    color: #c9a84c;
    letter-spacing: .04em;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #111111;
    border-right: 1px solid #2a2a2a;
}

/* KPI card */
.kpi-wrap {
    background: #161616;
    border: 1px solid #2e2a1e;
    border-radius: 14px;
    padding: 18px 22px;
    text-align: center;
    transition: border-color .25s;
}
.kpi-wrap:hover { border-color: #c9a84c55; }
.kpi-label {
    font-size: .72rem;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: #7a7060;
    margin-bottom: 6px;
}
.kpi-value {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.7rem;
    font-weight: 700;
    color: #c9a84c;
}
.kpi-sub { font-size: .75rem; color: #5a5040; margin-top: 2px; }

/* Glass card */
.card {
    background: #141414;
    border: 1px solid #252525;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 18px;
}

/* Plotly bg override */
.js-plotly-plot .plotly { background: transparent !important; }

/* Download buttons */
.stDownloadButton > button {
    border-radius: 999px !important;
    background: linear-gradient(135deg,#c9a84c,#9a7430) !important;
    color: #000 !important;
    border: none !important;
    font-weight: 600 !important;
    font-size: .8rem !important;
    transition: filter .2s !important;
}
.stDownloadButton > button:hover { filter: brightness(1.1) !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: .5rem; }
.stTabs [data-baseweb="tab"] {
    background: #1a1a1a;
    border-radius: 999px;
    padding: 6px 14px;
    border: 1px solid #2e2a1e;
    color: #9a8c70;
    font-size: .82rem;
    transition: all .2s;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg,#c9a84c,#9a7430);
    color: #000;
    border-color: transparent;
}

/* Table */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    border: 1px solid #252525 !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# PLOTLY TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────

import plotly.io as pio

pio.templates["outfit"] = pio.templates["plotly_dark"]
pio.templates["outfit"].layout.update(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#e8dcc8"),
    colorway=["#c9a84c","#7a5c1e","#e8c97a","#5a3e10","#f0dda0"],
    legend=dict(orientation="h", yanchor="bottom", y=-0.28),
    bargap=0.22,
)
pio.templates.default = "outfit"

_GOLD = [[0,"#1a1500"],[0.5,"#9a7430"],[1,"#c9a84c"]]

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────────────────────────────────────

for _k, _v in {"uid": None, "api_key": None, "email": None}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─────────────────────────────────────────────────────────────────────────────
# JSON-RPC HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def odoo_rpc(endpoint: str, method: str, args: list):
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {"service": endpoint, "method": method, "args": args},
    }
    r   = requests.post(f"{ODOO_URL}/jsonrpc", json=payload, timeout=60)
    res = r.json()
    if "error" in res:
        raise Exception(res["error"].get("data", {}).get("message", str(res["error"])))
    return res["result"]


def odoo_login(email: str, api_key: str) -> int:
    uid = odoo_rpc("common", "authenticate", [ODOO_DB, email, api_key, {}])
    if not uid:
        raise Exception("Login failed – check your e-mail and API key.")
    return uid


@st.cache_data(show_spinner=False, ttl=SALES_TTL)
def fetch_all(_uid, _api_key, model: str, domain: list, fields: list) -> list:
    """Paginated search_read in batches of BATCH."""
    all_recs, offset = [], 0
    while True:
        recs = odoo_rpc(
            "object", "execute_kw",
            [ODOO_DB, _uid, _api_key, model, "search_read",
             [domain],
             {"fields": fields, "limit": BATCH, "offset": offset, "order": "id asc"}],
        )
        if not recs:
            break
        all_recs.extend(recs)
        if len(recs) < BATCH:
            break
        offset += BATCH
    return all_recs

# ─────────────────────────────────────────────────────────────────────────────
# PARSE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _m2o(val, fallback="") -> tuple:
    """Parse a many2one [id, name] or False → (id, name)."""
    if isinstance(val, (list, tuple)) and len(val) >= 2:
        return int(val[0]), str(val[1])
    return 0, fallback


def get_branch_code(location_name: str) -> str:
    """'B402/لمسات-1' → 'B402'; 'WH' → 'WH'; None → 'Unknown'."""
    if isinstance(location_name, str) and location_name.strip():
        return location_name.split("/")[0].strip() if "/" in location_name else location_name.strip()
    return "Unknown"

# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADERS
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False, ttl=INV_TTL)
def load_products(_uid, _api_key) -> pd.DataFrame:
    recs = fetch_all(
        _uid, _api_key,
        "product.product",
        [["active", "=", True], ["type", "=", "product"]],
        ["id", "default_code", "name", "categ_id", "brand_id",
         "qty_available", "standard_price"],
    )
    rows = []
    for p in recs:
        _, cat   = _m2o(p.get("categ_id"),  "-")
        _, brand = _m2o(p.get("brand_id"),  "-")
        qty  = max(0, p.get("qty_available") or 0)
        cost = p.get("standard_price") or 0
        rows.append({
            "PID"     : p["id"],
            "Ref"     : p.get("default_code") or "",
            "Product" : p.get("name") or "",
            "Category": cat,
            "Brand"   : brand,
            "Qty"     : qty,
            "Cost"    : cost,
            "Value"   : round(qty * cost, 2),
        })
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False, ttl=SALES_TTL)
def load_sales(_uid, _api_key, _full_history: bool,
               _from_date, _to_date) -> pd.DataFrame:
    """Combine SO + POS lines.  Source = 'SO' or 'POS'."""

    # ── Sale Orders ──────────────────────────────────────────────────────────
    so_domain = [["state", "in", ["sale", "done"]]]
    if not _full_history:
        so_domain += [
            ["date_order", ">=", str(_from_date)],
            ["date_order", "<",  str(_to_date + timedelta(days=1))],
        ]
    so_orders = fetch_all(_uid, _api_key, "sale.order", so_domain,
                          ["id", "date_order"])
    so_rows = []
    if so_orders:
        so_dt = {o["id"]: o["date_order"] for o in so_orders}
        so_lines = fetch_all(
            _uid, _api_key, "sale.order.line",
            [["order_id", "in", [o["id"] for o in so_orders]]],
            ["order_id", "product_id", "product_uom_qty", "price_subtotal"],
        )
        for r in so_lines:
            oid        = _m2o(r.get("order_id"))[0]
            pid, pname = _m2o(r.get("product_id"))
            date       = so_dt.get(oid)
            if not date:
                continue
            qty = r.get("product_uom_qty") or 0
            amt = r.get("price_subtotal")  or 0
            so_rows.append({"PID": pid, "Product": pname, "Qty": qty,
                             "Amount": amt, "Source": "SO",
                             "Date": pd.to_datetime(date)})

    # ── POS Orders ───────────────────────────────────────────────────────────
    pos_domain = [["state", "not in", ["cancel"]]]
    if not _full_history:
        pos_domain += [
            ["date_order", ">=", str(_from_date)],
            ["date_order", "<",  str(_to_date + timedelta(days=1))],
        ]
    pos_orders = fetch_all(_uid, _api_key, "pos.order", pos_domain,
                           ["id", "date_order"])
    pos_rows = []
    if pos_orders:
        pos_dt = {o["id"]: o["date_order"] for o in pos_orders}
        pos_lines = fetch_all(
            _uid, _api_key, "pos.order.line",
            [["order_id", "in", [o["id"] for o in pos_orders]]],
            ["order_id", "product_id", "qty", "price_subtotal"],
        )
        for r in pos_lines:
            oid        = _m2o(r.get("order_id"))[0]
            pid, pname = _m2o(r.get("product_id"))
            date       = pos_dt.get(oid)
            if not date:
                continue
            qty = r.get("qty")            or 0
            amt = r.get("price_subtotal") or 0
            pos_rows.append({"PID": pid, "Product": pname, "Qty": qty,
                              "Amount": amt, "Source": "POS",
                              "Date": pd.to_datetime(date)})

    return pd.concat(
        [pd.DataFrame(so_rows), pd.DataFrame(pos_rows)],
        ignore_index=True,
    )


@st.cache_data(show_spinner=False, ttl=SALES_TTL)
def load_purchases(_uid, _api_key, _full_history: bool,
                   _from_date, _to_date) -> pd.DataFrame:
    domain = [["state", "in", ["purchase", "done"]]]
    if not _full_history:
        domain += [
            ["date_order", ">=", str(_from_date)],
            ["date_order", "<",  str(_to_date + timedelta(days=1))],
        ]
    orders = fetch_all(_uid, _api_key, "purchase.order", domain,
                       ["id", "date_order"])
    if not orders:
        return pd.DataFrame()
    dt_map = {o["id"]: o["date_order"] for o in orders}
    lines  = fetch_all(
        _uid, _api_key, "purchase.order.line",
        [["order_id", "in", [o["id"] for o in orders]]],
        ["order_id", "product_id", "product_qty", "price_subtotal"],
    )
    rows = []
    for r in lines:
        oid        = _m2o(r.get("order_id"))[0]
        pid, pname = _m2o(r.get("product_id"))
        date       = dt_map.get(oid)
        if not date:
            continue
        rows.append({
            "PID"    : pid,
            "Product": pname,
            "Qty"    : r.get("product_qty")    or 0,
            "Amount" : r.get("price_subtotal") or 0,
            "Date"   : pd.to_datetime(date),
        })
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False, ttl=INV_TTL)
def load_warehouse_stock(_uid, _api_key) -> pd.DataFrame:
    """
    Returns long-form stock per location:
    PID, Product, LocationName, BranchCode, Qty, Value
    """
    quants = fetch_all(
        _uid, _api_key, "stock.quant",
        [["location_id.usage", "=", "internal"], ["quantity", ">", 0]],
        ["product_id", "location_id", "quantity", "value"],
    )
    rows = []
    for q in quants:
        pid, pname = _m2o(q.get("product_id"))
        _, loc     = _m2o(q.get("location_id"))
        qty = max(0, q.get("quantity") or 0)
        val = q.get("value") or 0
        rows.append({
            "PID"         : pid,
            "Product"     : pname,
            "LocationName": loc,
            "BranchCode"  : get_branch_code(loc),
            "Qty"         : qty,
            "Value"       : round(val, 2),
        })
    return pd.DataFrame(rows)


def build_psi_view(df_pur: pd.DataFrame,
                   df_sales: pd.DataFrame,
                   df_inv: pd.DataFrame) -> pd.DataFrame:
    """Per-product PSI: PurQty/Value, SalesQty/Value, StockQty/Value, SellThrough."""

    pur_agg = (
        df_pur.groupby("PID", as_index=False)
              .agg(PurQty=("Qty","sum"), PurValue=("Amount","sum"))
        if not df_pur.empty
        else pd.DataFrame(columns=["PID","PurQty","PurValue"])
    )
    sal_agg = (
        df_sales.groupby("PID", as_index=False)
                .agg(SalesQty=("Qty","sum"), SalesValue=("Amount","sum"))
        if not df_sales.empty
        else pd.DataFrame(columns=["PID","SalesQty","SalesValue"])
    )

    inv_sub = (
        df_inv[["PID","Product","Category","Brand","Qty","Value"]]
        .rename(columns={"Qty":"StockQty","Value":"StockValue"})
    )

    df = (inv_sub
          .merge(pur_agg, on="PID", how="left")
          .merge(sal_agg, on="PID", how="left"))

    for col in ("PurQty","PurValue","SalesQty","SalesValue"):
        df[col] = df[col].fillna(0)

    df["SellThrough"] = np.where(
        df["PurQty"] > 0,
        (df["SalesQty"] / df["PurQty"] * 100).clip(upper=999),
        np.nan,
    )
    return df


def load_page_data(page: str, uid: int, api_key: str,
                   full_history: bool, from_date, to_date,
                   prog) -> dict:
    """Both pages use the same dataset; cache per session via st.session_state."""

    cache_key = f"data|{uid}|{full_history}|{from_date}|{to_date}"
    if cache_key in st.session_state:
        prog.progress(100, text="✅ Loaded from cache")
        return st.session_state[cache_key]

    prog.progress(8, text="📡 Launching parallel fetches…")

    with ThreadPoolExecutor(max_workers=5) as pool:
        f_prod  = pool.submit(load_products,         uid, api_key)
        f_sales = pool.submit(load_sales,            uid, api_key, full_history, from_date, to_date)
        f_pur   = pool.submit(load_purchases,        uid, api_key, full_history, from_date, to_date)
        f_stock = pool.submit(load_warehouse_stock,  uid, api_key)
        names   = {f_prod:"Products", f_sales:"Sales",
                   f_pur:"Purchases", f_stock:"WH Stock"}
        done, res = 0, {}
        for fut in as_completed([f_prod, f_sales, f_pur, f_stock]):
            done += 1
            prog.progress(8 + int(done / 4 * 80),
                          text=f"✅ {names[fut]} loaded ({done}/4)")
            res[fut] = fut.result()

    df_prod  = res[f_prod]
    df_sales = res[f_sales]
    df_pur   = res[f_pur]
    df_stock = res[f_stock]

    if not df_sales.empty and not df_prod.empty:
        meta = df_prod[["PID","Category","Brand"]].drop_duplicates("PID")
        df_sales = df_sales.merge(meta, on="PID", how="left")
        df_sales["Category"] = df_sales.get("Category", pd.Series(dtype=str)).fillna("-")
        df_sales["Brand"]    = df_sales.get("Brand",    pd.Series(dtype=str)).fillna("-")

    df_psi = build_psi_view(df_pur, df_sales, df_prod)

    prog.progress(100, text="✅ All data ready")

    result = {
        "products"  : df_prod,
        "sales"     : df_sales,
        "purchases" : df_pur,
        "stock_long": df_stock,
        "psi"       : df_psi,
    }
    st.session_state[cache_key] = result
    return result

# ─────────────────────────────────────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def kpi(label: str, value: str, sub: str = ""):
    st.markdown(
        f'<div class="kpi-wrap">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-sub">{sub}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _money(label="SAR"):  return st.column_config.NumberColumn(label, format="%.0f")
def _qty(label="Qty"):    return st.column_config.NumberColumn(label, format="%d")
def _pct(label="%"):      return st.column_config.NumberColumn(label, format="%.1f%%")


def _bar(df, x, y, title, horizontal=True, color_col=None):
    kwargs = dict(
        x=x if not horizontal else y,
        y=y if not horizontal else x,
        orientation="h" if horizontal else "v",
        title=title,
        color=color_col or (y if horizontal else x),
        color_continuous_scale=_GOLD,
    )
    fig = px.bar(df, **kwargs)
    if horizontal:
        fig.update_layout(yaxis=dict(autorange="reversed"), coloraxis_showscale=False)
    else:
        fig.update_layout(coloraxis_showscale=False, xaxis_tickangle=-40)
    return fig


def to_excel(sheets: dict) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, df in sheets.items():
            df.to_excel(w, sheet_name=name[:31], index=False)
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────

def page_overview(data: dict, date_info: str):
    df_sales = data["sales"]
    df_pur   = data["purchases"]
    df_psi   = data["psi"]

    st.markdown(
        f"## 📊 Overview  <span style='font-size:.9rem;color:#7a7060'>({date_info})</span>",
        unsafe_allow_html=True,
    )

    total_pur   = df_pur["Amount"].sum()   if not df_pur.empty   else 0
    total_sales = df_sales["Amount"].sum() if not df_sales.empty else 0
    units_sold  = df_sales["Qty"].sum()    if not df_sales.empty else 0
    stock_val   = df_psi["StockValue"].sum() if not df_psi.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("Total Purchases",  f"{total_pur:,.0f}",   "SAR")
    with c2: kpi("Total Sales",      f"{total_sales:,.0f}", "SAR")
    with c3: kpi("Units Sold",       f"{units_sold:,.0f}",  "pcs")
    with c4: kpi("Current Stock Value", f"{stock_val:,.0f}", "SAR")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Top 10 Products by Stock Value")
    if not df_psi.empty:
        top_prod = (
            df_psi.groupby("Product", as_index=False)["StockValue"]
            .sum()
            .nlargest(10, "StockValue")
        )
        st.plotly_chart(
            _bar(top_prod, "StockValue", "Product",
                 "Top 10 Products – Stock Value (SAR)"),
            use_container_width=True,
        )
        st.dataframe(
            top_prod.rename(columns={"StockValue":"Stock Value (SAR)"}),
            use_container_width=True,
            hide_index=True,
            column_config={"Stock Value (SAR)": _money()},
        )
        st.download_button(
            "📥 Export",
            to_excel({"Top_Products": top_prod}),
            "top_products.xlsx",
        )
    else:
        st.info("No PSI data available.")
    st.markdown("</div>", unsafe_allow_html=True)

# (Yahan se aage ka Overview + Stock by Branch + login_page + dashboard + entry
# tumhare original clean code jaisa hi rahe – agar chaho to woh bhi paste kar sakta hoon)
