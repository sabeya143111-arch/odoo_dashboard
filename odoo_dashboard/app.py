"""
SWAG Season Comparison Dashboard v10
================================================================================
What changed vs v9 (the important stuff):

1. CORRECT QUANTITY — now from stock.quant over ALL internal locations
   (exactly like the main product dashboard). No more reliance on
   qty_available, which only saw the API user's default warehouse and
   was reading 0 for stock held in other branches.

2. TWO VIEWS:
   - Company view  -> qty per system (sum of all its branches)
   - Branch view   -> qty per "System | Branch" (every location as a column)

3. FULL COVERAGE:
   - Every season of the chosen type, across every company (read_group).
   - Every model in the season is shown — even with 0 stock (no silent drops).
   - Optional "Include archived" so discontinued-but-stocked items appear too.

4. EXTRA FEATURES:
   - Only-differences filter (rows where systems disagree).
   - In-table model/product search.
   - Stock value per system (qty x price).
   - Missing-products + price-gap alerts.
   - Limit-hit / coverage diagnostics.
================================================================================
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
* , html , body , [class*="css"] { font-family: 'Outfit', sans-serif; }
.stApp { background: #060d0e !important; }
.block-container { padding-top: 1rem !important; max-width: 100% !important; }
section[data-testid="stSidebar"] { background: #060d0e !important; border-right: 1px solid rgba(74,172,180,0.1) !important; }
section[data-testid="stSidebar"] * { color: rgba(255,255,255,0.6) !important; }
[data-testid="stMetric"] { background: rgba(74,172,180,0.03); border: 1px solid rgba(74,172,180,0.08); border-radius: 4px; padding: 20px 24px; }
[data-testid="stMetricLabel"] { font-size: 8px; letter-spacing: 3px; text-transform: uppercase; color: rgba(255,255,255,0.25); }
[data-testid="stMetricValue"] { font-family: 'Cormorant Garamond', serif; font-size: 40px; font-weight: 300; color: #fff; }
.stButton button { font-size: 9px; letter-spacing: 2px; text-transform: uppercase; border-radius: 100px !important; }
.stButton button[kind="primary"] { background: #4AACB4 !important; color: #060d0e !important; border: none !important; font-weight: 600 !important; padding: 10px 28px !important; }
.stButton button[kind="secondary"] { background: transparent !important; color: rgba(74,172,180,0.6) !important; border: 1px solid rgba(74,172,180,0.2) !important; }
.info-banner { background: rgba(74,172,180,0.04); border-left: 2px solid #4AACB4; padding: 10px 16px; font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase; color: rgba(74,172,180,0.7); margin-bottom: 8px; }
.hero-title { font-size: 48px; font-weight: 700; color: #fff; letter-spacing: -1px; margin-bottom: 0; }
.hero-title em { color: #4AACB4; font-style: normal; }
.section-tag { font-size: 9px; letter-spacing: 4px; text-transform: uppercase; color: #4AACB4; margin: 20px 0 12px 0; display: flex; align-items: center; gap: 10px; }
.section-tag::before { content: ''; width: 20px; height: 1px; background: #4AACB4; }
.alert-missing { background: rgba(255,80,80,0.06); border-left: 2px solid #ff5050; padding: 10px 16px; font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase; color: rgba(255,80,80,0.8); margin-bottom: 8px; }
.alert-price { background: rgba(255,180,0,0.06); border-left: 2px solid #ffb400; padding: 10px 16px; font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase; color: rgba(255,180,0,0.8); margin-bottom: 8px; }
.season-match-box { background: rgba(74,172,180,0.04); border: 1px solid rgba(74,172,180,0.12); border-radius: 6px; padding: 12px 16px; margin-bottom: 12px; }
.season-match-sys { font-size: 8px; letter-spacing: 2px; text-transform: uppercase; color: rgba(74,172,180,0.5); margin-bottom: 4px; }
.season-match-label { font-size: 13px; color: #fff; font-weight: 500; }
</style>
""", unsafe_allow_html=True)

SYSTEM_KEYS = ["SWAG", "STOCK", "LAROUCHE", "DIFFC", "FASHIONLIMITS"]

SEASON_NAME_HINTS = [
    "season", "saison", "collection", "mawsim", "fasil",
    "موسم", "الموسم", "فصل", "كولكشن",
    "x_season", "x_collection", "x_saison", "x_mawsim",
]

ARABIC_SEASON_WORDS = [
    "صيفي", "شتوي", "ربيعي", "خريفي",
    "صيف", "شتاء", "ربيع", "خريف",
    "موسم", "فصل",
]

SEASON_CODE_PATTERNS = [
    r"\b(SS|AW|FW|SP|FA|SU|WI)\s*\d{2,4}\b",
    r"\b(S|W|F|A)\s*\d{2}\b",
    r"\b\d{2,4}\s*(SS|AW|FW|SP|FA)\b",
    r"\b(summer|winter|spring|fall|autumn)\b",
    r"\b(صيفي|شتوي|ربيعي|خريفي)\b",
    r"\b(صيفي|شتوي|ربيعي|خريفي)\s*\d{1,2}\b",
    r"\b\d{2,4}\s*(صيفي|شتوي|ربيعي|خريفي)\b",
]
SEASON_VALUE_RE = re.compile("|".join(SEASON_CODE_PATTERNS), re.IGNORECASE | re.UNICODE)

BLACKLIST_RELATION_MODELS = {
    "res.users", "res.partner", "res.company", "res.currency",
    "res.country", "res.lang", "res.groups",
    "uom.uom", "uom.category",
    "account.tax", "account.account", "account.journal",
    "mail.activity.type", "mail.template", "mail.alias",
    "ir.attachment", "ir.model", "ir.model.fields",
    "ir.actions.act_window", "ir.ui.view", "ir.ui.menu",
    "ir.rule", "ir.sequence",
    "stock.location", "stock.warehouse", "stock.quant",
}

USEFUL_FIELD_TYPES = {"many2one", "selection", "char", "text", "integer", "float"}

ALWAYS_SKIP_FIELDS = {
    "__last_update", "write_date", "create_date", "write_uid", "create_uid",
    "display_name", "image_1920", "image_1024", "image_512", "image_256",
    "image_128", "image_small", "image_medium",
    "message_ids", "message_follower_ids", "message_channel_ids",
    "message_main_attachment_id", "message_has_error",
    "message_needaction", "message_attachment_count",
    "message_needaction_counter", "message_has_error_counter",
    "website_message_ids", "activity_ids", "activity_state", "activity_type_id",
    "activity_user_id", "activity_summary", "activity_date_deadline",
    "activity_exception_decoration", "activity_exception_icon",
    "can_image_1024_be_zoomed",
}

ALWAYS_SKIP_PREFIXES = ("mail_", "message_", "activity_", "website_", "image_", "rating_")

AUDIT_SAMPLE_LIMIT = 300
RELATION_SAMPLE_LIMIT = 20
TEMPLATE_FETCH_LIMIT = 50000
PRODUCT_FETCH_LIMIT = 200000
QUANT_FETCH_LIMIT = 200000
PID_CHUNK = 1000

PRICE_DIFF_THRESHOLD_PCT = 10.0

# A clean season field has only a handful of distinct values (e.g. 5-20).
# If a detected field has more than this, it is almost certainly category /
# product-name data (not a real season field) and is rejected so it does not
# pull the whole catalog and blow up memory.
MAX_SEASON_DISTINCT = 80
# Defensive caps for heavy rendering / export on huge result sets.
MAX_BRANCH_COLS = 120
HEAVY_COMPUTE_ROW_CAP = 8000


def normalize_text(v):
    return re.sub(r"\s+", " ", str(v or "").strip()).lower()


def season_norm(v):
    s = normalize_text(v)
    return s.replace("-", "").replace("_", "").replace("/", "").replace(" ", "")


SEASON_TYPE_HINTS = [
    (("صيفي", "صيف", "summer", "ss", "su"), "SUMMER"),
    (("شتوي", "شتاء", "winter", "aw", "fw", "wi"), "WINTER"),
    (("ربيعي", "ربيع", "spring", "sp"), "SPRING"),
    (("خريفي", "خريف", "fall", "autumn", "fa"), "FALL"),
]

SEASON_TYPE_LABEL = {
    "SUMMER": "Summer / صيفي",
    "WINTER": "Winter / شتوي",
    "SPRING": "Spring / ربيعي",
    "FALL": "Fall / خريفي",
}


def season_type_only(label):
    s = normalize_text(label)
    for words, canon in SEASON_TYPE_HINTS:
        for w in words:
            if len(w) <= 2:
                if re.search(rf"\b{re.escape(w)}\b", s):
                    return canon
            elif w in s:
                return canon
    return None


def season_year(label):
    nums = re.findall(r"\d+", str(label or ""))
    if not nums:
        return ""
    n = nums[-1]
    if len(n) >= 4:
        return n[:4]
    if len(n) == 2:
        return "20" + n
    if len(n) == 1:
        return "200" + n
    return n


def season_signature(label):
    stype = season_type_only(label)
    if not stype:
        return None
    yr = season_year(label)
    return stype + (yr[-2:] if yr else "")


def should_skip_field(field_name, field_info):
    fn = field_name.lower()
    if field_name in ALWAYS_SKIP_FIELDS:
        return True
    for prefix in ALWAYS_SKIP_PREFIXES:
        if fn.startswith(prefix):
            return True
    if field_info.get("type", "") not in USEFUL_FIELD_TYPES:
        return True
    return False


def looks_like_season_value(val_str):
    if not val_str:
        return False
    val = str(val_str).strip()
    if any(word in val for word in ARABIC_SEASON_WORDS):
        return True
    return bool(SEASON_VALUE_RE.search(val))


def score_field_name(field_name, field_label):
    score = 0
    fn = field_name.lower()
    lbl = (field_label or "").lower()
    for hint in SEASON_NAME_HINTS:
        if hint in fn:
            score += 30
        if hint in lbl:
            score += 25
    if fn.startswith("x_studio"):
        score += 5
    elif fn.startswith("x_"):
        score += 3
    return score


