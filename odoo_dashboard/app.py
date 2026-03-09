import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from io import BytesIO
from datetime import datetime, timedelta
import numpy as np

# Globals
ODOO_URL = "https://odooprosys-la-rouche.odoo.com"
ODOO_DB = "odooprosys-la-rouche-production-12364313"
LOW_THRESHOLD = 5

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

def load_sal(_uid, _k, _full_history, _from_date, _to_date):
    order_domain = [["state", "in", ["sale", "done"]]]
    if not _full_history:
        order_domain += [["date_order", ">=", str(_from_date)], ["date_order", "<", str(_to_date + timedelta(days=1))]]
    orders = fetch_all(_uid, _k, "sale.order", order_domain, ["id", "date_order"])
    order_ids = [o["id"] for o in orders]
    order_date_map = {o["id"]: o["date_order"] for o in orders}
    line_domain = [["order_id", "in", order_ids]]
    recs = fetch_all(_uid, _k, "sale.order.line", line_domain, ["product_id", "product_uom_qty", "price_subtotal", "order_id"])
    rows = []
    for r in recs:
        order_id = r.get("order_id")[0] if r.get("order_id") else None
        date = order_date_map.get(order_id)
        if date:
            rows.append({
                "PID": r["product_id"][0] if r.get("product_id") else 0,
                "Product": r["product_id"][1] if r.get("product_id") else "-",
                "Qty": r.get("product_uom_qty") or 0,
                "Amount": r.get("price_subtotal") or 0,
                "Date": datetime.strptime(date, "%Y-%m-%d %H:%M:%S").date() if isinstance(date, str) else date
            })
    return pd.DataFrame(rows)

def load_pos_sales(_uid, _k, _full_history, _from_date, _to_date):
    order_domain = [["state", "in", ["paid", "invoiced", "done"]]]
    if not _full_history:
        order_domain += [["date_order", ">=", str(_from_date)], ["date_order", "<", str(_to_date + timedelta(days=1))]]
    orders = fetch_all(_uid, _k, "pos.order", order_domain, ["id", "date_order"])
    order_ids = [o["id"] for o in orders]
    order_date_map = {o["id"]: o["date_order"] for o in orders}
    line_domain = [["order_id", "in", order_ids]]
    recs = fetch_all(_uid, _k, "pos.order.line", line_domain, ["product_id", "qty", "price_subtotal", "order_id"])
    rows = []
    for r in recs:
        order_id = r.get("order_id")[0] if r.get("order_id") else None
        date = order_date_map.get(order_id)
        if date:
            rows.append({
                "PID": r["product_id"][0] if r.get("product_id") else 0,
                "Product": r["product_id"][1] if r.get("product_id") else "-",
                "Qty": r.get("qty") or 0,
                "Amount": r.get("price_subtotal") or 0,
                "Date": datetime.strptime(date, "%Y-%m-%d %H:%M:%S").date() if isinstance(date, str) else date
            })
    return pd.DataFrame(rows)

def load_pur(_uid, _k, _full_history, _from_date, _to_date):
    order_domain = [["state", "in", ["purchase", "done"]]]
    if not _full_history:
        order_domain += [["date_order", ">=", str(_from_date)], ["date_order", "<", str(_to_date + timedelta(days=1))]]
    orders = fetch_all(_uid, _k, "purchase.order", order_domain, ["id", "date_order"])
    order_ids = [o["id"] for o in orders]
    order_date_map = {o["id"]: o["date_order"] for o in orders}
    line_domain = [["order_id", "in", order_ids]]
    recs = fetch_all(_uid, _k, "purchase.order.line", line_domain, ["product_id", "product_qty", "price_subtotal", "order_id"])
    rows = []
    for r in recs:
        order_id = r.get("order_id")[0] if r.get("order_id") else None
        date = order_date_map.get(order_id)
        if date:
            rows.append({
                "PID": r["product_id"][0] if r.get("product_id") else 0,
                "Product": r["product_id"][1] if r.get("product_id") else "-",
                "Qty": r.get("product_qty") or 0,
                "Amount": r.get("price_subtotal") or 0,
                "Date": datetime.strptime(date, "%Y-%m-%d %H:%M:%S").date() if isinstance(date, str) else date
            })
    return pd.DataFrame(rows)

