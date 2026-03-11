import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.io as pio
from io import BytesIO
from datetime import datetime, timedelta
import numpy as np

# Globals
ODOO_URL = "https://odooprosys-la-rouche.odoo.com"
ODOO_DB = "odooprosys-la-rouche-production-12364313"
LOW_THRESHOLD = 5

# Plotly global theme
pio.templates.default = "plotly_white"
pio.templates["plotly_white"].layout.update(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=-0.25),
    bargap=0.22,
    transition_duration=1000,
)

st.set_page_config(page_title="👗 Outfit Dashboard", page_icon="👗", layout="wide")

# Luxury CSS (Outfit-branded)
st.markdown("""
<style>
.stApp {
    background: radial-gradient(circle at top left, #1a1a1a 0%, #0d0d0d 45%, #000000 100%);
    color: #f0e6d2;
    font-family: "Playfair Display", serif;
}
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 1.5rem;
}
h1, h2, h3, h4 {
    color: #d4af37;
    text-shadow: 0 0 5px rgba(212,175,55,0.5);
}
.glass-card {
    background: rgba(10,10,10,0.85);
    border-radius: 20px;
    padding: 20px 22px;
    border: 1px solid rgba(212,175,55,0.3);
    box-shadow: 0 20px 50px rgba(0,0,0,0.7);
    backdrop-filter: blur(16px);
    animation: fadeInUp 1s ease-out;
}
.kpi-card {
    background: linear-gradient(135deg, rgba(212,175,55,0.15), rgba(184,134,11,0.1));
    border-radius: 18px;
    padding: 16px 20px;
    border: 1px solid rgba(212,175,55,0.6);
    box-shadow: 0 14px 35px rgba(0,0,0,0.6);
    backdrop-filter: blur(14px);
    transition: all 0.3s ease-out;
    animation: pulseGlow 2s infinite alternate;
}
.kpi-card:hover {
    transform: translateY(-5px) scale(1.05);
    box-shadow: 0 20px 45px rgba(212,175,55,0.3);
}
.kpi-title {
    font-size: 0.8rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #c0c0c0;
}
.kpi-value {
    font-size: 1.4rem;
    font-weight: 700;
    color: #f0e6d2;
}
.kpi-sub {
    font-size: 0.8rem;
    color: #a9a9a9;
}
.status-pill {
    border-radius: 999px;
    padding: 3px 12px;
    font-size: 0.75rem;
    font-weight: 600;
    animation: glow 1.5s infinite alternate;
}
.status-OK {
    background: rgba(0,128,0,0.15);
    color: #90ee90;
    border: 1px solid rgba(0,128,0,0.6);
}
.status-LOW {
    background: rgba(255,165,0,0.15);
    color: #ffd700;
    border: 1px solid rgba(255,165,0,0.6);
}
.status-OUT {
    background: rgba(139,0,0,0.15);
    color: #ff6347;
    border: 1px solid rgba(139,0,0,0.6);
}
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d0d0d 0%, #000000 60%, #1a1a1a 100%);
    border-right: 1px solid rgba(212,175,55,0.4);
}
section[data-testid="stSidebar"] .block-container {
    padding-top: 1.6rem;
}
[data-testid="stSidebar"] .stRadio > label, [data-testid="stSidebar"] .stButton button {
    transition: transform 0.3s;
}
[data-testid="stSidebar"] .stRadio > label:hover, [data-testid="stSidebar"] .stButton button:hover {
    transform: scale(1.05);
}
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid rgba(212,175,55,0.4);
}
.stDownloadButton button {
    border-radius: 999px;
    background: linear-gradient(135deg, #d4af37, #b8860b) !important;
    color: #000 !important;
    border: none;
    font-weight: 600;
    transition: all 0.3s;
}
.stDownloadButton button:hover {
    filter: brightness(1.1);
    transform: scale(1.05);
}
.stTabs [data-baseweb="tab-list"] {
    gap: 0.6rem;
}
.stTabs [data-baseweb="tab"] {
    background-color: rgba(10,10,10,0.9);
    border-radius: 999px;
    padding: 7px 12px;
    border: 1px solid rgba(212,175,55,0.4);
    transition: all 0.3s;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #d4af37, #b8860b);
    color: #000;
    border-color: transparent;
}
.stTabs [data-baseweb="tab"]:hover {
    transform: scale(1.05);
}
.small-caption {
    font-size: 0.8rem;
    color: #a9a9a9;
}
.login-box {
    max-width: 400px;
    margin: 0 auto;
    animation: fadeIn 1s ease-in;
}
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes pulseGlow {
    from { box-shadow: 0 14px 35px rgba(0,0,0,0.6); }
    to { box-shadow: 0 14px 35px rgba(212,175,55,0.2); }
}
@keyframes glow {
    from { text-shadow: 0 0 3px currentColor; }
    to { text-shadow: 0 0 8px currentColor; }
}
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}
</style>
""", unsafe_allow_html=True)

# Color maps
STATUS_COLORS = {"OK": "#90ee90", "LOW": "#ffd700", "OUT": "#ff6347"}

# Odoo helpers
def odoo_rpc(endpoint, method, *args):
    payload = {"jsonrpc": "2.0", "method": "call", "params": {"service": endpoint, "method": method, "args": list(args)}}
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

def search_read(uid, k, model, domain, fields, limit=500, offset=0):
    return odoo_rpc("object", "execute_kw", ODOO_DB, uid, k, model, "search_read",
                    [domain], {"fields": fields, "limit": limit, "offset": offset, "order": "id asc"})

def fetch_all(uid, k, model, domain, fields, batch=500):
    all_recs, offset = [], 0
    ph = st.empty()
    while True:
        recs = search_read(uid, k, model, domain, fields, limit=batch, offset=offset)
        if not recs:
            break
        all_recs.extend(recs)
        ph.caption(f"Loading {model}: {len(all_recs)} records...")
        if len(recs) < batch:
            break
        offset += batch
    ph.empty()
    return all_recs

