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

ODOO_URL = "https://db.swag.com.sa"
ODOO_DB = "db2"

BATCH = 1_000

# 3 Odoo configs (we will also mirror these into hidden Streamlit inputs)
ODOO_SYSTEMS = {
    "SWAG": {
        "name": "SWAG (Main)",
        "url": "https://db.swag.com.sa",
        "db": "db2",
        "user": "ziad.m@swag.com.sa",
        "api_key": "d3b200e2b4c78112278baed986ea3191062f3773",
    },
    "LAROUCHE": {
        "name": "La Rouche",
        "url": "https://odooprosys-la-rouche.odoo.com",
        "db": "odooprosys-la-rouche-production-12364313",
        "user": "operations@swag.com.sa",
        "api_key": "41a79461e550026f539b09044a9d519dc1a2ffe8",
    },
    "DIFFC": {
        "name": "Different Clothes",
        "url": "https://odooprosys-different-clothes.odoo.com",
        "db": "odooprosys-different-clothes-production-16906605",
        "user": "ziad.m@swag.com.sa",
        "api_key": "05e22b60bc95bf9fd4323e41b428590a0c6c3f28",
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

/* KPI card */
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

.js-plotly-plot .plotly { background: transparent !important; }

.stDownloadButton > button {
    border-radius: 999px !important;
    background: linear-gradient(135deg,#c9a84c,#9a7430) !important;
    color: #000 !important;
    border: none !important;
    font-weight: 600 !important;
    font-size: .8rem !important;
    transition: filter .2s !important;
}
.stDownloadButton > button:hover { filter: brightness(1.1) !important; }

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

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────

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
                "فشل تسجيل الدخول – تأكد من الإيميل وكلمة المرور.",
            )
        )
    return uid


# ─────────────────────────────────────────────────────────────────────────────
# 3‑ODOO HELPERS (JSON‑RPC)
# ─────────────────────────────────────────────────────────────────────────────


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


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: 3‑ODOO STOCK COMPARE
# ─────────────────────────────────────────────────────────────────────────────


def page_multi_odoo_compare():
    st.markdown(
        f"""
    <div style="
        padding:18px 20px;
        border-radius:16px;
        margin-bottom:18px;
        border:1px solid #3a321f;
        background:radial-gradient(circle at 0 0,#3a2a10 0,#0c0c0c 45%);
        display:flex;align-items:center;justify-content:space-between;">
      <div>
        <div style="font-family:'Cormorant Garamond',serif;
                    font-size:1.6rem;color:#e8dcc8;letter-spacing:.06em;">
          🔁 {t('3‑Odoo Live Stock Mirror','مرآة المخزون الحي لثلاثة أودو')}
        </div>
        <div style="color:#9a8c70;font-size:.8rem;margin-top:4px;">
          {t('SWAG · La Rouche · Different Clothes — real‑time model stock',
             'سواغ · لا روش · ديفرنت كلوز — مخزون الموديل في الوقت الفعلي')}
        </div>
      </div>
      <div style="text-align:right;font-size:.76rem;color:#7a7060;">
        <div>{t('Source: Odoo JSON‑RPC','المصدر: Odoo JSON‑RPC')}</div>
        <div>{t('Updated on refresh • Live per query',
                 'يتحدّث عند التحديث • مباشر لكل استعلام')}</div>
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # HIDDEN CONFIG SECTION (3 Odoo details hidden inside expander)
    with st.expander(t("Advanced connection settings","إعدادات الاتصال المتقدمة"), expanded=False):
        st.caption(
            t(
                "3‑Odoo credentials are stored here (for admin only).",
                "بيانات الاتصال لـ 3 أودو محفوظة هنا (للإدارة فقط).",
            )
        )
        for key, conf in ODOO_SYSTEMS.items():
            st.text_input(
                f"{key} URL",
                value=conf["url"],
                key=f"cfg_{key}_url",
                disabled=True,
            )
            st.text_input(
                f"{key} DB",
                value=conf["db"],
                key=f"cfg_{key}_db",
                disabled=True,
            )
            st.text_input(
                f"{key} User",
                value=conf["user"],
                key=f"cfg_{key}_user",
                disabled=True,
            )
            st.text_input(
                f"{key} Secret",
                value=conf["api_key"],
                key=f"cfg_{key}_api",
                type="password",
                disabled=True,
            )

    col_left, col_right = st.columns([1.7, 1])

    with col_left:
        mode_single = t("Single model", "موديل واحد")
        mode_multi = t("Multiple models", "عدة موديلات")
        multi_mode = st.segmented_control(
            t("Mode", "الوضع"),
            options=[mode_single, mode_multi],
            default=mode_single,
        )

        if multi_mode == mode_multi:
            model_input = st.text_area(
                t("Models / Default Codes", "الموديلات / الأكواد"),
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

        st.caption(
            t(
                "Tip: Use default code, not display name.",
                "ملاحظة: استخدم كود الموديل، ليس اسم المنتج.",
            )
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            show_zero = st.toggle(
                t("Show zero qty", "عرض الكمية صفر"), value=True
            )
        with c2:
            show_branch = st.toggle(
                t(
                    "Branch‑wise detail (3‑Odoo)",
                    "تفاصيل حسب الفرع (3 أودو)",
                ),
                value=True,
            )
        with c3:
            sort_by_system = st.toggle(
                t("System wise sort", "ترتيب حسب النظام"),
                value=True,
            )

        run_compare = st.button(
            t("🚀 Compare across 3 Odoo", "🚀 مقارنة عبر 3 أودو"),
            type="primary",
            use_container_width=True,
        )

    with col_right:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("###### " + t("Snapshot (last run)", "ملخص (آخر تشغيل)"))
        st.caption(
            t(
                "Small summary based on latest query.",
                "ملخص بسيط بناءً على آخر استعلام.",
            )
        )
        if "last_compare_meta" in st.session_state:
            meta = st.session_state["last_compare_meta"]
            c1, c2 = st.columns(2)
            with c1:
                kpi(
                    t("Models checked", "الموديلات المفحوصة"),
                    f"{meta.get('models',0):,}",
                )
            with c2:
                kpi(
                    t("Systems online", "الأنظمة المتصلة"),
                    f"{meta.get('systems_ok',0)}/3",
                )
            st.caption(
                f"SWAG: {meta.get('swag_status','?')}  ·  "
                f"La Rouche: {meta.get('lr_status','?')}  ·  "
                f"Different Clothes: {meta.get('dc_status','?')}"
            )
        else:
            st.info(
                t("No comparison run yet.", "لم يتم تشغيل أي مقارنة بعد."),
                icon="ℹ️",
            )
        st.markdown("</div>", unsafe_allow_html=True)

    if not run_compare:
        return

    if not models:
        st.warning(
            t(
                "Enter at least 1 model/default code.",
                "أدخل موديل/كود واحد على الأقل.",
            )
        )
        return

    with st.spinner(
        t(
            "Fetching live stock from 3 Odoo instances…",
            "جلب المخزون الحي من 3 قواعد أودو…",
        )
    ):
        all_rows = []
        swag_status = "N/A"
        lr_status = "N/A"
        dc_status = "N/A"

        for m in models:
            df_one = compare_model_across_odoos(m)

            if "SWAG (Main)" in df_one["System"].values:
                row = df_one[df_one["System"] == "SWAG (Main)"].iloc[0]
                swag_status = (
                    "OK"
                    if row["Product"]
                    not in ("(not connected)", "(not found)")
                    else "OFF"
                )
            if "La Rouche" in df_one["System"].values:
                row = df_one[df_one["System"] == "La Rouche"].iloc[0]
                lr_status = (
                    "OK"
                    if row["Product"]
                    not in ("(not connected)", "(not found)")
                    else "OFF"
                )
            if "Different Clothes" in df_one["System"].values:
                row = df_one[df_one["System"] == "Different Clothes"].iloc[0]
                dc_status = (
                    "OK"
                    if row["Product"]
                    not in ("(not connected)", "(not found)")
                    else "OFF"
                )

            if not show_zero:
                df_one = df_one[df_one["Qty"] != 0]
            df_one.insert(0, "QueryModel", m)
            all_rows.append(df_one)

        if not all_rows:
            st.info(
                t(
                    "No data found (maybe all quantities are 0 or models invalid).",
                    "لا توجد بيانات (ربما كل الكميات صفر أو الموديلات غير صحيحة).",
                )
            )
            return

        df_all = pd.concat(all_rows, ignore_index=True)

    st.session_state["last_compare_meta"] = {
        "models": len(models),
        "systems_ok": len(
            df_all.loc[
                df_all["Product"] != "(not connected)", "System"
            ].unique()
        ),
        "swag_status": swag_status,
        "lr_status": lr_status,
        "dc_status": dc_status,
    }

    if sort_by_system:
        df_all = df_all.sort_values(["QueryModel", "System"])

    st.markdown(
        "### " + t("🔢 Total On‑Hand per System", "🔢 إجمالي المتوفر لكل نظام")
    )
    st.dataframe(
        df_all,
        use_container_width=True,
        hide_index=True,
        column_config={"Qty": _qty(t("On Hand", "متوفر"))},
    )

    csv = df_all.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        t("⬇️ Download CSV (Total view)", "⬇️ تحميل CSV (عرض إجمالي)"),
        csv,
        file_name="three_odoo_stock_compare_total.csv",
        mime="text/csv",
    )

    if show_branch:
        st.markdown("---")
        st.markdown(
            "### "
            + t(
                "🏬 Branch‑wise Stock (SWAG + La Rouche + Different Clothes)",
                "🏬 المخزون حسب الفرع (سواغ + لا روش + ديفرنت كلوز)",
            )
        )
        st.caption(
            t(
                "Internal warehouses/branches for all 3 systems (0 qty included).",
                "كل الفروع الداخلية للأنظمة الثلاثة (تشمل الكمية صفر).",
            )
        )

        with st.spinner(
            t(
                "Fetching branch‑wise stock.quant data…",
                "جلب بيانات stock.quant حسب الفروع…",
            )
        ):
            all_b = []
            for m in models:
                df_b = branch_stock_for_model_across_odoos(m)
                if df_b.empty:
                    continue
                df_b.insert(0, "QueryModel", m)
                all_b.append(df_b)

        if all_b:
            df_branch = pd.concat(all_b, ignore_index=True)
            df_branch = df_branch.sort_values(
                ["QueryModel", "System", "BranchCode", "LocationName"]
            )

            st.markdown(
                "#### "
                + t("Qty heat (branches)", "شدة الكمية (الفروع)")
            )
            agg_branch = (
                df_branch.groupby(
                    ["System", "BranchCode"], as_index=False
                )["Qty"]
                .sum()
                .sort_values("Qty", ascending=False)
            )
            fig = px.bar(
                agg_branch,
                x="BranchCode",
                y="Qty",
                color="System",
                title=t(
                    "Top branches by On‑Hand Qty (3‑Odoo)",
                    "أعلى الفروع حسب الكمية المتوفرة (3 أودو)",
                ),
                color_continuous_scale=_GOLD,
            )
            st.plotly_chart(fig, use_container_width=True)

            st.markdown(
                "#### " + t("Detail table", "جدول التفاصيل")
            )
            st.dataframe(
                df_branch,
                use_container_width=True,
                hide_index=True,
                column_config={"Qty": _qty(t("On Hand", "متوفر"))},
            )

            csv_b = df_branch.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                t(
                    "⬇️ Download CSV (Branch‑wise)",
                    "⬇️ تحميل CSV (حسب الفروع)",
                ),
                csv_b,
                file_name="three_odoo_stock_compare_branchwise.csv",
                mime="text/csv",
            )
        else:
            st.info(
                t(
                    "No branch‑wise data found.",
                    "لا توجد بيانات حسب الفروع.",
                )
            )


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN PAGE
# ─────────────────────────────────────────────────────────────────────────────


def login_page():
    st.markdown(
        f"""
    <div style="text-align:center;padding:60px 0 30px">
      <h1 style="font-family:'Cormorant Garamond',serif;color:#c9a84c;font-size:2.8rem;margin:0">
        👗 {t('Outfit Dashboard','لوحة تحكم أوتفِت')}</h1>
      <p style="color:#5a5040;margin-top:8px;letter-spacing:.08em;font-size:.85rem">
        {t('3‑ODOO LIVE STOCK MIRROR','مرآة المخزون الحي لثلاثة أودو')}</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        with st.container(border=True):
            st.markdown("#### " + t("Login to Odoo", "تسجيل الدخول إلى أودو"))
            st.text_input(
                t("URL", "الرابط"), value=ODOO_URL, disabled=True
            )
            st.text_input(
                t("Database", "قاعدة البيانات"),
                value=ODOO_DB,
                disabled=True,
            )
            email = st.text_input(
                t("Email", "الإيميل"),
                placeholder="user@example.com",
            )
            password = st.text_input(
                t("Password", "كلمة المرور"),
                type="password",
                placeholder=t("Enter your password", "أدخل كلمة المرور"),
            )
            if st.button(
                t("Login", "تسجيل الدخول"),
                type="primary",
                use_container_width=True,
            ):
                if not email or not password:
                    st.error(
                        t(
                            "Email and password are required.",
                            "الإيميل وكلمة المرور مطلوبان.",
                        )
                    )
                else:
                    with st.spinner(
                        t("Connecting…", "جاري الاتصال…")
                    ):
                        try:
                            uid = odoo_login(email, password)
                            st.session_state.uid = uid
                            st.session_state.api_key = password
                            st.session_state.email = email
                            st.rerun()
                        except Exception as e:
                            st.error(
                                f"{t('Login failed:','فشل تسجيل الدخول:')} {e}"
                            )
        st.caption(
            t(
                "Use your Odoo email and password to login.",
                "استخدم إيميل وكلمة مرور أودو لتسجيل الدخول.",
            )
        )


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD SHELL
# ─────────────────────────────────────────────────────────────────────────────


def dashboard():
    today = datetime.today().date()

    st.markdown(
        f"""
    <div style="text-align:center;padding:10px 0;
                background:linear-gradient(90deg,#0c0c0c,#2a2010,#0c0c0c);
                border-radius:12px;margin-bottom:20px;
                border:1px solid #2e2a1e;">
      <span style="font-family:'Cormorant Garamond',serif;color:#c9a84c;
                   font-size:1.05rem;letter-spacing:.1em;">
        👗 {t('OUTFIT COMPANY – 3‑ODOO LIVE STOCK',
              'شركة أوتفِت – مخزون حي من 3 أودو')}
      </span>
    </div>
    """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### " + t("Language", "اللغة"))
        lang_choice = st.toggle("العربية", value=(get_lang() == "AR"))
        set_lang("AR" if lang_choice else "EN")

        st.markdown(
            f"<div style='font-family:Cormorant Garamond,serif;"
            f"color:#c9a84c;font-size:1.2rem;margin-bottom:2px'>👗 Outfit</div>"
            f"<div style='color:#7a7060;font-size:.8rem'>👤 {st.session_state.email}</div>",
            unsafe_allow_html=True,
        )
        st.divider()

        st.markdown(
            "##### " + t("Date range (SWAG)","نطاق التاريخ (سواغ)")
        )
        from_date = st.date_input(
            t("From Date", "من تاريخ"),
            value=today - timedelta(days=30),
            key="from_date",
        )
        to_date = st.date_input(
            t("To Date", "إلى تاريخ"),
            value=today,
            key="to_date",
        )
        st.caption(
            t(
                "Date range is only for SWAG login (not for 3‑Odoo mirror).",
                "نطاق التاريخ فقط لتسجيل الدخول في سواغ (ليس لمرآة 3 أودو).",
            )
        )
        st.divider()

        if st.button(
            t("Logout", "تسجيل الخروج"),
            use_container_width=True,
        ):
            st.session_state.uid = None
            st.session_state.api_key = None
            st.rerun()

    page_multi_odoo_compare()


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if st.session_state.get("uid") is None:
    login_page()
else:
    dashboard()
