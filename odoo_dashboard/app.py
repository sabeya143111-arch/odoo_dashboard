# ╔══════════════════════════════════════════════════════════════════╗
# ║         👗 Outfit Dashboard – v2 (Full 3‑Odoo Branch)           ║
# ║   Pages: Overview · Stock by Branch · 3‑Odoo Stock Compare      ║
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
import plotly.io as pio

# ─────────────────────────────────────────────────────────────────────────────
# GLOBALS
# ─────────────────────────────────────────────────────────────────────────────

ODOO_URL  = "https://db.swag.com.sa"
ODOO_DB   = "db2"

BATCH     = 1_000
INV_TTL   = 600
SALES_TTL = 300

# 3 Odoo configs for multi‑DB compare
ODOO_SYSTEMS = {
    "SWAG": {
        "name": "SWAG (Main)",
        "url": ODOO_URL,
        "db":  ODOO_DB,
        "user": "email-1181@swag.com.sa",
        "api_key": "7ddbd5e498eb1b039beba7dab147be6a14fa8e47",
    },
    "LAROUCHE": {
        "name": "La Rouche",
        "url": "https://odooprosys-la-rouche.odoo.com",
        "db": "odooprosys-la-rouche-production-12364313",
        "user": "operations@swag.com.sa",
        "api_key": "41a79461e550026f539b09044a9d519dc1a2ffe8",
    },
    "DIFFC": {
        "name": "Different Clothes",
        "url": "https://odooprosys-different-clothes.odoo.com",
        "db": "odooprosys-different-clothes-production-16906605",
        "user": "ziad.m@swag.com.sa",
        "api_key": "05e22b60bc95bf9fd4323e41b428590a0c6c3f28",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# STYLING
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    color: #e8dcc8;
}
.stApp { background: #0c0c0c; }
.block-container { padding-top: 1.4rem; padding-bottom: 2rem; }

h1, h2, h3, h4 {
    font-family: 'Cormorant Garamond', serif;
    color: #c9a84c;
    letter-spacing: .04em;
}

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

.card {
    background: #141414;
    border: 1px solid #252525;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 18px;
}

.js-plotly-plot .plotly { background: transparent !important; }

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

[data-testid="stDataFrame"] {
    border-radius: 10px;
    border: 1px solid #252525 !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# PLOTLY TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────

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
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────

for _k in ("uid","api_key","email"):
    if _k not in st.session_state:
        st.session_state[_k] = None

# ─────────────────────────────────────────────────────────────────────────────
# JSON‑RPC HELPERS (main SWAG dashboard)
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
# 3‑ODOO HELPERS (JSON‑RPC)
# ─────────────────────────────────────────────────────────────────────────────

def odoo_jsonrpc_auth(sys_name: str, conf: dict) -> tuple:
    url    = conf["url"].rstrip("/")
    db     = conf["db"]
    user   = conf["user"]
    apikey = conf["api_key"]

    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "common",
            "method": "authenticate",
            "args": [db, user, apikey, {}],
        },
    }
    r = requests.post(f"{url}/jsonrpc", json=payload, timeout=30)
    res = r.json()
    if "error" in res:
        raise Exception(f"{sys_name} login failed: {res['error']}")
    uid = res.get("result")
    if not uid:
        raise Exception(f"{sys_name} login failed (uid False)")
    return url, db, uid, apikey

def odoo_jsonrpc_search_read(sys_name: str, conf: dict,
                             model: str, domain: list, fields: list,
                             limit: int = 500):
    url, db, uid, apikey = odoo_jsonrpc_auth(sys_name, conf)
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [
                db,
                uid,
                apikey,
                model,
                "search_read",
                [domain],
                {"fields": fields, "limit": limit},
            ],
        },
    }
    r = requests.post(f"{url}/jsonrpc", json=payload, timeout=60)
    res = r.json()
    if "error" in res:
        raise Exception(res["error"].get("data", {}).get("message", str(res["error"])))
    return res["result"]

