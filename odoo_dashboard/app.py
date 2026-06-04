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
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;1,300&family=Outfit:wght@300;400;500;600;700&display=swap');
* , html , body , [class*="css"] { font-family: 'Outfit', sans-serif; }
.stApp { background: #060d0e !important; }
.block-container { padding-top: 1rem !important; max-width: 100% !important; }
section[data-testid="stSidebar"] { background: #060d0e !important; border-right: 1px solid rgba(74,172,180,0.1) !important; }
section[data-testid="stSidebar"] * { color: rgba(255,255,255,0.65) !important; }
[data-testid="stMetric"] { background: rgba(74,172,180,0.03); border: 1px solid rgba(74,172,180,0.08); border-radius: 4px; padding: 20px 24px; }
[data-testid="stMetricLabel"] { font-size: 8px; letter-spacing: 3px; text-transform: uppercase; color: rgba(255,255,255,0.25); }
[data-testid="stMetricValue"] { font-family: 'Cormorant Garamond', serif; font-size: 44px; font-weight: 300; color: #fff; }
.stButton button { font-size: 9px; letter-spacing: 2px; text-transform: uppercase; border-radius: 100px !important; }
.stButton button[kind="primary"] { background: #4AACB4 !important; color: #060d0e !important; border: none !important; font-weight: 700 !important; padding: 10px 28px !important; }
.stButton button[kind="secondary"] { background: transparent !important; color: rgba(74,172,180,0.75) !important; border: 1px solid rgba(74,172,180,0.2) !important; }
.hero-title { font-size: 48px; font-weight: 700; color: #fff; letter-spacing: -1px; margin-bottom: 0; }
.hero-title em { color: #4AACB4; font-style: normal; }
.section-tag { font-size: 9px; letter-spacing: 4px; text-transform: uppercase; color: #4AACB4; margin: 20px 0 12px 0; display: flex; align-items: center; gap: 10px; }
.section-tag::before { content: ''; width: 20px; height: 1px; background: #4AACB4; }
.small-note { font-size: 12px; color: rgba(255,255,255,0.55); }
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

PRICE_NAME_HINTS = [
    "price", "sale_price", "list_price", "lst_price", "selling",
    "retail", "srp", "mrp", "sale", "public_price",
    "x_sale_price", "x_studio_sale_price", "x_studio_price"
]

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_email = ""

_COOKIE_SECRET = "swag_2025_secure"

def normalize_text(v):
    return re.sub(r"\s+", " ", str(v or "").strip()).lower()

def season_norm(v):
    s = normalize_text(v)
    return s.replace("-", "").replace("_", "").replace("/", "").replace(" ", "")

SEASON_TYPE_HINTS = [
    (("صيفي", "صيف", "summer"), "SUMMER"),
    (("شتوي", "شتاء", "winter", "الشتوي"), "WINTER"),
    (("ربيعي", "ربيع", "spring"), "SPRING"),
    (("خريفي", "خريف", "fall", "autumn"), "FALL"),
]

def season_signature(label):
    s = normalize_text(label)
    stype = None
    for words, canon in SEASON_TYPE_HINTS:
        if any(w in s for w in words):
            stype = canon
            break
    if not stype:
        return None
    year2 = ""
    for d in re.findall(r"\d+", s):
        if len(d) >= 2:
            year2 = d[-2:]
            break
        elif len(d) == 1:
            year2 = d.zfill(2)
    return stype + year2

def season_type_only(label):
    s = normalize_text(label)
    for words, canon in SEASON_TYPE_HINTS:
        if any(w in s for w in words):
            return canon
    return None

def extract_year_from_label(label):
    s = str(label or "").strip()
    nums = re.findall(r"\d{2,4}", s)
    if not nums:
        return ""
    val = nums[-1]
    if len(val) == 4:
        return val
    if len(val) == 2:
        return val
    if len(val) == 1:
        return val.zfill(2)
    return ""

def extract_best_year_from_labels(labels):
    years = []
    for lbl in labels or []:
        y = extract_year_from_label(lbl)
        if y:
            years.append(y)
    years = list(dict.fromkeys(years))
    return ", ".join(years)

def should_skip_field(field_name, field_info):
    fn = field_name.lower()
    if field_name in ALWAYS_SKIP_FIELDS:
        return True
    for prefix in ALWAYS_SKIP_PREFIXES:
        if fn.startswith(prefix):
            return True
    if field_info.get("type", "") not in USEFUL_FIELD_TYPES and field_info.get("type", "") != "monetary":
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

def looks_like_price_field(field_name, field_label):
    txt = f"{field_name} {field_label or ''}".lower()
    return any(h in txt for h in PRICE_NAME_HINTS)

def score_price_field(field_name, field_label, field_type):
    score = 0
    txt = f"{field_name} {field_label or ''}".lower()
    if field_type not in ("float", "integer", "monetary"):
        return -20
    for hint in PRICE_NAME_HINTS:
        if hint in txt:
            score += 20
    if field_name in ("lst_price", "list_price"):
        score += 40
    if field_name.startswith("x_studio"):
        score += 5
    elif field_name.startswith("x_"):
        score += 3
    return score

def safe_domain(conditions):
    result = []
    for c in conditions:
        if isinstance(c, (list, tuple)) and len(c) == 3:
            field, op, val = c
            result.append([field, op, val])
        else:
            result.append(c)
    return result

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

def _execute_plain(url, db, uid, api_key, model, method, args=None, kw=None):
    args = args or []
    kw = kw or {}
    return _proxy(url, "object").execute_kw(db, uid, api_key, model, method, args, kw)

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

def get_model_fields(system_key, model):
    cfg = get_system_config(system_key)
    if not cfg:
        return None, "No config"
    auth = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth["ok"]:
        return None, auth["error"]
    uid = auth["uid"]
    url, db, api_key = cfg["url"], cfg["db"], cfg["api_key"]

    try:
        fields_meta = _execute_plain(
            url, db, uid, api_key, model, "fields_get", [],
            {"attributes": ["string", "type", "relation", "store"]}
        )
        return fields_meta, None
    except Exception as e:
        return None, str(e)

def discover_price_fields_for_system(system_key):
    rows = []
    for model in ["product.template", "product.product"]:
        fields_meta, err = get_model_fields(system_key, model)
        if err or not fields_meta:
            continue
        for fname, finfo in fields_meta.items():
            ftype = finfo.get("type", "")
            flabel = finfo.get("string", fname)
            if fname in ALWAYS_SKIP_FIELDS:
                continue
            if any(fname.lower().startswith(p) for p in ALWAYS_SKIP_PREFIXES):
                continue

            score = score_price_field(fname, flabel, ftype)
            if score > 0 or looks_like_price_field(fname, flabel):
                rows.append({
                    "Model": model,
                    "Field": fname,
                    "Label": flabel,
                    "Type": ftype,
                    "Score": score
                })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["Score", "Model"], ascending=[False, True]).reset_index(drop=True)

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

    for model in ["product.template"]:
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
        audit["error"] = "Fields found but none scored positively."
    else:
        audit["status"] = "no_candidates"
        audit["error"] = "No eligible fields found."

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
                                    {"fields": ["id", "name", "display_name"], "limit": len(set(related_ids)) + 10})
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

def run_full_discovery():
    audits = {}
    all_systems_info = {}

    for sys in SYSTEM_KEYS:
        audit = deep_season_audit_for_system(sys)
        audits[sys] = audit

        if audit.get("confident") and audit.get("best_field"):
            best = audit["best_field"]
            seasons = fetch_distinct_seasons_from_field(
                sys, best["model"], best["field_name"], best["field_type"], best["relation_model"]
            )
            if seasons:
                label_to_value = {lbl: val for val, lbl in seasons}
                norm_to_value = {season_norm(lbl): val for val, lbl in seasons}
                value_to_label = {str(val): lbl for val, lbl in seasons}

                all_systems_info[sys] = {
                    "model": best["model"],
                    "field": best["field_name"],
                    "ftype": best["field_type"],
                    "relation": best["relation_model"],
                    "seasons": seasons,
                    "label_to_value": label_to_value,
                    "norm_to_value": norm_to_value,
                    "value_to_label": value_to_label,
                }

    return all_systems_info, audits

def find_matching_season_labels(search_text, all_systems_info):
    search_n = normalize_text(search_text)
    rows = []

    for sys, info in all_systems_info.items():
        for val, lbl in info.get("seasons", []):
            lbl_n = normalize_text(lbl)
            matched = False

            if search_n and search_n in lbl_n:
                matched = True
            else:
                stype_search = season_type_only(search_text)
                stype_label = season_type_only(lbl)
                if stype_search and stype_label and stype_search == stype_label:
                    matched = True

            if matched:
                rows.append({
                    "System": sys,
                    "System Name": get_system_name(sys),
                    "Stored Value": val,
                    "Season Label": lbl,
                    "Season Year": extract_year_from_label(lbl),
                    "Signature": season_signature(lbl) or "",
                })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).drop_duplicates(subset=["System", "Season Label"]).reset_index(drop=True)
    df = df.sort_values(["Season Label", "System Name"]).reset_index(drop=True)
    return df

def get_product_price(p):
    candidate_fields = [
        "x_studio_sale_price",
        "x_sale_price",
        "sale_price",
        "price",
        "lst_price",
        "list_price",
        "price_unit",
        "x_studio_price",
    ]
    for f in candidate_fields:
        val = p.get(f)
        if val not in (None, False, ""):
            try:
                return float(val)
            except Exception:
                pass
    return 0.0

def fetch_template_price_map(url, db, uid, api_key, tmpl_ids):
    if not tmpl_ids:
        return {}

    field_candidates = [
        "id", "list_price", "lst_price", "x_studio_sale_price",
        "x_sale_price", "sale_price", "price", "x_studio_price"
    ]
    price_map = {}

    try:
        templates = _execute(
            url, db, uid, api_key, "product.template", "search_read",
            safe_domain([["id", "in", tmpl_ids]]),
            {"fields": field_candidates, "limit": len(tmpl_ids) + 100}
        )
        for t in templates:
            price_map[t["id"]] = get_product_price(t)
    except Exception:
        pass

    return price_map

def fetch_products_for_exact_labels(system_key, sys_info, selected_labels, search_text):
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

    label_to_value = sys_info["label_to_value"]

    exact_pairs = []
    for lbl in selected_labels:
        if lbl in label_to_value:
            exact_pairs.append((label_to_value[lbl], lbl))

    debug = {
        "system": system_key,
        "search_text": search_text,
        "selected_labels": selected_labels,
        "matched_exact_labels": [x[1] for x in exact_pairs],
        "matched_values": [x[0] for x in exact_pairs],
        "templates_found": 0,
        "products_found": 0,
        "error": None,
    }

    if not exact_pairs:
        debug["error"] = "No exact labels found in this system"
        return pd.DataFrame(), debug

    stored_values = [x[0] for x in exact_pairs]
    season_labels = [x[1] for x in exact_pairs]
    season_year = extract_best_year_from_labels(season_labels)

    try:
        product_fields = [
            "default_code", "display_name", "qty_available",
            "lst_price", "list_price", "price", "price_unit",
            "x_studio_sale_price", "x_sale_price", "sale_price", "x_studio_price",
            "product_tmpl_id"
        ]

        if model == "product.template":
            if len(stored_values) == 1:
                tmpl_domain = safe_domain([[field, "=", stored_values[0]]])
            else:
                tmpl_domain = safe_domain([[field, "in", stored_values]])

            templates = _execute(
                url, db, uid, api_key, "product.template", "search_read",
                tmpl_domain, {"fields": ["id", "name"], "limit": 50000}
            )
            tmpl_ids = [t["id"] for t in templates] if templates else []
            debug["templates_found"] = len(tmpl_ids)

            if not tmpl_ids:
                return pd.DataFrame(), debug

            tmpl_price_map = fetch_template_price_map(url, db, uid, api_key, tmpl_ids)

            all_products = []
            batch_size = 50
            for i in range(0, len(tmpl_ids), batch_size):
                batch = tmpl_ids[i:i + batch_size]
                batch_products = _execute(
                    url, db, uid, api_key, "product.product", "search_read",
                    safe_domain([["product_tmpl_id", "in", batch], ["sale_ok", "=", True]]),
                    {"fields": product_fields, "limit": 10000}
                )
                if batch_products:
                    all_products.extend(batch_products)
            products = all_products
        else:
            tmpl_price_map = {}
            if len(stored_values) == 1:
                prod_domain = safe_domain([[field, "=", stored_values[0]], ["sale_ok", "=", True]])
            else:
                prod_domain = safe_domain([[field, "in", stored_values], ["sale_ok", "=", True]])

            products = _execute(
                url, db, uid, api_key, "product.product", "search_read",
                prod_domain, {"fields": product_fields, "limit": 200000}
            )

        if not products:
            return pd.DataFrame(), debug

        rows = []
        for p in products:
            code = str(p.get("default_code") or "").strip()
            name = str(p.get("display_name") or "").strip()
            name_norm = normalize_text(name)

            if code:
                match_key = code
            elif name_norm:
                match_key = "name::" + name_norm
            else:
                continue

            price = get_product_price(p)
            tmpl_val = p.get("product_tmpl_id")
            tmpl_id = None
            if isinstance(tmpl_val, list) and tmpl_val:
                tmpl_id = tmpl_val[0]
            elif isinstance(tmpl_val, int):
                tmpl_id = tmpl_val

            if (price in (0, 0.0)) and tmpl_id in tmpl_price_map:
                price = tmpl_price_map.get(tmpl_id, 0.0)

            rows.append({
                "Match Key": match_key,
                "Model Code": code,
                "Product": name,
                "Qty": float(p.get("qty_available") or 0),
                "Price": float(price or 0),
                "Season Search": search_text,
                "Season Label": ", ".join(season_labels),
                "Season Year": season_year,
                "System": system_key,
            })

        debug["products_found"] = len(rows)
        df = pd.DataFrame(rows)
        if df.empty:
            return df, debug

        df = (
            df.groupby(
                ["Match Key", "Model Code", "Product", "Season Search", "Season Label", "Season Year", "System"],
                as_index=False
            ).agg({"Qty": "sum", "Price": "max"})
        )
        return df, debug

    except Exception as e:
        debug["error"] = str(e)
        return pd.DataFrame(), debug

def build_comparison_from_selected_labels(search_text, selected_matches_df, all_systems_info):
    all_data = {}
    debug_info = {}

    labels_by_system = {}
    for _, row in selected_matches_df.iterrows():
        sys = row["System"]
        lbl = row["Season Label"]
        labels_by_system.setdefault(sys, []).append(lbl)

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(fetch_products_for_exact_labels, sys, all_systems_info[sys], labels, search_text): sys
            for sys, labels in labels_by_system.items() if sys in all_systems_info
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

    product_map = (
        combined.groupby("Match Key")["Product"]
        .agg(lambda s: next((x for x in s if str(x).strip()), ""))
        .reset_index()
    )
    code_map = (
        combined.groupby("Match Key")["Model Code"]
        .agg(lambda s: next((x for x in s if str(x).strip()), ""))
        .reset_index()
    )
    season_map = (
        combined.groupby("Match Key")[["Season Search", "Season Label", "Season Year"]]
        .agg(lambda s: next((x for x in s if str(x).strip()), ""))
        .reset_index()
    )

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
    price_pivot.columns = [f"{c} Sale Price" for c in price_pivot.columns]

    merged = qty_pivot.join(price_pivot, how="outer").reset_index()
    merged = merged.merge(code_map, on="Match Key", how="left")
    merged = merged.merge(product_map, on="Match Key", how="left")
    merged = merged.merge(season_map, on="Match Key", how="left")

    qty_cols = [c for c in merged.columns if c.endswith(" Qty")]
    price_cols = [c for c in merged.columns if c.endswith(" Sale Price")]

    for col in qty_cols:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0).astype(int)
    for col in price_cols:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0).round(2)

    merged["Model Code"] = merged["Model Code"].fillna("").astype(str)
    merged["Product"] = merged["Product"].fillna("").astype(str)
    merged["Season Search"] = merged["Season Search"].fillna("").astype(str)
    merged["Season Label"] = merged["Season Label"].fillna("").astype(str)
    merged["Season Year"] = merged["Season Year"].fillna("").astype(str)
    merged["Total Qty"] = merged[qty_cols].sum(axis=1).astype(int)

    ordered = ["Model Code", "Product", "Season Search", "Season Label", "Season Year"]
    for sys in SYSTEM_KEYS:
        if f"{sys} Qty" in merged.columns:
            ordered.append(f"{sys} Qty")
        if f"{sys} Sale Price" in merged.columns:
            ordered.append(f"{sys} Sale Price")
    ordered.append("Total Qty")

    merged = merged[[c for c in ordered if c in merged.columns]]
    merged = merged.sort_values(["Total Qty", "Model Code"], ascending=[False, True]).reset_index(drop=True)
    return merged, debug_info

def to_excel_season_matrix(df, season_name):
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    buf = io.BytesIO()

    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Season Comparison")
        ws = writer.sheets["Season Comparison"]

        hdr_fill = PatternFill("solid", fgColor="060D0E")
        hdr_font = Font(bold=True, color="4AACB4", size=11, name="Calibri")
        h_align = Alignment(horizontal="center", vertical="center")
        thin = Side(border_style="thin", color="1A2A2C")
        border = Border(left=thin, right=thin, top=thin, bottom=thin)

        max_row = ws.max_row
        max_col = ws.max_column
        ws.row_dimensions[1].height = 28

        for col_num in range(1, max_col + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = hdr_fill
            cell.font = hdr_font
            cell.alignment = h_align
            cell.border = border

        for col_num in range(1, max_col + 1):
            col_letter = get_column_letter(col_num)
            max_len = max((len(str(ws.cell(row=r, column=col_num).value or "")) for r in range(1, min(max_row, 200) + 1)), default=8)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(max_col)}{max_row}"

    return buf.getvalue()

def discover_all_system_metadata(search_text, all_systems_info):
    report = {}
    for sys in SYSTEM_KEYS:
        sys_report = {
            "season_candidates": [],
            "price_candidates": [],
            "season_matches": [],
            "best_season_field": None,
            "best_price_field": None,
            "errors": []
        }

        audit = deep_season_audit_for_system(sys)
        if audit.get("best_field"):
            sys_report["best_season_field"] = audit["best_field"]

        for c in audit.get("candidates", [])[:20]:
            sys_report["season_candidates"].append({
                "field_name": c["field_name"],
                "field_label": c["field_label"],
                "model": c["model"],
                "field_type": c["field_type"],
                "relation_model": c["relation_model"],
                "score": round(c["total_score"], 2),
                "samples": c.get("sample_raw_values", [])[:5]
            })

        if sys in all_systems_info:
            seasons = all_systems_info[sys].get("seasons", [])
            search_norm = normalize_text(search_text)
            matches = []
            for val, lbl in seasons:
                if search_norm in normalize_text(lbl) or (
                    season_type_only(search_text) and season_type_only(lbl) == season_type_only(search_text)
                ):
                    matches.append({
                        "stored_value": val,
                        "label": lbl,
                        "year": extract_year_from_label(lbl),
                        "signature": season_signature(lbl)
                    })
            sys_report["season_matches"] = matches[:50]

        price_df = discover_price_fields_for_system(sys)
        if not price_df.empty:
            sys_report["price_candidates"] = price_df.head(20).to_dict("records")
            sys_report["best_price_field"] = sys_report["price_candidates"][0]

        report[sys] = sys_report
    return report

def render_collab_debugger(all_systems_info):
    st.markdown("<div class='section-tag'>Collab Inspector</div>", unsafe_allow_html=True)

    search_text = st.text_input(
        "Inspector search",
        value=st.session_state.get("search_text", "الشتوي"),
        key="collab_search_text",
        help="winter / الشتوي / صيفي / SS24"
    )

    if st.button("Scan all systems", key="scan_all_systems"):
        with st.spinner("Scanning systems..."):
            st.session_state["collab_report"] = discover_all_system_metadata(search_text, all_systems_info)

    if "collab_report" in st.session_state:
        report = st.session_state["collab_report"]
        for sys in SYSTEM_KEYS:
            data = report.get(sys, {})
            with st.expander(f"{get_system_name(sys)} — inspector", expanded=False):
                st.markdown("**Best Season Field**")
                st.json(data.get("best_season_field") or {})

                st.markdown("**Season Matches**")
                matches = pd.DataFrame(data.get("season_matches") or [])
                if not matches.empty:
                    st.dataframe(matches, use_container_width=True)
                else:
                    st.info("No season matches found.")

                st.markdown("**Top Season Candidates**")
                sc = pd.DataFrame(data.get("season_candidates") or [])
                if not sc.empty:
                    st.dataframe(sc, use_container_width=True, height=220)

                st.markdown("**Top Price Candidates**")
                pc = pd.DataFrame(data.get("price_candidates") or [])
                if not pc.empty:
                    st.dataframe(pc, use_container_width=True, height=220)

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
    lines = []
    loaded = 0
    for sys in SYSTEM_KEYS:
        name = get_system_name(sys)
        d = (fetch_debug or {}).get(sys)

        if d is not None:
            if d.get("error"):
                lines.append(f"❌ **{name}** — {d.get('error')}")
            elif d.get("products_found", 0) > 0:
                loaded += 1
                lines.append(f"✅ **{name}** — {d.get('products_found', 0):,} products")
            else:
                lines.append(f"⚠️ **{name}** — 0 products")
            continue

        if sys in all_systems_info:
            n = len(all_systems_info[sys].get("seasons", []))
            lines.append(f"🟢 **{name}** — season field mila ({n} seasons), compare ke liye ready")
        else:
            a = audits.get(sys) or {}
            if a.get("error"):
                lines.append(f"⚠️ **{name}** — {a.get('error')}")
            else:
                lines.append(f"⚪ **{name}** — season field not ready")

    for ln in lines:
        st.markdown(ln)
    if fetch_debug:
        st.caption(f"{loaded} / {len(SYSTEM_KEYS)} companies ka data load hua.")

def show_dashboard():
    with st.sidebar:
        st.markdown("### SWAG")
        st.write(st.session_state.user_email)
        diag = st.checkbox("Diagnostics", value=False)
        if st.button("Reload Seasons", use_container_width=True, type="secondary"):
            for k in [
                "all_systems_info", "audits", "audit_done", "season_matches_df",
                "selected_match_keys", "season_matrix", "season_name", "fetch_debug",
                "excel_bytes", "excel_for", "collab_report"
            ]:
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

    all_systems_info = st.session_state.get("all_systems_info", {})
    audits = st.session_state.get("audits", {})
    fetch_debug = st.session_state.get("fetch_debug", {})

    render_company_status(all_systems_info, audits, fetch_debug)

    if not all_systems_info:
        st.error("Kisi bhi company ka season field detect nahi hua.")
        return

    st.markdown("<div class='section-tag'>Search Season</div>", unsafe_allow_html=True)
    search_text = st.text_input("Season search", value=st.session_state.get("search_text", "الشتوي"), key="search_text")

    c1, c2 = st.columns([1, 1])

    with c1:
        if st.button("Find matching seasons", type="primary"):
            matches_df = find_matching_season_labels(search_text, all_systems_info)
            st.session_state["season_matches_df"] = matches_df
            st.session_state.pop("selected_match_keys", None)
            st.session_state.pop("season_matrix", None)
            st.session_state.pop("fetch_debug", None)

    with c2:
        if st.button("Clear result", type="secondary"):
            for k in ["season_matches_df", "selected_match_keys", "season_matrix", "fetch_debug", "excel_bytes", "excel_for"]:
                st.session_state.pop(k, None)
            st.rerun()

    if "season_matches_df" in st.session_state:
        matches_df = st.session_state["season_matches_df"]

        if matches_df.empty:
            st.error("Is search ke liye koi matching season label nahi mila.")
        else:
            st.success(f"{len(matches_df)} matching season labels mile.")
            display_df = matches_df.copy()
            display_df["Pick Key"] = display_df["System"] + " || " + display_df["Season Label"]

            st.dataframe(
                display_df[["System Name", "Season Label", "Season Year", "Signature"]],
                use_container_width=True,
                height=300
            )

            default_keys = display_df["Pick Key"].tolist()
            selected_keys = st.multiselect(
                "Jo exact season labels compare karne hain unko select rakho",
                options=display_df["Pick Key"].tolist(),
                default=default_keys,
                key="selected_match_keys"
            )

            if st.button("Compare exact selected seasons", type="primary", key="compare_exact"):
                selected_df = display_df[display_df["Pick Key"].isin(selected_keys)].copy()
                with st.spinner("Fetching exact season products..."):
                    df_matrix, fetch_debug = build_comparison_from_selected_labels(
                        search_text, selected_df, all_systems_info
                    )
                st.session_state["fetch_debug"] = fetch_debug
                if df_matrix.empty:
                    st.error("Selected exact seasons ke liye koi product nahi mila.")
                else:
                    st.session_state["season_matrix"] = df_matrix
                    st.session_state["season_name"] = search_text
                    st.rerun()

    if "season_matrix" in st.session_state:
        df = st.session_state["season_matrix"]
        season_name = st.session_state["season_name"]

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Models", f"{len(df):,}")
        c2.metric("Total Units", f"{int(df['Total Qty'].sum()):,}")
        c3.metric("Systems with stock", str(sum(1 for s in SYSTEM_KEYS if f"{s} Qty" in df.columns and df[f'{s} Qty'].sum() > 0)))

        st.markdown("<div class='section-tag'>Comparison Matrix</div>", unsafe_allow_html=True)
        st.dataframe(df.head(100), use_container_width=True, height=600)
        st.caption(f"Preview: top 100 of {len(df):,} rows.")

        if st.session_state.get("excel_for") != season_name or "excel_bytes" not in st.session_state:
            with st.spinner("Preparing Excel..."):
                st.session_state["excel_bytes"] = to_excel_season_matrix(df, season_name)
                st.session_state["excel_for"] = season_name

        st.download_button(
            label="Download Excel",
            data=st.session_state["excel_bytes"],
            file_name=f"season_comparison_{season_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="season_download"
        )

        if diag:
            with st.expander("Fetch Debug"):
                for sys, dbg in st.session_state.get("fetch_debug", {}).items():
                    st.markdown(f"**{get_system_name(sys)}**")
                    st.json(dbg)

    if diag:
        render_collab_debugger(all_systems_info)

restore_session()
if not st.session_state.authenticated:
    show_login()
else:
    show_dashboard()