def score_relation_model(relation):
    if not relation:
        return 0
    if relation in BLACKLIST_RELATION_MODELS:
        return -50
    rel = relation.lower()
    for hint in SEASON_NAME_HINTS:
        if hint in rel:
            return 30
    return 0


def safe_domain(conditions):
    result = []
    for c in conditions:
        if isinstance(c, (list, tuple)) and len(c) == 3:
            field, op, val = c
            result.append([field, op, val])
        else:
            result.append(c)
    return result


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_email = ""

_COOKIE_SECRET = "swag_2025_secure"


def _make_token(email):
    return hashlib.sha256(f"{_COOKIE_SECRET}_{email}".encode()).hexdigest()[:32]


def _verify_token(email, token):
    return bool(email and token and token == _make_token(email))


def restore_session():
    if st.session_state.get("authenticated"):
        return
    try:
        params = st.query_params
        email = params.get("u", "")
        token = params.get("t", "")
        if email and token and _verify_token(email, token):
            st.session_state.authenticated = True
            st.session_state.user_email = email
    except Exception:
        pass


_KEY_ALIASES = {"FASHION_LIMITS": "FASHIONLIMITS", "FASHIONLIMITS": "FASHIONLIMITS"}


def _canonical_key(key):
    return _KEY_ALIASES.get(key, key)


def get_system_config(key):
    canonical = _canonical_key(key)
    cfg = st.secrets.get(canonical) or st.secrets.get(key)
    if not cfg:
        return None
    cfg = dict(cfg)
    url = str(cfg.get("url", "")).rstrip("/")
    if url.endswith("/odoo"):
        url = url[:-5]
    cfg["url"] = url
    return cfg


def get_system_name(key):
    cfg = get_system_config(key) or {}
    return cfg.get("name", key)


@st.cache_resource
def _proxy(url, ep):
    return xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/{ep}", allow_none=True)


@st.cache_data(ttl=28800, show_spinner=False)
def _auth(url, db, user, api_key):
    try:
        uid = _proxy(url, "common").authenticate(db, user, api_key, {})
        if uid:
            return {"ok": True, "uid": uid}
        return {"ok": False, "error": "BAD_CREDENTIALS"}
    except Exception as e:
        return {"ok": False, "error": f"AUTH_EXCEPTION: {e}"}


def _execute(url, db, uid, api_key, model, method, domain, kw):
    return _proxy(url, "object").execute_kw(db, uid, api_key, model, method, [domain], kw)


def _read_group(url, db, uid, api_key, model, domain, fields, groupby, kw=None):
    kw = kw or {}
    return _proxy(url, "object").execute_kw(
        db, uid, api_key, model, "read_group", [domain, fields, groupby], kw
    )


@st.cache_data(ttl=3600, show_spinner=False)
def get_internal_locations(system_key):
    """{location_id: location_name} for all internal, active locations.
    This is what makes the quantity correct across every branch."""
    cfg = get_system_config(system_key)
    if not cfg:
        return {}
    auth = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth["ok"]:
        return {}
    uid = auth["uid"]
    url, db, api_key = cfg["url"], cfg["db"], cfg["api_key"]
    try:
        locs = _execute(url, db, uid, api_key, "stock.location", "search_read",
                        safe_domain([["usage", "=", "internal"], ["active", "=", True]]),
                        {"fields": ["id", "complete_name", "display_name", "name"],
                         "limit": 10000})
        out = {}
        for l in locs or []:
            nm = l.get("complete_name") or l.get("display_name") or l.get("name") or str(l["id"])
            if isinstance(nm, list):
                nm = nm[1] if len(nm) > 1 else str(nm)
            out[l["id"]] = str(nm).strip()
        return out
    except Exception:
        return {}


def get_stock_context(cfg, include_archived=False):
    ctx = {}
    if include_archived:
        ctx["active_test"] = False
    if not cfg:
        return ctx
    try:
        if cfg.get("company_id"):
            cid = int(cfg["company_id"])
            ctx["allowed_company_ids"] = [cid]
            ctx["force_company"] = cid
    except Exception:
        pass
    return ctx


def browse_fields_for_system(system_key):
    cfg = get_system_config(system_key)
    if not cfg:
        return None, "No config"
    auth = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth["ok"]:
        return None, auth["error"]
    uid = auth["uid"]
    url, db, api_key = cfg["url"], cfg["db"], cfg["api_key"]
    rows = []
    for model in ["product.template"]:
        try:
            fields_meta = _execute(url, db, uid, api_key, model, "fields_get", [],
                                   {"attributes": ["string", "type", "relation", "store"]})
        except Exception:
            continue
        for fname, finfo in fields_meta.items():
            if should_skip_field(fname, finfo):
                continue
            rows.append({
                "Model": model, "Field": fname,
                "Label": finfo.get("string", fname),
                "Type": finfo.get("type", ""),
                "Relation": finfo.get("relation", "") or "",
                "Name Score": score_field_name(fname, finfo.get("string", fname)),
                "Rel Score": score_relation_model(finfo.get("relation", "") or ""),
            })
    if not rows:
        return None, "No eligible fields found"
    df = pd.DataFrame(rows)
    df["Total Score"] = df["Name Score"] + df["Rel Score"]
    return df.sort_values("Total Score", ascending=False).reset_index(drop=True), None


def _probe_relation_model(url, db, uid, api_key, relation_model, related_ids):
    result = {"sample_names": [], "season_like_count": 0, "total_fetched": 0, "error": None}
    if not related_ids or not relation_model:
        return result
    unique_ids = list({i for i in related_ids if isinstance(i, int)})[:RELATION_SAMPLE_LIMIT]
    if not unique_ids:
        return result
    try:
        recs = _execute(url, db, uid, api_key, relation_model, "search_read",
                        safe_domain([["id", "in", unique_ids]]),
                        {"fields": ["id", "name", "display_name"], "limit": RELATION_SAMPLE_LIMIT})
        result["total_fetched"] = len(recs)
        for rec in recs:
            name = rec.get("display_name") or rec.get("name") or ""
            if isinstance(name, list):
                name = name[1] if len(name) > 1 else str(name)
            name = str(name).strip()
            if name:
                result["sample_names"].append(name)
                if looks_like_season_value(name):
                    result["season_like_count"] += 1
    except Exception as e:
        result["error"] = str(e)
    return result


def deep_season_audit_for_system(system_key):
    audit = {
        "system": system_key, "status": "pending", "error": None,
        "candidates": [], "best_field": None, "confident": False,
        "manual_pick_needed": False, "raw_field_count": 0,
        "eligible_field_count": 0, "sample_ids_loaded": 0,
        "product_records_loaded": 0, "fetch_errors": [],
    }
    cfg = get_system_config(system_key)
    if not cfg:
        audit["status"] = "no_config"; audit["error"] = "No configuration found in secrets."
        return audit
    auth_res = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth_res["ok"]:
        audit["status"] = "auth_failed"; audit["error"] = auth_res.get("error", "Authentication failed")
        return audit
    uid = auth_res["uid"]
    url, db, api_key = cfg["url"], cfg["db"], cfg["api_key"]
    candidates = []
    for model in ["product.template"]:
        try:
            fields_meta = _execute(url, db, uid, api_key, model, "fields_get", [],
                                   {"attributes": ["string", "type", "relation", "store"]})
        except Exception as e:
            audit["fetch_errors"].append(f"fields_get/{model}: {e}")
            continue
        audit["raw_field_count"] += len(fields_meta)
        eligible_fields = {fn: fi for fn, fi in fields_meta.items() if not should_skip_field(fn, fi)}
        audit["eligible_field_count"] += len(eligible_fields)
        if not eligible_fields:
            continue
        sample_ids = []
        for domain_attempt in [[], [[1, "=", 1]]]:
            try:
                sample_recs = _execute(url, db, uid, api_key, model, "search_read",
                                       domain_attempt, {"fields": ["id"], "limit": AUDIT_SAMPLE_LIMIT})
                if sample_recs:
                    sample_ids = [r["id"] for r in sample_recs]
                    break
            except Exception as e:
                audit["fetch_errors"].append(f"search_ids/{model}: {e}")
        audit["sample_ids_loaded"] += len(sample_ids)
        product_records = []
        if sample_ids:
            field_list = list(eligible_fields.keys())
            fetched_recs = {}
            for i in range(0, len(field_list), 60):
                chunk_fields = field_list[i:i + 60]
                try:
                    recs = _execute(url, db, uid, api_key, model, "search_read",
                                    safe_domain([["id", "in", sample_ids]]),
                                    {"fields": chunk_fields, "limit": AUDIT_SAMPLE_LIMIT})
                    for rec in recs:
                        fetched_recs.setdefault(rec["id"], {}).update(rec)
                except Exception as e:
                    audit["fetch_errors"].append(f"search_read/{model}/chunk{i}: {e}")
            product_records = list(fetched_recs.values())
            audit["product_records_loaded"] += len(product_records)
        for fname, finfo in eligible_fields.items():
            ftype = finfo.get("type", "")
            relation = finfo.get("relation", "") or ""
            flabel = finfo.get("string", fname)
            name_score = score_field_name(fname, flabel)
            rel_score = score_relation_model(relation)
            candidate = {
                "field_name": fname, "field_label": flabel, "model": model,
                "field_type": ftype, "relation_model": relation,
                "name_score": name_score, "relation_model_score": rel_score,
                "data_score": 0, "total_score": 0, "non_empty_count": 0,
                "sample_raw_values": [], "season_like_direct_count": 0,
                "relation_probe": None, "rejection_reason": None,
            }
            if relation and relation in BLACKLIST_RELATION_MODELS:
                candidate["rejection_reason"] = f"Blacklisted relation: {relation}"
                candidate["total_score"] = name_score + rel_score
                candidates.append(candidate); continue
            if not product_records:
                candidate["rejection_reason"] = "No product records loaded (name-only score)"
                candidate["total_score"] = name_score + rel_score
                candidates.append(candidate); continue
            related_ids_seen = []
            for rec in product_records:
                val = rec.get(fname)
                if val is False or val is None:
                    continue
                if ftype == "many2one":
                    if isinstance(val, list) and len(val) >= 2:
                        related_ids_seen.append(val[0]); display = str(val[1])
                    elif isinstance(val, int) and val:
                        related_ids_seen.append(val); display = str(val)
                    else:
                        continue
                else:
                    display = str(val).strip()
                    if not display:
                        continue
                candidate["non_empty_count"] += 1
                if len(candidate["sample_raw_values"]) < 10:
                    candidate["sample_raw_values"].append(display)
                if looks_like_season_value(display):
                    candidate["season_like_direct_count"] += 1
            if candidate["non_empty_count"] == 0:
                candidate["rejection_reason"] = "No non-empty values in sample"
                candidate["total_score"] = name_score + rel_score
                candidates.append(candidate); continue
            if ftype == "many2one" and relation and related_ids_seen:
                probe = _probe_relation_model(url, db, uid, api_key, relation, related_ids_seen)
                candidate["relation_probe"] = probe
                candidate["season_like_direct_count"] += probe.get("season_like_count", 0)
                for rname in probe.get("sample_names", []):
                    if len(candidate["sample_raw_values"]) < 10:
                        candidate["sample_raw_values"].append("[rel] " + rname)
            ratio = candidate["season_like_direct_count"] / max(candidate["non_empty_count"], 1)
            candidate["data_score"] = ratio * 50
            candidate["total_score"] = name_score + rel_score + candidate["data_score"]
            if candidate["total_score"] <= 0:
                candidate["rejection_reason"] = "Score ≤ 0"
            candidates.append(candidate)
    candidates.sort(key=lambda c: c["total_score"], reverse=True)
    audit["candidates"] = candidates
    positive = [c for c in candidates if c["total_score"] > 0]
    if positive:
        best = positive[0]
        audit["best_field"] = best
        probe = best.get("relation_probe") or {}
        if (best["name_score"] >= 25 or best["season_like_direct_count"] > 0
                or probe.get("season_like_count", 0) > 0 or best["data_score"] > 0):
            audit["confident"] = True
        audit["status"] = "ok"
    elif candidates:
        audit["status"] = "no_confident_field"; audit["manual_pick_needed"] = True
        audit["error"] = "Fields found but none scored positively. Use manual override below."
    else:
        audit["status"] = "no_candidates"; audit["error"] = "No eligible fields at all."
    return audit