# Load sales (sale orders) with Source + OrderID
@st.cache_data(show_spinner=False, ttl=300)
def load_sal(_uid, _k, _full_history, _from_date, _to_date):
    order_domain = [["state", "in", ["sale", "done"]]]
    if not _full_history:
        order_domain.append(["date_order", ">=", str(_from_date)])
        order_domain.append(["date_order", "<", str(_to_date + timedelta(days=1))])
    orders = fetch_all(_uid, _k, "sale.order", order_domain, ["id", "date_order"])
    order_ids = [o["id"] for o in orders]
    order_date_map = {o["id"]: o["date_order"] for o in orders}
    line_domain = [["order_id", "in", order_ids]]
    recs = fetch_all(_uid, _k, "sale.order.line", line_domain, ["product_id", "product_uom_qty", "price_subtotal", "order_id"])
    rows = []
    for r in recs:
        order_id = r["order_id"][0] if r.get("order_id") else None
        date = order_date_map.get(order_id)
        if date and order_id:
            try:
                date_parsed = pd.to_datetime(date)
                rows.append({
                    "PID": r["product_id"][0] if r.get("product_id") else 0,
                    "Product": r["product_id"][1] if r.get("product_id") else "-",
                    "Qty": r.get("product_uom_qty") or 0,
                    "Amount": r.get("price_subtotal") or 0,
                    "Date": date_parsed,
                    "Source": "SO",
                    "OrderID": order_id
                })
            except:
                continue
    return pd.DataFrame(rows)

# Load POS sales with Source + OrderID
@st.cache_data(show_spinner=False, ttl=300)
def load_pos_sales(_uid, _k, _full_history, _from_date, _to_date):
    order_domain = [["state", "in", ["paid", "invoiced", "done"]]]
    if not _full_history:
        order_domain.append(["date_order", ">=", str(_from_date)])
        order_domain.append(["date_order", "<", str(_to_date + timedelta(days=1))])
    orders = fetch_all(_uid, _k, "pos.order", order_domain, ["id", "date_order"])
    order_ids = [o["id"] for o in orders]
    order_date_map = {o["id"]: o["date_order"] for o in orders}
    line_domain = [["order_id", "in", order_ids]]
    recs = fetch_all(_uid, _k, "pos.order.line", line_domain, ["product_id", "qty", "price_subtotal", "order_id"])
    rows = []
    for r in recs:
        order_id = r["order_id"][0] if r.get("order_id") else None
        date = order_date_map.get(order_id)
        if date and order_id:
            try:
                date_parsed = pd.to_datetime(date)
                rows.append({
                    "PID": r["product_id"][0] if r.get("product_id") else 0,
                    "Product": r["product_id"][1] if r.get("product_id") else "-",
                    "Qty": r.get("qty") or 0,
                    "Amount": r.get("price_subtotal") or 0,
                    "Date": date_parsed,
                    "Source": "POS",
                    "OrderID": order_id
                })
            except:
                continue
    return pd.DataFrame(rows)

# Load purchases with Supplier
@st.cache_data(show_spinner=False, ttl=300)
def load_pur(_uid, _k, _full_history, _from_date, _to_date):
    order_domain = [["state", "in", ["purchase", "done"]]]
    if not _full_history:
        order_domain.append(["date_order", ">=", str(_from_date)])
        order_domain.append(["date_order", "<", str(_to_date + timedelta(days=1))])
    orders = fetch_all(_uid, _k, "purchase.order", order_domain, ["id", "date_order", "partner_id"])
    order_ids = [o["id"] for o in orders]
    order_date_map = {o["id"]: o["date_order"] for o in orders}
    order_supplier_map = {o["id"]: (o.get("partner_id") or [0, "-"])[1] for o in orders}
    line_domain = [["order_id", "in", order_ids]]
    recs = fetch_all(_uid, _k, "purchase.order.line", line_domain, ["product_id", "product_qty", "price_subtotal", "order_id"])
    rows = []
    for r in recs:
        order_id = r["order_id"][0] if r.get("order_id") else None
        date = order_date_map.get(order_id)
        if date:
            try:
                date_parsed = pd.to_datetime(date)
                rows.append({
                    "PID": r["product_id"][0] if r.get("product_id") else 0,
                    "Product": r["product_id"][1] if r.get("product_id") else "-",
                    "Qty": r.get("product_qty") or 0,
                    "Amount": r.get("price_subtotal") or 0,
                    "Date": date_parsed,
                    "Supplier": order_supplier_map.get(order_id, "-")
                })
            except:
                continue
    return pd.DataFrame(rows)

# Load clean inventory
@st.cache_data(show_spinner=False, ttl=300)
def load_clean_inventory(_uid, _k, _full_history, _from_date, _to_date, _non_moving_days):
    fields = ["id", "default_code", "name", "categ_id", "brand_id", "qty_available", "virtual_available", "standard_price"]
    recs = fetch_all(_uid, _k, "product.product", [["active", "=", True], ["type", "=", "product"]], fields)
    rows = []
    for p in recs:
        qty = max(0, p.get("qty_available") or 0)
        cost = p.get("standard_price") or 0
        rows.append({
            "PID": p["id"],
            "Ref": p.get("default_code") or "",
            "Product": p.get("name") or "",
            "Category": p["categ_id"][1] if p.get("categ_id") else "-",
            "Brand": p["brand_id"][1] if p.get("brand_id") else "-",
            "Qty": qty,
            "Forecast": p.get("virtual_available") or 0,
            "Cost": cost,
            "Value": round(qty * cost, 2),
            "Status": "OUT" if qty <= 0 else ("LOW" if qty <= LOW_THRESHOLD else "OK")
        })
    df_inv = pd.DataFrame(rows)
    total_products_raw = len(df_inv)
    df_sal = load_sal(_uid, _k, _full_history, _from_date, _to_date)
    df_pos = load_pos_sales(_uid, _k, _full_history, _from_date, _to_date)
    df_sales_all = pd.concat([df_sal, df_pos], ignore_index=True)
    if not df_sales_all.empty:
        last_sale = df_sales_all.groupby('PID')['Date'].max().reset_index(name='LastSaleDate')
        df_inv = df_inv.merge(last_sale, on='PID', how='left')
    else:
        df_inv['LastSaleDate'] = pd.NaT
    df_inv['NonMoving'] = False
    mask = df_inv['Qty'] > 0
    today = datetime.today().date()
    today_dt = pd.to_datetime(today)
    threshold_date = today_dt - timedelta(days=_non_moving_days)
    df_inv.loc[mask, 'NonMoving'] = df_inv.loc[mask, 'LastSaleDate'].isna() | (df_inv.loc[mask, 'LastSaleDate'] < threshold_date)
    nm_value = df_inv[df_inv['NonMoving'] & (df_inv['Value'] > 0)]['Value'].sum()
    total_value = df_inv[df_inv['Value'] > 0]['Value'].sum()
    nonmoving_pct = round((nm_value / total_value * 100) if total_value else 0, 2)
    # Non-moving for sold styles
    sold_styles = df_inv[~df_inv['LastSaleDate'].isna() & (df_inv['Value'] > 0)]
    nm_value_sold = sold_styles[sold_styles['NonMoving']]['Value'].sum()
    total_value_sold = sold_styles['Value'].sum()
    nonmoving_pct_sold = round((nm_value_sold / total_value_sold * 100) if total_value_sold else 0, 2)
    # Never sold
    never_sold_df = df_inv[df_inv['LastSaleDate'].isna() & (df_inv['Value'] > 0)]
    never_sold_value = never_sold_df['Value'].sum()
    never_sold_count = len(never_sold_df)
    # Stock ageing
    df_pur = load_pur(_uid, _k, True, _from_date, _to_date)  # Use full history for first in
    if not df_pur.empty:
        first_in = df_pur.groupby('PID')['Date'].min().reset_index(name='FirstInDate')
        df_inv = df_inv.merge(first_in, on='PID', how='left')
    else:
        df_inv['FirstInDate'] = pd.NaT
    df_inv['DaysInStock'] = (today_dt - df_inv['FirstInDate']).dt.days.where(df_inv['Qty'] > 0, np.nan)
    return df_inv, df_sales_all, nonmoving_pct, total_products_raw, total_value, nm_value, never_sold_value, never_sold_count, nonmoving_pct_sold


