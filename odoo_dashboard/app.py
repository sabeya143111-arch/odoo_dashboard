"""
SWAG Product Comparison Dashboard
Real-time Stock & Price Comparison across 4 Odoo Systems
Version 2.0 — Production Ready
"""

import io
import xmlrpc.client
from datetime import datetime

import pandas as pd
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SWAG Product Comparison",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans Arabic', sans-serif;
}

/* ── Cards ─────────────────────────────────────────────── */
.snap-card {
    background: #f8f9fb;
    border: 1px solid #dee2e6;
    border-radius: 10px;
    padding: 14px 18px;
    font-size: 0.87rem;
    color: #333;
    line-height: 2;
}
.sys-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}

/* ── Status badges ──────────────────────────────────────── */
.badge-ok  { background:#d1fae5; color:#065f46; border-radius:4px; padding:2px 8px; font-size:0.76rem; font-weight:700; }
.badge-off { background:#fee2e2; color:#991b1b; border-radius:4px; padding:2px 8px; font-size:0.76rem; font-weight:700; }
.badge-err { background:#fef3c7; color:#92400e; border-radius:4px; padding:2px 8px; font-size:0.76rem; font-weight:700; }

/* ── Info banners ───────────────────────────────────────── */
.info-banner {
    background: #eff6ff;
    border-left: 4px solid #3b82f6;
    border-radius: 6px;
    padding: 10px 14px;
    margin: 8px 0 16px 0;
    font-size: 0.85rem;
    color: #1e40af;
}
.warn-banner {
    background: #fffbeb;
    border-left: 4px solid #f59e0b;
    border-radius: 6px;
    padding: 10px 14px;
    margin: 8px 0 16px 0;
    font-size: 0.85rem;
    color: #92400e;
}
.success-banner {
    background: #f0fdf4;
    border-left: 4px solid #22c55e;
    border-radius: 6px;
    padding: 10px 14px;
    margin: 8px 0 16px 0;
    font-size: 0.85rem;
    color: #166534;
}

/* ── Mono codes ─────────────────────────────────────────── */
.mono { font-family: 'IBM Plex Mono', monospace; font-size: 0.82rem; }

footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SECRETS & CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
secrets = st.secrets
SYSTEM_KEYS = ["SWAG", "LAROUCHE", "DIFFC", "FASHION_LIMITS"]

# ─────────────────────────────────────────────────────────────────────────────
# LANGUAGE & TRANSLATION
# ─────────────────────────────────────────────────────────────────────────────
def get_lang() -> str:
    return st.session_state.get("lang", "EN")


def t(en: str, ar: str) -> str:
    return ar if get_lang() == "AR" else en


def get_system_name(key: str) -> str:
    cfg = secrets.get(key, {})
    if get_lang() == "AR":
        return cfg.get("name_ar", cfg.get("name", key))
    return cfg.get("name", key)


# ─────────────────────────────────────────────────────────────────────────────
# DOWNLOAD HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def to_csv_arabic(df: pd.DataFrame) -> bytes:
    clean = df.drop(columns=["_status"], errors="ignore")
    return clean.to_csv(index=False).encode("utf-8-sig")


def to_excel_arabic(df: pd.DataFrame) -> bytes:
    clean = df.drop(columns=["_status"], errors="ignore")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        clean.to_excel(writer, index=False, sheet_name="Data")
    return buf.getvalue()


def dl_filename(tag: str, ext: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    return f"swag_comparison_{tag}_{ts}.{ext}"


# ─────────────────────────────────────────────────────────────────────────────
# XML-RPC HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _authenticate(url: str, db: str, user: str, api_key: str):
    try:
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", allow_none=True)
        uid = common.authenticate(db, user, api_key, {})
        return uid if uid else None
    except Exception:
        return None


def _exec(url, db, uid, api_key, model, method, domain, kwargs):
    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object", allow_none=True)
    return models.execute_kw(db, uid, api_key, model, method, domain, kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# FETCH: TOTAL STOCK — with VARIANT SUPPORT
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def fetch_total_stock(model_code: str, exact: bool = False) -> pd.DataFrame:
    """
    Fetch product.product across all 4 systems.

    When exact=False (default):
      Uses =like wildcard so XP6013 matches XP6013-S, XP6013-M, XP6013-L, etc.
    When exact=True:
      Uses = for an exact default_code match.

    qty_available is Odoo's computed field — matches what the product form shows.
    """
    COL_SYS   = t("System",     "النظام")
    COL_MOD   = t("Model Code", "رمز الموديل")
    COL_PROD  = t("Product",    "المنتج")
    COL_PRICE = t("Sale Price", "سعر البيع")
    COL_QTY   = t("On Hand",   "متوفر")

    operator = "=" if exact else "=like"
    pattern  = model_code if exact else f"{model_code}%"

    rows = []
    for key in SYSTEM_KEYS:
        cfg      = secrets.get(key)
        sys_name = get_system_name(key)

        if not cfg:
            rows.append({COL_SYS: sys_name, COL_MOD: model_code,
                         COL_PROD: "—", COL_PRICE: 0.0, COL_QTY: 0,
                         "_status": "ERROR"})
            continue

        uid = _authenticate(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
        if not uid:
            rows.append({COL_SYS: sys_name, COL_MOD: model_code,
                         COL_PROD: t("⚠️ Auth failed", "⚠️ فشل التحقق"),
                         COL_PRICE: 0.0, COL_QTY: 0, "_status": "ERROR"})
            continue

        try:
            prods = _exec(
                cfg["url"], cfg["db"], uid, cfg["api_key"],
                "product.product", "search_read",
                [[["default_code", operator, pattern]]],
                {"fields": ["id", "display_name", "default_code",
                            "qty_available", "list_price"]},
            )

            if not prods:
                rows.append({COL_SYS: sys_name, COL_MOD: model_code,
                             COL_PROD: t("Not found", "غير موجود"),
                             COL_PRICE: 0.0, COL_QTY: 0,
                             "_status": "NOT_FOUND"})
            else:
                for p in prods:
                    rows.append({
                        COL_SYS:   sys_name,
                        COL_MOD:   p.get("default_code") or model_code,
                        COL_PROD:  p.get("display_name") or "",
                        COL_PRICE: float(p.get("list_price") or 0),
                        COL_QTY:   int(p.get("qty_available") or 0),
                        "_status": "OK",
                    })
        except Exception as e:
            rows.append({COL_SYS: sys_name, COL_MOD: model_code,
                         COL_PROD: f"❌ {e}", COL_PRICE: 0.0, COL_QTY: 0,
                         "_status": "ERROR"})

    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=[COL_SYS, COL_MOD, COL_PROD, COL_PRICE, COL_QTY, "_status"])


# ─────────────────────────────────────────────────────────────────────────────
# FETCH: BRANCH STOCK — with VARIANT SUPPORT
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def fetch_branch_stock(model_code: str, exact: bool = False) -> pd.DataFrame:
    """
    Fetch stock.quant per location across all 4 systems.

    When exact=False (default):
      Uses =like wildcard to capture all size/color variants.
    When exact=True:
      Uses = for an exact default_code match.

    Filter: ["quantity", ">", 0] only — no location_id.usage restriction.
    This includes WH02, transit, and all valid stock locations.
    """
    COL_QUERY  = t("Query",     "البحث")
    COL_SYS    = t("System",    "النظام")
    COL_BRANCH = t("Branch",    "الفرع")
    COL_LOC    = t("Location",  "الموقع")
    COL_PRICE  = t("Sale Price","سعر البيع")
    COL_QTY    = t("On Hand",   "متوفر")
    COL_MOD    = t("Model Code","رمز الموديل")

    operator = "=" if exact else "=like"
    pattern  = model_code if exact else f"{model_code}%"

    rows = []
    for key in SYSTEM_KEYS:
        cfg      = secrets.get(key)
        sys_name = get_system_name(key)

        if not cfg:
            continue

        uid = _authenticate(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
        if not uid:
            rows.append({
                COL_QUERY: model_code, COL_SYS: sys_name,
                COL_BRANCH: t("⚠️ Auth failed", "⚠️ فشل التحقق"),
                COL_MOD: "—", COL_LOC: "—", COL_PRICE: 0.0, COL_QTY: 0,
                "_status": "ERROR",
            })
            continue

        try:
            # Step 1: get matching product ids + sale prices
            prods = _exec(
                cfg["url"], cfg["db"], uid, cfg["api_key"],
                "product.product", "search_read",
                [[["default_code", operator, pattern]]],
                {"fields": ["id", "default_code", "list_price"]},
            )

            if not prods:
                rows.append({
                    COL_QUERY: model_code, COL_SYS: sys_name,
                    COL_BRANCH: t("Not found", "غير موجود"),
                    COL_MOD: "—", COL_LOC: "—", COL_PRICE: 0.0, COL_QTY: 0,
                    "_status": "NOT_FOUND",
                })
                continue

            # Step 2: for each matching product, fetch quants
            for prod in prods:
                prod_id    = prod["id"]
                sale_price = float(prod.get("list_price") or 0)
                prod_code  = prod.get("default_code") or model_code

                quants = _exec(
                    cfg["url"], cfg["db"], uid, cfg["api_key"],
                    "stock.quant", "search_read",
                    [[["product_id", "=", prod_id],
                      ["quantity",   ">", 0]]],
                    {"fields": ["location_id", "quantity"]},
                )

                if not quants:
                    rows.append({
                        COL_QUERY:  model_code,
                        COL_SYS:    sys_name,
                        COL_BRANCH: t("No stock", "لا مخزون"),
                        COL_MOD:    prod_code,
                        COL_LOC:    "—",
                        COL_PRICE:  sale_price,
                        COL_QTY:    0,
                        "_status":  "OK",
                    })
                else:
                    for q in quants:
                        loc_raw  = q.get("location_id") or [None, "—"]
                        loc_name = loc_raw[1] if isinstance(loc_raw, list) else str(loc_raw)
                        branch   = loc_name.split("/")[0].strip()
                        rows.append({
                            COL_QUERY:  model_code,
                            COL_SYS:    sys_name,
                            COL_BRANCH: branch,
                            COL_MOD:    prod_code,
                            COL_LOC:    loc_name,
                            COL_PRICE:  sale_price,
                            COL_QTY:    int(q.get("quantity") or 0),
                            "_status":  "OK",
                        })

        except Exception as e:
            rows.append({
                COL_QUERY: model_code, COL_SYS: sys_name,
                COL_BRANCH: f"❌ {e}", COL_MOD: "—", COL_LOC: "—",
                COL_PRICE: 0.0, COL_QTY: 0, "_status": "ERROR",
            })

    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=[COL_QUERY, COL_SYS, COL_BRANCH,
                 COL_MOD, COL_LOC, COL_PRICE, COL_QTY, "_status"])


# ─────────────────────────────────────────────────────────────────────────────
# DISPLAY DATAFRAME
# ─────────────────────────────────────────────────────────────────────────────
def display_df(df: pd.DataFrame) -> None:
    if df is None or df.empty:
        st.info(t("No data to display.", "لا توجد بيانات للعرض."))
        return

    price_col = t("Sale Price", "سعر البيع")
    qty_col   = t("On Hand",   "متوفر")
    show      = df.drop(columns=["_status"], errors="ignore")
    cfg: dict = {}

    if price_col in show.columns:
        cfg[price_col] = st.column_config.NumberColumn(
            price_col, format="%.2f SAR", min_value=0)
    if qty_col in show.columns:
        cfg[qty_col] = st.column_config.NumberColumn(
            qty_col, format="%d", min_value=0)

    st.dataframe(show, use_container_width=True,
                 column_config=cfg, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE DEFAULTS
# ─────────────────────────────────────────────────────────────────────────────
_DEFAULTS = {
    "authenticated": False,
    "user_email":    "",
    "lang":          "EN",
    "last_run":      None,
    "total_df":      None,
    "branch_df":     None,
    "sys_stats":     {},
    "search_exact":  False,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN PAGE
# ─────────────────────────────────────────────────────────────────────────────
def show_login() -> None:
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown("## 📊 SWAG Product Comparison")
        st.markdown(
            "<p style='color:#6c757d; margin-top:-10px;'>"
            "Real-time Stock &amp; Price across 4 Odoo Systems</p>",
            unsafe_allow_html=True)
        st.markdown("")

        with st.form("login_form"):
            email    = st.text_input("Email", placeholder="you@swag.com.sa")
            password = st.text_input("Password", type="password")
            submit   = st.form_submit_button("🔐 Sign In", use_container_width=True)

        if submit:
            if not email or not password:
                st.error("Please fill in both fields.")
                return
            try:
                cfg = secrets["LOGIN"]
                uid = _authenticate(cfg["url"], cfg["db"], email, password)
                if uid:
                    st.session_state.authenticated = True
                    st.session_state.user_email    = email
                    st.rerun()
                else:
                    st.error("Invalid credentials — please try again.")
            except Exception as e:
                st.error(f"Connection error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD PAGE
# ─────────────────────────────────────────────────────────────────────────────
def show_dashboard() -> None:

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"### ⚙️ {t('Settings', 'الإعدادات')}")

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
        st.markdown(f"👤 `{st.session_state.user_email}`")
        if st.button(f"🚪 {t('Logout','تسجيل الخروج')}", use_container_width=True):
            for k, v in _DEFAULTS.items():
                st.session_state[k] = v
            st.rerun()

        st.divider()
        st.markdown(f"##### 🔬 {t('Search Mode','وضع البحث')}")
        exact_toggle = st.toggle(
            t("Exact match only", "تطابق تام فقط"),
            value=st.session_state.search_exact,
            help=t(
                "OFF = wildcard match (XP6013 → XP6013-S, XP6013-M, XP6013-L …)\n"
                "ON  = exact code match only",
                "إيقاف = بحث بالبادئة (XP6013 يجلب XP6013-S و M و L …)\n"
                "تشغيل = تطابق تام بالرمز فقط"
            ),
        )
        if exact_toggle != st.session_state.search_exact:
            st.session_state.search_exact = exact_toggle
            # Clear cached results so next run re-fetches with new mode
            st.session_state.total_df  = None
            st.session_state.branch_df = None
            st.rerun()

        mode_label = (
            t("🎯 Exact match", "🎯 تطابق تام")
            if st.session_state.search_exact
            else t("🔍 Variant match (wildcard)", "🔍 مطابقة المتغيرات (بادئة)")
        )
        st.caption(mode_label)

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        f"## 📊 {t('SWAG Product Comparison','مقارنة منتجات سواغ')}")
    st.markdown(
        f"<p style='color:#6c757d; margin-top:-12px;'>"
        f"{t('Real-time stock & price across 4 Odoo systems','المخزون والسعر الفوري عبر 4 أنظمة أودو')}"
        f"</p>", unsafe_allow_html=True)
    st.divider()

    # ── Two-column layout ─────────────────────────────────────────────────────
    left, right = st.columns([1.5, 1])

    # ── LEFT: Controls ────────────────────────────────────────────────────────
    with left:
        st.markdown(f"#### 🔍 {t('Search','البحث')}")

        # Variant mode info banner
        if not st.session_state.search_exact:
            st.markdown(
                f"<div class='info-banner'>"
                f"{'🔍 <b>Variant mode active</b> — entering <span class=\"mono\">XP6013</span> will match '
                   '<span class=\"mono\">XP6013-S</span>, <span class=\"mono\">XP6013-M</span>, '
                   '<span class=\"mono\">XP6013-L</span> and all other variants automatically.'
                   if get_lang() == 'EN' else
                   '🔍 <b>وضع المتغيرات مفعّل</b> — إدخال <span class=\"mono\">XP6013</span> سيجلب '
                   '<span class=\"mono\">XP6013-S</span> و <span class=\"mono\">XP6013-M</span> '
                   'وكل المقاسات تلقائيًا.'}"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div class='warn-banner'>"
                f"{'🎯 <b>Exact match mode</b> — only products with an identical code will be returned.'
                   if get_lang() == 'EN' else
                   '🎯 <b>وضع التطابق التام</b> — سيتم إرجاع المنتجات ذات الرمز المطابق تمامًا فقط.'}"
                f"</div>",
                unsafe_allow_html=True,
            )

        mode_single = t("Single Model",    "موديل واحد")
        mode_multi  = t("Multiple Models", "موديلات متعددة")
        mode = st.radio(t("Mode","الوضع"), [mode_single, mode_multi],
                        horizontal=True, label_visibility="collapsed")
        is_multi = (mode == mode_multi)

        if is_multi:
            raw = st.text_area(
                t("Model codes (one per line or comma-separated):",
                  "رموز الموديل (سطر لكل رمز أو مفصولة بفاصلة):"),
                height=130,
                placeholder="ABC123\nDEF456, GHI789",
            )
            codes = [c.strip()
                     for c in raw.replace(",", "\n").splitlines()
                     if c.strip()]
        else:
            single = st.text_input(
                t("Model Code:", "رمز الموديل:"),
                placeholder=t("e.g. XP6013  (matches all variants)", "مثال: XP6013  (يجلب كل المقاسات)"))
            codes = [single.strip()] if single.strip() else []

        st.caption(
            t("Use the Internal Reference (default_code), not the product display name.",
              "استخدم المرجع الداخلي (default_code)، وليس اسم المنتج."))

        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            show_zero   = st.toggle(t("Show zero qty",  "إظهار الصفري"),   value=False)
        with tc2:
            show_branch = st.toggle(t("Branch details", "تفاصيل الفروع"),  value=False)
        with tc3:
            sort_sys    = st.toggle(t("Sort by system", "ترتيب بالنظام"),  value=False)

        compare_btn = st.button(
            f"🔍 {t('Compare','مقارنة')}",
            use_container_width=True, type="primary")

    # ── RIGHT: Last Run Snapshot ──────────────────────────────────────────────
    with right:
        st.markdown(f"#### 📋 {t('Last Run Snapshot','ملخص آخر تشغيل')}")
        snap  = st.session_state.last_run
        stats = st.session_state.sys_stats

        if snap and not all(k in snap for k in ("time", "models", "rows")):
            st.session_state.last_run = None
            snap = None

        if not snap:
            st.info(t("Run a comparison to see results here.",
                      "قم بتشغيل مقارنة لرؤية النتائج هنا."))
        else:
            online     = sum(1 for v in stats.values() if v == "OK")
            match_mode = (t("Exact", "تطابق تام")
                          if snap.get("exact_mode")
                          else t("Variant (wildcard)", "متغيرات (بادئة)"))

            st.markdown(
                f"<div class='snap-card'>"
                f"🕒 <b>{t('Time','الوقت')}:</b> {snap.get('time','—')}<br>"
                f"📦 <b>{t('Models','الموديلات')}:</b> {snap.get('models','—')}<br>"
                f"🌐 <b>{t('Systems online','الأنظمة')}:</b> {online}/4<br>"
                f"📊 <b>{t('Total rows','الصفوف')}:</b> {snap.get('rows','—')}<br>"
                f"🔍 <b>{t('Match mode','وضع البحث')}:</b> {match_mode}"
                f"</div>", unsafe_allow_html=True)
            st.markdown("")

            for key in SYSTEM_KEYS:
                status = stats.get(key, "—")
                badge_cls  = ("badge-ok"  if status == "OK"
                               else "badge-off" if status == "NOT_FOUND"
                               else "badge-err")
                badge_text = ("✅ OK"   if status == "OK"
                               else "🔴 OFF" if status == "NOT_FOUND"
                               else "⚠️ ERR")
                st.markdown(
                    f"<div class='sys-row'>"
                    f"<span style='font-size:0.85rem'><b>{get_system_name(key)}</b></span>"
                    f"<span class='{badge_cls}'>{badge_text}</span>"
                    f"</div>", unsafe_allow_html=True)

    # ── Run comparison ────────────────────────────────────────────────────────
    if compare_btn:
        if not codes:
            st.warning(t("Please enter at least one model code.",
                          "الرجاء إدخال رمز موديل واحد على الأقل."))
            st.stop()

        exact        = st.session_state.search_exact
        total_parts  = []
        branch_parts = []
        new_stats    = {k: "NOT_FOUND" for k in SYSTEM_KEYS}
        sys_col      = t("System", "النظام")
        qty_col      = t("On Hand","متوفر")

        bar = st.progress(0, text=t("Fetching data…","جلب البيانات…"))

        for i, code in enumerate(codes):
            tf = fetch_total_stock(code, exact=exact)
            total_parts.append(tf)

            if show_branch:
                bf = fetch_branch_stock(code, exact=exact)
                branch_parts.append(bf)

            if "_status" in tf.columns and sys_col in tf.columns:
                for key in SYSTEM_KEYS:
                    name = get_system_name(key)
                    mask = tf[sys_col] == name
                    if mask.any():
                        row_st = tf.loc[mask, "_status"].iloc[0]
                        if row_st == "OK":
                            new_stats[key] = "OK"
                        elif row_st == "ERROR" and new_stats[key] != "OK":
                            new_stats[key] = "ERROR"

            bar.progress(
                (i + 1) / len(codes),
                text=f"{t('Processed','تمت معالجة')} {i+1}/{len(codes)}")

        bar.empty()

        total_df  = pd.concat(total_parts,  ignore_index=True) if total_parts  else pd.DataFrame()
        branch_df = pd.concat(branch_parts, ignore_index=True) if branch_parts else pd.DataFrame()

        # Apply show-zero filter
        if not show_zero and qty_col in total_df.columns:
            total_df = total_df[total_df[qty_col] != 0].reset_index(drop=True)
        if show_branch and not show_zero and qty_col in branch_df.columns:
            branch_df = branch_df[branch_df[qty_col] > 0].reset_index(drop=True)

        # Apply sort
        if sort_sys and sys_col in total_df.columns:
            total_df = total_df.sort_values(sys_col).reset_index(drop=True)
        if show_branch and sort_sys and sys_col in branch_df.columns:
            branch_df = branch_df.sort_values(sys_col).reset_index(drop=True)

        st.session_state.total_df  = total_df
        st.session_state.branch_df = branch_df
        st.session_state.sys_stats = new_stats
        st.session_state.last_run  = {
            "time":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "models":     len(codes),
            "rows":       len(total_df),
            "exact_mode": exact,
        }
        st.rerun()

    # ── Display results ───────────────────────────────────────────────────────
    total_df  = st.session_state.total_df
    branch_df = st.session_state.branch_df

    if total_df is None or total_df.empty:
        return

    st.divider()

    # KPI metrics row
    qty_col   = t("On Hand",   "متوفر")
    price_col = t("Sale Price","سعر البيع")
    stats     = st.session_state.sys_stats
    online    = sum(1 for v in stats.values() if v == "OK")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(t("Total Rows",     "إجمالي الصفوف"),   len(total_df))
    m2.metric(t("Systems Online", "الأنظمة المتصلة"), f"{online}/4")

    ok_rows = (total_df[total_df["_status"] == "OK"]
               if "_status" in total_df.columns else total_df)

    if qty_col in ok_rows.columns:
        m3.metric(t("Total Qty","إجمالي الكمية"), int(ok_rows[qty_col].sum()))

    if price_col in ok_rows.columns:
        valid = ok_rows[ok_rows[price_col] > 0][price_col]
        avg   = valid.mean() if not valid.empty else 0.0
        m4.metric(t("Avg Sale Price","متوسط سعر البيع"), f"{avg:,.2f} SAR")

    # ── Total stock table ─────────────────────────────────────────────────────
    st.markdown(f"### 📦 {t('Total Stock View','عرض المخزون الإجمالي')}")
    display_df(total_df)

    dl1, dl2, _ = st.columns([1, 1, 2])
    with dl1:
        st.download_button(
            f"⬇️ {t('Download CSV','تحميل CSV')}",
            data=to_csv_arabic(total_df),
            file_name=dl_filename("total", "csv"),
            mime="text/csv",
            use_container_width=True)
    with dl2:
        st.download_button(
            f"⬇️ {t('Download Excel','تحميل Excel')}",
            data=to_excel_arabic(total_df),
            file_name=dl_filename("total", "xlsx"),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)

    # ── Branch-wise table ─────────────────────────────────────────────────────
    if branch_df is not None and not branch_df.empty:
        st.divider()
        st.markdown(f"### 🗺️ {t('Branch-wise Stock View','عرض مخزون الفروع')}")
        display_df(branch_df)

        branch_col = t("Branch", "الفرع")
        sys_col    = t("System", "النظام")
        ok_branch  = (branch_df[branch_df["_status"] == "OK"]
                      if "_status" in branch_df.columns else branch_df)

        if (not ok_branch.empty
                and branch_col in ok_branch.columns
                and qty_col in ok_branch.columns):
            chart = (ok_branch
                     .groupby([sys_col, branch_col])[qty_col]
                     .sum()
                     .reset_index())
            if not chart.empty:
                st.markdown(f"#### 📊 {t('Qty by Branch','الكميات حسب الفرع')}")
                st.bar_chart(chart.set_index(branch_col)[qty_col],
                             use_container_width=True)

        dl3, dl4, _ = st.columns([1, 1, 2])
        with dl3:
            st.download_button(
                f"⬇️ {t('Branch CSV','CSV الفروع')}",
                data=to_csv_arabic(branch_df),
                file_name=dl_filename("branch", "csv"),
                mime="text/csv",
                use_container_width=True)
        with dl4:
            st.download_button(
                f"⬇️ {t('Branch Excel','Excel الفروع')}",
                data=to_excel_arabic(branch_df),
                file_name=dl_filename("branch", "xlsx"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.authenticated:
    show_login()
else:
    show_dashboard()
