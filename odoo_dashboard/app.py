"""
SWAG Product Comparison Dashboard
Real-time Stock & Price Comparison across 5 Odoo Systems
"""

import xmlrpc.client
import streamlit as st
import pandas as pd
import io
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SWAG Product Comparison",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# MINIMAL CSS  (light theme, RTL support, clean cards)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Snapshot card */
.snap-card {
    background: #f8f9fa;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 14px 18px;
    font-size: 0.85rem;
    color: #444;
    line-height: 1.8;
}
/* Status badges */
.badge-ok   { background:#d4edda; color:#155724; border-radius:4px; padding:2px 8px; font-size:0.78rem; font-weight:600; }
.badge-off  { background:#f8d7da; color:#721c24; border-radius:4px; padding:2px 8px; font-size:0.78rem; font-weight:600; }
.badge-err  { background:#fff3cd; color:#856404; border-radius:4px; padding:2px 8px; font-size:0.78rem; font-weight:600; }
/* RTL helper */
[dir=rtl] { direction: rtl; text-align: right; }
/* Hide default Streamlit footer */
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SECRETS & SYSTEM KEYS
# ─────────────────────────────────────────────────────────────────────────────
secrets = st.secrets
SYSTEM_KEYS = ["SWAG", "LAROUCHE", "DIFFC", "FASHION_LIMITS", "SYSTEM5"]

# ─────────────────────────────────────────────────────────────────────────────
# LANGUAGE HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def get_lang() -> str:
    return st.session_state.get("lang", "EN")

def t(en: str, ar: str) -> str:
    """Return text in the current UI language."""
    return ar if get_lang() == "AR" else en

def get_system_name(key: str) -> str:
    """Return company name in current language."""
    try:
        if get_lang() == "AR":
            return secrets[key]["name_ar"]
        return secrets[key]["name"]
    except Exception:
        return key

# ─────────────────────────────────────────────────────────────────────────────
# ODOO XML-RPC HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _get_uid(url: str, db: str, user: str, api_key: str) -> int:
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", allow_none=True)
    return common.authenticate(db, user, api_key, {})

def _models(url: str) -> xmlrpc.client.ServerProxy:
    return xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", allow_none=True)

def _exec(url, db, uid, api_key, model, method, *args):
    return _models(url).execute_kw(db, uid, api_key, model, method, *args)

# ─────────────────────────────────────────────────────────────────────────────
# FETCH: TOTAL STOCK
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def fetch_total_stock(model_code: str) -> pd.DataFrame:
    """
    For each system: search product.product by default_code,
    return system / model / product / sale_price / on_hand rows.
    """
    price_col = t("Sale Price", "سعر البيع")
    qty_col   = t("On Hand",   "متوفر")
    sys_col   = t("System",    "النظام")
    mod_col   = t("Model",     "الموديل")
    prod_col  = t("Product",   "المنتج")

    rows = []
    for key in SYSTEM_KEYS:
        cfg = secrets.get(key)
        if not cfg:
            continue
        sys_name = get_system_name(key)
        try:
            uid = _get_uid(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
            if not uid:
                rows.append({
                    sys_col: sys_name, mod_col: model_code,
                    prod_col: "⚠️ Auth failed",
                    price_col: 0.0, qty_col: 0,
                    "_status": "ERROR",
                })
                continue

            prods = _exec(
                cfg["url"], cfg["db"], uid, cfg["api_key"],
                "product.product", "search_read",
                [[["default_code", "=", model_code]]],
                {"fields": ["id", "display_name", "default_code",
                            "qty_available", "list_price"]},
            )

            if not prods:
                rows.append({
                    sys_col: sys_name, mod_col: model_code,
                    prod_col: t("Not found", "غير موجود"),
                    price_col: 0.0, qty_col: 0,
                    "_status": "NOT_FOUND",
                })
            else:
                for r in prods:
                    rows.append({
                        sys_col:   sys_name,
                        mod_col:   r.get("default_code") or model_code,
                        prod_col:  r.get("display_name") or "",
                        price_col: float(r.get("list_price") or 0),
                        qty_col:   int(r.get("qty_available") or 0),
                        "_status": "OK",
                    })

        except Exception as e:
            rows.append({
                sys_col: sys_name, mod_col: model_code,
                prod_col: f"❌ {e}",
                price_col: 0.0, qty_col: 0,
                "_status": "ERROR",
            })

    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=[sys_col, mod_col, prod_col,
                                    price_col, qty_col, "_status"])
    return df


# ─────────────────────────────────────────────────────────────────────────────
# FETCH: BRANCH STOCK
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def fetch_branch_stock(model_code: str) -> pd.DataFrame:
    """
    For each system: get stock per location using stock.quant,
    also include sale_price (same for all branches).
    """
    price_col  = t("Sale Price",    "سعر البيع")
    qty_col    = t("On Hand",       "متوفر")
    sys_col    = t("System",        "النظام")
    query_col  = t("Query",         "البحث")
    branch_col = t("Branch",        "الفرع")
    loc_col    = t("Location",      "الموقع")

    rows = []
    for key in SYSTEM_KEYS:
        cfg = secrets.get(key)
        if not cfg:
            continue
        sys_name = get_system_name(key)
        try:
            uid = _get_uid(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
            if not uid:
                rows.append({
                    query_col: model_code, sys_col: sys_name,
                    branch_col: "⚠️ Auth", loc_col: "-",
                    price_col: 0.0, qty_col: 0, "_status": "ERROR",
                })
                continue

            # Get product id + sale price
            prods = _exec(
                cfg["url"], cfg["db"], uid, cfg["api_key"],
                "product.product", "search_read",
                [[["default_code", "=", model_code]]],
                {"fields": ["id", "list_price"], "limit": 1},
            )

            if not prods:
                rows.append({
                    query_col: model_code, sys_col: sys_name,
                    branch_col: t("Not found", "غير موجود"), loc_col: "-",
                    price_col: 0.0, qty_col: 0, "_status": "NOT_FOUND",
                })
                continue

            prod_id    = prods[0]["id"]
            sale_price = float(prods[0].get("list_price") or 0)

            # Get quants per location
            quants = _exec(
                cfg["url"], cfg["db"], uid, cfg["api_key"],
                "stock.quant", "search_read",
                [[["product_id", "=", prod_id],
                  ["location_id.usage", "=", "internal"]]],
                {"fields": ["location_id", "quantity"]},
            )

            if not quants:
                rows.append({
                    query_col: model_code, sys_col: sys_name,
                    branch_col: t("No stock", "لا مخزون"), loc_col: "-",
                    price_col: sale_price, qty_col: 0, "_status": "OK",
                })
            else:
                for q in quants:
                    loc      = q.get("location_id") or [None, "-"]
                    loc_name = loc[1] if isinstance(loc, list) else str(loc)
                    # derive branch code from location (first segment)
                    branch   = loc_name.split("/")[0].strip() if "/" in loc_name else loc_name
                    rows.append({
                        query_col:  model_code,
                        sys_col:    sys_name,
                        branch_col: branch,
                        loc_col:    loc_name,
                        price_col:  sale_price,
                        qty_col:    int(q.get("quantity") or 0),
                        "_status":  "OK",
                    })

        except Exception as e:
            rows.append({
                query_col: model_code, sys_col: sys_name,
                branch_col: f"❌ {e}", loc_col: "-",
                price_col: 0.0, qty_col: 0, "_status": "ERROR",
            })

    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=[query_col, sys_col, branch_col,
                                    loc_col, price_col, qty_col, "_status"])
    return df


# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY HELPER
# ─────────────────────────────────────────────────────────────────────────────
def _display_df(df: pd.DataFrame) -> None:
    """Render a DataFrame with bilingual column configs and price formatting."""
    if df.empty:
        st.info(t("No data.", "لا توجد بيانات."))
        return

    price_col = t("Sale Price", "سعر البيع")
    qty_col   = t("On Hand",   "متوفر")

    # Drop internal columns
    display_df = df.drop(columns=["_status"], errors="ignore")

    col_config: dict = {}
    if price_col in display_df.columns:
        col_config[price_col] = st.column_config.NumberColumn(
            price_col, format="%.2f SAR", min_value=0
        )
    if qty_col in display_df.columns:
        col_config[qty_col] = st.column_config.NumberColumn(
            qty_col, format="%d", min_value=0
        )

    st.dataframe(
        display_df,
        use_container_width=True,
        column_config=col_config,
        hide_index=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _to_csv(df: pd.DataFrame) -> bytes:
    clean = df.drop(columns=["_status"], errors="ignore")
    return clean.to_csv(index=False).encode("utf-8-sig")   # BOM for Arabic

def _to_excel(df: pd.DataFrame) -> bytes:
    clean = df.drop(columns=["_status"], errors="ignore")
    buf   = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        clean.to_excel(writer, index=False, sheet_name="Comparison")
    return buf.getvalue()

def _filename(tag: str, ext: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    return f"swag_comparison_{tag}_{ts}.{ext}"


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE DEFAULTS
# ─────────────────────────────────────────────────────────────────────────────
for key, default in [
    ("authenticated", False),
    ("user_email",    ""),
    ("lang",          "EN"),
    ("last_run",      None),
    ("total_df",      None),
    ("branch_df",     None),
    ("system_stats",  {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN PAGE
# ─────────────────────────────────────────────────────────────────────────────
def show_login() -> None:
    col1, col2, col3 = st.columns([1, 1.6, 1])
    with col2:
        st.markdown("## 📊 SWAG Product Comparison")
        st.markdown(
            "<p style='color:#888; margin-top:-10px;'>"
            "Real-time Stock &amp; Price across 5 Odoo Systems</p>",
            unsafe_allow_html=True,
        )
        st.divider()

        with st.form("login_form"):
            email    = st.text_input("Email", placeholder="you@swag.com.sa")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("🔐 Sign In", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Please enter both email and password.")
                return
            try:
                login_cfg = secrets["LOGIN"]
                common    = xmlrpc.client.ServerProxy(
                    f"{login_cfg['url']}/xmlrpc/2/common", allow_none=True
                )
                uid = common.authenticate(login_cfg["db"], email, password, {})
                if uid:
                    st.session_state.authenticated = True
                    st.session_state.user_email    = email
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please try again.")
            except Exception as e:
                st.error(f"Connection error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def show_dashboard() -> None:
    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ " + t("Settings", "الإعدادات"))
        lang_choice = st.radio(
            t("Language", "اللغة"),
            ["EN", "AR"],
            index=0 if get_lang() == "EN" else 1,
            horizontal=True,
        )
        if lang_choice != get_lang():
            st.session_state.lang = lang_choice
            st.rerun()

        st.divider()
        st.markdown(f"👤 **{st.session_state.user_email}**")
        if st.button("🚪 " + t("Logout", "تسجيل الخروج"), use_container_width=True):
            for k in ["authenticated", "user_email", "last_run",
                      "total_df", "branch_df", "system_stats"]:
                st.session_state[k] = (
                    False if k == "authenticated" else
                    ""    if k == "user_email"    else None
                )
            st.rerun()

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        f"## 📊 {t('SWAG Product Comparison', 'مقارنة منتجات سواغ')}"
    )
    st.markdown(
        f"<p style='color:#888; margin-top:-10px;'>"
        f"{t('Real-time stock & price across 5 Odoo systems', 'المخزون والسعر الفوري عبر 5 أنظمة أودو')}"
        f"</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Controls + Snapshot (2 columns) ───────────────────────────────────────
    left, right = st.columns([1.3, 1])

    with left:
        st.markdown(f"### 🔍 {t('Search', 'البحث')}")
        mode = st.radio(
            t("Mode", "الوضع"),
            [t("Single Model", "موديل واحد"), t("Multiple Models", "موديلات متعددة")],
            horizontal=True,
        )
        multi_mode = t("Multiple Models", "موديلات متعددة") in mode

        if multi_mode:
            raw_input = st.text_area(
                t("Enter model codes (one per line or comma-separated):",
                  "أدخل رموز الموديل (سطر لكل رمز أو مفصول بفاصلة):"),
                height=120,
                placeholder="ABC123\nDEF456\nGHI789",
            )
            model_codes = [
                m.strip()
                for m in raw_input.replace(",", "\n").splitlines()
                if m.strip()
            ]
        else:
            single = st.text_input(
                t("Model Code:", "رمز الموديل:"),
                placeholder="e.g. ABC123",
            )
            model_codes = [single.strip()] if single.strip() else []

        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            show_zero   = st.toggle(t("Show zero qty",     "إظهار الصفري"),   value=False)
        with col_t2:
            show_branch = st.toggle(t("Branch-wise view",  "عرض الفروع"),     value=False)
        with col_t3:
            sort_system = st.toggle(t("Sort by system",    "ترتيب حسب النظام"), value=False)

        compare_btn = st.button(
            f"🔍 {t('Compare', 'مقارنة')}",
            use_container_width=True,
            type="primary",
        )

    with right:
        st.markdown(f"### 📋 {t('Last Run Snapshot', 'ملخص آخر تشغيل')}")
        snap = st.session_state.last_run
        if snap:
            stats    = st.session_state.system_stats
            online   = sum(1 for v in stats.values() if v == "OK")
            snap_html = (
                f"<div class='snap-card'>"
                f"🕒 <b>{t('Time', 'الوقت')}:</b> {snap['time']}<br>"
                f"📦 <b>{t('Models checked', 'الموديلات')}:</b> {snap['models_checked']}<br>"
                f"🌐 <b>{t('Systems online', 'الأنظمة')}:</b> {online}/{len(SYSTEM_KEYS)}<br>"
                f"📊 <b>{t('Total rows', 'الإجمالي')}:</b> {snap['total_rows']}"
                f"</div>"
            )
            st.markdown(snap_html, unsafe_allow_html=True)
            st.markdown("")

            # System status badges
            for key in SYSTEM_KEYS:
                status = stats.get(key, "—")
                badge_cls = (
                    "badge-ok"  if status == "OK"  else
                    "badge-off" if status == "OFF" else
                    "badge-err"
                )
                label_badge = (
                    "✅ OK"   if status == "OK"  else
                    "🔴 OFF" if status == "OFF" else
                    "⚠️ ERR"
                )
                name = get_system_name(key)
                st.markdown(
                    f"<span><b>{name}</b> &nbsp;"
                    f"<span class='{badge_cls}'>{label_badge}</span></span>",
                    unsafe_allow_html=True,
                )
        else:
            st.info(t("Run a comparison to see results here.",
                      "قم بتشغيل مقارنة لرؤية النتائج هنا."))

    # ── Run Comparison ────────────────────────────────────────────────────────
    if compare_btn:
        if not model_codes:
            st.warning(t("Please enter at least one model code.",
                          "الرجاء إدخال رمز موديل واحد على الأقل."))
            st.stop()

        total_dfs  = []
        branch_dfs = []
        stats      = {}

        progress = st.progress(0, text=t("Fetching data…", "جلب البيانات…"))
        for i, code in enumerate(model_codes):
            tf = fetch_total_stock(code)
            total_dfs.append(tf)

            if show_branch:
                bf = fetch_branch_stock(code)
                branch_dfs.append(bf)

            # Derive per-system status from total df
            sys_col = t("System", "النظام")
            for key in SYSTEM_KEYS:
                sname = get_system_name(key)
                mask  = tf[sys_col] == sname if sys_col in tf.columns else pd.Series(False)
                if not mask.any():
                    stats[key] = stats.get(key) or "OFF"
                else:
                    row_status = tf.loc[mask, "_status"].iloc[0] if "_status" in tf.columns else "OK"
                    if row_status == "OK":
                        stats[key] = "OK"
                    elif row_status == "ERROR":
                        stats[key] = stats.get(key) or "ERROR"
                    else:
                        stats[key] = stats.get(key) or "OFF"

            progress.progress(
                (i + 1) / len(model_codes),
                text=f"{t('Processed', 'تمت معالجة')} {i+1}/{len(model_codes)}",
            )

        progress.empty()

        total_df  = pd.concat(total_dfs,  ignore_index=True) if total_dfs  else pd.DataFrame()
        branch_df = pd.concat(branch_dfs, ignore_index=True) if branch_dfs else pd.DataFrame()

        # ── filters ──
        qty_col = t("On Hand", "متوفر")
        if not show_zero and qty_col in total_df.columns:
            total_df = total_df[total_df[qty_col] != 0]
        if show_branch and not show_zero and qty_col in branch_df.columns:
            branch_df = branch_df[branch_df[qty_col] != 0]

        # ── sort ──
        if sort_system and t("System", "النظام") in total_df.columns:
            total_df  = total_df.sort_values(t("System", "النظام"))
        if show_branch and sort_system and t("System", "النظام") in branch_df.columns:
            branch_df = branch_df.sort_values([t("System", "النظام")])

        # ── persist ──
        st.session_state.total_df     = total_df
        st.session_state.branch_df    = branch_df
        st.session_state.system_stats = stats
        st.session_state.last_run     = {
            "time":          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "models_checked": len(model_codes),
            "total_rows":    len(total_df),
        }
        st.rerun()

    # ── Display Results ───────────────────────────────────────────────────────
    total_df  = st.session_state.total_df
    branch_df = st.session_state.branch_df

    if total_df is None or total_df.empty:
        return

    st.divider()

    # ── Metrics row ──────────────────────────────────────────────────────────
    stats   = st.session_state.system_stats
    online  = sum(1 for v in stats.values() if v == "OK")
    qty_col   = t("On Hand",   "متوفر")
    price_col = t("Sale Price","سعر البيع")

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric(t("Total Rows",     "إجمالي الصفوف"),    len(total_df))
    mc2.metric(t("Systems Online", "الأنظمة المتصلة"), f"{online}/{len(SYSTEM_KEYS)}")

    if qty_col in total_df.columns:
        mc3.metric(
            t("Total Qty", "إجمالي الكمية"),
            int(total_df[qty_col].sum()),
        )
    if price_col in total_df.columns:
        valid_prices = total_df[total_df[price_col] > 0][price_col]
        avg_price    = valid_prices.mean() if not valid_prices.empty else 0.0
        mc4.metric(
            t("Avg Sale Price", "متوسط سعر البيع"),
            f"{avg_price:,.2f} SAR",
        )

    # ── Total Table ───────────────────────────────────────────────────────────
    st.markdown(f"### 📦 {t('Total Stock View', 'عرض المخزون الإجمالي')}")
    _display_df(total_df)

    # ── Downloads: Total ──────────────────────────────────────────────────────
    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            f"⬇️ {t('Download CSV', 'تحميل CSV')}",
            data=_to_csv(total_df),
            file_name=_filename("total", "csv"),
            mime="text/csv",
            use_container_width=True,
        )
    with dl2:
        st.download_button(
            f"⬇️ {t('Download Excel', 'تحميل Excel')}",
            data=_to_excel(total_df),
            file_name=_filename("total", "xlsx"),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    # ── Branch Table ──────────────────────────────────────────────────────────
    if branch_df is not None and not branch_df.empty:
        st.divider()
        st.markdown(f"### 🗺️ {t('Branch-wise Stock View', 'عرض مخزون الفروع')}")
        _display_df(branch_df)

        # Bar chart
        sys_col    = t("System",   "النظام")
        branch_col = t("Branch",   "الفرع")
        if sys_col in branch_df.columns and qty_col in branch_df.columns:
            chart_df = (
                branch_df[branch_df["_status"] == "OK"]
                .groupby([sys_col, branch_col])[qty_col]
                .sum()
                .reset_index()
            )
            if not chart_df.empty:
                st.markdown(f"#### 📊 {t('Quantity by Branch', 'الكميات حسب الفرع')}")
                st.bar_chart(
                    chart_df.set_index(branch_col)[qty_col],
                    use_container_width=True,
                )

        dl3, dl4 = st.columns(2)
        with dl3:
            st.download_button(
                f"⬇️ {t('Download Branch CSV', 'تحميل CSV الفروع')}",
                data=_to_csv(branch_df),
                file_name=_filename("branch", "csv"),
                mime="text/csv",
                use_container_width=True,
            )
        with dl4:
            st.download_button(
                f"⬇️ {t('Download Branch Excel', 'تحميل Excel الفروع')}",
                data=_to_excel(branch_df),
                file_name=_filename("branch", "xlsx"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.authenticated:
    show_login()
else:
    show_dashboard()
