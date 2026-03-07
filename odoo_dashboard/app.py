import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from io import BytesIO
from datetime import datetime, timedelta

# ==========================
#  Odoo Config
# ==========================
ODOO_URL = "https://odooprosys-la-rouche.odoo.com"
ODOO_DB = "odooprosys-la-rouche-production-12364313"

st.set_page_config(page_title="Odoo Retail Dashboard", page_icon="📊", layout="wide")

# ==========================
#  Odoo RPC Helpers
# ==========================
def odoo_rpc(endpoint, method, *args):
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": endpoint,
            "method": method,
            "args": list(args),
        },
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

def search_read(uid, k, model, domain, fields, limit=500, offset=0, order="id asc"):
    return odoo_rpc(
        "object",
        "execute_kw",
        ODOO_DB,
        uid,
        k,
        model,
        "search_read",
        [domain],
        {"fields": fields, "limit": limit, "offset": offset, "order": order},
    )

def fetch_all(uid, k, model, domain, fields, batch=500, order="id asc"):
    all_recs, offset = [], 0
    ph = st.empty()
    while True:
        recs = search_read(uid, k, model, domain, fields, limit=batch, offset=offset, order=order)
        if not recs:
            break
        all_recs.extend(recs)
        ph.caption(f"Loading {model}: {len(all_recs)} records...")
        if len(recs) < batch:
            break
        offset += batch
    ph.empty()
    return all_recs

# ==========================
#  Utility: Excel Export
# ==========================
def to_excel(dfs):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for name, df in dfs.items():
            df.to_excel(w, sheet_name=name[:31], index=False)
    return buf.getvalue()

CM = {"OK": "#27ae60", "LOW": "#e67e22", "OUT": "#e74c3c"}

# ==========================
#  Session State Init
# ==========================
for k, v in {"uid": None, "api_key": None, "uname": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ==========================
#  Data Loaders
# ==========================
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
            "lst_price",
            "barcode",
            "uom_id",
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
                "SP": p.get("lst_price") or 0,
                "Barcode": p.get("barcode") or "",
                "UoM": p["uom_id"][1] if p.get("uom_id") else "",
                "Status": "OUT" if qty <= 0 else ("LOW" if qty <= 5 else "OK"),
            }
        )
    df = pd.DataFrame(rows)
    return df

