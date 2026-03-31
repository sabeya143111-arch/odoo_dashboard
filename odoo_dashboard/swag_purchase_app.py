import io
import xmlrpc.client
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

# ─────────────────────────────────────────
# PAGE CONFIG + BASIC STYLE
# ─────────────────────────────────────────
st.set_page_config(
    page_title="SWAG Purchase Analytics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    body, .stApp {
        background: linear-gradient(135deg,#0f0c29,#302b63,#24243e);
        color: #e8e8ff;
        font-family: "IBM Plex Sans", sans-serif;
    }
    .panel-header {
        background: linear-gradient(135deg,#1e1e3f,#2d2b55);
        border: 1px solid #667eea44;
        border-radius: 12px;
        padding: 12px 20px;
        margin: 16px 0 12px;
        font-size: 1.05rem;
        font-weight: 700;
        color: #c4b5fd;
    }
    .info-banner {
        background: linear-gradient(135deg,#1e3a5f,#1e3a5f99);
        border-left: 4px solid #3b82f6;
        border-radius: 10px;
        padding: 11px 16px;
        margin: 8px 0 16px;
        font-size: 0.9rem;
        color: #93c5fd;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────
# ODOO CONNECTION – SAME AS MAIN APP (SWAG ONLY)
# ─────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def proxy_url(url: str, ep: str):
    return xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/{ep}", allow_none=True)

@st.cache_data(ttl=8 * 60 * 60, show_spinner=False)
def auth(url: str, db: str, user: str, key: str):
    try:
        common = proxy_url(url, "common")
        uid = common.authenticate(db, user, key, {})
        return uid or None
    except Exception:
        return None

def xurl(url, db, uid, key, model, method, domain=None, kw=None):
    if domain is None:
        domain = []
    if kw is None:
        kw = {}
    models = proxy_url(url, "object")
    return models.execute_kw(db, uid, key, model, method, domain, kw)

def get_swag_cfg():
    """
    Same style as your main app:
    st.secrets["SWAG"] should contain: url, db, user, apikey/password.
    """
    cfg = st.secrets.get("SWAG", {})
    return (
        cfg.get("url"),
        cfg.get("db"),
        cfg.get("user"),
        cfg.get("apikey") or cfg.get("password"),
    )

def tocsv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")

# ─────────────────────────────────────────
# PLACEHOLDER: Yaha tum apne REAL helpers paste karoge
# (fetch_swag_purchase_history, fetch_swag_model_purchases_and_stock,
#  to_excel_purchase) – same code jo file:182 me hai.
# ─────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_swag_purchase_history(model_code: str | None,
                                date_from: str,
                                date_to: str) -> pd.DataFrame:
    """
    TODO: file:182 se fetchswagpurchasehistory ka full code yahan paste karo.
    Yeh function internally get_swag_cfg() + auth + xurl ka use kare.
    """
    return pd.DataFrame()

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_swag_model_purchases_and_stock(model_code: str,
                                         date_from: str,
                                         date_to: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    TODO: file:182 se fetchswagmodelpurchasesandstock ka full code yahan paste karo.
    Woh already SWAG config + auth + xurl use kar raha hai –
    sirf direct copy-paste karo.
    """
    purchempty = pd.DataFrame(columns=["Branch", "Vendor", "Date", "Qty Purchased"])
    stockempty = pd.DataFrame(columns=["Branch", "On Hand"])
    return purchempty, stockempty

def to_excel_purchase(df: pd.DataFrame) -> bytes:
    """
    TODO: file:182 se toexcelpurchase ka full code paste karo.
    Abhi simple fallback rakha hai.
    """
    buf = io.BytesIO()
    df.to_excel(buf, index=False, sheet_name="SWAG Purchase")
    return buf.getvalue()

# ─────────────────────────────────────────
# PANELS: A (overall), B (single model), C (model vs stock)
# ─────────────────────────────────────────

def panel_A_overall_purchase():
    st.markdown('<div class="panel-header">Panel A – SWAG Purchase Analytics</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="info-banner">Overall purchase analytics from the <b>SWAG</b> system – vendor, product, category, brand.</div>',
        unsafe_allow_html=True,
    )

    col_code, col_from, col_to, col_btn = st.columns([1.5, 1, 1, 1])
    with col_from:
        d_from = st.date_input("From", value=datetime.now().date() - timedelta(days=365), key="pa_from")
    with col_to:
        d_to = st.date_input("To", value=datetime.now().date(), key="pa_to")
    with col_code:
        model_code = st.text_input("Model Code (optional)", value="", key="pa_model").strip().upper()
    with col_btn:
        fetch = st.button("Fetch Purchase Analytics", type="primary", use_container_width=True, key="pa_btn")

    if not fetch:
        st.info("Select date range and click “Fetch Purchase Analytics”.")
        return

    date_from = d_from.strftime("%Y-%m-%d")
    date_to = d_to.strftime("%Y-%m-%d")
    mc = model_code or None

    with st.spinner("Fetching purchase data from SWAG..."):
        pdf = fetch_swag_purchase_history(mc, date_from, date_to)

    if pdf is None or pdf.empty:
        st.info("No purchases found for this period / model.")
        return

    total_qty = float(pdf["Qty"].sum())
    total_amount = float(pdf["Subtotal"].sum())
    vendors = int(pdf["Vendor"].nunique())
    models = int(pdf["Model Code"].nunique())

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Qty Purchased", f"{total_qty:,.0f}")
    k2.metric("Total Purchase Amount", f"{total_amount:,.2f} SAR")
    k3.metric("Distinct Vendors", f"{vendors}")
    k4.metric("Distinct Products", f"{models}")

    st.divider()
    st.write("🔧 Yaha Top 10 Vendor / Product / Category / Brand charts ka code paste karo.")

def panel_B_single_model():
    st.markdown('<div class="panel-header">Panel B – Single Model Purchase Detail</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="info-banner">Enter one model code to see vendor‑wise history, charts, and prices.</div>',
        unsafe_allow_html=True,
    )

    col_code, col_from, col_to, col_btn = st.columns([1.5, 1, 1, 1])
    with col_code:
        model_code = st.text_input("Model Code (Internal Ref)", value="", key="pb_model").strip().upper()
    with col_from:
        d_from = st.date_input("From", value=datetime.now().date() - timedelta(days=365), key="pb_from")
    with col_to:
        d_to = st.date_input("To", value=datetime.now().date(), key="pb_to")
    with col_btn:
        fetch = st.button("Fetch Single Model Detail", type="primary", use_container_width=True, key="pb_btn")

    if not fetch:
        st.info("Enter a model code and click the button.")
        return
    if not model_code:
        st.warning("Model code is required.")
        return

    date_from = d_from.strftime("%Y-%m-%d")
    date_to = d_to.strftime("%Y-%m-%d")

    with st.spinner("Fetching purchase history for this model from SWAG..."):
        pdf = fetch_swag_purchase_history(model_code, date_from, date_to)

    if pdf is None or pdf.empty:
        st.info("No purchases found for this model in the selected period.")
        return

    st.write("🔧 Yaha Panel B ka detailed analytics code paste karo (KPIs, vendor filter, time‑series, vendor share, table + downloads).")

def panel_C_model_vs_stock():
    st.markdown('<div class="panel-header">Panel C – Model Purchase vs Stock (SWAG Branches)</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="info-banner">See how much SWAG purchased for one model and how much stock is left in each branch.</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
    with c1:
        model_code = st.text_input("Model Code (Internal Ref)", value="", key="pc_model").strip().upper()
    with c2:
        d_from = st.date_input("From", value=datetime.now().date() - timedelta(days=365), key="pc_from")
    with c3:
        d_to = st.date_input("To", value=datetime.now().date(), key="pc_to")
    with c4:
        fetch = st.button("Fetch SWAG Model Analytics", type="primary", use_container_width=True, key="pc_btn")

    if not fetch:
        st.info("Enter a model code and click the button.")
        return
    if not model_code:
        st.warning("Model code is required.")
        return

    date_from = d_from.strftime("%Y-%m-%d")
    date_to = d_to.strftime("%Y-%m-%d")

    with st.spinner("Fetching model purchase + stock from SWAG..."):
        purch_df, stock_df = fetch_swag_model_purchases_and_stock(model_code, date_from, date_to)

    if purch_df.empty and stock_df.empty:
        st.info("No purchase or stock found for this model.")
        return

    total_purch = float(purch_df["Qty Purchased"].sum()) if not purch_df.empty else 0.0
    total_stock = float(stock_df["On Hand"].sum()) if not stock_df.empty else 0.0
    branches_purch = int(purch_df["Branch"].nunique()) if not purch_df.empty else 0
    branches_stock = int(stock_df["Branch"].nunique()) if not stock_df.empty else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Qty Purchased", f"{total_purch:,.0f}")
    k2.metric("Total Qty On Hand", f"{total_stock:,.0f}")
    k3.metric("Branches (Purchased)", f"{branches_purch}")
    k4.metric("Branches (Stock)", f"{branches_stock}")

    st.divider()
    st.write("🔧 Yaha branch‑wise bar charts + raw tables + CSV/Excel download ka code paste karo.")

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def main():
    st.markdown(
        """
        <div class="dash-header">
            <div class="dash-title">SWAG Purchase Analytics</div>
            <div class="dash-subtitle">
                Vendor, product and branch insights – SWAG Odoo 19
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tabA, tabB, tabC = st.tabs([
        "Panel A – Overall Purchase",
        "Panel B – Single Model",
        "Panel C – Model vs Stock",
    ])

    with tabA:
        panel_A_overall_purchase()
    with tabB:
        panel_B_single_model()
    with tabC:
        panel_C_model_vs_stock()

if __name__ == "__main__":
    main()