def fetch_distinct_seasons_from_field(system_key, model, field, ftype, relation):
    cfg = get_system_config(system_key)
    if not cfg:
        return []
    auth = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth["ok"]:
        return []
    uid = auth["uid"]
    url, db, api_key = cfg["url"], cfg["db"], cfg["api_key"]

    # Fast path: read_group
    try:
        groups = _read_group(url, db, uid, api_key, model,
                             safe_domain([[field, "!=", False]]),
                             [field], [field], {"lazy": False})
        seasons = {}
        for g in groups or []:
            val = g.get(field)
            if val is False or val is None:
                continue
            if ftype == "many2one":
                if isinstance(val, list) and len(val) >= 2:
                    seasons[val[0]] = str(val[1]).strip()
                elif isinstance(val, int) and val:
                    seasons[val] = str(val)
            else:
                seasons[val] = str(val).strip()
        out = [(v, lbl) for v, lbl in seasons.items() if str(lbl).strip()]
        if out:
            out.sort(key=lambda x: str(x[1]))
            return out
    except Exception:
        pass

    # Fallback: full scan
    try:
        records = _execute(url, db, uid, api_key, model, "search_read",
                           safe_domain([[field, "!=", False]]),
                           {"fields": [field], "limit": 50000})
        if not records:
            return []
        unique_vals = {}
        related_ids = []
        for rec in records:
            val = rec.get(field)
            if val is False or val is None:
                continue
            if ftype == "many2one":
                if isinstance(val, list) and len(val) >= 2:
                    unique_vals[val[0]] = str(val[1]).strip(); related_ids.append(val[0])
                elif isinstance(val, int) and val:
                    unique_vals[val] = str(val); related_ids.append(val)
            else:
                unique_vals[val] = str(val).strip()
        if ftype == "many2one" and relation and related_ids:
            try:
                rel_recs = _execute(url, db, uid, api_key, relation, "search_read",
                                    safe_domain([["id", "in", list(set(related_ids))]]),
                                    {"fields": ["id", "name", "display_name"],
                                     "limit": len(set(related_ids)) + 10})
                for r in rel_recs:
                    name = r.get("display_name") or r.get("name") or str(r["id"])
                    if isinstance(name, list):
                        name = name[1] if len(name) > 1 else str(name)
                    unique_vals[r["id"]] = str(name).strip()
            except Exception:
                pass
        seasons = [(v, unique_vals[v]) for v in unique_vals if str(unique_vals[v]).strip()]
        seasons.sort(key=lambda x: str(x[1]))
        return seasons
    except Exception:
        return []


def fetch_distinct_seasons_from_audit(system_key, audit):
    if not audit.get("confident") or not audit.get("best_field"):
        return []
    best = audit["best_field"]
    return fetch_distinct_seasons_from_field(
        system_key, best["model"], best["field_name"], best["field_type"], best["relation_model"]
    )


@st.cache_data(ttl=3600, show_spinner=False)
def run_full_discovery():
    audits = {}
    all_systems_info = {}

    def _work(sys):
        audit = deep_season_audit_for_system(sys)
        info = None
        rejected = []
        # Try positive candidates in score order; pick the first that returns a
        # sane (<= MAX_SEASON_DISTINCT) season list. This skips junk fields that
        # match "winter" across hundreds of category/name values.
        positives = [c for c in audit.get("candidates", []) if c.get("total_score", 0) > 0]
        for cand in positives[:6]:
            seasons = fetch_distinct_seasons_from_field(
                sys, cand["model"], cand["field_name"],
                cand["field_type"], cand["relation_model"])
            if not seasons:
                continue
            if len(seasons) > MAX_SEASON_DISTINCT:
                rejected.append((cand["field_name"], len(seasons)))
                continue
            info = {
                "model": cand["model"], "field": cand["field_name"],
                "ftype": cand["field_type"], "relation": cand["relation_model"],
                "seasons": seasons,
            }
            audit["best_field"] = cand
            audit["chosen_field"] = cand["field_name"]
            audit["confident"] = True
            audit["status"] = "ok"
            break
        if rejected:
            audit["rejected_too_many"] = rejected
        if info is None and rejected:
            audit["status"] = "rejected_junk"
            audit["confident"] = False
            audit["manual_pick_needed"] = True
            audit["error"] = (
                f"Detected field had too many distinct values (> {MAX_SEASON_DISTINCT}) — "
                "looks like category/product-name data, not a season field: "
                + ", ".join(f"{f} ({n})" for f, n in rejected)
                + ". Excluded to protect accuracy & memory. Use manual override if a real "
                  "season field exists.")
        return sys, audit, info

    with ThreadPoolExecutor(max_workers=len(SYSTEM_KEYS)) as executor:
        for sys, audit, info in executor.map(_work, SYSTEM_KEYS):
            audits[sys] = audit
            if info:
                all_systems_info[sys] = info
    return all_systems_info, audits


def resolve_season_values_for_system(query, sys_info, mode="type"):
    seasons = sys_info.get("seasons", [])
    if not seasons:
        return [], [], "No seasons available"
    out_vals, out_lbls, seen = [], [], set()

    def add(val, lbl):
        if (val, lbl) not in seen:
            seen.add((val, lbl)); out_vals.append(val); out_lbls.append(lbl)

    q_norm = season_norm(query)
    q_type = season_type_only(query)
    q_year = season_year(query)

    if mode == "type":
        if not q_type:
            return [], [], f"'{query}' is not a recognized season type"
        for val, lbl in seasons:
            if season_type_only(lbl) == q_type:
                add(val, lbl)
        return (out_vals, out_lbls, None) if out_vals else ([], [], f"No '{q_type}' seasons found")

    for val, lbl in seasons:
        if lbl == query:
            add(val, lbl)
    if out_vals:
        return out_vals, out_lbls, None
    for val, lbl in seasons:
        if season_norm(lbl) == q_norm:
            add(val, lbl)
    if out_vals:
        return out_vals, out_lbls, None
    if q_type and q_year:
        sig = season_signature(query)
        for val, lbl in seasons:
            if season_signature(lbl) == sig:
                add(val, lbl)
        return (out_vals, out_lbls, None) if out_vals else ([], [], f"Season not found: {query}")
    if q_type:
        for val, lbl in seasons:
            if season_type_only(lbl) == q_type:
                add(val, lbl)
        if out_vals:
            return out_vals, out_lbls, None
    return [], [], f"Season not found: {query}"


# ══════════════════════════════════════════════════════════════════════════════
# QUANT-BASED FETCH  →  long format (one row per product × branch)
# ══════════════════════════════════════════════════════════════════════════════
LONG_COLS = ["System", "Branch", "Match Key", "Model Code", "Product", "Season", "Year", "Qty", "Price"]


