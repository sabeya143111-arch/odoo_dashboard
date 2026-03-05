import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
ODOO_URL = "https://odooprosys-la-rouche.odoo.com"
ODOO_DB  = "odooprosys-la-rouche-production-12364313"

st.set_page_config(
    page_title="Odoo Dashboard – La Rouche",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────
# ODOO API HELPERS
# ─────────────────────────────────────────
def odoo_rpc(endpoint, method, *args):
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {"service": endpoint, "method": method, "args": list(args)}
    }
    try:
        r = requests.post(f"{ODOO_URL}/jsonrpc", json=payload, timeout=60)
        res = r.json()
        if "error" in res:
            msg = res["error"].get("data", {}).get("message", str(res["error"]))
            raise Exception(msg)
        return res["result"]
    except requests.exceptions.RequestException as e:
        raise Exception(f"Connection error: {e}")


def odoo_login(username, api_key):
    uid = odoo_rpc("common", "authenticate", ODOO_DB, username, api_key, {})
    if not uid:
        raise Exception("Login failed – check email / API key")
    return uid


def search_read(uid, api_key, model, domain, fields, limit=5000, offset=0, order="id asc"):
    return odoo_rpc(
        "object", "execute_kw",
        ODOO_DB, uid, api_key,
        model, "search_read",
        [domain],
        {"fields": fields, "limit": limit, "offset": offset, "order": order}
    )


def fetch_all(uid, api_key, model, domain, fields, batch=500):
    all_recs = []
    offset = 0
    progress_text = st.empty()
    while True:
        recs = search_read(uid, api_key, model, domain, fields, limit=batch, offset=offset)
        if not recs:
            break
        all_recs.extend(recs)
        progress_text.caption(f"⏳ {model}: {len(all_recs)} records loaded...")
        if len(recs) < batch:
            break
        offset += batch
    progress_text.empty()
    return all_recs


# ─────────────────────────────────────────
# DATA LOADERS (cached per session)
# ─────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=300)
def load_products(_uid, _api_key):
    recs = fetch_all(
        _uid, _api_key,
        "product.product",
        [["active", "=", True], ["type", "=", "product"]],
        ["id", "default_code", "name", "categ_id",
         "product_brand_id", "qty_available",
         "virtual_available", "standard_price"]
    )
    rows = []
    for p in recs:
        qty  = p.get("qty_available") or 0
        vqty = p.get("virtual_available") or 0
        cost = p.get("standard_price") or 0
        val  = qty * cost
        cat  = p["categ_id"][1] if p.get("categ_id") else "-"
        brand = p["product_brand_id"][1] if p.get("product_brand_id") else "-"
        status = "OUT" if qty <= 0 else ("LOW" if qty <= 5 else "OK")
        rows.append({
            "ID": p["id"],
            "Internal Ref": p.get("default_code") or "",
            "Product Name": p.get("name") or "",
            "Category": cat,
            "Brand": brand,
            "Qty On Hand": qty,
            "Forecasted Qty": vqty,
            "Cost": cost,
            "Stock Value": round(val, 2),
            "Status": status
        })
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False, ttl=300)
def load_sales(_uid, _api_key):
    recs = fetch_all(
        _uid, _api_key,
        "sale.order.line",
        [["order_id.state", "in", ["sale", "done"]]],
        ["product_id", "product_uom_qty", "price_unit", "price_subtotal",
         "order_id", "categ_id"]
    )
    rows = []
    for r in recs:
        rows.append({
            "Product ID": r["product_id"][0] if r.get("product_id") else 0,
            "Product Name": r["product_id"][1] if r.get("product_id") else "-",
            "Order": r["order_id"][1] if r.get("order_id") else "-",
            "Qty Sold": r.get("product_uom_qty") or 0,
            "Unit Price": r.get("price_unit") or 0,
            "Subtotal": r.get("price_subtotal") or 0,
        })
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False, ttl=300)
def load_purchase(_uid, _api_key):
    recs = fetch_all(
        _uid, _api_key,
        "purchase.order.line",
        [["order_id.state", "in", ["purchase", "done"]]],
        ["product_id", "product_qty", "price_unit", "price_subtotal", "order_id"]
    )
    rows = []
    for r in recs:
        rows.append({
            "Product ID": r["product_id"][0] if r.get("product_id") else 0,
            "Product Name": r["product_id"][1] if r.get("product_id") else "-",
            "Order": r["order_id"][1] if r.get("order_id") else "-",
            "Qty Purchased": r.get("product_qty") or 0,
            "Unit Price": r.get("price_unit") or 0,
            "Subtotal": r.get("price_subtotal") or 0,
        })
    return pd.DataFrame(rows)


def to_excel(dfs: dict) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for sheet, df in dfs.items():
            df.to_excel(w, sheet_name=sheet, index=False)
    return buf.getvalue()


# ─────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────
if "uid" not in st.session_state:
    st.session_state.uid     = None
    st.session_state.api_key = None
    st.session_state.username= None


