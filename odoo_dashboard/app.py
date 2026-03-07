import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.io as pio
from io import BytesIO
from datetime import datetime, timedelta
# ================== GLOBAL CONFIG ==================
ODOO_URL = "https://odooprosys-la-rouche.odoo.com"
ODOO_DB = "odooprosys-la-rouche-production-12364313"
LOW_THRESHOLD = 5  # Configurable low stock threshold
ENABLE_WAREHOUSE = False  # Toggle for warehouse features (if available)
# Plotly global theme – transparent bg, nice spacing
pio.templates.default = "plotly_white"
pio.templates["plotly_white"].layout.update(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=-0.25),
    bargap=0.22,
    transition_duration=1000,  # Enable Plotly animations
)
st.set_page_config(
    page_title="Premium Odoo Dashboard",
    page_icon="📊",
    layout="wide"
)
# =============== LUXURY CUSTOM CSS WITH ANIMATIONS ===============
st.markdown("""
<style>
/* Luxury full page background - black and gold theme */
.stApp {
    background: radial-gradient(circle at top left, #1a1a1a 0%, #0d0d0d 45%, #000000 100%);
    color: #f0e6d2;
    font-family: "Playfair Display", serif; /* Elegant font */
}
/* Remove default padding */
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 1.5rem;
}
/* Headings with gold accent */
h1, h2, h3, h4 {
    color: #d4af37; /* Gold */
    text-shadow: 0 0 5px rgba(212,175,55,0.5);
}
/* Luxury glass containers with animation */
.glass-card {
    background: rgba(10,10,10,0.85);
    border-radius: 20px;
    padding: 20px 22px;
    border: 1px solid rgba(212,175,55,0.3); /* Gold border */
    box-shadow: 0 20px 50px rgba(0,0,0,0.7);
    backdrop-filter: blur(16px);
    animation: fadeInUp 1s ease-out;
}
/* KPI cards with luxury gradient and animations */
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
/* Status pill with glow */
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
/* Sidebar luxury style */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d0d0d 0%, #000000 60%, #1a1a1a 100%);
    border-right: 1px solid rgba(212,175,55,0.4);
}
section[data-testid="stSidebar"] .block-container {
    padding-top: 1.6rem;
}
/* Sidebar elements with animation */
[data-testid="stSidebar"] .stRadio > label, [data-testid="stSidebar"] .stButton button {
    transition: transform 0.3s;
}
[data-testid="stSidebar"] .stRadio > label:hover, [data-testid="stSidebar"] .stButton button:hover {
    transform: scale(1.05);
}
/* Dataframe luxury tweaks */
[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid rgba(212,175,55,0.4);
}
/* Download buttons luxury */
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
/* Tabs luxury styling */
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
/* Small caption */
.small-caption {
    font-size: 0.8rem;
    color: #a9a9a9;
}
/* Login box luxury */
.login-box {
    max-width: 400px;
    margin: 0 auto;
    animation: fadeIn 1s ease-in;
}
/* Keyframes for animations */
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
# ================== ODOO HELPERS ==================
def odoo_rpc(endpoint, method, *args):
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
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

def search_read(uid, k, model, domain, fields, limit=500, offset=0):
    return odoo_rpc(
        "object",
        "execute_kw",
        ODOO_DB,
        uid,
        k,
        model,
        "search_read",
        [domain],
        {"fields": fields, "limit": limit, "offset": offset, "order": "id asc"},
    )

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
# ================== DATA LOADERS ==================
@st.cache_data(show_spinner=False, ttl=300)
def load_inv(_uid, _k):
    fields = [
        "id",
        "default_code",
        "name",
        "categ_id",
        "brand_id",
        "qty_available",
        "virtual_available",
        "standard_price",
    ]
    if ENABLE_WAREHOUSE:
        fields.append("warehouse_id")
    recs = fetch_all(
        _uid,
        _k,
        "product.product",
        [["active", "=", True], ["type", "=", "product"]],
        fields,
    )
    rows = []
    for p in recs:
        qty = p.get("qty_available") or 0
        cost = p.get("standard_price") or 0
        row = {
            "ID": p["id"],
            "Ref": p.get("default_code") or "",
            "Product": p.get("name") or "",
            "Category": p["categ_id"][1] if p.get("categ_id") else "-",
            "Brand": p["brand_id"][1] if p.get("brand_id") else "-",
            "Qty": qty,
            "Forecast": p.get("virtual_available") or 0,
            "Cost": cost,
            "Value": round(qty * cost, 2),
            "Status": "OUT" if qty <= 0 else ("LOW" if qty <= LOW_THRESHOLD else "OK"),
        }
        if ENABLE_WAREHOUSE:
            row["Warehouse"] = p["warehouse_id"][1] if p.get("warehouse_id") else "-"
        rows.append(row)
    return pd.DataFrame(rows)

@st.cache_data(show_spinner=False, ttl=300)
def load_sal(_uid, _k, _full_history, _from_date, _to_date):
    order_domain = [["state", "=", "sale"]]  # Only confirmed sales
    if not _full_history:
        order_domain.append(["date_order", ">=", str(_from_date)])
        order_domain.append(["date_order", "<", str(_to_date + timedelta(days=1))])
    orders = fetch_all(
        _uid,
        _k,
        "sale.order",
        order_domain,
        ["id", "date_order"],
    )
    order_ids = [o["id"] for o in orders]
    order_date_map = {o["id"]: o["date_order"] for o in orders}
    line_domain = [["order_id", "in", order_ids]]
    recs = fetch_all(
        _uid,
        _k,
        "sale.order.line",
        line_domain,
        ["product_id", "product_uom_qty", "price_subtotal", "order_id"],
    )
    rows = []
    for r in recs:
        order_id = r["order_id"][0] if r.get("order_id") else None
        date = order_date_map.get(order_id, None)
        rows.append(
            {
                "PID": r["product_id"][0] if r.get("product_id") else 0,
                "Product": r["product_id"][1] if r.get("product_id") else "-",
                "Qty": r.get("product_uom_qty") or 0,
                "Amount": r.get("price_subtotal") or 0,
                "Date": date,
            }
        )
    df = pd.DataFrame(rows)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    return df

@st.cache_data(show_spinner=False, ttl=300)
def load_pur(_uid, _k, _full_history, _from_date, _to_date):
    order_domain = [["state", "=", "purchase"]]  # Only confirmed purchases
    if not _full_history:
        order_domain.append(["date_order", ">=", str(_from_date)])
        order_domain.append(["date_order", "<", str(_to_date + timedelta(days=1))])
    orders = fetch_all(
        _uid,
        _k,
        "purchase.order",
        order_domain,
        ["id", "date_order"],
    )
    order_ids = [o["id"] for o in orders]
    order_date_map = {o["id"]: o["date_order"] for o in orders}
    line_domain = [["order_id", "in", order_ids]]
    recs = fetch_all(
        _uid,
        _k,
        "purchase.order.line",
        line_domain,
        ["product_id", "product_qty", "price_subtotal", "order_id"],
    )
    rows = []
    for r in recs:
        order_id = r["order_id"][0] if r.get("order_id") else None
        date = order_date_map.get(order_id, None)
        rows.append(
            {
                "PID": r["product_id"][0] if r.get("product_id") else 0,
                "Product": r["product_id"][1] if r.get("product_id") else "-",
                "Qty": r.get("product_qty") or 0,
                "Amount": r.get("price_subtotal") or 0,
                "Date": date,
            }
        )
    df = pd.DataFrame(rows)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    return df

def to_excel(dfs):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, df in dfs.items():
            df.to_excel(w, sheet_name=name[:31], index=False)
    return buf.getvalue()

CM = {"OK": "#90ee90", "LOW": "#ffd700", "OUT": "#ff6347"}  # Updated colors for luxury

# ================== SESSION INIT ==================
for k, v in {"uid": None, "api_key": None, "uname": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ================== LOGIN PAGE ==================
def login_page():
    st.markdown(
        """
        <div style='text-align:center;padding:14px 0 6px'>
            <h1 style='margin-bottom:0.3rem;'>📊 Premium Odoo Dashboard</h1>
            <p style='margin-bottom:0;'>La Rouche – Luxury Analytics Experience</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container():
        col_spacer, col_main, col_spacer2 = st.columns([1, 1.1, 1])
        with col_main:
            st.markdown("<div class='glass-card login-box'>", unsafe_allow_html=True)
            st.markdown("#### 🔗 Secure Odoo Connection")
            st.text_input("URL", value=ODOO_URL, disabled=True)
            st.text_input("Database", value=ODOO_DB, disabled=True)
            user = st.text_input("Email", placeholder="your@email.com")
            key = st.text_input(
                "API Key",
                type="password",
                placeholder="Settings → API Keys → New",
            )
            if st.button("🔗 Connect & Load", type="primary", use_container_width=True):
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
                            st.error(f"❌ {e}")
            st.markdown("</div>", unsafe_allow_html=True)
        st.caption(
            "Create API Key: Odoo → User Icon → Preferences → Account Security → API Keys → New"
        )

# ================== DASHBOARD ==================
def dashboard():
    uid = st.session_state.uid
    key = st.session_state.api_key
    # ---------- Sidebar ----------
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.uname}")
        st.markdown(
            "<p class='small-caption'>Luxury Connection to La Rouche Odoo</p>",
            unsafe_allow_html=True,
        )
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
            ],
        )
        st.divider()
        default_from = datetime.today().date() - timedelta(days=90)
        default_to = datetime.today().date()
        from_date = st.date_input("From Date", value=default_from)
        to_date = st.date_input("To Date", value=default_to)
        full_history = st.toggle("Full History (slow)", value=False)
        if full_history:
            st.warning("Full history may take time for large data.")
        global_search = st.text_input("🔍 Global Search")
        rows_per = st.selectbox("Rows per Table", [50, 100, 200, 500, "All"])
        st.divider()
        col_r, col_l = st.columns(2)
        with col_r:
            if st.button("🔄 Refresh", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        with col_l:
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.uid = None
                st.session_state.api_key = None
                st.rerun()
    # ---------- Load data ----------
    with st.spinner("Loading luxury data from Odoo..."):
        try:
            df_inv = load_inv(uid, key)
            df_sal = load_sal(uid, key, full_history, from_date, to_date)
            df_pur = load_pur(uid, key, full_history, from_date, to_date)
        except Exception as e:
            st.error(f"Error: {e}")
            return
    # Enrich sales & purchase with meta
    meta = df_inv[["ID", "Category", "Brand"]].drop_duplicates("ID")
    df_sal = df_sal.merge(meta, left_on="PID", right_on="ID", how="left").fillna("-").drop(columns=["ID"])
    df_pur = df_pur.merge(meta, left_on="PID", right_on="ID", how="left").fillna("-").drop(columns=["ID"])
    # Apply global search
    if global_search:
        df_inv = df_inv[
            df_inv.Product.str.contains(global_search, case=False, na=False) |
            df_inv.Ref.str.contains(global_search, case=False, na=False)
        ]
        df_sal = df_sal[df_sal.Product.str.contains(global_search, case=False, na=False)]
        df_pur = df_pur[df_pur.Product.str.contains(global_search, case=False, na=False)]
    # Feature 1: Inventory Analytics (already + enhanced)
    if page == "📦 Inventory":
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("### 📦 Luxury Inventory Report")
        total_ok = int((df_inv.Status == "OK").sum())
        total_low = int((df_inv.Status == "LOW").sum())
        total_out = int((df_inv.Status == "OUT").sum())
        total_products = len(df_inv)
        stock_value = df_inv.Value.sum()
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">TOTAL PRODUCTS</div>
                  <div class="kpi-value">{total_products:,}</div>
                  <div class="kpi-sub">Active SKUs</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">IN STOCK (OK)</div>
                  <div class="kpi-value">{total_ok:,}</div>
                  <div class="kpi-sub">Healthy stock</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">LOW STOCK (≤{LOW_THRESHOLD})</div>
                  <div class="kpi-value">{total_low:,}</div>
                  <div class="kpi-sub">Need attention</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">OUT OF STOCK</div>
                  <div class="kpi-value">{total_out:,}</div>
                  <div class="kpi-sub">Lost sales risk</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c5:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">TOTAL VALUE</div>
                  <div class="kpi-value">{stock_value:,.0f}</div>
                  <div class="kpi-sub">Inventory on hand</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            sc = df_inv.Status.value_counts().reset_index()
            sc.columns = ["Status", "Count"]
            fig = px.pie(
                sc,
                names="Status",
                values="Count",
                color="Status",
                color_discrete_map=CM,
                hole=0.45,
                title="Stock Status Distribution",
            )
            fig.update_layout(
                title_x=0.5,
                margin=dict(t=50, l=10, r=10, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            t10 = df_inv.nlargest(10, "Value")
            fig = px.bar(
                t10,
                x="Value",
                y="Product",
                orientation="h",
                color="Status",
                color_discrete_map=CM,
                title="Top 10 Products by Stock Value",
            )
            fig.update_layout(
                yaxis=dict(autorange="reversed"),
                margin=dict(t=50, l=10, r=10, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)
        if ENABLE_WAREHOUSE:
            wh_val = df_inv.groupby("Warehouse")["Value"].sum().reset_index().sort_values("Value", ascending=False)
            fig_wh = px.bar(
                wh_val,
                x="Value",
                y="Warehouse",
                orientation="h",
                title="Warehouse Wise Stock Value",
            )
            fig_wh.update_layout(
                yaxis=dict(autorange="reversed"),
                margin=dict(t=50, l=10, r=10, b=10),
            )
            st.plotly_chart(fig_wh, use_container_width=True)
        # Feature 2: Low-stock alert panel
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Low Stock Alert Panel")
        low_df = df_inv[df_inv.Status.isin(["LOW", "OUT"])].sort_values("Qty").head(50)
        st.dataframe(low_df.drop(columns=["ID"]), use_container_width=True)
        st.download_button(
            "⬇ Export Low Stock",
            to_excel({"Low_Stock": low_df.drop(columns=["ID"])}),
            "low_stock.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.markdown("</div>", unsafe_allow_html=True)
        # Feature 3: ABC Analysis
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("ABC Inventory Analysis")
        df_abc = df_inv.sort_values("Value", ascending=False)
        df_abc['CumValue'] = df_abc['Value'].cumsum()
        total_val = df_abc['Value'].sum()
        df_abc['CumPct'] = df_abc['CumValue'] / total_val
        df_abc['ABC'] = 'C'
        df_abc.loc[df_abc['CumPct'] <= 0.8, 'ABC'] = 'A'
        df_abc.loc[(df_abc['CumPct'] > 0.8) & (df_abc['CumPct'] <= 0.95), 'ABC'] = 'B'
        abc_counts = df_abc['ABC'].value_counts().reset_index()
        abc_counts.columns = ["ABC", "count"]
        fig_abc = px.pie(abc_counts, names="ABC", values="count", title="ABC Classification")
        st.plotly_chart(fig_abc, use_container_width=True)
        st.dataframe(df_abc[['Product', 'Value', 'ABC']], use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        # Feature 4: Inventory filters and table
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        fc1, fc2, fc3, fc4 = st.columns(4)
        srch = fc1.text_input("🔍 Search", "")
        fstat = fc2.selectbox("Status", ["All", "OK", "LOW", "OUT"])
        fcat = fc3.selectbox("Category", ["All"] + sorted(df_inv.Category.unique().tolist()))
        fbrd = fc4.selectbox("Brand", ["All"] + sorted(df_inv.Brand.unique().tolist()))
        df_f = df_inv.copy()
        if srch:
            df_f = df_f[
                df_f.Product.str.contains(srch, case=False, na=False)
                | df_f.Ref.str.contains(srch, case=False, na=False)
            ]
        if fstat != "All":
            df_f = df_f[df_f.Status == fstat]
        if fcat != "All":
            df_f = df_f[df_f.Category == fcat]
        if fbrd != "All":
            df_f = df_f[df_f.Brand == fbrd]
        if rows_per != "All":
            df_f = df_f.head(rows_per)
        st.caption(f"Showing {len(df_f)} of {len(df_inv)} products")
        st.dataframe(df_f.drop(columns=["ID"]), use_container_width=True)
        st.download_button(
            "⬇ Download Excel",
            to_excel({"Inventory": df_f.drop(columns=["ID"])}),
            "inventory.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.markdown("</div>", unsafe_allow_html=True)
    # Feature 5: Sales Analytics (enhanced with time series)
    elif page == "🛒 Sales":
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("### 🛒 Luxury Sales Report")
        agg = (
            df_sal.groupby(["PID", "Product", "Category", "Brand"])
            .agg(Qty=("Qty", "sum"), Amount=("Amount", "sum"))
            .reset_index()
            .sort_values("Amount", ascending=False)
        )
        total_sales = agg.Amount.sum()
        total_qty = agg.Qty.sum()
        top_product = agg.iloc[0]["Product"] if len(agg) else "-"
        unique_products = len(agg)
        avg_sales = total_sales / unique_products if unique_products else 0
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">UNIQUE SOLD</div>
                  <div class="kpi-value">{unique_products:,}</div>
                  <div class="kpi-sub">SKUs</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">TOTAL QTY</div>
                  <div class="kpi-value">{total_qty:,.0f}</div>
                  <div class="kpi-sub">Units</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">TOTAL AMOUNT</div>
                  <div class="kpi-value">{total_sales:,.0f}</div>
                  <div class="kpi-sub">Revenue</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">TOP PRODUCT</div>
                  <div class="kpi-value" style="font-size:1rem;">{top_product}</div>
                  <div class="kpi-sub">Highest</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c5:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">AVG SALES</div>
                  <div class="kpi-value">{avg_sales:,.0f}</div>
                  <div class="kpi-sub">Per Product</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(
                agg.head(10),
                x="Amount",
                y="Product",
                orientation="h",
                title="Top 10 Products by Sales",
            )
            fig.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=50, l=10, r=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            cat_s = agg.groupby("Category")["Amount"].sum().reset_index().sort_values("Amount", ascending=False).head(10)
            fig = px.bar(
                cat_s,
                x="Amount",
                y="Category",
                orientation="h",
                title="Top 10 Categories by Sales",
            )
            fig.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=50, l=10, r=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        # Feature 6: Sales Time Series
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Sales Trend Over Time")
        time_sal = df_sal.groupby("Date")["Amount"].sum().reset_index().sort_values("Date")
        fig_time = px.line(time_sal, x="Date", y="Amount", title="Daily Sales Trend")
        st.plotly_chart(fig_time, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        # Feature 7: Sales filters and table
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        fc1, fc2, fc3 = st.columns(3)
        srch = fc1.text_input("🔍 Search", "", key="s_srch")
        fcat = fc2.selectbox("Category", ["All"] + sorted(agg.Category.unique().tolist()), key="s_cat")
        fbrd = fc3.selectbox("Brand", ["All"] + sorted(agg.Brand.unique().tolist()), key="s_brd")
        df_f = agg.copy()
        if srch:
            df_f = df_f[df_f.Product.str.contains(srch, case=False, na=False)]
        if fcat != "All":
            df_f = df_f[df_f.Category == fcat]
        if fbrd != "All":
            df_f = df_f[df_f.Brand == fbrd]
        if rows_per != "All":
            df_f = df_f.head(rows_per)
        st.dataframe(df_f.drop(columns=["PID"]), use_container_width=True)
        st.download_button(
            "⬇ Download Excel",
            to_excel({"Sales": df_f.drop(columns=["PID"])}),
            "sales.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.markdown("</div>", unsafe_allow_html=True)
    # Feature 8: Purchase Analytics (enhanced)
    elif page == "🏪 Purchase":
        # Similar enhancements as sales, with time series, extra KPI, etc.
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("### 🏪 Luxury Purchase Report")
        agg = (
            df_pur.groupby(["PID", "Product", "Category", "Brand"])
            .agg(Qty=("Qty", "sum"), Amount=("Amount", "sum"))
            .reset_index()
            .sort_values("Amount", ascending=False)
        )
        total_purchase = agg.Amount.sum()
        total_qty = agg.Qty.sum()
        unique_products = len(agg)
        top_product = agg.iloc[0]["Product"] if len(agg) else "-"
        avg_purchase = total_purchase / unique_products if unique_products else 0
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">UNIQUE PURCHASED</div>
                  <div class="kpi-value">{unique_products:,}</div>
                  <div class="kpi-sub">SKUs</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">TOTAL QTY</div>
                  <div class="kpi-value">{total_qty:,.0f}</div>
                  <div class="kpi-sub">Units</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">TOTAL AMOUNT</div>
                  <div class="kpi-value">{total_purchase:,.0f}</div>
                  <div class="kpi-sub">Spend</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">TOP PRODUCT</div>
                  <div class="kpi-value" style="font-size:1rem;">{top_product}</div>
                  <div class="kpi-sub">Highest</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c5:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">AVG PURCHASE</div>
                  <div class="kpi-value">{avg_purchase:,.0f}</div>
                  <div class="kpi-sub">Per Product</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(
                agg.head(10),
                x="Amount",
                y="Product",
                orientation="h",
                title="Top 10 Products by Purchase",
            )
            fig.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=50, l=10, r=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            cat_s = agg.groupby("Category")["Amount"].sum().reset_index().sort_values("Amount", ascending=False).head(10)
            fig = px.bar(
                cat_s,
                x="Amount",
                y="Category",
                orientation="h",
                title="Top 10 Categories by Purchase",
            )
            fig.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=50, l=10, r=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        # Feature 9: Purchase Time Series
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Purchase Trend Over Time")
        time_pur = df_pur.groupby("Date")["Amount"].sum().reset_index().sort_values("Date")
        fig_time = px.line(time_pur, x="Date", y="Amount", title="Daily Purchase Trend")
        st.plotly_chart(fig_time, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        # Feature 10: Purchase filters and table
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        fc1, fc2, fc3 = st.columns(3)
        srch = fc1.text_input("🔍 Search", "", key="p_srch")
        fcat = fc2.selectbox("Category", ["All"] + sorted(agg.Category.unique().tolist()), key="p_cat")
        fbrd = fc3.selectbox("Brand", ["All"] + sorted(agg.Brand.unique().tolist()), key="p_brd")
        df_f = agg.copy()
        if srch:
            df_f = df_f[df_f.Product.str.contains(srch, case=False, na=False)]
        if fcat != "All":
            df_f = df_f[df_f.Category == fcat]
        if fbrd != "All":
            df_f = df_f[df_f.Brand == fbrd]
        if rows_per != "All":
            df_f = df_f.head(rows_per)
        st.dataframe(df_f.drop(columns=["PID"]), use_container_width=True)
        st.download_button(
            "⬇ Download Excel",
            to_excel({"Purchase": df_f.drop(columns=["PID"])}),
            "purchase.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.markdown("</div>", unsafe_allow_html=True)
    # Feature 11: Category Analysis (enhanced)
    elif page == "📁 Category":
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("### 📁 Luxury Category Analysis")
        cat_agg = (
            df_inv.groupby("Category")
            .agg(
                Num_Products=("ID", "nunique"),
                Total_Qty=("Qty", "sum"),
                Total_Value=("Value", "sum"),
            )
            .reset_index()
            .sort_values("Total_Value", ascending=False)
        )
        sal_cat = df_sal.groupby("Category")["Amount"].sum().reset_index().sort_values("Amount", ascending=False)
        total_categories = len(cat_agg)
        total_products = int(cat_agg.Num_Products.sum())
        total_stock_value = cat_agg.Total_Value.sum()
        avg_value_per_cat = total_stock_value / total_categories if total_categories else 0
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">TOTAL CATEGORIES</div>
                  <div class="kpi-value">{total_categories:,}</div>
                  <div class="kpi-sub">Groups</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">TOTAL PRODUCTS</div>
                  <div class="kpi-value">{total_products:,}</div>
                  <div class="kpi-sub">Across</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">TOTAL VALUE</div>
                  <div class="kpi-value">{total_stock_value:,.0f}</div>
                  <div class="kpi-sub">Stock</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">AVG VALUE</div>
                  <div class="kpi-value">{avg_value_per_cat:,.0f}</div>
                  <div class="kpi-sub">Per Category</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(
                cat_agg.head(12),
                x="Total_Value",
                y="Category",
                orientation="h",
                title="Stock Value by Category",
            )
            fig.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=50, l=10, r=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.pie(
                cat_agg.head(8),
                names="Category",
                values="Total_Value",
                title="Category Share",
            )
            fig.update_layout(title_x=0.5, margin=dict(t=50, l=10, r=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        fig_sales = px.bar(
            sal_cat.head(10),
            x="Amount",
            y="Category",
            orientation="h",
            title="Top Categories by Sales",
        )
        fig_sales.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=50, l=10, r=10, b=10))
        st.plotly_chart(fig_sales, use_container_width=True)
        # Feature 12: Category x Brand Heatmap
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Category × Brand Sales Heatmap")
        pivot = df_sal.pivot_table(index="Category", columns="Brand", values="Amount", aggfunc="sum", fill_value=0)
        fig_heat = px.imshow(pivot, title="Sales Heatmap", aspect="auto")
        st.plotly_chart(fig_heat, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        # Feature 13: Category table
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        if rows_per != "All":
            cat_agg = cat_agg.head(rows_per)
        st.dataframe(cat_agg, use_container_width=True)
        st.download_button(
            "⬇ Download Excel",
            to_excel({"Categories": cat_agg, "Sales_by_Category": sal_cat}),
            "category_analysis.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.markdown("</div>", unsafe_allow_html=True)
    # Feature 14: Brand Analysis (enhanced)
    elif page == "🏷️ Brand":
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("### 🏷️ Luxury Brand Analysis")
        brd_agg = (
            df_inv.groupby("Brand")
            .agg(
                Num_Products=("ID", "nunique"),
                Total_Qty=("Qty", "sum"),
                Total_Value=("Value", "sum"),
            )
            .reset_index()
            .sort_values("Total_Value", ascending=False)
        )
        sal_brd = df_sal.groupby("Brand")["Amount"].sum().reset_index().sort_values("Amount", ascending=False)
        total_brands = len(brd_agg)
        total_products = int(brd_agg.Num_Products.sum())
        total_stock_value = brd_agg.Total_Value.sum()
        avg_value_per_brd = total_stock_value / total_brands if total_brands else 0
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">TOTAL BRANDS</div>
                  <div class="kpi-value">{total_brands:,}</div>
                  <div class="kpi-sub">Portfolio</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">TOTAL PRODUCTS</div>
                  <div class="kpi-value">{total_products:,}</div>
                  <div class="kpi-sub">Across</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">TOTAL VALUE</div>
                  <div class="kpi-value">{total_stock_value:,.0f}</div>
                  <div class="kpi-sub">Stock</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">AVG VALUE</div>
                  <div class="kpi-value">{avg_value_per_brd:,.0f}</div>
                  <div class="kpi-sub">Per Brand</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(
                brd_agg.head(12),
                x="Total_Value",
                y="Brand",
                orientation="h",
                title="Stock Value by Brand",
            )
            fig.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=50, l=10, r=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.pie(
                brd_agg.head(8),
                names="Brand",
                values="Total_Value",
                title="Brand Share",
            )
            fig.update_layout(title_x=0.5, margin=dict(t=50, l=10, r=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        fig_sales = px.bar(
            sal_brd.head(10),
            x="Amount",
            y="Brand",
            orientation="h",
            title="Top Brands by Sales",
        )
        fig_sales.update_layout(yaxis=dict(autorange="reversed"), margin=dict(t=50, l=10, r=10, b=10))
        st.plotly_chart(fig_sales, use_container_width=True)
        # Feature 15: Brand Performance Score
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.subheader("Brand Performance Score (Sales / Stock Value)")
        brd_sal = df_sal.groupby("Brand")["Amount"].sum().reset_index().rename(columns={"Amount": "Sales"})
        brd_val = df_inv.groupby("Brand")["Value"].sum().reset_index().rename(columns={"Value": "Stock_Value"})
        perf = brd_val.merge(brd_sal, on="Brand", how="left").fillna(0)
        perf["Score"] = perf.apply(lambda r: r.Sales / r.Stock_Value if r.Stock_Value > 0 else 0, axis=1)
        perf = perf.sort_values("Score", ascending=False)
        if rows_per != "All":
            perf = perf.head(rows_per)
        st.dataframe(perf, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        # Feature 16: Brand table
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        if rows_per != "All":
            brd_agg = brd_agg.head(rows_per)
        st.dataframe(brd_agg, use_container_width=True)
        st.download_button(
            "⬇ Download Excel",
            to_excel({"Brands": brd_agg, "Sales_by_Brand": sal_brd, "Performance": perf}),
            "brand_analysis.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.markdown("</div>", unsafe_allow_html=True)
    # Feature 17: Combined Dashboard (enhanced)
    elif page == "📊 Combined":
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("### 📊 Luxury Combined Dashboard")
        total_products = len(df_inv)
        stock_value = df_inv.Value.sum()
        total_sales = df_sal.Amount.sum()
        total_purchase = df_pur.Amount.sum()
        net = total_sales - total_purchase
        inventory_turnover = total_sales / stock_value if stock_value else 0
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">PRODUCTS</div>
                  <div class="kpi-value">{total_products:,}</div>
                  <div class="kpi-sub">Total</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">STOCK VALUE</div>
                  <div class="kpi-value">{stock_value:,.0f}</div>
                  <div class="kpi-sub">On Hand</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">SALES</div>
                  <div class="kpi-value">{total_sales:,.0f}</div>
                  <div class="kpi-sub">Revenue</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">PURCHASE</div>
                  <div class="kpi-value">{total_purchase:,.0f}</div>
                  <div class="kpi-sub">Spend</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c5:
            net_color = "#90ee90" if net >= 0 else "#ff6347"
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">NET</div>
                  <div class="kpi-value" style="color:{net_color};">{net:,.0f}</div>
                  <div class="kpi-sub">Profit</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c6:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">TURNOVER</div>
                  <div class="kpi-value">{inventory_turnover:.2f}</div>
                  <div class="kpi-sub">Ratio</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        # Feature 18: Inventory Health Donut
        sc = df_inv.Status.value_counts().reset_index()
        sc.columns = ["Status", "Count"]
        fig = px.pie(
            sc,
            names="Status",
            values="Count",
            color="Status",
            color_discrete_map=CM,
            hole=0.45,
            title="Inventory Health",
        )
        fig.update_layout(title_x=0.5, margin=dict(t=50, l=10, r=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
        # Feature 19: Top Lists
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.subheader("Top 10 by Value")
            t10_val = df_inv.nlargest(10, "Value")[["Product", "Value", "Status"]]
            st.dataframe(t10_val, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with col2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.subheader("Top 10 Sold")
            top_sold = df_sal.groupby("Product")["Amount"].sum().nlargest(10).reset_index()
            st.dataframe(top_sold, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with col3:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.subheader("Top 10 Purchased")
            top_pur = df_pur.groupby("Product")["Amount"].sum().nlargest(10).reset_index()
            st.dataframe(top_pur, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        # Feature 20: Quick Exports
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        col_exp1, col_exp2, col_exp3, col_exp4 = st.columns(4)
        with col_exp1:
            st.download_button(
                "⬇ Inventory",
                to_excel({"Inventory": df_inv.drop(columns=["ID"])}),
                "inventory.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with col_exp2:
            st.download_button(
                "⬇ Sales",
                to_excel({"Sales": df_sal.drop(columns=["PID"])}),
                "sales.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with col_exp3:
            st.download_button(
                "⬇ Purchase",
                to_excel({"Purchase": df_pur.drop(columns=["PID"])}),
                "purchase.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with col_exp4:
            st.download_button(
                "⬇ Full Report",
                to_excel({"Inventory": df_inv, "Sales": df_sal, "Purchase": df_pur}),
                "full_report.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        st.markdown("</div>", unsafe_allow_html=True)

# ===================== MAIN =====================
if st.session_state.uid is None:
    login_page()
else:
    dashboard()
