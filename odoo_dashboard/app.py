# ╔══════════════════════════════════════════════════════════════════╗
# ║  🏢 SWAG Dashboard  –  3-Odoo Live Stock Compare                ║
# ║  Production-ready · Bilingual EN/AR · Dark gold theme           ║
# ╚══════════════════════════════════════════════════════════════════╝

import streamlit as st

# ── Page config (must be first Streamlit call) ────────────────────────────────
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

# ─────────────────────────────────────────────────────────────────────────────
# 1.  SECRETS  –  loaded via  st.secrets  (never from runtime internals)
# ─────────────────────────────────────────────────────────────────────────────
#
#  Required .streamlit/secrets.toml  (or Streamlit Cloud → App Settings → Secrets)
#
#  [SWAG]
#  name    = "SWAG (Main)"
#  url     = "https://db.swag.com.sa"
#  db      = "db2"
#  user    = "ziad.m@swag.com.sa"
#  api_key = "..."
#
#  [LAROUCHE]
#  name    = "La Rouche"
#  url     = "https://odooprosys-la-rouche.odoo.com"
#  db      = "odooprosys-la-rouche-production-12364313"
#  user    = "operations@swag.com.sa"
#  api_key = "..."
#
#  [DIFFC]
#  name    = "Different Clothes"
#  url     = "https://odooprosys-different-clothes.odoo.com"
#  db      = "odooprosys-different-clothes-production-16906605"
#  user    = "ziad.m@swag.com.sa"
#  api_key = "..."
#
#  [LOGIN]
#  url = "https://db.swag.com.sa"
#  db  = "db2"

secrets = st.secrets  # ← single canonical alias; never import from runtime

