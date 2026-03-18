# import streamlit as st

import streamlit as st

st.set_page_config(
    page_title="SWAG Dashboard",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"Get help": None, "Report a bug": None, "About": None},
)

import requests
import pandas as pd
import plotly.express as px
from io import BytesIO
from datetime import datetime, timedelta
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import plotly.io as pio

# ─────────────────────────────────────────────────────────────────────────────
# LOAD SECRETS
# ─────────────────────────────────────────────────────────────────────────────
from streamlit.runtime.secrets import secrets

ODOO_URL = "https://db.swag.com.sa"
ODOO_DB = "db2"
BATCH = 1_000
INV_TTL = 600
SALES_TTL = 300

# 3 Odoo configs – loaded from Streamlit secrets (NO HARDCODED CREDENTIALS)
ODOO_SYSTEMS = {
    "SWAG": {
        "name": secrets["SWAG"]["name"],
        "url": secrets["SWAG"]["url"],
        "db": secrets["SWAG"]["db"],
        "user": secrets["SWAG"]["user"],
        "api_key": secrets["SWAG"]["api_key"],
    },
    "LAROUCHE": {
        "name": secrets["LAROUCHE"]["name"],
        "url": secrets["LAROUCHE"]["url"],
        "db": secrets["LAROUCHE"]["db"],
        "user": secrets["LAROUCHE"]["user"],
        "api_key": secrets["LAROUCHE"]["api_key"],
    },
    "DIFFC": {
        "name": secrets["DIFFC"]["name"],
        "url": secrets["DIFFC"]["url"],
        "db": secrets["DIFFC"]["db"],
        "user": secrets["DIFFC"]["user"],
        "api_key": secrets["DIFFC"]["api_key"],
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS  –  fonts + light card styling only; Streamlit white theme used
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(
    """
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}
h1, h2, h3, h4 {
    font-family: 'Cormorant Garamond', serif;
    letter-spacing: .03em;
}

/* ── Snapshot card ── */
.snapshot-card {
    background: #f8f9fb;
    border: 1px solid #e2e6ea;
    border-radius: 12px;
    padding: 18px 20px;
}
.snapshot-card h5 {
    font-family: 'Cormorant Garamond', serif;
    margin: 0 0 10px 0;
    font-size: 1.1rem;
    color: #1a1a2e;
}

/* ── Login card ── */
.login-card {
    background: #ffffff;
    border: 1px solid #e2e6ea;
    border-radius: 16px;
    padding: 28px 30px;
    box-shadow: 0 2px 12px rgba(0,0,0,.06);
}
</style>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# LANGUAGE SUPPORT
# ─────────────────────────────────────────────────────────────────────────────

if "lang" not in st.session_state:
    st.session_state["lang"] = "EN"


def set_lang(lang_code: str):
    st.session_state["lang"] = lang_code


def get_lang() -> str:
    return st.session_state.get("lang", "EN")


def t(en: str, ar: str) -> str:
    """Return the correct string for the active language."""
    return ar if get_lang() == "AR" else en


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────

for _k in ("uid", "password", "email"):
    if _k not in st.session_state:
        st.session_state[_k] = None

# ─────────────────────────────────────────────────────────────────────────────
# SECRETS LOADER
# Globals are empty at import time; _load_secrets() fills them at the entry
# point AFTER Streamlit is fully initialised, so a missing key never causes a
# raw crash – the user sees a clear setup guide instead.
# ─────────────────────────────────────────────────────────────────────────────

ODOO_SYSTEMS: dict = {}
_LOGIN_URL:   str  = ""
_LOGIN_DB:    str  = ""


def _load_secrets() -> tuple:
    """
    Load all Odoo credentials from Streamlit secrets at runtime.

    Required .streamlit/secrets.toml layout
    ────────────────────────────────────────
    [LOGIN]
    url = "https://db.swag.com.sa"
    db  = "db2"

    [SWAG]
    name    = "SWAG (Main)"
    url     = "https://db.swag.com.sa"
    db      = "db2"
    user    = "you@swag.com.sa"
    api_key = "your_api_key_here"

    [LAROUCHE]
    name    = "La Rouche"
    url     = "https://odooprosys-la-rouche.odoo.com"
    db      = "odooprosys-la-rouche-production-XXXXX"
    user    = "you@swag.com.sa"
    api_key = "your_api_key_here"

    [DIFFC]
    name    = "Different Clothes"
    url     = "https://odooprosys-different-clothes.odoo.com"
    db      = "odooprosys-different-clothes-production-XXXXX"
    user    = "you@swag.com.sa"
    api_key = "your_api_key_here"
    """
    _REQUIRED = {
        "LOGIN":    ["url", "db"],
        "SWAG":     ["name", "url", "db", "user", "api_key"],
        "LAROUCHE": ["name", "url", "db", "user", "api_key"],
        "DIFFC":    ["name", "url", "db", "user", "api_key"],
    }

    # ── Validate ──────────────────────────────────────────────────────────────
    missing = []
    for section, keys in _REQUIRED.items():
        if section not in st.secrets:
            missing.append(f"[{section}]  ← entire section missing")
        else:
            for k in keys:
                if k not in st.secrets[section]:
                    missing.append(f"[{section}] → {k}")

    if missing:
        st.error(
            "**🔐 Secrets not configured.** "
            "Add the missing keys to `.streamlit/secrets.toml` (local) "
            "or **App Settings → Secrets** (Streamlit Cloud)."
        )
        st.markdown("**Missing keys:**")
        for m in missing:
            st.markdown(f"- `{m}`")
        st.code(
            """# .streamlit/secrets.toml

[LOGIN]
url = "https://db.swag.com.sa"
db  = "db2"

[SWAG]
name    = "SWAG (Main)"
url     = "https://db.swag.com.sa"
db      = "db2"
user    = "you@swag.com.sa"
api_key = "your_api_key_here"

[LAROUCHE]
name    = "La Rouche"
url     = "https://odooprosys-la-rouche.odoo.com"
db      = "odooprosys-la-rouche-production-XXXXX"
user    = "you@swag.com.sa"
api_key = "your_api_key_here"

[DIFFC]
name    = "Different Clothes"
url     = "https://odooprosys-different-clothes.odoo.com"
db      = "odooprosys-different-clothes-production-XXXXX"
user    = "you@swag.com.sa"
api_key = "your_api_key_here"
""",
            language="toml",
        )
        st.stop()

    # ── Build ODOO_SYSTEMS from st.secrets ───────────────────────────────────
    odoo_systems = {
        "SWAG": {
            "name":    st.secrets["SWAG"]["name"],
            "url":     st.secrets["SWAG"]["url"],
            "db":      st.secrets["SWAG"]["db"],
            "user":    st.secrets["SWAG"]["user"],
            "api_key": st.secrets["SWAG"]["api_key"],
        },
        "LAROUCHE": {
            "name":    st.secrets["LAROUCHE"]["name"],
            "url":     st.secrets["LAROUCHE"]["url"],
            "db":      st.secrets["LAROUCHE"]["db"],
            "user":    st.secrets["LAROUCHE"]["user"],
            "api_key": st.secrets["LAROUCHE"]["api_key"],
        },
        "DIFFC": {
            "name":    st.secrets["DIFFC"]["name"],
            "url":     st.secrets["DIFFC"]["url"],
            "db":      st.secrets["DIFFC"]["db"],
            "user":    st.secrets["DIFFC"]["user"],
            "api_key": st.secrets["DIFFC"]["api_key"],
        },
    }
    login_url = st.secrets["LOGIN"]["url"]
    login_db  = st.secrets["LOGIN"]["db"]
    return odoo_systems, login_url, login_db


# ─────────────────────────────────────────────────────────────────────────────
# ODOO JSON‑RPC HELPERS
# ─────────────────────────────────────────────────────────────────────────────


def odoo_login(email: str, password: str) -> int:
    """Authenticate against the LOGIN Odoo instance using email + password."""
    payload = {
        "jsonrpc": "2.0",
        "method":  "call",
        "params": {
            "service": "common",
            "method":  "authenticate",
            "args":    [_LOGIN_DB, email, password, {}],
        },
    }
    r   = requests.post(f"{_LOGIN_URL}/jsonrpc", json=payload, timeout=30)
    res = r.json()
    if "error" in res:
        raise Exception(res["error"].get("data", {}).get("message", str(res["error"])))
    uid = res.get("result")
    if not uid:
        raise Exception(t(
            "Login failed – check your email and password.",
            "فشل تسجيل الدخول – تأكد من البريد الإلكتروني وكلمة المرور.",
        ))
    return uid


def _jsonrpc_auth(sys_name: str, conf: dict) -> tuple:
    url    = conf["url"].rstrip("/")
    db     = conf["db"]
    user   = conf["user"]
    apikey = conf["api_key"]
    payload = {
        "jsonrpc": "2.0", "method": "call",
        "params": {
            "service": "common", "method": "authenticate",
            "args": [db, user, apikey, {}],
        },
    }
    r   = requests.post(f"{url}/jsonrpc", json=payload, timeout=30)
    res = r.json()
    if "error" in res:
        raise Exception(f"{sys_name} auth failed: {res['error']}")
    uid = res.get("result")
    if not uid:
        raise Exception(f"{sys_name} auth failed (uid=False)")
    return url, db, uid, apikey


def _jsonrpc_search_read(sys_name, conf, model, domain, fields, limit=500):
    url, db, uid, apikey = _jsonrpc_auth(sys_name, conf)
    payload = {
        "jsonrpc": "2.0", "method": "call",
        "params": {
            "service": "object", "method": "execute_kw",
            "args": [
                db, uid, apikey, model, "search_read", [domain],
                {"fields": fields, "limit": limit},
            ],
        },
    }
    r   = requests.post(f"{url}/jsonrpc", json=payload, timeout=60)
    res = r.json()
    if "error" in res:
        raise Exception(res["error"].get("data", {}).get("message", str(res["error"])))
    return res["result"]


# ─────────────────────────────────────────────────────────────────────────────
# COMPARE LOGIC
# ─────────────────────────────────────────────────────────────────────────────


def get_branch_code(loc: str) -> str:
    if isinstance(loc, str) and loc.strip():
        return loc.split("/")[0].strip() if "/" in loc else loc.strip()
    return "Unknown"


def compare_model_across_odoos(model_code: str) -> pd.DataFrame:
    rows = []
    for key, conf in ODOO_SYSTEMS.items():
        name = conf["name"]
        try:
            recs = _jsonrpc_search_read(
                name, conf, "product.product",
                [["default_code", "=", model_code]],
                ["id", "display_name", "default_code", "qty_available"],
            )
            if recs:
                r = recs[0]
                rows.append({
                    "System":  name,
                    "Model":   r.get("default_code") or model_code,
                    "Product": r.get("display_name") or "",
                    "Qty":     float(r.get("qty_available") or 0.0),
                })
            else:
                rows.append({"System": name, "Model": model_code,
                             "Product": "(not found)", "Qty": 0.0})
        except Exception:
            rows.append({"System": name, "Model": model_code,
                         "Product": "(not connected)", "Qty": 0.0})
    return pd.DataFrame(rows)


def branch_stock_for_model_across_odoos(model_code: str) -> pd.DataFrame:
    rows = []
    for key, conf in ODOO_SYSTEMS.items():
        sys_name = conf["name"]
        try:
            prods = _jsonrpc_search_read(
                sys_name, conf, "product.product",
                [["default_code", "=", model_code]],
                ["id", "display_name", "default_code"],
                limit=50,
            )
            if not prods:
                continue
            prod_ids  = [p["id"] for p in prods]
            prod_name = prods[0].get("display_name") or ""
            url, db, uid, apikey = _jsonrpc_auth(sys_name, conf)
            payload = {
                "jsonrpc": "2.0", "method": "call",
                "params": {
                    "service": "object", "method": "execute_kw",
                    "args": [
                        db, uid, apikey, "stock.quant", "search_read",
                        [[["product_id", "in", prod_ids],
                          ["location_id.usage", "=", "internal"]]],
                        {"fields": ["product_id", "location_id", "quantity"],
                         "limit": 2000},
                    ],
                },
            }
            r   = requests.post(f"{url}/jsonrpc", json=payload, timeout=60)
            res = r.json()
            if "error" in res:
                raise Exception(
                    res["error"].get("data", {}).get("message", str(res["error"]))
                )
            for q in res["result"]:
                loc      = q.get("location_id")
                loc_name = loc[1] if isinstance(loc, (list, tuple)) and len(loc) >= 2 else ""
                rows.append({
                    "System":       sys_name,
                    "Model":        model_code,
                    "Product":      prod_name,
                    "LocationName": loc_name,
                    "BranchCode":   get_branch_code(loc_name),
                    "Qty":          float(q.get("quantity") or 0.0),
                })
        except Exception:
            continue
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: 3‑ODOO STOCK COMPARE
# ─────────────────────────────────────────────────────────────────────────────


def _qty_col(label=None):
    return st.column_config.NumberColumn(label or t("Qty", "الكمية"), format="%d")


def page_multi_odoo_compare():
    st.title("🔁 " + t("3‑Odoo Live Stock Compare", "مقارنة المخزون الحي لثلاثة أودو"))
    st.caption(t(
        "SWAG · La Rouche · Different Clothes — real‑time stock per model code",
        "سواغ · لا روش · ديفرنت كلوز — مخزون الموديل في الوقت الفعلي",
    ))
    st.divider()

    col_left, col_right = st.columns([1.7, 1], gap="large")

    # ── Left: query controls ──────────────────────────────────────────────────
    with col_left:
        mode_single = t("Single model", "موديل واحد")
        mode_multi  = t("Multiple models", "عدة موديلات")
        multi_mode  = st.segmented_control(
            t("Mode", "الوضع"),
            options=[mode_single, mode_multi],
            default=mode_single,
        )

        if multi_mode == mode_multi:
            model_input = st.text_area(
                t("Models / Default Codes (one per line)",
                  "الموديلات / الأكواد (كود لكل سطر)"),
                placeholder="MM0579\nRVT196\nAB1234",
                height=130,
            )
            models = [m.strip() for m in model_input.splitlines() if m.strip()]
        else:
            model_input = st.text_input(
                t("Model / Default Code", "الموديل / الكود"),
                placeholder=t("e.g. RVT196", "مثال: RVT196"),
            )
            models = [model_input.strip()] if model_input.strip() else []

        st.caption(t(
            "Tip: use the default code, not the display name.",
            "ملاحظة: استخدم كود الموديل، ليس اسم المنتج.",
        ))

        c1, c2, c3 = st.columns(3)
        show_zero      = c1.toggle(t("Show zero qty",      "عرض الكمية صفر"),    value=True)
        show_branch    = c2.toggle(t("Branch‑wise detail", "تفاصيل حسب الفرع"),  value=True)
        sort_by_system = c3.toggle(t("Sort by system",     "ترتيب حسب النظام"),  value=True)

        run_compare = st.button(
            t("🚀 Compare across 3 Odoo", "🚀 مقارنة عبر 3 أودو"),
            type="primary",
            use_container_width=True,
        )

    # ── Right: snapshot card ──────────────────────────────────────────────────
    with col_right:
        if "last_compare_meta" in st.session_state:
            meta = st.session_state["last_compare_meta"]
            st.markdown(
                f"""
                <div class="snapshot-card">
                  <h5>📊 {t('Snapshot – last run', 'ملخص – آخر تشغيل')}</h5>
                  <table style="width:100%;border-collapse:collapse;font-size:.9rem">
                    <tr>
                      <td style="padding:4px 8px;color:#666">{t('Models checked','الموديلات')}</td>
                      <td style="padding:4px 8px;font-weight:600">{meta.get('models', 0)}</td>
                    </tr>
                    <tr>
                      <td style="padding:4px 8px;color:#666">{t('Systems online','الأنظمة')}</td>
                      <td style="padding:4px 8px;font-weight:600">{meta.get('systems_ok', 0)}/3</td>
                    </tr>
                    <tr>
                      <td style="padding:4px 8px;color:#666">SWAG</td>
                      <td style="padding:4px 8px;font-weight:600;color:{'#16a34a' if meta.get('swag_status')=='OK' else '#dc2626'}">{meta.get('swag_status','?')}</td>
                    </tr>
                    <tr>
                      <td style="padding:4px 8px;color:#666">La Rouche</td>
                      <td style="padding:4px 8px;font-weight:600;color:{'#16a34a' if meta.get('lr_status')=='OK' else '#dc2626'}">{meta.get('lr_status','?')}</td>
                    </tr>
                    <tr>
                      <td style="padding:4px 8px;color:#666">Diff. Clothes</td>
                      <td style="padding:4px 8px;font-weight:600;color:{'#16a34a' if meta.get('dc_status')=='OK' else '#dc2626'}">{meta.get('dc_status','?')}</td>
                    </tr>
                  </table>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="snapshot-card">
                  <h5>📊 {t('Snapshot – last run', 'ملخص – آخر تشغيل')}</h5>
                  <p style="color:#888;font-size:.88rem;margin:0">
                    {t('No comparison run yet.', 'لم يتم تشغيل أي مقارنة بعد.')}
                  </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if not run_compare:
        return

    if not models:
        st.warning(t(
            "Enter at least one model/default code.",
            "أدخل موديل/كود واحد على الأقل.",
        ))
        return

    # ── Fetch totals ──────────────────────────────────────────────────────────
    with st.spinner(t(
        "Fetching live stock from 3 Odoo instances…",
        "جلب المخزون الحي من 3 أودو…",
    )):
        all_rows                          = []
        swag_status = lr_status = dc_status = "N/A"

        for m in models:
            df_one = compare_model_across_odoos(m)

            def _status(sys_name, df=df_one):
                if sys_name in df["System"].values:
                    p = df.loc[df["System"] == sys_name, "Product"].iloc[0]
                    return "OK" if p not in ("(not connected)", "(not found)") else "OFF"
                return "N/A"

            swag_status = _status(ODOO_SYSTEMS["SWAG"]["name"])
            lr_status   = _status(ODOO_SYSTEMS["LAROUCHE"]["name"])
            dc_status   = _status(ODOO_SYSTEMS["DIFFC"]["name"])

            if not show_zero:
                df_one = df_one[df_one["Qty"] != 0]
            df_one.insert(0, "QueryModel", m)
            all_rows.append(df_one)

    df_all = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()

    if df_all.empty:
        st.info(t(
            "No data returned (all quantities zero or model codes not found).",
            "لا توجد بيانات (كل الكميات صفر أو الأكواد غير موجودة).",
        ))
        return

    st.session_state["last_compare_meta"] = {
        "models":      len(models),
        "systems_ok":  int(df_all.loc[
            df_all["Product"] != "(not connected)", "System"
        ].nunique()),
        "swag_status": swag_status,
        "lr_status":   lr_status,
        "dc_status":   dc_status,
    }

    if sort_by_system:
        df_all = df_all.sort_values(["QueryModel", "System"])

    # ── Results table ─────────────────────────────────────────────────────────
    st.subheader("🔢 " + t("Total On‑Hand per System", "إجمالي المتوفر لكل نظام"))
    st.dataframe(
        df_all,
        width="stretch",
        hide_index=True,
        column_config={"Qty": _qty_col(t("On Hand", "متوفر"))},
    )
    st.download_button(
        t("⬇️ Download CSV", "⬇️ تحميل CSV"),
        df_all.to_csv(index=False).encode("utf-8-sig"),
        file_name="3odoo_stock_total.csv",
        mime="text/csv",
    )

    if not show_branch:
        return

    # ── Branch detail ─────────────────────────────────────────────────────────
    st.divider()
    st.subheader("🏬 " + t(
        "Branch‑wise Stock (all 3 systems)",
        "المخزون حسب الفرع (الأنظمة الثلاثة)",
    ))
    st.caption(t(
        "Reads stock.quant from internal locations across all 3 Odoo instances.",
        "يقرأ stock.quant من المواقع الداخلية في الأنظمة الثلاثة.",
    ))

    with st.spinner(t(
        "Fetching branch‑wise quants…",
        "جلب بيانات الكميات حسب الفروع…",
    )):
        all_b = []
        for m in models:
            df_b = branch_stock_for_model_across_odoos(m)
            if not df_b.empty:
                df_b.insert(0, "QueryModel", m)
                all_b.append(df_b)

    if not all_b:
        st.info(t("No branch‑wise data found.", "لا توجد بيانات حسب الفروع."))
        return

    df_branch = pd.concat(all_b, ignore_index=True)
    df_branch = df_branch.sort_values(
        ["QueryModel", "System", "BranchCode", "LocationName"]
    )

    agg = (
        df_branch.groupby(["System", "BranchCode"], as_index=False)["Qty"]
        .sum()
        .sort_values("Qty", ascending=False)
    )
    fig = px.bar(
        agg, x="BranchCode", y="Qty", color="System", barmode="group",
        title=t(
            "On‑Hand Qty by Branch & System",
            "الكمية المتوفرة حسب الفرع والنظام",
        ),
    )
    fig.update_layout(xaxis_tickangle=-35)
    st.plotly_chart(fig, width="stretch")

    st.dataframe(
        df_branch,
        width="stretch",
        hide_index=True,
        column_config={"Qty": _qty_col(t("On Hand", "متوفر"))},
    )
    st.download_button(
        t("⬇️ Download Branch CSV", "⬇️ تحميل CSV الفروع"),
        df_branch.to_csv(index=False).encode("utf-8-sig"),
        file_name="3odoo_stock_branches.csv",
        mime="text/csv",
    )


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN PAGE
# ─────────────────────────────────────────────────────────────────────────────


def login_page():
    with st.sidebar:
        st.markdown("### " + t("Language / اللغة", "اللغة / Language"))
        lang_ar = st.toggle("🇸🇦 العربية", value=(get_lang() == "AR"))
        set_lang("AR" if lang_ar else "EN")

    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown(
            f"<h1 style='text-align:center'>"
            f"🏢 {t('SWAG Dashboard', 'لوحة سواغ')}"
            f"</h1>"
            f"<p style='text-align:center;color:#888;font-size:.9rem;margin-bottom:24px'>"
            f"{t('LIVE ODOO INSIGHTS', 'تحليلات أودو مباشرة')}"
            f"</p>",
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown("#### " + t("Sign In", "تسجيل الدخول"))
            st.markdown("<br>", unsafe_allow_html=True)

            email = st.text_input(
                t("Email", "البريد الإلكتروني"),
                placeholder="you@example.com",
            )
            password = st.text_input(
                t("Password", "كلمة المرور"),
                type="password",
                placeholder=t("Enter your password", "أدخل كلمة المرور"),
            )
            st.markdown("<br>", unsafe_allow_html=True)

            if st.button(
                t("Sign In →", "دخول →"),
                type="primary",
                use_container_width=True,
            ):
                if not email or not password:
                    st.error(t(
                        "Email and Password are required.",
                        "البريد الإلكتروني وكلمة المرور مطلوبان.",
                    ))
                else:
                    with st.spinner(t("Connecting…", "جارٍ الاتصال…")):
                        try:
                            uid = odoo_login(email, password)
                            st.session_state.uid      = uid
                            st.session_state.password = password
                            st.session_state.email    = email
                            st.rerun()
                        except Exception as e:
                            st.error(
                                f"{t('Login failed:', 'فشل تسجيل الدخول:')} {e}"
                            )

        st.caption(t(
            "Use your Odoo account email and password.",
            "استخدم بريدك الإلكتروني وكلمة مرور حساب أودو.",
        ))


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD SHELL
# ─────────────────────────────────────────────────────────────────────────────


def dashboard():
    with st.sidebar:
        st.markdown("### " + t("Language / اللغة", "اللغة / Language"))
        lang_ar = st.toggle("🇸🇦 العربية", value=(get_lang() == "AR"))
        set_lang("AR" if lang_ar else "EN")
        st.divider()

        st.markdown("**🏢 SWAG Dashboard**")
        st.caption(f"👤 {st.session_state.email}")
        st.divider()

        if st.button(t("🚪 Logout", "تسجيل الخروج 🚪"), use_container_width=True):
            for k in ("uid", "password", "email", "last_compare_meta"):
                st.session_state[k] = None
            st.rerun()

    page_multi_odoo_compare()


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# Secrets are loaded here – after Streamlit is initialised – so a missing key
# shows a friendly setup guide instead of a raw crash.
# ─────────────────────────────────────────────────────────────────────────────

ODOO_SYSTEMS, _LOGIN_URL, _LOGIN_DB = _load_secrets()

if st.session_state.get("uid") is None:
    login_page()
else:
    dashboard()
