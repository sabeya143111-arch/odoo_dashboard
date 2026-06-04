"""
SWAG Season Comparison Dashboard v5
Fixes:
- _execute() now wraps the domain as [domain] so execute_kw receives it as the
  FIRST positional argument. Previously the domain was passed directly as the
  args list, which stripped one nesting level and produced a bare leaf that
  Odoo 17/18 Domain() rejects:
      ValueError: Domain() invalid item in domain: [8301, 8224, ...]
- safe_domain() already correctly preserves list values (["id","in",[...]])
- Audit loop uses only product.template to avoid GS1 smart_barcode addon conflict
- product.product still used for final product fetch (different domain format)
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
[data-testid="stMetricValue"] { font-family: 'Cormorant Garamond', serif; font-size: 44px; font-weight: 300; color: #fff; }
.stButton button { font-size: 9px; letter-spacing: 2px; text-transform: uppercase; border-radius: 100px !important; }
.stButton button[kind="primary"] { background: #4AACB4 !important; color: #060d0e !important; border: none !important; font-weight: 600 !important; padding: 10px 28px !important; }
.stButton button[kind="secondary"] { background: transparent !important; color: rgba(74,172,180,0.6) !important; border: 1px solid rgba(74,172,180,0.2) !important; }
.info-banner { background: rgba(74,172,180,0.04); border-left: 2px solid #4AACB4; padding: 10px 16px; font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase; color: rgba(74,172,180,0.7); }
.hero-title { font-size: 48px; font-weight: 700; color: #fff; letter-spacing: -1px; margin-bottom: 0; }
.hero-title em { color: #4AACB4; font-style: normal; }
.section-tag { font-size: 9px; letter-spacing: 4px; text-transform: uppercase; color: #4AACB4; margin: 20px 0 12px 0; display: flex; align-items: center; gap: 10px; }
.section-tag::before { content: ''; width: 20px; height: 1px; background: #4AACB4; }
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

# ── helpers ────────────────────────────────────────────────────────────────

def normalize_text(v):
    return re.sub(r"\s+", " ", str(v or "").strip()).lower()

def season_norm(v):
    s = normalize_text(v)
    return s.replace("-","").replace("_","").replace("/","").replace(" ","")

def should_skip_field(field_name, field_info):
    fn = field_name.lower()
    if field_name in ALWAYS_SKIP_FIELDS:
        return True
    for prefix in ALWAYS_SKIP_PREFIXES:
        if fn.startswith(prefix):
            return True
    if field_info.get("type","") not in USEFUL_FIELD_TYPES:
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

# ── safe_domain ────────────────────────────────────────────────────────────
# Converts domain conditions to plain lists safe for XML-RPC.
#   - 3-element conditions: ("field", "op", value)  →  ["field", "op", value]
#   - Logical operators:    "&", "|", "!"            →  passed through as-is
# Critically, 'value' is NOT iterated — list values like [1,2,3] are preserved
# for 'in' / 'not in' operators.

def safe_domain(conditions):
    result = []
    for c in conditions:
        if isinstance(c, (list, tuple)) and len(c) == 3:
            field, op, val = c
            result.append([field, op, val])
        else:
            # Logical operator strings like "&", "|", "!" or already-plain items
            result.append(c)
    return result

# ── session / auth ─────────────────────────────────────────────────────────

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
        email = params.get("u","")
        token = params.get("t","")
        if email and token and _verify_token(email, token):
            st.session_state.authenticated = True
            st.session_state.user_email = email
    except Exception:
        pass

_KEY_ALIASES = {"FASHION_LIMITS":"FASHIONLIMITS","FASHIONLIMITS":"FASHIONLIMITS"}

def _canonical_key(key):
    return _KEY_ALIASES.get(key, key)

def get_system_config(key):
    canonical = _canonical_key(key)
    cfg = st.secrets.get(canonical) or st.secrets.get(key)
    if not cfg:
        return None
    cfg = dict(cfg)
    url = str(cfg.get("url","")).rstrip("/")
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

def _auth(url, db, user, api_key):
    try:
        uid = _proxy(url,"common").authenticate(db, user, api_key, {})
        if uid:
            return {"ok":True,"uid":uid}
        return {"ok":False,"error":"BAD_CREDENTIALS"}
    except Exception as e:
        return {"ok":False,"error":f"AUTH_EXCEPTION: {e}"}

def _execute(url, db, uid, api_key, model, method, domain, kw):
    # FIX (v5): execute_kw expects the positional-args list as its 6th argument,
    # and for search_read/search/etc. the domain must be the FIRST element of
    # that list -> [domain]. The old code passed `domain` directly as the args
    # list, which stripped one nesting level: a proper domain [["id","in",[...]]]
    # collapsed into the bare leaf ["id","in",[...]], and Odoo 17/18 Domain()
    # rejected the ID list with:
    #     ValueError: Domain() invalid item in domain: [8301, 8224, ...]
    # Wrapping as [domain] makes Odoo receive the domain at the correct depth.
    return _proxy(url,"object").execute_kw(db, uid, api_key, model, method, [domain], kw)

# ── field browser (diagnostic) ─────────────────────────────────────────────

def browse_fields_for_system(system_key):
    """Return all eligible fields with name scores — no product data needed."""
    cfg = get_system_config(system_key)
    if not cfg:
        return None, "No config"
    auth = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth["ok"]:
        return None, auth["error"]

    uid = auth["uid"]
    url, db, api_key = cfg["url"], cfg["db"], cfg["api_key"]

    rows = []
    # only browse product.template to avoid GS1 smart_barcode addon on product.product
    for model in ["product.template"]:
        try:
            fields_meta = _execute(url, db, uid, api_key, model, "fields_get", [],
                                   {"attributes":["string","type","relation","store"]})
        except Exception as e:
            continue

        for fname, finfo in fields_meta.items():
            if should_skip_field(fname, finfo):
                continue
            ftype = finfo.get("type","")
            relation = finfo.get("relation","") or ""
            flabel = finfo.get("string", fname)
            name_score = score_field_name(fname, flabel)
            rel_score = score_relation_model(relation)
            rows.append({
                "Model": model,
                "Field": fname,
                "Label": flabel,
                "Type": ftype,
                "Relation": relation,
                "Name Score": name_score,
                "Rel Score": rel_score,
                "Total Score": name_score + rel_score,
            })

    if not rows:
        return None, "No eligible fields found"

    df = pd.DataFrame(rows).sort_values("Total Score", ascending=False).reset_index(drop=True)
    return df, None

# ── probe relation ─────────────────────────────────────────────────────────

def _probe_relation_model(url, db, uid, api_key, relation_model, related_ids):
    result = {"sample_names":[], "season_like_count":0, "total_fetched":0, "error":None}
    if not related_ids or not relation_model:
        return result
    unique_ids = list({i for i in related_ids if isinstance(i, int)})[:RELATION_SAMPLE_LIMIT]
    if not unique_ids:
        return result
    try:
        recs = _execute(url, db, uid, api_key, relation_model, "search_read",
                        safe_domain([["id","in",unique_ids]]),
                        {"fields":["id","name","display_name"],"limit":RELATION_SAMPLE_LIMIT})
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

# ── core audit ─────────────────────────────────────────────────────────────

def deep_season_audit_for_system(system_key):
    audit = {
        "system": system_key,
        "status": "pending",
        "error": None,
        "candidates": [],
        "best_field": None,
        "confident": False,
        "manual_pick_needed": False,
        "raw_field_count": 0,
        "eligible_field_count": 0,
        "sample_ids_loaded": 0,
        "product_records_loaded": 0,
        "fetch_errors": [],
    }

    cfg = get_system_config(system_key)
    if not cfg:
        audit["status"] = "no_config"
        audit["error"] = "No configuration found in secrets."
        return audit

    auth_res = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth_res["ok"]:
        audit["status"] = "auth_failed"
        audit["error"] = auth_res.get("error","Authentication failed")
        return audit

    uid = auth_res["uid"]
    url, db, api_key = cfg["url"], cfg["db"], cfg["api_key"]
    candidates = []

    # Use ONLY product.template for the audit loop.
    # product.product has a custom GS1 smart_barcode addon that overrides _search
    # and rejects our ["id","in",[...]] domain format, causing Fault errors.
    # product.template does not have this override and works correctly.
    # The season field lives on product.template anyway (season_id confirmed score=85).
    AUDIT_MODELS = ["product.template"]

    for model in AUDIT_MODELS:
        # 1. Get field metadata
        try:
            fields_meta = _execute(url, db, uid, api_key, model, "fields_get", [],
                                   {"attributes":["string","type","relation","store"]})
        except Exception as e:
            audit["fetch_errors"].append(f"fields_get/{model}: {e}")
            continue

        audit["raw_field_count"] += len(fields_meta)

        eligible_fields = {
            fname: finfo for fname, finfo in fields_meta.items()
            if not should_skip_field(fname, finfo)
        }
        audit["eligible_field_count"] += len(eligible_fields)

        if not eligible_fields:
            continue

        # 2. Get sample IDs — try multiple domain formats
        sample_ids = []
        for domain_attempt in [[], [[1,"=",1]]]:
            try:
                sample_recs = _execute(url, db, uid, api_key, model, "search_read",
                                       domain_attempt,
                                       {"fields":["id"], "limit": AUDIT_SAMPLE_LIMIT})
                if sample_recs:
                    sample_ids = [r["id"] for r in sample_recs]
                    break
            except Exception as e:
                audit["fetch_errors"].append(f"search_ids/{model}/{domain_attempt}: {e}")

        audit["sample_ids_loaded"] += len(sample_ids)

        # 3. Get product records (if we have IDs)
        product_records = []
        if sample_ids:
            field_list = list(eligible_fields.keys())
            chunk_size = 60
            fetched_recs = {}

            for i in range(0, len(field_list), chunk_size):
                chunk_fields = field_list[i:i+chunk_size]
                try:
                    recs = _execute(url, db, uid, api_key, model, "search_read",
                                    safe_domain([["id","in", sample_ids]]),
                                    {"fields": chunk_fields, "limit": AUDIT_SAMPLE_LIMIT})
                    for rec in recs:
                        rid = rec["id"]
                        if rid not in fetched_recs:
                            fetched_recs[rid] = {}
                        fetched_recs[rid].update(rec)
                except Exception as e:
                    audit["fetch_errors"].append(f"search_read/{model}/chunk{i}: {e}")

            product_records = list(fetched_recs.values())
            audit["product_records_loaded"] += len(product_records)

        # 4. Score each field
        for fname, finfo in eligible_fields.items():
            ftype    = finfo.get("type","")
            relation = finfo.get("relation","") or ""
            flabel   = finfo.get("string", fname)

            name_score = score_field_name(fname, flabel)
            rel_score  = score_relation_model(relation)

            candidate = {
                "field_name": fname,
                "field_label": flabel,
                "model": model,
                "field_type": ftype,
                "relation_model": relation,
                "name_score": name_score,
                "relation_model_score": rel_score,
                "data_score": 0,
                "total_score": 0,
                "non_empty_count": 0,
                "sample_raw_values": [],
                "season_like_direct_count": 0,
                "relation_probe": None,
                "rejection_reason": None,
            }

            # Skip blacklisted relation
            if relation and relation in BLACKLIST_RELATION_MODELS:
                candidate["rejection_reason"] = f"Blacklisted relation: {relation}"
                candidate["total_score"] = name_score + rel_score
                candidates.append(candidate)
                continue

            # If no product records, score by name only
            if not product_records:
                candidate["rejection_reason"] = "No product records loaded (name-only score)"
                candidate["total_score"] = name_score + rel_score
                candidates.append(candidate)
                continue

            # Score from data
            related_ids_seen = []
            for rec in product_records:
                val = rec.get(fname)
                if val is False or val is None:
                    continue

                if ftype == "many2one":
                    if isinstance(val, list) and len(val) >= 2:
                        related_ids_seen.append(val[0])
                        display = str(val[1])
                    elif isinstance(val, int) and val:
                        related_ids_seen.append(val)
                        display = str(val)
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
                candidates.append(candidate)
                continue

            # Probe many2one relation
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
        if (best["name_score"] >= 25
                or best["season_like_direct_count"] > 0
                or probe.get("season_like_count", 0) > 0
                or best["data_score"] > 0):
            audit["confident"] = True
        audit["status"] = "ok"
    elif candidates:
        audit["status"] = "no_confident_field"
        audit["manual_pick_needed"] = True
        audit["error"] = "Fields found but none scored positively. Use manual override below."
    else:
        audit["status"] = "no_candidates"
        audit["error"] = "No eligible fields at all — check filter logic."

    return audit

# ── season fetchers ────────────────────────────────────────────────────────

def fetch_distinct_seasons_from_field(system_key, model, field, ftype, relation):
    cfg = get_system_config(system_key)
    if not cfg:
        return []
    auth = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth["ok"]:
        return []
    uid = auth["uid"]
    url, db, api_key = cfg["url"], cfg["db"], cfg["api_key"]

    try:
        records = _execute(url, db, uid, api_key, model, "search_read",
                           safe_domain([[field,"!=",False]]),
                           {"fields":[field], "limit":50000})
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
                    unique_vals[val[0]] = str(val[1]).strip()
                    related_ids.append(val[0])
                elif isinstance(val, int) and val:
                    unique_vals[val] = str(val)
                    related_ids.append(val)
            else:
                unique_vals[val] = str(val).strip()

        if ftype == "many2one" and relation and related_ids:
            try:
                rel_recs = _execute(url, db, uid, api_key, relation, "search_read",
                                    safe_domain([["id","in",list(set(related_ids))]]),
                                    {"fields":["id","name","display_name"],
                                     "limit":len(set(related_ids))+10})
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
        system_key, best["model"], best["field_name"], best["field_type"], best["relation_model"])

# ── discovery ─────────────────────────────────────────────────────────────

def run_full_discovery():
    audits = {}
    all_systems_info = {}

    for sys in SYSTEM_KEYS:
        audit = deep_season_audit_for_system(sys)
        audits[sys] = audit

        if audit.get("confident") and audit.get("best_field"):
            seasons = fetch_distinct_seasons_from_audit(sys, audit)
            if seasons:
                best = audit["best_field"]
                label_to_value = {lbl: val for val, lbl in seasons}
                norm_to_value  = {season_norm(lbl): val for val, lbl in seasons}
                all_systems_info[sys] = {
                    "model": best["model"],
                    "field": best["field_name"],
                    "ftype": best["field_type"],
                    "relation": best["relation_model"],
                    "seasons": seasons,
                    "label_to_value": label_to_value,
                    "norm_to_value":  norm_to_value,
                }

    return all_systems_info, audits

# ── product fetch + matrix ─────────────────────────────────────────────────

def resolve_season_for_system(season_label, sys_info):
    label_to_value = sys_info["label_to_value"]
    norm_to_value  = sys_info["norm_to_value"]
    if season_label in label_to_value:
        return label_to_value[season_label], season_label, None
    n = season_norm(season_label)
    if n in norm_to_value:
        val = norm_to_value[n]
        matched = next((l for l,v in label_to_value.items() if v==val), season_label)
        return val, matched, None
    for lbl, val in label_to_value.items():
        if n in season_norm(lbl) or season_norm(lbl) in n:
            return val, lbl, None
    return None, None, f"Season not found: {season_label}"

def fetch_season_products(system_key, sys_info, season_label):
    cfg = get_system_config(system_key)
    if not cfg:
        return pd.DataFrame(), {"error":"No config"}
    auth = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth["ok"]:
        return pd.DataFrame(), {"error":"Auth failed: "+str(auth.get("error"))}

    uid = auth["uid"]
    url, db, api_key = cfg["url"], cfg["db"], cfg["api_key"]
    model = sys_info["model"]
    field = sys_info["field"]
    ftype = sys_info["ftype"]

    stored_value, matched_label, resolve_err = resolve_season_for_system(season_label, sys_info)
    debug = {
        "system":system_key,"model":model,"field":field,"ftype":ftype,
        "requested_label":season_label,"matched_label":matched_label,
        "stored_value":stored_value,"resolve_error":resolve_err,
        "templates_found":0,"products_found":0,"domain_used":None,"error":None,
    }

    if resolve_err:
        debug["error"] = resolve_err
        return pd.DataFrame(), debug

    try:
        if model == "product.template":
            tmpl_domain = safe_domain([[field,"=",stored_value]])
            debug["domain_used"] = tmpl_domain
            templates = _execute(url, db, uid, api_key, "product.template", "search_read",
                                 tmpl_domain, {"fields":["id"],"limit":50000})
            tmpl_ids = [t["id"] for t in templates] if templates else []
            debug["templates_found"] = len(tmpl_ids)
            if not tmpl_ids:
                return pd.DataFrame(), debug

            # For product.product fetch during final comparison, use template-based
            # domain instead of id-in domain to avoid GS1 smart_barcode addon conflict.
            # We search by product_tmpl_id which is a simple many2one filter, not an id list.
            # Split into batches of 50 template IDs to keep domain size manageable.
            all_products = []
            batch_size = 50
            for i in range(0, len(tmpl_ids), batch_size):
                batch = tmpl_ids[i:i+batch_size]
                try:
                    batch_products = _execute(
                        url, db, uid, api_key, "product.product", "search_read",
                        safe_domain([["product_tmpl_id","in",batch],["sale_ok","=",True]]),
                        {"fields":["default_code","display_name","qty_available","list_price"],
                         "limit":10000}
                    )
                    if batch_products:
                        all_products.extend(batch_products)
                except Exception as e:
                    # If GS1 addon still blocks, record the batch error and continue
                    debug.setdefault("batch_errors", []).append(str(e))
            products = all_products

        else:
            prod_domain = safe_domain([[field,"=",stored_value],["sale_ok","=",True]])
            debug["domain_used"] = prod_domain
            products = _execute(url, db, uid, api_key, "product.product", "search_read",
                                prod_domain,
                                {"fields":["default_code","display_name","qty_available","list_price"],
                                 "limit":200000})

        if not products:
            return pd.DataFrame(), debug

        rows = []
        for p in products:
            code = str(p.get("default_code") or "").strip()
            if not code:
                continue
            rows.append({
                "Model Code": code,
                "Product":    str(p.get("display_name") or "").strip(),
                "Qty":        float(p.get("qty_available") or 0),
                "Price":      float(p.get("list_price") or 0),
                "Season":     season_label,
                "System":     system_key,
            })

        debug["products_found"] = len(rows)
        df = pd.DataFrame(rows)
        if df.empty:
            return df, debug
        df = (df.groupby(["Model Code","Product","Season","System"], as_index=False)
                .agg({"Qty":"sum","Price":"max"}))
        return df, debug
    except Exception as e:
        debug["error"] = str(e)
        return pd.DataFrame(), debug

def build_season_comparison_matrix(selected_label, all_systems_info):
    all_data = {}
    debug_info = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch_season_products, sys, info, selected_label): sys
                   for sys, info in all_systems_info.items()}
        for fut in as_completed(futures):
            sys = futures[fut]
            try:
                df, dbg = fut.result()
                debug_info[sys] = dbg
                if not df.empty:
                    all_data[sys] = df
            except Exception as e:
                debug_info[sys] = {"error": str(e)}

    if not all_data:
        return pd.DataFrame(), debug_info

    combined = pd.concat(all_data.values(), ignore_index=True)
    product_map = (combined.groupby("Model Code")["Product"]
                   .agg(lambda s: next((x for x in s if str(x).strip()), ""))
                   .reset_index())

    qty_pivot   = combined.pivot_table(index="Model Code", columns="System", values="Qty",   aggfunc="sum", fill_value=0)
    price_pivot = combined.pivot_table(index="Model Code", columns="System", values="Price",  aggfunc="max", fill_value=0)
    qty_pivot.columns   = [f"{c} Qty"   for c in qty_pivot.columns]
    price_pivot.columns = [f"{c} Price" for c in price_pivot.columns]

    merged = qty_pivot.join(price_pivot, how="outer").reset_index()
    merged = merged.merge(product_map, on="Model Code", how="left")
    merged["Season"] = selected_label

    qty_cols   = [c for c in merged.columns if c.endswith(" Qty")]
    price_cols = [c for c in merged.columns if c.endswith(" Price")]

    for col in qty_cols:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0).astype(int)
    for col in price_cols:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0).round(2)

    merged["Product"]   = merged["Product"].fillna("").astype(str)
    merged["Total Qty"] = merged[qty_cols].sum(axis=1).astype(int)

    ordered = ["Model Code","Product","Season"]
    for sys in SYSTEM_KEYS:
        if f"{sys} Qty"   in merged.columns: ordered.append(f"{sys} Qty")
        if f"{sys} Price" in merged.columns: ordered.append(f"{sys} Price")
    ordered.append("Total Qty")

    merged = merged[[c for c in ordered if c in merged.columns]]
    merged = merged.sort_values(["Total Qty","Model Code"], ascending=[False,True]).reset_index(drop=True)
    return merged, debug_info

# ── excel export ───────────────────────────────────────────────────────────

def to_excel_season_matrix(df, season_name):
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Season Comparison")
        ws = writer.sheets["Season Comparison"]

        hdr_fill = PatternFill("solid", fgColor="060D0E")
        hdr_font = Font(bold=True, color="4AACB4", size=11, name="Calibri")
        h_align  = Alignment(horizontal="center", vertical="center")
        thin     = Side(border_style="thin", color="1A2A2C")
        border   = Border(left=thin, right=thin, top=thin, bottom=thin)
        alt_fill = PatternFill("solid", fgColor="0D1A1C")
        norm_font= Font(name="Calibri", size=10, color="8AACB0")
        num_align= Alignment(horizontal="right", vertical="center")
        txt_align= Alignment(horizontal="center", vertical="center")
        tot_fill = PatternFill("solid", fgColor="060D0E")
        tot_font = Font(bold=True, name="Calibri", color="D4A84B")

        max_row = ws.max_row
        max_col = ws.max_column
        ws.row_dimensions[1].height = 28

        for col_num in range(1, max_col+1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = hdr_fill; cell.font = hdr_font
            cell.alignment = h_align; cell.border = border

        for row in ws.iter_rows(min_row=2, max_row=max_row):
            for cell in row:
                cell.border = border; cell.font = norm_font
                if cell.row % 2 == 0: cell.fill = alt_fill
                cell.alignment = num_align if isinstance(cell.value,(int,float)) else txt_align
            ws.row_dimensions[row[0].row].height = 18

        for col_num in range(1, max_col+1):
            col_letter = get_column_letter(col_num)
            max_len = max((len(str(ws.cell(row=r,column=col_num).value or ""))
                           for r in range(1,max_row+1)), default=8)
            ws.column_dimensions[col_letter].width = min(max(max_len+3,12),45)

        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(max_col)}{max_row}"

        total_row = max_row + 1
        tc = ws.cell(row=total_row, column=1, value="TOTAL")
        tc.font = tot_font; tc.fill = tot_fill; tc.alignment = h_align

        for col_idx, col_name in enumerate(df.columns, start=1):
            if "Qty" in col_name or "Price" in col_name:
                col_letter = get_column_letter(col_idx)
                c = ws.cell(row=total_row, column=col_idx,
                            value=f"=SUM({col_letter}2:{col_letter}{max_row})")
                c.font = tot_font; c.fill = tot_fill; c.alignment = num_align

        ws.sheet_properties.tabColor = "4AACB4"
        footer_row = total_row + 2
        fc = ws.cell(row=footer_row, column=1,
                     value=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Season: {season_name}")
        fc.font = Font(italic=True, color="4AACB4", size=9, name="Calibri")

    return buf.getvalue()

# ── UI helpers ─────────────────────────────────────────────────────────────

def _register_manual_system(sys, candidate):
    """Add a manually chosen field to all_systems_info."""
    seasons = fetch_distinct_seasons_from_field(
        sys, candidate["model"], candidate["field_name"],
        candidate["field_type"], candidate["relation_model"])
    if seasons:
        label_to_value = {lbl: val for val, lbl in seasons}
        norm_to_value  = {season_norm(lbl): val for val, lbl in seasons}
        info = st.session_state.get("all_systems_info", {})
        info[sys] = {
            "model":   candidate["model"],
            "field":   candidate["field_name"],
            "ftype":   candidate["field_type"],
            "relation":candidate["relation_model"],
            "seasons": seasons,
            "label_to_value": label_to_value,
            "norm_to_value":  norm_to_value,
        }
        st.session_state["all_systems_info"] = info
        return len(seasons)
    return 0

def render_audit_report(audits):
    st.markdown("<div class='section-tag'>Deep Season Field Audit Report</div>", unsafe_allow_html=True)

    for sys in SYSTEM_KEYS:
        audit = audits.get(sys)
        if not audit:
            st.markdown(f"**{get_system_name(sys)}** — not audited")
            continue

        found  = audit.get("confident", False)
        manual = audit.get("manual_pick_needed", False)
        icon   = "✅" if found else ("⚠️" if manual else "❌")
        label  = "Field Found" if found else ("Manual Pick Needed" if manual else "No Field Identified")

        with st.expander(f"{get_system_name(sys)}  —  {icon} {label}", expanded=not found):

            st.markdown(
                f"**Status:** `{audit['status']}` | "
                f"Raw fields: **{audit.get('raw_field_count','?')}** | "
                f"Eligible: **{audit.get('eligible_field_count','?')}** | "
                f"Sample IDs loaded: **{audit.get('sample_ids_loaded','?')}** | "
                f"Product records: **{audit.get('product_records_loaded','?')}**"
            )

            if audit.get("fetch_errors"):
                with st.expander("Fetch errors", expanded=False):
                    for e in audit["fetch_errors"]:
                        st.code(e)

            if audit.get("error"):
                st.warning(audit["error"])

            if audit.get("best_field"):
                best = audit["best_field"]
                probe = best.get("relation_probe") or {}
                st.success(
                    f"Best: `{best['model']}.{best['field_name']}` | "
                    f"type: {best['field_type']} | label: **{best['field_label']}** | "
                    f"score: {round(best['total_score'],1)}"
                )
                if best.get("relation_model"):
                    st.markdown(f"**Relation:** `{best['relation_model']}`")
                if probe.get("sample_names"):
                    st.markdown("**Related names:** " + " | ".join(probe["sample_names"][:10]))

            candidates = audit.get("candidates", [])
            pickable = [c for c in candidates
                        if c["total_score"] > -49 and not (c.get("rejection_reason") or "").startswith("Blacklisted")]

            if pickable and not found:
                st.markdown("---")
                st.markdown("**🔧 Manual field override**")
                field_options = {
                    f"{c['model']}.{c['field_name']} [{c['field_label']}] (score {round(c['total_score'],1)})": c
                    for c in pickable[:20]
                }
                chosen_label = st.selectbox(
                    "Choose the season field for this system",
                    list(field_options.keys()),
                    key=f"manual_{sys}",
                )
                chosen = field_options[chosen_label]
                if st.button(f"✓ Use this field for {get_system_name(sys)}", key=f"use_{sys}"):
                    n = _register_manual_system(sys, chosen)
                    if n:
                        st.success(f"Set! Found {n} seasons.")
                        st.rerun()
                    else:
                        st.error("No season values found with that field.")

            if candidates:
                rows = []
                for c in candidates[:40]:
                    probe = c.get("relation_probe") or {}
                    rows.append({
                        "Field":      c["field_name"],
                        "Label":      c["field_label"],
                        "Model":      c["model"],
                        "Type":       c["field_type"],
                        "Relation":   c["relation_model"] or "",
                        "Non-Empty":  c["non_empty_count"],
                        "Season-Like":c["season_like_direct_count"],
                        "Name Score": round(c["name_score"],1),
                        "Data Score": round(c["data_score"],1),
                        "Total":      round(c["total_score"],1),
                        "Samples":    "; ".join(str(v) for v in c["sample_raw_values"][:3]),
                        "Rel Names":  "; ".join((probe.get("sample_names") or [])[:3]),
                        "Note":       c["rejection_reason"] or "—",
                    })
                st.dataframe(pd.DataFrame(rows), use_container_width=True, height=420)

            if st.button(f"🔍 Browse ALL fields for {get_system_name(sys)}", key=f"browse_{sys}"):
                with st.spinner("Loading all fields..."):
                    df_fields, err = browse_fields_for_system(sys)
                if err:
                    st.error(err)
                else:
                    st.dataframe(df_fields, use_container_width=True, height=500)
                    st.caption("Pick a field from here and use the override above.")

# ── login / logout ─────────────────────────────────────────────────────────

def show_login():
    with st.form("login_form"):
        email    = st.text_input("Email", placeholder="you@company.com")
        password = st.text_input("Password", type="password")
        submit   = st.form_submit_button("Sign In", type="primary", use_container_width=True)

    if submit:
        if not email or not password:
            st.error("Fill both fields.")
            return
        if "LOGIN" not in st.secrets:
            st.error("Missing LOGIN section in secrets.toml")
            return
        cfg = st.secrets["LOGIN"]
        try:
            login_url = str(cfg.get("url","")).rstrip("/")
            if login_url.endswith("/odoo"):
                login_url = login_url[:-5]
            proxy = xmlrpc.client.ServerProxy(login_url+"/xmlrpc/2/common", allow_none=True)
            uid = proxy.authenticate(cfg["db"], email, password, {})
            if uid:
                token = _make_token(email)
                st.query_params["u"] = email
                st.query_params["t"] = token
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.rerun()
            else:
                st.error("Wrong email or password.")
        except Exception as e:
            st.error("Connection error: " + str(e))

def do_logout():
    try: st.query_params.clear()
    except Exception: pass
    st.session_state.authenticated = False
    st.session_state.user_email = ""
    st.rerun()

# ── main dashboard ─────────────────────────────────────────────────────────

def show_dashboard():
    with st.sidebar:
        st.markdown("### SWAG")
        st.write(st.session_state.user_email)
        if st.button("Logout", use_container_width=True, type="secondary"):
            do_logout()

    st.markdown("<div class='hero-title'>Season <em>Comparison</em></div>", unsafe_allow_html=True)

    st.markdown("<div class='section-tag'>Connected Systems</div>", unsafe_allow_html=True)
    badges = []
    for sys in SYSTEM_KEYS:
        cfg = get_system_config(sys)
        if cfg:
            ok = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])["ok"]
            status = "Online" if ok else "Offline"
        else:
            status = "No config"
        badges.append(
            f"<span style='background:rgba(74,172,180,0.1);padding:4px 12px;"
            f"border-radius:100px;font-size:10px;'>"
            f"{get_system_name(sys)}: {status}</span>"
        )
    st.markdown("<div style='display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px;'>"
                + "".join(badges) + "</div>", unsafe_allow_html=True)

    st.markdown("<div class='section-tag'>Season Discovery</div>", unsafe_allow_html=True)
    col_btn, col_info = st.columns([1,3])
    with col_btn:
        run_audit = st.button("Run Deep Season Audit", type="primary", use_container_width=True)
    with col_info:
        st.markdown(
            "<div class='info-banner'>Auto-detects season field. "
            "If auto-detect fails, use Browse ALL Fields + manual override per system.</div>",
            unsafe_allow_html=True)

    if run_audit or st.session_state.get("audit_done"):
        if run_audit or not st.session_state.get("all_systems_info"):
            with st.spinner("Running deep season field audit..."):
                all_systems_info, audits = run_full_discovery()
                st.session_state["all_systems_info"] = all_systems_info
                st.session_state["audits"] = audits
                st.session_state["audit_done"] = True
                for k in ["season_matrix","season_name","fetch_debug"]:
                    st.session_state.pop(k, None)

        all_systems_info = st.session_state["all_systems_info"]
        audits = st.session_state["audits"]

        render_audit_report(audits)

        if not all_systems_info:
            st.error("No season field identified yet. Use 🔍 Browse ALL Fields and manual override above.")
            return

        st.markdown("<div class='section-tag'>Compare Season</div>", unsafe_allow_html=True)

        global_seasons = sorted({lbl for info in all_systems_info.values()
                                  for _, lbl in info["seasons"]})
        if not global_seasons:
            st.warning("Season fields found but no values retrieved.")
            return

        selected_label = st.selectbox("Select Season", global_seasons, key="season_select")

        if st.button("Compare Season", type="primary"):
            with st.spinner("Fetching products from all systems..."):
                df_matrix, fetch_debug = build_season_comparison_matrix(selected_label, all_systems_info)

            if df_matrix.empty:
                st.error("No products found for this season.")
                with st.expander("Fetch Debug", expanded=True):
                    for sys, dbg in fetch_debug.items():
                        st.markdown(f"**{get_system_name(sys)}**")
                        for k, v in dbg.items():
                            st.write(f"{k}: {v}")
                        st.write("---")
            else:
                st.session_state["season_matrix"]  = df_matrix
                st.session_state["season_name"]    = selected_label
                st.session_state["fetch_debug"]    = fetch_debug
                st.rerun()

    if "season_matrix" in st.session_state:
        df = st.session_state["season_matrix"]
        season_name = st.session_state["season_name"]

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Models", f"{df['Model Code'].nunique():,}")
        c2.metric("Total Units",  f"{int(df['Total Qty'].sum()):,}")
        c3.metric("Systems with stock",
                  str(sum(1 for s in SYSTEM_KEYS
                          if f"{s} Qty" in df.columns and df[f"{s} Qty"].sum() > 0)))

        st.markdown("<div class='section-tag'>Comparison Matrix</div>", unsafe_allow_html=True)
        if len(df) > 200:
            st.info(f"Showing first 10 of {len(df)} rows. Download Excel for full data.")
            st.dataframe(df.head(10), use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)

        excel_bytes = to_excel_season_matrix(df, season_name)
        st.download_button(
            label="Download Excel",
            data=excel_bytes,
            file_name=f"season_comparison_{season_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="season_download",
        )

        with st.expander("Fetch Debug"):
            for sys, dbg in st.session_state.get("fetch_debug",{}).items():
                st.markdown(f"**{get_system_name(sys)}**")
                if dbg.get("error"): st.error(dbg["error"])
                for k, v in dbg.items(): st.write(f"{k}: {v}")
                st.write("---")

        if st.button("Clear Results", type="secondary"):
            for k in ["season_matrix","season_name","fetch_debug"]:
                st.session_state.pop(k, None)
            st.rerun()

# ── entry point ────────────────────────────────────────────────────────────

restore_session()
if not st.session_state.authenticated:
    show_login()
else:
    show_dashboard()
