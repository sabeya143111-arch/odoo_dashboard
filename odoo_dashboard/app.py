"""
SWAG Season Comparison Dashboard v9
New in v9 (smart):
1. SEASON TYPE MODE — type/pick "Winter" and it pulls EVERY year of that type
   (Winter 24, 23, 22 ...) from EVERY company, then aggregates.
2. YEAR column — each product row shows which season-year it belongs to.
3. On-hand only by default ("jo on hand hai") + a toggle to also show zero stock.
4. Data-correctness fixes:
   - Label collision fix: two season records with the same display name are BOTH
     fetched now (no silent overwrite -> no missing products).
   - Limit-hit warning: if a fetch hits its row cap, it is flagged as PARTIAL.
   - Optional warehouse/location context for a correct qty_available per system.
   - Exact mode no longer over-matches: if a year is given it won't grab other years.
5. Stock Value per system (qty x price) summary.
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

# ─── Price difference threshold (%) — alert if it exceeds this ───
PRICE_DIFF_THRESHOLD_PCT = 10.0


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
    # word-boundary check for short codes so "ss"/"aw" don't false-match inside words
    for words, canon in SEASON_TYPE_HINTS:
        for w in words:
            if len(w) <= 2:
                if re.search(rf"\b{re.escape(w)}\b", s):
                    return canon
            elif w in s:
                return canon
    return None


def season_year(label):
    """Return a 4-digit year string from a label, or '' if none."""
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


def get_stock_context(cfg):
    """Optional warehouse/location context so qty_available is computed
    for the right branch instead of the API user's default."""
    ctx = {}
    if not cfg:
        return ctx
    wid = cfg.get("warehouse_id")
    lid = cfg.get("location_id")
    cid = cfg.get("company_id")
    try:
        if wid:
            ctx["warehouse"] = int(wid)
        if lid:
            ctx["location"] = int(lid)
        if cid:
            ctx["allowed_company_ids"] = [int(cid)]
            ctx["force_company"] = int(cid)
    except Exception:
        pass
    return ctx