@st.cache_data(show_spinner=False, ttl=300)
def load_sal(_uid, _k):
    recs = fetch_all(
        _uid,
        _k,
        "sale.order.line",
        [["order_id.state", "in", ["sale", "done"]]],
        [
            "product_id",
            "product_uom_qty",
            "price_subtotal",
            "order_id",
            "order_id.date_order",
            "order_id.warehouse_id",
        ],
        order="id desc",
    )
    rows = []
    for r in recs:
        rows.append(
            {
                "PID": r["product_id"][0] if r.get("product_id") else 0,
                "Product": r["product_id"][1] if r.get("product_id") else "-",
                "Qty": r.get("product_uom_qty") or 0,
                "Amount": r.get("price_subtotal") or 0,
                "Order": r["order_id"][1] if r.get("order_id") else "",
                "Date": r.get("order_id.date_order"),
                "Warehouse": r["order_id.warehouse_id"][1] if r.get("order_id.warehouse_id") else "-",
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df

@st.cache_data(show_spinner=False, ttl=300)
def load_pur(_uid, _k):
    recs = fetch_all(
        _uid,
        _k,
        "purchase.order.line",
        [["order_id.state", "in", ["purchase", "done"]]],
        [
            "product_id",
            "product_qty",
            "price_subtotal",
            "order_id",
            "order_id.date_approve",
        ],
        order="id desc",
    )
    rows = []
    for r in recs:
        rows.append(
            {
                "PID": r["product_id"][0] if r.get("product_id") else 0,
                "Product": r["product_id"][1] if r.get("product_id") else "-",
                "Qty": r.get("product_qty") or 0,
                "Amount": r.get("price_subtotal") or 0,
                "Order": r["order_id"][1] if r.get("order_id") else "",
                "Date": r.get("order_id.date_approve"),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df

@st.cache_data(show_spinner=False, ttl=300)
def load_pos(_uid, _k):
    recs = fetch_all(
        _uid,
        _k,
        "pos.order.line",
        [["order_id.state", "=", "done"]],
        [
            "product_id",
            "qty",
            "price_subtotal_incl",
            "order_id",
            "order_id.date_order",
            "order_id.config_id",
        ],
        order="id desc",
    )
    rows = []
    for r in recs:
        rows.append(
            {
                "PID": r["product_id"][0] if r.get("product_id") else 0,
                "Product": r["product_id"][1] if r.get("product_id") else "-",
                "Qty": r.get("qty") or 0,
                "Amount": r.get("price_subtotal_incl") or 0,
                "Order": r["order_id"][1] if r.get("order_id") else "",
                "Date": r.get("order_id.date_order"),
                "POS": r["order_id.config_id"][1] if r.get("order_id.config_id") else "-",
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df

# ==========================
#  Login Page
# ==========================
def login_page():
    st.markdown(
        """
    <div style='text-align:center;padding:40px 0 10px'>
        <h1 style='color:#1565c0'>📊 Odoo Retail Dashboard</h1>
        <p style='color:#888'>La Rouche – Inventory · Sales · POS · Purchase · Movement</p>
    </div>
    """,
        unsafe_allow_html=True,
    )
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        with st.container(border=True):
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
        st.caption(
            "API Key banane ka tarika: Odoo → User Icon → Preferences → Account Security → API Keys → New"
        )

# ==========================
#  Main Dashboard
# ==========================
def dashboard():
    uid = st.session_state.uid
    key = st.session_state.api_key

    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.uname}")
        st.divider()
        st.markdown("#### ⚙️ Global Filters")

        # Date range default: last 90 days
        today = datetime.today().date()
        default_from = today - timedelta(days=90)
        date_from, date_to = st.date_input(
            "Date Range (Sales & POS)",
            value=(default_from, today),
        )

        st.divider()
        if st.button("🔄 Refresh All", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.uid = None
            st.session_state.api_key = None
            st.rerun()

    # Load data
    with st.spinner("Loading data from Odoo..."):
        try:
            df_inv = load_inv(uid, key)
            df_sal = load_sal(uid, key)
            df_pur = load_pur(uid, key)
            df_pos = load_pos(uid, key)
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return

    # Product meta
    meta = df_inv[["ID", "Ref", "Product", "Category", "Brand"]].drop_duplicates("ID")

    # Merge meta into sales/purchase/pos
    if not df_sal.empty:
        df_sal = df_sal.merge(meta, left_on="PID", right_on="ID", how="left")
    if not df_pur.empty:
        df_pur = df_pur.merge(meta, left_on="PID", right_on="ID", how="left")
    if not df_pos.empty:
        df_pos = df_pos.merge(meta, left_on="PID", right_on="ID", how="left")

    # Apply date filter to sales & POS & purchase
    def date_filter(df, col_name):
        if df.empty or col_name not in df.columns:
            return df
        mask = (df[col_name].dt.date >= date_from) & (df[col_name].dt.date <= date_to)
        return df[mask]

    df_sal_f = date_filter(df_sal, "Date")
    df_pos_f = date_filter(df_pos, "Date")
    df_pur_f = date_filter(df_pur, "Date")

    # Brand & Category & POS options
    brands = sorted([b for b in df_inv["Brand"].unique().tolist() if b and b != "-"])
    cats = sorted([c for c in df_inv["Category"].unique().tolist() if c and c != "-"])
    pos_list = sorted([p for p in df_pos["POS"].dropna().unique().tolist() if p and p != "-"])

    # Top filter row
    st.markdown("### 📊 Global Filters")
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        f_brands = st.multiselect("Brand", options=brands, default=[])
    with fc2:
        f_cats = st.multiselect("Category", options=cats, default=[])
    with fc3:
        f_pos = st.multiselect("POS Shop", options=pos_list, default=[])

    def apply_bc_filter(df):
        df2 = df.copy()
        if f_brands:
            if "Brand" in df2.columns:
                df2 = df2[df2["Brand"].isin(f_brands)]
        if f_cats:
            if "Category" in df2.columns:
                df2 = df2[df2["Category"].isin(f_cats)]
        return df2

    df_inv_f = apply_bc_filter(df_inv)
    df_sal_f = apply_bc_filter(df_sal_f)
    df_pur_f = apply_bc_filter(df_pur_f)

    if f_pos and not df_pos_f.empty:
        df_pos_f = df_pos_f[df_pos_f["POS"].isin(f_pos)]
    df_pos_f = apply_bc_filter(df_pos_f)

    # Movement Aggregations
    def agg_or_empty(df, group_fields, agg_dict):
        if df.empty:
            return pd.DataFrame(columns=list(group_fields) + list(agg_dict.keys()))
        return df.groupby(group_fields, as_index=False).agg(agg_dict)

    df_sal_agg = agg_or_empty(
        df_sal_f, ["PID"], {"Qty": "sum", "Amount": "sum"}
    )
    df_sal_agg.rename(
        columns={"Qty": "SaleQty", "Amount": "SaleAmount"}, inplace=True
    )

    df_pos_agg = agg_or_empty(
        df_pos_f, ["PID"], {"Qty": "sum", "Amount": "sum"}
    )
    df_pos_agg.rename(
        columns={"Qty": "POSQty", "Amount": "POSAmount"}, inplace=True
    )

    df_pur_agg = agg_or_empty(
        df_pur_f, ["PID"], {"Qty": "sum", "Amount": "sum"}
    )
    df_pur_agg.rename(
        columns={"Qty": "PurQty", "Amount": "PurAmount"}, inplace=True
    )

    df_mov = (
        meta.merge(
            df_inv_f[
                ["ID", "Qty", "Forecast", "Cost", "Value", "Status", "SP", "Barcode", "UoM"]
            ],
            on="ID",
            how="left",
        )
        .merge(df_sal_agg, left_on="ID", right_on="PID", how="left")
        .merge(df_pos_agg, left_on="ID", right_on="PID", how="left")
        .merge(df_pur_agg, left_on="ID", right_on="PID", how="left")
    )

    for col in ["SaleQty", "SaleAmount", "POSQty", "POSAmount", "PurQty", "PurAmount"]:
        if col in df_mov.columns:
            df_mov[col] = df_mov[col].fillna(0)

    df_mov["TotalSoldQty"] = df_mov["SaleQty"] + df_mov["POSQty"]
    df_mov["TotalSales"] = df_mov["SaleAmount"] + df_mov["POSAmount"]

    # Main Tabs
    tabs = st.tabs(
        ["📦 Inventory", "🛒 Sales", "🧾 POS / Shops", "🚚 Movement", "📊 Summary"]
    )

    # ======================
    #  Inventory Tab
    # ======================
    with tabs[0]:
        st.subheader("📦 Inventory Report")

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Total Products", len(df_inv_f))
        c2.metric("In Stock (OK)", int((df_inv_f.Status == "OK").sum()))
        c3.metric("Low Stock (≤5)", int((df_inv_f.Status == "LOW").sum()))
        c4.metric("Out of Stock", int((df_inv_f.Status == "OUT").sum()))
        c5.metric("Total Stock Value", f"{df_inv_f.Value.sum():,.0f}")

        col1, col2 = st.columns(2)
        with col1:
            sc = df_inv_f.Status.value_counts().reset_index()
            sc.columns = ["Status", "Count"]
            if not sc.empty:
                fig = px.pie(
                    sc,
                    names="Status",
                    values="Count",
                    color="Status",
                    color_discrete_map=CM,
                    hole=0.4,
                    title="Stock Status Distribution",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No inventory data to display.")

        with col2:
            if not df_inv_f.empty:
                t10 = df_inv_f.nlargest(10, "Value")
                fig = px.bar(
                    t10,
                    x="Value",
                    y="Product",
                    orientation="h",
                    color="Status",
                    color_discrete_map=CM,
                    title="Top 10 Products by Stock Value",
                )
                fig.update_layout(yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No inventory data to display.")

        fc1, fc2, fc3, fc4 = st.columns(4)
        srch = fc1.text_input("🔍 Search (Ref / Product)", "")
        fstat = fc2.selectbox("Status", ["All", "OK", "LOW", "OUT"])
        fcat = fc3.selectbox(
            "Category (Local)", ["All"] + sorted(df_inv_f.Category.unique().tolist())
        )
        fbrd = fc4.selectbox(
            "Brand (Local)", ["All"] + sorted(df_inv_f.Brand.unique().tolist())
        )

        df_f = df_inv_f.copy()
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

        st.caption(f"Showing {len(df_f)} of {len(df_inv_f)} products")
        st.dataframe(
            df_f.drop(columns=["ID"]),
            use_container_width=True,
            height=420,
        )
        st.download_button(
            "⬇ Download Inventory Excel",
            to_excel({"Inventory": df_f.drop(columns=["ID"])}),
            "inventory.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    # ======================
    #  Sales Tab
    # ======================
    with tabs[1]:
        st.subheader("🛒 Sales (Backend Orders)")

        if df_sal_f.empty:
            st.info("No sales data in selected filters.")
        else:
            total_sales = df_sal_f["Amount"].sum()
            total_qty = df_sal_f["Qty"].sum()
            orders_count = df_sal_f["Order"].nunique()

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Sales Amount", f"{total_sales:,.0f}")
            c2.metric("Total Qty Sold", int(total_qty))
            c3.metric("Orders Count", int(orders_count))

            # Sales over time
            df_sal_daily = df_sal_f.groupby(df_sal_f["Date"].dt.date, as_index=False).agg(
                Amount=("Amount", "sum"),
                Qty=("Qty", "sum"),
            )
            fig = px.line(
                df_sal_daily,
                x="Date",
                y="Amount",
                title="Sales Amount Over Time",
            )
            st.plotly_chart(fig, use_container_width=True)

            # Top products by sales amount
            df_sal_prod = (
                df_sal_f.groupby(["PID", "Product", "Brand", "Category"], as_index=False)
                .agg(Amount=("Amount", "sum"), Qty=("Qty", "sum"))
                .sort_values("Amount", ascending=False)
                .head(20)
            )
            fig2 = px.bar(
                df_sal_prod,
                x="Amount",
                y="Product",
                color="Brand",
                orientation="h",
                title="Top 20 Products by Sales Amount",
            )
            fig2.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig2, use_container_width=True)

            st.dataframe(df_sal_prod, use_container_width=True, height=420)
            st.download_button(
                "⬇ Download Sales Excel",
                to_excel({"Sales": df_sal_prod}),
                "sales.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    # ======================
    #  POS Tab
    # ======================
    with tabs[2]:
        st.subheader("🧾 POS / Shops Sales")

        if df_pos_f.empty:
            st.info("No POS data in selected filters.")
        else:
            total_pos_sales = df_pos_f["Amount"].sum()
            total_pos_qty = df_pos_f["Qty"].sum()
            shops_count = df_pos_f["POS"].nunique()

            c1, c2, c3 = st.columns(3)
            c1.metric("Total POS Sales", f"{total_pos_sales:,.0f}")
            c2.metric("Total POS Qty", int(total_pos_qty))
            c3.metric("Shops (POS)", int(shops_count))

            # POS shop-wise
            df_pos_shop = (
                df_pos_f.groupby("POS", as_index=False)
                .agg(Qty=("Qty", "sum"), Amount=("Amount", "sum"))
                .sort_values("Amount", ascending=False)
            )
            fig = px.pie(
                df_pos_shop,
                names="POS",
                values="Amount",
                title="POS Sales by Shop",
            )
            st.plotly_chart(fig, use_container_width=True)

            # Top products in POS
            df_pos_prod = (
                df_pos_f.groupby(["PID", "Product", "Brand", "Category"], as_index=False)
                .agg(Amount=("Amount", "sum"), Qty=("Qty", "sum"))
                .sort_values("Amount", ascending=False)
                .head(20)
            )
            fig2 = px.bar(
                df_pos_prod,
                x="Amount",
                y="Product",
                color="POS" if "POS" in df_pos_f.columns else None,
                orientation="h",
                title="Top 20 POS Products by Sales Amount",
            )
            fig2.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig2, use_container_width=True)

            st.dataframe(df_pos_prod, use_container_width=True, height=420)
            st.download_button(
                "⬇ Download POS Excel",
                to_excel({"POS": df_pos_prod}),
                "pos_sales.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    # ======================
    #  Movement Tab
    # ======================
    with tabs[3]:
        st.subheader("🚚 Product Movement (Sales + POS)")

        if df_mov.empty:
            st.info("No data available.")
        else:
            total_sold_qty = df_mov["TotalSoldQty"].sum()
            total_sales_amt = df_mov["TotalSales"].sum()
            out_movers = df_mov[(df_mov["Qty"] <= 0) & (df_mov["TotalSoldQty"] > 0)]
            fast_movers = df_mov[df_mov["TotalSoldQty"] >= 10]  # threshold tweak karo

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Sold Qty", int(total_sold_qty))
            c2.metric("Total Sales (Sales+POS)", f"{total_sales_amt:,.0f}")
            c3.metric("Out-of-Stock Movers", len(out_movers))
            c4.metric("Fast Movers (Qty ≥10)", len(fast_movers))

            # Top movers
            df_top_mv = (
                df_mov.sort_values("TotalSoldQty", ascending=False)
                .head(20)
            )
            fig = px.bar(
                df_top_mv,
                x="TotalSoldQty",
                y="Product",
                color="Status",
                color_discrete_map=CM,
                orientation="h",
                title="Top 20 Products by Total Sold Qty",
            )
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

            # Out of stock movers (reorder priority)
            df_out_mv = out_movers.sort_values("TotalSoldQty", ascending=False).head(30)
            st.markdown("#### 🔁 Reorder Priority – Out-of-Stock but Selling Products")
            st.dataframe(
                df_out_mv[
                    [
                        "Ref",
                        "Product",
                        "Brand",
                        "Category",
                        "Qty",
                        "TotalSoldQty",
                        "TotalSales",
                        "PurQty",
                    ]
                ],
                use_container_width=True,
                height=350,
            )
            st.download_button(
                "⬇ Download Movement Excel",
                to_excel({"Movement": df_mov, "OutOfStockMovers": df_out_mv}),
                "movement.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    # ======================
    #  Summary Tab
    # ======================
    with tabs[4]:
        st.subheader("📊 Summary")

        total_stock_val = df_inv_f["Value"].sum()
        total_sales_period = df_sal_f["Amount"].sum() + df_pos_f["Amount"].sum()
        total_purchase_period = df_pur_f["Amount"].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Stock Value", f"{total_stock_val:,.0f}")
        c2.metric("Sales (Period)", f"{total_sales_period:,.0f}")
        c3.metric("Purchase (Period)", f"{total_purchase_period:,.0f}")

        # Brand summary
        if not df_mov.empty:
            df_brand_summary = (
                df_mov.groupby("Brand", as_index=False)
                .agg(
                    StockValue=("Value", "sum"),
                    SoldQty=("TotalSoldQty", "sum"),
                    Sales=("TotalSales", "sum"),
                )
                .sort_values("Sales", ascending=False)
            )
            st.markdown("#### Brand Performance")
            st.dataframe(df_brand_summary, use_container_width=True, height=350)

            fig = px.bar(
                df_brand_summary,
                x="Brand",
                y="Sales",
                title="Sales by Brand",
            )
            st.plotly_chart(fig, use_container_width=True)

            st.download_button(
                "⬇ Download Summary Excel",
                to_excel(
                    {
                        "Inventory": df_inv_f,
                        "Sales": df_sal_f,
                        "POS": df_pos_f,
                        "Movement": df_mov,
                        "BrandSummary": df_brand_summary,
                    }
                ),
                "summary_full.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("No movement data available for summary.")

# ==========================
#  Main
# ==========================
if st.session_state.uid is None:
    login_page()
else:
    dashboard()