# ─────────────────────────────────────────
# LOGIN PAGE
# ─────────────────────────────────────────
def login_page():
    st.markdown("""
    <div style='text-align:center;padding:40px 0 10px'>
        <h1 style='color:#1565c0'>📊 Odoo Report Dashboard</h1>
        <p style='color:#888'>La Rouche – Product · Category · Brand · Sales · Purchase · Inventory</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.container(border=True):
            st.markdown("#### 🔗 Connect to Odoo")
            st.text_input("Odoo URL", value=ODOO_URL, disabled=True)
            st.text_input("Database", value=ODOO_DB, disabled=True)
            username = st.text_input("Email / Username", placeholder="your@email.com")
            api_key  = st.text_input("API Key", type="password",
                                      placeholder="Settings → API Keys → New",
                                      help="Odoo → Top Right → Preferences → Account Security → API Keys")
            if st.button("🔗 Connect & Load Data", type="primary", use_container_width=True):
                if not username or not api_key:
                    st.error("Email aur API Key dono zaroori hain")
                else:
                    with st.spinner("Connecting to Odoo..."):
                        try:
                            uid = odoo_login(username, api_key)
                            st.session_state.uid      = uid
                            st.session_state.api_key  = api_key
                            st.session_state.username = username
                            st.success("✅ Connected!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ {e}")

        st.caption("💡 Tip: API Key banane ke liye: Odoo → User Icon → Preferences → Account Security → API Keys → New")


# ─────────────────────────────────────────
# MAIN DASHBOARD
# ─────────────────────────────────────────
def dashboard():
    uid     = st.session_state.uid
    api_key = st.session_state.api_key

    # SIDEBAR
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.caption(f"DB: `{ODOO_DB}`")
        st.divider()
        page = st.radio("📋 Navigation", [
            "📦 Inventory",
            "🛒 Sales",
            "🏪 Purchase",
            "📁 Category Analysis",
            "🏷️ Brand Analysis",
            "📊 Combined Report"
        ])
        st.divider()
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
        if st.button("🚪 Logout"):
            for k in ["uid","api_key","username"]:
                st.session_state[k] = None
            st.rerun()

    # LOAD DATA
    with st.spinner("Loading data from Odoo..."):
        try:
            df_inv  = load_products(uid, api_key)
            df_sal  = load_sales(uid, api_key)
            df_pur  = load_purchase(uid, api_key)
        except Exception as e:
            st.error(f"❌ Data load error: {e}")
            return

    # Merge category/brand into sales & purchase
    meta = df_inv[["ID","Category","Brand"]].drop_duplicates("ID")
    df_sal = df_sal.merge(meta, left_on="Product ID", right_on="ID", how="left").fillna("-")
    df_pur = df_pur.merge(meta, left_on="Product ID", right_on="ID", how="left").fillna("-")

    # ── INVENTORY ──────────────────────────────────────────────
    if page == "📦 Inventory":
        st.title("📦 Inventory Report")
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Total Products",  len(df_inv))
        c2.metric("In Stock (OK)",   len(df_inv[df_inv.Status=="OK"]))
        c3.metric("Low Stock (≤5)",  len(df_inv[df_inv.Status=="LOW"]))
        c4.metric("Out of Stock",    len(df_inv[df_inv.Status=="OUT"]))
        c5.metric("Stock Value",     f"{df_inv['Stock Value'].sum():,.0f}")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Stock Status Distribution")
            sc = df_inv.Status.value_counts().reset_index()
            sc.columns = ["Status","Count"]
            color_map = {"OK":"#27ae60","LOW":"#e67e22","OUT":"#e74c3c"}
            fig = px.pie(sc, names="Status", values="Count",
                        color="Status", color_discrete_map=color_map, hole=0.4)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Top 10 by Stock Value")
            top10 = df_inv.nlargest(10,"Stock Value")
            fig = px.bar(top10, x="Stock Value", y="Product Name",
                        orientation="h", color="Status",
                        color_discrete_map=color_map)
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("🔍 Filter & Search")
        fc1,fc2,fc3,fc4 = st.columns(4)
        srch   = fc1.text_input("Search Product", placeholder="Type name or ref...")
        f_stat = fc2.selectbox("Status", ["All","OK","LOW","OUT"])
        cats   = ["All"] + sorted(df_inv.Category.unique().tolist())
        brands = ["All"] + sorted(df_inv.Brand.unique().tolist())
        f_cat  = fc3.selectbox("Category", cats)
        f_brd  = fc4.selectbox("Brand", brands)

        df_f = df_inv.copy()
        if srch:
            df_f = df_f[df_f["Product Name"].str.contains(srch, case=False, na=False) |
                        df_f["Internal Ref"].str.contains(srch, case=False, na=False)]
        if f_stat != "All":
            df_f = df_f[df_f.Status == f_stat]
        if f_cat != "All":
            df_f = df_f[df_f.Category == f_cat]
        if f_brd != "All":
            df_f = df_f[df_f.Brand == f_brd]

        st.caption(f"Showing {len(df_f)} of {len(df_inv)} products")
        st.dataframe(df_f.drop(columns=["ID"]), use_container_width=True, height=400)

        xl = to_excel({"Inventory