@st.cache_resource
def _proxy(url, ep):
    return xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/{ep}", allow_none=True)


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
            ftype = finfo.get("type", "")
            relation = finfo.get("relation", "") or ""
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
        audit["error"] = auth_res.get("error", "Authentication failed")
        return audit

    uid = auth_res["uid"]
    url, db, api_key = cfg["url"], cfg["db"], cfg["api_key"]
    candidates = []

    AUDIT_MODELS = ["product.template"]

    for model in AUDIT_MODELS:
        try:
            fields_meta = _execute(url, db, uid, api_key, model, "fields_get", [],
                                   {"attributes": ["string", "type", "relation", "store"]})
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

        sample_ids = []
        for domain_attempt in [[], [[1, "=", 1]]]:
            try:
                sample_recs = _execute(url, db, uid, api_key, model, "search_read",
                                       domain_attempt,
                                       {"fields": ["id"], "limit": AUDIT_SAMPLE_LIMIT})
                if sample_recs:
                    sample_ids = [r["id"] for r in sample_recs]
                    break
            except Exception as e:
                audit["fetch_errors"].append(f"search_ids/{model}/{domain_attempt}: {e}")

        audit["sample_ids_loaded"] += len(sample_ids)

        product_records = []
        if sample_ids:
            field_list = list(eligible_fields.keys())
            chunk_size = 60
            fetched_recs = {}

            for i in range(0, len(field_list), chunk_size):
                chunk_fields = field_list[i:i + chunk_size]
                try:
                    recs = _execute(url, db, uid, api_key, model, "search_read",
                                    safe_domain([["id", "in", sample_ids]]),
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

        for fname, finfo in eligible_fields.items():
            ftype = finfo.get("type", "")
            relation = finfo.get("relation", "") or ""
            flabel = finfo.get("string", fname)

            name_score = score_field_name(fname, flabel)
            rel_score = score_relation_model(relation)

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

            if relation and relation in BLACKLIST_RELATION_MODELS:
                candidate["rejection_reason"] = f"Blacklisted relation: {relation}"
                candidate["total_score"] = name_score + rel_score
                candidates.append(candidate)
                continue

            if not product_records:
                candidate["rejection_reason"] = "No product records loaded (name-only score)"
                candidate["total_score"] = name_score + rel_score
                candidates.append(candidate)
                continue

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
        if (
            best["name_score"] >= 25
            or best["season_like_direct_count"] > 0
            or probe.get("season_like_count", 0) > 0
            or best["data_score"] > 0
        ):
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
                all_systems_info[sys] = {
                    "model": best["model"],
                    "field": best["field_name"],
                    "ftype": best["field_type"],
                    "relation": best["relation_model"],
                    "seasons": seasons,   # list of (value, label) — kept as a LIST (no collision)
                }

    return all_systems_info, audits


def resolve_season_values_for_system(query, sys_info, mode="type"):
    """
    Returns (stored_values, matched_labels, error).

    mode = "type"  -> match EVERY season whose type == query's type (all years).
    mode = "exact" -> match a specific season; if the query carries a year it will
                      NOT spill over into other years.

    Works on the seasons LIST directly so two records sharing a display label are
    BOTH returned (no dict overwrite => no silently dropped products).
    """
    seasons = sys_info.get("seasons", [])   # [(value, label), ...]
    if not seasons:
        return [], [], "No seasons available"

    out_vals, out_lbls, seen = [], [], set()

    def add(val, lbl):
        key = (val, lbl)
        if key not in seen:
            seen.add(key)
            out_vals.append(val)
            out_lbls.append(lbl)

    q_norm = season_norm(query)
    q_type = season_type_only(query)
    q_year = season_year(query)

    if mode == "type":
        # All years of this season type, across the whole system.
        if not q_type:
            return [], [], f"'{query}' is not a recognized season type"
        for val, lbl in seasons:
            if season_type_only(lbl) == q_type:
                add(val, lbl)
        if out_vals:
            return out_vals, out_lbls, None
        return [], [], f"No '{q_type}' seasons found"

    # ---- exact mode ----
    # 1) exact label
    for val, lbl in seasons:
        if lbl == query:
            add(val, lbl)
    if out_vals:
        return out_vals, out_lbls, None

    # 2) normalized exact
    for val, lbl in seasons:
        if season_norm(lbl) == q_norm:
            add(val, lbl)
    if out_vals:
        return out_vals, out_lbls, None

    # 3) signature (type + year) — only when a year is present, so years don't mix
    if q_type and q_year:
        sig = season_signature(query)
        for val, lbl in seasons:
            if season_signature(lbl) == sig:
                add(val, lbl)
        if out_vals:
            return out_vals, out_lbls, None
        return [], [], f"Season not found: {query}"

    # 4) no year given -> treat like a type match (all years)
    if q_type:
        for val, lbl in seasons:
            if season_type_only(lbl) == q_type:
                add(val, lbl)
        if out_vals:
            return out_vals, out_lbls, None

    return [], [], f"Season not found: {query}"


def fetch_season_products(system_key, sys_info, query, mode="type", include_zero=False):
    cfg = get_system_config(system_key)
    if not cfg:
        return pd.DataFrame(), {"error": "No config"}
    auth = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth["ok"]:
        return pd.DataFrame(), {"error": "Auth failed: " + str(auth.get("error"))}

    uid = auth["uid"]
    url, db, api_key = cfg["url"], cfg["db"], cfg["api_key"]
    model = sys_info["model"]
    field = sys_info["field"]
    ftype = sys_info["ftype"]
    stock_ctx = get_stock_context(cfg)

    stored_values, matched_labels, resolve_err = resolve_season_values_for_system(query, sys_info, mode)

    # value -> label map (aligned lists). For many2one the value is the related id.
    val_to_label = {}
    for v, l in zip(stored_values, matched_labels):
        val_to_label[v] = l

    debug = {
        "system": system_key,
        "model": model,
        "field": field,
        "ftype": ftype,
        "mode": mode,
        "requested": query,
        "matched_labels": matched_labels,
        "matched_years": sorted({season_year(l) for l in matched_labels if season_year(l)}),
        "stored_values": stored_values,
        "resolve_error": resolve_err,
        "templates_found": 0,
        "products_found": 0,
        "limit_hit": False,
        "domain_used": None,
        "error": None,
    }

    if resolve_err or not stored_values:
        debug["error"] = resolve_err or "No matching stored values"
        return pd.DataFrame(), debug

    prod_fields = ["default_code", "barcode", "display_name",
                   "qty_available", "lst_price", "list_price", "product_tmpl_id"]

    try:
        if model == "product.template":
            tmpl_domain = (safe_domain([[field, "=", stored_values[0]]])
                           if len(stored_values) == 1
                           else safe_domain([[field, "in", stored_values]]))
            debug["domain_used"] = tmpl_domain

            tmpl_recs = _execute(
                url, db, uid, api_key, "product.template", "search_read",
                tmpl_domain, {"fields": ["id", field], "limit": TEMPLATE_FETCH_LIMIT}
            ) or []
            if len(tmpl_recs) >= TEMPLATE_FETCH_LIMIT:
                debug["limit_hit"] = True

            # template id -> season label (so each product knows its year)
            tmpl_season = {}
            for t in tmpl_recs:
                v = t.get(field)
                if isinstance(v, list) and v:
                    v = v[0]
                tmpl_season[t["id"]] = val_to_label.get(v, ", ".join(matched_labels))
            debug["templates_found"] = len(tmpl_season)

            if not tmpl_season:
                return pd.DataFrame(), debug

            tmpl_ids = list(tmpl_season.keys())
            products = []
            batch_size = 50
            for i in range(0, len(tmpl_ids), batch_size):
                batch = tmpl_ids[i:i + batch_size]
                try:
                    recs = _execute(
                        url, db, uid, api_key, "product.product", "search_read",
                        safe_domain([["product_tmpl_id", "in", batch]]),
                        {"fields": prod_fields, "limit": 20000, "context": stock_ctx}
                    )
                    if recs:
                        products.extend(recs)
                except Exception as e:
                    debug.setdefault("batch_errors", []).append(str(e))

            def season_of(p):
                tm = p.get("product_tmpl_id")
                tid = tm[0] if isinstance(tm, list) and tm else tm
                return tmpl_season.get(tid, ", ".join(matched_labels))

        else:
            prod_domain = (safe_domain([[field, "=", stored_values[0]]])
                           if len(stored_values) == 1
                           else safe_domain([[field, "in", stored_values]]))
            debug["domain_used"] = prod_domain

            products = _execute(
                url, db, uid, api_key, "product.product", "search_read",
                prod_domain,
                {"fields": prod_fields + [field], "limit": PRODUCT_FETCH_LIMIT, "context": stock_ctx}
            ) or []
            if len(products) >= PRODUCT_FETCH_LIMIT:
                debug["limit_hit"] = True

            def season_of(p):
                v = p.get(field)
                if isinstance(v, list) and v:
                    v = v[0]
                return val_to_label.get(v, ", ".join(matched_labels))

        if not products:
            return pd.DataFrame(), debug

        rows = []
        for p in products:
            qty = float(p.get("qty_available") or 0)
            if not include_zero and qty <= 0:      # on-hand only
                continue

            code = str(p.get("default_code") or "").strip()
            barcode = str(p.get("barcode") or "").strip()
            name = str(p.get("display_name") or "").strip()
            name_norm = normalize_text(name)

            # match key priority: code -> barcode -> name (more reliable cross-system)
            if code:
                match_key = code
            elif barcode:
                match_key = "bc::" + barcode
            elif name_norm:
                match_key = "name::" + name_norm
            else:
                continue

            price = p.get("lst_price")
            if price in (None, False):
                price = p.get("list_price")

            season_lbl = season_of(p)
            rows.append({
                "Match Key": match_key,
                "Model Code": code,
                "Product": name,
                "Season": season_lbl,
                "Year": season_year(season_lbl),
                "Qty": qty,
                "Price": float(price or 0),
                "System": system_key,
            })

        debug["products_found"] = len(rows)
        df = pd.DataFrame(rows)
        if df.empty:
            return df, debug

        df = (
            df.groupby(["Match Key", "Model Code", "Product", "Season", "Year", "System"],
                       as_index=False)
              .agg({"Qty": "sum", "Price": "max"})
        )
        return df, debug

    except Exception as e:
        debug["error"] = str(e)
        return pd.DataFrame(), debug


def _join_distinct(series):
    vals = []
    for x in series:
        x = str(x).strip()
        if x and x not in vals:
            vals.append(x)
    return ", ".join(sorted(vals))


def build_season_comparison_matrix(query, all_systems_info, mode="type", include_zero=False):
    all_data = {}
    debug_info = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(fetch_season_products, sys, info, query, mode, include_zero): sys
            for sys, info in all_systems_info.items()
        }
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

    product_map = combined.groupby("Match Key")["Product"].agg(
        lambda s: next((x for x in s if str(x).strip()), "")).reset_index()
    code_map = combined.groupby("Match Key")["Model Code"].agg(
        lambda s: next((x for x in s if str(x).strip()), "")).reset_index()
    season_map = combined.groupby("Match Key")["Season"].agg(_join_distinct).reset_index()
    year_map = combined.groupby("Match Key")["Year"].agg(_join_distinct).reset_index()

    qty_pivot = combined.pivot_table(index="Match Key", columns="System", values="Qty", aggfunc="sum", fill_value=0)
    price_pivot = combined.pivot_table(index="Match Key", columns="System", values="Price", aggfunc="max", fill_value=0)

    systems_all = [s for s in SYSTEM_KEYS if s in all_systems_info]
    for s in systems_all:
        if s not in qty_pivot.columns:
            qty_pivot[s] = 0
        if s not in price_pivot.columns:
            price_pivot[s] = 0
    if systems_all:
        qty_pivot = qty_pivot[systems_all]
        price_pivot = price_pivot[systems_all]

    qty_pivot.columns = [f"{c} Qty" for c in qty_pivot.columns]
    price_pivot.columns = [f"{c} Price" for c in price_pivot.columns]

    merged = qty_pivot.join(price_pivot, how="outer").reset_index()
    merged = merged.merge(code_map, on="Match Key", how="left")
    merged = merged.merge(product_map, on="Match Key", how="left")
    merged = merged.merge(season_map, on="Match Key", how="left")
    merged = merged.merge(year_map, on="Match Key", how="left")

    qty_cols = [c for c in merged.columns if c.endswith(" Qty")]
    price_cols = [c for c in merged.columns if c.endswith(" Price")]

    for col in qty_cols:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0).astype(int)
    for col in price_cols:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0).round(2)

    merged["Model Code"] = merged["Model Code"].fillna("").astype(str)
    merged["Product"] = merged["Product"].fillna("").astype(str)
    merged["Season"] = merged["Season"].fillna("").astype(str)
    merged["Year"] = merged["Year"].fillna("").astype(str)
    merged["Total Qty"] = merged[qty_cols].sum(axis=1).astype(int)

    ordered = ["Model Code", "Product", "Year", "Season"]
    for sys in SYSTEM_KEYS:
        if f"{sys} Qty" in merged.columns:
            ordered.append(f"{sys} Qty")
        if f"{sys} Price" in merged.columns:
            ordered.append(f"{sys} Price")
    ordered.append("Total Qty")

    merged = merged[[c for c in ordered if c in merged.columns]]
    merged = merged.sort_values(["Total Qty", "Model Code"], ascending=[False, True]).reset_index(drop=True)
    return merged, debug_info


