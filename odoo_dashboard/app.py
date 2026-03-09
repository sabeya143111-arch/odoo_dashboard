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

st.set_page_config(page_title="Odoo Dashboard", page_icon="📊", layout="wide")

# Luxury CSS
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
    if not uid: raise Exception("Login failed")
    return uid

def search_read(uid, k, model, domain, fields, limit=500, offset=0):
    return odoo_rpc("object", "execute_kw", ODOO_DB, uid, k, model, "search_read",
                    [domain], {"fields": fields, "limit": limit, "offset": offset, "order": "id asc"})

def fetch_all(uid, k, model, domain, fields, batch=500):
    all_recs, offset = [], 0
    ph = st.empty()
    while True:
        recs = search_read(uid, k, model, domain, fields, limit=batch, offset=offset)
        if not recs: break
        all_recs.extend(recs)
        ph.caption(f"Loading {model}: {len(all_recs)} records...")
        if len(recs) < batch: break
        offset += batch
    ph.empty()
    return all_recs

# Load sales (sale orders)
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
        if date:
            try:
                date_parsed = pd.to_datetime(date).date()
                rows.append({
                    "PID": r["product_id"][0] if r.get("product_id") else 0,
                    "Product": r["product_id"][1] if r.get("product_id") else "-",
                    "Qty": r.get("product_uom_qty") or 0,
                    "Amount": r.get("price_subtotal") or 0,
                    "Date": date_parsed
                })
            except:
                continue  # Skip invalid dates
    return pd.DataFrame(rows)

# Load POS sales
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
        if date:
            try:
                date_parsed = pd.to_datetime(date).date()
                rows.append({
                    "PID": r["product_id"][0] if r.get("product_id") else 0,
                    "Product": r["product_id"][1] if r.get("product_id") else "-",
                    "Qty": r.get("qty") or 0,
                    "Amount": r.get("price_subtotal") or 0,
                    "Date": date_parsed
                })
            except:
                continue  # Skip invalid dates
    return pd.DataFrame(rows)

# Load purchases
@st.cache_data(show_spinner=False, ttl=300)
def load_pur(_uid, _k, _full_history, _from_date, _to_date):
    order_domain = [["state", "in", ["purchase", "done"]]]
    if not _full_history:
        order_domain.append(["date_order", ">=", str(_from_date)])
        order_domain.append(["date_order", "<", str(_to_date + timedelta(days=1))])
    orders = fetch_all(_uid, _k, "purchase.order", order_domain, ["id", "date_order"])
    order_ids = [o["id"] for o in orders]
    order_date_map = {o["id"]: o["date_order"] for o in orders}
    line_domain = [["order_id", "in", order_ids]]
    recs = fetch_all(_uid, _k, "purchase.order.line", line_domain, ["product_id", "product_qty", "price_subtotal", "order_id"])
    rows = []
    for r in recs:
        order_id = r["order_id"][0] if r.get("order_id") else None
        date = order_date_map.get(order_id)
        if date:
            try:
                date_parsed = pd.to_datetime(date).date()
                rows.append({
                    "PID": r["product_id"][0] if r.get("product_id") else 0,
                    "Product": r["product_id"][1] if r.get("product_id") else "-",
                    "Qty": r.get("product_qty") or 0,
                    "Amount": r.get("price_subtotal") or 0,
                    "Date": date_parsed
                })
            except:
                continue  # Skip invalid dates
    return pd.DataFrame(rows)