def fetch_season_products(system_key, sys_info, query, mode="type", include_archived=False):
    cfg = get_system_config(system_key)
    if not cfg:
        return pd.DataFrame(columns=LONG_COLS), {"error": "No config"}
    auth = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth["ok"]:
        return pd.DataFrame(columns=LONG_COLS), {"error": "Auth failed: " + str(auth.get("error"))}

    uid = auth["uid"]
    url, db, api_key = cfg["url"], cfg["db"], cfg["api_key"]
    model, field, ftype = sys_info["model"], sys_info["field"], sys_info["ftype"]
    ctx = get_stock_context(cfg, include_archived)

    stored_values, matched_labels, resolve_err = resolve_season_values_for_system(query, sys_info, mode)
    val_to_label = dict(zip(stored_values, matched_labels))

    debug = {
        "system": system_key, "model": model, "field": field, "mode": mode,
        "requested": query, "matched_labels": matched_labels,
        "matched_years": sorted({season_year(l) for l in matched_labels if season_year(l)}),
        "stored_values": stored_values, "resolve_error": resolve_err,
        "models_found": 0, "with_stock": 0, "branches": 0,
        "limit_hit": False, "error": None,
    }
    if resolve_err or not stored_values:
        debug["error"] = resolve_err or "No matching stored values"
        return pd.DataFrame(columns=LONG_COLS), debug

    prod_fields = ["default_code", "barcode", "display_name",
                   "list_price", "lst_price", "product_tmpl_id"]

    try:
        # ── 1. Master product list of the season (covers every model, 0 stock too) ──
        if model == "product.template":
            tmpl_domain = (safe_domain([[field, "=", stored_values[0]]])
                           if len(stored_values) == 1
                           else safe_domain([[field, "in", stored_values]]))
            tmpl_recs = _execute(url, db, uid, api_key, "product.template", "search_read",
                                 tmpl_domain, {"fields": ["id", field],
                                               "limit": TEMPLATE_FETCH_LIMIT, "context": ctx}) or []
            if len(tmpl_recs) >= TEMPLATE_FETCH_LIMIT:
                debug["limit_hit"] = True
            tmpl_season = {}
            for tr in tmpl_recs:
                v = tr.get(field)
                if isinstance(v, list) and v:
                    v = v[0]
                tmpl_season[tr["id"]] = val_to_label.get(v, ", ".join(matched_labels))
            if not tmpl_season:
                return pd.DataFrame(columns=LONG_COLS), debug
            products = []
            for batch in _chunks(list(tmpl_season.keys()), 50):
                recs = _execute(url, db, uid, api_key, "product.product", "search_read",
                                safe_domain([["product_tmpl_id", "in", batch]]),
                                {"fields": prod_fields, "limit": 20000, "context": ctx})
                if recs:
                    products.extend(recs)

            def season_of(p):
                tm = p.get("product_tmpl_id")
                tid = tm[0] if isinstance(tm, list) and tm else tm
                return tmpl_season.get(tid, ", ".join(matched_labels))
        else:
            prod_domain = (safe_domain([[field, "=", stored_values[0]]])
                           if len(stored_values) == 1
                           else safe_domain([[field, "in", stored_values]]))
            products = _execute(url, db, uid, api_key, "product.product", "search_read",
                                prod_domain, {"fields": prod_fields + [field],
                                              "limit": PRODUCT_FETCH_LIMIT, "context": ctx}) or []
            if len(products) >= PRODUCT_FETCH_LIMIT:
                debug["limit_hit"] = True

            def season_of(p):
                v = p.get(field)
                if isinstance(v, list) and v:
                    v = v[0]
                return val_to_label.get(v, ", ".join(matched_labels))

        if not products:
            return pd.DataFrame(columns=LONG_COLS), debug

        pmap = {p["id"]: p for p in products}
        pids = list(pmap.keys())
        debug["models_found"] = len(pids)

        # ── 2. Internal locations + quants (the CORRECT qty) ──
        loc_map = get_internal_locations(system_key)
        loc_ids = list(loc_map.keys())

        quants = []
        if loc_ids:
            for chunk in _chunks(pids, PID_CHUNK):
                qs = _execute(url, db, uid, api_key, "stock.quant", "search_read",
                              safe_domain([["product_id", "in", chunk],
                                           ["location_id", "in", loc_ids],
                                           ["quantity", ">", 0]]),
                              {"fields": ["product_id", "location_id", "quantity"],
                               "limit": QUANT_FETCH_LIMIT, "context": ctx})
                if qs:
                    quants.extend(qs)

        def meta(pid):
            p = pmap.get(pid, {})
            code = str(p.get("default_code") or "").strip()
            barcode = str(p.get("barcode") or "").strip()
            name = str(p.get("display_name") or "").strip()
            if code:
                mk = code
            elif barcode:
                mk = "bc::" + barcode
            else:
                mk = "name::" + normalize_text(name)
            price = p.get("lst_price")
            if price in (None, False):
                price = p.get("list_price")
            return mk, code, name, float(price or 0), season_of(p)

        rows = []
        seen_pids = set()
        branches = set()
        for q in quants:
            pr = q.get("product_id")
            pid = pr[0] if isinstance(pr, list) and pr else pr
            if pid not in pmap:
                continue
            loc = q.get("location_id")
            if isinstance(loc, list) and loc:
                bname = loc[1] if len(loc) > 1 else loc_map.get(loc[0], "—")
            else:
                bname = loc_map.get(loc, "—")
            bname = str(bname).strip() or "—"
            branches.add(bname)
            seen_pids.add(pid)
            mk, code, name, price, season_lbl = meta(pid)
            rows.append({
                "System": system_key, "Branch": bname, "Match Key": mk,
                "Model Code": code, "Product": name,
                "Season": season_lbl, "Year": season_year(season_lbl),
                "Qty": float(q.get("quantity") or 0), "Price": price,
            })

        # coverage: products with no stock anywhere — keep them (0 qty)
        for pid in pids:
            if pid not in seen_pids:
                mk, code, name, price, season_lbl = meta(pid)
                rows.append({
                    "System": system_key, "Branch": "—", "Match Key": mk,
                    "Model Code": code, "Product": name,
                    "Season": season_lbl, "Year": season_year(season_lbl),
                    "Qty": 0.0, "Price": price,
                })

        debug["with_stock"] = len(seen_pids)
        debug["branches"] = len(branches)

        df = pd.DataFrame(rows, columns=LONG_COLS)
        if df.empty:
            return df, debug
        df = (df.groupby(["System", "Branch", "Match Key", "Model Code",
                          "Product", "Season", "Year"], as_index=False)
                .agg({"Qty": "sum", "Price": "max"}))
        return df, debug

    except Exception as e:
        debug["error"] = str(e)
        return pd.DataFrame(columns=LONG_COLS), debug


def _join_distinct(series):
    vals = []
    for x in series:
        x = str(x).strip()
        if x and x not in vals:
            vals.append(x)
    return ", ".join(sorted(vals))


def build_matrices(query, all_systems_info, mode="type", include_archived=False):
    """Returns (long_df, company_matrix, debug). Branch view is derived from long_df."""
    parts = {}
    debug = {}
    with ThreadPoolExecutor(max_workers=len(all_systems_info) or 1) as ex:
        futs = {ex.submit(fetch_season_products, sys, info, query, mode, include_archived): sys
                for sys, info in all_systems_info.items()}
        for fut in as_completed(futs):
            sys = futs[fut]
            try:
                df, dbg = fut.result()
                debug[sys] = dbg
                if not df.empty:
                    parts[sys] = df
            except Exception as e:
                debug[sys] = {"error": str(e)}

    if not parts:
        return pd.DataFrame(columns=LONG_COLS), pd.DataFrame(), debug

    long_df = pd.concat(parts.values(), ignore_index=True)

    # ── Company matrix: qty per system (sum across branches) ──
    qty_pivot = long_df.pivot_table(index="Match Key", columns="System", values="Qty", aggfunc="sum", fill_value=0)
    price_pivot = long_df.pivot_table(index="Match Key", columns="System", values="Price", aggfunc="max", fill_value=0)
    systems_all = [s for s in SYSTEM_KEYS if s in all_systems_info]
    for s in systems_all:
        if s not in qty_pivot.columns:
            qty_pivot[s] = 0
        if s not in price_pivot.columns:
            price_pivot[s] = 0
    qty_pivot = qty_pivot[systems_all]
    price_pivot = price_pivot[systems_all]
    qty_pivot.columns = [f"{c} Qty" for c in qty_pivot.columns]
    price_pivot.columns = [f"{c} Price" for c in price_pivot.columns]

    code_map = long_df.groupby("Match Key")["Model Code"].agg(
        lambda s: next((x for x in s if str(x).strip()), "")).reset_index()
    prod_map = long_df.groupby("Match Key")["Product"].agg(
        lambda s: next((x for x in s if str(x).strip()), "")).reset_index()
    season_map = long_df.groupby("Match Key")["Season"].agg(_join_distinct).reset_index()
    year_map = long_df.groupby("Match Key")["Year"].agg(_join_distinct).reset_index()

    comp = (qty_pivot.join(price_pivot, how="outer").reset_index()
            .merge(code_map, on="Match Key", how="left")
            .merge(prod_map, on="Match Key", how="left")
            .merge(season_map, on="Match Key", how="left")
            .merge(year_map, on="Match Key", how="left"))

    qcols = [c for c in comp.columns if c.endswith(" Qty")]
    pcols = [c for c in comp.columns if c.endswith(" Price")]
    for c in qcols:
        comp[c] = pd.to_numeric(comp[c], errors="coerce").fillna(0).astype(int)
    for c in pcols:
        comp[c] = pd.to_numeric(comp[c], errors="coerce").fillna(0).round(2)
    comp["Model Code"] = comp["Model Code"].fillna("").astype(str)
    comp["Product"] = comp["Product"].fillna("").astype(str)
    comp["Year"] = comp["Year"].fillna("").astype(str)
    comp["Season"] = comp["Season"].fillna("").astype(str)
    comp["Total Qty"] = comp[qcols].sum(axis=1).astype(int)

    ordered = ["Model Code", "Product", "Year", "Season"]
    for sys in SYSTEM_KEYS:
        if f"{sys} Qty" in comp.columns:
            ordered.append(f"{sys} Qty")
        if f"{sys} Price" in comp.columns:
            ordered.append(f"{sys} Price")
    ordered.append("Total Qty")
    comp = comp[[c for c in ordered if c in comp.columns]]
    comp = comp.sort_values(["Total Qty", "Model Code"], ascending=[False, True]).reset_index(drop=True)
    return long_df, comp, debug