# ══════════════════════════════════════════════════════
# SMART FEATURE: Cross-system missing products analysis
# ══════════════════════════════════════════════════════
def compute_missing_analysis(df, active_systems):
    """Products with stock in SWAG but 0 in at least one other system."""
    if df.empty or not active_systems:
        return pd.DataFrame()

    qty_cols = {s: f"{s} Qty" for s in active_systems if f"{s} Qty" in df.columns}
    swag_col = qty_cols.get("SWAG")
    if not qty_cols or not swag_col:
        return pd.DataFrame()

    has_swag_stock = df[swag_col] > 0
    missing_rows = []
    for sys, col in qty_cols.items():
        if sys == "SWAG":
            continue
        flagged = df[has_swag_stock & (df[col] == 0)][["Model Code", "Product", "Year", swag_col]].copy()
        if not flagged.empty:
            flagged["Missing In"] = get_system_name(sys)
            flagged.rename(columns={swag_col: "SWAG Qty"}, inplace=True)
            missing_rows.append(flagged[["Model Code", "Product", "Year", "SWAG Qty", "Missing In"]])

    if not missing_rows:
        return pd.DataFrame()

    return pd.concat(missing_rows, ignore_index=True).sort_values(
        "SWAG Qty", ascending=False).reset_index(drop=True)


