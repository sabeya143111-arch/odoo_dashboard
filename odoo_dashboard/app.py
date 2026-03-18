# ╔══════════════════════════════════════════════════════════════════╗
# ║         👗 Outfit Dashboard – 3‑Odoo Compare (Bilingual)        ║
# ╚══════════════════════════════════════════════════════════════════╝

import streamlit as st

st.set_page_config(
    page_title="👗 Outfit Dashboard",
    page_icon="👗",
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
# GLOBALS
# ─────────────────────────────────────────────────────────────────────────────

from streamlit.runtime.secrets import secrets

ODOO_URL = "https://db.swag.com.sa"
ODOO_DB = "db2"

BATCH = 1_000

# 3 Odoo configs – values loaded from Streamlit secrets (not visible in GitHub)
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
# LANGUAGE SUPPORT
# ─────────────────────────────────────────────────────────────────────────────

if "lang" not in st.session_state:
    st.session_state["lang"] = "EN"


def set_lang(lang_code: str):
    st.session_state["lang"] = lang_code


def get_lang() -> str:
    return st.session_state.get("lang", "EN")


def t(en: str, ar: str) -> str:
    return ar if get_lang() == "AR" else en


# ─────────────────────────────────────────────────────────────────────────────
# STYLING
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    color: #e8dcc8;
}
.stApp { background: #0c0c0c; }
.block-container { padding-top: 1.4rem; padding-bottom: 2rem; }

h1, h2, h3, h4 {
    font-family: 'Cormorant Garamond', serif;
    color: #c9a84c;
    letter-spacing: .04em;
}

section[data-testid="stSidebar"] {
    background: #111111;
    border-right: 1px solid #2a2a2a;
}

.kpi-wrap {
    background: #161616;
    border: 1px solid #2e2a1e;
    border-radius: 14px;
    padding: 18px 22px;
    text-align: center;
    transition: border-color .25s;
}
.kpi-wrap:hover { border-color: #c9a84c55; }
.kpi-label {
    font-size: .72rem;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: #7a7060;
    margin-bottom: 6px;
}
.kpi-value {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.7rem;
    font-weight: 700;
    color: #c9a84c;
}
.kpi-sub { font-size: .75rem; color: #5a5040; margin-top: 2px; }

.card {
    background: #141414;
    border: 1px solid #252525;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 18px;
}

.stDownloadButton > button {
    border-radius: 999px !important;
    background: linear-gradient(135deg,#c9a84c,#9a7430) !important;
    color: #000 !important;
    border: none !important;
    font-weight: 600 !important;
    font-size: .8rem !important;
}

[data-testid="stDataFrame"] {
    border-radius: 10px;
    border: 1px solid #252525 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# PLOTLY TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────

pio.templates["outfit"] = pio.templates["plotly_dark"]
pio.templates["outfit"].layout.update(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans", color="#e8dcc8"),
    colorway=["#c9a84c", "#7a5c1e", "#e8c97a", "#5a3e10", "#f0dda0"],
    legend=dict(orientation="h", yanchor="bottom", y=-0.28),
)
pio.templates.default = "outfit"
_GOLD = [[0, "#1a1500"], [0.5, "#9a7430"], [1, "#c9a84c"]]

for _k in ("uid", "api_key", "email"):
    if _k not in st.session_state:
        st.session_state[_k] = None


# ─────────────────────────────────────────────────────────────────────────────
# JSON‑RPC HELPERS
# ─────────────────────────────────────────────────────────────────────────────


def odoo_rpc(endpoint: str, method: str, args: list):
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {"service": endpoint, "method": method, "args": args},
    }
    r = requests.post(f"{ODOO_URL}/jsonrpc", json=payload, timeout=60)
    res = r.json()
    if "error" in res:
        raise Exception(
            res["error"].get("data", {}).get("message", str(res["error"]))
        )
    return res["result"]


def odoo_login(email: str, api_key: str) -> int:
    uid = odoo_rpc("common", "authenticate", [ODOO_DB, email, api_key, {}])
    if not uid:
        raise Exception(
            t(
                "Login failed – check your e-mail and password.",
                "تسجيل الدخول فشل – تأكد من الإيميل وكلمة المرور.",
            )
        )
    return uid


def odoo_jsonrpc_auth(sys_name: str, conf: dict) -> tuple:
    url = conf["url"].rstrip("/")
    db = conf["db"]
    user = conf["user"]
    apikey = conf["api_key"]

    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "common",
            "method": "authenticate",
            "args": [db, user, apikey, {}],
        },
    }
    r = requests.post(f"{url}/jsonrpc", json=payload, timeout=30)
    res = r.json()
    if "error" in res:
        raise Exception(f"{sys_name} login failed: {res['error']}")
    uid = res.get("result")
    if not uid:
        raise Exception(f"{sys_name} login failed (uid False)")
    return url, db, uid, apikey


def odoo_jsonrpc_search_read(
    sys_name: str,
    conf: dict,
    model: str,
    domain: list,
    fields: list,
    limit: int = 500,
):
    url, db, uid, apikey = odoo_jsonrpc_auth(sys_name, conf)
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "service": "object",
            "method": "execute_kw",
            "args": [
                db,
                uid,
                apikey,
                model,
                "search_read",
                [domain],
                {"fields": fields, "limit": limit},
            ],
        },
    }
    r = requests.post(f"{url}/jsonrpc", json=payload, timeout=60)
    res = r.json()
    if "error" in res:
        raise Exception(
            res["error"].get("data", {}).get("message", str(res["error"]))
        )
    return res["result"]


