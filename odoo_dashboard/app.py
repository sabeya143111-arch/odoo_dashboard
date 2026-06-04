The markdown table explanation was accidentally included in the Python file. Here is the clean code only:

```python
"""
SWAG Season Comparison Dashboard – Deep Season Field Audit Mode
Read-only · Relation-model probing · Full candidate transparency
"""

import io
import re
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
section[data-testid="stSidebar"] {
    background: #060d0e !important;
    border-right: 1px solid rgba(74,172,180,0.1) !important;
}
section[data-testid="stSidebar"] * { color: rgba(255,255,255,0.6) !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #4AACB4 !important;
    font-size: 9px !important;
    letter-spacing: 4px !important;
    text-transform: uppercase !important;
}
[data-testid="stMetric"] {
    background: rgba(74,172,180,0.03);
    border: 1px solid rgba(74,172,180,0.08);
    border-radius: 4px;
    padding: 20px 24px;
}
[data-testid="stMetricLabel"] {
    font-size: 8px; letter-spacing: 3px; text-transform: uppercase;
    color: rgba(255,255,255,0.25);
}
[data-testid="stMetricValue"] {
    font-family: 'Cormorant Garamond', serif;
    font-size: 44px; font-weight: 300; color: #fff;
}
.stButton button {
    font-size: 9px; letter-spacing: 2px; text-transform: uppercase;
    border-radius: 100px !important;
}
.stButton button[kind="primary"] {
    background: #4AACB4 !important; color: #060d0e !important;
    border: none !important; font-weight: 600 !important;
    padding: 10px 28px !important;
}
.stButton button[kind="primary"]:hover {
    background: #2E8A91 !important; transform: translateY(-1px);
}
.stButton button[kind="secondary"] {
    background: transparent !important;
    color: rgba(74,172,180,0.6) !important;
    border: 1px solid rgba(74,172,180,0.2) !important;
}
.info-banner {
    background: rgba(74,172,180,0.04);
    border-left: 2px solid #4AACB4;
    padding: 10px 16px;
    font-size: 9px; letter-spacing: 1.5px;
    text-transform: uppercase; color: rgba(74,172,180,0.7);
}
.warn-banner {
    background: rgba(212,168,75,0.04);
    border-left: 2px solid #D4A84B;
    padding: 10px 16px;
    font-size: 9px; letter-spacing: 1.5px;
    text-transform: uppercase; color: rgba(212,168,75,0.7);
}
.hero-title {
    font-family: 'Tajawal', sans-serif;
    font-size: 48px; font-weight: 700; color: #fff;
    letter-spacing: -1px; margin-bottom: 0;
}
.hero-title em { color: #4AACB4; font-style: normal; }
.section-tag {
    font-size: 9px; letter-spacing: 4px; text-transform: uppercase;
    color: #4AACB4; margin: 20px 0 12px 0;
    display: flex; align-items: center; gap: 10px;
}
.section-tag::before {
    content: ''; width: 20px; height: 1px; background: #4AACB4;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
SYSTEM_KEYS = ["SWAG", "STOCK", "LAROUCHE", "DIFFC", "FASHIONLIMITS"]

SEASON_NAME_HINTS = [
    "season", "saison", "collection", "col",
    "mawsim", "fasil",
    "\u0645\u0648\u0633\u0645",
    "\u0627\u0644\u0645\u0648\u0633\u0645",
    "\u0641\u0635\u0644",
]

ARABIC_SEASON_WORDS = [
    "\u0635\u064a\u0641\u064a",
    "\u0634\u062a\u0648\u064a",
    "\u0631\u0628\u064a\u0639\u064a",
    "\u062e\u0631\u064a\u0641\u064a",
    "\u0635\u064a\u0641",
    "\u0634\u062a\u0627\u0621",
    "\u0631\u0628\u064a\u0639",
    "\u062e\u0631\u064a\u0641",
    "\u0645\u0648\u0633\u0645",
    "\u0641\u0635\u0644",
]

SEASON_CODE_PATTERNS = [
    r"\b(SS|AW|FW|SP|FA|SU|WI)\s*\d{2,4}\b",
    r"\b(S|W|F|A)\s*\d{2}\b",
    r"\b\d{2,4}\s*(SS|AW|FW|SP|FA)\b",
    r"\b(summer|winter|spring|fall|autumn)\b",
    r"\b(\u0635\u064a\u0641\u064a|\u0634\u062a\u0648\u064a|\u0631\u0628\u064a\u0639\u064a|\u062e\u0631\u064a\u0641\u064a)\b",
    r"\b(\u0635\u064a\u0641\u064a|\u0634\u062a\u0648\u064a|\u0631\u0628\u064a\u0639\u064a|\u062e\u0631\u064a\u0641\u064a)\s*\d{1,2}\b",
    r"\b\d{2,4}\s*(\u0635\u064a\u0641\u064a|\u0634\u062a\u0648\u064a|\u0631\u0628\u064a\u0639\u064a|\u062e\u0631\u064a\u0641\u064a)\b",
]
SEASON_VALUE_RE = re.compile(
    "|".join(SEASON_CODE_PATTERNS),
    re.IGNORECASE | re.UNICODE,
)

BLACKLIST_RELATION_MODELS = {
    "res.users", "res.partner", "res.company", "res.currency",
    "res.country", "res.lang", "res.groups",
    "uom.uom", "uom.category",
    "account.tax", "account.account", "account.journal",
    "mail.activity.type", "mail.template", "mail.alias",
    "product.category", "product.pricelist",
    "product.attribute", "product.attribute.value",
    "product.template.attribute.line",
    "product.template.attribute.value",
    "ir.attachment", "ir.model", "ir.model.fields",
    "ir.actions.act_window", "ir.ui.view", "ir.ui.menu",
    "ir.rule", "ir.sequence",
    "stock.location", "stock.warehouse", "stock.quant",
    "mrp.bom", "sale.order", "purchase.order",
}

USEFUL_FIELD_TYPES = {"many2one", "selection", "char", "text"}

ALWAYS_SKIP_FIELDS = {
    "__last_update", "write_date", "create_date", "write_uid", "create_uid",
    "display_name",
    "image_1920", "image_1024", "image_512", "image_256",
    "image_128", "image_small", "image_medium",
    "message_ids", "message_follower_ids", "message_channel_ids",
    "message_main_attachment_id", "message_has_error",
    "message_needaction", "message_attachment_count",
    "message_needaction_counter", "message_has_error_counter",
    "website_message_ids",
    "activity_ids", "activity_state", "activity_type_id",
    "activity_user_id", "activity_summary", "activity_date_deadline",
    "activity_exception_decoration", "activity_exception_icon",
    "mail_activity_state", "mail_activity_type_id", "mail_activity_ids",
    "rating_ids", "color", "sequence", "priority",
    "product_variant_count", "product_variant_ids",
    "product_template_attribute_line_ids", "attribute_line_ids",
    "can_image_1024_be_zoomed",
}

ALWAYS_SKIP_PREFIXES = (
    "mail_", "message_", "activity_", "website_",
    "image_", "rating_",
)

ALWAYS_SKIP_SUBSTRINGS = ("message", "attachment", "follower")

AUDIT_SAMPLE_LIMIT = 500
RELATION_SAMPLE_LIMIT = 20


# ---------------------------------------------------------------------------
# LANGUAGE
# ---------------------------------------------------------------------------
def get_lang():
    return st.session_state.get("lang", "EN")


def t(en, ar):
    return ar if get_lang() == "AR" else en


def get_system_name(key):
    cfg = get_system_config(key) or {}
    return (
        cfg.get("name_ar", cfg.get("name", key))
        if get_lang() == "AR"
        else cfg.get("name", key)
    )


# ---------------------------------------------------------------------------
# FIELD HELPERS
# ---------------------------------------------------------------------------
def should_skip_field(field_name, field_info):
    fn = field_name.lower()
    if field_name in ALWAYS_SKIP_FIELDS:
        return True
    for prefix in ALWAYS_SKIP_PREFIXES:
        if fn.startswith(prefix):
            return True
    for sub in ALWAYS_SKIP_SUBSTRINGS:
        if sub in fn:
            return True
    if field_info.get("type", "") not in USEFUL_FIELD_TYPES:
        return True
    return False


def looks_like_season_value(val_str):
    if not val_str:
        return False
    val = str(val_str).strip()
    if not val:
        return False
    for word in ARABIC_SEASON_WORDS:
        if word in val:
            return True
    if SEASON_VALUE_RE.search(val):
        return True
    return False


def score_field_name(field_name, field_label):
    score = 0
    fn = field_name.lower()
    lbl = (field_label or "").lower()
    for hint in SEASON_NAME_HINTS:
        if hint in fn:
            score += 25
        if hint in lbl:
            score += 20
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


# ---------------------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_email = ""
    st.session_state.lang = "EN"
    st.session_state.season_debug = {}
    st.session_state.deep_audit = {}

# ---------------------------------------------------------------------------
# SESSION LOGIN RESTORE
# ---------------------------------------------------------------------------
import hashlib

_COOKIE_SECRET = "swag_2025_secure"


def _make_token(email):
    return hashlib.sha256(
        f"{_COOKIE_SECRET}_{email}".encode()
    ).hexdigest()[:32]


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


# ---------------------------------------------------------------------------
# XML-RPC HELPERS
# ---------------------------------------------------------------------------
_KEY_ALIASES = {
    "FASHION_LIMITS": "FASHIONLIMITS",
    "FASHIONLIMITS": "FASHIONLIMITS",
}


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
        url = url[: -len("/odoo")]
    cfg["url"] = url
    return cfg


@st.cache_resource
def _proxy(url, ep):
    return xmlrpc.client.ServerProxy(
        f"{url}/xmlrpc/2/{ep}", allow_none=True
    )


def _auth(url, db, user, api_key):
    try:
        uid = _proxy(url, "common").authenticate(db, user, api_key, {})
        if uid:
            return {"ok": True, "uid": uid}
        return {"ok": False, "error": "BAD_CREDENTIALS"}
    except Exception as e:
        return {"ok": False, "error": f"AUTH_EXCEPTION: {e}"}


def _execute(url, db, uid, api_key, model, method, domain, kw):
    if not isinstance(domain, list):
        raise ValueError(f"Domain must be a list, got {type(domain)}")
    return _proxy(url, "object").execute_kw(
        db, uid, api_key, model, method, domain, kw
    )


def safe_domain(conditions):
    if not conditions:
        return []
    result = []
    for cond in conditions:
        if isinstance(cond, (list, tuple)) and len(cond) == 3:
            result.append(list(cond))
        else:
            raise ValueError(f"Invalid domain condition: {cond}")
    return result


# ---------------------------------------------------------------------------
# RELATION MODEL PROBE
# ---------------------------------------------------------------------------
def _probe_relation_model(url, db, uid, api_key, relation_model, related_ids):
    result = {
        "sample_names": [],
        "season_like_count": 0,
        "total_fetched": 0,
        "error": None,
    }
    if not related_ids or not relation_model:
        return result

    unique_ids = list(
        {i for i in related_ids if isinstance(i, int)}
    )[:RELATION_SAMPLE_LIMIT]
    if not unique_ids:
        return result

    try:
        recs = _execute(
            url, db, uid, api_key,
            relation_model, "search_read",
            safe_domain([["id", "in", unique_ids]]),
            {
                "fields": ["id", "name", "display_name"],
                "limit": RELATION_SAMPLE_LIMIT,
            },
        )
        result["total_fetched"] = len(recs)
        for rec in recs:
            name = (
                rec.get("display_name")
                or rec.get("name")
                or ""
            )
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


# ---------------------------------------------------------------------------
# DEEP SEASON AUDIT (one system)
# ---------------------------------------------------------------------------
def deep_season_audit_for_system(system_key):
    audit = {
        "system": system_key,
        "status": "pending",
        "error": None,
        "candidates": [],
        "best_field": None,
        "confident": False,
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

    for model in ["product.template", "product.product"]:

        # 1. Get all fields
        try:
            fields_meta = _execute(
                url, db, uid, api_key,
                model, "fields_get", [],
                {"attributes": ["string", "type", "relation", "store"]},
            )
        except Exception:
            continue

        # 2. Sample product IDs
        try:
            sample_recs = _execute(
                url, db, uid, api_key,
                model, "search_read", [],
                {"fields": ["id"], "limit": AUDIT_SAMPLE_LIMIT},
            )
            sample_ids = [r["id"] for r in sample_recs]
        except Exception:
            sample_ids = []

        if not sample_ids:
            continue

        # 3. Pre-filter fields
        eligible_fields = {
            fname: finfo
            for fname, finfo in fields_meta.items()
            if not should_skip_field(fname, finfo)
        }
        if not eligible_fields:
            continue

        # 4. Batch-read eligible fields on the sample
        try:
            product_records = _execute(
                url, db, uid, api_key,
                model, "search_read",
                safe_domain([["id", "in", sample_ids]]),
                {
                    "fields": list(eligible_fields.keys()),
                    "limit": AUDIT_SAMPLE_LIMIT,
                },
            )
        except Exception:
            continue

        # 5. Evaluate each field
        for fname, finfo in eligible_fields.items():
            ftype = finfo.get("type", "")
            relation = finfo.get("relation") or ""
            flabel = finfo.get("string", fname)

            candidate = {
                "field_name": fname,
                "field_label": flabel,
                "model": model,
                "field_type": ftype,
                "relation_model": relation,
                "name_score": 0,
                "relation_model_score": 0,
                "data_score": 0,
                "total_score": 0,
                "non_empty_count": 0,
                "sample_raw_values": [],
                "season_like_direct_count": 0,
                "relation_probe": None,
                "rejection_reason": None,
            }

            candidate["name_score"] = score_field_name(fname, flabel)
            candidate["relation_model_score"] = score_relation_model(relation)

            if relation and relation in BLACKLIST_RELATION_MODELS:
                candidate["rejection_reason"] = (
                    f"Relation model '{relation}' is blacklisted"
                )
                candidate["total_score"] = (
                    candidate["name_score"]
                    + candidate["relation_model_score"]
                )
                candidates.append(candidate)
                continue

            # Collect raw values
            related_ids_seen = []
            for rec in product_records:
                val = rec.get(fname)
                if val is False or val is None:
                    continue

                if ftype == "many2one":
                    if isinstance(val, list) and len(val) >= 2:
                        rel_id = val[0]
                        display = str(val[1])
                        related_ids_seen.append(rel_id)
                    elif isinstance(val, int) and val:
                        rel_id = val
                        display = str(val)
                        related_ids_seen.append(rel_id)
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
                candidate["rejection_reason"] = (
                    "No non-empty values in sample"
                )
                candidate["total_score"] = candidate["name_score"]
                candidates.append(candidate)
                continue

            # Probe relation model if many2one
            if ftype == "many2one" and relation and related_ids_seen:
                probe = _probe_relation_model(
                    url, db, uid, api_key,
                    relation, related_ids_seen,
                )
                candidate["relation_probe"] = probe
                candidate["season_like_direct_count"] += probe.get(
                    "season_like_count", 0
                )
                for rname in probe.get("sample_names", []):
                    if len(candidate["sample_raw_values"]) < 10:
                        candidate["sample_raw_values"].append(
                            f"[rel] {rname}"
                        )

            # Data score
            total_checked = candidate["non_empty_count"]
            if total_checked > 0:
                ratio = (
                    candidate["season_like_direct_count"] / total_checked
                )
                candidate["data_score"] = ratio * 40

            candidate["total_score"] = (
                candidate["name_score"]
                + candidate["relation_model_score"]
                + candidate["data_score"]
            )

            if candidate["total_score"] <= 0:
                candidate["rejection_reason"] = (
                    "Score <= 0: no name hints and no season-like data"
                )

            candidates.append(candidate)

    # Sort by score descending
    candidates.sort(key=lambda c: c["total_score"], reverse=True)
    audit["candidates"] = candidates

    if candidates and candidates[0]["total_score"] > 0:
        best = candidates[0]
        audit["best_field"] = best
        probe = best.get("relation_probe") or {}
        if (
            best["total_score"] >= 15
            or best["season_like_direct_count"] > 0
            or probe.get("season_like_count", 0) > 0
        ):
            audit["confident"] = True
        audit["status"] = "ok"
    else:
        audit["status"] = "no_candidates"
        audit["error"] = (
            "No candidate fields found with score > 0. "
            "All eligible fields either had no data or scored zero."
        )

    return audit


# ---------------------------------------------------------------------------
# FETCH DISTINCT SEASONS FROM AUDIT
# ---------------------------------------------------------------------------
def fetch_distinct_seasons_from_audit(system_key, audit):
    if not audit.get("confident") or not audit.get("best_field"):
        return []

    best = audit["best_field"]
    model = best["model"]
    field = best["field_name"]
    ftype = best["field_type"]
    relation = best["relation_model"]

    cfg = get_system_config(system_key)
    if not cfg:
        return []
    auth_res = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth_res["ok"]:
        return []
    uid = auth_res["uid"]
    url, db, api_key = cfg["url"], cfg["db"], cfg["api_key"]

    try:
        records = _execute(
            url, db, uid, api_key,
            model, "search_read",
            safe_domain([[field, "!=", False]]),
            {"fields": [field], "limit": 50000},
        )
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
                    unique_vals[val[0]] = val[1]
                    related_ids.append(val[0])
                elif isinstance(val, int) and val:
                    unique_vals[val] = str(val)
                    related_ids.append(val)
            else:
                unique_vals[val] = str(val)

        # Refresh names from relation model
        if ftype == "many2one" and relation and related_ids:
            unique_ids = list(set(related_ids))
            try:
                rel_recs = _execute(
                    url, db, uid, api_key,
                    relation, "search_read",
                    safe_domain([["id", "in", unique_ids]]),
                    {
                        "fields": ["id", "name", "display_name"],
                        "limit": len(unique_ids) + 10,
                    },
                )
                for r in rel_recs:
                    name = (
                        r.get("display_name")
                        or r.get("name")
                        or str(r["id"])
                    )
                    if isinstance(name, list):
                        name = name[1] if len(name) > 1 else str(name)
                    unique_vals[r["id"]] = str(name).strip()
            except Exception:
                pass

        seasons = [(v, unique_vals[v]) for v in unique_vals]
        seasons.sort(key=lambda x: str(x[1]))
        return seasons

    except Exception:
        return []


# ---------------------------------------------------------------------------
# MAIN DISCOVERY ENTRY POINT
# ---------------------------------------------------------------------------
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
                label_to_value = {label: value for value, label in seasons}
                value_to_label = {value: label for value, label in seasons}
                all_systems_info[sys] = {
                    "model": best["model"],
                    "field": best["field_name"],
                    "ftype": best["field_type"],
                    "relation": best["relation_model"],
                    "seasons": seasons,
                    "label_to_value": label_to_value,
                    "value_to_label": value_to_label,
                }

    return all_systems_info, audits


# ---------------------------------------------------------------------------
# SEASON RESOLUTION
# ---------------------------------------------------------------------------
def resolve_season_for_system(season_label, sys_info):
    label_to_value = sys_info["label_to_value"]
    if season_label in label_to_value:
        return label_to_value[season_label], season_label, None
    norm = season_label.strip().lower()
    for label, value in label_to_value.items():
        if label.strip().lower() == norm:
            return value, label, None
    for label, value in label_to_value.items():
        if norm in label.lower() or label.lower() in norm:
            return value, label, None
    return None, None, f"Season '{season_label}' not found in system"


# ---------------------------------------------------------------------------
# FETCH PRODUCTS FOR A SYSTEM AND SEASON
# ---------------------------------------------------------------------------
def fetch_season_products(system_key, sys_info, season_label):
    cfg = get_system_config(system_key)
    if not cfg:
        return pd.DataFrame(), {"error": "No config"}

    auth_res = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth_res["ok"]:
        return pd.DataFrame(), {
            "error": f"Auth failed: {auth_res.get('error')}"
        }

    uid = auth_res["uid"]
    url, db, api_key = cfg["url"], cfg["db"], cfg["api_key"]
    model = sys_info["model"]
    field = sys_info["field"]
    ftype = sys_info["ftype"]

    stored_value, matched_label, resolve_err = resolve_season_for_system(
        season_label, sys_info
    )

    debug = {
        "system": system_key,
        "model": model,
        "field": field,
        "ftype": ftype,
        "requested_label": season_label,
        "matched_label": matched_label,
        "stored_value": stored_value,
        "resolve_error": resolve_err,
        "templates_found": 0,
        "products_found": 0,
        "domain_used": None,
        "error": None,
    }

    if resolve_err:
        debug["error"] = resolve_err
        return pd.DataFrame(), debug

    try:
        if model == "product.template":
            template_domain = safe_domain([[field, "=", stored_value]])
            debug["domain_used"] = template_domain
            templates = _execute(
                url, db, uid, api_key,
                "product.template", "search_read",
                template_domain,
                {"fields": ["id"], "limit": 50000},
            )
            if not templates:
                debug["templates_found"] = 0
                return pd.DataFrame(), debug

            tmpl_ids = [t["id"] for t in templates]
            debug["templates_found"] = len(tmpl_ids)

            products = _execute(
                url, db, uid, api_key,
                "product.product", "search_read",
                safe_domain(
                    [["product_tmpl_id", "in", tmpl_ids],
                     ["sale_ok", "=", True]]
                ),
                {
                    "fields": [
                        "default_code", "display_name",
                        "qty_available", "list_price",
                    ],
                    "limit": 200000,
                },
            )
        else:
            product_domain = safe_domain(
                [[field, "=", stored_value], ["sale_ok", "=", True]]
            )
            debug["domain_used"] = product_domain
            products = _execute(
                url, db, uid, api_key,
                "product.product", "search_read",
                product_domain,
                {
                    "fields": [
                        "default_code", "display_name",
                        "qty_available", "list_price",
                    ],
                    "limit": 200000,
                },
            )

        if not products:
            debug["products_found"] = 0
            return pd.DataFrame(), debug

        debug["products_found"] = len(products)
        rows = []
        for p in products:
            code = (p.get("default_code") or "").strip()
            if not code:
                continue
            rows.append({
                "Model Code": code,
                "Product": p.get("display_name") or "",
                "Qty": float(p.get("qty_available") or 0),
                "Price": float(p.get("list_price") or 0),
                "Season": season_label,
            })

        return pd.DataFrame(rows), debug

    except Exception as e:
        debug["error"] = str(e)
        return pd.DataFrame(), debug


# ---------------------------------------------------------------------------
# BUILD COMPARISON MATRIX
# ---------------------------------------------------------------------------
def build_season_comparison_matrix(selected_season_label, all_systems_info):
    all_data = {}
    debug_info = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(
                fetch_season_products, sys, info, selected_season_label
            ): sys
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

    merged = None
    for sys, df in all_data.items():
        sub = df[["Model Code", "Product", "Qty", "Price"]].copy()
        sub = sub.rename(
            columns={"Qty": f"{sys} Qty", "Price": f"{sys} Price"}
        )
        if merged is None:
            merged = sub
        else:
            merged = pd.merge(merged, sub, on="Model Code", how="outer")

    if merged is None:
        return pd.DataFrame(), debug_info

    qty_cols = [c for c in merged.columns if c.endswith(" Qty")]
    merged["Total Qty"] = merged[qty_cols].sum(axis=1)

    # Consolidate Product column after outer joins
    pcols = [c for c in merged.columns if c == "Product"
             or c.startswith("Product_")]
    if len(pcols) > 1:
        merged["Product"] = merged[pcols].bfill(axis=1).iloc[:, 0]
        for pc in pcols:
            if pc != "Product":
                merged.drop(columns=[pc], inplace=True, errors="ignore")

    merged["Season"] = selected_season_label

    base_cols = ["Model Code", "Product", "Season"]
    sys_cols = []
    for sys in SYSTEM_KEYS:
        if f"{sys} Qty" in merged.columns:
            sys_cols.append(f"{sys} Qty")
        if f"{sys} Price" in merged.columns:
            sys_cols.append(f"{sys} Price")
    final_cols = base_cols + sys_cols + ["Total Qty"]
    final_cols = [c for c in final_cols if c in merged.columns]

    merged = merged[final_cols].fillna(0).reset_index(drop=True)
    for col in merged.columns:
        if "Price" in col:
            merged[col] = merged[col].round(2)
        elif "Qty" in col:
            merged[col] = merged[col].astype(int)

    return merged, debug_info


# ---------------------------------------------------------------------------
# EXCEL EXPORT
# ---------------------------------------------------------------------------
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
        alt_fill = PatternFill("solid", fgColor="0D1A1C")
        norm_font = Font(name="Calibri", size=10, color="8AACB0")
        num_align = Alignment(horizontal="right", vertical="center")
        tot_fill = PatternFill("solid", fgColor="060D0E")
        tot_font = Font(bold=True, name="Calibri", color="D4A84B")

        max_row = ws.max_row
        max_col = ws.max_column
        ws.row_dimensions[1].height = 28

        for col_num in range(1, max_col + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.fill = hdr_fill
            cell.font = hdr_font
            cell.alignment = h_align
            cell.border = border

        for row in ws.iter_rows(min_row=2, max_row=max_row):
            for cell in row:
                cell.border = border
                cell.font = norm_font
                if cell.row % 2 == 0:
                    cell.fill = alt_fill
                cell.alignment = (
                    num_align
                    if isinstance(cell.value, (int, float))
                    else h_align
                )
            ws.row_dimensions[row[0].row].height = 18

        for col_num in range(1, max_col + 1):
            col_letter = get_column_letter(col_num)
            max_len = max(
                (
                    len(str(ws.cell(row=r, column=col_num).value or ""))
                    for r in range(1, max_row + 1)
                ),
                default=8,
            )
            ws.column_dimensions[col_letter].width = min(
                max(max_len + 3, 12), 45
            )

        ws.freeze_panes = "A2"
        ws.auto_filter.ref = (
            f"A1:{get_column_letter(max_col)}{max_row}"
        )

        total_row = max_row + 1
        tc = ws.cell(row=total_row, column=1, value="TOTAL")
        tc.font = tot_font
        tc.fill = tot_fill
        tc.alignment = h_align

        for col_idx, col_name in enumerate(df.columns, start=1):
            if "Qty" in col_name or "Price" in col_name:
                col_letter = get_column_letter(col_idx)
                c = ws.cell(
                    row=total_row,
                    column=col_idx,
                    value=f"=SUM({col_letter}2:{col_letter}{max_row})",
                )
                c.font = tot_font
                c.fill = tot_fill
                c.alignment = num_align

        ws.sheet_properties.tabColor = "4AACB4"
        footer_row = total_row + 2
        fc = ws.cell(
            row=footer_row,
            column=1,
            value=(
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                f"  |  Season: {season_name}"
            ),
        )
        fc.font = Font(
            italic=True, color="4AACB4", size=9, name="Calibri"
        )

    return buf.getvalue()


# ---------------------------------------------------------------------------
# AUDIT REPORT RENDERER
# ---------------------------------------------------------------------------
def render_deep_audit_report(audits):
    st.markdown(
        "<div class='section-tag'>Deep Season Field Audit Report</div>",
        unsafe_allow_html=True,
    )

    for sys in SYSTEM_KEYS:
        audit = audits.get(sys)
        if not audit:
            st.markdown(f"**{get_system_name(sys)}** - not audited")
            continue

        label = (
            "Field Found"
            if audit.get("confident")
            else "No Field Identified"
        )
        icon = "OK" if audit.get("confident") else "FAIL"

        with st.expander(
            f"{get_system_name(sys)}  [{icon}]  {label}",
            expanded=not audit.get("confident"),
        ):
            st.markdown(f"**Status:** `{audit['status']}`")

            if audit.get("error"):
                st.error(audit["error"])

            if audit.get("best_field"):
                best = audit["best_field"]
                st.success(
                    f"Best candidate: "
                    f"`{best['model']}.{best['field_name']}` "
                    f"| type: `{best['field_type']}` "
                    f"| label: {best['field_label']} "
                    f"| score: {best['total_score']:.1f}"
                )
                if best.get("relation_model"):
                    st.markdown(
                        f"**Relation model:** `{best['relation_model']}`"
                    )
                probe = best.get("relation_probe") or {}
                if probe.get("sample_names"):
                    names_str = "  |  ".join(
                        probe["sample_names"][:10]
                    )
                    st.markdown(
                        f"**Sample related-record names:** {names_str}"
                    )
            else:
                st.warning(
                    "No field could be confidently identified. "
                    "Review the top candidates below to find it manually."
                )

            candidates = audit.get("candidates", [])
            top_n = candidates[:20]

            if top_n:
                st.markdown(
                    f"**Top {len(top_n)} candidate fields "
                    f"(of {len(candidates)} evaluated)**"
                )
                rows = []
                for c in top_n:
                    probe = c.get("relation_probe") or {}
                    rel_names = "; ".join(
                        probe.get("sample_names", [])[:3]
                    )
                    rows.append(
                        {
                            "Field": c["field_name"],
                            "Label": c["field_label"],
                            "Model": c["model"],
                            "Type": c["field_type"],
                            "Relation": c["relation_model"] or "",
                            "Non-Empty": c["non_empty_count"],
                            "Season-Like": c["season_like_direct_count"],
                            "Score": round(c["total_score"], 1),
                            "Sample Values": "; ".join(
                                str(v)
                                for v in c["sample_raw_values"][:3]
                            ),
                            "Related Names": rel_names or "",
                            "Rejection": (
                                c["rejection_reason"] or "Accepted"
                            ),
                        }
                    )
                audit_df = pd.DataFrame(rows)
                st.dataframe(
                    audit_df,
                    use_container_width=True,
                    height=min(400, 40 + 35 * len(rows)),
                )
            else:
                st.write(
                    "No eligible fields found after filtering."
                )


# ---------------------------------------------------------------------------
# LOGIN
# ---------------------------------------------------------------------------
def show_login():
    lg = st.radio(
        "", ["EN", "AR"],
        horizontal=True,
        index=0 if get_lang() == "EN" else 1,
        label_visibility="collapsed",
        key="llr",
    )
    if lg != get_lang():
        st.session_state.lang = lg
        st.rerun()

    st.markdown("""
    <div style='display:flex; flex-direction:column; align-items:center;
                justify-content:center; min-height:80vh;'>
      <div style='font-family:"Cormorant Garamond",serif; font-size:52px;
                  color:#fff; letter-spacing:8px; margin-bottom:8px;'>
        SWAG
      </div>
      <div style='font-family:Outfit,sans-serif; font-size:9px;
                  letter-spacing:5px; text-transform:uppercase;
                  color:#4AACB4; margin-bottom:32px;'>
        Season Comparison
      </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        email = st.text_input(
            t("Email", "البريد الإلكتروني"),
            placeholder="you@company.com",
        )
        password = st.text_input(
            t("Password", "كلمة المرور"), type="password"
        )
        submit = st.form_submit_button(
            t("Sign In", "تسجيل الدخول"),
            type="primary",
            use_container_width=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    if submit:
        if not email or not password:
            st.error(t("Fill both fields.", "يرجى ملء جميع الحقول."))
            return
        if "LOGIN" not in st.secrets:
            st.error("Missing LOGIN section in secrets.toml")
            return
        cfg = st.secrets["LOGIN"]
        try:
            login_url = str(cfg.get("url", "")).rstrip("/")
            if login_url.endswith("/odoo"):
                login_url = login_url[: -len("/odoo")]
            proxy = xmlrpc.client.ServerProxy(
                f"{login_url}/xmlrpc/2/common", allow_none=True
            )
            uid = proxy.authenticate(cfg["db"], email, password, {})
            if uid:
                token = _make_token(email)
                st.query_params["u"] = email
                st.query_params["t"] = token
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.rerun()
            else:
                st.error(
                    t(
                        "Wrong email or password.",
                        "بريد الكتروني او كلمة مرور خاطئة.",
                    )
                )
        except Exception as e:
            st.error(f"Connection error: {e}")


def do_logout():
    try:
        st.query_params.clear()
    except Exception:
        pass
    st.session_state.authenticated = False
    st.session_state.user_email = ""
    st.rerun()


# ---------------------------------------------------------------------------
# MAIN DASHBOARD
# ---------------------------------------------------------------------------
def show_dashboard():
    with st.sidebar:
        st.markdown("""
        <div style='padding:24px 0 20px;
                    border-bottom:1px solid rgba(74,172,180,0.08);
                    margin-bottom:20px;'>
          <div style='display:flex; align-items:center; gap:10px;'>
            <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
              <path d="M16 2 L28 16 L16 30 L4 16 Z"
                    stroke="#4AACB4" stroke-width="1"
                    fill="rgba(74,172,180,0.04)"/>
              <path d="M16 9 L23 16 L16 23 L9 16 Z"
                    fill="#4AACB4" opacity="0.3"/>
            </svg>
            <div>
              <div style='font-family:Outfit; font-size:13px;
                          font-weight:600; color:#fff;
                          letter-spacing:2px;'>SWAG</div>
              <div style='font-family:Outfit; font-size:7px;
                          letter-spacing:3px; color:#4AACB4;'>
                Season
              </div>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

        lc = st.radio(
            t("Language", "اللغة"), ["EN", "AR"],
            horizontal=True,
            index=0 if get_lang() == "EN" else 1,
        )
        if lc != get_lang():
            st.session_state.lang = lc
            st.rerun()

        st.markdown(
            f"<div style='margin:16px 0 8px; font-size:7px; "
            f"letter-spacing:3px;'>"
            f"{st.session_state.user_email}</div>",
            unsafe_allow_html=True,
        )
        if st.button(
            t("Logout", "خروج"),
            use_container_width=True,
            type="secondary",
        ):
            do_logout()

    st.markdown("""
    <div style='padding:1rem 2rem 0 2rem;'>
      <div class='hero-title'>موسم <em>المقارنة</em></div>
      <div class='hero-title' style='font-size:28px; margin-top:-8px;'>
        Season Comparison
      </div>
    </div>
    """, unsafe_allow_html=True)

    # System status badges
    st.markdown(
        "<div class='section-tag'>Connected Systems</div>",
        unsafe_allow_html=True,
    )
    badges = []
    for sys in SYSTEM_KEYS:
        cfg = get_system_config(sys)
        if cfg:
            ok = _auth(
                cfg["url"], cfg["db"], cfg["user"], cfg["api_key"]
            )["ok"]
            status = "Online" if ok else "Offline"
        else:
            status = "No config"
        badges.append(
            f"<span style='background:rgba(74,172,180,0.1);"
            f"padding:4px 12px; border-radius:100px;"
            f"font-size:10px; letter-spacing:1px;'>"
            f"{get_system_name(sys)}: {status}"
            f"</span>"
        )
    st.markdown(
        f"<div style='display:flex; gap:8px; flex-wrap:wrap;"
        f"margin-bottom:20px;'>"
        f"{''.join(badges)}</div>",
        unsafe_allow_html=True,
    )

    # Audit trigger
    st.markdown(
        "<div class='section-tag'>Season Discovery</div>",
        unsafe_allow_html=True,
    )

    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        run_audit = st.button(
            "Run Deep Season Audit",
            type="primary",
            use_container_width=True,
        )
    with col_info:
        st.markdown(
            "<div class='info-banner'>"
            "Inspects all product fields including custom x_studio fields, "
            "many2one relations and their related-model record names. "
            "Shows top 20 candidates per system."
            "</div>",
            unsafe_allow_html=True,
        )

    if run_audit or st.session_state.get("audit_done"):
        if run_audit or not st.session_state.get("all_systems_info"):
            with st.spinner(
                "Running deep season field audit... "
                "This may take 30-90 seconds."
            ):
                all_systems_info, audits = run_full_discovery()
                st.session_state["all_systems_info"] = all_systems_info
                st.session_state["audits"] = audits
                st.session_state["audit_done"] = True
                for k in ["season_matrix", "season_name", "fetch_debug"]:
                    st.session_state.pop(k, None)

        all_systems_info = st.session_state["all_systems_info"]
        audits = st.session_state["audits"]

        # Always show audit report
        render_deep_audit_report(audits)

        if not all_systems_info:
            st.error(
                t(
                    "No season field could be confidently identified "
                    "in any system. Review the audit report above. "
                    "You may need to manually specify the field.",
                    "لم يتم التعرف على حقل الموسم في اي نظام. "
                    "راجع تقرير التدقيق اعلاه.",
                )
            )
            return

        # Season selector
        st.markdown(
            "<div class='section-tag'>Compare Season</div>",
            unsafe_allow_html=True,
        )

        global_seasons = set()
        for sys, info in all_systems_info.items():
            for _value, label in info["seasons"]:
                global_seasons.add(label)

        season_labels = sorted(global_seasons)

        if not season_labels:
            st.warning(
                "Season fields were identified but no season values "
                "could be retrieved. Check the audit report."
            )
            return

        selected_label = st.selectbox(
            t("Select Season", "اختر الموسم"),
            season_labels,
            key="season_select",
        )

        # Coverage per system
        cov_badges = []
        for sys, info in all_systems_info.items():
            labels_in_sys = {lbl for _, lbl in info["seasons"]}
            has = selected_label in labels_in_sys
            mark = "YES" if has else "MAPPED"
            cov_badges.append(
                f"<span style='background:rgba(74,172,180,0.1);"
                f"padding:4px 10px; border-radius:100px;"
                f"font-size:10px;'>"
                f"{get_system_name(sys)}: {mark}"
                f"</span>"
            )
        st.markdown(
            f"<div style='display:flex; gap:6px; flex-wrap:wrap;"
            f"margin-bottom:16px;'>"
            f"{''.join(cov_badges)}</div>",
            unsafe_allow_html=True,
        )

        if st.button(
            t("Compare Season", "مقارنة الموسم"),
            type="primary",
        ):
            with st.spinner(
                t(
                    "Fetching products from all systems...",
                    "جلب المنتجات من جميع الانظمة...",
                )
            ):
                df_matrix, fetch_debug = build_season_comparison_matrix(
                    selected_label, all_systems_info
                )
            if df_matrix.empty:
                st.error(
                    t(
                        "No products found for this season.",
                        "لا توجد منتجات لهذا الموسم.",
                    )
                )
                with st.expander("Product Fetch Debug", expanded=True):
                    for sys, dbg in fetch_debug.items():
                        st.markdown(f"**{get_system_name(sys)}**")
                        for k, v in dbg.items():
                            st.write(f"  {k}: {v}")
                        st.write("---")
            else:
                st.session_state["season_matrix"] = df_matrix
                st.session_state["season_name"] = selected_label
                st.session_state["fetch_debug"] = fetch_debug
                st.rerun()

    # Results
    if "season_matrix" in st.session_state:
        df = st.session_state["season_matrix"]
        season_name = st.session_state["season_name"]

        total_models = df["Model Code"].nunique()
        total_qty = int(df["Total Qty"].sum())
        sys_qty_stats = {}
        for sys in SYSTEM_KEYS:
            col = f"{sys} Qty"
            if col in df.columns:
                v = int(df[col].sum())
                if v > 0:
                    sys_qty_stats[get_system_name(sys)] = v

        c1, c2, c3 = st.columns(3)
        c1.metric(
            t("Total Models", "اجمالي الموديلات"),
            f"{total_models:,}",
        )
        c2.metric(
            t("Total Units", "اجمالي الوحدات"),
            f"{total_qty:,}",
        )
        c3.metric(
            t("Systems with stock", "انظمة بها مخزون"),
            (
                ", ".join(f"{k}: {v:,}" for k, v in sys_qty_stats.items())
                or "None"
            ),
        )

        st.markdown("---")
        st.markdown(
            "<div class='section-tag'>Comparison Matrix</div>",
            unsafe_allow_html=True,
        )

        if len(df) > 200:
            st.info(
                f"Showing first 10 of {len(df)} rows. "
                "Download Excel for full data."
            )
            st.dataframe(df.head(10), use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)

        excel_bytes = to_excel_season_matrix(df, season_name)
        st.download_button(
            label=t("Download Excel", "تحميل Excel"),
            data=excel_bytes,
            file_name=(
                f"season_comparison_{season_name}_"
                f"{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-officedocument"
                ".spreadsheetml.sheet"
            ),
            key="season_download",
        )

        with st.expander("Product Fetch Debug"):
            for sys, dbg in st.session_state.get(
                "fetch_debug", {}
            ).items():
                st.markdown(f"**{get_system_name(sys)}**")
                if dbg.get("error"):
                    st.error(dbg["error"])
                for k, v in dbg.items():
                    st.write(f"  {k}: {v}")
                st.write("---")

        if st.button(
            t("Clear Results", "مسح النتائج"), type="secondary"
        ):
            for k in ["season_matrix", "season_name", "fetch_debug"]:
                st.session_state.pop(k, None)
            st.rerun()


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------
restore_session()
if not st.session_state.authenticated:
    show_login()
else:
    show_dashboard()
```