# ══════════════════════════════════════════════════════
# SMART FEATURE: Price difference analysis
# ══════════════════════════════════════════════════════
def compute_price_alerts(df, active_systems):
    """Products whose price differs by more than the threshold across systems."""
    if df.empty:
        return pd.DataFrame()

    price_cols = {s: f"{s} Price" for s in active_systems if f"{s} Price" in df.columns}
    if len(price_cols) < 2:
        return pd.DataFrame()

    alerts = []
    for _, row in df.iterrows():
        prices = {s: float(row[col]) for s, col in price_cols.items() if float(row[col]) > 0}
        if len(prices) < 2:
            continue
        min_p, max_p = min(prices.values()), max(prices.values())
        if min_p == 0:
            continue
        diff_pct = ((max_p - min_p) / min_p) * 100
        if diff_pct >= PRICE_DIFF_THRESHOLD_PCT:
            alert = {
                "Model Code": row.get("Model Code", ""),
                "Product": row.get("Product", ""),
                "Min Price": round(min_p, 2),
                "Max Price": round(max_p, 2),
                "Diff %": round(diff_pct, 1),
                "Cheapest In": get_system_name(min(prices, key=prices.get)),
                "Highest In": get_system_name(max(prices, key=prices.get)),
            }
            for s, col in price_cols.items():
                alert[f"{get_system_name(s)} Price"] = float(row[col])
            alerts.append(alert)

    if not alerts:
        return pd.DataFrame()
    return pd.DataFrame(alerts).sort_values("Diff %", ascending=False).reset_index(drop=True)