# ==================== BRANCH SALES DATA LOADER ====================
@st.cache_data(show_spinner=False, ttl=300)
def load_branch_sales(_uid, _k, _full_history, _from_date, _to_date):
    """
    Loads sale.order + sale.order.line with branch info (team_id, warehouse_id).
    Only sale orders in confirmed/done state. No POS.
    Returns a flat DataFrame with one row per order line, enriched with branch data.
    """
    # Step 1 – fetch sale orders with branch fields
    order_domain = [["state", "in", ["sale", "done"]]]
    if not _full_history:
        order_domain.append(["date_order", ">=", str(_from_date)])
        order_domain.append(["date_order", "<", str(_to_date + timedelta(days=1))])

    orders = fetch_all(
        _uid, _k, "sale.order", order_domain,
        ["id", "date_order", "team_id", "warehouse_id"]
    )
    if not orders:
        return pd.DataFrame()

    order_ids          = [o["id"] for o in orders]
    order_date_map     = {o["id"]: o["date_order"] for o in orders}
    order_branch_map   = {
        o["id"]: (o.get("team_id") or [0, "No Branch"])[1] for o in orders
    }
    order_warehouse_map = {
        o["id"]: (o.get("warehouse_id") or [0, "No Warehouse"])[1] for o in orders
    }

    # Step 2 – fetch order lines
    line_domain = [["order_id", "in", order_ids]]
    recs = fetch_all(
        _uid, _k, "sale.order.line", line_domain,
        ["product_id", "product_uom_qty", "price_subtotal", "order_id"]
    )

    rows = []
    for r in recs:
        order_id = r["order_id"][0] if r.get("order_id") else None
        date_raw = order_date_map.get(order_id)
        if not date_raw or not order_id:
            continue
        try:
            date_parsed = pd.to_datetime(date_raw)
        except Exception:
            continue
        rows.append({
            "OrderID"  : order_id,
            "Date"     : date_parsed,
            "Branch"   : order_branch_map.get(order_id, "No Branch"),
            "Warehouse": order_warehouse_map.get(order_id, "No Warehouse"),
            "PID"      : r["product_id"][0] if r.get("product_id") else 0,
            "Product"  : r["product_id"][1] if r.get("product_id") else "-",
            "Qty"      : r.get("product_uom_qty") or 0,
            "Amount"   : r.get("price_subtotal") or 0,
        })

    return pd.DataFrame(rows)


# Validation checks
def get_validation_checks(df_inv):
    negative_cost = df_inv[df_inv['Cost'] < 0]
    zero_cost_with_qty = df_inv[(df_inv['Cost'] == 0) & (df_inv['Qty'] > 0)]
    high_cost = df_inv[df_inv['Cost'] > df_inv['Cost'].quantile(0.99)] if not df_inv.empty else pd.DataFrame()
    return {
        "Negative Cost": negative_cost,
        "Zero Cost with Qty": zero_cost_with_qty,
        "High Cost Outliers": high_cost
    }

# Excel export
def to_excel(dfs):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, df in dfs.items():
            df.to_excel(w, sheet_name=name[:31], index=False)
    return buf.getvalue()

# Excel export – pivot keeps index (branch names as rows/cols)
def to_excel_with_index(dfs_no_index, dfs_with_index=None):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, df in dfs_no_index.items():
            df.to_excel(w, sheet_name=name[:31], index=False)
        if dfs_with_index:
            for name, df in dfs_with_index.items():
                df.to_excel(w, sheet_name=name[:31], index=True)
    return buf.getvalue()

