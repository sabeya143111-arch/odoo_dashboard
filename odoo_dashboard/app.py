"""
SWAG Season Comparison Dashboard v10
New in v10:
1. stock.quant-based qty (real per-location, not qty_available)
   → no more 0s due to login warehouse context
2. Company matrix  — one Qty + Price column per system (all rows, even zero stock)
3. Branch matrix   — one column per (System · Location), rows = Match Key
4. All seasons / models covered: meta fetch ensures every product appears even with 0 qty
5. New features:
   - Stock Value by Branch table (qty × price per location)
   - Zero-stock report (products present in season but no stock anywhere)
   - Price alerts unchanged but now uses company matrix
   - Missing-product analysis unchanged
   - Multi-sheet Excel: Company | Branch | Branch Value | Zero Stock
6. Parallel fetch with ThreadPoolExecutor (unchanged from v9)
7. All v9 UX kept: season type / exact mode, login, diagnostics, reload seasons
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

# ══════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════
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
    r"\b(صيفي|شتوي|ربيعي|خريفي)\s*\d{1,2}\b",
    r"\b\d{2,4}\s*(صيفي|شتوي|ربيعي|خريفي)\b",
]
SEASON_VALUE_RE = re.compile("|".join(SEASON_CODE_PATTERNS), re.IGNORECASE | re.UNICODE)

BLACKLIST_RELATION_MODELS = {
    "res.users","res.partner","res.company","res.currency","res.country","res.lang","res.groups",
    "uom.uom","uom.category","account.tax","account.account","account.journal",
    "mail.activity.type","mail.template","mail.alias","ir.attachment","ir.model","ir.model.fields",
    "ir.actions.act_window","ir.ui.view","ir.ui.menu","ir.rule","ir.sequence",
    "stock.location","stock.warehouse","stock.quant",
}
USEFUL_FIELD_TYPES = {"many2one","selection","char","text","integer","float"}
ALWAYS_SKIP_FIELDS = {
    "__last_update","write_date","create_date","write_uid","create_uid",
    "display_name","image_1920","image_1024","image_512","image_256","image_128",
    "image_small","image_medium","message_ids","message_follower_ids","message_channel_ids",
    "message_main_attachment_id","message_has_error","message_needaction",
    "message_attachment_count","message_needaction_counter","message_has_error_counter",
    "website_message_ids","activity_ids","activity_state","activity_type_id","activity_user_id",
    "activity_summary","activity_date_deadline","activity_exception_decoration",
    "activity_exception_icon","can_image_1024_be_zoomed",
}
ALWAYS_SKIP_PREFIXES = ("mail_","message_","activity_","website_","image_","rating_")
AUDIT_SAMPLE_LIMIT   = 300
RELATION_SAMPLE_LIMIT = 20
TEMPLATE_FETCH_LIMIT = 50000
PRODUCT_FETCH_LIMIT  = 200000
PRICE_DIFF_THRESHOLD_PCT = 10.0

# ══════════════════════════════════════════════════════
# TEXT HELPERS
# ══════════════════════════════════════════════════════
def normalize_text(v):
    return re.sub(r"\s+", " ", str(v or "").strip()).lower()

def season_norm(v):
    s = normalize_text(v)
    return s.replace("-","").replace("_","").replace("/","").replace(" ","")

SEASON_TYPE_HINTS = [
    (("صيفي","صيف","summer","ss","su"), "SUMMER"),
    (("شتوي","شتاء","winter","aw","fw","wi"), "WINTER"),
    (("ربيعي","ربيع","spring","sp"), "SPRING"),
    (("خريفي","خريف","fall","autumn","fa"), "FALL"),
]
SEASON_TYPE_LABEL = {
    "SUMMER":"Summer / صيفي","WINTER":"Winter / شتوي",
    "SPRING":"Spring / ربيعي","FALL":"Fall / خريفي",
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
    if not nums: return ""
    n = nums[-1]
    if len(n) >= 4: return n[:4]
    if len(n) == 2: return "20" + n
    if len(n) == 1: return "200" + n
    return n

def season_signature(label):
    stype = season_type_only(label)
    if not stype: return None
    yr = season_year(label)
    return stype + (yr[-2:] if yr else "")

def should_skip_field(field_name, field_info):
    fn = field_name.lower()
    if field_name in ALWAYS_SKIP_FIELDS: return True
    for prefix in ALWAYS_SKIP_PREFIXES:
        if fn.startswith(prefix): return True
    if field_info.get("type","") not in USEFUL_FIELD_TYPES: return True
    return False

def looks_like_season_value(val_str):
    if not val_str: return False
    val = str(val_str).strip()
    if any(word in val for word in ARABIC_SEASON_WORDS): return True
    return bool(SEASON_VALUE_RE.search(val))

def score_field_name(field_name, field_label):
    score = 0
    fn  = field_name.lower()
    lbl = (field_label or "").lower()
    for hint in SEASON_NAME_HINTS:
        if hint in fn:  score += 30
        if hint in lbl: score += 25
    if fn.startswith("x_studio"): score += 5
    elif fn.startswith("x_"):     score += 3
    return score

def score_relation_model(relation):
    if not relation: return 0
    if relation in BLACKLIST_RELATION_MODELS: return -50
    rel = relation.lower()
    for hint in SEASON_NAME_HINTS:
        if hint in rel: return 30
    return 0

def safe_domain(conditions):
    result = []
    for c in conditions:
        if isinstance(c, (list, tuple)) and len(c) == 3:
            result.append([c[0], c[1], c[2]])
        else:
            result.append(c)
    return result

def _join_distinct(series):
    vals = []
    for x in series:
        x = str(x).strip()
        if x and x not in vals:
            vals.append(x)
    return ", ".join(sorted(vals))

# ══════════════════════════════════════════════════════
# SESSION / AUTH
# ══════════════════════════════════════════════════════
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user_email = ""

_COOKIE_SECRET = "swag_2025_secure"

def _make_token(email):
    return hashlib.sha256(f"{_COOKIE_SECRET}_{email}".encode()).hexdigest()[:32]

def _verify_token(email, token):
    return bool(email and token and token == _make_token(email))

def restore_session():
    if st.session_state.get("authenticated"): return
    try:
        params = st.query_params
        email  = params.get("u","")
        token  = params.get("t","")
        if email and token and _verify_token(email, token):
            st.session_state.authenticated = True
            st.session_state.user_email    = email
    except Exception:
        pass

_KEY_ALIASES = {"FASHION_LIMITS":"FASHIONLIMITS","FASHIONLIMITS":"FASHIONLIMITS"}

def _canonical_key(key):
    return _KEY_ALIASES.get(key, key)

def get_system_config(key):
    canonical = _canonical_key(key)
    cfg = st.secrets.get(canonical) or st.secrets.get(key)
    if not cfg: return None
    cfg = dict(cfg)
    url = str(cfg.get("url","")).rstrip("/")
    if url.endswith("/odoo"): url = url[:-5]
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
        if uid: return {"ok": True, "uid": uid}
        return {"ok": False, "error": "BAD_CREDENTIALS"}
    except Exception as e:
        return {"ok": False, "error": f"AUTH_EXCEPTION: {e}"}

def _execute(url, db, uid, api_key, model, method, domain, kw):
    return _proxy(url, "object").execute_kw(db, uid, api_key, model, method, [domain], kw)

def _read_group(url, db, uid, api_key, model, domain, fields, groupby, kw=None):
    kw = kw or {}
    return _proxy(url, "object").execute_kw(db, uid, api_key, model, "read_group",
                                             [domain, fields, groupby], kw)

# ══════════════════════════════════════════════════════
# INTERNAL LOCATIONS CACHE (per system)
# ══════════════════════════════════════════════════════
@st.cache_data(ttl=3600, show_spinner=False)
def get_internal_locations(system_key):
    cfg = get_system_config(system_key)
    if not cfg: return [], {}
    auth = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth["ok"]: return [], {}
    uid = auth["uid"]; url, db, ak = cfg["url"], cfg["db"], cfg["api_key"]
    try:
        locs = _execute(url, db, uid, ak, "stock.location", "search_read",
                        safe_domain([["usage","=","internal"],["active","=",True]]),
                        {"fields":["id","complete_name","display_name","name"],"limit":10000}) or []
    except Exception:
        return [], {}
    loc_ids, loc_name = [], {}
    for l in locs:
        loc_ids.append(l["id"])
        nm = l.get("complete_name") or l.get("display_name") or l.get("name") or str(l["id"])
        loc_name[l["id"]] = str(nm).strip()
    return loc_ids, loc_name

# ══════════════════════════════════════════════════════
# SEASON FIELD DISCOVERY (unchanged from v9)
# ══════════════════════════════════════════════════════
def browse_fields_for_system(system_key):
    cfg = get_system_config(system_key)
    if not cfg: return None, "No config"
    auth = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth["ok"]: return None, auth["error"]
    uid = auth["uid"]; url, db, api_key = cfg["url"], cfg["db"], cfg["api_key"]
    rows = []
    for model in ["product.template"]:
        try:
            fields_meta = _execute(url, db, uid, api_key, model, "fields_get", [],
                                   {"attributes":["string","type","relation","store"]})
        except Exception:
            continue
        for fname, finfo in fields_meta.items():
            if should_skip_field(fname, finfo): continue
            ftype = finfo.get("type",""); relation = finfo.get("relation","") or ""
            flabel = finfo.get("string", fname)
            name_score = score_field_name(fname, flabel)
            rel_score  = score_relation_model(relation)
            rows.append({"Model":model,"Field":fname,"Label":flabel,"Type":ftype,
                         "Relation":relation,"Name Score":name_score,"Rel Score":rel_score,
                         "Total Score":name_score+rel_score})
    if not rows: return None, "No eligible fields found"
    df = pd.DataFrame(rows).sort_values("Total Score",ascending=False).reset_index(drop=True)
    return df, None

def _probe_relation_model(url, db, uid, api_key, relation_model, related_ids):
    result = {"sample_names":[],"season_like_count":0,"total_fetched":0,"error":None}
    if not related_ids or not relation_model: return result
    unique_ids = list({i for i in related_ids if isinstance(i,int)})[:RELATION_SAMPLE_LIMIT]
    if not unique_ids: return result
    try:
        recs = _execute(url, db, uid, api_key, relation_model, "search_read",
                        safe_domain([["id","in",unique_ids]]),
                        {"fields":["id","name","display_name"],"limit":RELATION_SAMPLE_LIMIT})
        result["total_fetched"] = len(recs)
        for rec in recs:
            name = rec.get("display_name") or rec.get("name") or ""
            if isinstance(name, list): name = name[1] if len(name)>1 else str(name)
            name = str(name).strip()
            if name:
                result["sample_names"].append(name)
                if looks_like_season_value(name): result["season_like_count"] += 1
    except Exception as e:
        result["error"] = str(e)
    return result

def deep_season_audit_for_system(system_key):
    audit = {
        "system":system_key,"status":"pending","error":None,"candidates":[],
        "best_field":None,"confident":False,"manual_pick_needed":False,
        "raw_field_count":0,"eligible_field_count":0,"sample_ids_loaded":0,
        "product_records_loaded":0,"fetch_errors":[],
    }
    cfg = get_system_config(system_key)
    if not cfg: audit["status"]="no_config"; audit["error"]="No configuration found."; return audit
    auth_res = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth_res["ok"]: audit["status"]="auth_failed"; audit["error"]=auth_res.get("error","Auth failed"); return audit
    uid = auth_res["uid"]; url, db, api_key = cfg["url"], cfg["db"], cfg["api_key"]
    candidates = []
    for model in ["product.template"]:
        try:
            fields_meta = _execute(url, db, uid, api_key, model, "fields_get", [],
                                   {"attributes":["string","type","relation","store"]})
        except Exception as e:
            audit["fetch_errors"].append(f"fields_get/{model}: {e}"); continue
        audit["raw_field_count"] += len(fields_meta)
        eligible_fields = {fn:fi for fn,fi in fields_meta.items() if not should_skip_field(fn,fi)}
        audit["eligible_field_count"] += len(eligible_fields)
        if not eligible_fields: continue
        sample_ids = []
        for domain_attempt in [[], [[1,"=",1]]]:
            try:
                sample_recs = _execute(url, db, uid, api_key, model, "search_read", domain_attempt,
                                       {"fields":["id"],"limit":AUDIT_SAMPLE_LIMIT})
                if sample_recs: sample_ids = [r["id"] for r in sample_recs]; break
            except Exception as e:
                audit["fetch_errors"].append(f"search_ids/{model}: {e}")
        audit["sample_ids_loaded"] += len(sample_ids)
        product_records = []
        if sample_ids:
            field_list = list(eligible_fields.keys()); chunk_size = 60; fetched_recs = {}
            for i in range(0, len(field_list), chunk_size):
                chunk_fields = field_list[i:i+chunk_size]
                try:
                    recs = _execute(url, db, uid, api_key, model, "search_read",
                                    safe_domain([["id","in",sample_ids]]),
                                    {"fields":chunk_fields,"limit":AUDIT_SAMPLE_LIMIT})
                    for rec in recs:
                        rid = rec["id"]
                        if rid not in fetched_recs: fetched_recs[rid] = {}
                        fetched_recs[rid].update(rec)
                except Exception as e:
                    audit["fetch_errors"].append(f"search_read/{model}/chunk{i}: {e}")
            product_records = list(fetched_recs.values())
            audit["product_records_loaded"] += len(product_records)
        for fname, finfo in eligible_fields.items():
            ftype=finfo.get("type",""); relation=finfo.get("relation","") or ""; flabel=finfo.get("string",fname)
            name_score=score_field_name(fname,flabel); rel_score=score_relation_model(relation)
            candidate = {
                "field_name":fname,"field_label":flabel,"model":model,"field_type":ftype,
                "relation_model":relation,"name_score":name_score,"relation_model_score":rel_score,
                "data_score":0,"total_score":0,"non_empty_count":0,"sample_raw_values":[],
                "season_like_direct_count":0,"relation_probe":None,"rejection_reason":None,
            }
            if relation and relation in BLACKLIST_RELATION_MODELS:
                candidate["rejection_reason"]=f"Blacklisted relation: {relation}"
                candidate["total_score"]=name_score+rel_score; candidates.append(candidate); continue
            if not product_records:
                candidate["rejection_reason"]="No product records loaded"
                candidate["total_score"]=name_score+rel_score; candidates.append(candidate); continue
            related_ids_seen = []
            for rec in product_records:
                val = rec.get(fname)
                if val is False or val is None: continue
                if ftype == "many2one":
                    if isinstance(val,list) and len(val)>=2: related_ids_seen.append(val[0]); display=str(val[1])
                    elif isinstance(val,int) and val: related_ids_seen.append(val); display=str(val)
                    else: continue
                else:
                    display=str(val).strip()
                    if not display: continue
                candidate["non_empty_count"] += 1
                if len(candidate["sample_raw_values"]) < 10: candidate["sample_raw_values"].append(display)
                if looks_like_season_value(display): candidate["season_like_direct_count"] += 1
            if candidate["non_empty_count"] == 0:
                candidate["rejection_reason"]="No non-empty values"; candidate["total_score"]=name_score+rel_score
                candidates.append(candidate); continue
            if ftype == "many2one" and relation and related_ids_seen:
                probe = _probe_relation_model(url, db, uid, api_key, relation, related_ids_seen)
                candidate["relation_probe"] = probe
                candidate["season_like_direct_count"] += probe.get("season_like_count",0)
                for rname in probe.get("sample_names",[]):
                    if len(candidate["sample_raw_values"]) < 10:
                        candidate["sample_raw_values"].append("[rel] "+rname)
            ratio = candidate["season_like_direct_count"] / max(candidate["non_empty_count"],1)
            candidate["data_score"] = ratio * 50
            candidate["total_score"] = name_score + rel_score + candidate["data_score"]
            if candidate["total_score"] <= 0: candidate["rejection_reason"] = "Score ≤ 0"
            candidates.append(candidate)
    candidates.sort(key=lambda c: c["total_score"], reverse=True)
    audit["candidates"] = candidates
    positive = [c for c in candidates if c["total_score"] > 0]
    if positive:
        best = positive[0]; audit["best_field"] = best
        probe = best.get("relation_probe") or {}
        if (best["name_score"]>=25 or best["season_like_direct_count"]>0 or
                probe.get("season_like_count",0)>0 or best["data_score"]>0):
            audit["confident"] = True
        audit["status"] = "ok"
    elif candidates:
        audit["status"]="no_confident_field"; audit["manual_pick_needed"]=True
        audit["error"]="Fields found but none scored positively."
    else:
        audit["status"]="no_candidates"; audit["error"]="No eligible fields at all."
    return audit

def fetch_distinct_seasons_from_field(system_key, model, field, ftype, relation):
    cfg = get_system_config(system_key)
    if not cfg: return []
    auth = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth["ok"]: return []
    uid = auth["uid"]; url, db, api_key = cfg["url"], cfg["db"], cfg["api_key"]
    try:
        groups = _read_group(url, db, uid, api_key, model,
                             safe_domain([[field,"!=",False]]), [field], [field], {"lazy":False})
        seasons = {}
        for g in groups or []:
            val = g.get(field)
            if val is False or val is None: continue
            if ftype == "many2one":
                if isinstance(val,list) and len(val)>=2: seasons[val[0]] = str(val[1]).strip()
                elif isinstance(val,int) and val: seasons[val] = str(val)
            else:
                seasons[val] = str(val).strip()
        out = [(v,lbl) for v,lbl in seasons.items() if str(lbl).strip()]
        if out: out.sort(key=lambda x: str(x[1])); return out
    except Exception:
        pass
    try:
        records = _execute(url, db, uid, api_key, model, "search_read",
                           safe_domain([[field,"!=",False]]),
                           {"fields":[field],"limit":50000})
        if not records: return []
        unique_vals = {}; related_ids = []
        for rec in records:
            val = rec.get(field)
            if val is False or val is None: continue
            if ftype == "many2one":
                if isinstance(val,list) and len(val)>=2: unique_vals[val[0]]=str(val[1]).strip(); related_ids.append(val[0])
                elif isinstance(val,int) and val: unique_vals[val]=str(val); related_ids.append(val)
            else:
                unique_vals[val] = str(val).strip()
        if ftype == "many2one" and relation and related_ids:
            try:
                rel_recs = _execute(url, db, uid, api_key, relation, "search_read",
                                    safe_domain([["id","in",list(set(related_ids))]]),
                                    {"fields":["id","name","display_name"],"limit":len(set(related_ids))+10})
                for r in rel_recs:
                    name = r.get("display_name") or r.get("name") or str(r["id"])
                    if isinstance(name,list): name = name[1] if len(name)>1 else str(name)
                    unique_vals[r["id"]] = str(name).strip()
            except Exception:
                pass
        seasons = [(v, unique_vals[v]) for v in unique_vals if str(unique_vals[v]).strip()]
        seasons.sort(key=lambda x: str(x[1]))
        return seasons
    except Exception:
        return []

def fetch_distinct_seasons_from_audit(system_key, audit):
    if not audit.get("confident") or not audit.get("best_field"): return []
    best = audit["best_field"]
    return fetch_distinct_seasons_from_field(
        system_key, best["model"], best["field_name"], best["field_type"], best["relation_model"])

@st.cache_data(ttl=3600, show_spinner=False)
def run_full_discovery():
    audits = {}; all_systems_info = {}
    def _work(sys):
        audit = deep_season_audit_for_system(sys); info = None
        if audit.get("confident") and audit.get("best_field"):
            seasons = fetch_distinct_seasons_from_audit(sys, audit)
            if seasons:
                best = audit["best_field"]
                info = {"model":best["model"],"field":best["field_name"],
                        "ftype":best["field_type"],"relation":best["relation_model"],"seasons":seasons}
        return sys, audit, info
    with ThreadPoolExecutor(max_workers=len(SYSTEM_KEYS)) as executor:
        for sys, audit, info in executor.map(_work, SYSTEM_KEYS):
            audits[sys] = audit
            if info: all_systems_info[sys] = info
    return all_systems_info, audits

def resolve_season_values_for_system(query, sys_info, mode="type"):
    seasons = sys_info.get("seasons", [])
    if not seasons: return [], [], "No seasons available"
    out_vals, out_lbls, seen = [], [], set()
    def add(val, lbl):
        key = (val, lbl)
        if key not in seen:
            seen.add(key); out_vals.append(val); out_lbls.append(lbl)
    q_norm  = season_norm(query); q_type = season_type_only(query); q_year = season_year(query)
    if mode == "type":
        if not q_type: return [], [], f"'{query}' is not a recognized season type"
        for val, lbl in seasons:
            if season_type_only(lbl) == q_type: add(val, lbl)
        if out_vals: return out_vals, out_lbls, None
        return [], [], f"No '{q_type}' seasons found"
    for val, lbl in seasons:
        if lbl == query: add(val, lbl)
    if out_vals: return out_vals, out_lbls, None
    for val, lbl in seasons:
        if season_norm(lbl) == q_norm: add(val, lbl)
    if out_vals: return out_vals, out_lbls, None
    if q_type and q_year:
        sig = season_signature(query)
        for val, lbl in seasons:
            if season_signature(lbl) == sig: add(val, lbl)
        if out_vals: return out_vals, out_lbls, None
        return [], [], f"Season not found: {query}"
    if q_type:
        for val, lbl in seasons:
            if season_type_only(lbl) == q_type: add(val, lbl)
        if out_vals: return out_vals, out_lbls, None
    return [], [], f"Season not found: {query}"

# ══════════════════════════════════════════════════════
# CORE FETCH — stock.quant for real per-location qty
# ══════════════════════════════════════════════════════
def _add_meta(pid_meta, p, season_lbl, system_key):
    code    = str(p.get("default_code") or "").strip()
    barcode = str(p.get("barcode") or "").strip()
    name    = str(p.get("display_name") or "").strip()
    if code:          mk = code
    elif barcode:     mk = "bc::" + barcode
    elif name.strip():mk = "name::" + normalize_text(name)
    else:             return
    price = p.get("lst_price")
    if price in (None, False): price = p.get("list_price")
    pid_meta[p["id"]] = {
        "System":system_key, "Match Key":mk, "Model Code":code,
        "Product":name, "Season":season_lbl, "Year":season_year(season_lbl),
        "Price":float(price or 0),
    }

def fetch_season_stock(system_key, sys_info, query, mode="type", include_archived=True):
    """
    Returns (long_df, meta_df, debug).
    meta_df : one row per season product — used for company matrix (zero stock included).
    long_df : one row per (product × branch/location) with real qty from stock.quant.
    """
    empty = pd.DataFrame()
    cfg = get_system_config(system_key)
    if not cfg: return empty, empty, {"system":system_key,"error":"No config"}
    auth = _auth(cfg["url"], cfg["db"], cfg["user"], cfg["api_key"])
    if not auth["ok"]: return empty, empty, {"system":system_key,"error":"Auth failed: "+str(auth.get("error"))}
    uid = auth["uid"]; url, db, ak = cfg["url"], cfg["db"], cfg["api_key"]
    model=sys_info["model"]; field=sys_info["field"]; ftype=sys_info["ftype"]
    ctx = {"active_test":False} if include_archived else {}
    stored_values, matched_labels, resolve_err = resolve_season_values_for_system(query, sys_info, mode)
    val_to_label = {v:l for v,l in zip(stored_values, matched_labels)}
    joined = ", ".join(matched_labels)
    debug = {
        "system":system_key,"model":model,"field":field,"mode":mode,
        "requested":query,"matched_labels":matched_labels,
        "matched_years":sorted({season_year(l) for l in matched_labels if season_year(l)}),
        "resolve_error":resolve_err,"products_found":0,"with_stock":0,
        "branches":0,"limit_hit":False,"error":None,
    }
    if resolve_err or not stored_values:
        debug["error"] = resolve_err or "No matching stored values"
        return empty, empty, debug
    prod_fields = ["default_code","barcode","display_name","lst_price","list_price","product_tmpl_id"]
    pid_meta = {}
    try:
        if model == "product.template":
            tmpl_domain = (safe_domain([[field,"=",stored_values[0]]]) if len(stored_values)==1
                           else safe_domain([[field,"in",stored_values]]))
            tmpl_recs = _execute(url, db, uid, ak, "product.template", "search_read",
                                 tmpl_domain, {"fields":["id",field],"limit":TEMPLATE_FETCH_LIMIT,"context":ctx}) or []
            if len(tmpl_recs) >= TEMPLATE_FETCH_LIMIT: debug["limit_hit"] = True
            tmpl_season = {}
            for tr in tmpl_recs:
                v = tr.get(field)
                if isinstance(v,list) and v: v = v[0]
                tmpl_season[tr["id"]] = val_to_label.get(v, joined)
            tmpl_ids = list(tmpl_season.keys())
            for i in range(0, len(tmpl_ids), 50):
                batch = tmpl_ids[i:i+50]
                recs = _execute(url, db, uid, ak, "product.product", "search_read",
                                safe_domain([["product_tmpl_id","in",batch]]),
                                {"fields":prod_fields,"limit":20000,"context":ctx}) or []
                for p in recs:
                    tm=p.get("product_tmpl_id"); tid=tm[0] if isinstance(tm,list) and tm else tm
                    _add_meta(pid_meta, p, tmpl_season.get(tid, joined), system_key)
        else:
            prod_domain = (safe_domain([[field,"=",stored_values[0]]]) if len(stored_values)==1
                           else safe_domain([[field,"in",stored_values]]))
            recs = _execute(url, db, uid, ak, "product.product", "search_read",
                            prod_domain, {"fields":prod_fields+[field],"limit":PRODUCT_FETCH_LIMIT,"context":ctx}) or []
            if len(recs) >= PRODUCT_FETCH_LIMIT: debug["limit_hit"] = True
            for p in recs:
                v=p.get(field)
                if isinstance(v,list) and v: v=v[0]
                _add_meta(pid_meta, p, val_to_label.get(v, joined), system_key)
    except Exception as e:
        debug["error"] = f"meta fetch: {e}"
        return empty, empty, debug
    debug["products_found"] = len(pid_meta)
    if not pid_meta: return empty, empty, debug
    # Real per-location qty from stock.quant
    loc_ids, loc_name = get_internal_locations(system_key)
    long_rows = []
    pids = list(pid_meta.keys())
    if loc_ids:
        try:
            for i in range(0, len(pids), 400):
                batch = pids[i:i+400]
                quants = _execute(url, db, uid, ak, "stock.quant", "search_read",
                                  safe_domain([["product_id","in",batch],
                                               ["location_id","in",loc_ids]]),
                                  {"fields":["product_id","location_id","quantity"],"limit":200000,"context":ctx}) or []
                for q in quants:
                    pr=q.get("product_id"); pid=pr[0] if isinstance(pr,list) else pr
                    lc=q.get("location_id"); lid=lc[0] if isinstance(lc,list) else lc
                    qty=float(q.get("quantity") or 0)
                    m=pid_meta.get(pid)
                    if not m: continue
                    branch=loc_name.get(lid) or (lc[1] if isinstance(lc,list) and len(lc)>1 else str(lid))
                    long_rows.append({**m,"Branch":branch,"Qty":qty})
        except Exception as e:
            debug["quant_error"] = str(e)
    long_df = pd.DataFrame(long_rows)
    if not long_df.empty:
        long_df = (long_df.groupby(["System","Branch","Match Key","Model Code","Product",
                                    "Season","Year","Price"],as_index=False).agg({"Qty":"sum"}))
        debug["with_stock"] = int((long_df.groupby("Match Key")["Qty"].sum() > 0).sum())
        debug["branches"]   = int(long_df["Branch"].nunique())
    meta_df = pd.DataFrame(list(pid_meta.values()))
    if not meta_df.empty:
        meta_df = (meta_df.groupby(["System","Match Key","Model Code","Product","Season","Year"],
                                   as_index=False).agg({"Price":"max"}))
    return long_df, meta_df, debug

# ══════════════════════════════════════════════════════
# BUILD VIEWS
# ══════════════════════════════════════════════════════
def build_season_views(query, all_systems_info, mode="type", include_archived=True):
    longs, metas, debug_info = [], [], {}
    workers = min(5, max(1, len(all_systems_info)))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch_season_stock, s, info, query, mode, include_archived): s
                for s, info in all_systems_info.items()}
        for f in as_completed(futs):
            s = futs[f]
            try:
                ldf, mdf, dbg = f.result()
                debug_info[s] = dbg
                if mdf is not None and not mdf.empty: metas.append(mdf)
                if ldf is not None and not ldf.empty: longs.append(ldf)
            except Exception as e:
                debug_info[s] = {"error": str(e)}
    meta_all = pd.concat(metas, ignore_index=True) if metas else pd.DataFrame()
    long_all = pd.concat(longs, ignore_index=True) if longs else pd.DataFrame()
    company = build_company_matrix(meta_all, long_all, all_systems_info)
    branch  = build_branch_matrix(long_all)
    return company, branch, long_all, debug_info

def build_company_matrix(meta_all, long_all, all_systems_info):
    if meta_all is None or meta_all.empty: return pd.DataFrame()
    systems_all = [s for s in SYSTEM_KEYS if s in all_systems_info]
    all_keys = pd.Index(sorted(meta_all["Match Key"].unique()), name="Match Key")
    if long_all is not None and not long_all.empty:
        qty = long_all.groupby(["Match Key","System"])["Qty"].sum().reset_index()
        qty_pivot = qty.pivot_table(index="Match Key", columns="System", values="Qty",
                                    aggfunc="sum", fill_value=0).reindex(all_keys, fill_value=0)
    else:
        qty_pivot = pd.DataFrame(index=all_keys)
    price = meta_all.groupby(["Match Key","System"])["Price"].max().reset_index()
    price_pivot = price.pivot_table(index="Match Key", columns="System", values="Price",
                                    aggfunc="max", fill_value=0).reindex(all_keys, fill_value=0)
    for s in systems_all:
        if s not in qty_pivot.columns:   qty_pivot[s]   = 0
        if s not in price_pivot.columns: price_pivot[s] = 0
    qty_pivot   = qty_pivot[systems_all];   price_pivot = price_pivot[systems_all]
    qty_pivot.columns   = [f"{c} Qty"   for c in qty_pivot.columns]
    price_pivot.columns = [f"{c} Price" for c in price_pivot.columns]
    merged = qty_pivot.join(price_pivot, how="outer").reset_index()
    for agg_col, label in [("Model Code","Model Code"),("Product","Product"),
                            ("Season","Season"),("Year","Year")]:
        m = meta_all.groupby("Match Key")[agg_col].agg(
            lambda s: next((x for x in s if str(x).strip()),"")).reset_index()
        merged = merged.merge(m, on="Match Key", how="left")
    qty_cols   = [c for c in merged.columns if c.endswith(" Qty")]
    price_cols = [c for c in merged.columns if c.endswith(" Price")]
    for c in qty_cols:   merged[c] = pd.to_numeric(merged[c],errors="coerce").fillna(0).astype(int)
    for c in price_cols: merged[c] = pd.to_numeric(merged[c],errors="coerce").fillna(0).round(2)
    for c in ["Model Code","Product","Season","Year"]: merged[c] = merged[c].fillna("").astype(str)
    merged["Total Qty"] = merged[qty_cols].sum(axis=1).astype(int)
    ordered = ["Model Code","Product","Year","Season"]
    for s in SYSTEM_KEYS:
        if f"{s} Qty"   in merged.columns: ordered.append(f"{s} Qty")
        if f"{s} Price" in merged.columns: ordered.append(f"{s} Price")
    ordered.append("Total Qty")
    merged = merged[[c for c in ordered if c in merged.columns]]
    return merged.sort_values(["Total Qty","Model Code"],ascending=[False,True]).reset_index(drop=True)

def build_branch_matrix(long_all):
    if long_all is None or long_all.empty: return pd.DataFrame()
    work = long_all.copy()
    work["Loc"] = work["System"].map(get_system_name).astype(str) + " · " + work["Branch"].astype(str)
    piv = work.pivot_table(index="Match Key", columns="Loc", values="Qty",
                           aggfunc="sum", fill_value=0)
    loc_cols = list(piv.columns); piv = piv.reset_index()
    for agg_col in ["Model Code","Product","Year"]:
        m = long_all.groupby("Match Key")[agg_col].agg(
            lambda s: next((x for x in s if str(x).strip()),"")).reset_index()
        piv = piv.merge(m, on="Match Key", how="left")
    for c in loc_cols: piv[c] = pd.to_numeric(piv[c],errors="coerce").fillna(0).astype(int)
    piv["Total Qty"] = piv[loc_cols].sum(axis=1).astype(int)
    ordered = ["Model Code","Product","Year"] + loc_cols + ["Total Qty"]
    piv = piv[[c for c in ordered if c in piv.columns]]
    return piv.sort_values(["Total Qty","Model Code"],ascending=[False,True]).reset_index(drop=True)

# ══════════════════════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════════════════════
def compute_missing_analysis(df, active_systems):
    if df is None or df.empty or not active_systems: return pd.DataFrame()
    qty_cols = {s:f"{s} Qty" for s in active_systems if f"{s} Qty" in df.columns}
    swag_col = qty_cols.get("SWAG")
    if not qty_cols or not swag_col: return pd.DataFrame()
    has_swag = df[swag_col] > 0
    base_cols = ["Model Code","Product"] + (["Year"] if "Year" in df.columns else [])
    rows = []
    for sys, col in qty_cols.items():
        if sys == "SWAG": continue
        flagged = df[has_swag & (df[col] == 0)][base_cols + [swag_col]].copy()
        if not flagged.empty:
            flagged["Missing In"] = get_system_name(sys)
            flagged.rename(columns={swag_col:"SWAG Qty"}, inplace=True)
            rows.append(flagged[base_cols + ["SWAG Qty","Missing In"]])
    if not rows: return pd.DataFrame()
    return pd.concat(rows,ignore_index=True).sort_values("SWAG Qty",ascending=False).reset_index(drop=True)

def compute_price_alerts(df, active_systems):
    if df is None or df.empty: return pd.DataFrame()
    price_cols = {s:f"{s} Price" for s in active_systems if f"{s} Price" in df.columns}
    if len(price_cols) < 2: return pd.DataFrame()
    alerts = []
    for _, row in df.iterrows():
        prices = {s:float(row[col]) for s,col in price_cols.items() if float(row[col])>0}
        if len(prices) < 2: continue
        min_p, max_p = min(prices.values()), max(prices.values())
        if min_p == 0: continue
        diff_pct = ((max_p-min_p)/min_p)*100
        if diff_pct >= PRICE_DIFF_THRESHOLD_PCT:
            alert = {"Model Code":row.get("Model Code",""),"Product":row.get("Product",""),
                     "Min Price":round(min_p,2),"Max Price":round(max_p,2),"Diff %":round(diff_pct,1),
                     "Cheapest In":get_system_name(min(prices,key=prices.get)),
                     "Highest In":get_system_name(max(prices,key=prices.get))}
            for s,col in price_cols.items():
                alert[f"{get_system_name(s)} Price"] = float(row[col])
            alerts.append(alert)
    if not alerts: return pd.DataFrame()
    return pd.DataFrame(alerts).sort_values("Diff %",ascending=False).reset_index(drop=True)

def compute_stock_value(df, active_systems):
    out = {}
    for s in active_systems:
        qcol, pcol = f"{s} Qty", f"{s} Price"
        if qcol in df.columns and pcol in df.columns:
            out[get_system_name(s)] = float((df[qcol]*df[pcol]).sum())
    return out

def compute_stock_value_by_branch(long_all):
    if long_all is None or long_all.empty: return pd.DataFrame()
    w = long_all.copy()
    w["Value"] = (pd.to_numeric(w["Qty"],errors="coerce").fillna(0) *
                  pd.to_numeric(w["Price"],errors="coerce").fillna(0))
    g = (w.groupby(["System","Branch"],as_index=False)
          .agg(Qty=("Qty","sum"),Value=("Value","sum"),SKUs=("Match Key","nunique")))
    g["Company"] = g["System"].map(get_system_name)
    return g[["Company","Branch","SKUs","Qty","Value"]].sort_values("Value",ascending=False).reset_index(drop=True)

def compute_zero_stock(company_df):
    if company_df is None or company_df.empty or "Total Qty" not in company_df.columns: return pd.DataFrame()
    cols = [c for c in ["Model Code","Product","Year","Season"] if c in company_df.columns]
    return company_df[company_df["Total Qty"]==0][cols].reset_index(drop=True)

# ══════════════════════════════════════════════════════
# MULTI-SHEET EXCEL
# ══════════════════════════════════════════════════════
def to_excel_views(company_df, branch_df, branch_value_df, zero_df, season_name):
    from openpyxl.styles import PatternFill, Font, Alignment
    from openpyxl.utils import get_column_letter
    buf = io.BytesIO()

    def _style(ws):
        hf = PatternFill("solid", fgColor="060D0E")
        ff = Font(bold=True, color="4AACB4", size=11, name="Calibri")
        for c in range(1, ws.max_column+1):
            cell = ws.cell(row=1, column=c)
            cell.fill=hf; cell.font=ff
            cell.alignment = Alignment(horizontal="center",vertical="center")
        ws.freeze_panes = "A2"
        last = min(ws.max_row, 200)
        for c in range(1, ws.max_column+1):
            cl = get_column_letter(c)
            ml = max((len(str(ws.cell(row=r,column=c).value or "")) for r in range(1,last+1)), default=10)
            ws.column_dimensions[cl].width = min(max(ml+2,12),45)
        ws.sheet_properties.tabColor = "4AACB4"
        # auto filter
        ws.auto_filter.ref = f"A1:{get_column_letter(ws.max_column)}{ws.max_row}"
        # alternate row fill
        alt = PatternFill("solid", fgColor="0D1A1C")
        for r in range(2, ws.max_row+1):
            if r % 2 == 0:
                for col in range(1, ws.max_column+1):
                    ws.cell(row=r,column=col).fill = alt

    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        def _sheet(df, name):
            if df is None or df.empty:
                pd.DataFrame({"info":["no data"]}).to_excel(w,index=False,sheet_name=name)
            else:
                df.to_excel(w,index=False,sheet_name=name)
            _style(w.sheets[name])

        _sheet(company_df,      "Company View")
        _sheet(branch_df,       "Branch View")
        _sheet(branch_value_df, "Branch Value")
        if zero_df is not None and not zero_df.empty:
            _sheet(zero_df, "Zero Stock")

        # Footer
        for sname in w.sheets:
            ws = w.sheets[sname]
            fr = ws.max_row + 2
            ws.cell(row=fr, column=1,
                    value=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Season: {season_name}"
                    ).font = Font(italic=True, color="4AACB4", size=9, name="Calibri")

    return buf.getvalue()

# ══════════════════════════════════════════════════════
# SEASON LIST BUILDERS
# ══════════════════════════════════════════════════════
def build_unified_season_list(all_systems_info):
    all_labels = set()
    for sys, info in all_systems_info.items():
        for val, lbl in info.get("seasons",[]):
            if str(lbl).strip(): all_labels.add(str(lbl).strip())
    def sort_key(lbl):
        stype = season_type_only(lbl) or "ZZZ"
        yr    = season_year(lbl)
        return (stype, -(int(yr) if yr else 0), lbl)
    return sorted(all_labels, key=sort_key)

def build_available_types(all_systems_info):
    types_found = set()
    for sys, info in all_systems_info.items():
        for val, lbl in info.get("seasons",[]):
            t = season_type_only(lbl)
            if t: types_found.add(t)
    return [t for t in ["SUMMER","WINTER","SPRING","FALL"] if t in types_found]

# ══════════════════════════════════════════════════════
# AUDIT REPORT UI
# ══════════════════════════════════════════════════════
def _register_manual_system(sys, candidate):
    seasons = fetch_distinct_seasons_from_field(
        sys, candidate["model"], candidate["field_name"],
        candidate["field_type"], candidate["relation_model"])
    if seasons:
        info = st.session_state.get("all_systems_info",{})
        info[sys] = {"model":candidate["model"],"field":candidate["field_name"],
                     "ftype":candidate["field_type"],"relation":candidate["relation_model"],"seasons":seasons}
        st.session_state["all_systems_info"] = info
        st.session_state["unified_seasons"]  = build_unified_season_list(info)
        return len(seasons)
    return 0

def render_audit_report(audits):
    st.markdown("<div class='section-tag'>Deep Season Field Audit Report</div>", unsafe_allow_html=True)
    for sys in SYSTEM_KEYS:
        audit = audits.get(sys)
        if not audit: st.markdown(f"**{get_system_name(sys)}** — not audited"); continue
        found=audit.get("confident",False); manual=audit.get("manual_pick_needed",False)
        icon = "✅" if found else ("⚠️" if manual else "❌")
        label = "Field Found" if found else ("Manual Pick Needed" if manual else "No Field Identified")
        with st.expander(f"{get_system_name(sys)}  —  {icon} {label}", expanded=not found):
            st.markdown(f"**Status:** `{audit['status']}` | Raw: **{audit.get('raw_field_count','?')}** | "
                        f"Eligible: **{audit.get('eligible_field_count','?')}** | "
                        f"Sample IDs: **{audit.get('sample_ids_loaded','?')}** | "
                        f"Records: **{audit.get('product_records_loaded','?')}**")
            if audit.get("error"): st.warning(audit["error"])
            if audit.get("best_field"):
                best=audit["best_field"]; probe=best.get("relation_probe") or {}
                st.success(f"Best: `{best['model']}.{best['field_name']}` | type: {best['field_type']} | "
                           f"label: **{best['field_label']}** | score: {round(best['total_score'],1)}")
                if probe.get("sample_names"): st.markdown("**Related names:** "+"  |  ".join(probe["sample_names"][:10]))
            candidates = audit.get("candidates",[])
            pickable = [c for c in candidates if c["total_score"]>-49 and
                        not (c.get("rejection_reason") or "").startswith("Blacklisted")]
            if pickable and not found:
                st.markdown("---"); st.markdown("**🔧 Manual field override**")
                field_options = {
                    f"{c['model']}.{c['field_name']} [{c['field_label']}] (score {round(c['total_score'],1)})": c
                    for c in pickable[:20]}
                chosen_label = st.selectbox("Choose the season field", list(field_options.keys()), key=f"manual_{sys}")
                chosen = field_options[chosen_label]
                if st.button(f"✓ Use this field for {get_system_name(sys)}", key=f"use_{sys}"):
                    n = _register_manual_system(sys, chosen)
                    if n: st.success(f"Set! Found {n} seasons."); st.rerun()
                    else: st.error("No season values found with that field.")

# ══════════════════════════════════════════════════════
# COMPANY STATUS
# ══════════════════════════════════════════════════════
def render_company_status(all_systems_info, audits, fetch_debug):
    st.markdown(f"<div class='section-tag'>Companies ({len(SYSTEM_KEYS)})</div>", unsafe_allow_html=True)
    loaded=0; lines=[]
    for sys in SYSTEM_KEYS:
        name=get_system_name(sys); d=(fetch_debug or {}).get(sys)
        if d is not None:
            if d.get("error"):
                lines.append(f"❌ **{name}** — error: {d.get('error')}")
            elif d.get("resolve_error"):
                lines.append(f"⚠️ **{name}** — season did not match")
            elif d.get("products_found",0)>0:
                loaded+=1; yrs=d.get("matched_years") or []
                yr_txt=f" [years: {', '.join(yrs)}]" if yrs else ""
                ws2=d.get("with_stock"); stock_txt=f" ({ws2:,} with stock)" if ws2 is not None else ""
                partial="  ⚠️ PARTIAL (row limit hit)" if d.get("limit_hit") else ""
                lines.append(f"✅ **{name}** — {d.get('products_found',0):,} products{stock_txt}{yr_txt}{partial}")
            else:
                lines.append(f"⚠️ **{name}** — 0 products")
            continue
        if sys in all_systems_info:
            n_seasons=len(all_systems_info[sys].get("seasons",[]))
            lines.append(f"🟢 **{name}** — season field found ({n_seasons:,} seasons), ready")
        else:
            a=audits.get(sys) or {}; status=a.get("status")
            if status=="auth_failed": lines.append(f"❌ **{name}** — login/connection failed")
            elif status=="no_config": lines.append(f"❌ **{name}** — config missing")
            elif status in ("no_confident_field","no_candidates"): lines.append(f"⚠️ **{name}** — season field could not be auto-detected")
            elif a.get("error"): lines.append(f"⚠️ **{name}** — {a.get('error')}")
            else: lines.append(f"⚪ **{name}** — status unknown")
    for ln in lines: st.markdown(ln)
    if fetch_debug: st.caption(f"Loaded data for {loaded} / {len(SYSTEM_KEYS)} companies.")

# ══════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════
def show_login():
    with st.form("login_form"):
        email    = st.text_input("Email", placeholder="you@company.com")
        password = st.text_input("Password", type="password")
        submit   = st.form_submit_button("Sign In", type="primary", use_container_width=True)
    if submit:
        if not email or not password: st.error("Fill both fields."); return
        if "LOGIN" not in st.secrets: st.error("Missing LOGIN section in secrets.toml"); return
        cfg = st.secrets["LOGIN"]
        try:
            login_url = str(cfg.get("url","")).rstrip("/")
            if login_url.endswith("/odoo"): login_url=login_url[:-5]
            proxy = xmlrpc.client.ServerProxy(login_url+"/xmlrpc/2/common", allow_none=True)
            uid = proxy.authenticate(cfg["db"], email, password, {})
            if uid:
                token = _make_token(email)
                st.query_params["u"]=email; st.query_params["t"]=token
                st.session_state.authenticated=True; st.session_state.user_email=email; st.rerun()
            else:
                st.error("Wrong email or password.")
        except Exception as e:
            st.error("Connection error: "+str(e))

def do_logout():
    try: st.query_params.clear()
    except Exception: pass
    st.session_state.authenticated=False; st.session_state.user_email=""; st.rerun()

# ══════════════════════════════════════════════════════
# MAIN DASHBOARD
# ══════════════════════════════════════════════════════
def show_dashboard():
    with st.sidebar:
        st.markdown("### SWAG")
        st.write(st.session_state.user_email)
        diag = st.checkbox("Diagnostics", value=False)
        include_archived = not st.checkbox("Active products only (exclude archived)", value=False)
        if st.button("Reload Seasons", use_container_width=True, type="secondary"):
            try: run_full_discovery.clear()
            except Exception: pass
            for k in ["all_systems_info","audits","audit_done","season_matrix","season_name",
                      "fetch_debug","unified_seasons","available_types","long_all",
                      "company_df","branch_df","branch_value_df","zero_df"]:
                st.session_state.pop(k, None)
            st.rerun()
        if st.button("Logout", use_container_width=True, type="secondary"):
            do_logout()

    st.markdown("<div class='hero-title'>Season <em>Comparison</em></div>", unsafe_allow_html=True)

    if not st.session_state.get("audit_done"):
        with st.spinner("Loading seasons..."):
            all_systems_info, audits = run_full_discovery()
            st.session_state["all_systems_info"] = all_systems_info
            st.session_state["audits"]            = audits
            st.session_state["audit_done"]        = True
            st.session_state["unified_seasons"]   = build_unified_season_list(all_systems_info)
            st.session_state["available_types"]   = build_available_types(all_systems_info)
            for k in ["season_matrix","season_name","fetch_debug","long_all",
                      "company_df","branch_df","branch_value_df","zero_df"]:
                st.session_state.pop(k, None)

    all_systems_info = st.session_state.get("all_systems_info",{})
    audits           = st.session_state.get("audits",{})
    fetch_debug      = st.session_state.get("fetch_debug",{})
    unified_seasons  = st.session_state.get("unified_seasons",[])
    available_types  = st.session_state.get("available_types",[])

    if diag: render_audit_report(audits)
    render_company_status(all_systems_info, audits, fetch_debug)
    if not all_systems_info: st.error("No season field could be detected for any company."); return

    # ── SEARCH ──
    st.markdown("<div class='section-tag'>Search Season</div>", unsafe_allow_html=True)
    search_mode = st.radio("Selection mode",
        ["🌦️ Season type — ALL years, ALL companies","🎯 Exact season"],
        horizontal=True, label_visibility="collapsed")
    selected_query=""; resolve_mode="type"
    if search_mode.startswith("🌦️"):
        resolve_mode="type"
        col_pick, col_type = st.columns([2,3])
        with col_pick:
            if available_types:
                picked = st.selectbox("Season type",
                    options=[""] + available_types,
                    format_func=lambda t: "— Choose a type —" if t=="" else SEASON_TYPE_LABEL.get(t,t),
                    key="season_type_pick")
                if picked: selected_query=picked
            else: st.warning("No season types detected.")
        with col_type:
            typed = st.text_input("...or type it", placeholder="winter / صيفي / summer", key="season_type_typed")
            if typed.strip():
                t2 = season_type_only(typed.strip())
                if t2: selected_query=t2
                else: st.warning(f"'{typed}' is not a recognized season type")
    else:
        resolve_mode="exact"
        if unified_seasons:
            selected_query = st.selectbox("Season", options=[""] + unified_seasons,
                format_func=lambda x: "— Choose a season —" if x=="" else x, key="season_exact_pick")
        else: st.warning("No seasons loaded. Reload.")

    if selected_query:
        title = (SEASON_TYPE_LABEL.get(selected_query, selected_query) if resolve_mode=="type" else selected_query)
        st.markdown(f"<div class='info-banner'>Will fetch: {title}</div>", unsafe_allow_html=True)
        preview_cols = st.columns(len(all_systems_info))
        for i, (sys, info) in enumerate(all_systems_info.items()):
            vals, lbls, err = resolve_season_values_for_system(selected_query, info, resolve_mode)
            with preview_cols[i]:
                show = "<br>".join(lbls) if lbls else "—"
                st.markdown(f"<div class='season-match-box'><div class='season-match-sys'>"
                            f"{get_system_name(sys)}</div>"
                            f"<div class='season-match-label'>{show}</div></div>", unsafe_allow_html=True)

    col_btn, _ = st.columns([1,4])
    with col_btn:
        compare_clicked = st.button("Compare", type="primary", disabled=not bool(selected_query))

    if compare_clicked and selected_query:
        with st.spinner("Fetching from all companies via stock.quant..."):
            company_df, branch_df, long_all, fetch_debug = build_season_views(
                selected_query, all_systems_info, resolve_mode, include_archived)
        st.session_state["fetch_debug"]  = fetch_debug
        st.session_state["long_all"]     = long_all
        if company_df.empty:
            st.error("No products found for this season.")
        else:
            disp = (SEASON_TYPE_LABEL.get(selected_query, selected_query)
                    if resolve_mode=="type" else selected_query)
            branch_value_df = compute_stock_value_by_branch(long_all)
            zero_df         = compute_zero_stock(company_df)
            st.session_state["company_df"]      = company_df
            st.session_state["branch_df"]       = branch_df
            st.session_state["branch_value_df"] = branch_value_df
            st.session_state["zero_df"]         = zero_df
            st.session_state["season_name"]     = disp
            for k in ["excel_bytes","excel_for"]: st.session_state.pop(k, None)
            st.rerun()

    # ══════════════════════════════════════════════════════
    # RESULTS
    # ══════════════════════════════════════════════════════
    if "company_df" not in st.session_state: return
    company_df      = st.session_state["company_df"]
    branch_df       = st.session_state.get("branch_df", pd.DataFrame())
    branch_value_df = st.session_state.get("branch_value_df", pd.DataFrame())
    zero_df         = st.session_state.get("zero_df", pd.DataFrame())
    season_name     = st.session_state["season_name"]
    active_systems  = [s for s in SYSTEM_KEYS if f"{s} Qty" in company_df.columns]

    # ── Summary metrics ──
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Models",    f"{len(company_df):,}")
    c2.metric("Total Units",     f"{int(company_df['Total Qty'].sum()):,}")
    years_set = set()
    if "Year" in company_df.columns:
        years_set = {y for v in company_df["Year"] for y in str(v).split(", ") if y}
    c3.metric("Years Covered",   ", ".join(sorted(years_set)) or "—")
    has_stock_count = int((company_df["Total Qty"] > 0).sum())
    c4.metric("Models with Stock", f"{has_stock_count:,}")

    # ── Stock value per system ──
    stock_val = compute_stock_value(company_df, active_systems)
    if stock_val:
        with st.expander("💵 Stock Value per Company (qty × price)", expanded=False):
            vcols = st.columns(len(stock_val))
            for i,(name,val) in enumerate(stock_val.items()):
                vcols[i].metric(name, f"{val:,.0f} SAR")

    # ── Branch value table ──
    if branch_value_df is not None and not branch_value_df.empty:
        with st.expander(f"🏪 Stock Value by Branch — {len(branch_value_df)} locations", expanded=False):
            st.dataframe(branch_value_df, use_container_width=True, height=350)

    # ── Zero stock report ──
    if zero_df is not None and not zero_df.empty:
        with st.expander(f"🚫 Zero Stock Models — {len(zero_df):,} models (in season but no stock anywhere)", expanded=False):
            st.dataframe(zero_df, use_container_width=True, height=350)
            buf_z = io.BytesIO()
            zero_df.to_excel(buf_z, index=False)
            st.download_button("Download Zero Stock Excel", data=buf_z.getvalue(),
                               file_name=f"zero_stock_{season_name}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               key="zero_download")

    # ── Missing products ──
    missing_df = compute_missing_analysis(company_df, active_systems)
    if not missing_df.empty:
        with st.expander(f"⚠️ Missing Products Alert — {len(missing_df):,} items in SWAG but not in others", expanded=False):
            st.markdown("<div class='alert-missing'>In stock in SWAG, 0 in another system</div>", unsafe_allow_html=True)
            st.dataframe(missing_df.head(200), use_container_width=True, height=350)
            buf_m = io.BytesIO(); missing_df.to_excel(buf_m, index=False)
            st.download_button("Download Missing Products Excel", data=buf_m.getvalue(),
                               file_name=f"missing_{season_name}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               key="missing_download")

    # ── Price alerts ──
    price_alerts_df = compute_price_alerts(company_df, active_systems)
    if not price_alerts_df.empty:
        with st.expander(f"💰 Price Alerts — {len(price_alerts_df):,} products with {PRICE_DIFF_THRESHOLD_PCT:.0f}%+ gap", expanded=False):
            st.markdown("<div class='alert-price'>Same product, different price across companies</div>", unsafe_allow_html=True)
            st.dataframe(price_alerts_df.head(200), use_container_width=True, height=350)
            buf_p = io.BytesIO(); price_alerts_df.to_excel(buf_p, index=False)
            st.download_button("Download Price Alerts Excel", data=buf_p.getvalue(),
                               file_name=f"price_alerts_{season_name}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               key="price_download")

    # ── Tabs: Company | Branch ──
    tab_company, tab_branch = st.tabs(["🏢 Company View", "🏪 Branch View"])

    with tab_company:
        st.markdown("<div class='section-tag'>Company Matrix (all models, even zero stock)</div>", unsafe_allow_html=True)
        show_zero = st.checkbox("Include zero-stock models", value=True, key="show_zero_company")
        df_show = company_df if show_zero else company_df[company_df["Total Qty"] > 0]
        st.dataframe(df_show.head(200), use_container_width=True, height=600)
        st.caption(f"Preview: top 200 of {len(df_show):,} models. Download for full data.")

    with tab_branch:
        st.markdown("<div class='section-tag'>Branch Matrix (stock.quant — all locations)</div>", unsafe_allow_html=True)
        if branch_df is None or branch_df.empty:
            st.info("No branch-level stock data available (all quantities may be 0).")
        else:
            st.dataframe(branch_df.head(200), use_container_width=True, height=600)
            st.caption(f"Preview: top 200 of {len(branch_df):,} models. Download for full data.")

    # ── Excel download ──
    if st.session_state.get("excel_for") != season_name or "excel_bytes" not in st.session_state:
        with st.spinner(f"Preparing multi-sheet Excel ({len(company_df):,} models)..."):
            st.session_state["excel_bytes"] = to_excel_views(
                company_df, branch_df, branch_value_df, zero_df, season_name)
            st.session_state["excel_for"] = season_name

    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        label="📥 Download Full Excel (Company + Branch + Value + Zero Stock sheets)",
        data=st.session_state["excel_bytes"],
        file_name=f"season_{season_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="main_download",
    )

    if diag:
        with st.expander("Fetch Debug"):
            for sys, dbg in st.session_state.get("fetch_debug", {}).items():
                st.markdown(f"**{get_system_name(sys)}**")
                if dbg.get("error"): st.error(dbg["error"])
                for k, v in dbg.items(): st.write(f"{k}: {v}")
                st.write("---")

    if st.button("Clear Results", type="secondary"):
        for k in ["company_df","branch_df","branch_value_df","zero_df","season_name",
                  "fetch_debug","long_all","excel_bytes","excel_for"]:
            st.session_state.pop(k, None)
        st.rerun()


restore_session()
if not st.session_state.authenticated:
    show_login()
else:
    show_dashboard()
