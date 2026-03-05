import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from io import BytesIO

ODOO_URL = "https://odooprosys-la-rouche.odoo.com"
ODOO_DB = "odooprosys-la-rouche-production-12364313"

st.set_page_config(page_title="Odoo Dashboard", page_icon="📊", layout="wide")

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

@st.cache_data(show_spinner=False, ttl=300)
def load_inv(_uid, _k):
    recs = fetch_all(_uid, _k, "product.product",
                     [["active", "=", True], ["type", "=", "product"]],
                     ["id", "default_code", "name", "categ_id", "product_brand_id",
                      "qty_available", "virtual_available", "standard_price"])
    rows = []
    for p in recs:
        qty = p.get("qty_available") or 0
        cost = p.get("standard_price") or 0
        rows.append({
            "ID": p["id"],
            "Ref": p.get("default_code") or "",
            "Product": p.get("name") or "",
            "Category": p["categ_id"][1] if p.get("categ_id") else "-",
            "Brand": p["product_brand_id"][1] if p.get("product_brand_id") else "-",
            "Qty": qty,
            "Forecast": p.get("virtual_available") or 0,
            "Cost": cost,
            "Value": round(qty * cost, 2),
            "Status": "OUT" if qty <= 0 else ("LOW" if qty <= 5 else "OK")
        })
    return pd.DataFrame(rows)

@st.cache_data(show_spinner=False, ttl=300)
def load_sal(_uid, _k):
    recs = fetch_all(_uid, _k, "sale.order.line",
                     [["order_id.state", "in", ["sale", "done"]]],
                     ["product_id", "product_uom_qty", "price_subtotal"])
    rows = []
    for r in recs:
        rows.append({
            "PID": r["product_id"][0] if r.get("product_id") else 0,
            "Product": r["product_id"][1] if r.get("product_id") else "-",
            "Qty": r.get("product_uom_qty") or 0,
            "Amount": r.get("price_subtotal") or 0
        })
    return pd.DataFrame(rows)

@st.cache_data(show_spinner=False, ttl=300)
def load_pur(_uid, _k):
    recs = fetch_all(_uid, _k, "purchase.order.line",
                     [["order_id.state", "in", ["purchase", "done"]]],
                     ["product_id", "product_qty", "price_subtotal"])
    rows = []
    for r in recs:
        rows.append({
            "PID": r["product_id"][0] if r.get("product_id") else 0,
            "Product": r["product_id"][1] if r.get("product_id") else "-",
            "Qty": r.get("product_qty") or 0,
            "Amount": r.get("price_subtotal") or 0
        })
    return pd.DataFrame(rows)

def to_excel(dfs):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, df in dfs.items():
            df.to_excel(w, sheet_name=name[:31], index=False)
    return buf.getvalue()

CM = {"OK": "#27ae60", "LOW": "#e67e22", "OUT": "#e74c3c"}