def load_clean_inventory(_uid, _k, _full_history, _from_date, _to_date):
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
            "Value": round(qty * cost, 2)
        })
    df_inv_raw = pd.DataFrame(rows)
    total_raw = len(df_inv_raw)
    df_sal = load_sal(_uid, _k, _full_history, _from_date, _to_date)
    df_pos = load_pos_sales(_uid, _k, _full_history, _from_date, _to_date)
    df_sales_all = pd.concat([df_sal, df_pos], ignore_index=True)
    sold_pids = df_sales_all['PID'].unique()
    df_inv = df_inv_raw[df_inv_raw['PID'].isin(sold_pids)]
    if not df_sales_all.empty:
        last_sale = df_sales_all.groupby('PID')['Date'].max().reset_index(name='LastSaleDate')
        df_inv = df_inv.merge(last_sale, on='PID', how='left')
    else:
        df_inv['LastSaleDate'] = pd.NaT
    df_inv['NonMoving'] = False
    mask = df_inv['Qty'] > 0
    today = datetime.today().date()
    df_inv.loc[mask, 'NonMoving'] = df_inv.loc[mask, 'LastSaleDate'].isna() | (df_inv.loc[mask, 'LastSaleDate'] < (today - timedelta(days=NON_MOVING_DAYS)))
    nm_value = df_inv[df_inv['NonMoving']]['Value'].sum()
    total_value = df_inv['Value'].sum()
    nonmoving_pct = round((nm_value / total_value * 100) if total_value else 0, 2)
    return df_inv, df_sales_all, nonmoving_pct, total_raw

def to_excel(dfs):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, df in dfs.items():
            df.to_excel(w, sheet_name=name[:31], index=False)
    return buf.getvalue()

CM = {"OK": "#27ae60","LOW":"#e67e22","OUT":"#e74c3c"}

for k,v in {"uid":None,"api_key":None,"uname":None}.items():
    if k not in st.session_state: st.session_state[k]=v

