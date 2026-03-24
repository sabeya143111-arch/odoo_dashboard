# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  🏢 SWAG Dashboard  –  4-Odoo Live Stock Compare                        ║
# ║  Production-ready · Bilingual EN/AR · Dark gold theme                   ║
# ║  SWAG · La Rouche · Different Clothes · Fashion Limits                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝

import streamlit as st

# ── Page config MUST be the first Streamlit call ──────────────────────────────
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
# SECTION 1 · SECRETS
# Use `secrets = st.secrets` — NEVER import from streamlit.runtime.secrets
# ─────────────────────────────────────────────────────────────────────────────

secrets = st.secrets  # single canonical alias throughout this file

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 · THEME  (dark gold, Cormorant Garamond headings, DM Sans body)
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=DM+Sans:wght@300;400;500&display=swap');

/* ── Base ───────────────────────────────────────────────── */
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; color:#e8dcc8; }
.stApp { background:#0c0c0c; }
.block-container { padding-top:1.2rem; padding-bottom:2rem; }

/* ── Typography ─────────────────────────────────────────── */
h1,h2,h3,h4,h5,h6 {
    font-family:'Cormorant Garamond',serif;
    color:#c9a84c; letter-spacing:.04em;
}

/* ── Sidebar ─────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background:#111; border-right:1px solid #2a2a2a;
}
section[data-testid="stSidebar"] * { color:#e8dcc8 !important; }
section[data-testid="stSidebar"] hr { border-color:#2a2a2a !important; }

/* ── Inputs ──────────────────────────────────────────────── */
input, textarea {
    background:#1a1a1a !important; color:#e8dcc8 !important;
    border-color:#3a3020 !important; border-radius:8px !important;
}
input::placeholder,textarea::placeholder { color:#5a5040 !important; }
label { color:#9a8c70 !important; }

/* ── Primary button (Sign In / Compare) ─────────────────── */
.stButton > button {
    background:linear-gradient(135deg,#c9a84c,#9a7430) !important;
    color:#0c0c0c !important; border:none !important;
    border-radius:8px !important; font-weight:600 !important;
    transition:filter .2s !important;
}
.stButton > button:hover { filter:brightness(1.12) !important; }

/* ── Download button ─────────────────────────────────────── */
.stDownloadButton > button {
    background:#1e1e1e !important; color:#c9a84c !important;
    border:1px solid #3a3020 !important; border-radius:8px !important;
    font-weight:500 !important;
}
.stDownloadButton > button:hover {
    background:#2a2a1a !important; border-color:#c9a84c !important;
}

/* ── Metrics ─────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background:#161616; border:1px solid #2e2a1e;
    border-radius:12px; padding:16px 20px;
    transition:border-color .25s;
}
[data-testid="stMetric"]:hover { border-color:#c9a84c55; }
[data-testid="stMetricLabel"] { color:#9a8c70 !important; font-size:.76rem !important; text-transform:uppercase; letter-spacing:.08em; }
[data-testid="stMetricValue"] {
    font-family:'Cormorant Garamond',serif !important;
    color:#c9a84c !important; font-size:1.65rem !important;
}

/* ── Dataframe ───────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border-radius:10px; border:1px solid #252525 !important;
}

/* ── Divider ─────────────────────────────────────────────── */
hr { border-color:#2a2a2a !important; }

/* ── Alerts ──────────────────────────────────────────────── */
[data-testid="stAlert"] {
    background:#161616 !important; border-radius:8px !important;
    border-left-color:#c9a84c !important; color:#e8dcc8 !important;
}

/* ── Container border ────────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] {
    background:#141414; border-color:#2e2a1e !important;
    border-radius:14px !important;
}

/* ── Segmented control ───────────────────────────────────── */
[data-testid="stSegmentedControl"] button {
    background:#1a1a1a !important; color:#9a8c70 !important;
    border:1px solid #2e2a1e !important;
}
[data-testid="stSegmentedControl"] button[aria-checked="true"] {
    background:linear-gradient(135deg,#c9a84c,#9a7430) !important;
    color:#0c0c0c !important; font-weight:600 !important;
    border-color:transparent !important;
}

/* ── Toggle ──────────────────────────────────────────────── */
.stToggle span { color:#9a8c70 !important; }

/* ── Spinner ─────────────────────────────────────────────── */
.stSpinner > div { border-top-color:#c9a84c !important; }

/* ── Caption ─────────────────────────────────────────────── */
.stCaption { color:#7a7060 !important; }

/* ── Code block ──────────────────────────────────────────── */
.stCode { background:#111 !important; border:1px solid #2a2a2a !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 · LANGUAGE  (EN / AR)
# ─────────────────────────────────────────────────────────────────────────────

if "lang" not in st.session_state:
    st.session_state["lang"] = "EN"


def get_lang() -> str:
    return st.session_state.get("lang", "EN")


def t(en: str, ar: str) -> str:
    """Return the correct string for the active language."""
    return ar if get_lang() == "AR" else en


def get_system_name(system_key: str) -> str:
    """Return company name in the active language using secrets name / name_ar."""
    if get_lang() == "AR":
        return secrets[system_key].get("name_ar", secrets[system_key]["name"])
    return secrets[system_key]["name"]


def _lang_toggle(key_suffix: str):
    """Render the EN/AR language toggle in the sidebar."""
    st.markdown(f"### {t('Language', 'اللغة')}")
    is_ar = st.toggle(
        "🇸🇦 العربية",
        value=(get_lang() == "AR"),
        key=f"lang_toggle_{key_suffix}",
    )
    st.session_state["lang"] = "AR" if is_ar else "EN"


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 · SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────

for _k in ("uid", "password", "email", "last_meta"):
    if _k not in st.session_state:
        st.session_state[_k] = None

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 · SECRETS VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_KEYS = ("SWAG", "LAROUCHE", "DIFFC", "FASHION_LIMITS")

_REQUIRED_SECRETS: dict[str, list[str]] = {
    "LOGIN":          ["url", "db"],
    "SWAG":           ["name", "name_ar", "url", "db", "user", "api_key"],
    "LAROUCHE":       ["name", "name_ar", "url", "db", "user", "api_key"],
    "DIFFC":          ["name", "name_ar", "url", "db", "user", "api_key"],
    "FASHION_LIMITS": ["name", "name_ar", "url", "db", "user", "api_key"],
}


def _validate_secrets() -> None:
    """Check all required secrets exist. Show setup guide + st.stop() if not."""
    missing: list[str] = []
    for section, keys in _REQUIRED_SECRETS.items():
        if section not in secrets:
            missing.append(f"[{section}]  ← entire section missing")
        else:
            for k in keys:
                if k not in secrets[section]:
                    missing.append(f"[{section}] → {k}")

    if not missing:
        return

    st.error(
        "**🔐 Secrets not configured.**  \n"
        "Add the missing entries to `.streamlit/secrets.toml` (local) "
        "or **App Settings → Secrets** (Streamlit Cloud)."
    )
    st.markdown("**Missing keys:**\n" + "\n".join(f"- `{m}`" for m in missing))
    st.code("""# .streamlit/secrets.toml

[LOGIN]
url = "https://db.swag.com.sa"
db  = "db2"

[SWAG]
name    = "SWAG (Main)"
name_ar = "سواغ (الرئيسي)"
url     = "https://db.swag.com.sa"
db      = "db2"
user    = "ziad.m@swag.com.sa"
api_key = "..."

[LAROUCHE]
name    = "La Rouche"
name_ar = "لا روش"
url     = "https://odooprosys-la-rouche.odoo.com"
db      = "odooprosys-la-rouche-production-12364313"
user    = "operations@swag.com.sa"
api_key = "..."

[DIFFC]
name    = "Different Clothes"
name_ar = "ديفرنت كلوز"
url     = "https://odooprosys-different-clothes.odoo.com"
db      = "odooprosys-different-clothes-production-16906605"
user    = "ziad.m@swag.com.sa"
api_key = "..."

[FASHION_LIMITS]
name    = "Fashion Limits"
name_ar = "فاشن ليميتس"
url     = "https://odooprosys-fashion-limits.odoo.com"
db      = "odooprosys-fashion-limits-production-18388912"
user    = "ziad.m@swag.com.sa"
api_key = "..."
""", language="toml")
    st.stop()


_validate_secrets()

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 · ODOO SYSTEM CONFIGS  (built from secrets after validation)
# ─────────────────────────────────────────────────────────────────────────────

ODOO_SYSTEMS: dict[str, dict] = {
    key: {
        "name":    secrets[key]["name"],
        "name_ar": secrets[key]["name_ar"],
        "url":     secrets[key]["url"].rstrip("/"),
        "db":      secrets[key]["db"],
        "user":    secrets[key]["user"],
        "api_key": secrets[key]["api_key"],
    }
    for key in _SYSTEM_KEYS
}

_LOGIN_URL: str = secrets["LOGIN"]["url"].rstrip("/")
_LOGIN_DB:  str = secrets["LOGIN"]["db"]

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 · ODOO JSON-RPC LAYER
# ─────────────────────────────────────────────────────────────────────────────


def _rpc(url: str, payload: dict, timeout: int = 30):
    """Execute a single JSON-RPC call and return the result value."""
    try:
        r = requests.post(f"{url}/jsonrpc", json=payload, timeout=timeout)
        r.raise_for_status()
    except requests.exceptions.Timeout:
        raise ConnectionError(t(
            f"Request timed out after {timeout}s — check the server.",
            f"انتهت مهلة الطلب ({timeout}ث) — تحقق من الخادم.",
        ))
    except requests.exceptions.ConnectionError:
        raise ConnectionError(t(
            "Cannot reach the Odoo server. Check the URL in secrets.",
            "لا يمكن الوصول إلى خادم أودو. تحقق من الرابط في الإعدادات.",
        ))
    except requests.exceptions.HTTPError as exc:
        raise ConnectionError(t(
            f"HTTP error: {exc}",
            f"خطأ HTTP: {exc}",
        ))

    res = r.json()
    if "error" in res:
        data = res["error"].get("data", {})
        msg  = data.get("message") or data.get("debug") or str(res["error"])
        raise RuntimeError(msg)
    return res.get("result")


def _authenticate(url: str, db: str, user: str, password: str) -> int:
    uid = _rpc(url, {
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


def _search_read(
    url: str, db: str, uid: int, apikey: str,
    model: str, domain: list, fields: list, limit: int = 500,
) -> list:
    result = _rpc(url, {
        "jsonrpc": "2.0", "method": "call",
        "params": {
            "service": "object", "method": "execute_kw",
            "args": [db, uid, apikey, model, "search_read", [domain],
                     {"fields": fields, "limit": limit}],
        },
    }, timeout=60)
    return result or []


def _sys_session(key: str) -> tuple[str, str, int, str]:
    """Authenticate to a system using its api_key (service account)."""
    conf = ODOO_SYSTEMS[key]
    uid  = _authenticate(conf["url"], conf["db"], conf["user"], conf["api_key"])
    return conf["url"], conf["db"], uid, conf["api_key"]


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8 · BUSINESS LOGIC – fetch stock data
# ─────────────────────────────────────────────────────────────────────────────


def _branch_code(loc: str) -> str:
    """Extract top-level branch from a location path like 'WH/Stock'."""
    if isinstance(loc, str) and loc.strip():
        return loc.split("/")[0].strip() if "/" in loc else loc.strip()
    return t("Unknown", "غير معروف")


def fetch_total_stock(model_code: str) -> pd.DataFrame:
    """
    Return one row per Odoo system showing total on-hand qty.
    Never raises — errors are captured as rows with status=ERROR.
    """
    sys_col  = t("System",  "النظام")
    mod_col  = t("Model",   "الموديل")
    prod_col = t("Product", "المنتج")
    qty_col  = t("On Hand", "متوفر")

    rows: list[dict] = []
    for key in _SYSTEM_KEYS:
        display_name = get_system_name(key)
        try:
            url, db, uid, apikey = _sys_session(key)
            recs = _search_read(
                url, db, uid, apikey,
                "product.product",
                [["default_code", "=", model_code]],
                ["id", "display_name", "default_code", "qty_available"],
            )
            if recs:
                r = recs[0]
                rows.append({
                    sys_col:  display_name,
                    mod_col:  r.get("default_code") or model_code,
                    prod_col: r.get("display_name") or "",
                    qty_col:  float(r.get("qty_available") or 0),
                    "_key":   key,
                    "_status":"OK",
                })
            else:
                rows.append({
                    sys_col:  display_name,
                    mod_col:  model_code,
                    prod_col: t("(not found)", "(غير موجود)"),
                    qty_col:  0.0,
                    "_key":   key,
                    "_status":"NOT_FOUND",
                })
        except Exception as exc:
            rows.append({
                sys_col:  display_name,
                mod_col:  model_code,
                prod_col: t(f"(error: {exc})", f"(خطأ: {exc})"),
                qty_col:  0.0,
                "_key":   key,
                "_status":"ERROR",
            })
    return pd.DataFrame(rows)


def fetch_branch_stock(model_code: str) -> pd.DataFrame:
    """
    Return stock.quant rows split by branch/location for all 4 systems.
    Systems that fail are silently skipped (error surfaced via total fetch).
    """
    sys_col  = t("System",   "النظام")
    mod_col  = t("Model",    "الموديل")
    prod_col = t("Product",  "المنتج")
    loc_col  = t("Location", "الموقع")
    br_col   = t("Branch",   "الفرع")
    qty_col  = t("On Hand",  "متوفر")

    rows: list[dict] = []
    for key in _SYSTEM_KEYS:
        display_name = get_system_name(key)
        try:
            url, db, uid, apikey = _sys_session(key)

            prods = _search_read(
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

            quants = _rpc(url, {
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
                loc_name = (
                    loc[1] if isinstance(loc, (list, tuple)) and len(loc) >= 2
                    else ""
                )
                rows.append({
                    sys_col:  display_name,
                    mod_col:  model_code,
                    prod_col: prod_name,
                    loc_col:  loc_name,
                    br_col:   _branch_code(loc_name),
                    qty_col:  float(q.get("quantity") or 0),
                })
        except Exception:
            continue   # silently skip — error already shown in total table

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9 · DOWNLOAD HELPERS  (UTF-8-BOM for Arabic Excel compatibility)
# ─────────────────────────────────────────────────────────────────────────────


def _to_csv(df: pd.DataFrame) -> bytes:
    """CSV with UTF-8 BOM so Arabic opens correctly in Excel."""
    return df.to_csv(index=False).encode("utf-8-sig")


def _to_excel(sheets: dict[str, pd.DataFrame]) -> bytes:
    """Multi-sheet Excel workbook."""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
    return buf.getvalue()


def _display_df(df: pd.DataFrame, qty_label: str | None = None) -> None:
    """Render a DataFrame without the internal _key / _status helper columns."""
    show = df.drop(columns=[c for c in ("_key", "_status") if c in df.columns],
                   errors="ignore")
    qty_col = qty_label or t("On Hand", "متوفر")
    st.dataframe(
        show,
        width="stretch",
        hide_index=True,
        column_config={
            qty_col: st.column_config.NumberColumn(
                qty_col, format="%d"
            )
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 10 · LOGIN PAGE
# ─────────────────────────────────────────────────────────────────────────────


def render_login() -> None:
    with st.sidebar:
        _lang_toggle("login")

    # ── Centred hero + form ──────────────────────────────────────────────────
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.1, 1])
    with mid:
        st.markdown(
            f"<h1 style='text-align:center;margin-bottom:4px'>"
            f"🏢 {t('SWAG Dashboard', 'لوحة سواغ')}</h1>"
            f"<p style='text-align:center;color:#7a7060;font-size:.86rem;"
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
                key="login_email",
            )
            password = st.text_input(
                t("Password", "كلمة المرور"),
                type="password",
                placeholder=t("Enter your password", "أدخل كلمة المرور"),
                key="login_password",
            )
            st.markdown("<br>", unsafe_allow_html=True)

            if st.button(
                t("Sign In →", "دخول →"),
                type="primary",
                use_container_width=True,
                key="btn_signin",
            ):
                if not email or not password:
                    st.error(t(
                        "Email and password are required.",
                        "البريد الإلكتروني وكلمة المرور مطلوبان.",
                    ))
                else:
                    with st.spinner(t("Authenticating…", "جارٍ التحقق…")):
                        try:
                            uid = _authenticate(
                                _LOGIN_URL, _LOGIN_DB, email, password
                            )
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
# SECTION 11 · MAIN DASHBOARD  (single page, no navigation)
# ─────────────────────────────────────────────────────────────────────────────


def _render_snapshot() -> None:
    """Render the last-run snapshot card."""
    meta = st.session_state.get("last_meta")
    with st.container(border=True):
        st.markdown(f"**📊 {t('Last run snapshot', 'ملخص آخر تشغيل')}**")
        if not meta:
            st.caption(t(
                "Run a comparison to see results here.",
                "شغّل مقارنة لرؤية النتائج هنا.",
            ))
            return

        m1, m2 = st.columns(2)
        m1.metric(t("Models", "الموديلات"), meta["n_models"])
        m2.metric(t("Systems OK", "أنظمة متصلة"),
                  f"{meta['n_ok']}/{len(_SYSTEM_KEYS)}")
        st.divider()

        def _badge(s: str) -> str:
            return {"OK": "🟢 OK", "OFF": "🔴 OFF", "ERROR": "🔴 ERR"}.get(s, "⚪ N/A")

        lines = []
        for key in _SYSTEM_KEYS:
            name = get_system_name(key)
            lines.append(f"**{name}:** {_badge(meta.get(key, 'N/A'))}")
        st.markdown("  \n".join(lines))


def render_dashboard() -> None:
    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        _lang_toggle("dash")
        st.divider()
        st.markdown("**🏢 SWAG Dashboard**")
        st.caption(f"👤 {st.session_state['email']}")
        st.divider()
        if st.button(
            t("🚪 Logout", "🚪 تسجيل الخروج"),
            use_container_width=True,
            key="btn_logout",
        ):
            for k in ("uid", "password", "email", "last_meta"):
                st.session_state[k] = None
            st.rerun()

    # ── Page header ────────────────────────────────────────────────────────────
    st.markdown(
        f"<h1 style='margin-bottom:2px'>🔁 "
        f"{t('4-Odoo Live Stock Compare', 'مقارنة المخزون الحي لأربعة أودو')}"
        f"</h1>"
        f"<p style='color:#9a8c70;font-size:.86rem;margin-top:0'>"
        f"{t('SWAG · La Rouche · Different Clothes · Fashion Limits — real-time stock per model code','سواغ · لا روش · ديفرنت كلوز · فاشن ليميتس — مخزون الموديل في الوقت الفعلي')}"
        f"</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    # ── Two-column layout: controls (left) + snapshot (right) ─────────────────
    ctrl_col, snap_col = st.columns([1.9, 1], gap="large")

    with snap_col:
        _render_snapshot()

    with ctrl_col:
        # Mode selector
        single_lbl = t("Single model", "موديل واحد")
        multi_lbl  = t("Multiple models", "عدة موديلات")
        mode = st.segmented_control(
            t("Query mode", "وضع الاستعلام"),
            options=[single_lbl, multi_lbl],
            default=single_lbl,
            key="qmode",
        )

        if mode == multi_lbl:
            raw = st.text_area(
                t("Default codes – one per line", "أكواد الموديلات – كود في كل سطر"),
                placeholder="MM0579\nRVT196\nAB1234",
                height=120,
                key="multi_input",
            )
            models = [m.strip().upper() for m in raw.splitlines() if m.strip()]
        else:
            raw = st.text_input(
                t("Default code", "كود الموديل"),
                placeholder=t("e.g. RVT196", "مثال: RVT196"),
                key="single_input",
            )
            models = [raw.strip().upper()] if raw.strip() else []

        st.caption(t(
            "ℹ️  Use the Internal Reference field (default_code), not the product display name.",
            "ℹ️  استخدم حقل الرمز الداخلي (default_code) وليس اسم المنتج.",
        ))

        # Toggle options
        o1, o2, o3 = st.columns(3)
        show_zero   = o1.toggle(t("Show zero",     "عرض الصفر"),       value=True,  key="tog_zero")
        show_branch = o2.toggle(t("Branch detail", "تفاصيل الفروع"),  value=True,  key="tog_branch")
        sort_sys    = o3.toggle(t("Sort by system","ترتيب حسب النظام"),value=True,  key="tog_sort")

        run = st.button(
            t("🚀  Compare across 4 Odoo systems", "🚀  مقارنة عبر 4 أنظمة أودو"),
            type="primary",
            use_container_width=True,
            key="btn_compare",
        )

    # ── Guard ─────────────────────────────────────────────────────────────────
    if not run:
        return

    if not models:
        st.warning(t(
            "Enter at least one default code to compare.",
            "أدخل كود موديل واحد على الأقل للمقارنة.",
        ))
        return

    # ── Fetch total stock ──────────────────────────────────────────────────────
    st.divider()
    prog = st.progress(0, text=t("⏳  Connecting to Odoo systems…", "⏳  الاتصال بأنظمة أودو…"))

    qty_col = t("On Hand", "متوفر")
    sys_col = t("System",  "النظام")
    qry_col = t("Query",   "الاستعلام")

    all_frames: list[pd.DataFrame] = []
    status_map: dict[str, str]     = {k: "N/A" for k in _SYSTEM_KEYS}

    for i, code in enumerate(models):
        prog.progress(
            int((i / len(models)) * 80),
            text=t(f"⏳  Fetching: {code}", f"⏳  جلب: {code}"),
        )
        df = fetch_total_stock(code)

        # Update status map from this batch
        for key in _SYSTEM_KEYS:
            name = get_system_name(key)
            row  = df[df[sys_col] == name]
            if not row.empty:
                s = row.iloc[0].get("_status", "N/A")
                status_map[key] = "OK" if s == "OK" else ("OFF" if s == "NOT_FOUND" else "ERROR")

        df = df.drop(columns=["_key", "_status"], errors="ignore")
        if not show_zero:
            df = df[df[qty_col] != 0]
        df.insert(0, qry_col, code)
        all_frames.append(df)

    prog.progress(90, text=t("⏳  Building results…", "⏳  بناء النتائج…"))

    # Save snapshot
    st.session_state["last_meta"] = {
        "n_models": len(models),
        "n_ok":     sum(1 for v in status_map.values() if v == "OK"),
        **status_map,
    }

    df_all = (
        pd.concat([f for f in all_frames if not f.empty], ignore_index=True)
        if all_frames else pd.DataFrame()
    )
    if sort_sys and not df_all.empty:
        df_all = df_all.sort_values([qry_col, sys_col])

    prog.progress(100, text=t("✅  Done", "✅  اكتملت"))
    prog.empty()

    if df_all.empty:
        st.info(t(
            "No data returned. Verify the model codes are correct (case-sensitive).",
            "لا توجد بيانات. تأكد من صحة أكواد الموديلات (حساسة لحالة الأحرف).",
        ))
        return

    # ── KPI metrics per system ─────────────────────────────────────────────────
    st.subheader("🔢 " + t("On-Hand Summary by System", "ملخص المتوفر حسب النظام"))
    totals = df_all.groupby(sys_col)[qty_col].sum()
    kpi_cols = st.columns(len(_SYSTEM_KEYS))
    for i, key in enumerate(_SYSTEM_KEYS):
        name = get_system_name(key)
        val  = totals.get(name, 0)
        stat = status_map.get(key, "N/A")
        delta_str = (
            None if stat == "OK"
            else t("not found", "غير موجود") if stat == "OFF"
            else t("connection error", "خطأ في الاتصال")
        )
        kpi_cols[i].metric(
            label=name,
            value=f"{val:,.0f} {t('pcs','قطعة')}",
            delta=delta_str,
            delta_color="off" if delta_str else "normal",
        )

    # ── Total stock table ──────────────────────────────────────────────────────
    st.subheader("📋 " + t("Detailed Results", "النتائج التفصيلية"))
    _display_df(df_all, qty_col)

    # Downloads – total
    dl1, dl2, _ = st.columns([1, 1, 2])
    dl1.download_button(
        t("⬇️ CSV", "⬇️ CSV"),
        _to_csv(df_all),
        file_name="odoo_stock_total.csv",
        mime="text/csv",
        key="dl_total_csv",
    )
    dl2.download_button(
        t("⬇️ Excel", "⬇️ Excel"),
        _to_excel({t("Total Stock", "إجمالي المخزون"): df_all}),
        file_name="odoo_stock_total.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_total_xlsx",
    )

    # ── Branch detail ──────────────────────────────────────────────────────────
    if not show_branch:
        return

    st.divider()
    st.subheader("🏬 " + t(
        "Branch-wise Stock Detail (all 4 systems)",
        "تفاصيل المخزون حسب الفرع (الأنظمة الأربعة)",
    ))
    st.caption(t(
        "Reads stock.quant from all internal warehouse locations across all systems.",
        "يقرأ stock.quant من جميع مواقع المستودعات الداخلية في الأنظمة الأربعة.",
    ))

    br_prog = st.progress(0, text=t("⏳  Fetching branch data…", "⏳  جلب بيانات الفروع…"))
    branch_frames: list[pd.DataFrame] = []

    for i, code in enumerate(models):
        br_prog.progress(
            int((i / len(models)) * 90),
            text=t(f"⏳  Branch data: {code}", f"⏳  بيانات الفرع: {code}"),
        )
        df_b = fetch_branch_stock(code)
        if not df_b.empty:
            df_b.insert(0, qry_col, code)
            branch_frames.append(df_b)

    br_prog.progress(100, text=t("✅  Done", "✅  اكتملت"))
    br_prog.empty()

    if not branch_frames:
        st.info(t(
            "No branch stock data found. The products may not exist in any internal locations.",
            "لا توجد بيانات مخزون للفروع. قد لا توجد المنتجات في أي مواقع داخلية.",
        ))
        return

    df_branch = pd.concat(branch_frames, ignore_index=True)
    br_col  = t("Branch",  "الفرع")
    df_branch = df_branch.sort_values(
        [qry_col, sys_col, br_col, t("Location", "الموقع")]
    )

    # ── Bar chart ──────────────────────────────────────────────────────────────
    agg = (
        df_branch.groupby([sys_col, br_col], as_index=False)[qty_col]
        .sum()
        .sort_values(qty_col, ascending=False)
    )
    # Build ordered colour sequence matching system order
    sys_names   = [get_system_name(k) for k in _SYSTEM_KEYS]
    colour_pool = ["#c9a84c", "#7a5c1e", "#e8c97a", "#a0783c"]
    colour_map  = {name: colour_pool[i % len(colour_pool)]
                   for i, name in enumerate(sys_names)}
    colours     = [colour_map.get(s, "#c9a84c") for s in agg[sys_col]]

    fig = px.bar(
        agg,
        x=br_col, y=qty_col, color=sys_col,
        barmode="group",
        color_discrete_sequence=colour_pool,
        title=t(
            "On-Hand Qty by Branch & System",
            "الكمية المتوفرة حسب الفرع والنظام",
        ),
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans", color="#e8dcc8"),
        title_font=dict(family="Cormorant Garamond", color="#c9a84c", size=18),
        xaxis=dict(tickangle=-35, gridcolor="#1e1e1e"),
        yaxis=dict(gridcolor="#1e1e1e"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.4,
                    bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig, width="stretch")

    # ── Branch table ───────────────────────────────────────────────────────────
    _display_df(df_branch, qty_col)

    # Downloads – branches
    bld1, bld2, _ = st.columns([1, 1, 2])
    bld1.download_button(
        t("⬇️ Branch CSV", "⬇️ CSV الفروع"),
        _to_csv(df_branch),
        file_name="odoo_stock_branches.csv",
        mime="text/csv",
        key="dl_branch_csv",
    )
    bld2.download_button(
        t("⬇️ Full Excel (both sheets)", "⬇️ Excel الكامل (ورقتان)"),
        _to_excel({
            t("Total Stock",    "إجمالي المخزون"): df_all,
            t("Branch Detail",  "تفاصيل الفروع"):  df_branch,
        }),
        file_name="odoo_stock_full.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_branch_xlsx",
    )


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 12 · ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if st.session_state.get("uid") is None:
    render_login()
else:
    render_dashboard()