def build_branch_matrix(long_df):
    """Branch view: one column per 'System | Branch'."""
    if long_df.empty:
        return pd.DataFrame()
    piv = long_df.pivot_table(index=["Model Code", "Product", "Year"],
                              columns=["System", "Branch"], values="Qty",
                              aggfunc="sum", fill_value=0)
    piv.columns = [f"{a} | {b}" for a, b in piv.columns]
    piv = piv.reset_index().copy()  # copy() de-fragments after pivot+reset
    branch_cols = [c for c in piv.columns if " | " in c]
    for c in branch_cols:
        piv[c] = pd.to_numeric(piv[c], errors="coerce").fillna(0).astype(int)
    piv["Total"] = piv[branch_cols].sum(axis=1).astype(int)
    piv = piv.sort_values(["Total", "Model Code"], ascending=[False, True]).reset_index(drop=True)
    return piv


# ── Size breakdown (fashion: S/M/L/XL...) ──
_SIZE_ORDER = ["2XS", "XS", "S", "M", "L", "XL", "XXL", "2XL", "3XL", "4XL", "5XL", "OS", "OSFA"]
_SIZE_RE = re.compile(r'-?(2XS|XS|XXL|2XL|3XL|4XL|5XL|XL|XS|OSFA|OS|S|M|L)$', re.IGNORECASE)


def extract_size(code):
    """Return (base_model, size) from a model code like XP6013-M -> (XP6013, M)."""
    code = str(code).strip()
    m = _SIZE_RE.search(code)
    if m:
        size = m.group(1).upper()
        base = code[:m.start()].rstrip("-").strip()
        return (base or code), size
    return code, ""


def build_size_pivot(long_df):
    """base_model x size pivot of qty (summed across all systems & branches).
    Returns (pivot_df, size_cols) or (empty, [])."""
    if long_df is None or long_df.empty:
        return pd.DataFrame(), []
    w = long_df.copy()
    w["_qty"] = pd.to_numeric(w["Qty"], errors="coerce").fillna(0)
    bs = w["Model Code"].apply(lambda c: pd.Series(extract_size(c), index=["_base", "_size"]))
    w = pd.concat([w, bs], axis=1)
    sized = w[w["_size"] != ""]
    if sized.empty:
        return pd.DataFrame(), []
    piv = sized.pivot_table(index="_base", columns="_size", values="_qty",
                            aggfunc="sum", fill_value=0).reset_index()
    piv.columns.name = None
    size_cols = [s for s in _SIZE_ORDER if s in piv.columns]
    extra = [c for c in piv.columns if c not in (["_base"] + _SIZE_ORDER)]
    size_cols = size_cols + sorted(extra)
    for c in size_cols:
        piv[c] = pd.to_numeric(piv[c], errors="coerce").fillna(0).astype(int)
    piv["Total"] = piv[size_cols].sum(axis=1).astype(int)
    prod_map = (sized.groupby("_base")["Product"]
                .agg(lambda s: next((x for x in s if str(x).strip()), "")).to_dict())
    piv.insert(1, "Product", piv["_base"].map(prod_map).fillna(""))
    piv = piv.rename(columns={"_base": "Base Model"})
    piv = piv[["Base Model", "Product"] + size_cols + ["Total"]]
    return piv.sort_values(["Total", "Base Model"], ascending=[False, True]).reset_index(drop=True), size_cols


def units_by_company(long_df):
    if long_df is None or long_df.empty:
        return pd.DataFrame()
    w = long_df.copy()
    w["_qty"] = pd.to_numeric(w["Qty"], errors="coerce").fillna(0)
    g = w.groupby("System", as_index=False)["_qty"].sum().rename(columns={"_qty": "Units"})
    g["Company"] = g["System"].map(get_system_name)
    return g.set_index("Company")[["Units"]].sort_values("Units", ascending=False)


def units_by_branch(long_df, top_n=20):
    if long_df is None or long_df.empty:
        return pd.DataFrame()
    w = long_df.copy()
    w["_qty"] = pd.to_numeric(w["Qty"], errors="coerce").fillna(0)
    w["Loc"] = w["System"].map(get_system_name) + " | " + w["Branch"].astype(str)
    g = (w.groupby("Loc", as_index=False)["_qty"].sum()
         .rename(columns={"_qty": "Units"}).sort_values("Units", ascending=False))
    return g.head(top_n).set_index("Loc")[["Units"]]


def stock_health(comp, active_systems):
    """Quick health stats on the company matrix."""
    qcols = [f"{s} Qty" for s in active_systems if f"{s} Qty" in comp.columns]
    if not qcols:
        return {}
    in_n = (comp[qcols] > 0).sum(axis=1)
    return {
        "zero_all": int((comp["Total Qty"] == 0).sum()),
        "single_company": int(((in_n == 1)).sum()),
        "all_companies": int((in_n == len(qcols)).sum()),
    }


# ── Alerts / value (operate on company matrix) ──
def compute_missing_analysis(df, active_systems):
    if df.empty or not active_systems:
        return pd.DataFrame()
    qty_cols = {s: f"{s} Qty" for s in active_systems if f"{s} Qty" in df.columns}
    swag_col = qty_cols.get("SWAG")
    if not qty_cols or not swag_col:
        return pd.DataFrame()
    has = df[swag_col] > 0
    has_year = "Year" in df.columns
    base = ["Model Code", "Product"] + (["Year"] if has_year else [])
    out = []
    for sys, col in qty_cols.items():
        if sys == "SWAG":
            continue
        f = df[has & (df[col] == 0)][base + [swag_col]].copy()
        if not f.empty:
            f["Missing In"] = get_system_name(sys)
            f.rename(columns={swag_col: "SWAG Qty"}, inplace=True)
            out.append(f[base + ["SWAG Qty", "Missing In"]])
    if not out:
        return pd.DataFrame()
    return pd.concat(out, ignore_index=True).sort_values("SWAG Qty", ascending=False).reset_index(drop=True)


def compute_price_alerts(df, active_systems):
    if df.empty:
        return pd.DataFrame()
    price_cols = {s: f"{s} Price" for s in active_systems if f"{s} Price" in df.columns}
    if len(price_cols) < 2:
        return pd.DataFrame()
    alerts = []
    for _, row in df.iterrows():
        prices = {s: float(row[c]) for s, c in price_cols.items() if float(row[c]) > 0}
        if len(prices) < 2:
            continue
        mn, mx = min(prices.values()), max(prices.values())
        if mn == 0:
            continue
        diff = ((mx - mn) / mn) * 100
        if diff >= PRICE_DIFF_THRESHOLD_PCT:
            alerts.append({"Model Code": row.get("Model Code", ""), "Product": row.get("Product", ""),
                           "Min Price": round(mn, 2), "Max Price": round(mx, 2), "Diff %": round(diff, 1),
                           "Cheapest In": get_system_name(min(prices, key=prices.get)),
                           "Highest In": get_system_name(max(prices, key=prices.get))})
    if not alerts:
        return pd.DataFrame()
    return pd.DataFrame(alerts).sort_values("Diff %", ascending=False).reset_index(drop=True)


def compute_stock_value(df, active_systems):
    out = {}
    for s in active_systems:
        q, p = f"{s} Qty", f"{s} Price"
        if q in df.columns and p in df.columns:
            out[get_system_name(s)] = float((df[q] * df[p]).sum())
    return out


def only_differences(df, active_systems):
    qcols = [f"{s} Qty" for s in active_systems if f"{s} Qty" in df.columns]
    if len(qcols) < 2:
        return df
    vals = df[qcols]
    mask = vals.max(axis=1) != vals.min(axis=1)
    return df[mask].reset_index(drop=True)