# ══════════════════════════════════════════════════════
# SMART FEATURE: Stock value per system (qty x price)
# ══════════════════════════════════════════════════════
def compute_stock_value(df, active_systems):
    out = {}
    for s in active_systems:
        qcol, pcol = f"{s} Qty", f"{s} Price"
        if qcol in df.columns and pcol in df.columns:
            out[get_system_name(s)] = float((df[qcol] * df[pcol]).sum())
    return out


# ══════════════════════════════════════════════════════
# Season type list (for the smart "all years" dropdown)
# ══════════════════════════════════════════════════════
def build_unified_season_list(all_systems_info):
    all_labels = set()
    for sys, info in all_systems_info.items():
        for val, lbl in info.get("seasons", []):
            if str(lbl).strip():
                all_labels.add(str(lbl).strip())

    def sort_key(lbl):
        stype = season_type_only(lbl) or "ZZZ"
        yr = season_year(lbl)
        return (stype, -(int(yr) if yr else 0), lbl)

    return sorted(all_labels, key=sort_key)


def build_available_types(all_systems_info):
    """Which season types actually exist across all systems."""
    types_found = set()
    for sys, info in all_systems_info.items():
        for val, lbl in info.get("seasons", []):
            t = season_type_only(lbl)
            if t:
                types_found.add(t)
    order = ["SUMMER", "WINTER", "SPRING", "FALL"]
    return [t for t in order if t in types_found]