# Session State
for k, v in {"uid": None, "api_key": None, "uname": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v


def login_page():
    st.markdown("<div style='text-align:center;padding:40px 0 20px'>"
                "<h1 style='color:#1565c0'>📊 Odoo Report Dashboard</h1>"
                "<p style='color:#888'>La Rouche – Inventory · Sales · Purchase · Category · Brand</p>"
                "</div>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        with st.container(border=True):
            st.markdown("#### 🔗 Connect to Odoo")
            st.text_input("URL", value=ODOO_URL, disabled=True)
            st.text_input("Database", value=ODOO_DB, disabled=True)
            user = st.text_input("Email", placeholder="your@email.com")
            key = st.text_input("API Key", type="password", placeholder="Settings → API Keys → New")
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
        st.caption("API Key banane ka tarika: Odoo → User Icon → Preferences → Account Security → API Keys → New")


def dashboard():
    uid = st.session_state.uid
    key = st.session_state.api_key

    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.uname}")
        st.divider()
        page = st.radio("Navigation", [
            "📦 Inventory",
            "🛒 Sales",
            "🏪 Purchase",
            "📁 Category",
            "🏷️ Brand",
            "📊 Combined"
        ])
        st.divider()
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.uid = None
            st.session_state.api_key = None
            st.rerun()

    with st.spinner("Loading data from Odoo..."):
        try:
            df_inv = load_inv(uid, key)
            df_sal = load_sal(uid, key)
            df_pur = load_pur(uid, key)
        except Exception as e:
            st.error(f"Error: {e}")
            return

    meta = df_inv[["ID", "Category", "Brand"]].drop_duplicates("ID")
    df_sal = df_sal.merge(meta, left_on="PID", right_on="ID", how="left").fillna("-")
    df_pur = df_pur.merge(meta, left_on="PID", right_on="ID", how="left").fillna("-")

    # ===================== INVENTORY =====================
    if page == "📦 Inventory":
        st.title("📦 Inventory Report")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Products", len(df_inv))
        c2.metric("In Stock (OK)", int((df_inv.Status == "OK").sum()))
        c3.metric("Low Stock (≤5)", int((df_inv.Status == "LOW").sum()))
        c4.metric("Out of Stock", int((df_inv.Status == "OUT").sum()))
        c5.metric("Total Value", f"{df_inv.Value.sum():,.0f}")

        col1, col2 = st.columns(2)
        with col1:
            sc = df_inv.Status.value_counts().reset_index()
            sc.columns = ["Status", "Count"]
            fig = px.pie(sc, names="Status", values="Count", color="Status",
                         color_discrete_map=CM, hole=0.4, title="Stock Status Distribution")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            t10 = df_inv.nlargest(10, "Value")
            fig = px.bar(t10, x="Value", y="Product", orientation="h",
                         color="Status", color_discrete_map=CM,
                         title="Top 10 Products by Stock Value")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

        fc1, fc2, fc3, fc4 = st.columns(4)
        srch = fc1.text_input("🔍 Search", "")
        fstat = fc2.selectbox("Status", ["All", "OK", "LOW", "OUT"])
        fcat = fc3.selectbox("Category", ["All"] + sorted(df_inv.Category.unique().tolist()))
        fbrd = fc4.selectbox("Brand", ["All"] + sorted(df_inv.Brand.unique().tolist()))

        df_f = df_inv.copy()
        if srch:
            df_f = df_f[df_f.Product.str.contains(srch, case=False, na=False) |
                        df_f.Ref.str.contains(srch, case=False, na=False)]
        if fstat != "All":
            df_f = df_f[df_f.Status == fstat]
        if fcat != "All":
            df_f = df_f[df_f.Category == fcat]
        if fbrd != "All":
            df_f = df_f[df_f.Brand == fbrd]

        st.caption(f"Showing {len(df_f)} of {len(df_inv)} products")
        st.dataframe(df_f.drop(columns=["ID"]), use_container_width=True, height=420)
        st.download_button("⬇ Download Excel",
                           to_excel({"Inventory": df_f.drop(columns=["ID"])}),
                           "inventory.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ===================== SALES =====================
    elif page == "🛒 Sales":
        st.title("🛒 Sales Report")
        agg = df_sal.groupby(["PID", "Product", "Category", "Brand"]).agg(
            Qty=("Qty", "sum"), Amount=("Amount", "sum")
        ).reset_index().sort_values("Amount", ascending=False)

        c1, c2, c3 = st.columns(3)
        c1.metric("Unique Products Sold", len(agg))
        c2.metric("Total Qty Sold", f"{agg.Qty.sum():,.0f}")
        c3.metric("Total Sales Amount", f"{agg.Amount.sum():,.0f}")

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(agg.head(10), x="Amount", y="Product",
                         orientation="h", title="Top 10 Products by Sales")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            cat_s = agg.groupby("Category")["Amount"].sum().reset_index()\
                       .sort_values("Amount", ascending=False).head(10)
            fig = px.bar(cat_s, x="Amount", y="Category",
                         orientation="h", title="Top 10 Categories by Sales")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

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

        st.dataframe(df_f.drop(columns=["PID"]), use_container_width=True, height=420)
        st.download_button("⬇ Download Excel",
                           to_excel({"Sales": df_f.drop(columns=["PID"])}),
                           "sales.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ===================== PURCHASE =====================
    elif page == "🏪 Purchase":
        st.title("🏪 Purchase Report")
        agg = df_pur.groupby(["PID", "Product", "Category", "Brand"]).agg(
            Qty=("Qty", "sum"), Amount=("Amount", "sum")
        ).reset_index().sort_values("Amount", ascending=False)

        c1, c2, c3 = st.columns(3)
        c1.metric("Unique Products Purchased", len(agg))
        c2.metric("Total Qty Purchased", f"{agg.Qty.sum():,.0f}")
        c3.metric("Total Purchase Amount", f"{agg.Amount.sum():,.0f}")

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(agg.head(10), x="Amount", y="Product",
                         orientation="h", title="Top 10 Products by Purchase")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            cat_s = agg.groupby("Category")["Amount"].sum().reset_index()\
                       .sort_values("Amount", ascending=False).head(10)
            fig = px.bar(cat_s, x="Amount", y="Category",
                         orientation="h", title="Top 10 Categories by Purchase")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

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

        st.dataframe(df_f.drop(columns=["PID"]), use_container_width=True, height=420)
        st.download_button("⬇ Download Excel",
                           to_excel({"Purchase": df_f.drop(columns=["PID"])}),
                           "purchase.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ===================== CATEGORY =====================
    elif page == "📁 Category":
        st.title("📁 Category Analysis")
        cat_agg = df_inv.groupby("Category").agg(
            Num_Products=("ID", "nunique"),
            Total_Qty=("Qty", "sum"),
            Total_Value=("Value", "sum")
        ).reset_index().sort_values("Total_Value", ascending=False)

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Categories", len(cat_agg))
        c2.metric("Total Products", int(cat_agg.Num_Products.sum()))
        c3.metric("Total Stock Value", f"{cat_agg.Total_Value.sum():,.0f}")

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(cat_agg.head(12), x="Total_Value", y="Category", orientation="h",
                         title="Top Categories by Stock Value")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.pie(cat_agg.head(8), names="Category", values="Total_Value",
                         title="Stock Value Share")
            st.plotly_chart(fig, use_container_width=True)

        sal_cat = df_sal.groupby("Category")["Amount"].sum().reset_index().sort_values("Amount", ascending=False)
        fig_sal = px.bar(sal_cat.head(10), x="Amount", y="Category", orientation="h",
                         title="Top Categories by Sales")
        st.plotly_chart(fig_sal, use_container_width=True)

        st.dataframe(cat_agg, use_container_width=True)
        st.download_button("⬇ Download Excel",
                           to_excel({"Categories": cat_agg, "Sales_by_Category": sal_cat}),
                           "category_analysis.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ===================== BRAND =====================
    elif page == "🏷️ Brand":
        st.title("🏷️ Brand Analysis")
        brd_agg = df_inv.groupby("Brand").agg(
            Num_Products=("ID", "nunique"),
            Total_Qty=("Qty", "sum"),
            Total_Value=("Value", "sum")
        ).reset_index().sort_values("Total_Value", ascending=False)

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Brands", len(brd_agg))
        c2.metric("Total Products", int(brd_agg.Num_Products.sum()))
        c3.metric("Total Stock Value", f"{brd_agg.Total_Value.sum():,.0f}")

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(brd_agg.head(12), x="Total_Value", y="Brand", orientation="h",
                         title="Top Brands by Stock Value")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.pie(brd_agg.head(8), names="Brand", values="Total_Value",
                         title="Stock Value Share by Brand")
            st.plotly_chart(fig, use_container_width=True)

        sal_brd = df_sal.groupby("Brand")["Amount"].sum().reset_index().sort_values("Amount", ascending=False)
        fig_sal = px.bar(sal_brd.head(10), x="Amount", y="Brand", orientation="h",
                         title="Top Brands by Sales")
        st.plotly_chart(fig_sal, use_container_width=True)

        st.dataframe(brd_agg, use_container_width=True)
        st.download_button("⬇ Download Excel",
                           to_excel({"Brands": brd_agg, "Sales_by_Brand": sal_brd}),
                           "brand_analysis.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ===================== COMBINED =====================
    elif page == "📊 Combined":
        st.title("📊 Combined Dashboard")
        tab1, tab2, tab3, tab4 = st.tabs(["Key Metrics", "Inventory", "Sales", "Purchase"])

        with tab1:
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Total Products", len(df_inv))
            c2.metric("Stock Value", f"{df_inv.Value.sum():,.0f}")
            c3.metric("Total Sales", f"{df_sal.Amount.sum():,.0f}")
            c4.metric("Total Purchase", f"{df_pur.Amount.sum():,.0f}")
            c5.metric("Net", f"{df_sal.Amount.sum() - df_pur.Amount.sum():,.0f}")

            sc = df_inv.Status.value_counts().reset_index()
            sc.columns = ["Status", "Count"]
            fig = px.pie(sc, names="Status", values="Count", color="Status",
                         color_discrete_map=CM, hole=0.4)
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.subheader("Top 10 Products by Value")
            t10 = df_inv.nlargest(10, "Value")
            fig = px.bar(t10, x="Value", y="Product", orientation="h", color="Status", color_discrete_map=CM)
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

        with tab3:
            st.subheader("Top 10 Sold Products")
            top_sal = df_sal.groupby("Product")["Amount"].sum().nlargest(10).reset_index()
            st.dataframe(top_sal, use_container_width=True)

        with tab4:
            st.subheader("Top 10 Purchased Products")
            top_pur = df_pur.groupby("Product")["Amount"].sum().nlargest(10).reset_index()
            st.dataframe(top_pur, use_container_width=True)

        st.download_button("⬇ Download All Data",
                           to_excel({"Inventory": df_inv, "Sales": df_sal, "Purchase": df_pur}),
                           "full_report.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ===================== MAIN =====================
if st.session_state.uid is None:
    login_page()
else:
    dashboard()