# Load clean inventory (fixed date parsing)
@st.cache_data(show_spinner=False, ttl=300)
def load_clean_inventory(_uid, _k, _full_history, _from_date, _to_date, _non_moving_days):
    fields = ["id", "default_code", "name", "categ_id", "brand_id", "qty_available", "virtual_available", "standard_price"]
    recs = fetch_all(_uid, _k, "product.product", [["active", "=", True], ["type", "=", "product"]], fields)
    rows = []
    for p in recs:
        qty = p.get("qty_available") or 0
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
    df_inv.loc[mask, 'NonMoving'] = df_inv.loc[mask, 'LastSaleDate'].isna() | (df_inv.loc[mask, 'LastSaleDate'] < (today - timedelta(days=_non_moving_days)))
    nm_value = df_inv[df_inv['NonMoving']]['Value'].sum()
    total_value = df_inv['Value'].sum()
    nonmoving_pct = round((nm_value / total_value * 100) if total_value else 0, 2)
    return df_inv, df_sales_all, nonmoving_pct, total_products_raw, total_value, nm_value

# Excel export
def to_excel(dfs):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, df in dfs.items():
            df.to_excel(w, sheet_name=name[:31], index=False)
    return buf.getvalue()

# Session state
for k, v in {"uid": None, "api_key": None, "uname": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Login page
def login_page():
    st.markdown("<div style='text-align:center;padding:40px 0 20px'>"
                "<h1 style='color:#d4af37'>📊 Odoo Dashboard</h1>"
                "<p style='color:#a9a9a9'>Inventory, Sales, Purchase Reports</p>"
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
                            st.error(f"Error: {e}")
        st.caption("API Key: Odoo → Preferences → Account Security → API Keys → New")

# Dashboard
def dashboard():
    uid = st.session_state.uid
    key = st.session_state.api_key
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.uname}")
        st.divider()
        page = st.radio("Navigation", ["📦 Inventory", "🛒 Sales", "🏪 Purchase", "📁 Category", "🏷️ Brand", "📊 Combined", "💼 Power BI"])
        st.divider()
        default_from = datetime.today().date() - timedelta(days=90)
        default_to = datetime.today().date()
        from_date = st.date_input("From Date", value=default_from)
        to_date = st.date_input("To Date", value=default_to)
        full_history = st.toggle("Full History", value=False)
        non_moving_days = st.selectbox("Non-Moving Days", [30, 60, 90, 180], index=2)
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        if st.button("Logout", use_container_width=True):
            st.session_state.uid = None
            st.session_state.api_key = None
            st.rerun()
    # Load data
    with st.spinner("Loading data..."):
        try:
            df_inv, df_sales_all, nonmoving_pct, total_products_raw, total_value, nm_value = load_clean_inventory(uid, key, full_history, from_date, to_date, non_moving_days)
            df_pur = load_pur(uid, key, full_history, from_date, to_date)
        except Exception as e:
            st.error(f"Error: {e}")
            return
    # Debug summary
    st.write(f"Debug: Total stockable products: {total_products_raw}")
    st.write(f"Debug: Inventory value: {total_value:,.0f}")
    non_moving = df_inv[df_inv['NonMoving']]
    nm_count = len(non_moving)
    st.write(f"Debug: Non-moving count: {nm_count} value: {nm_value:,.0f}")

    if page == "📦 Inventory":
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("### 📦 Inventory Report")
        total_ok = int((df_inv.Status == "OK").sum())
        total_low = int((df_inv.Status == "LOW").sum())
        total_out = int((df_inv.Status == "OUT").sum())
        stock_value = df_inv.Value.sum()
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">TOTAL PRODUCTS</div><div class="kpi-value">{total_products_raw:,}</div><div class="kpi-sub">Stockable</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">IN STOCK (OK)</div><div class="kpi-value">{total_ok:,}</div><div class="kpi-sub">Healthy</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">LOW STOCK</div><div class="kpi-value">{total_low:,}</div><div class="kpi-sub">≤ {LOW_THRESHOLD}</div></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">OUT OF STOCK</div><div class="kpi-value">{total_out:,}</div><div class="kpi-sub">Zero</div></div>', unsafe_allow_html=True)
        with c5:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">TOTAL VALUE</div><div class="kpi-value">{stock_value:,.0f}</div><div class="kpi-sub">Inventory</div></div>', unsafe_allow_html=True)
        with c6:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title">NON MOVING %</div><div class="kpi-value">{nonmoving_pct}%</div><div class="kpi-sub">Inventory Value</div></div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            sc = df_inv.Status.value_counts().reset_index()
            sc.columns = ["Status", "Count"]
            fig = px.pie(sc, names="Status", values="Count", color="Status", color_discrete_map=CM, hole=0.4, title="Stock Status")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            t10 = df_inv.nlargest(10, "Value")
            fig = px.bar(t10, x="Value", y="Product", orientation="h", color="Status", color_discrete_map=CM, title="Top 10 by Value")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Low Stock Alert")
        low_df = df_inv[df_inv.Status.isin(["LOW", "OUT"])].sort_values("Qty").head(50)
        st.dataframe(low_df.drop(columns=["PID"]), use_container_width=True)
        st.download_button("Export Low Stock", to_excel({"Low_Stock": low_df.drop(columns=["PID"])}), "low_stock.xlsx")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("ABC Analysis")
        df_abc = df_inv.sort_values("Value", ascending=False)
        df_abc['CumValue'] = df_abc['Value'].cumsum()
        total_val = df_abc['Value'].sum()
        df_abc['CumPct'] = df_abc['CumValue'] / total_val
        df_abc['ABC'] = 'C'
        df_abc.loc[df_abc['CumPct'] <= 0.8, 'ABC'] = 'A'
        df_abc.loc[(df_abc['CumPct'] > 0.8) & (df_abc['CumPct'] <= 0.95), 'ABC'] = 'B'
        abc_counts = df_abc['ABC'].value_counts().reset_index()
        abc_counts.columns = ["ABC", "Count"]
        fig_abc = px.pie(abc_counts, names="ABC", values="Count", title="ABC Classification")
        st.plotly_chart(fig_abc, use_container_width=True)
        st.dataframe(df_abc[['Product', 'Value', 'ABC']], use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        fc1, fc2, fc3, fc4 = st.columns(4)
        srch = fc1.text_input("Search")
        fstat = fc2.selectbox("Status", ["All", "OK", "LOW", "OUT"])
        fcat = fc3.selectbox("Category", ["All"] + sorted(df_inv.Category.unique().tolist()))
        fbrd = fc4.selectbox("Brand", ["All"] + sorted(df_inv.Brand.unique().tolist()))
        df_f = df_inv.copy()
        if srch:
            df_f = df_f[df_f.Product.str.contains(srch, case=False, na=False) | df_f.Ref.str.contains(srch, case=False, na=False)]
        if fstat != "All":
            df_f = df_f[df_f.Status == fstat]
        if fcat != "All":
            df_f = df_f[df_f.Category == fcat]
        if fbrd != "All":
            df_f = df_f[df_f.Brand == fbrd]
        st.caption(f"Showing {len(df_f)} products")
        st.dataframe(df_f.drop(columns=["PID"]), use_container_width=True)
        st.download_button("Export Inventory", to_excel({"Inventory": df_f.drop(columns=["PID"])}), "inventory.xlsx")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Inventory Turnover")
        turnover = df_sales_all.Amount.sum() / stock_value if stock_value else 0
        st.metric("Turnover Ratio", f"{turnover:.2f}")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Non-Moving Products")
        non_moving = df_inv[df_inv['NonMoving']]
        nm_count = len(non_moving)
        st.caption(f"Products: {nm_count}, Value: {nm_value:,.0f}, {nonmoving_pct}% of inventory")
        st.dataframe(non_moving.drop(columns=["PID"]), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Sales Trend Over Time")
        if not df_sales_all.empty:
            time_sal = df_sales_all.groupby("Date")["Amount"].sum().reset_index().sort_values("Date")
            fig_time = px.line(time_sal, x="Date", y="Amount", title="Daily Sales Trend")
            st.plotly_chart(fig_time, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    # Add similar structures for other pages as in previous code

if st.session_state.get("uid") is None:
    login_page()
else:
    dashboard()