def to_excel_season_matrix(df, season_name):
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    buf = io.BytesIO()
    n_rows = len(df)
    heavy_style = n_rows <= 3000

    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Season Comparison")
        ws = writer.sheets["Season Comparison"]

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
        price_alert_fill = PatternFill("solid", fgColor="2A1500")

        max_row = ws.max_row
        max_col = ws.max_column
        ws.row_dimensions[1].height = 28

        col_names = [ws.cell(row=1, column=c).value for c in range(1, max_col + 1)]
        price_col_indices = [i + 1 for i, n in enumerate(col_names) if n and "Price" in str(n)]

        for col_num in range(1, max_col + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = hdr_fill
            cell.font = hdr_font
            cell.alignment = h_align
            cell.border = border

        if heavy_style:
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, max_row=max_row), start=2):
                is_price_alert = False
                if price_col_indices:
                    row_prices = [float(ws.cell(row=row_idx, column=ci).value or 0) for ci in price_col_indices]
                    nonzero = [p for p in row_prices if p > 0]
                    if len(nonzero) >= 2:
                        diff = ((max(nonzero) - min(nonzero)) / min(nonzero)) * 100
                        is_price_alert = diff >= PRICE_DIFF_THRESHOLD_PCT
                for cell in row:
                    cell.border = border
                    cell.font = norm_font
                    if is_price_alert and cell.column in price_col_indices:
                        cell.fill = price_alert_fill
                    elif cell.row % 2 == 0:
                        cell.fill = alt_fill
                    cell.alignment = num_align if isinstance(cell.value, (int, float)) else txt_align
                ws.row_dimensions[row[0].row].height = 18

        sample_last = min(max_row, 201)
        for col_num in range(1, max_col + 1):
            col_letter = get_column_letter(col_num)
            max_len = max((len(str(ws.cell(row=r, column=col_num).value or "")) for r in range(1, sample_last + 1)), default=8)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(max_col)}{max_row}"

        total_row = max_row + 1
        tc = ws.cell(row=total_row, column=1, value="TOTAL")
        tc.font = tot_font
        tc.fill = tot_fill
        tc.alignment = h_align

        for col_idx, col_name in enumerate(df.columns, start=1):
            if "Qty" in col_name or "Price" in col_name:
                col_letter = get_column_letter(col_idx)
                c = ws.cell(row=total_row, column=col_idx, value=f"=SUM({col_letter}2:{col_letter}{max_row})")
                c.font = tot_font
                c.fill = tot_fill
                c.alignment = num_align

        ws.sheet_properties.tabColor = "4AACB4"
        footer_row = total_row + 2
        fc = ws.cell(row=footer_row, column=1,
                     value=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Season: {season_name}")
        fc.font = Font(italic=True, color="4AACB4", size=9, name="Calibri")

    return buf.getvalue()


def _register_manual_system(sys, candidate):
    seasons = fetch_distinct_seasons_from_field(
        sys, candidate["model"], candidate["field_name"],
        candidate["field_type"], candidate["relation_model"]
    )
    if seasons:
        info = st.session_state.get("all_systems_info", {})
        info[sys] = {
            "model": candidate["model"],
            "field": candidate["field_name"],
            "ftype": candidate["field_type"],
            "relation": candidate["relation_model"],
            "seasons": seasons,
        }
        st.session_state["all_systems_info"] = info
        st.session_state["unified_seasons"] = build_unified_season_list(info)
        return len(seasons)
    return 0


def render_audit_report(audits):
    st.markdown("<div class='section-tag'>Deep Season Field Audit Report</div>", unsafe_allow_html=True)

    for sys in SYSTEM_KEYS:
        audit = audits.get(sys)
        if not audit:
            st.markdown(f"**{get_system_name(sys)}** — not audited")
            continue

        found = audit.get("confident", False)
        manual = audit.get("manual_pick_needed", False)
        icon = "✅" if found else ("⚠️" if manual else "❌")
        label = "Field Found" if found else ("Manual Pick Needed" if manual else "No Field Identified")

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
            pickable = [
                c for c in candidates
                if c["total_score"] > -49 and not (c.get("rejection_reason") or "").startswith("Blacklisted")
            ]

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
                        "Field": c["field_name"],
                        "Label": c["field_label"],
                        "Model": c["model"],
                        "Type": c["field_type"],
                        "Relation": c["relation_model"] or "",
                        "Non-Empty": c["non_empty_count"],
                        "Season-Like": c["season_like_direct_count"],
                        "Name Score": round(c["name_score"], 1),
                        "Data Score": round(c["data_score"], 1),
                        "Total": round(c["total_score"], 1),
                        "Samples": "; ".join(str(v) for v in c["sample_raw_values"][:3]),
                        "Rel Names": "; ".join((probe.get("sample_names") or [])[:3]),
                        "Note": c["rejection_reason"] or "—",
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


def show_login():
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="you@company.com")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Sign In", type="primary", use_container_width=True)

    if submit:
        if not email or not password:
            st.error("Fill both fields.")
            return
        if "LOGIN" not in st.secrets:
            st.error("Missing LOGIN section in secrets.toml")
            return
        cfg = st.secrets["LOGIN"]
        try:
            login_url = str(cfg.get("url", "")).rstrip("/")
            if login_url.endswith("/odoo"):
                login_url = login_url[:-5]
            proxy = xmlrpc.client.ServerProxy(login_url + "/xmlrpc/2/common", allow_none=True)
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
    lines = []
    for sys in SYSTEM_KEYS:
        name = get_system_name(sys)
        d = (fetch_debug or {}).get(sys)
        if d is not None:
            if d.get("error"):
                lines.append(f"❌ **{name}** — error: {d.get('error')}")
            elif d.get("resolve_error"):
                lines.append(f"⚠️ **{name}** — season did not match")
            elif d.get("products_found", 0) > 0:
                loaded += 1
                yrs = d.get("matched_years") or []
                yr_txt = f" [years: {', '.join(yrs)}]" if yrs else ""
                partial = "  ⚠️ PARTIAL (row limit hit)" if d.get("limit_hit") else ""
                lines.append(f"✅ **{name}** — {d.get('products_found', 0):,} on-hand products{yr_txt}{partial}")
            else:
                lines.append(f"⚠️ **{name}** — 0 on-hand products")
            continue

        if sys in all_systems_info:
            n_seasons = len(all_systems_info[sys].get("seasons", []))
            lines.append(f"🟢 **{name}** — season field found ({n_seasons:,} seasons), ready")
        else:
            a = audits.get(sys) or {}
            status = a.get("status")
            if status == "auth_failed":
                lines.append(f"❌ **{name}** — login/connection failed")
            elif status == "no_config":
                lines.append(f"❌ **{name}** — config missing")
            elif status in ("no_confident_field", "no_candidates"):
                lines.append(f"⚠️ **{name}** — season field could not be auto-detected")
            elif a.get("error"):
                lines.append(f"⚠️ **{name}** — {a.get('error')}")
            else:
                lines.append(f"⚪ **{name}** — status unknown")

    for ln in lines:
        st.markdown(ln)
    if fetch_debug:
        st.caption(f"Loaded data for {loaded} / {len(SYSTEM_KEYS)} companies.")