def compute_rebalancing(df, active_systems, min_surplus=2):
    """Cross-company transfer suggestions.
    For each model that is stocked in some companies and 0 in others, the company
    with the most stock (>= min_surplus) is the donor; companies with 0 are targets.
    Returns one row per (model x empty-company)."""
    qty_cols = {s: f"{s} Qty" for s in active_systems if f"{s} Qty" in df.columns}
    if len(qty_cols) < 2:
        return pd.DataFrame()
    out = []
    for _, row in df.iterrows():
        stocks = {s: int(row[c]) for s, c in qty_cols.items()}
        donors = {s: q for s, q in stocks.items() if q >= min_surplus}
        empties = [s for s, q in stocks.items() if q == 0]
        if not donors or not empties:
            continue
        src = max(donors, key=donors.get)
        src_qty = donors[src]
        move_each = max(1, src_qty // (len(empties) + 1))
        for dst in empties:
            out.append({
                "Model Code": row.get("Model Code", ""),
                "Product": row.get("Product", ""),
                "From (has stock)": get_system_name(src),
                "From Qty": src_qty,
                "To (0 stock)": get_system_name(dst),
                "Suggested Move": move_each,
            })
    if not out:
        return pd.DataFrame()
    return pd.DataFrame(out).sort_values("From Qty", ascending=False).reset_index(drop=True)


def zero_stock_models(df):
    """Models in this season with 0 units across every company — clearance / discontinue candidates."""
    if df.empty or "Total Qty" not in df.columns:
        return pd.DataFrame()
    z = df[df["Total Qty"] == 0]
    cols = [c for c in ["Model Code", "Product", "Year", "Season"] if c in z.columns]
    return z[cols].reset_index(drop=True)


def build_season_text_summary(comp, long_df, season_name, active_systems):
    """Copyable WhatsApp-style text report of the season."""
    lines = []
    lines.append(f"SWAG Season Report - {season_name}")
    lines.append(datetime.now().strftime("%Y-%m-%d %H:%M"))
    lines.append("")
    total_models = len(comp)
    total_units = int(comp["Total Qty"].sum()) if "Total Qty" in comp.columns else 0
    lines.append(f"Models: {total_models:,}")
    lines.append(f"Total units: {total_units:,}")
    n_branches = long_df["Branch"].nunique() if not long_df.empty else 0
    lines.append(f"Branches: {n_branches}")
    lines.append("")
    lines.append("Units by company:")
    for s in active_systems:
        col = f"{s} Qty"
        if col in comp.columns:
            lines.append(f"  - {get_system_name(s)}: {int(comp[col].sum()):,}")
    sv = compute_stock_value(comp, active_systems)
    if sv:
        lines.append("")
        lines.append("Stock value (SAR):")
        for nm, val in sv.items():
            lines.append(f"  - {nm}: {val:,.0f}")
    hs = stock_health(comp, active_systems)
    if hs:
        lines.append("")
        lines.append(f"Zero-stock models: {hs['zero_all']:,}")
        lines.append(f"Single-company only: {hs['single_company']:,}")
        lines.append(f"In all companies: {hs['all_companies']:,}")
    lines.append("")
    lines.append("- SWAG Season Dashboard")
    return "\n".join(lines)


def build_unified_season_list(all_systems_info):
    labels = set()
    for sys, info in all_systems_info.items():
        for val, lbl in info.get("seasons", []):
            if str(lbl).strip():
                labels.add(str(lbl).strip())

    def sk(lbl):
        st_ = season_type_only(lbl) or "ZZZ"
        yr = season_year(lbl)
        return (st_, -(int(yr) if yr else 0), lbl)
    return sorted(labels, key=sk)


def build_available_types(all_systems_info):
    found = set()
    for sys, info in all_systems_info.items():
        for val, lbl in info.get("seasons", []):
            tt = season_type_only(lbl)
            if tt:
                found.add(tt)
    return [t for t in ["SUMMER", "WINTER", "SPRING", "FALL"] if t in found]


def to_excel_generic(df, season_name, sheet="Sheet1"):
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet[:31])
        ws = writer.sheets[sheet[:31]]
        hdr_fill = PatternFill("solid", fgColor="060D0E")
        hdr_font = Font(bold=True, color="4AACB4", size=11, name="Calibri")
        h_align = Alignment(horizontal="center", vertical="center")
        thin = Side(border_style="thin", color="1A2A2C")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        alt_fill = PatternFill("solid", fgColor="0D1A1C")
        norm_font = Font(name="Calibri", size=10, color="8AACB0")
        num_align = Alignment(horizontal="right", vertical="center")
        txt_align = Alignment(horizontal="center", vertical="center")
        tot_fill = PatternFill("solid", fgColor="060D0E")
        tot_font = Font(bold=True, name="Calibri", color="D4A84B")
        max_row, max_col = ws.max_row, ws.max_column
        ws.row_dimensions[1].height = 26
        for c in range(1, max_col + 1):
            cell = ws.cell(row=1, column=c)
            cell.fill = hdr_fill; cell.font = hdr_font; cell.alignment = h_align; cell.border = border
        if max_row <= 4000:
            for row in ws.iter_rows(min_row=2, max_row=max_row):
                for cell in row:
                    cell.border = border; cell.font = norm_font
                    if cell.row % 2 == 0:
                        cell.fill = alt_fill
                    cell.alignment = num_align if isinstance(cell.value, (int, float)) else txt_align
        for c in range(1, max_col + 1):
            cl = get_column_letter(c)
            ml = max((len(str(ws.cell(row=r, column=c).value or "")) for r in range(1, min(max_row, 201) + 1)), default=8)
            ws.column_dimensions[cl].width = min(max(ml + 3, 12), 45)
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(max_col)}{max_row}"
        tr = max_row + 1
        tc = ws.cell(row=tr, column=1, value="TOTAL"); tc.font = tot_font; tc.fill = tot_fill; tc.alignment = h_align
        for ci, cn in enumerate(df.columns, start=1):
            if "Qty" in str(cn) or "Total" in str(cn) or " | " in str(cn) or "Price" in str(cn):
                cl = get_column_letter(ci)
                c2 = ws.cell(row=tr, column=ci, value=f"=SUM({cl}2:{cl}{max_row})")
                c2.font = tot_font; c2.fill = tot_fill; c2.alignment = num_align
        ws.sheet_properties.tabColor = "4AACB4"
        fr = tr + 2
        fc = ws.cell(row=fr, column=1, value=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  {season_name}")
        fc.font = Font(italic=True, color="4AACB4", size=9, name="Calibri")
    return buf.getvalue()


def to_excel_workbook(sheets, season_name):
    """sheets: list of (sheet_name, df). One styled workbook, every view in its own tab."""
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for sheet, df in sheets:
            if df is None or df.empty:
                continue
            df.to_excel(writer, index=False, sheet_name=sheet[:31])
            ws = writer.sheets[sheet[:31]]
            hdr_fill = PatternFill("solid", fgColor="060D0E")
            hdr_font = Font(bold=True, color="4AACB4", size=11, name="Calibri")
            h_align = Alignment(horizontal="center", vertical="center")
            thin = Side(border_style="thin", color="1A2A2C")
            border = Border(left=thin, right=thin, top=thin, bottom=thin)
            alt_fill = PatternFill("solid", fgColor="0D1A1C")
            norm_font = Font(name="Calibri", size=10, color="8AACB0")
            num_align = Alignment(horizontal="right", vertical="center")
            txt_align = Alignment(horizontal="center", vertical="center")
            tot_fill = PatternFill("solid", fgColor="060D0E")
            tot_font = Font(bold=True, name="Calibri", color="D4A84B")
            mr, mc = ws.max_row, ws.max_column
            ws.row_dimensions[1].height = 26
            for c in range(1, mc + 1):
                cell = ws.cell(row=1, column=c)
                cell.fill = hdr_fill; cell.font = hdr_font; cell.alignment = h_align; cell.border = border
            if mr <= 4000:
                for row in ws.iter_rows(min_row=2, max_row=mr):
                    for cell in row:
                        cell.border = border; cell.font = norm_font
                        if cell.row % 2 == 0:
                            cell.fill = alt_fill
                        cell.alignment = num_align if isinstance(cell.value, (int, float)) else txt_align
            for c in range(1, mc + 1):
                cl = get_column_letter(c)
                ml = max((len(str(ws.cell(row=r, column=c).value or "")) for r in range(1, min(mr, 201) + 1)), default=8)
                ws.column_dimensions[cl].width = min(max(ml + 3, 12), 45)
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = f"A1:{get_column_letter(mc)}{mr}"
            tr = mr + 1
            tc = ws.cell(row=tr, column=1, value="TOTAL"); tc.font = tot_font; tc.fill = tot_fill; tc.alignment = h_align
            for ci, cn in enumerate(df.columns, start=1):
                if "Qty" in str(cn) or "Total" in str(cn) or " | " in str(cn):
                    cl = get_column_letter(ci)
                    c2 = ws.cell(row=tr, column=ci, value=f"=SUM({cl}2:{cl}{mr})")
                    c2.font = tot_font; c2.fill = tot_fill; c2.alignment = num_align
            ws.sheet_properties.tabColor = "4AACB4"
    return buf.getvalue()


def _register_manual_system(sys, candidate):
    seasons = fetch_distinct_seasons_from_field(
        sys, candidate["model"], candidate["field_name"],
        candidate["field_type"], candidate["relation_model"])
    if seasons:
        info = st.session_state.get("all_systems_info", {})
        info[sys] = {"model": candidate["model"], "field": candidate["field_name"],
                     "ftype": candidate["field_type"], "relation": candidate["relation_model"],
                     "seasons": seasons}
        st.session_state["all_systems_info"] = info
        st.session_state["unified_seasons"] = build_unified_season_list(info)
        st.session_state["available_types"] = build_available_types(info)
        return len(seasons)
    return 0


def render_audit_report(audits):
    st.markdown("<div class='section-tag'>Deep Season Field Audit Report</div>", unsafe_allow_html=True)
    for sys in SYSTEM_KEYS:
        audit = audits.get(sys)
        if not audit:
            st.markdown(f"**{get_system_name(sys)}** — not audited"); continue
        found = audit.get("confident", False)
        manual = audit.get("manual_pick_needed", False)
        icon = "✅" if found else ("⚠️" if manual else "❌")
        label = "Field Found" if found else ("Manual Pick Needed" if manual else "No Field Identified")
        with st.expander(f"{get_system_name(sys)}  —  {icon} {label}", expanded=not found):
            st.markdown(
                f"**Status:** `{audit['status']}` | Raw: **{audit.get('raw_field_count','?')}** | "
                f"Eligible: **{audit.get('eligible_field_count','?')}** | "
                f"Records: **{audit.get('product_records_loaded','?')}**")
            if audit.get("error"):
                st.warning(audit["error"])
            if audit.get("best_field"):
                best = audit["best_field"]
                st.success(f"Best: `{best['model']}.{best['field_name']}` | "
                           f"type: {best['field_type']} | label: **{best['field_label']}** | "
                           f"score: {round(best['total_score'],1)}")
            candidates = audit.get("candidates", [])
            pickable = [c for c in candidates if c["total_score"] > -49
                        and not (c.get("rejection_reason") or "").startswith("Blacklisted")]
            if pickable and not found:
                st.markdown("**🔧 Manual field override**")
                opts = {f"{c['model']}.{c['field_name']} [{c['field_label']}] (score {round(c['total_score'],1)})": c
                        for c in pickable[:20]}
                chosen = opts[st.selectbox("Choose the season field", list(opts.keys()), key=f"manual_{sys}")]
                if st.button(f"✓ Use this for {get_system_name(sys)}", key=f"use_{sys}"):
                    n = _register_manual_system(sys, chosen)
                    if n:
                        st.success(f"Set! Found {n} seasons."); st.rerun()
                    else:
                        st.error("No season values found.")
            if candidates:
                rows = [{"Field": c["field_name"], "Label": c["field_label"], "Type": c["field_type"],
                         "Relation": c["relation_model"] or "", "Non-Empty": c["non_empty_count"],
                         "Season-Like": c["season_like_direct_count"], "Total": round(c["total_score"], 1),
                         "Samples": "; ".join(str(v) for v in c["sample_raw_values"][:3]),
                         "Note": c["rejection_reason"] or "—"} for c in candidates[:40]]
                st.dataframe(pd.DataFrame(rows), use_container_width=True, height=360)


def show_login():
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="you@company.com")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Sign In", type="primary", use_container_width=True)
    if submit:
        if not email or not password:
            st.error("Fill both fields."); return
        if "LOGIN" not in st.secrets:
            st.error("Missing LOGIN section in secrets.toml"); return
        cfg = st.secrets["LOGIN"]
        try:
            login_url = str(cfg.get("url", "")).rstrip("/")
            if login_url.endswith("/odoo"):
                login_url = login_url[:-5]
            proxy = xmlrpc.client.ServerProxy(login_url + "/xmlrpc/2/common", allow_none=True)
            uid = proxy.authenticate(cfg["db"], email, password, {})
            if uid:
                st.query_params["u"] = email
                st.query_params["t"] = _make_token(email)
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.rerun()
            else:
                st.error("Wrong email or password.")
        except Exception as e:
            st.error("Connection error: " + str(e))