# Session state
for k, v in {"uid": None, "api_key": None, "uname": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Login page (Outfit branding)
def login_page():
    st.markdown("<div style='text-align:center;padding:40px 0 20px'>"
                "<h1 style='color:#d4af37'>👗 Outfit Dashboard</h1>"
                "<p style='color:#a9a9a9'>Live Odoo insights for Outfit Company</p>"
                "</div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1,1.1,1])
    with col:
        with st.container(border=True):
            st.markdown("#### 🔗 Connect to Odoo")
            st.text_input("URL", value=ODOO_URL, disabled=True)
            st.text_input("Database", value=ODOO_DB, disabled=True)
            user = st.text_input("Email", placeholder="your@email.com")
            key = st.text_input("API Key", type="password", placeholder="Settings → API Keys → New")
            if st.button("Connect", type="primary", use_container_width=True):
                if not user or not key:
                    st.error("Email and API Key required")
                else:
                    with st.spinner("Connecting..."):
                        try:
                            uid = odoo_login(user, key)
                            st.session_state.uid = uid
                            st.session_state.api_key = key
                            st.session_state.uname = user
                            st.rerun()
                        except Exception as e:
                            st.error(f"Connection failed: {e}")
        st.caption("API Key: Odoo → Preferences → Account Security → API Keys → New")

# Dashboard
def dashboard():
    uid = st.session_state.uid
    key = st.session_state.api_key

    # Live banner
    st.markdown("""
    <div style="text-align: center; padding: 12px; background: linear-gradient(90deg, #1a1a1a, #d4af37, #1a1a1a); 
    border-radius: 15px; margin-bottom: 20px; box-shadow: 0 0 20px rgba(212,175,55,0.3);">
    <h2 style="color: #000; margin:0; font-size:1.1rem;">👗 Outfit Company – Live Odoo Insights</h2>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown(f"### 👗 Outfit Company  \n👤 {st.session_state.uname}")
        st.divider()
        page = st.radio(
            "Navigation",
            [
                "📦 Inventory",
                "🛒 Sales",
                "🏪 Purchase",
                "📁 Category",
                "🏷️ Brand",
                "📊 Combined",
                "🏢 Branch Sales",   # ← NEW
                "💼 Power BI",
            ]
        )
        st.divider()
        default_from = datetime.today().date() - timedelta(days=90)
        default_to = datetime.today().date()
        from_date = st.date_input("From Date", value=default_from)
        to_date = st.date_input("To Date", value=default_to)
        full_history = st.toggle("Full History", value=False)
        non_moving_days = st.selectbox("Non-Moving Days", [30, 60, 90, 180], index=2)
        debug = st.toggle("Debug Mode", value=False)
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        if st.button("Logout", use_container_width=True):
            st.session_state.uid = None
            st.session_state.api_key = None
            st.rerun()

    # ── Branch Sales page skips the heavy inventory load ──────────────────────
    if page == "🏢 Branch Sales":
        branch_sales_page(uid, key, full_history, from_date, to_date)
        return

    # Load data once (all other pages)
    with st.spinner("Loading Outfit data from Odoo..."):
        try:
            df_inv, df_sales_all, nonmoving_pct, total_products_raw, total_value, nm_value, never_sold_value, never_sold_count, nonmoving_pct_sold = load_clean_inventory(uid, key, full_history, from_date, to_date, non_moving_days)
            df_pur = load_pur(uid, key, full_history, from_date, to_date)
        except Exception as e:
            st.error(f"Data load failed: {e}")
            st.stop()

    # Enrich sales & purchases with Category/Brand (once)
    product_info = df_inv[['PID', 'Category', 'Brand']].drop_duplicates()
    if not df_sales_all.empty:
        df_sales_all = df_sales_all.merge(product_info, on='PID', how='left')
    if not df_pur.empty:
        df_pur = df_pur.merge(product_info, on='PID', how='left')

    # Date range info
    date_info = "Full History" if full_history else f"From {from_date} to {to_date}"
    days_in_range = (to_date - from_date).days if not full_history else float('inf')
    if days_in_range < 30 and not full_history:
        st.warning("Selected date range is less than 30 days. Some KPIs may be misleading due to limited data.")

    # Validation checks
    validation = get_validation_checks(df_inv)

    # Sell-through approximation (assuming period purchases and sales)
    if not df_sales_all.empty and not df_pur.empty:
        sales_qty = df_sales_all.groupby('PID')['Qty'].sum().reset_index(name='SalesQty')
        pur_qty = df_pur.groupby('PID')['Qty'].sum().reset_index(name='PurQty')
        df_st = df_inv.merge(sales_qty, on='PID', how='left').merge(pur_qty, on='PID', how='left').fillna(0)
        df_st['OpeningQtyEst'] = df_st['Qty'] + df_st['SalesQty'] - df_st['PurQty']
        df_st['OpeningQtyEst'] = df_st['OpeningQtyEst'].clip(lower=0)
        df_st['SellThrough'] = np.where((df_st['OpeningQtyEst'] + df_st['PurQty']) > 0, (df_st['SalesQty'] / (df_st['OpeningQtyEst'] + df_st['PurQty'])) * 100, 0)
    else:
        df_st = pd.DataFrame()

    # OOS risk simple: if Forecast < 0
    oos_risk_count = len(df_inv[df_inv['Forecast'] < 0]) if not df_inv.empty else 0

    # Stock ageing buckets
    if 'DaysInStock' in df_inv.columns:
        bins = [0, 90, 180, 365, np.inf]
        labels = ['0-90', '91-180', '181-365', '365+']
        df_inv['AgeBucket'] = pd.cut(df_inv['DaysInStock'], bins=bins, labels=labels)
        age_agg = df_inv.groupby('AgeBucket', observed=True).agg(Count=('PID', 'count'), Value=('Value', 'sum')).reset_index()
    else:
        age_agg = pd.DataFrame()

    # Debug (toggle controlled)
    if debug:
        st.write(f"Debug: Total stockable products: {total_products_raw}")
        st.write(f"Debug: Inventory value: {total_value:,.0f}")
        non_moving = df_inv[df_inv['NonMoving']]
        nm_count = len(non_moving)
        st.write(f"Debug: Non-moving count: {nm_count} | value: {nm_value:,.0f}")

    # ==================== INVENTORY PAGE ====================
    if page == "📦 Inventory":
        st.markdown(f"### 👗 Outfit Inventory Overview ({date_info})")
        total_ok = int((df_inv.Status == "OK").sum())
        total_low = int((df_inv.Status == "LOW").sum())
        total_out = int((df_inv.Status == "OUT").sum())
        stock_value = df_inv.Value.sum()

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">TOTAL STYLES</div><div class="kpi-value">{total_products_raw:,}</div><div class="kpi-sub">Stockable</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">IN STOCK (OK)</div><div class="kpi-value">{total_ok:,}</div><div class="kpi-sub">Healthy</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">LOW STOCK</div><div class="kpi-value">{total_low:,}</div><div class="kpi-sub">≤ {LOW_THRESHOLD}</div></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">OUT OF STOCK</div><div class="kpi-value">{total_out:,}</div><div class="kpi-sub">Zero</div></div>', unsafe_allow_html=True)
        with c5:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">TOTAL VALUE</div><div class="kpi-value">{stock_value:,.0f}</div><div class="kpi-sub">SAR</div></div>', unsafe_allow_html=True)
        with c6:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">NON MOVING %</div><div class="kpi-value">{nonmoving_pct}%</div><div class="kpi-sub">Whole Catalog</div></div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            sc = df_inv.Status.value_counts().reset_index()
            sc.columns = ["Status", "Count"]
            fig = px.pie(sc, names="Status", values="Count", color="Status", color_discrete_map=STATUS_COLORS, hole=0.4, title="Stock Status")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            t10 = df_inv.nlargest(10, "Value")
            fig = px.bar(t10, x="Value", y="Product", orientation="h", color="Status", color_discrete_map=STATUS_COLORS, title="Top 10 Styles by Value")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

        # Low Stock Alert
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Low Stock Styles Alert")
        low_df = df_inv[df_inv.Status.isin(["LOW", "OUT"])].sort_values("Qty").head(50)
        if low_df.empty:
            st.info("No low/out-of-stock styles.")
        else:
            st.dataframe(low_df.drop(columns=["PID"]), use_container_width=True)
            st.download_button("Export Low Stock", to_excel({"Low_Stock": low_df.drop(columns=["PID"])}), "low_stock.xlsx")
        st.markdown("</div>", unsafe_allow_html=True)

        # Stock Ageing
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Stock Ageing")
        if not age_agg.empty:
            fig_age = px.bar(age_agg, x="AgeBucket", y="Value", title="Stock Value by Age Bucket")
            st.plotly_chart(fig_age, use_container_width=True)
            st.dataframe(age_agg, use_container_width=True)
        else:
            st.info("No ageing data available.")
        st.markdown("</div>", unsafe_allow_html=True)

        # Inventory filters + detail view
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Full Inventory")
        colf = st.columns([2,1,1,1,1,1])
        with colf[0]:
            srch = st.text_input("Search Ref / Style")
        with colf[1]:
            fstat = st.selectbox("Status", ["All", "OK", "LOW", "OUT"])
        with colf[2]:
            fcat = st.selectbox("Category", ["All"] + sorted(df_inv.Category.unique().tolist()))
        with colf[3]:
            fbrd = st.selectbox("Brand", ["All"] + sorted(df_inv.Brand.unique().tolist()))
        with colf[4]:
            fmov = st.selectbox("Movement", ["All", "Moving", "Non-Moving"])
        with colf[5]:
            min_qty = st.number_input("Min Qty", min_value=0, value=0)

        df_f = df_inv.copy()
        if srch:
            df_f = df_f[df_f.Product.str.contains(srch, case=False, na=False) | df_f.Ref.str.contains(srch, case=False, na=False)]
        if fstat != "All":
            df_f = df_f[df_f.Status == fstat]
        if fcat != "All":
            df_f = df_f[df_f.Category == fcat]
        if fbrd != "All":
            df_f = df_f[df_f.Brand == fbrd]
        if fmov == "Non-Moving":
            df_f = df_f[df_f.NonMoving]
        elif fmov == "Moving":
            df_f = df_f[~df_f.NonMoving]
        df_f = df_f[df_f.Qty >= min_qty]

        st.caption(f"Showing {len(df_f)} styles")
        st.dataframe(df_f.drop(columns=["PID"]), use_container_width=True)
        st.download_button("Export Inventory", to_excel({"Inventory": df_f.drop(columns=["PID"])}), "inventory.xlsx")
        st.markdown("</div>", unsafe_allow_html=True)

        # Style Detail View
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Style Detail View")
        if not df_inv.empty:
            options = [f"{r.Ref} | {r.Product}" for _, r in df_inv.iterrows()]
            selected_str = st.selectbox("Select Style", options)
            selected_row = df_inv[(df_inv['Ref'] + ' | ' + df_inv['Product']) == selected_str].iloc[0]
            pid = selected_row.PID

            # Last 12 months sales
            today = datetime.today().date()
            today_dt = pd.to_datetime(today)
            sales_12m = df_sales_all[(df_sales_all.PID == pid) & (df_sales_all.Date >= today_dt - timedelta(days=365))]
            sales_qty_12m = sales_12m.Qty.sum()
            sales_amt_12m = sales_12m.Amount.sum()

            # Last 6 months monthly
            sales_6m = sales_12m[sales_12m.Date >= today_dt - timedelta(days=180)]
            if not sales_6m.empty:
                sales_6m['Month'] = sales_6m['Date'].dt.strftime("%Y-%m")
                monthly = sales_6m.groupby('Month').agg(Qty=('Qty', 'sum'), Amount=('Amount', 'sum')).reset_index()
            else:
                monthly = pd.DataFrame(columns=['Month', 'Qty', 'Amount'])

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Current Stock", f"{selected_row.Qty:,}")
            with c2:
                st.metric("Stock Value", f"{selected_row.Value:,.0f}")
            with c3:
                st.metric("Last Sale", selected_row.LastSaleDate.strftime("%d %b %Y") if pd.notna(selected_row.LastSaleDate) else "Never")
            with c4:
                st.metric("12m Sales", f"{sales_qty_12m} pcs / {sales_amt_12m:,.0f}")

            st.markdown(f"**Status**: <span class='status-pill status-{selected_row.Status}'>{selected_row.Status}</span>", unsafe_allow_html=True)
            st.subheader("Last 6 Months Sales")
            st.dataframe(monthly, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Turnover & Non-Moving
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Inventory Turnover")
        turnover = df_sales_all.Amount.sum() / stock_value if stock_value else 0
        st.metric("Turnover Ratio", f"{turnover:.2f}x")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Non-Moving Styles")
        non_moving = df_inv[df_inv['NonMoving']]
        nm_count = len(non_moving)
        st.caption(f"Styles: {nm_count} | Value: {nm_value:,.0f} SAR ({nonmoving_pct}% of catalog)")
        st.caption(f"Non-Moving % (Sold Styles): {nonmoving_pct_sold}%")
        st.caption(f"Never Sold Styles: {never_sold_count}, Value: {never_sold_value:,.0f} SAR")
        st.dataframe(non_moving.drop(columns=["PID"]), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Never Sold High-Value
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Top 20 High-Value Never Sold Styles")
        never_sold_high = df_inv[df_inv['LastSaleDate'].isna()].nlargest(20, 'Value')
        if never_sold_high.empty:
            st.info("No never sold high-value styles.")
        else:
            st.dataframe(never_sold_high.drop(columns=["PID"]), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Validation Checks
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Validation Checks")
        for name, df_val in validation.items():
            st.caption(f"{name}: {len(df_val)} items")
            if not df_val.empty:
                st.dataframe(df_val.drop(columns=["PID"]), use_container_width=True)
                st.download_button(f"Export {name}", to_excel({name: df_val.drop(columns=["PID"])}), f"{name.lower().replace(' ', '_')}.xlsx")
        st.markdown("</div>", unsafe_allow_html=True)

        # Sell-Through
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Sell-Through Rates")
        if not df_st.empty:
            top_st = df_st.nlargest(10, 'SellThrough')
            bottom_st = df_st.nsmallest(10, 'SellThrough')
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Top Styles")
                st.dataframe(top_st[['Product', 'SellThrough']], use_container_width=True)
            with col2:
                st.subheader("Bottom Styles")
                st.dataframe(bottom_st[['Product', 'SellThrough']], use_container_width=True)
        else:
            st.info("Insufficient data for sell-through calculation.")
        st.markdown("</div>", unsafe_allow_html=True)

        # OOS Risk
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("OOS Risk")
        st.metric("Styles at Risk", oos_risk_count)
        st.markdown("</div>", unsafe_allow_html=True)

        # Sales Trend
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Sales Trend Over Time")
        if not df_sales_all.empty:
            time_sal = df_sales_all.groupby(df_sales_all["Date"].dt.date)["Amount"].sum().reset_index(name="Amount").sort_values("Date")
            time_sal['MA7'] = time_sal['Amount'].rolling(7, min_periods=1).mean()
            time_sal['MA30'] = time_sal['Amount'].rolling(30, min_periods=1).mean()
            fig_time = px.line(time_sal, x="Date", y=["Amount", "MA7", "MA30"], title="Daily Sales Trend (SAR) with Moving Averages")
            st.plotly_chart(fig_time, use_container_width=True)
        else:
            st.info("No sales data in selected period.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ==================== SALES PAGE ====================
    elif page == "🛒 Sales":
        st.markdown(f"### 🛒 Outfit Sales Analysis ({date_info})")
        if df_sales_all.empty:
            st.warning("No sales data in the selected period.")
        else:
            colf1, colf2, colf3, colf4 = st.columns(4)
            with colf1:
                channel = st.selectbox("Channel", ["Both", "SO", "POS"])
            with colf2:
                cat_f = st.selectbox("Category", ["All"] + sorted(df_sales_all.Category.dropna().unique().tolist()))
            with colf3:
                brd_f = st.selectbox("Brand", ["All"] + sorted(df_sales_all.Brand.dropna().unique().tolist()))

            df_s = df_sales_all.copy()
            if channel != "Both":
                df_s = df_s[df_s.Source == channel]
            if cat_f != "All":
                df_s = df_s[df_s.Category == cat_f]
            if brd_f != "All":
                df_s = df_s[df_s.Brand == brd_f]

            total_sales = df_s.Amount.sum()
            total_qty = df_s.Qty.sum()
            avg_bill = df_s.groupby("OrderID")["Amount"].sum().mean() if not df_s.empty else 0
            so_sales = df_s[df_s.Source == 'SO']['Amount'].sum()
            pos_sales = df_s[df_s.Source == 'POS']['Amount'].sum()
            channel_ratio = pos_sales / so_sales if so_sales > 0 else 0

            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.markdown(f'<div class="kpi-card"><div class="kpi-title">TOTAL SALES</div><div class="kpi-value">{total_sales:,.0f}</div><div class="kpi-sub">SAR</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="kpi-card"><div class="kpi-title">UNITS SOLD</div><div class="kpi-value">{total_qty:,.0f}</div><div class="kpi-sub">pcs</div></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="kpi-card"><div class="kpi-title">AVG BILL VALUE</div><div class="kpi-value">{avg_bill:,.0f}</div><div class="kpi-sub">SAR per order</div></div>', unsafe_allow_html=True)
            with c4:
                st.markdown(f'<div class="kpi-card"><div class="kpi-title">SO SALES</div><div class="kpi-value">{so_sales:,.0f}</div><div class="kpi-sub">SAR</div></div>', unsafe_allow_html=True)
            with c5:
                st.markdown(f'<div class="kpi-card"><div class="kpi-title">POS SALES</div><div class="kpi-value">{pos_sales:,.0f}</div><div class="kpi-sub">SAR</div></div>', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                top_styles = df_s.groupby(['PID','Product'])['Amount'].sum().nlargest(20).reset_index()
                fig = px.bar(top_styles, x="Amount", y="Product", orientation="h", title="Top 20 Styles")
                fig.update_layout(yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                top_brands = df_s.groupby('Brand')['Amount'].sum().nlargest(10).reset_index()
                fig = px.bar(top_brands, x="Amount", y="Brand", title="Top 10 Brands")
                st.plotly_chart(fig, use_container_width=True)

            st.download_button("Export Sales Data", to_excel({"Sales": df_s}), "sales_export.xlsx")

    # ==================== PURCHASE PAGE ====================
    elif page == "🏪 Purchase":
        st.markdown(f"### 🏪 Outfit Purchase Analysis ({date_info})")
        if df_pur.empty:
            st.warning("No purchase data in the selected period.")
        else:
            total_pur = df_pur.Amount.sum()
            total_qty_pur = df_pur.Qty.sum()
            supp_count = df_pur.Supplier.nunique()

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f'<div class="kpi-card"><div class="kpi-title">TOTAL PURCHASES</div><div class="kpi-value">{total_pur:,.0f}</div><div class="kpi-sub">SAR</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="kpi-card"><div class="kpi-title">UNITS PURCHASED</div><div class="kpi-value">{total_qty_pur:,.0f}</div><div class="kpi-sub">pcs</div></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="kpi-card"><div class="kpi-title">SUPPLIERS</div><div class="kpi-value">{supp_count}</div><div class="kpi-sub">Distinct</div></div>', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                time_pur = df_pur.groupby(df_pur["Date"].dt.date)["Amount"].sum().reset_index(name="Amount")
                fig = px.line(time_pur, x="Date", y="Amount", title="Purchases Over Time")
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                top_supp = df_pur.groupby("Supplier")["Amount"].sum().nlargest(10).reset_index()
                fig = px.bar(top_supp, x="Amount", y="Supplier", title="Top 10 Suppliers")
                st.plotly_chart(fig, use_container_width=True)

            st.download_button("Export Purchases", to_excel({"Purchases": df_pur}), "purchases.xlsx")

    # ==================== CATEGORY PAGE ====================
    elif page == "📁 Category":
        st.markdown(f"### 📁 Category Dashboard ({date_info})")
        if df_inv.empty:
            st.info("No inventory data.")
        else:
            cat_stock = df_inv.groupby('Category').agg(
                Stock_Value=('Value', 'sum'),
                Num_Styles=('PID', 'nunique')
            ).reset_index()

            sales_cat = df_sales_all.groupby('Category').agg(
                Sales_Value=('Amount', 'sum'),
                Sales_Qty=('Qty', 'sum')
            ).reset_index()

            cat_df = cat_stock.merge(sales_cat, on='Category', how='left').fillna(0)

            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(cat_df, x='Category', y='Stock_Value', title="Stock Value by Category")
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig = px.pie(cat_df, names='Category', values='Sales_Value', title="Sales Contribution by Category")
                st.plotly_chart(fig, use_container_width=True)

            st.dataframe(cat_df, use_container_width=True)

    # ==================== BRAND PAGE ====================
    elif page == "🏷️ Brand":
        st.markdown(f"### 🏷️ Brand Dashboard ({date_info})")
        if df_inv.empty:
            st.info("No inventory data.")
        else:
            brand_stock = df_inv.groupby('Brand').agg(
                Stock_Value=('Value', 'sum'),
                Num_Styles=('PID', 'nunique')
            ).reset_index()

            today = datetime.today().date()
            today_dt = pd.to_datetime(today)
            sales_90 = df_sales_all[df_sales_all.Date >= today_dt - timedelta(days=90)]
            brand_sales_90 = sales_90.groupby('Brand')['Amount'].sum().reset_index(name='Sales_Last90d')

            brand_df = brand_stock.merge(brand_sales_90, on='Brand', how='left').fillna(0)

            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(brand_df, x='Brand', y='Stock_Value', title="Stock Value by Brand")
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig = px.bar(brand_df, x='Brand', y='Sales_Last90d', title="Sales Last 90 Days by Brand")
                st.plotly_chart(fig, use_container_width=True)

            st.dataframe(brand_df, use_container_width=True)

    # ==================== COMBINED PAGE ====================
    elif page == "📊 Combined":
        st.markdown(f"### 📊 Combined Overview ({date_info})")
        stock_value = df_inv.Value.sum()
        today = datetime.today().date()
        today_dt = pd.to_datetime(today)
        sales_30 = df_sales_all[df_sales_all.Date >= today_dt - timedelta(days=30)]['Amount'].sum()
        turnover = df_sales_all.Amount.sum() / stock_value if stock_value else 0

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total Stock Value", f"{stock_value:,.0f} SAR")
        with c2:
            st.metric("Last 30 Days Sales", f"{sales_30:,.0f} SAR")
        with c3:
            st.metric("Non-Moving %", f"{nonmoving_pct}%")
        with c4:
            st.metric("Overall Turnover", f"{turnover:.2f}x")

        # Sales vs Purchases over time
        if not df_sales_all.empty or not df_pur.empty:
            sales_time = df_sales_all.groupby(df_sales_all["Date"].dt.date)["Amount"].sum().reset_index(name="Sales")
            pur_time = df_pur.groupby(df_pur["Date"].dt.date)["Amount"].sum().reset_index(name="Purchases")
            time_df = pd.merge(sales_time, pur_time, on="Date", how="outer").fillna(0).sort_values("Date")
            fig = px.line(time_df, x="Date", y=["Sales", "Purchases"], title="Sales vs Purchases Over Time")
            st.plotly_chart(fig, use_container_width=True)

        # Top 10 categories contribution
        if not df_sales_all.empty:
            cat_sales = df_sales_all.groupby("Category")["Amount"].sum().nlargest(10).reset_index()
            fig = px.bar(cat_sales, x="Amount", y="Category", title="Top 10 Categories by Sales")
            st.plotly_chart(fig, use_container_width=True)

    # ==================== POWER BI PAGE ====================
    elif page == "💼 Power BI":
        st.markdown("### 💼 Power BI Export Helper")
        st.markdown("""
        **How to use in Power BI**  
        1. Download any file below  
        2. In Power BI → Get Data → Excel → select file  
        3. All sheets are ready for relationships on **PID**  
        """)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button("📦 Inventory", to_excel({"Inventory": df_inv.drop(columns=["PID"], errors="ignore")}), "outfit_inventory.xlsx")
        with col2:
            st.download_button("🛒 Sales", to_excel({"Sales": df_sales_all}), "outfit_sales.xlsx")
        with col3:
            st.download_button("🏪 Purchases", to_excel({"Purchases": df_pur}), "outfit_purchases.xlsx")
        st.download_button("📁 ALL DATA (multi-sheet)", to_excel({
            "Inventory": df_inv.drop(columns=["PID"], errors="ignore"),
            "Sales": df_sales_all,
            "Purchases": df_pur
        }), "outfit_full_export.xlsx")


# ==================== BRANCH SALES PAGE (standalone function) ====================
def branch_sales_page(uid, key, full_history, from_date, to_date):
    date_info = "Full History" if full_history else f"From {from_date} to {to_date}"
    st.markdown(f"### 🏢 Branch Sales Analysis ({date_info})")
    st.caption("Source: sale.order + sale.order.line only (SO channel) — moving products only")

    # ── Load data ──────────────────────────────────────────────────────────────
    with st.spinner("Loading branch sales from Odoo..."):
        try:
            df_raw = load_branch_sales(uid, key, full_history, from_date, to_date)
        except Exception as e:
            st.error(f"Branch sales load failed: {e}")
            return

    if df_raw.empty:
        st.warning("No confirmed sale orders found in the selected period.")
        return

    # ── Enrich with Category & Brand via product.product ──────────────────────
    # We use a lightweight fetch of just the product fields we need.
    @st.cache_data(show_spinner=False, ttl=300)
    def load_product_meta(_uid, _k, _pids):
        if not _pids:
            return pd.DataFrame(columns=["PID", "Category", "Brand"])
        recs = fetch_all(
            _uid, _k, "product.product",
            [["id", "in", list(_pids)], ["active", "=", True]],
            ["id", "categ_id", "brand_id"]
        )
        rows = []
        for p in recs:
            rows.append({
                "PID"     : p["id"],
                "Category": p["categ_id"][1] if p.get("categ_id") else "-",
                "Brand"   : p["brand_id"][1]  if p.get("brand_id")  else "-",
            })
        return pd.DataFrame(rows)

    unique_pids = tuple(sorted(df_raw["PID"].unique().tolist()))
    df_meta = load_product_meta(uid, key, unique_pids)
    df_raw = df_raw.merge(df_meta, on="PID", how="left")
    df_raw["Category"] = df_raw["Category"].fillna("-")
    df_raw["Brand"]    = df_raw["Brand"].fillna("-")

    # ── Keep only MOVING products (Qty > 0 in the period) ─────────────────────
    product_qty = df_raw.groupby("PID")["Qty"].sum()
    moving_pids = product_qty[product_qty > 0].index
    df_raw = df_raw[df_raw["PID"].isin(moving_pids)].copy()

    if df_raw.empty:
        st.warning("No moving products found in the selected period.")
        return

    # ── Sidebar-style filters (rendered inline at top of page) ────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.markdown("#### 🔍 Filters")
    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
    with fcol1:
        branch_opts  = ["All"] + sorted(df_raw["Branch"].dropna().unique().tolist())
        f_branch     = st.selectbox("Branch (Sales Team)", branch_opts, key="bs_branch")
    with fcol2:
        wh_opts      = ["All"] + sorted(df_raw["Warehouse"].dropna().unique().tolist())
        f_warehouse  = st.selectbox("Warehouse", wh_opts, key="bs_wh")
    with fcol3:
        cat_opts     = ["All"] + sorted(df_raw["Category"].dropna().unique().tolist())
        f_cat        = st.selectbox("Category", cat_opts, key="bs_cat")
    with fcol4:
        brd_opts     = ["All"] + sorted(df_raw["Brand"].dropna().unique().tolist())
        f_brand      = st.selectbox("Brand", brd_opts, key="bs_brd")
    st.markdown("</div>", unsafe_allow_html=True)

    # Apply filters
    df = df_raw.copy()
    if f_branch    != "All": df = df[df["Branch"]    == f_branch]
    if f_warehouse != "All": df = df[df["Warehouse"] == f_warehouse]
    if f_cat       != "All": df = df[df["Category"]  == f_cat]
    if f_brand     != "All": df = df[df["Brand"]     == f_brand]

    if df.empty:
        st.warning("No data after applying filters.")
        return

    # ── KPIs ──────────────────────────────────────────────────────────────────
    total_sales_sar  = df["Amount"].sum()
    total_units      = df["Qty"].sum()
    num_branches     = df["Branch"].nunique()
    unique_products  = df["Product"].nunique()

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-title">TOTAL SALES</div>'
            f'<div class="kpi-value">{total_sales_sar:,.0f}</div>'
            f'<div class="kpi-sub">SAR</div></div>',
            unsafe_allow_html=True
        )
    with k2:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-title">UNITS SOLD</div>'
            f'<div class="kpi-value">{total_units:,.0f}</div>'
            f'<div class="kpi-sub">pcs</div></div>',
            unsafe_allow_html=True
        )
    with k3:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-title">BRANCHES</div>'
            f'<div class="kpi-value">{num_branches}</div>'
            f'<div class="kpi-sub">Sales Teams</div></div>',
            unsafe_allow_html=True
        )
    with k4:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-title">UNIQUE PRODUCTS</div>'
            f'<div class="kpi-value">{unique_products:,}</div>'
            f'<div class="kpi-sub">Moving Styles</div></div>',
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Chart 1 – Sales by Branch (bar) ───────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Sales by Branch")
    branch_agg = (
        df.groupby("Branch")
          .agg(Sales_SAR=("Amount", "sum"), Units=("Qty", "sum"))
          .reset_index()
          .sort_values("Sales_SAR", ascending=False)
    )
    col_a, col_b = st.columns(2)
    with col_a:
        fig_branch_sar = px.bar(
            branch_agg, x="Branch", y="Sales_SAR",
            title="Sales (SAR) by Branch",
            color="Sales_SAR",
            color_continuous_scale=[[0, "#1a1a1a"], [0.5, "#b8860b"], [1, "#d4af37"]],
            labels={"Sales_SAR": "Sales (SAR)"}
        )
        fig_branch_sar.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_branch_sar, use_container_width=True)
    with col_b:
        fig_branch_qty = px.bar(
            branch_agg, x="Branch", y="Units",
            title="Units Sold by Branch",
            color="Units",
            color_continuous_scale=[[0, "#1a1a1a"], [0.5, "#b8860b"], [1, "#d4af37"]],
            labels={"Units": "Qty"}
        )
        fig_branch_qty.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_branch_qty, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Chart 2 – Daily Sales Trend by Branch (line) ──────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Daily Sales Trend by Branch")
    daily_branch = (
        df.groupby([df["Date"].dt.date, "Branch"])["Amount"]
          .sum()
          .reset_index(name="Sales_SAR")
    )
    daily_branch.rename(columns={"Date": "Day"}, inplace=True)
    fig_trend = px.line(
        daily_branch, x="Day", y="Sales_SAR", color="Branch",
        title="Daily Sales (SAR) per Branch",
        labels={"Sales_SAR": "Sales (SAR)", "Day": "Date"}
    )
    fig_trend.update_traces(mode="lines+markers", marker=dict(size=4))
    st.plotly_chart(fig_trend, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Chart 3 – Top 20 Products per Branch (drill-down) ────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Top 20 Products per Branch")
    branch_list  = sorted(df["Branch"].unique().tolist())
    selected_br  = st.selectbox(
        "Select Branch to drill down", branch_list, key="bs_drilldown"
    )
    df_branch_sel = df[df["Branch"] == selected_br]
    top20_branch  = (
        df_branch_sel.groupby("Product")
                     .agg(Sales_SAR=("Amount", "sum"), Units=("Qty", "sum"))
                     .reset_index()
                     .nlargest(20, "Sales_SAR")
    )
    metric_choice = st.radio(
        "Metric", ["Sales (SAR)", "Units"], horizontal=True, key="bs_metric"
    )
    y_col   = "Sales_SAR" if metric_choice == "Sales (SAR)" else "Units"
    y_label = "Sales (SAR)" if metric_choice == "Sales (SAR)" else "Qty"
    fig_top20 = px.bar(
        top20_branch, x=y_col, y="Product", orientation="h",
        title=f"Top 20 Products – {selected_br} ({metric_choice})",
        color=y_col,
        color_continuous_scale=[[0, "#1a1a1a"], [0.5, "#b8860b"], [1, "#d4af37"]],
        labels={y_col: y_label}
    )
    fig_top20.update_layout(
        yaxis=dict(autorange="reversed"),
        coloraxis_showscale=False
    )
    st.plotly_chart(fig_top20, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Pivot Table – Product × Branch (Qty) ──────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Branch × Product Pivot Table (Qty Sold)")
    pivot_metric = st.radio(
        "Pivot Value", ["Qty", "Amount (SAR)"], horizontal=True, key="bs_pivot_metric"
    )
    pv_col = "Qty" if pivot_metric == "Qty" else "Amount"
    pivot_df = (
        df.groupby(["Product", "Branch"])[pv_col]
          .sum()
          .reset_index()
          .pivot(index="Product", columns="Branch", values=pv_col)
          .fillna(0)
    )
    # Add row total
    pivot_df["TOTAL"] = pivot_df.sum(axis=1)
    pivot_df = pivot_df.sort_values("TOTAL", ascending=False)
    st.caption(
        f"Rows = products ({len(pivot_df)}) · Columns = branches · "
        f"Values = {pivot_metric}"
    )
    st.dataframe(
        pivot_df.style.background_gradient(cmap="YlOrBr", axis=None),
        use_container_width=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Raw Data Table ─────────────────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Raw Sales Data")
    display_cols = ["Date", "Branch", "Warehouse", "Product", "Category", "Brand", "Qty", "Amount", "OrderID"]
    st.dataframe(
        df[display_cols].sort_values("Date", ascending=False),
        use_container_width=True
    )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Export ─────────────────────────────────────────────────────────────────
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Export")
    pivot_reset = pivot_df.reset_index()  # keep Product as a column in Excel
    export_bytes = to_excel_with_index(
        dfs_no_index={"Raw_Data": df[display_cols].sort_values("Date", ascending=False)},
        dfs_with_index={"Pivot_Branch_Product": pivot_reset}
    )
    st.download_button(
        label="📥 Export Branch Sales (Pivot + Raw Data)",
        data=export_bytes,
        file_name="branch_sales_export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    st.markdown("</div>", unsafe_allow_html=True)


# ── Entry point ───────────────────────────────────────────────────────────────
if st.session_state.get("uid") is None:
    login_page()
else:
    dashboard()