def compare_model_across_odoos(model_code: str) -> pd.DataFrame:
    """
    Har system ke liye total qty_available.
    Login fail ho to Product='(not connected)', Qty=0.
    """
    rows = []
    for key, conf in ODOO_SYSTEMS.items():
        name = conf["name"]
        try:
            recs = odoo_jsonrpc_search_read(
                name,
                conf,
                "product.product",
                [["default_code", "=", model_code]],
                ["id", "display_name", "default_code", "qty_available"],
            )
            if recs:
                r = recs[0]
                rows.append({
                    "System": name,
                    "Model": r.get("default_code") or model_code,
                    "Product": r.get("display_name") or "",
                    "Qty": float(r.get("qty_available") or 0.0),
                })
            else:
                rows.append({
                    "System": name,
                    "Model": model_code,
                    "Product": "(not found)",
                    "Qty": 0.0,
                })
        except Exception:
            rows.append({
                "System": name,
                "Model": model_code,
                "Product": "(not connected)",
                "Qty": 0.0,
            })
    return pd.DataFrame(rows)

def get_branch_code(location_name: str) -> str:
    if isinstance(location_name, str) and location_name.strip():
        return location_name.split("/")[0].strip() if "/" in location_name else location_name.strip()
    return "Unknown"

def branch_stock_for_model_across_odoos(model_code: str) -> pd.DataFrame:
    """
    Tino systems (SWAG + La Rouche + Different Clothes) ke liye
    stock.quant se branch‑wise qty laata hai.

    - Sirf internal locations (usage = internal)
    - quantity filter HATA diya (0 qty branches bhi aayengi)
    - limit 2000 tak badha diya
    """
    rows = []
    for key, conf in ODOO_SYSTEMS.items():
        sys_name = conf["name"]

        try:
            prods = odoo_jsonrpc_search_read(
                sys_name,
                conf,
                "product.product",
                [["default_code", "=", model_code]],
                ["id", "display_name", "default_code"],
                limit=50,
            )
            if not prods:
                continue
            prod_ids = [p["id"] for p in prods]
            prod_name = prods[0].get("display_name") or ""
            url, db, uid, apikey = odoo_jsonrpc_auth(sys_name, conf)

            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "service": "object",
                    "method": "execute_kw",
                    "args": [
                        db,
                        uid,
                        apikey,
                        "stock.quant",
                        "search_read",
                        [[
                            ["product_id", "in", prod_ids],
                            ["location_id.usage", "=", "internal"],
                        ]],
                        {
                            "fields": ["product_id", "location_id", "quantity"],
                            "limit": 2000,
                        },
                    ],
                },
            }
            r = requests.post(f"{url}/jsonrpc", json=payload, timeout=60)
            res = r.json()
            if "error" in res:
                raise Exception(
                    res["error"].get("data", {}).get("message", str(res["error"]))
                )
            quants = res["result"]

            for q in quants:
                loc = q.get("location_id")
                if isinstance(loc, (list, tuple)) and len(loc) >= 2:
                    loc_name = loc[1]
                else:
                    loc_name = ""
                qty = float(q.get("quantity") or 0.0)
                rows.append({
                    "System": sys_name,
                    "Model": model_code,
                    "Product": prod_name,
                    "LocationName": loc_name,
                    "BranchCode": get_branch_code(loc_name),
                    "Qty": qty,
                })
        except Exception:
            continue

    return pd.DataFrame(rows)

# ─────────────────────────────────────────────────────────────────────────────
# PARSE HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _m2o(val, fallback="") -> tuple:
    if isinstance(val, (list, tuple)) and len(val) >= 2:
        return int(val[0]), str(val[1])
    return 0, fallback

# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADERS (SWAG main dashboard)
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
            so_rows.append({
                "PID": pid, "Product": pname, "Qty": qty,
                "Amount": amt, "Source": "SO",
                "Date": pd.to_datetime(date),
            })

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
            pos_rows.append({
                "PID": pid, "Product": pname, "Qty": qty,
                "Amount": amt, "Source": "POS",
                "Date": pd.to_datetime(date),
            })

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

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Top 10 Categories by Stock Value")
    if not df_psi.empty and "Category" in df_psi.columns:
        top_cat = (
            df_psi.groupby("Category", as_index=False)
            .agg(
                StockQty=("StockQty","sum"),
                StockValue=("StockValue","sum"),
                SalesQty=("SalesQty","sum"),
                SalesValue=("SalesValue","sum"),
            )
            .nlargest(10, "StockValue")
        )
        col_a, col_b = st.columns([3,2])
        with col_a:
            st.plotly_chart(
                _bar(top_cat, "StockValue", "Category",
                     "Top 10 Categories – Stock Value"),
                use_container_width=True,
            )
        with col_b:
            st.plotly_chart(
                px.pie(top_cat, names="Category", values="SalesValue",
                       title="Sales Mix by Category", hole=0.42),
                use_container_width=True,
            )
        st.dataframe(
            top_cat,
            use_container_width=True,
            hide_index=True,
            column_config={
                "StockValue": _money("Stock SAR"),
                "SalesValue": _money("Sales SAR"),
                "StockQty":   _qty(),
                "SalesQty":   _qty(),
            },
        )
        st.download_button(
            "📥 Export",
            to_excel({"Top_Categories": top_cat}),
            "top_categories.xlsx",
        )
    else:
        st.info("No category data available.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Top 10 Brands by Stock Value")
    if not df_psi.empty and "Brand" in df_psi.columns:
        top_brand = (
            df_psi.groupby("Brand", as_index=False)
            .agg(
                StockQty=("StockQty","sum"),
                StockValue=("StockValue","sum"),
                SalesQty=("SalesQty","sum"),
                SalesValue=("SalesValue","sum"),
            )
            .nlargest(10, "StockValue")
        )
        col_a, col_b = st.columns([3,2])
        with col_a:
            st.plotly_chart(
                _bar(top_brand, "StockValue", "Brand",
                     "Top 10 Brands – Stock Value"),
                use_container_width=True,
            )
        with col_b:
            st.plotly_chart(
                px.pie(top_brand, names="Brand", values="SalesValue",
                       title="Sales Mix by Brand", hole=0.42),
                use_container_width=True,
            )
        st.dataframe(
            top_brand,
            use_container_width=True,
            hide_index=True,
            column_config={
                "StockValue": _money("Stock SAR"),
                "SalesValue": _money("Sales SAR"),
                "StockQty":   _qty(),
                "SalesQty":   _qty(),
            },
        )
        st.download_button(
            "📥 Export",
            to_excel({"Top_Brands": top_brand}),
            "top_brands.xlsx",
        )
    else:
        st.info("No brand data available.")
    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: STOCK BY BRANCH
# ─────────────────────────────────────────────────────────────────────────────