def show_dashboard():
    with st.sidebar:
        st.markdown("### SWAG")
        st.write(st.session_state.user_email)
        diag = st.checkbox("Diagnostics", value=False)
        include_zero = st.checkbox("Show zero-stock too", value=False,
                                   help="Off = on-hand only (qty > 0).")
        if st.button("Reload Seasons", use_container_width=True, type="secondary"):
            for k in ["all_systems_info", "audits", "audit_done", "season_matrix",
                      "season_name", "fetch_debug", "unified_seasons", "available_types"]:
                st.session_state.pop(k, None)
            st.rerun()
        if st.button("Logout", use_container_width=True, type="secondary"):
            do_logout()

    st.markdown("<div class='hero-title'>Season <em>Comparison</em></div>", unsafe_allow_html=True)

    if not st.session_state.get("audit_done"):
        with st.spinner("Loading seasons..."):
            all_systems_info, audits = run_full_discovery()
            st.session_state["all_systems_info"] = all_systems_info
            st.session_state["audits"] = audits
            st.session_state["audit_done"] = True
            st.session_state["unified_seasons"] = build_unified_season_list(all_systems_info)
            st.session_state["available_types"] = build_available_types(all_systems_info)
            for k in ["season_matrix", "season_name", "fetch_debug"]:
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

    # ══════════════════════════════════════════════════════
    # SEARCH SEASON
    # ══════════════════════════════════════════════════════
    st.markdown("<div class='section-tag'>Search Season</div>", unsafe_allow_html=True)

    search_mode = st.radio(
        "Selection mode",
        ["🌦️ Season type — ALL years, ALL companies", "🎯 Exact season"],
        horizontal=True,
        label_visibility="collapsed",
    )

    selected_query = ""
    resolve_mode = "type"

    if search_mode.startswith("🌦️"):
        resolve_mode = "type"
        col_pick, col_type = st.columns([2, 3])
        with col_pick:
            if available_types:
                pretty = [SEASON_TYPE_LABEL.get(t, t) for t in available_types]
                picked = st.selectbox(
                    "Season type",
                    options=[""] + available_types,
                    format_func=lambda t: "— Choose a type —" if t == "" else SEASON_TYPE_LABEL.get(t, t),
                    key="season_type_pick",
                )
                if picked:
                    selected_query = picked
            else:
                st.warning("No season types detected.")
        with col_type:
            typed = st.text_input(
                "...or type it",
                placeholder="winter / صيفي / summer",
                key="season_type_typed",
            )
            if typed.strip():
                t = season_type_only(typed.strip())
                if t:
                    selected_query = t
                else:
                    st.warning(f"'{typed}' is not a recognized season type")

    else:
        resolve_mode = "exact"
        if unified_seasons:
            selected_query = st.selectbox(
                "Season",
                options=[""] + unified_seasons,
                format_func=lambda x: "— Choose a season —" if x == "" else x,
                key="season_exact_pick",
            )
        else:
            st.warning("No seasons loaded. Reload.")

    # ── Preview: which years each company will pull ──
    if selected_query:
        title = (SEASON_TYPE_LABEL.get(selected_query, selected_query)
                 if resolve_mode == "type" else selected_query)
        st.markdown(f"<div class='info-banner'>Will fetch: {title}</div>", unsafe_allow_html=True)
        preview_cols = st.columns(len(all_systems_info))
        for i, (sys, info) in enumerate(all_systems_info.items()):
            vals, lbls, err = resolve_season_values_for_system(selected_query, info, resolve_mode)
            with preview_cols[i]:
                show = "<br>".join(lbls) if lbls else "—"
                st.markdown(f"<div class='season-match-box'>"
                            f"<div class='season-match-sys'>{get_system_name(sys)}</div>"
                            f"<div class='season-match-label'>{show}</div>"
                            f"</div>", unsafe_allow_html=True)

    col_btn, _ = st.columns([1, 4])
    with col_btn:
        compare_clicked = st.button("Compare", type="primary", disabled=not bool(selected_query))

    if compare_clicked and selected_query:
        with st.spinner("Fetching products from all companies..."):
            df_matrix, fetch_debug = build_season_comparison_matrix(
                selected_query, all_systems_info, resolve_mode, include_zero
            )
        st.session_state["fetch_debug"] = fetch_debug
        if df_matrix.empty:
            st.error("No products found for this season.")
        else:
            disp = SEASON_TYPE_LABEL.get(selected_query, selected_query) if resolve_mode == "type" else selected_query
            st.session_state["season_matrix"] = df_matrix
            st.session_state["season_name"] = disp
            for k in ["excel_bytes", "excel_for"]:
                st.session_state.pop(k, None)
            st.rerun()

    # ══════════════════════════════════════════════════════
    # RESULTS
    # ══════════════════════════════════════════════════════
    if "season_matrix" in st.session_state:
        df = st.session_state["season_matrix"]
        season_name = st.session_state["season_name"]
        active_systems = [s for s in SYSTEM_KEYS if f"{s} Qty" in df.columns]

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Models", f"{len(df):,}")
        c2.metric("Total Units", f"{int(df['Total Qty'].sum()):,}")
        c3.metric("Years Covered", ", ".join(sorted(
            {y for v in df["Year"] for y in str(v).split(", ") if y})) or "—")

        # ── Stock value per system ──
        stock_val = compute_stock_value(df, active_systems)
        if stock_val:
            with st.expander("💵 Stock Value per System (qty × price)", expanded=False):
                vcols = st.columns(len(stock_val))
                for i, (name, val) in enumerate(stock_val.items()):
                    vcols[i].metric(name, f"{val:,.0f}")

        # ── Missing products alert ──
        missing_df = compute_missing_analysis(df, active_systems)
        if not missing_df.empty:
            with st.expander(
                f"⚠️ Missing Products Alert — {len(missing_df):,} items in SWAG but not in the others",
                expanded=False
            ):
                st.markdown(
                    "<div class='alert-missing'>In stock in SWAG, 0 in another system — "
                    "possible sync issue or unlisted products</div>",
                    unsafe_allow_html=True
                )
                st.dataframe(missing_df.head(200), use_container_width=True, height=350)
                buf = io.BytesIO()
                missing_df.to_excel(buf, index=False)
                st.download_button("Download Missing Products Excel", data=buf.getvalue(),
                                   file_name=f"missing_products_{season_name}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   key="missing_download")

        # ── Price difference alert ──
        price_alerts_df = compute_price_alerts(df, active_systems)
        if not price_alerts_df.empty:
            with st.expander(
                f"💰 Price Difference Alert — {len(price_alerts_df):,} products with a {PRICE_DIFF_THRESHOLD_PCT:.0f}%+ gap",
                expanded=False
            ):
                st.markdown(
                    "<div class='alert-price'>Same product, different price across systems — "
                    "review pricing consistency</div>",
                    unsafe_allow_html=True
                )
                st.dataframe(price_alerts_df.head(200), use_container_width=True, height=350)
                buf = io.BytesIO()
                price_alerts_df.to_excel(buf, index=False)
                st.download_button("Download Price Alerts Excel", data=buf.getvalue(),
                                   file_name=f"price_alerts_{season_name}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   key="price_download")

        st.markdown("<div class='section-tag'>Comparison Matrix</div>", unsafe_allow_html=True)
        st.dataframe(df.head(50), use_container_width=True, height=600)
        st.caption(f"Preview: top 50 of {len(df):,} models. Full data is in the Excel.")

        if st.session_state.get("excel_for") != season_name or "excel_bytes" not in st.session_state:
            with st.spinner(f"Preparing Excel ({len(df):,} rows)..."):
                st.session_state["excel_bytes"] = to_excel_season_matrix(df, season_name)
                st.session_state["excel_for"] = season_name
        excel_bytes = st.session_state["excel_bytes"]

        st.download_button(
            label="Download Excel (full data)",
            data=excel_bytes,
            file_name=f"season_comparison_{season_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="season_download",
        )

        if diag:
            with st.expander("Fetch Debug"):
                for sys, dbg in st.session_state.get("fetch_debug", {}).items():
                    st.markdown(f"**{get_system_name(sys)}**")
                    if dbg.get("error"):
                        st.error(dbg["error"])
                    for k, v in dbg.items():
                        st.write(f"{k}: {v}")
                    st.write("---")

        if st.button("Clear", type="secondary"):
            for k in ["season_matrix", "season_name", "fetch_debug", "excel_bytes", "excel_for"]:
                st.session_state.pop(k, None)
            st.rerun()


restore_session()
if not st.session_state.authenticated:
    show_login()
else:
    show_dashboard()
