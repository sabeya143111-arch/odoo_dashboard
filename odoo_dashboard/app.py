import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.io as pio
from io import BytesIO

# ================== GLOBAL CONFIG ==================
ODOO_URL = "https://odooprosys-la-rouche.odoo.com"
ODOO_DB = "odooprosys-la-rouche-production-12364313"

# Plotly global theme – transparent bg, nice spacing
pio.templates.default = "plotly_white"
pio.templates["plotly_white"].layout.update(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=-0.25),
    bargap=0.22,
)

st.set_page_config(
    page_title="Odoo Dashboard",
    page_icon="📊",
    layout="wide"
)

# =============== CUSTOM CSS ===============
st.markdown("""
<style>
/* Full page background */
.stApp {
    background: radial-gradient(circle at top left, #1f2933 0, #020617 45%, #020617 100%);
    color: #e5e7eb;
    font-family: "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

/* Remove default padding a bit */
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 1.5rem;
}

/* Headings */
h1, h2, h3, h4 {
    color: #f9fafb;
}

/* Nice glass containers */
.glass-card {
    background: rgba(15,23,42,0.78);
    border-radius: 18px;
    padding: 18px 20px;
    border: 1px solid rgba(148,163,184,0.25);
    box-shadow: 0 18px 45px rgba(15,23,42,0.65);
    backdrop-filter: blur(14px);
}

/* KPI cards */
.kpi-card {
    background: linear-gradient(135deg, rgba(56,189,248,0.1), rgba(129,140,248,0.08));
    border-radius: 16px;
    padding: 14px 18px;
    border: 1px solid rgba(94,234,212,0.55);
    box-shadow: 0 12px 30px rgba(15,23,42,0.55);
    backdrop-filter: blur(12px);
    transition: all 0.2s ease-out;
}
.kpi-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 18px 40px rgba(15,23,42,0.75);
}
.kpi-title {
    font-size: 0.78rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #9ca3af;
}
.kpi-value {
    font-size: 1.35rem;
    font-weight: 700;
    color: #e5e7eb;
}
.kpi-sub {
    font-size: 0.78rem;
    color: #9ca3af;
}

/* Status pill */
.status-pill {
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 0.7rem;
    font-weight: 600;
}
.status-OK {
    background: rgba(34,197,94,0.12);
    color: #4ade80;
    border: 1px solid rgba(34,197,94,0.5);
}
.status-LOW {
    background: rgba(234,179,8,0.12);
    color: #fbbf24;
    border: 1px solid rgba(234,179,8,0.5);
}
.status-OUT {
    background: rgba(248,113,113,0.12);
    color: #fca5a5;
    border: 1px solid rgba(248,113,113,0.5);
}

/* Sidebar style */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #020617 0%, #020617 60%, #0f172a 100%);
    border-right: 1px solid rgba(148,163,184,0.4);
}
section[data-testid="stSidebar"] .block-container {
    padding-top: 1.4rem;
}

/* Sidebar radio buttons */
[data-testid="stSidebar"] .stRadio > label {
    font-weight: 600;
    color: #e5e7eb;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label {
    background: rgba(15,23,42,0.6);
    border-radius: 999px;
    padding: 4px 10px;
}

/* Dataframe tweaks */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid rgba(148,163,184,0.4);
}

/* Download buttons */
.stDownloadButton button {
    border-radius: 999px;
    background: linear-gradient(135deg, #4f46e5, #06b6d4) !important;
    color: white !important;
    border: none;
    font-weight: 600;
}
.stDownloadButton button:hover {
    filter: brightness(1.06);
}

/* Refresh / Logout buttons */
.stButton button {
    border-radius: 999px;
}

/* Tabs styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.5rem;
}
.stTabs [data-baseweb="tab"] {
    background-color: rgba(15,23,42,0.8);
    border-radius: 999px;
    padding-top: 6px;
    padding-bottom: 6px;
    border: 1px solid rgba(148,163,184,0.4);
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #4f46e5, #06b6d4);
    color: white;
    border-color: transparent;
}

/* Small caption */
.small-caption {
    font-size: 0.76rem;
    color: #9ca3af;
}

/* Login box center on page */
.login-box {
    max-width: 380px;
    margin: 0 auto;
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
    recs = fetch_all(
        _uid,
        _k,
        "product.product",
        [["active", "=", True], ["type", "=", "product"]],
        [
            "id",
            "default_code",
            "name",
            "categ_id",
            "brand_id",
            "qty_available",
            "virtual_available",
            "standard_price",
        ],
    )
    rows = []
    for p in recs:
        qty = p.get("qty_available") or 0
        cost = p.get("standard_price") or 0
        rows.append(
            {
                "ID": p["id"],
                "Ref": p.get("default_code") or "",
                "Product": p.get("name") or "",
                "Category": p["categ_id"][1] if p.get("categ_id") else "-",
                "Brand": p["brand_id"][1] if p.get("brand_id") else "-",
                "Qty": qty,
                "Forecast": p.get("virtual_available") or 0,
                "Cost": cost,
                "Value": round(qty * cost, 2),
                "Status": "OUT" if qty <= 0 else ("LOW" if qty <= 5 else "OK"),
            }
        )
    return pd.DataFrame(rows)

@st.cache_data(show_spinner=False, ttl=300)
def load_sal(_uid, _k):
    recs = fetch_all(
        _uid,
        _k,
        "sale.order.line",
        [["order_id.state", "in", ["sale", "done"]]],
        ["product_id", "product_uom_qty", "price_subtotal"],
    )
    rows = []
    for r in recs:
        rows.append(
            {
                "PID": r["product_id"][0] if r.get("product_id") else 0,
                "Product": r["product_id"][1] if r.get("product_id") else "-",
                "Qty": r.get("product_uom_qty") or 0,
                "Amount": r.get("price_subtotal") or 0,
            }
        )
    return pd.DataFrame(rows)

@st.cache_data(show_spinner=False, ttl=300)
def load_pur(_uid, _k):
    recs = fetch_all(
        _uid,
        _k,
        "purchase.order.line",
        [["order_id.state", "in", ["purchase", "done"]]],
        ["product_id", "product_qty", "price_subtotal"],
    )
    rows = []
    for r in recs:
        rows.append(
            {
                "PID": r["product_id"][0] if r.get("product_id") else 0,
                "Product": r["product_id"][1] if r.get("product_id") else "-",
                "Qty": r.get("product_qty") or 0,
                "Amount": r.get("price_subtotal") or 0,
            }
        )
    return pd.DataFrame(rows)

def to_excel(dfs):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, df in dfs.items():
            df.to_excel(w, sheet_name=name[:31], index=False)
    return buf.getvalue()

CM = {"OK": "#22c55e", "LOW": "#eab308", "OUT": "#ef4444"}

# ================== SESSION INIT ==================
for k, v in {"uid": None, "api_key": None, "uname": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ================== LOGIN PAGE ==================
def login_page():
    st.markdown(
        """
        <div style='text-align:center;padding:14px 0 6px'>
            <h1 style='color:#e5e7eb;margin-bottom:0.3rem;'>📊 Odoo Report Dashboard</h1>
            <p style='color:#9ca3af;margin-bottom:0;'>La Rouche – Inventory · Sales · Purchase · Category · Brand</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    with st.container():
        col_spacer, col_main, col_spacer2 = st.columns([1, 1.1, 1])
        with col_main:
            st.markdown("<div class='glass-card login-box'>", unsafe_allow_html=True)
            st.markdown("#### 🔗 Connect to Odoo")
            st.text_input("URL", value=ODOO_URL, disabled=True)
            st.text_input("Database", value=ODOO_DB, disabled=True)
            user = st.text_input("Email", placeholder="your@email.com")
            key = st.text_input(
                "API Key",
                type="password",
                placeholder="Settings → API Keys → New",
            )
            if st.button("🔗 Connect & Load Data", type="primary", use_container_width=True):
                if not user or not key:
                    st.error("Email aur API Key dono zaroori hain")
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
            "API Key banane ka tarika: Odoo → User Icon → Preferences → Account Security → API Keys → New"
        )

