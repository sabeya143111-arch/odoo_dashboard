"""
SWAG Season Comparison Dashboard v5
Clean & focused:
- Auto-detect season field per system
- Season dropdown (union of all systems)
- Compare: all models in that season across all systems
- Match by Model Code first, then Product Name
- Missing company = 0 qty, 0 price (never blank)
"""

import io
import re
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import xmlrpc.client

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Season Comparison",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;1,300&family=Outfit:wght@300;400;500;600&display=swap');
*, html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }
.stApp { background: #060d0e !important; }
.block-container { padding-top: 1.5rem !important; max-width: 100% !important; }
section[data-testid="stSidebar"] { background: #060d0e !important; border-right: 1px solid rgba(74,172,180,0.1) !important; }
section[data-testid="stSidebar"] * { color: rgba(255,255,255,0.6) !important; }
[data-testid="stMetric"] { background: rgba(74,172,180,0.03); border: 1px solid rgba(74,172,180,0.08); border-radius: 6px; padding: 20px 24px; }
[data-testid="stMetricLabel"] { font-size: 8px; letter-spacing: 3px; text-transform: uppercase; color: rgba(255,255,255,0.25); }
[data-testid="stMetricValue"] { font-family: 'Cormorant Garamond', serif; font-size: 44px; font-weight: 300; color: #fff; }
.stButton button { font-size: 9px; letter-spacing: 2px; text-transform: uppercase; border-radius: 100px !important; }
.stButton button[kind="primary"] { background: #4AACB4 !important; color: #060d0e !important; border: none !important; font-weight: 600 !important; padding: 10px 28px !important; }
.stButton button[kind="secondary"] { background: transparent !important; color: rgba(74,172,180,0.6) !important; border: 1px solid rgba(74,172,180,0.2) !important; }
.hero-title { font-size: 48px; font-weight: 700; color: #fff; letter-spacing: -1px; margin-bottom: 4px; }
.hero-title em { color: #4AACB4; font-style: normal; }
.section-tag { font-size: 9px; letter-spacing: 4px; text-transform: uppercase; color: #4AACB4; margin: 24px 0 12px 0; display: flex; align-items: center; gap: 10px; }
.section-tag::before { content: ''; width: 20px; height: 1px; background: #4AACB4; }
.info-banner { background: rgba(74,172,180,0.04); border-left: 2px solid #4AACB4; padding: 10px 16px; font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase; color: rgba(74,172,180,0.7); border-radius: 0 4px 4px 0; }
</style>
""", unsafe_allow_html=True)

# ── Config ─────────────────────────────────────────────────────────────────

SYSTEM_KEYS = ["SWAG", "STOCK", "LAROUCHE", "DIFFC", "FASHIONLIMITS"]

SEASON_NAME_HINTS = [
    "season", "saison", "collection", "mawsim", "fasil",
    "موسم", "الموسم", "فصل", "كولكشن",
    "x_season", "x_collection", "x_saison", "x_mawsim",
]
ARABIC_SEASON_WORDS = ["صيفي","شتوي","ربيعي","خريفي","صيف","شتاء","ربيع","خريف","موسم","فصل"]
SEASON_CODE_PATTERNS = [
    r"\b(SS|AW|FW|SP|FA|SU|WI)\s*\d{2,4}\b",
    r"\b(S|W|F|A)\s*\d{2}\b",
    r"\b\d{2,4}\s*(SS|AW|FW|SP|FA)\b",
    r"\b(summer|winter|spring|fall|autumn)\b",
    r"\b(صيفي|شتوي|ربيعي|خريفي)\b",
]
SEASON_VALUE_RE = re.compile("|".join(SEASON_CODE_PATTERNS), re.IGNORECASE | re.UNICODE)

BLACKLIST_RELATIONS = {
    "res.users","res.partner","res.company","res.currency","res.country","res.lang","res.groups",
    "uom.uom","uom.category","account.tax","account.account","account.journal",
    "mail.activity.type","mail.template","mail.alias","ir.attachment","ir.model",
    "ir.model.fields","ir.actions.act_window","ir.ui.view","ir.ui.menu","ir.rule","ir.sequence",
    "stock.location","stock.warehouse","stock.quant",
}
USEFUL_TYPES   = {"many2one","selection","char","text","integer","float"}
SKIP_FIELDS    = {
    "__last_update","write_date","create_date","write_uid","create_uid","display_name",
    "image_1920","image_1024","image_512","image_256","image_128","image_small","image_medium",
    "message_ids","message_follower_ids","message_channel_ids","message_main_attachment_id",
    "message_has_error","message_needaction","message_attachment_count",
    "message_needaction_counter","message_has_error_counter","website_message_ids",
    "activity_ids","activity_state","activity_type_id","activity_user_id",
    "activity_summary","activity_date_deadline","activity_exception_decoration",
    "activity_exception_icon","can_image_1024_be_zoomed",
}
SKIP_PREFIXES  = ("mail_","message_","activity_","website_","image_","rating_")

# ── Helpers ────────────────────────────────────────────────────────────────

def norm(v):
    return re.sub(r"\s+"," ", str(v or "").strip()).lower()

def season_norm(v):
    return norm(v).replace("-","").replace("_","").replace("/","").replace(" ","")

def looks_season(val):
    if not val: return False
    v = str(val).strip()
    if any(w in v for w in ARABIC_SEASON_WORDS): return True
    return bool(SEASON_VALUE_RE.search(v))

def skip_field(fname, finfo):
    if fname in SKIP_FIELDS: return True
    fn = fname.lower()
    if any(fn.startswith(p) for p in SKIP_PREFIXES): return True
    if finfo.get("type","") not in USEFUL_TYPES: return True
    return False

def field_score(fname, flabel):
    score = 0
    fn, lbl = fname.lower(), (flabel or "").lower()
    for h in SEASON_NAME_HINTS:
        if h in fn:  score += 30
        if h in lbl: score += 25
    if fn.startswith("x_studio"): score += 5
    elif fn.startswith("x_"):     score += 3
    return score

def rel_score(relation):
    if not relation: return 0
    if relation in BLACKLIST_RELATIONS: return -50
    r = relation.lower()
    return 30 if any(h in r for h in SEASON_NAME_HINTS) else 0

# ── safe_domain (FIXED) ────────────────────────────────────────────────────

def safe_domain(conditions):
    result = []
    for c in conditions:
        if isinstance(c, (list, tuple)) and len(c) == 3:
            f, op, v = c
            result.append([f, op, v])
        else:
            result.append(c)
    return result

# ── Auth / RPC ─────────────────────────────────────────────────────────────

_KEY_ALIASES = {"FASHION_LIMITS": "FASHIONLIMITS"}

def get_cfg(key):
    k = _KEY_ALIASES.get(key, key)
    cfg = st.secrets.get(k) or st.secrets.get(key)
    if not cfg: return None
    cfg = dict(cfg)
    url = str(cfg.get("url","")).rstrip("/")
    if url.endswith("/odoo"): url = url[:-5]
    cfg["url"] = url
    return cfg

def sys_name(key):
    return (get_cfg(key) or {}).get("name", key)

@st.cache_resource
def _proxy(url, ep):
    return xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/{ep}", allow_none=True)

def rpc_auth(cfg):
    try:
        uid = _proxy(cfg["url"],"common").authenticate(cfg["db"], cfg["user"], cfg["api_key"], {})
        return (uid, None) if uid else (None, "Bad credentials")
    except Exception as e:
        return None, str(e)

def rpc_call(cfg, uid, model, method, domain, kw):
    return _proxy(cfg["url"],"object").execute_kw(
        cfg["db"], uid, cfg["api_key"], model, method, domain, kw)

# ── Session ────────────────────────────────────────────────────────────────

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_email    = ""

_SECRET = "swag_2025_secure"

def make_token(email):
    return hashlib.sha256(f"{_SECRET}_{email}".encode()).hexdigest()[:32]

def restore_session():
    if st.session_state.get("authenticated"): return
    try:
        p = st.query_params
        e, t = p.get("u",""), p.get("t","")
        if e and t and t == make_token(e):
            st.session_state.authenticated = True
            st.session_state.user_email    = e
    except Exception:
        pass

# ── Step 1: Auto-detect season field ──────────────────────────────────────

def detect_season_field(sys_key):
    cfg = get_cfg(sys_key)
    if not cfg:
        return {"error": "No config"}
    uid, err = rpc_auth(cfg)
    if err:
        return {"error": err}

    model = "product.template"
    try:
        meta = rpc_call(cfg, uid, model, "fields_get", [],
                        {"attributes": ["string","type","relation","store"]})
    except Exception as e:
        return {"error": f"fields_get failed: {e}"}

    candidates = []
    for fname, finfo in meta.items():
        if skip_field(fname, finfo): continue
        ftype    = finfo.get("type","")
        relation = finfo.get("relation","") or ""
        flabel   = finfo.get("string", fname)
        ns = field_score(fname, flabel)
        rs = rel_score(relation)
        total = ns + rs
        if total > 0:
            candidates.append({
                "field": fname, "label": flabel,
                "ftype": ftype, "relation": relation,
                "score": total,
            })

    if not candidates:
        return {"error": "No season-like fields found"}

    candidates.sort(key=lambda x: x["score"], reverse=True)

    for c in candidates[:5]:
        try:
            sample = rpc_call(cfg, uid, model, "search_read",
                              safe_domain([[c["field"],"!=",False]]),
                              {"fields":[c["field"]], "limit": 50})
            if sample:
                return {
                    "field":    c["field"],
                    "label":    c["label"],
                    "model":    model,
                    "ftype":    c["ftype"],
                    "relation": c["relation"],
                    "score":    c["score"],
                    "error":    None,
                }
        except Exception:
            continue

    best = candidates[0]
    return {
        "field":    best["field"],
        "label":    best["label"],
        "model":    model,
        "ftype":    best["ftype"],
        "relation": best["relation"],
        "score":    best["score"],
        "error":    None,
    }

# ── Step 2: Fetch all distinct seasons ────────────────────────────────────

def fetch_seasons(sys_key, field_info):
    cfg = get_cfg(sys_key)
    if not cfg: return []
    uid, err = rpc_auth(cfg)
    if err: return []

    model    = field_info["model"]
    field    = field_info["field"]
    ftype    = field_info["ftype"]
    relation = field_info["relation"]

    try:
        recs = rpc_call(cfg, uid, model, "search_read",
                        safe_domain([[field,"!=",False]]),
                        {"fields": [field], "limit": 100000})
        if not recs: return []

        seen = {}
        rel_ids = []
        for r in recs:
            v = r.get(field)
            if v is False or v is None: continue
            if ftype == "many2one":
                if isinstance(v, list) and len(v) >= 2:
                    seen[v[0]] = str(v[1]).strip()
                    rel_ids.append(v[0])
                elif isinstance(v, int) and v:
                    seen[v] = str(v)
                    rel_ids.append(v)
            else:
                s = str(v).strip()
                if s: seen[s] = s

        if ftype == "many2one" and relation and rel_ids:
            try:
                rel_recs = rpc_call(cfg, uid, relation, "search_read",
                                    safe_domain([["id","in",list(set(rel_ids))]]),
                                    {"fields":["id","name","display_name"],
                                     "limit": len(set(rel_ids)) + 10})
                for r in rel_recs:
                    name = r.get("display_name") or r.get("name") or str(r["id"])
                    if isinstance(name, list):
                        name = name[1] if len(name)>1 else str(name)
                    seen[r["id"]] = str(name).strip()
            except Exception:
                pass

        result = [(k, v) for k, v in seen.items() if v]
        result.sort(key=lambda x: str(x[1]))
        return result
    except Exception:
        return []

# ── Step 3: Fetch products for a season ───────────────────────────────────

def fetch_products_for_season(sys_key, field_info, stored_value):
    cfg = get_cfg(sys_key)
    if not cfg: return pd.DataFrame()
    uid, err = rpc_auth(cfg)
    if err: return pd.DataFrame()

    model = field_info["model"]
    field = field_info["field"]

    try:
        tmpl_recs = rpc_call(cfg, uid, model, "search_read",
                             safe_domain([[field,"=",stored_value]]),
                             {"fields":["id"], "limit": 100000})
        if not tmpl_recs: return pd.DataFrame()

        tmpl_ids = [r["id"] for r in tmpl_recs]
        all_prods = []
        batch_size = 100

        for i in range(0, len(tmpl_ids), batch_size):
            batch = tmpl_ids[i:i+batch_size]
            try:
                prods = rpc_call(cfg, uid, "product.product", "search_read",
                                 safe_domain([["product_tmpl_id","in",batch]]),
                                 {"fields":["default_code","name","display_name",
                                            "qty_available","list_price"],
                                  "limit": 100000})
                if prods:
                    all_prods.extend(prods)
            except Exception:
                # GS1 addon fallback: read from template
                try:
                    tmpls = rpc_call(cfg, uid, "product.template", "search_read",
                                     safe_domain([["id","in",batch]]),
                                     {"fields":["default_code","name",
                                                "qty_available","list_price"],
                                      "limit": 100000})
                    if tmpls:
                        all_prods.extend(tmpls)
                except Exception:
                    pass

        if not all_prods: return pd.DataFrame()

        rows = []
        for p in all_prods:
            code  = str(p.get("default_code") or "").strip()
            name  = str(p.get("display_name") or p.get("name") or "").strip()
            qty   = float(p.get("qty_available") or 0)
            price = float(p.get("list_price") or 0)
            if not code and not name: continue
            rows.append({"Model Code": code, "Product Name": name,
                         "Qty": qty, "Price": price})

        if not rows: return pd.DataFrame()
        df = pd.DataFrame(rows)
        df = df.groupby(["Model Code","Product Name"], as_index=False).agg(
            {"Qty":"sum", "Price":"max"})
        return df
    except Exception:
        return pd.DataFrame()

# ── Step 4: Build comparison matrix ───────────────────────────────────────

def build_matrix(season_label, systems_info):
    system_dfs = {}

    def _fetch_one(sys_key):
        info = systems_info.get(sys_key)
        if not info: return sys_key, pd.DataFrame()
        stored = None
        n_target = season_norm(season_label)
        for val, lbl in info["seasons"]:
            if lbl == season_label or season_norm(lbl) == n_target:
                stored = val; break
        if stored is None:
            for val, lbl in info["seasons"]:
                if n_target in season_norm(lbl) or season_norm(lbl) in n_target:
                    stored = val; break
        if stored is None: return sys_key, pd.DataFrame()
        df = fetch_products_for_season(sys_key, info["field_info"], stored)
        return sys_key, df

    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(_fetch_one, k): k for k in systems_info}
        for fut in as_completed(futures):
            try:
                k, df = fut.result()
                if not df.empty:
                    system_dfs[k] = df
            except Exception:
                pass

    if not system_dfs:
        return pd.DataFrame()

    # Build unified key set
    all_codes    = set()
    code_to_name = {}
    all_names    = set()

    for df in system_dfs.values():
        for _, row in df.iterrows():
            code = row["Model Code"]
            name = row["Product Name"]
            if code:
                all_codes.add(code)
                if code not in code_to_name and name:
                    code_to_name[code] = name
            elif name:
                all_names.add(name)

    all_keys = sorted(all_codes) + sorted(all_names - all_codes)

    result_rows = []
    for key in all_keys:
        row = {
            "Model Code":   key if key in all_codes else "",
            "Product Name": code_to_name.get(key, key if key in all_names else ""),
        }
        for sk in SYSTEM_KEYS:
            df = system_dfs.get(sk, pd.DataFrame())
            qty, price = 0, 0.0
            if not df.empty:
                match = df[df["Model Code"] == key] if key in all_codes else pd.DataFrame()
                if match.empty and key in all_names:
                    match = df[df["Product Name"] == key]
                if not match.empty:
                    qty   = int(match["Qty"].sum())
                    price = float(match["Price"].max())
            row[f"{sk} Qty"]   = qty
            row[f"{sk} Price"] = round(price, 2)

        row["Total Qty"] = sum(row.get(f"{k} Qty", 0) for k in SYSTEM_KEYS)
        result_rows.append(row)

    df_out = pd.DataFrame(result_rows)
    cols = ["Model Code","Product Name"]
    for k in SYSTEM_KEYS:
        cols += [f"{k} Qty", f"{k} Price"]
    cols.append("Total Qty")
    df_out = df_out[[c for c in cols if c in df_out.columns]]
    df_out = df_out.sort_values(["Total Qty","Model Code"], ascending=[False,True]).reset_index(drop=True)
    return df_out

# ── Excel Export ───────────────────────────────────────────────────────────

def export_excel(df, season_name):
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Season Comparison")
        ws = writer.sheets["Season Comparison"]

        hdr_fill  = PatternFill("solid", fgColor="060D0E")
        hdr_font  = Font(bold=True, color="4AACB4", size=11, name="Calibri")
        alt_fill  = PatternFill("solid", fgColor="0D1A1C")
        norm_font = Font(name="Calibri", size=10, color="8AACB0")
        tot_font  = Font(bold=True, name="Calibri", color="D4A84B")
        tot_fill  = PatternFill("solid", fgColor="060D0E")
        thin      = Side(border_style="thin", color="1A2A2C")
        border    = Border(left=thin, right=thin, top=thin, bottom=thin)
        c_align   = Alignment(horizontal="center", vertical="center")
        r_align   = Alignment(horizontal="right",  vertical="center")

        max_row = ws.max_row
        max_col = ws.max_column
        ws.row_dimensions[1].height = 30

        for col in range(1, max_col+1):
            cell = ws.cell(row=1, column=col)
            cell.fill = hdr_fill; cell.font = hdr_font
            cell.alignment = c_align; cell.border = border

        for row in ws.iter_rows(min_row=2, max_row=max_row):
            for cell in row:
                cell.border = border; cell.font = norm_font
                if cell.row % 2 == 0: cell.fill = alt_fill
                cell.alignment = r_align if isinstance(cell.value,(int,float)) else c_align
            ws.row_dimensions[row[0].row].height = 18

        for col in range(1, max_col+1):
            cl = get_column_letter(col)
            ml = max((len(str(ws.cell(row=r,column=col).value or ""))
                      for r in range(1,max_row+1)), default=8)
            ws.column_dimensions[cl].width = min(max(ml+3,10),40)

        ws.freeze_panes = "C2"
        ws.auto_filter.ref = f"A1:{get_column_letter(max_col)}{max_row}"

        tr = max_row + 1
        tc = ws.cell(row=tr, column=1, value="TOTAL")
        tc.font = tot_font; tc.fill = tot_fill; tc.alignment = c_align
        for ci, cn in enumerate(df.columns, 1):
            if "Qty" in cn or "Price" in cn:
                cl = get_column_letter(ci)
                c = ws.cell(row=tr, column=ci,
                            value=f"=SUM({cl}2:{cl}{max_row})")
                c.font = tot_font; c.fill = tot_fill; c.alignment = r_align

        ws.sheet_properties.tabColor = "4AACB4"
        ws.cell(row=tr+2, column=1,
                value=f"Generated: {datetime.now():%Y-%m-%d %H:%M}  |  Season: {season_name}"
               ).font = Font(italic=True, color="4AACB4", size=9, name="Calibri")

    return buf.getvalue()

# ── Login / Logout ─────────────────────────────────────────────────────────

def show_login():
    st.markdown("<div class='hero-title'>Season <em>Comparison</em></div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    with st.form("login"):
        email    = st.text_input("Email", placeholder="you@company.com")
        password = st.text_input("Password", type="password")
        submit   = st.form_submit_button("Sign In", type="primary", use_container_width=True)
    if submit:
        if not email or not password:
            st.error("Fill both fields.")
            return
        if "LOGIN" not in st.secrets:
            st.error("No LOGIN config in secrets.")
            return
        cfg = dict(st.secrets["LOGIN"])
        url = str(cfg.get("url","")).rstrip("/")
        if url.endswith("/odoo"): url = url[:-5]
        try:
            uid = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common", allow_none=True)\
                      .authenticate(cfg["db"], email, password, {})
            if uid:
                st.query_params["u"] = email
                st.query_params["t"] = make_token(email)
                st.session_state.authenticated = True
                st.session_state.user_email    = email
                st.rerun()
            else:
                st.error("Wrong email or password.")
        except Exception as e:
            st.error(f"Connection error: {e}")

def do_logout():
    try: st.query_params.clear()
    except Exception: pass
    st.session_state.authenticated = False
    st.session_state.user_email    = ""
    for k in ["systems_info","season_matrix","season_name"]:
        st.session_state.pop(k, None)
    st.rerun()

# ── Main Dashboard ─────────────────────────────────────────────────────────

def show_dashboard():
    with st.sidebar:
        st.markdown("### 🌾 SWAG")
        st.caption(st.session_state.user_email)
        st.divider()
        if st.button("Logout", use_container_width=True, type="secondary"):
            do_logout()

        if st.session_state.get("systems_info"):
            st.divider()
            st.markdown("**Detected Season Fields**")
            for k in SYSTEM_KEYS:
                info = st.session_state["systems_info"].get(k)
                if info:
                    fi = info["field_info"]
                    st.markdown(
                        f"<span style='color:#4AACB4;font-size:10px'>✓ {sys_name(k)}</span><br>"
                        f"<small style='color:rgba(255,255,255,0.3)'>`{fi['field']}` · {len(info['seasons'])} seasons</small>",
                        unsafe_allow_html=True)
                else:
                    st.markdown(
                        f"<span style='color:rgba(255,100,100,0.6);font-size:10px'>✗ {sys_name(k)}</span>",
                        unsafe_allow_html=True)
                st.markdown("")

    st.markdown("<div class='hero-title'>Season <em>Comparison</em></div>", unsafe_allow_html=True)
    st.markdown("<p style='color:rgba(255,255,255,0.3);font-size:13px;margin-bottom:0'>Compare stock & price across all systems for any season</p>", unsafe_allow_html=True)

    # ── STEP 1: Discover ──────────────────────────────────────────────────
    st.markdown("<div class='section-tag'>Step 1 — Connect & Discover</div>", unsafe_allow_html=True)

    c1, c2 = st.columns([1,4])
    with c1:
        do_discover = st.button("🔍  Discover Seasons", type="primary", use_container_width=True)
    with c2:
        st.markdown(
            "<div class='info-banner'>Auto-detects the season field in each system and loads all available season values.</div>",
            unsafe_allow_html=True)

    if do_discover:
        systems_info = {}
        progress = st.progress(0, text="Connecting to systems...")
        total = len(SYSTEM_KEYS)

        for i, sk in enumerate(SYSTEM_KEYS):
            progress.progress(i/total, text=f"Scanning {sys_name(sk)}...")
            fi = detect_season_field(sk)
            if fi.get("error"):
                continue
            seasons = fetch_seasons(sk, fi)
            if seasons:
                systems_info[sk] = {"field_info": fi, "seasons": seasons}

        progress.progress(1.0, text="Done!")
        st.session_state["systems_info"] = systems_info
        for k in ["season_matrix","season_name"]:
            st.session_state.pop(k, None)
        st.rerun()

    # System status cards
    systems_info = st.session_state.get("systems_info")
    if systems_info is not None:
        cols = st.columns(len(SYSTEM_KEYS))
        for i, sk in enumerate(SYSTEM_KEYS):
            with cols[i]:
                info = systems_info.get(sk)
                if info:
                    fi = info["field_info"]
                    st.markdown(
                        f"<div style='background:rgba(74,172,180,0.05);border:1px solid rgba(74,172,180,0.15);"
                        f"border-radius:8px;padding:14px;text-align:center'>"
                        f"<div style='color:#4AACB4;font-size:10px;letter-spacing:2px;text-transform:uppercase'>{sys_name(sk)}</div>"
                        f"<div style='color:#fff;font-size:28px;font-weight:700;margin:6px 0'>{len(info['seasons'])}</div>"
                        f"<div style='color:rgba(255,255,255,0.3);font-size:9px'>seasons found</div>"
                        f"<div style='color:rgba(74,172,180,0.4);font-size:8px;margin-top:6px;word-break:break-all'>{fi['field']}</div>"
                        f"</div>",
                        unsafe_allow_html=True)
                else:
                    st.markdown(
                        f"<div style='background:rgba(255,80,80,0.03);border:1px solid rgba(255,80,80,0.1);"
                        f"border-radius:8px;padding:14px;text-align:center'>"
                        f"<div style='color:rgba(255,100,100,0.6);font-size:10px;letter-spacing:2px;text-transform:uppercase'>{sys_name(sk)}</div>"
                        f"<div style='color:rgba(255,100,100,0.3);font-size:22px;margin-top:8px'>—</div>"
                        f"<div style='color:rgba(255,100,100,0.3);font-size:9px'>not connected</div>"
                        f"</div>",
                        unsafe_allow_html=True)

    # ── STEP 2: Select & Compare ──────────────────────────────────────────
    if systems_info:
        st.markdown("<div class='section-tag'>Step 2 — Select Season & Compare</div>", unsafe_allow_html=True)

        all_seasons = sorted({
            lbl
            for info in systems_info.values()
            for _, lbl in info["seasons"]
        })

        if not all_seasons:
            st.warning("No season values found. Try re-running discovery.")
        else:
            col_sel, col_btn = st.columns([3,1])
            with col_sel:
                selected = st.selectbox(
                    "Choose a Season",
                    all_seasons,
                    key="season_select",
                    help=f"{len(all_seasons)} total seasons across all systems"
                )
            with col_btn:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                do_compare = st.button("▶  Compare", type="primary", use_container_width=True)

            # Which systems have this season?
            has, missing = [], []
            for sk in SYSTEM_KEYS:
                info = systems_info.get(sk)
                if not info: missing.append(sk); continue
                n_t = season_norm(selected)
                found = any(
                    season_norm(lbl) == n_t or n_t in season_norm(lbl)
                    for _, lbl in info["seasons"]
                )
                (has if found else missing).append(sk)

            parts = []
            if has:
                parts.append("**In:** " + " · ".join(
                    f"<span style='color:#4AACB4'>{sys_name(k)}</span>" for k in has))
            if missing:
                parts.append("**Not found in:** " + " · ".join(
                    f"<span style='color:rgba(255,100,100,0.5)'>{sys_name(k)}</span>" for k in missing))
            if parts:
                st.markdown("  |  ".join(parts), unsafe_allow_html=True)

            if do_compare:
                with st.spinner(f"Fetching products for **{selected}**..."):
                    df_matrix = build_matrix(selected, systems_info)

                if df_matrix.empty:
                    st.error("No products found for this season across any system.")
                else:
                    st.session_state["season_matrix"] = df_matrix
                    st.session_state["season_name"]   = selected
                    st.rerun()

    # ── STEP 3: Results ───────────────────────────────────────────────────
    if "season_matrix" in st.session_state:
        df          = st.session_state["season_matrix"]
        season_name = st.session_state["season_name"]

        st.markdown(
            f"<div class='section-tag'>Results — {season_name}</div>",
            unsafe_allow_html=True)

        # Metrics
        metric_cols = st.columns(2 + len(SYSTEM_KEYS))
        metric_cols[0].metric("Total Models",   f"{len(df):,}")
        metric_cols[1].metric("Total Units",    f"{int(df['Total Qty'].sum()):,}")
        for i, sk in enumerate(SYSTEM_KEYS):
            qc = f"{sk} Qty"
            if qc in df.columns:
                metric_cols[i+2].metric(sys_name(sk), f"{int(df[qc].sum()):,}")

        # Table
        col_cfg = {}
        for k in SYSTEM_KEYS:
            if f"{k} Qty"   in df.columns:
                col_cfg[f"{k} Qty"]   = st.column_config.NumberColumn(f"{sys_name(k)} Qty",   format="%d")
            if f"{k} Price" in df.columns:
                col_cfg[f"{k} Price"] = st.column_config.NumberColumn(f"{sys_name(k)} Price", format="%.2f")
        if "Total Qty" in df.columns:
            col_cfg["Total Qty"] = st.column_config.NumberColumn("Total Qty", format="%d")

        st.dataframe(
            df,
            use_container_width=True,
            height=min(650, 60 + len(df)*36),
            column_config=col_cfg,
        )

        # Actions
        c_dl, c_clr = st.columns([2,1])
        with c_dl:
            st.download_button(
                label="⬇  Download Excel",
                data=export_excel(df, season_name),
                file_name=f"season_{season_name}_{datetime.now():%Y%m%d_%H%M}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
            )
        with c_clr:
            if st.button("✕  Clear Results", type="secondary"):
                for k in ["season_matrix","season_name"]:
                    st.session_state.pop(k, None)
                st.rerun()

# ── Entry ──────────────────────────────────────────────────────────────────

restore_session()
if not st.session_state.authenticated:
    show_login()
else:
    show_dashboard()