def page_stock_by_branch(data: dict, date_info: str):
    df_stock = data["stock_long"]

    st.markdown(
        f"## 🏬 Stock by Branch  <span style='font-size:.9rem;color:#7a7060'>({date_info})</span>",
        unsafe_allow_html=True,
    )

    if df_stock.empty:
        st.info("No internal stock data found (check stock.quant access).")
        return

    branch_agg = (
        df_stock.groupby("BranchCode", as_index=False)
        .agg(TotalQty=("Qty","sum"), TotalValue=("Value","sum"))
        .sort_values("TotalValue", ascending=False)
    )

    strip_cols = st.columns(min(len(branch_agg), 6))
    for i, row in branch_agg.head(6).iterrows():
        with strip_cols[i % 6]:
            kpi(
                row["BranchCode"],
                f"{row['TotalQty']:,.0f} pcs",
                f"{row['TotalValue']:,.0f} SAR",
            )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Stock Value by Branch")
    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.plotly_chart(
            _bar(
                branch_agg,
                "TotalValue",
                "BranchCode",
                "Stock Value (SAR) per Branch",
                horizontal=False,
                color_col="TotalValue",
            ),
            use_container_width=True,
        )
    with col_b:
        st.plotly_chart(
            px.pie(
                branch_agg,
                names="BranchCode",
                values="TotalValue",
                title="Value Share by Branch",
                hole=0.4,
            ),
            use_container_width=True,
        )

    st.dataframe(
        branch_agg,
        use_container_width=True,
        hide_index=True,
        column_config={
            "TotalQty": _qty("On Hand"),
            "TotalValue": _money("Value SAR"),
        },
    )
    st.download_button(
        "📥 Export Branch Summary",
        to_excel({"Branch_Summary": branch_agg}),
        "branch_summary.xlsx",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Branch Drill-down")
    branches     = sorted(df_stock["BranchCode"].dropna().unique().tolist())
    sel_branch   = st.selectbox("Select Branch", ["All"] + branches)
    search_prod  = st.text_input("Search Product")

    df_drill = df_stock.copy()
    if sel_branch != "All":
        df_drill = df_drill[df_drill["BranchCode"] == sel_branch]
    if search_prod:
        df_drill = df_drill[
            df_drill["Product"].str.contains(search_prod, case=False, na=False)
        ]

    df_drill_agg = (
        df_drill.groupby(["Product","LocationName","BranchCode"], as_index=False)
        .agg(Qty=("Qty","sum"), Value=("Value","sum"))
        .sort_values("Value", ascending=False)
    )

    st.caption(
        f"{len(df_drill_agg):,} rows · "
        f"Total: {df_drill_agg['Qty'].sum():,.0f} pcs, "
        f"{df_drill_agg['Value'].sum():,.0f} SAR"
    )
    st.dataframe(
        df_drill_agg,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Qty": _qty("On Hand"),
            "Value": _money("Value SAR"),
        },
    )
    st.download_button(
        "📥 Export Drill-down",
        to_excel({"Branch_Detail": df_drill_agg}),
        f"branch_detail_{sel_branch.replace(' ','_')}.xlsx",
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE: 3‑ODOO STOCK COMPARE (Premium)
# ─────────────────────────────────────────────────────────────────────────────

def page_multi_odoo_compare():
    st.markdown("""
    <div style="
        padding:18px 20px;
        border-radius:16px;
        margin-bottom:18px;
        border:1px solid #3a321f;
        background:radial-gradient(circle at 0 0,#3a2a10 0,#0c0c0c 45%);
        display:flex;align-items:center;justify-content:space-between;">
      <div>
        <div style="font-family:'Cormorant Garamond',serif;
                    font-size:1.6rem;color:#e8dcc8;letter-spacing:.06em;">
          🔁 3‑Odoo Live Stock Mirror
        </div>
        <div style="color:#9a8c70;font-size:.8rem;margin-top:4px;">
          SWAG · La Rouche · Different Clothes — real‑time model stock
        </div>
      </div>
      <div style="text-align:right;font-size:.76rem;color:#7a7060;">
        <div>Source: Odoo JSON‑RPC</div>
        <div>Updated on refresh • Live per query</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns([1.7, 1])

    with col_left:
        multi_mode = st.segmented_control(
            "Mode",
            options=["Single model","Multiple models"],
            default="Single model",
        )

        if multi_mode == "Multiple models":
            model_input = st.text_area(
                "Models / Default Codes",
                placeholder="MM0579\nRVT196\nAB1234",
                height=130,
            )
            models = [m.strip() for m in model_input.splitlines() if m.strip()]
        else:
            model_input = st.text_input(
                "Model / Default Code",
                placeholder="e.g. RVT196",
            )
            models = [model_input.strip()] if model_input.strip() else []

        st.caption("Tip: Default code hi daalna, display name nahi.")

        c1, c2, c3 = st.columns(3)
        with c1:
            show_zero = st.toggle("Zero qty show", value=True)
        with c2:
            show_branch = st.toggle(
                "Branch‑wise detail (3‑Odoo)",
                value=True,
                help="SWAG, La Rouche aur Different Clothes ka branch breakdown.",
            )
        with c3:
            sort_by_system = st.toggle(
                "System wise sort",
                value=True,
                help="On‑hand comparison ko system + model ke hisaab se sort kare.",
            )

        run_compare = st.button(
            "🚀 Compare across 3 Odoo",
            type="primary",
            use_container_width=True,
        )

    with col_right:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("###### Snapshot (last run)")
        st.caption("Latest query ke base par chhota summary.")
        if "last_compare_meta" in st.session_state:
            meta = st.session_state["last_compare_meta"]
            c1, c2 = st.columns(2)
            with c1:
                kpi("Models checked", f"{meta.get('models',0):,}")
            with c2:
                kpi("Systems online", f"{meta.get('systems_ok',0)}/3")
            st.caption(
                f"SWAG: {meta.get('swag_status','?')}  ·  "
                f"La Rouche: {meta.get('lr_status','?')}  ·  "
                f"Different Clothes: {meta.get('dc_status','?')}"
            )
        else:
            st.info("Abhi tak koi comparison run nahi hua.", icon="ℹ️")
        st.markdown("</div>", unsafe_allow_html=True)

    if not run_compare:
        return

    if not models:
        st.warning("Kam se kam 1 model/default code daalo.")
        return

    with st.spinner("Fetching live stock from 3 Odoo instances…"):
        all_rows = []
        swag_status = "N/A"
        lr_status   = "N/A"
        dc_status   = "N/A"

        for m in models:
            df_one = compare_model_across_odoos(m)

            if "SWAG (Main)" in df_one["System"].values:
                row = df_one[df_one["System"] == "SWAG (Main)"].iloc[0]
                swag_status = "OK" if row["Product"] not in ("(not connected)","(not found)") else "OFF"
            if "La Rouche" in df_one["System"].values:
                row = df_one[df_one["System"] == "La Rouche"].iloc[0]
                lr_status = "OK" if row["Product"] not in ("(not connected)","(not found)") else "OFF"
            if "Different Clothes" in df_one["System"].values:
                row = df_one[df_one["System"] == "Different Clothes"].iloc[0]
                dc_status = "OK" if row["Product"] not in ("(not connected)","(not found)") else "OFF"

            if not show_zero:
                df_one = df_one[df_one["Qty"] != 0]
            df_one.insert(0, "QueryModel", m)
            all_rows.append(df_one)

        if not all_rows:
            st.info("Koi data nahi mila (maybe sab qty 0 ya models invalid).")
            return

        df_all = pd.concat(all_rows, ignore_index=True)

    st.session_state["last_compare_meta"] = {
        "models": len(models),
        "systems_ok": len(df_all.loc[df_all["Product"] != "(not connected)","System"].unique()),
        "swag_status": swag_status,
        "lr_status": lr_status,
        "dc_status": dc_status,
    }

    if sort_by_system:
        df_all = df_all.sort_values(["QueryModel","System"])

    st.markdown("### 🔢 Total On‑Hand per System")
    st.dataframe(
        df_all,
        use_container_width=True,
        hide_index=True,
        column_config={"Qty": _qty("On Hand")},
    )

    csv = df_all.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Download CSV (Total view)",
        csv,
        file_name="three_odoo_stock_compare_total.csv",
        mime="text/csv",
    )

    if show_branch:
        st.markdown("---")
        st.markdown("### 🏬 Branch‑wise Stock (SWAG + La Rouche + Different Clothes)")
        st.caption("Tino systems ke internal warehouses/branches yahan dikh rahe hain (0 qty included).")

        with st.spinner("Branch‑wise stock.quant data laa rahe hain…"):
            all_b = []
            for m in models:
                df_b = branch_stock_for_model_across_odoos(m)
                if df_b.empty:
                    continue
                df_b.insert(0, "QueryModel", m)
                all_b.append(df_b)

        if all_b:
            df_branch = pd.concat(all_b, ignore_index=True)
            df_branch = df_branch.sort_values(["QueryModel","System","BranchCode","LocationName"])

            st.markdown("#### Qty heat (branches)")
            agg_branch = (
                df_branch.groupby(["System","BranchCode"], as_index=False)["Qty"]
                .sum()
                .sort_values("Qty", ascending=False)
            )
            fig = _bar(
                agg_branch,
                x="BranchCode",
                y="Qty",
                title="Top branches by On‑Hand Qty (3‑Odoo)",
                horizontal=False,
                color_col="System",
            )
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("#### Detail table")
            st.dataframe(
                df_branch,
                use_container_width=True,
                hide_index=True,
                column_config={"Qty": _qty("On Hand")},
            )

            csv_b = df_branch.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇️ Download CSV (Branch‑wise detail)",
                csv_b,
                file_name="three_odoo_stock_compare_branchwise.csv",
                mime="text/csv",
            )
        else:
            st.info("Branch‑wise data nahi mila (maybe access issue ya in models ke liye stock hi nahi).")

# ─────────────────────────────────────────────────────────────────────────────
# LOGIN PAGE
# ─────────────────────────────────────────────────────────────────────────────

def login_page():
    st.markdown("""
    <div style="text-align:center;padding:60px 0 30px">
      <h1 style="font-family:'Cormorant Garamond',serif;color:#c9a84c;font-size:2.8rem;margin:0">
        👗 Outfit Dashboard</h1>
      <p style="color:#5a5040;margin-top:8px;letter-spacing:.08em;font-size:.85rem">
        LIVE ODOO INSIGHTS</p>
    </div>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        with st.container(border=True):
            st.markdown("#### Connect to Odoo")
            st.text_input("URL",      value=ODOO_URL, disabled=True)
            st.text_input("Database", value=ODOO_DB,  disabled=True)
            email = st.text_input("Email",   placeholder="your@email.com")
            apik  = st.text_input("API Key", type="password",
                                  placeholder="Settings → API Keys → New")
            if st.button("Connect", type="primary", use_container_width=True):
                if not email or not apik:
                    st.error("Email and API Key are required.")
                else:
                    with st.spinner("Connecting…"):
                        try:
                            uid = odoo_login(email, apik)
                            st.session_state.uid     = uid
                            st.session_state.api_key = apik
                            st.session_state.email   = email
                            st.rerun()
                        except Exception as e:
                            st.error(f"Connection failed: {e}")
        st.caption("API Key: Odoo → Preferences → Account Security → API Keys → New")

# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD SHELL
# ─────────────────────────────────────────────────────────────────────────────

def dashboard():
    uid     = st.session_state.uid
    api_key = st.session_state.api_key
    today   = datetime.today().date()

    st.markdown("""
    <div style="text-align:center;padding:10px 0;
                background:linear-gradient(90deg,#0c0c0c,#2a2010,#0c0c0c);
                border-radius:12px;margin-bottom:20px;
                border:1px solid #2e2a1e;">
      <span style="font-family:'Cormorant Garamond',serif;color:#c9a84c;
                   font-size:1.05rem;letter-spacing:.1em;">
        👗 OUTFIT COMPANY – LIVE ODOO INSIGHTS
      </span>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown(
            f"<div style='font-family:Cormorant Garamond,serif;"
            f"color:#c9a84c;font-size:1.2rem;margin-bottom:2px'>👗 Outfit</div>"
            f"<div style='color:#7a7060;font-size:.8rem'>👤 {st.session_state.email}</div>",
            unsafe_allow_html=True,
        )
        st.divider()

        page = st.radio(
            "Navigation",
            ["📊 Overview", "🏬 Stock by Branch", "🔁 3‑Odoo Stock Compare"],
        )
        st.divider()

        from_date    = st.date_input("From Date",
                                     value=today - timedelta(days=90))
        to_date      = st.date_input("To Date", value=today)
        full_history = st.toggle("Full History", value=False)
        st.divider()

        if st.button("🔄 Refresh Data", use_container_width=True):
            load_products.clear()
            load_sales.clear()
            load_purchases.clear()
            load_warehouse_stock.clear()
            fetch_all.clear()
            for k in [k for k in st.session_state if k.startswith("data|")]:
                del st.session_state[k]
            st.rerun()

        if st.button("Logout", use_container_width=True):
            st.session_state.uid = st.session_state.api_key = None
            st.rerun()

    date_info = "Full History" if full_history else f"{from_date} → {to_date}"
    if not full_history and (to_date - from_date).days < 30 and page != "🔁 3‑Odoo Stock Compare":
        st.warning("⚠️ Selected range < 30 days – some KPIs may be misleading.")

    if page in ("📊 Overview", "🏬 Stock by Branch"):
        prog = st.progress(0, text="⏳ Initialising…")
        try:
            data = load_page_data(
                page, uid, api_key, full_history, from_date, to_date, prog)
        except Exception as e:
            prog.empty()
            st.error(f"Data load failed: {e}")
            st.stop()
        prog.empty()
    else:
        data = None

    if page == "📊 Overview":
        page_overview(data, date_info)
    elif page == "🏬 Stock by Branch":
        page_stock_by_branch(data, date_info)
    elif page == "🔁 3‑Odoo Stock Compare":
        page_multi_odoo_compare()

# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if st.session_state.get("uid") is None:
    login_page()
else:
    dashboard()