# ================== DASHBOARD ==================
def dashboard():
    uid = st.session_state.uid
    key = st.session_state.api_key

    # ---------- Sidebar ----------
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.uname}")
        st.markdown(
            "<p class='small-caption'>Connected to La Rouche Odoo</p>",
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
    with st.spinner("Loading data from Odoo..."):
        try:
            df_inv = load_inv(uid, key)
            df_sal = load_sal(uid, key)
            df_pur = load_pur(uid, key)
        except Exception as e:
            st.error(f"Error: {e}")
            return

    # Enrich sales & purchase with meta
    meta = df_inv[["ID", "Category", "Brand"]].drop_duplicates("ID")
    df_sal = df_sal.merge(meta, left_on="PID", right_on="ID", how="left").fillna("-")
    df_pur = df_pur.merge(meta, left_on="PID", right_on="ID", how="left").fillna("-")

    # ================== INVENTORY ==================
    if page == "📦 Inventory":
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("### 📦 Inventory Report")

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
                  <div class="kpi-title">LOW STOCK (≤5)</div>
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

        st.caption(f"Showing {len(df_f)} of {len(df_inv)} products")
        st.dataframe(df_f.drop(columns=["ID"]), use_container_width=True, height=420)
        st.download_button(
            "⬇ Download Excel",
            to_excel({"Inventory": df_f.drop(columns=["ID"])}),
            "inventory.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ================== SALES ==================
    elif page == "🛒 Sales":
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("### 🛒 Sales Report")

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

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">UNIQUE PRODUCTS SOLD</div>
                  <div class="kpi-value">{unique_products:,}</div>
                  <div class="kpi-sub">Distinct SKUs</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">TOTAL QTY SOLD</div>
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
                  <div class="kpi-title">TOTAL SALES AMOUNT</div>
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
                  <div class="kpi-sub">Highest sales</div>
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
            fig.update_layout(
                yaxis=dict(autorange="reversed"),
                margin=dict(t=50, l=10, r=10, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            cat_s = (
                agg.groupby("Category")["Amount"]
                .sum()
                .reset_index()
                .sort_values("Amount", ascending=False)
                .head(10)
            )
            fig = px.bar(
                cat_s,
                x="Amount",
                y="Category",
                orientation="h",
                title="Top 10 Categories by Sales",
            )
            fig.update_layout(
                yaxis=dict(autorange="reversed"),
                margin=dict(t=50, l=10, r=10, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        fc1, fc2, fc3 = st.columns(3)
        srch = fc1.text_input("🔍 Search", "", key="s_srch")
        fcat = fc2.selectbox(
            "Category",
            ["All"] + sorted(agg.Category.unique().tolist()),
            key="s_cat",
        )
        fbrd = fc3.selectbox(
            "Brand",
            ["All"] + sorted(agg.Brand.unique().tolist()),
            key="s_brd",
        )

        df_f = agg.copy()
        if srch:
            df_f = df_f[df_f.Product.str.contains(srch, case=False, na=False)]
        if fcat != "All":
            df_f = df_f[df_f.Category == fcat]
        if fbrd != "All":
            df_f = df_f[df_f.Brand == fbrd]

        st.dataframe(df_f.drop(columns=["PID"]), use_container_width=True, height=420)
        st.download_button(
            "⬇ Download Excel",
            to_excel({"Sales": df_f.drop(columns=["PID"])}),
            "sales.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ================== PURCHASE ==================
    elif page == "🏪 Purchase":
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("### 🏪 Purchase Report")

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

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">UNIQUE PRODUCTS PURCHASED</div>
                  <div class="kpi-value">{unique_products:,}</div>
                  <div class="kpi-sub">Distinct SKUs</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">TOTAL QTY PURCHASED</div>
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
                  <div class="kpi-title">TOTAL PURCHASE AMOUNT</div>
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
                  <div class="kpi-title">TOP PURCHASED PRODUCT</div>
                  <div class="kpi-value" style="font-size:1rem;">{top_product}</div>
                  <div class="kpi-sub">Highest spend</div>
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
            fig.update_layout(
                yaxis=dict(autorange="reversed"),
                margin=dict(t=50, l=10, r=10, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            cat_s = (
                agg.groupby("Category")["Amount"]
                .sum()
                .reset_index()
                .sort_values("Amount", ascending=False)
                .head(10)
            )
            fig = px.bar(
                cat_s,
                x="Amount",
                y="Category",
                orientation="h",
                title="Top 10 Categories by Purchase",
            )
            fig.update_layout(
                yaxis=dict(autorange="reversed"),
                margin=dict(t=50, l=10, r=10, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        fc1, fc2, fc3 = st.columns(3)
        srch = fc1.text_input("🔍 Search", "", key="p_srch")
        fcat = fc2.selectbox(
            "Category",
            ["All"] + sorted(agg.Category.unique().tolist()),
            key="p_cat",
        )
        fbrd = fc3.selectbox(
            "Brand",
            ["All"] + sorted(agg.Brand.unique().tolist()),
            key="p_brd",
        )

        df_f = agg.copy()
        if srch:
            df_f = df_f[df_f.Product.str.contains(srch, case=False, na=False)]
        if fcat != "All":
            df_f = df_f[df_f.Category == fcat]
        if fbrd != "All":
            df_f = df_f[df_f.Brand == fbrd]

        st.dataframe(df_f.drop(columns=["PID"]), use_container_width=True, height=420)
        st.download_button(
            "⬇ Download Excel",
            to_excel({"Purchase": df_f.drop(columns=["PID"])}),
            "purchase.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ================== CATEGORY ==================
    elif page == "📁 Category":
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("### 📁 Category Analysis")

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
        sal_cat = (
            df_sal.groupby("Category")["Amount"]
            .sum()
            .reset_index()
            .sort_values("Amount", ascending=False)
        )

        total_categories = len(cat_agg)
        total_products = int(cat_agg.Num_Products.sum())
        total_stock_value = cat_agg.Total_Value.sum()

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">TOTAL CATEGORIES</div>
                  <div class="kpi-value">{total_categories:,}</div>
                  <div class="kpi-sub">Inventory groups</div>
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
                  <div class="kpi-sub">Across categories</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">TOTAL STOCK VALUE</div>
                  <div class="kpi-value">{total_stock_value:,.0f}</div>
                  <div class="kpi-sub">All categories</div>
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
                title="Top Categories by Stock Value",
            )
            fig.update_layout(
                yaxis=dict(autorange="reversed"),
                margin=dict(t=50, l=10, r=10, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.pie(
                cat_agg.head(8),
                names="Category",
                values="Total_Value",
                title="Stock Value Share",
            )
            fig.update_layout(title_x=0.5, margin=dict(t=50, l=10, r=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

        st.plotly_chart(
            px.bar(
                sal_cat.head(10),
                x="Amount",
                y="Category",
                orientation="h",
                title="Top Categories by Sales",
            ).update_layout(
                yaxis=dict(autorange="reversed"),
                margin=dict(t=50, l=10, r=10, b=10),
            ),
            use_container_width=True,
        )

        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.dataframe(cat_agg, use_container_width=True)
        st.download_button(
            "⬇ Download Excel",
            to_excel(
                {
                    "Categories": cat_agg,
                    "Sales_by_Category": sal_cat,
                }
            ),
            "category_analysis.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ================== BRAND ==================
    elif page == "🏷️ Brand":
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("### 🏷️ Brand Analysis")

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
        sal_brd = (
            df_sal.groupby("Brand")["Amount"]
            .sum()
            .reset_index()
            .sort_values("Amount", ascending=False)
        )

        total_brands = len(brd_agg)
        total_products = int(brd_agg.Num_Products.sum())
        total_stock_value = brd_agg.Total_Value.sum()

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">TOTAL BRANDS</div>
                  <div class="kpi-value">{total_brands:,}</div>
                  <div class="kpi-sub">Brand portfolio</div>
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
                  <div class="kpi-sub">Across brands</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f"""
                <div class="kpi-card">
                  <div class="kpi-title">TOTAL STOCK VALUE</div>
                  <div class="kpi-value">{total_stock_value:,.0f}</div>
                  <div class="kpi-sub">All brands</div>
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
                title="Top Brands by Stock Value",
            )
            fig.update_layout(
                yaxis=dict(autorange="reversed"),
                margin=dict(t=50, l=10, r=10, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.pie(
                brd_agg.head(8),
                names="Brand",
                values="Total_Value",
                title="Stock Value Share by Brand",
            )
            fig.update_layout(title_x=0.5, margin=dict(t=50, l=10, r=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

        st.plotly_chart(
            px.bar(
                sal_brd.head(10),
                x="Amount",
                y="Brand",
                orientation="h",
                title="Top Brands by Sales",
            ).update_layout(
                yaxis=dict(autorange="reversed"),
                margin=dict(t=50, l=10, r=10, b=10),
            ),
            use_container_width=True,
        )

        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.dataframe(brd_agg, use_container_width=True)
        st.download_button(
            "⬇ Download Excel",
            to_excel(
                {
                    "Brands": brd_agg,
                    "Sales_by_Brand": sal_brd,
                }
            ),
            "brand_analysis.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # ================== COMBINED ==================
    elif page == "📊 Combined":
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("### 📊 Combined Dashboard")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        tab1, tab2, tab3, tab4 = st.tabs(
            ["Key Metrics", "Inventory", "Sales", "Purchase"]
        )

        with tab1:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            total_products = len(df_inv)
            stock_value = df_inv.Value.sum()
            total_sales = df_sal.Amount.sum()
            total_purchase = df_pur.Amount.sum()
            net = total_sales - total_purchase

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
                      <div class="kpi-title">STOCK VALUE</div>
                      <div class="kpi-value">{stock_value:,.0f}</div>
                      <div class="kpi-sub">On hand</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with c3:
                st.markdown(
                    f"""
                    <div class="kpi-card">
                      <div class="kpi-title">TOTAL SALES</div>
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
                      <div class="kpi-title">TOTAL PURCHASE</div>
                      <div class="kpi-value">{total_purchase:,.0f}</div>
                      <div class="kpi-sub">Spend</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with c5:
                net_color = "#22c55e" if net >= 0 else "#ef4444"
                st.markdown(
                    f"""
                    <div class="kpi-card">
                      <div class="kpi-title">NET</div>
                      <div class="kpi-value" style="color:{net_color};">{net:,.0f}</div>
                      <div class="kpi-sub">Sales − Purchase</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

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
            st.markdown("</div>", unsafe_allow_html=True)

        with tab2:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.subheader("Top 10 Products by Value")
            t10 = df_inv.nlargest(10, "Value")
            fig = px.bar(
                t10,
                x="Value",
                y="Product",
                orientation="h",
                color="Status",
                color_discrete_map=CM,
            )
            fig.update_layout(
                yaxis=dict(autorange="reversed"),
                margin=dict(t=50, l=10, r=10, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with tab3:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.subheader("Top 10 Sold Products")
            st.dataframe(
                df_sal.groupby("Product")["Amount"]
                .sum()
                .nlargest(10)
                .reset_index(),
                use_container_width=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        with tab4:
            st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
            st.subheader("Top 10 Purchased Products")
            st.dataframe(
                df_pur.groupby("Product")["Amount"]
                .sum()
                .nlargest(10)
                .reset_index(),
                use_container_width=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.download_button(
            "⬇ Download All Data",
            to_excel(
                {
                    "Inventory": df_inv,
                    "Sales": df_sal,
                    "Purchase": df_pur,
                }
            ),
            "full_report.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.markdown("</div>", unsafe_allow_html=True)

# ===================== MAIN =====================
if st.session_state.uid is None:
    login_page()
else:
    dashboard()