def do_logout():
    try:
        st.query_params.clear()
    except Exception:
        pass
    st.session_state.authenticated = False
    st.session_state.user_email = ""
    st.rerun()


def render_company_status(all_systems_info, audits, fetch_debug):
    st.markdown(f"<div class='section-tag'>Companies ({len(SYSTEM_KEYS)})</div>", unsafe_allow_html=True)
    loaded = 0
    for sys in SYSTEM_KEYS:
        name = get_system_name(sys)
        d = (fetch_debug or {}).get(sys)
        if d is not None:
            if d.get("error"):
                st.markdown(f"❌ **{name}** — error: {d.get('error')}")
            elif d.get("resolve_error"):
                st.markdown(f"⚠️ **{name}** — season did not match")
            elif d.get("models_found", 0) > 0:
                loaded += 1
                yrs = d.get("matched_years") or []
                yr = f" [years: {', '.join(yrs)}]" if yrs else ""
                ws = d.get("with_stock", 0); br = d.get("branches", 0)
                part = "  ⚠️ PARTIAL (row limit hit)" if d.get("limit_hit") else ""
                st.markdown(f"✅ **{name}** — {d.get('models_found',0):,} models, "
                            f"{ws:,} with stock, {br} branch(es){yr}{part}")
            else:
                st.markdown(f"⚠️ **{name}** — 0 models")
            continue
        if sys in all_systems_info:
            n = len(all_systems_info[sys].get("seasons", []))
            st.markdown(f"🟢 **{name}** — season field found ({n:,} seasons), ready")
        else:
            a = audits.get(sys) or {}
            stt = a.get("status")
            if stt == "auth_failed":
                st.markdown(f"❌ **{name}** — login/connection failed")
            elif stt == "no_config":
                st.markdown(f"❌ **{name}** — config missing")
            elif stt == "rejected_junk":
                rj = a.get("rejected_too_many") or []
                detail = ", ".join(f"{f} ({n:,} values)" for f, n in rj)
                st.markdown(f"⚠️ **{name}** — no clean season field. "
                            f"Skipped junk field: {detail}. "
                            "Turn on Diagnostics to pick a field manually.")
            elif stt in ("no_confident_field", "no_candidates"):
                st.markdown(f"⚠️ **{name}** — season field could not be auto-detected")
            else:
                st.markdown(f"⚪ **{name}** — {a.get('error','status unknown')}")
    if fetch_debug:
        st.caption(f"Loaded data for {loaded} / {len(SYSTEM_KEYS)} companies.")