def compare_model_across_odoos(model_code: str) -> pd.DataFrame:
    rows = []
    for key, conf in ODOO_SYSTEMS.items():
        name = conf["name"]
        try:
            recs = odoo_jsonrpc_search_read(
                name,
                conf,
                "product.product",
                [["default_code", "=", model_code]],
                ["id", "display_name", "default_code", "qty_available"],
            )
            if recs:
                r = recs[0]
                rows.append(
                    {
                        "System": name,
                        "Model": r.get("default_code") or model_code,
                        "Product": r.get("display_name") or "",
                        "Qty": float(r.get("qty_available") or 0.0),
                    }
                )
            else:
                rows.append(
                    {
                        "System": name,
                        "Model": model_code,
                        "Product": "(not found)",
                        "Qty": 0.0,
                    }
                )
        except Exception:
            rows.append(
                {
                    "System": name,
                    "Model": model_code,
                    "Product": "(not connected)",
                    "Qty": 0.0,
                }
            )
    return pd.DataFrame(rows)


def get_branch_code(location_name: str) -> str:
    if isinstance(location_name, str) and location_name.strip():
        return (
            location_name.split("/")[0].strip()
            if "/" in location_name
            else location_name.strip()
        )
    return "Unknown"


def branch_stock_for_model_across_odoos(model_code: str) -> pd.DataFrame:
    rows = []
    for key, conf in ODOO_SYSTEMS.items():
        sys_name = conf["name"]
        try:
            prods = odoo_jsonrpc_search_read(
                sys_name,
                conf,
                "product.product",
                [["default_code", "=", model_code]],
                ["id", "display_name", "default_code"],
                limit=50,
            )
            if not prods:
                continue
            prod_ids = [p["id"] for p in prods]
            prod_name = prods[0].get("display_name") or ""
            url, db, uid, apikey = odoo_jsonrpc_auth(sys_name, conf)

            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "service": "object",
                    "method": "execute_kw",
                    "args": [
                        db,
                        uid,
                        apikey,
                        "stock.quant",
                        "search_read",
                        [
                            [
                                ["product_id", "in", prod_ids],
                                ["location_id.usage", "=", "internal"],
                            ]
                        ],
                        {
                            "fields": [
                                "product_id",
                                "location_id",
                                "quantity",
                            ],
                            "limit": 2000,
                        },
                    ],
                },
            }
            r = requests.post(f"{url}/jsonrpc", json=payload, timeout=60)
            res = r.json()
            if "error" in res:
                raise Exception(
                    res["error"]
                    .get("data", {})
                    .get("message", str(res["error"]))
                )
            quants = res["result"]

            for q in quants:
                loc = q.get("location_id")
                if isinstance(loc, (list, tuple)) and len(loc) >= 2:
                    loc_name = loc[1]
                else:
                    loc_name = ""
                qty = float(q.get("quantity") or 0.0)
                rows.append(
                    {
                        "System": sys_name,
                        "Model": model_code,
                        "Product": prod_name,
                        "LocationName": loc_name,
                        "BranchCode": get_branch_code(loc_name),
                        "Qty": qty,
                    }
                )
        except Exception:
            continue

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────────────────────────────────────


def kpi(label: str, value: str, sub: str = ""):
    st.markdown(
        f'<div class="kpi-wrap">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-sub">{sub}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def _qty(label=None):
    return st.column_config.NumberColumn(
        label or t("Qty", "الكمية"), format="%d"
    )


# ─────────────────────