# ─────────────────────────────────────────────────────────────────────────────
# 2.  DARK GOLD THEME CSS
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=DM+Sans:wght@300;400;500&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    color: #e8dcc8;
}
.stApp { background: #0c0c0c; }
.block-container { padding-top: 1.4rem; padding-bottom: 2rem; }

/* ── Typography ── */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Cormorant Garamond', serif;
    color: #c9a84c;
    letter-spacing: .04em;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #111111;
    border-right: 1px solid #2a2a2a;
}
section[data-testid="stSidebar"] * { color: #e8dcc8 !important; }

/* ── Inputs ── */
input, textarea {
    background: #1a1a1a !important;
    color: #e8dcc8 !important;
    border-color: #3a3020 !important;
    border-radius: 8px !important;
}
input::placeholder, textarea::placeholder { color: #5a5040 !important; }

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #c9a84c, #9a7430) !important;
    color: #0c0c0c !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: filter .2s !important;
}
.stButton > button:hover { filter: brightness(1.12) !important; }

/* ── Download button ── */
.stDownloadButton > button {
    background: #1e1e1e !important;
    color: #c9a84c !important;
    border: 1px solid #3a3020 !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}
.stDownloadButton > button:hover {
    background: #2a2a1a !important;
    border-color: #c9a84c !important;
}

/* ── Metrics ── */
[data-testid="stMetric"] {
    background: #161616;
    border: 1px solid #2e2a1e;
    border-radius: 12px;
    padding: 16px 20px;
}
[data-testid="stMetricLabel"] { color: #9a8c70 !important; font-size: .78rem !important; }
[data-testid="stMetricValue"] {
    font-family: 'Cormorant Garamond', serif !important;
    color: #c9a84c !important;
    font-size: 1.65rem !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border-radius: 10px;
    border: 1px solid #252525 !important;
}

/* ── Divider ── */
hr { border-color: #2a2a2a !important; }

/* ── Info / Warning / Error ── */
[data-testid="stAlert"] {
    background: #161616 !important;
    border-left-color: #c9a84c !important;
    color: #e8dcc8 !important;
    border-radius: 8px !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { gap: .5rem; }
.stTabs [data-baseweb="tab"] {
    background: #1a1a1a;
    border-radius: 999px;
    padding: 6px 16px;
    border: 1px solid #2e2a1e;
    color: #9a8c70;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #c9a84c, #9a7430);
    color: #0c0c0c;
    border-color: transparent;
    font-weight: 600;
}

/* ── Segmented control ── */
[data-testid="stSegmentedControl"] button {
    background: #1a1a1a !important;
    color: #9a8c70 !important;
    border: 1px solid #2e2a1e !important;
}
[data-testid="stSegmentedControl"] button[aria-checked="true"] {
    background: linear-gradient(135deg, #c9a84c, #9a7430) !important;
    color: #0c0c0c !important;
    font-weight: 600 !important;
}

/* ── Toggle ── */
.stToggle > label > div[data-testid="stToggle"] { background-color: #3a3020 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# 3.  LANGUAGE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

if "lang" not in st.session_state:
    st.session_state["lang"] = "EN"


def t(en: str, ar: str) -> str:
    """Return English or Arabic string based on current language setting."""
    return ar if st.session_state["lang"] == "AR" else en


# ─────────────────────────────────────────────────────────────────────────────
# 4.  SESSION STATE INITIALISATION
# ─────────────────────────────────────────────────────────────────────────────

for _k in ("uid", "password", "email"):
    if _k not in st.session_state:
        st.session_state[_k] = None

# ─────────────────────────────────────────────────────────────────────────────
# 5.  SECRETS VALIDATION  (runs before any page renders)
# ─────────────────────────────────────────────────────────────────────────────

_REQUIRED_SECRETS = {
    "LOGIN":    ["url", "db"],
    "SWAG":     ["name", "url", "db", "user", "api_key"],
    "LAROUCHE": ["name", "url", "db", "user", "api_key"],
    "DIFFC":    ["name", "url", "db", "user", "api_key"],
}


def _validate_secrets() -> bool:
    """Return True if all required secrets are present; show error + stop otherwise."""
    missing = []
    for section, keys in _REQUIRED_SECRETS.items():
        if section not in secrets:
            missing.append(f"[{section}]  ← entire section missing")
        else:
            for k in keys:
                if k not in secrets[section]:
                    missing.append(f"[{section}] → {k}")
    if not missing:
        return True

    st.error("**🔐 Secrets not configured.** Fill `.streamlit/secrets.toml` or Streamlit Cloud → App Settings → Secrets.")
    st.markdown("**Missing:**\n" + "\n".join(f"- `{m}`" for m in missing))
    st.code("""# .streamlit/secrets.toml

[LOGIN]
url = "https://db.swag.com.sa"
db  = "db2"

[SWAG]
name    = "SWAG (Main)"
url     = "https://db.swag.com.sa"
db      = "db2"
user    = "ziad.m@swag.com.sa"
api_key = "your_key_here"

[LAROUCHE]
name    = "La Rouche"
url     = "https://odooprosys-la-rouche.odoo.com"
db      = "odooprosys-la-rouche-production-12364313"
user    = "operations@swag.com.sa"
api_key = "your_key_here"

[DIFFC]
name    = "Different Clothes"
url     = "https://odooprosys-different-clothes.odoo.com"
db      = "odooprosys-different-clothes-production-16906605"
user    = "ziad.m@swag.com.sa"
api_key = "your_key_here"
""", language="toml")
    st.stop()


_validate_secrets()

# ─────────────────────────────────────────────────────────────────────────────
# 6.  ODOO SYSTEM CONFIGS  (built from secrets after validation)
# ─────────────────────────────────────────────────────────────────────────────

ODOO_SYSTEMS: dict[str, dict] = {
    "SWAG": {
        "name":    secrets["SWAG"]["name"],
        "url":     secrets["SWAG"]["url"],
        "db":      secrets["SWAG"]["db"],
        "user":    secrets["SWAG"]["user"],
        "api_key": secrets["SWAG"]["api_key"],
    },
    "LAROUCHE": {
        "name":    secrets["LAROUCHE"]["name"],
        "url":     secrets["LAROUCHE"]["url"],
        "db":      secrets["LAROUCHE"]["db"],
        "user":    secrets["LAROUCHE"]["user"],
        "api_key": secrets["LAROUCHE"]["api_key"],
    },
    "DIFFC": {
        "name":    secrets["DIFFC"]["name"],
        "url":     secrets["DIFFC"]["url"],
        "db":      secrets["DIFFC"]["db"],
        "user":    secrets["DIFFC"]["user"],
        "api_key": secrets["DIFFC"]["api_key"],
    },
}

_LOGIN_URL: str = secrets["LOGIN"]["url"]
_LOGIN_DB:  str = secrets["LOGIN"]["db"]

# ─────────────────────────────────────────────────────────────────────────────
# 7.  ODOO JSON-RPC LAYER
# ─────────────────────────────────────────────────────────────────────────────


def _rpc_call(url: str, payload: dict, timeout: int = 30) -> dict:
    """Execute a single JSON-RPC call and return the result dict."""
    try:
        r = requests.post(f"{url}/jsonrpc", json=payload, timeout=timeout)
        r.raise_for_status()
    except requests.exceptions.Timeout:
        raise ConnectionError(t(
            f"Request timed out after {timeout}s.",
            f"انتهت مهلة الطلب بعد {timeout} ثانية.",
        ))
    except requests.exceptions.ConnectionError:
        raise ConnectionError(t(
            "Cannot reach the Odoo server. Check the URL.",
            "لا يمكن الوصول إلى خادم أودو. تحقق من الرابط.",
        ))
    res = r.json()
    if "error" in res:
        msg = res["error"].get("data", {}).get("message", str(res["error"]))
        raise RuntimeError(msg)
    return res.get("result")


def odoo_authenticate(url: str, db: str, user: str, password: str) -> int:
    """Return UID on success, raise on failure."""
    uid = _rpc_call(url, {
        "jsonrpc": "2.0", "method": "call",
        "params": {"service": "common", "method": "authenticate",
                   "args": [db, user, password, {}]},
    })
    if not uid:
        raise PermissionError(t(
            "Authentication failed – wrong email or password.",
            "فشل التحقق – بريد إلكتروني أو كلمة مرور خاطئة.",
        ))
    return int(uid)


def odoo_search_read(
    url: str, db: str, uid: int, apikey: str,
    model: str, domain: list, fields: list, limit: int = 500,
) -> list:
    return _rpc_call(url, {
        "jsonrpc": "2.0", "method": "call",
        "params": {
            "service": "object", "method": "execute_kw",
            "args": [db, uid, apikey, model, "search_read", [domain],
                     {"fields": fields, "limit": limit}],
        },
    }, timeout=60) or []


def _sys_auth(key: str) -> tuple[str, str, int, str]:
    """Authenticate against a system from ODOO_SYSTEMS; return (url, db, uid, apikey)."""
    conf = ODOO_SYSTEMS[key]
    url, db, user, apikey = (
        conf["url"].rstrip("/"), conf["db"], conf["user"], conf["api_key"]
    )
    uid = odoo_authenticate(url, db, user, apikey)
    return url, db, uid, apikey


# ─────────────────────────────────────────────────────────────────────────────
# 8.  LOGIN  (uses LOGIN section from secrets)
# ─────────────────────────────────────────────────────────────────────────────


def do_login(email: str, password: str) -> int:
    return odoo_authenticate(_LOGIN_URL.rstrip("/"), _LOGIN_DB, email, password)


# ─────────────────────────────────────────────────────────────────────────────
# 9.  COMPARE BUSINESS LOGIC
# ─────────────────────────────────────────────────────────────────────────────


def _branch_code(loc: str) -> str:
    if isinstance(loc, str) and loc.strip():
        return loc.split("/")[0].strip() if "/" in loc else loc.strip()
    return "Unknown"


def fetch_total_stock(model_code: str) -> pd.DataFrame:
    """Return one row per Odoo system with total on-hand qty."""
    rows = []
    for key, conf in ODOO_SYSTEMS.items():
        name = conf["name"]
        try:
            url, db, uid, apikey = _sys_auth(key)
            recs = odoo_search_read(
                url, db, uid, apikey,
                "product.product",
                [["default_code", "=", model_code]],
                ["id", "display_name", "default_code", "qty_available"],
            )
            if recs:
                r = recs[0]
                rows.append({
                    t("System", "النظام"):   name,
                    t("Model", "الموديل"):   r.get("default_code") or model_code,
                    t("Product", "المنتج"):  r.get("display_name") or "",
                    t("On Hand", "متوفر"):   float(r.get("qty_available") or 0),
                    "_status": "OK",
                })
            else:
                rows.append({
                    t("System", "النظام"):  name,
                    t("Model", "الموديل"):  model_code,
                    t("Product", "المنتج"): t("(not found)", "(غير موجود)"),
                    t("On Hand", "متوفر"):  0.0,
                    "_status": "NOT_FOUND",
                })
        except Exception as exc:
            rows.append({
                t("System", "النظام"):  name,
                t("Model", "الموديل"):  model_code,
                t("Product", "المنتج"): f"({t('error', 'خطأ')}: {exc})",
                t("On Hand", "متوفر"):  0.0,
                "_status": "ERROR",
            })
    return pd.DataFrame(rows)


def fetch_branch_stock(model_code: str) -> pd.DataFrame:
    """Return stock.quant rows split by branch/location for all 3 systems."""
    rows = []
    for key, conf in ODOO_SYSTEMS.items():
        sys_name = conf["name"]
        try:
            url, db, uid, apikey = _sys_auth(key)

            # Find product IDs matching the default_code
            prods = odoo_search_read(
                url, db, uid, apikey,
                "product.product",
                [["default_code", "=", model_code]],
                ["id", "display_name"],
                limit=50,
            )
            if not prods:
                continue

            prod_ids  = [p["id"] for p in prods]
            prod_name = prods[0].get("display_name") or ""

            # Pull stock quants for internal locations
            quants = _rpc_call(url, {
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
            }, timeout=60) or []

            for q in quants:
                loc = q.get("location_id")
                loc_name = loc[1] if isinstance(loc, (list, tuple)) and len(loc) >= 2 else ""
                rows.append({
                    t("System", "النظام"):       sys_name,
                    t("Model", "الموديل"):        model_code,
                    t("Product", "المنتج"):       prod_name,
                    t("Location", "الموقع"):      loc_name,
                    t("Branch", "الفرع"):         _branch_code(loc_name),
                    t("On Hand", "متوفر"):        float(q.get("quantity") or 0),
                })
        except Exception:
            continue

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# 10.  DOWNLOAD HELPERS  (UTF-8-BOM for Excel/Arabic compatibility)
# ─────────────────────────────────────────────────────────────────────────────


def df_to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def df_to_excel(sheets: dict[str, pd.DataFrame]) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        for sheet_name, df in sheets.items():
            df.to_excel(w, sheet_name=sheet_name[:31], index=False)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# 11.  LOGIN PAGE
# ─────────────────────────────────────────────────────────────────────────────


def render_login():
    # Sidebar: language only
    with st.sidebar:
        st.markdown(f"### {t('Language', 'اللغة')}")
        if st.toggle("🇸🇦 العربية", value=(st.session_state["lang"] == "AR"),
                     key="lang_toggle_login"):
            st.session_state["lang"] = "AR"
        else:
            st.session_state["lang"] = "EN"

    # Centre the login card
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.05, 1])
    with mid:
        st.markdown(
            f"<h1 style='text-align:center;margin-bottom:4px'>"
            f"🏢 {t('SWAG Dashboard', 'لوحة سواغ')}</h1>"
            f"<p style='text-align:center;color:#7a7060;font-size:.88rem;"
            f"letter-spacing:.1em;margin-bottom:28px'>"
            f"{t('LIVE ODOO INSIGHTS', 'تحليلات أودو مباشرة')}</p>",
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown(f"#### {t('Sign In', 'تسجيل الدخول')}")
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
                        "Email and password are required.",
                        "البريد الإلكتروني وكلمة المرور مطلوبان.",
                    ))
                else:
                    with st.spinner(t("Authenticating…", "جارٍ التحقق…")):
                        try:
                            uid = do_login(email, password)
                            st.session_state["uid"]      = uid
                            st.session_state["password"] = password
                            st.session_state["email"]    = email
                            st.rerun()
                        except (PermissionError, ConnectionError, RuntimeError) as exc:
                            st.error(str(exc))
                        except Exception as exc:
                            st.error(t(
                                f"Unexpected error: {exc}",
                                f"خطأ غير متوقع: {exc}",
                            ))

        st.caption(t(
            "Use your Odoo account email and password.",
            "استخدم بريدك الإلكتروني وكلمة مرور حساب أودو.",
        ))


# ─────────────────────────────────────────────────────────────────────────────
# 12.  MAIN DASHBOARD  (3-Odoo Stock Compare – single page, no nav)
# ─────────────────────────────────────────────────────────────────────────────


def render_dashboard():
    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"### {t('Language', 'اللغة')}")
        if st.toggle("🇸🇦 العربية", value=(st.session_state["lang"] == "AR"),
                     key="lang_toggle_dash"):
            st.session_state["lang"] = "AR"
        else:
            st.session_state["lang"] = "EN"

        st.divider()
        st.markdown("**🏢 SWAG Dashboard**")
        st.caption(f"👤 {st.session_state['email']}")
        st.divider()

        if st.button(t("🚪 Logout", "🚪 تسجيل الخروج"), use_container_width=True):
            for k in ("uid", "password", "email", "last_meta"):
                st.session_state[k] = None
            st.rerun()

    # ── Page header ──────────────────────────────────────────────────────────
    st.markdown(
        f"<h1 style='margin-bottom:2px'>🔁 "
        f"{t('3‑Odoo Live Stock Compare', 'مقارنة المخزون الحي لثلاثة أودو')}"
        f"</h1>"
        f"<p style='color:#9a8c70;font-size:.88rem;margin-top:0'>"
        f"{t('SWAG · La Rouche · Different Clothes — real‑time stock per model code','سواغ · لا روش · ديفرنت كلوز — مخزون الموديل في الوقت الفعلي')}"
        f"</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Controls + Snapshot layout ────────────────────────────────────────────
    ctrl_col, snap_col = st.columns([1.8, 1], gap="large")

    with ctrl_col:
        # Mode selector
        single_lbl = t("Single model", "موديل واحد")
        multi_lbl  = t("Multiple models", "عدة موديلات")
        mode = st.segmented_control(
            t("Query mode", "وضع الاستعلام"),
            options=[single_lbl, multi_lbl],
            default=single_lbl,
        )

        if mode == multi_lbl:
            raw = st.text_area(
                t("Default codes – one per line", "أكواد الموديلات – كود في كل سطر"),
                placeholder="MM0579\nRVT196\nAB1234",
                height=120,
            )
            models = [m.strip().upper() for m in raw.splitlines() if m.strip()]
        else:
            raw = st.text_input(
                t("Default code", "كود الموديل"),
                placeholder=t("e.g. RVT196", "مثال: RVT196"),
            )
            models = [raw.strip().upper()] if raw.strip() else []

        st.caption(t(
            "ℹ️  Use the Internal Reference (default_code), not the product name.",
            "ℹ️  استخدم الرمز الداخلي (default_code) وليس اسم المنتج.",
        ))

        # Options row
        o1, o2, o3 = st.columns(3)
        show_zero      = o1.toggle(t("Show zero",      "عرض الصفر"),        value=True)
        show_branch    = o2.toggle(t("Branch detail",  "تفاصيل الفروع"),    value=True)
        sort_by_system = o3.toggle(t("Sort by system", "ترتيب حسب النظام"), value=True)

        run = st.button(
            t("🚀  Compare across 3 Odoo", "🚀  مقارنة عبر 3 أودو"),
            type="primary",
            use_container_width=True,
        )

    # ── Snapshot card (right column) ─────────────────────────────────────────
    with snap_col:
        with st.container(border=True):
            st.markdown(
                f"**📊 {t('Last run snapshot', 'ملخص آخر تشغيل')}**"
            )
            meta = st.session_state.get("last_meta")
            if meta:
                m1, m2 = st.columns(2)
                m1.metric(t("Models", "الموديلات"), meta["models"])
                m2.metric(t("Systems OK", "أنظمة متصلة"), f"{meta['ok']}/3")
                st.divider()

                def _status_badge(s: str) -> str:
                    return "🟢 OK" if s == "OK" else ("🔴 OFF" if s == "OFF" else "⚪ N/A")

                st.markdown(
                    f"**SWAG:** {_status_badge(meta.get('swag','N/A'))}  \n"
                    f"**La Rouche:** {_status_badge(meta.get('lr','N/A'))}  \n"
                    f"**Diff. Clothes:** {_status_badge(meta.get('dc','N/A'))}"
                )
            else:
                st.caption(t(
                    "Run a comparison to see the snapshot.",
                    "شغّل مقارنة لرؤية الملخص.",
                ))

    # ── Guard ────────────────────────────────────────────────────────────────
    if not run:
        return
    if not models:
        st.warning(t(
            "Enter at least one default code.",
            "أدخل كود موديل واحد على الأقل.",
        ))
        return

    # ── Fetch total stock ─────────────────────────────────────────────────────
    st.divider()
    with st.spinner(t(
        "⏳  Fetching live stock from 3 Odoo instances…",
        "⏳  جلب المخزون الحي من 3 أودو…",
    )):
        frames = []
        statuses = {"swag": "N/A", "lr": "N/A", "dc": "N/A"}

        for code in models:
            df = fetch_total_stock(code)
            # Derive per-system status
            name_map = {
                "swag": ODOO_SYSTEMS["SWAG"]["name"],
                "lr":   ODOO_SYSTEMS["LAROUCHE"]["name"],
                "dc":   ODOO_SYSTEMS["DIFFC"]["name"],
            }
            sys_col = t("System", "النظام")
            for skey, sname in name_map.items():
                row = df[df[sys_col] == sname]
                if not row.empty:
                    statuses[skey] = row.iloc[0].get("_status", "N/A")
                    statuses[skey] = "OK" if statuses[skey] == "OK" else "OFF"

            # Drop internal status column before display
            df = df.drop(columns=["_status"], errors="ignore")
            if not show_zero:
                df = df[df[t("On Hand", "متوفر")] != 0]
            df.insert(0, t("Query", "الاستعلام"), code)
            frames.append(df)

    if not frames or all(f.empty for f in frames):
        st.info(t(
            "No data returned. Check the model codes and try again.",
            "لا توجد بيانات. تحقق من الأكواد وحاول مجدداً.",
        ))
        return

    df_all = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    if sort_by_system:
        df_all = df_all.sort_values(
            [t("Query", "الاستعلام"), t("System", "النظام")]
        )

    # Save snapshot meta
    ok_count = sum(1 for v in statuses.values() if v == "OK")
    st.session_state["last_meta"] = {
        "models": len(models),
        "ok":     ok_count,
        **statuses,
    }

    # ── KPI metrics ──────────────────────────────────────────────────────────
    st.subheader("🔢 " + t("On-Hand Summary", "ملخص المتوفر"))
    qty_col = t("On Hand", "متوفر")
    sys_col = t("System", "النظام")

    totals = df_all.groupby(sys_col)[qty_col].sum()
    kpi_cols = st.columns(len(ODOO_SYSTEMS))
    for i, (key, conf) in enumerate(ODOO_SYSTEMS.items()):
        name = conf["name"]
        val  = totals.get(name, 0)
        kpi_cols[i].metric(label=name, value=f"{val:,.0f} {t('pcs','قطعة')}")

    # ── Total table ───────────────────────────────────────────────────────────
    st.subheader("📋 " + t("Detailed Results", "النتائج التفصيلية"))
    st.dataframe(
        df_all,
        width="stretch",
        hide_index=True,
        column_config={qty_col: st.column_config.NumberColumn(qty_col, format="%d")},
    )

    dl1, dl2 = st.columns(2)
    dl1.download_button(
        t("⬇️ CSV (total)", "⬇️ CSV (إجمالي)"),
        df_to_csv(df_all),
        file_name="3odoo_total.csv",
        mime="text/csv",
    )
    dl2.download_button(
        t("⬇️ Excel (total)", "⬇️ Excel (إجمالي)"),
        df_to_excel({t("Total", "إجمالي"): df_all}),
        file_name="3odoo_total.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # ── Branch detail ─────────────────────────────────────────────────────────
    if not show_branch:
        return

    st.divider()
    st.subheader("🏬 " + t(
        "Branch-wise Stock (all 3 systems)",
        "المخزون حسب الفرع (الأنظمة الثلاثة)",
    ))
    st.caption(t(
        "Reads stock.quant from all internal locations.",
        "يقرأ stock.quant من جميع المواقع الداخلية.",
    ))

    with st.spinner(t("⏳  Fetching branch quants…", "⏳  جلب بيانات الفروع…")):
        branch_frames = []
        for code in models:
            df_b = fetch_branch_stock(code)
            if not df_b.empty:
                df_b.insert(0, t("Query", "الاستعلام"), code)
                branch_frames.append(df_b)

    if not branch_frames:
        st.info(t("No branch data found.", "لا توجد بيانات حسب الفروع."))
        return

    df_branch = pd.concat(branch_frames, ignore_index=True)
    df_branch = df_branch.sort_values(
        [t("Query", "الاستعلام"), t("System", "النظام"),
         t("Branch", "الفرع"), t("Location", "الموقع")]
    )

    # Bar chart: branch qty per system
    branch_col = t("Branch", "الفرع")
    agg = (
        df_branch.groupby([sys_col, branch_col], as_index=False)[qty_col]
        .sum()
        .sort_values(qty_col, ascending=False)
    )
    fig = px.bar(
        agg, x=branch_col, y=qty_col, color=sys_col,
        barmode="group",
        title=t(
            "On-Hand Qty by Branch & System",
            "الكمية المتوفرة حسب الفرع والنظام",
        ),
        color_discrete_sequence=["#c9a84c", "#7a5c1e", "#e8c97a"],
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e8dcc8"),
        xaxis_tickangle=-35,
        legend=dict(orientation="h", yanchor="bottom", y=-0.35),
    )
    st.plotly_chart(fig, width="stretch")

    # Branch table
    st.dataframe(
        df_branch,
        width="stretch",
        hide_index=True,
        column_config={qty_col: st.column_config.NumberColumn(qty_col, format="%d")},
    )

    db1, db2 = st.columns(2)
    db1.download_button(
        t("⬇️ CSV (branches)", "⬇️ CSV (فروع)"),
        df_to_csv(df_branch),
        file_name="3odoo_branches.csv",
        mime="text/csv",
    )
    db2.download_button(
        t("⬇️ Excel (branches)", "⬇️ Excel (فروع)"),
        df_to_excel({
            t("Total", "إجمالي"):   df_all,
            t("Branches", "فروع"):  df_branch,
        }),
        file_name="3odoo_branches.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 13.  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if st.session_state.get("uid") is None:
    render_login()
else:
    render_dashboard()