def show_dashboard():
    with st.sidebar:
        st.markdown("### SWAG")
        st.write(st.session_state.user_email)
        diag = st.checkbox("Diagnostics", value=False)
        include_archived = st.checkbox("Include archived products", value=False,
                                       help="On = also include discontinued/archived items "
                                            "(maximum coverage). Off = active products only.")
        if st.button("Reload Seasons", use_container_width=True, type="secondary"):
            try:
                run_full_discovery.clear()
                get_internal_locations.clear()
            except Exception:
                pass
            for k in ["all_systems_info", "audits", "audit_done", "long_df", "company_matrix",
                      "season_name", "fetch_debug", "unified_seasons", "available_types"]:
                st.session_state.pop(k, None)
            st.rerun()
        if st.button("Logout", use_container_width=True, type="secondary"):
            do_logout()

    st.markdown("<div class='hero-title'>Season <em>Comparison</em></div>", unsafe_allow_html=True)

    if not st.session_state.get("audit_done"):
        with st.spinner("Loading seasons..."):
            asi, audits = run_full_discovery()
            st.session_state["all_systems_info"] = asi
            st.session_state["audits"] = audits
            st.session_state["audit_done"] = True
            st.session_state["unified_seasons"] = build_unified_season_list(asi)
            st.session_state["available_types"] = build_available_types(asi)
            for k in ["long_df", "company_matrix", "season_name", "fetch_debug"]:
                st.session_state.pop(k, None)

    all_systems_info = st.session_state.get("all_systems_info", {})
    audits = st.session_state.get("audits", {})
    fetch_debug = st.session_state.get("fetch_debug", {})
    unified_seasons = st.session_state.get("unified_seasons", [])
    available_types = st.session_state.get("available_types", [])

    if diag:
        render_audit_report(audits)
    render_company_status(all_systems_info, audits, fetch_debug)

    if not all_systems_info:
        st.error("No season field could be detected for any company.")
        return

    # ── SEARCH ──
    st.markdown("<div class='section-tag'>Search Season</div>", unsafe_allow_html=True)
    search_mode = st.radio("Selection mode",
                           ["🌦️ Season type — ALL years, ALL companies", "🎯 Exact season"],
                           horizontal=True, label_visibility="collapsed")
    selected_query = ""
    resolve_mode = "type"

    if search_mode.startswith("🌦️"):
        resolve_mode = "type"
        cpick, ctype = st.columns([2, 3])
        with cpick:
            if available_types:
                picked = st.selectbox("Season type", options=[""] + available_types,
                                      format_func=lambda t: "— Choose a type —" if t == "" else SEASON_TYPE_LABEL.get(t, t),
                                      key="season_type_pick")
                if picked:
                    selected_query = picked
            else:
                st.warning("No season types detected.")
        with ctype:
            typed = st.text_input("...or type it", placeholder="winter / صيفي / summer", key="season_type_typed")
            if typed.strip():
                tt = season_type_only(typed.strip())
                if tt:
                    selected_query = tt
                else:
                    st.warning(f"'{typed}' is not a recognized season type")
    else:
        resolve_mode = "exact"
        if unified_seasons:
            selected_query = st.selectbox("Season", options=[""] + unified_seasons,
                                          format_func=lambda x: "— Choose a season —" if x == "" else x,
                                          key="season_exact_pick")
        else:
            st.warning("No seasons loaded. Reload.")

    if selected_query:
        title = SEASON_TYPE_LABEL.get(selected_query, selected_query) if resolve_mode == "type" else selected_query
        st.markdown(f"<div class='info-banner'>Will fetch: {title}</div>", unsafe_allow_html=True)
        cols = st.columns(len(all_systems_info))
        for i, (sys, info) in enumerate(all_systems_info.items()):
            _, lbls, _ = resolve_season_values_for_system(selected_query, info, resolve_mode)
            with cols[i]:
                st.markdown(f"<div class='season-match-box'>"
                            f"<div class='season-match-sys'>{get_system_name(sys)}</div>"
                            f"<div class='season-match-label'>{'<br>'.join(lbls) if lbls else '—'}</div>"
                            f"</div>", unsafe_allow_html=True)

    cbtn, _ = st.columns([1, 4])
    with cbtn:
        compare_clicked = st.button("Compare", type="primary", disabled=not bool(selected_query))

    if compare_clicked and selected_query:
        with st.spinner("Fetching stock from every branch of every company..."):
            long_df, comp, fdebug = build_matrices(selected_query, all_systems_info, resolve_mode, include_archived)
        st.session_state["fetch_debug"] = fdebug
        if comp.empty:
            st.error("No products found for this season.")
        else:
            disp = SEASON_TYPE_LABEL.get(selected_query, selected_query) if resolve_mode == "type" else selected_query
            st.session_state["long_df"] = long_df
            st.session_state["company_matrix"] = comp
            st.session_state["season_name"] = disp
            st.rerun()

    # ── RESULTS ──
    if "company_matrix" in st.session_state:
        comp = st.session_state["company_matrix"]
        long_df = st.session_state.get("long_df", pd.DataFrame(columns=LONG_COLS))
        season_name = st.session_state["season_name"]
        active_systems = [s for s in SYSTEM_KEYS if f"{s} Qty" in comp.columns]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Models", f"{len(comp):,}")
        c2.metric("Total Units", f"{int(comp['Total Qty'].sum()):,}")
        years = set()
        if "Year" in comp.columns:
            years = {y for v in comp["Year"] for y in str(v).split(", ") if y}
        c3.metric("Years Covered", ", ".join(sorted(years)) or "—")
        n_branches = long_df["Branch"].nunique() if not long_df.empty else 0
        c4.metric("Branches", f"{n_branches:,}")

        # Stock health quick stats
        hs = stock_health(comp, active_systems)
        if hs:
            h1, h2, h3 = st.columns(3)
            h1.metric("Zero-Stock Models", f"{hs['zero_all']:,}",
                      help="Models in this season with 0 units everywhere")
            h2.metric("Single-Company Only", f"{hs['single_company']:,}",
                      help="Stocked in exactly one company — candidates for transfer/sync")
            h3.metric("In All Companies", f"{hs['all_companies']:,}",
                      help="Models carried by every company")

        # Overview charts
        with st.expander("📊 Overview Charts (units by company / branch)", expanded=False):
            ucol, bcol = st.columns(2)
            with ucol:
                st.caption("Units by Company")
                ubc = units_by_company(long_df)
                if not ubc.empty:
                    st.bar_chart(ubc, use_container_width=True)
            with bcol:
                st.caption("Top Branches by Units")
                ubb = units_by_branch(long_df, top_n=15)
                if not ubb.empty:
                    st.bar_chart(ubb, use_container_width=True)

        # Stock value per system
        sv = compute_stock_value(comp, active_systems)
        if sv:
            with st.expander("💵 Stock Value per System (qty × price)", expanded=False):
                vc = st.columns(len(sv))
                for i, (nm, val) in enumerate(sv.items()):
                    vc[i].metric(nm, f"{val:,.0f}")

        # Missing alert
        miss = compute_missing_analysis(comp, active_systems)
        if not miss.empty:
            with st.expander(f"⚠️ Missing Products — {len(miss):,} items in SWAG but not in others", expanded=False):
                st.markdown("<div class='alert-missing'>In stock in SWAG, 0 elsewhere — possible sync issue</div>", unsafe_allow_html=True)
                st.dataframe(miss.head(200), use_container_width=True, height=320)
                st.download_button("Download Missing Excel", to_excel_generic(miss, season_name, "Missing"),
                                   f"missing_{season_name}.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   key="miss_dl")

        _heavy_ok = len(comp) <= HEAVY_COMPUTE_ROW_CAP
        if not _heavy_ok:
            st.markdown(f"<div class='info-banner'>Large result ({len(comp):,} models) — "
                        "Price Gap and Transfer Suggestions are skipped on screen to keep things "
                        "fast. Use the matrix views and Excel exports below.</div>",
                        unsafe_allow_html=True)

        # Price alert
        pa = compute_price_alerts(comp, active_systems) if _heavy_ok else pd.DataFrame()
        if not pa.empty:
            with st.expander(f"💰 Price Gap — {len(pa):,} products with {PRICE_DIFF_THRESHOLD_PCT:.0f}%+ difference", expanded=False):
                st.markdown("<div class='alert-price'>Same product, different price across systems</div>", unsafe_allow_html=True)
                st.dataframe(pa.head(200), use_container_width=True, height=320)
                st.download_button("Download Price Alerts Excel", to_excel_generic(pa, season_name, "PriceGaps"),
                                   f"price_{season_name}.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   key="price_dl")

        # Rebalancing / transfer suggestions
        rb = compute_rebalancing(comp, active_systems) if _heavy_ok else pd.DataFrame()
        if not rb.empty:
            with st.expander(f"🔄 Transfer Suggestions — {len(rb):,} rebalancing moves "
                             "(model has stock in one company, 0 in another)", expanded=False):
                st.markdown("<div class='alert-missing'>Move stock from a company that has it "
                            "to a company with 0 — balance the season across branches.</div>",
                            unsafe_allow_html=True)
                st.dataframe(rb.head(300), use_container_width=True, height=340)
                st.download_button("Download Transfer Suggestions Excel",
                                   to_excel_generic(rb, season_name, "Transfers"),
                                   f"transfers_{season_name}.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   key="rebal_dl")

        # Zero-stock (clearance / discontinue candidates)
        zs = zero_stock_models(comp)
        if not zs.empty:
            with st.expander(f"🪦 Zero-Stock Models — {len(zs):,} models with 0 units everywhere "
                             "(clearance / discontinue review)", expanded=False):
                st.markdown("<div class='alert-price'>These season models are out of stock in every "
                            "company. Review for re-order, discontinue, or removal.</div>",
                            unsafe_allow_html=True)
                st.dataframe(zs.head(300), use_container_width=True, height=320)
                st.download_button("Download Zero-Stock Excel",
                                   to_excel_generic(zs, season_name, "ZeroStock"),
                                   f"zerostock_{season_name}.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   key="zero_dl")

        # Copyable text / WhatsApp summary
        with st.expander("📝 Text Summary (copy → paste to WhatsApp / email)", expanded=False):
            _summary = build_season_text_summary(comp, long_df, season_name, active_systems)
            st.text_area("Season summary", value=_summary, height=300, key="season_summary",
                         help="Select all → copy → paste anywhere.")
            st.download_button("Download .txt", _summary.encode("utf-8"),
                               f"season_summary_{season_name}.txt", "text/plain",
                               key="summary_txt_dl")

        # ── View toggle ──
        st.markdown("<div class='section-tag'>Comparison Matrix</div>", unsafe_allow_html=True)
        view = st.radio("View", ["🏢 Company-wise", "🏬 Branch-wise", "📏 Size-wise"],
                        horizontal=True, label_visibility="collapsed")
        search = st.text_input("Search model / product", placeholder="e.g. XP6013", key="matrix_search").strip()

        if view.startswith("🏢"):
            show_df = comp.copy()
            only_diff = st.checkbox("Only differences (systems disagree)", value=False)
            if only_diff:
                show_df = only_differences(show_df, active_systems)
            if search:
                q = search.lower()
                m = (show_df["Model Code"].astype(str).str.lower().str.contains(q, regex=False)
                     | show_df["Product"].astype(str).str.lower().str.contains(q, regex=False))
                show_df = show_df[m]
            st.dataframe(show_df.head(200), use_container_width=True, height=560)
            st.caption(f"Showing {min(len(show_df),200):,} of {len(show_df):,} models. Full data in Excel.")
            dca, dcb = st.columns(2)
            dca.download_button("Download Company-wise Excel", to_excel_generic(show_df, season_name, "Company"),
                                f"season_company_{season_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="comp_dl", use_container_width=True)
            dcb.download_button("Download CSV", show_df.to_csv(index=False).encode("utf-8-sig"),
                                f"season_company_{season_name}.csv", "text/csv",
                                key="comp_csv", use_container_width=True)
        elif view.startswith("🏬"):
            branch_df = build_branch_matrix(long_df)
            if branch_df.empty:
                st.info("No branch data.")
            else:
                branch_cols = [c for c in branch_df.columns if " | " in c]
                sys_options = sorted({c.split(" | ")[0] for c in branch_cols})
                sel = st.multiselect("Filter companies", options=sys_options, default=sys_options, key="branch_sys_filter")
                keep_cols = ["Model Code", "Product", "Year"] + [c for c in branch_cols if c.split(" | ")[0] in sel] + ["Total"]
                view_df = branch_df[keep_cols].copy()
                fbc = [c for c in keep_cols if " | " in c]
                view_df["Total"] = view_df[fbc].sum(axis=1).astype(int)
                if search:
                    q = search.lower()
                    m = (view_df["Model Code"].astype(str).str.lower().str.contains(q, regex=False)
                         | view_df["Product"].astype(str).str.lower().str.contains(q, regex=False))
                    view_df = view_df[m]
                view_df = view_df.sort_values(["Total", "Model Code"], ascending=[False, True]).reset_index(drop=True)
                st.dataframe(view_df.head(200), use_container_width=True, height=560)
                st.caption(f"Showing {min(len(view_df),200):,} of {len(view_df):,} models · "
                           f"{len(fbc)} branch columns. Full data in Excel.")
                dba, dbb = st.columns(2)
                dba.download_button("Download Branch-wise Excel", to_excel_generic(view_df, season_name, "Branch"),
                                    f"season_branch_{season_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key="branch_dl", use_container_width=True)
                dbb.download_button("Download CSV", view_df.to_csv(index=False).encode("utf-8-sig"),
                                    f"season_branch_{season_name}.csv", "text/csv",
                                    key="branch_csv", use_container_width=True)
        else:
            # Size-wise pivot (base model × size, summed across companies & branches)
            size_df, size_cols = build_size_pivot(long_df)
            if size_df.empty:
                st.info("No size suffixes detected in model codes (e.g. XP6013-M). "
                        "Size view works when codes end with -S / -M / -L / -XL / -XXL etc.")
            else:
                sm1, sm2, sm3 = st.columns(3)
                sm1.metric("Base Models", f"{size_df['Base Model'].nunique():,}")
                sm2.metric("Total Units", f"{int(size_df['Total'].sum()):,}")
                sm3.metric("Sizes Found", f"{len(size_cols)}")
                sdf = size_df.copy()
                if search:
                    q = search.lower()
                    m = (sdf["Base Model"].astype(str).str.lower().str.contains(q, regex=False)
                         | sdf["Product"].astype(str).str.lower().str.contains(q, regex=False))
                    sdf = sdf[m]
                st.dataframe(sdf.head(200), use_container_width=True, height=560)
                st.caption(f"Showing {min(len(sdf),200):,} of {len(sdf):,} base models · sizes: {', '.join(size_cols)}")
                dsa, dsb = st.columns(2)
                dsa.download_button("Download Size-wise Excel", to_excel_generic(sdf, season_name, "Sizes"),
                                    f"season_sizes_{season_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key="size_dl", use_container_width=True)
                dsb.download_button("Download CSV", sdf.to_csv(index=False).encode("utf-8-sig"),
                                    f"season_sizes_{season_name}.csv", "text/csv",
                                    key="size_csv", use_container_width=True)

        # ── Combined workbook (all views in one file) — built on demand only ──
        st.markdown("<div class='section-tag'>Full Export</div>", unsafe_allow_html=True)
        if st.checkbox("Prepare combined workbook (Company + Branch + Size + Transfers + Zero-Stock)",
                       value=False, key="prep_full"):
            with st.spinner("Building combined workbook..."):
                _branch_full = build_branch_matrix(long_df)
                _size_full, _ = build_size_pivot(long_df)
                _rebal_full = compute_rebalancing(comp, active_systems) if len(comp) <= HEAVY_COMPUTE_ROW_CAP else pd.DataFrame()
                _zero_full = zero_stock_models(comp)
                _wb = to_excel_workbook(
                    [("Company", comp), ("Branch", _branch_full), ("Sizes", _size_full),
                     ("Transfers", _rebal_full), ("ZeroStock", _zero_full)],
                    season_name)
            st.download_button(
                "⬇️ Download EVERYTHING (one Excel)",
                _wb,
                f"season_full_{season_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="full_dl", use_container_width=True)


        if diag:
            with st.expander("Fetch Debug"):
                for sys, dbg in st.session_state.get("fetch_debug", {}).items():
                    st.markdown(f"**{get_system_name(sys)}**")
                    for k, v in dbg.items():
                        st.write(f"{k}: {v}")
                    st.write("---")

        if st.button("Clear", type="secondary"):
            for k in ["long_df", "company_matrix", "season_name", "fetch_debug"]:
                st.session_state.pop(k, None)
            st.rerun()


restore_session()
if not st.session_state.authenticated:
    show_login()
else:
    show_dashboard()