def login_page():
    st.markdown("<div style='text-align:center;padding:40px 0 20px'>"
                "<h1 style='color:#1565c0'>📊 Odoo Report Dashboard</h1>"
                "<p style='color:#888'>La Rouche – Inventory · Sales · Purchase · Category · Brand</p>"
                "</div>", unsafe_allow_html=True)
    _,col,_ = st.columns([1,1.1,1])
    with col:
        with st.container(border=True):
            st.markdown("#### 🔗 Connect to Odoo")
            st.text_input("URL", value=ODOO_URL, disabled=True)
            st.text_input("Database", value=ODOO_DB, disabled=True)
            user = st.text_input("Email", placeholder="your@email.com")
            key = st.text_input("API Key", type="password",
                                  placeholder="Settings → API Keys → New")
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
        default_from = datetime.today().date() - timedelta(days=90)
        default_to = datetime.today().date()
        from_date = st.date_input("From Date", value=default_from)
        to_date = st.date_input("To Date", value=default_to)
        full_history = st.toggle("Full History", value=False)
        non_moving_days = st.selectbox("Non Moving Days", [30, 60, 90, 180], index=2)
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.uid=None
            st.session_state.api_key=None
            st.rerun()
    with st.spinner("Loading data from Odoo..."):
        try:
            df_inv, df_sal, nonmoving_pct, total_products_raw = load_clean_inventory(uid, key, full_history, from_date, to_date)
            df_pur = load_pur(uid, key, full_history, from_date, to_date)
        except Exception as e:
            st.error(f"Error: {e}")
            return
    meta = df_inv[["PID", "Category", "Brand"]].drop_duplicates("PID")
    df_sal = df_sal.merge(meta, on="PID", how="left").fillna("-")
    df_pur = df_pur.merge(meta, on="PID", how="left").fillna("-")
    if page == "📦 Inventory":
        st.title("📦 Inventory Report")
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Total Products", total_products_raw)
        c2.metric("In Stock (OK)", int((df_inv.Status=="OK").sum()))
        c3.metric("Low Stock (≤5)", int((df_inv.Status=="LOW").sum()))
        c4.metric("Out of Stock", int((df_inv.Status=="OUT").sum()))
        c5.metric("Total Value", f"{df_inv.Value.sum():,.0f}")
        col1,col2 = st.columns(2)
        with col1:
            sc = df_inv.Status.value_counts().reset_index()
            sc.columns = ["Status","Count"]
            fig = px.pie(sc, names="Status", values="Count",
                         color="Status", color_discrete_map=CM,
                         hole=0.4, title="Stock Status Distribution")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            t10 = df_inv.nlargest(10,"Value")
            fig = px.bar(t10, x="Value", y="Product", orientation="h",
                         color="Status", color_discrete_map=CM,
                         title="Top 10 Products by Stock Value")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        fc1,fc2,fc3,fc4 = st.columns(4)
        srch = fc1.text_input("🔍 Search","")
        fstat = fc2.selectbox("Status",["All","OK","LOW","OUT"])
        fcat = fc3.selectbox("Category",["All"]+sorted(df_inv.Category.unique().tolist()))
        fbrd = fc4.selectbox("Brand",["All"]+sorted(df_inv.Brand.unique().tolist()))
        df_f = df_inv.copy()
        if srch:
            df_f = df_f[df_f.Product.str.contains(srch,case=False,na=False)|
                        df_f.Ref.str.contains(srch,case=False,na=False)]
        if fstat!="All": df_f=df_f[df_f.Status==fstat]
        if fcat!="All": df_f=df_f[df_f.Category==fcat]
        if fbrd!="All": df_fbrd=df_f[df_f.Brand==fbrd]
        st.caption(f"Showing {len(df_f)} of {len(df_inv)} products")
        st.dataframe(df_f.drop(columns=["PID"]), use_container_width=True, height=420)
        st.download_button("⬇ Download Excel",
            to_excel({"Inventory":df_f.drop(columns=["PID"])}),
            "inventory.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        # ABC Analysis
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
        st.dataframe(df_abc[["Product", "Value", "ABC"]])
        # Non-Moving
        st.subheader("Non-Moving Products")
        non_moving = df_inv[df_inv['NonMoving']]
        nm_count = len(non_moving)
        nm_value = non_moving['Value'].sum()
        st.metric("Non Moving %", f"{nonmoving_pct}%", "Inventory Value")
        st.caption(f"Products: {nm_count}, Value: {nm_value:,.0f}, {nonmoving_pct}% of inventory")
        st.dataframe(non_moving.drop(columns=["PID"]))
        # Sales Trend
        st.subheader("Sales Trend Over Time")
        if not df_sal.empty:
            time_sal = df_sal.groupby("Date")["Amount"].sum().reset_index().sort_values("Date")
            fig_time = px.line(time_sal, x="Date", y="Amount", title="Daily Sales Trend")
            st.plotly_chart(fig_time, use_container_width=True)
    elif page == "🛒 Sales":
        st.title("🛒 Sales Report")
        agg = df_sal.groupby(["PID","Product","Category","Brand"]).agg(
            Qty=("Qty","sum"), Amount=("Amount","sum")
        ).reset_index().sort_values("Amount", ascending=False)
        c1,c2,c3 = st.columns(3)
        c1.metric("Unique Products Sold", len(agg))
        c2.metric("Total Qty Sold", f"{agg.Qty.sum():,.0f}")
        c3.metric("Total Sales Amount", f"{agg.Amount.sum():,.0f}")
        col1,col2 = st.columns(2)
        with col1:
            fig = px.bar(agg.head(10), x="Amount", y="Product",
                         orientation="h", title="Top 10 Products by Sales")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            cat_s = agg.groupby("Category")["Amount"].sum().reset_index()\
                       .sort_values("Amount",ascending=False).head(10)
            fig = px.bar(cat_s, x="Amount", y="Category",
                         orientation="h", title="Top 10 Categories by Sales")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        fc1,fc2,fc3 = st.columns(3)
        srch = fc1.text_input("🔍 Search","", key="s_srch")
        fcat = fc2.selectbox("Category",["All"]+sorted(agg.Category.unique().tolist()), key="s_cat")
        fbrd = fc3.selectbox("Brand",["All"]+sorted(agg.Brand.unique().tolist()), key="s_brd")
        df_f = agg.copy()
        if srch: df_f=df_f[df_f.Product.str.contains(srch,case=False,na=False)]
        if fcat!="All": df_f=df_f[df_f.Category==fcat]
        if fbrd!="All": df_f=df_f[df_f.Brand==fbrd]
        st.dataframe(df_f.drop(columns=["PID"]), use_container_width=True, height=420)
        st.download_button("⬇ Download Excel",
            to_excel({"Sales":df_f.drop(columns=["PID"])}),
            "sales.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    elif page == "🏪 Purchase":
        st.title("🏪 Purchase Report")
        agg = df_pur.groupby(["PID","Product","Category","Brand"]).agg(
            Qty=("Qty","sum"), Amount=("Amount","sum")
        ).reset_index().sort_values("Amount", ascending=False)
        c1,c2,c3 = st.columns(3)
        c1.metric("Unique Products Purchased", len(agg))
        c2.metric("Total Qty Purchased", f"{agg.Qty.sum():,.0f}")
        c3.metric("Total Purchase Amount", f"{agg.Amount.sum():,.0f}")
        col1,col2 = st.columns(2)
        with col1:
            fig = px.bar(agg.head(10), x="Amount", y="Product",
                         orientation="h", title="Top 10 Products by Purchase")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            cat_s = agg.groupby("Category")["Amount"].sum().reset_index()\
                       .sort_values("Amount",ascending=False).head(10)
            fig = px.bar(cat_s, x="Amount", y="Category",
                         orientation="h", title="Top 10 Categories by Purchase")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        fc1,fc2,fc3 = st.columns(3)
        srch = fc1.text_input("🔍 Search","", key="p_srch")
        fcat = fc2.selectbox("Category",["All"]+sorted(agg.Category.unique().tolist()), key="p_cat")
        fbrd = fc3.selectbox("Brand",["All"]+sorted(agg.Brand.unique().tolist()), key="p_brd")
        df_f = agg.copy()
        if srch: df_f=df_f[df_f.Product.str.contains(srch,case=False,na=False)]
        if fcat!="All": df_f=df_f[df_f.Category==fcat]
        if fbrd!="All": df_f=df_f[df_f.Brand==fbrd]
        st.dataframe(df_f.drop(columns=["PID"]), use_container_width=True, height=420)
        st.download_button("⬇ Download Excel",
            to_excel({"Purchase":df_f.drop(columns=["PID"])}),
            "purchase.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    elif page == "📁 Category":
        st.title("📁 Category Report")
        cat_agg = df_inv.groupby("Category").agg(
            Num_Products=("PID","nunique"), Total_Qty=("Qty","sum"), Total_Value=("Value","sum")
        ).reset_index().sort_values("Total_Value", ascending=False)
        c1,c2,c3 = st.columns(3)
        c1.metric("Total Categories", len(cat_agg))
        c2.metric("Total Products", int(cat_agg.Num_Products.sum()))
        c3.metric("Total Value", f"{cat_agg.Total_Value.sum():,.0f}")
        col1,col2 = st.columns(2)
        with col1:
            fig = px.bar(cat_agg.head(10), x="Total_Value", y="Category", orientation="h",
                         title="Top 10 Categories by Stock Value")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.pie(cat_agg.head(10), names="Category", values="Total_Value",
                         title="Category Stock Value Share")
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(cat_agg, use_container_width=True)
    elif page == "🏷️ Brand":
        st.title("🏷️ Brand Report")
        brand_agg = df_inv.groupby("Brand").agg(
            Num_Products=("PID","nunique"), Total_Qty=("Qty","sum"), Total_Value=("Value","sum")
        ).reset_index().sort_values("Total_Value", ascending=False)
        c1,c2,c3 = st.columns(3)
        c1.metric("Total Brands", len(brand_agg))
        c2.metric("Total Products", int(brand_agg.Num_Products.sum()))
        c3.metric("Total Value", f"{brand_agg.Total_Value.sum():,.0f}")
        col1,col2 = st.columns(2)
        with col1:
            fig = px.bar(brand_agg.head(10), x="Total_Value", y="Brand", orientation="h",
                         title="Top 10 Brands by Stock Value")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.pie(brand_agg.head(10), names="Brand", values="Total_Value",
                         title="Brand Stock Value Share")
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(brand_agg, use_container_width=True)
    elif page == "📊 Combined":
        st.title("📊 Summary Report")
        c1,c2,c3 = st.columns(3)
        c1.metric("Total Products", total_products_raw)
        c2.metric("Total Inventory Value", f"{df_inv.Value.sum():,.0f}")
        c3.metric("Non Moving %", f"{nonmoving_pct}%")
        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(df_inv, names="Category", values="Value", title="Inventory by Category")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.pie(df_inv, names="Brand", values="Value", title="Inventory by Brand")
            st.plotly_chart(fig, use_container_width=True)
    elif page == "💼 Power BI":
        st.title("💼 Power BI Integration")
        url = st.text_input("Enter Power BI Embed URL")
        if url:
            st.components.v1.iframe(url, height=600)

if "uid" not in st.session_state or st.session_state.uid is None:
    login_page()
else:
    dashboard()
