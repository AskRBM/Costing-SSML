
import os, hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="RBM Textile Costing", page_icon="🧵", layout="wide", initial_sidebar_state="collapsed")

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
GROUP_CSV = DATA_DIR / "group_costing.csv"
RM_CSV = DATA_DIR / "rm_price_master.csv"
USERS_CSV = DATA_DIR / "users_default.csv"

TABLE_USERS = "users"
TABLE_AUDIT = "audit_log"
TABLE_SORT = "sort_master"
TABLE_RM = "rm_price_master"

PERMISSIONS = [
    ("can_cost_sheet", "Cost Sheet"),
    ("can_cost_local", "Cost - Local"),
    ("can_cost_export", "Cost - Export"),
    ("can_add_sort", "Add Sort"),
    ("can_edit_sort", "Edit Sort"),
    ("can_delete_sort", "Delete Sort"),
]

DEFAULT_SUPABASE_URL = "https://mmzvwlitakluttlnnioh.supabase.co"

# ---------- CSS ----------
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {background:#eaf6fb;}
.block-container {padding:0.05rem 0.35rem 0.25rem 0.35rem; max-width:100%;}
[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {display:none !important;}
div[data-testid="stVerticalBlock"] {gap:0.10rem;}
input, textarea {color:#0b1f35 !important; background:#fff !important;}
label[data-testid="stWidgetLabel"] p{font-weight:900;font-size:12px;margin:0;}
.stButton>button{font-weight:900;border-radius:4px;min-height:30px;padding:.25rem .75rem;font-size:13px;}
.stSelectbox div[data-baseweb="select"]>div,.stNumberInput input,.stTextInput input{min-height:28px;height:28px;font-size:12px;}
/* Header exactly compact desktop style */
.topbar{background:#0b4f73;color:#fff;display:grid;grid-template-columns:145px 230px 1fr 390px;align-items:center;gap:8px;padding:5px 10px;min-height:52px;border-radius:4px 4px 0 0;}
.logo{font-size:27px;font-weight:950;line-height:25px;letter-spacing:.5px}.logosub{font-size:8px;font-weight:900;line-height:10px}
.titlebox{background:#128b77;color:#fff;padding:9px 12px;font-size:20px;font-weight:950;text-align:center;border-bottom:4px solid #c8f5e8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.userarea{display:flex;gap:8px;align-items:center;justify-content:flex-end;font-size:12px;font-weight:900}.pill{padding:8px 12px;border-radius:4px;color:#fff;font-weight:950}.green{background:#08a84d}.on{background:#087b2d}.red{background:#d91515}
.navbar{background:#0b4f73;padding:0 390px 6px 390px;margin-top:-42px;min-height:40px;}
.navbar div[data-testid="column"]{padding:0 3px}.navbar .stButton>button{width:100%;background:#fff;color:#09294a;border:1px solid #b8c5d8}.navbar .stButton>button[kind="primary"]{background:#0d6edb;color:#fff;border-color:#0d6edb}
.control{background:#e3ded8;border:1px solid #d5d1cc;padding:4px 8px;margin:0;display:flex;align-items:center;gap:8px;}
.fast{color:#006b16;font-weight:950;font-size:13px;padding-top:6px}
.report{background:#f6fbff;border:1px solid #b9cfdf;padding:5px;border-radius:3px}
.report-head{background:#0b4f73;color:#fff;padding:5px 9px;font-size:17px;font-weight:950;display:flex;justify-content:space-between;align-items:center}
.metric-row{display:grid;grid-template-columns:repeat(5,1fr);gap:5px;margin:3px 0}
.metric{color:white;padding:4px 8px;border-radius:2px;min-height:24px;display:flex;align-items:center;gap:14px;white-space:nowrap;overflow:hidden}.metric small{font-size:10px;font-weight:950}.metric b{font-size:13px}
.bg-teal{background:#138b75}.bg-blue{background:#405ad9}.bg-gold{background:#9c6a00}.bg-green{background:#10a848}.bg-red{background:#b52e34}.bg-navy{background:#0b4f73}
.whatbox{border:1px solid #b9c3cf;background:#f7fbff;padding:4px 7px;margin:2px 0 5px 0;border-radius:2px}
.what-title{font-weight:950;color:#09294a;font-size:13px;margin-bottom:3px}
.table-box{border:1px solid #cfd8e2;background:#fff;padding:0}.table-box table{width:100%;border-collapse:collapse;font-size:12px}.table-box th{background:#0b4f73;color:#fff;padding:5px 7px;border:1px solid #111;text-align:left;font-weight:950}.table-box td{padding:3px 7px;border:1px solid #111;background:#f7fbff;font-weight:750}.table-box tr:nth-child(even) td{background:#edf5ff}
.green-row td{background:#9ff0ad !important;font-weight:950}.red-row td:first-child{background:#ff5757 !important;color:#fff;font-weight:950}.red-row td:last-child{background:#ffc9c9 !important;font-weight:950}.yellow-row td{background:#fff0b7 !important;font-weight:950}
.section-head{background:#128b77;color:#fff;padding:6px 10px;font-size:18px;font-weight:950;margin:0}
.compact-card{border:1px solid #b9cfdf;background:#f6fbff;padding:8px;border-radius:4px}
.foot{background:#073f66;color:#fff;margin-top:8px;padding:9px 18px;display:flex;justify-content:space-between;font-weight:900}.yellow{color:#ffe900}
@media(max-width:1100px){.topbar{grid-template-columns:140px 1fr}.navbar{margin-top:0;padding:0 6px 6px 6px}.userarea{grid-column:1/3;justify-content:flex-start}.metric-row{grid-template-columns:1fr 1fr}.control{display:block}.foot{display:block}.titlebox{font-size:18px}}
</style>
""", unsafe_allow_html=True)

# ---------- Helpers ----------
def get_secret(name: str, default: str = "") -> str:
    try:
        if name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass
    return os.getenv(name, default).strip()

SUPABASE_URL = get_secret("SUPABASE_URL", DEFAULT_SUPABASE_URL).rstrip("/")
SUPABASE_SECRET_KEY = get_secret("SUPABASE_SECRET_KEY", "")

def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def hash_password(password: str) -> str:
    return hashlib.sha256((password or "").encode("utf-8")).hexdigest()

def clean_num(v: Any, default: Optional[float] = 0.0) -> Optional[float]:
    try:
        if v is None:
            return default
        s = str(v).strip()
        if s == "" or s in ["-", "#VALUE!", "nan", "None"]:
            return default
        return float(s.replace(",", ""))
    except Exception:
        return default

def fmt(v: Any, decimals: int = 2) -> str:
    n = clean_num(v, None)
    if n is None:
        return "-"
    if abs(n - int(n)) < 0.0000001:
        return str(int(n))
    return f"{n:.{decimals}f}"

def sb_headers() -> Dict[str, str]:
    if not SUPABASE_SECRET_KEY:
        raise RuntimeError("SUPABASE_SECRET_KEY missing in Streamlit Secrets.")
    return {"apikey": SUPABASE_SECRET_KEY, "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
            "Content-Type": "application/json", "Prefer": "return=representation"}

def sb_url(table: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{table}"

def sb_select(table: str, params: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    r = requests.get(sb_url(table), headers=sb_headers(), params=params or {}, timeout=25)
    if r.status_code >= 300:
        raise RuntimeError(f"Supabase select failed {table}: {r.status_code} {r.text}")
    return r.json()

def sb_insert(table: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    r = requests.post(sb_url(table), headers=sb_headers(), json=payload, timeout=25)
    if r.status_code >= 300:
        raise RuntimeError(f"Supabase insert failed {table}: {r.status_code} {r.text}")
    clear_cache()
    return r.json() if r.text else []

def sb_update(table: str, filters: Dict[str, str], payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    r = requests.patch(sb_url(table), headers=sb_headers(), params=filters, json=payload, timeout=25)
    if r.status_code >= 300:
        raise RuntimeError(f"Supabase update failed {table}: {r.status_code} {r.text}")
    clear_cache()
    return r.json() if r.text else []

def sb_delete(table: str, filters: Dict[str, str]) -> None:
    h = sb_headers(); h["Prefer"] = "return=minimal"
    r = requests.delete(sb_url(table), headers=h, params=filters, timeout=25)
    if r.status_code >= 300:
        raise RuntimeError(f"Supabase delete failed {table}: {r.status_code} {r.text}")
    clear_cache()

def clear_cache():
    try:
        load_group_data.clear(); load_rm_data.clear(); get_users.clear()
    except Exception:
        pass

@st.cache_data(ttl=300)
def load_group_data() -> pd.DataFrame:
    df = pd.read_csv(GROUP_CSV, dtype=str).fillna("")
    return df

@st.cache_data(ttl=300)
def load_rm_data() -> pd.DataFrame:
    if RM_CSV.exists():
        return pd.read_csv(RM_CSV, dtype=str).fillna("")
    return pd.DataFrame()

@st.cache_data(ttl=120)
def get_users() -> List[Dict[str, Any]]:
    try:
        return sb_select(TABLE_USERS, {"select":"*","order":"id.asc","limit":"1000"})
    except Exception:
        if USERS_CSV.exists():
            return pd.read_csv(USERS_CSV, dtype=str).fillna("").to_dict("records")
        return [{"username":"admin","password":"rbm123","role":"Developer","can_cost_sheet":True,"can_cost_local":True,"can_cost_export":True,"can_add_sort":True,"can_edit_sort":True,"can_delete_sort":True}]

def audit(action: str, old_value: str = "", new_value: str = "") -> None:
    try:
        sb_insert(TABLE_AUDIT, {"username": st.session_state.get("username","system"), "action": action, "old_value": old_value, "new_value": new_value, "created_at": now_text()})
    except Exception:
        pass

def is_developer() -> bool:
    return st.session_state.get("role") == "Developer"

def has_perm(perm: str) -> bool:
    if is_developer():
        return True
    return bool(st.session_state.get("perms", {}).get(perm))

def find_user(username: str) -> Optional[Dict[str, Any]]:
    for u in get_users():
        if str(u.get("username","")).strip().lower() == username.strip().lower():
            return u
    return None

def list_sort_numbers() -> List[str]:
    df = load_group_data()
    key = "dev_sorts" if "dev_sorts" in df.columns else "sort_no"
    return [str(x).strip() for x in df[key].tolist() if str(x).strip()]

def get_sort(sort_no: str) -> Optional[Dict[str, Any]]:
    df = load_group_data()
    for key in ["dev_sorts","sort_no"]:
        if key in df.columns:
            m = df[df[key].astype(str).str.strip() == str(sort_no).strip()]
            if not m.empty:
                return m.iloc[0].to_dict()
    return None

def first_sort() -> str:
    rows = list_sort_numbers()
    return rows[0] if rows else ""

# ---------- Desktop exact calculation ----------
def derive_after_knitting_pct(row: Dict[str, Any]) -> float:
    raw = clean_num(row.get("raw_material_cost"), 0) or 0
    knit = clean_num(row.get("knittng__processing_cost"), 0) or 0
    waste2 = clean_num(row.get("wastage_2"), 0) or 0
    base = raw + knit
    return (waste2 / base * 100) if base else 0

def derive_margin_pct(row: Dict[str, Any]) -> float:
    costing = clean_num(row.get("costing"), 0) or 0
    margin = clean_num(row.get("margin"), 0) or 0
    return (margin / costing * 100) if costing else 0

def derive_commission_pct(row: Dict[str, Any]) -> float:
    price = clean_num(row.get("price_per_kg_inr"), clean_num(row.get("selling_price"), 0)) or 0
    comm = clean_num(row.get("commission"), 0) or 0
    return (comm / price * 100) if price else 0

def apply_whatif_to_row(row: Dict[str, Any], what: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Same logic as desktop app_desktop.py _apply_whatif_to_row."""
    what = what or {}
    row = dict(row)
    currency = clean_num(what.get("currency_rate", row.get("currency_rate")), 87) or 87
    discount = clean_num(what.get("discount_if_any", row.get("discount_if_any")), 0) or 0
    freight = clean_num(what.get("freight_inr_per_kg", row.get("freight_inr_per_kg")), 0) or 0
    commission_pct = clean_num(what.get("commission_pct", derive_commission_pct(row)), derive_commission_pct(row)) or 0
    lc_int = clean_num(what.get("lc_days_interest", row.get("lc_days_interest", row.get("lc_days__interest_15_pm"))), 0) or 0
    wastage_amt = clean_num(what.get("wastage", row.get("wastage")), 0) or 0
    dyeing = clean_num(what.get("dyeing_cost_rs", row.get("dyeing_cost_rs")), 0) or 0
    knitting = clean_num(what.get("knittng__processing_cost", row.get("knittng__processing_cost")), 90) or 0
    waste_after_pct = clean_num(what.get("wastage_after_knitting_pct", derive_after_knitting_pct(row)), derive_after_knitting_pct(row)) or 0
    margin_pct = clean_num(what.get("margin_pct", derive_margin_pct(row)), derive_margin_pct(row)) or 0

    cotton_yarn = clean_num(row.get("cotton_yarn_costing"), 0) or 0
    dyed_yarn = cotton_yarn + wastage_amt + dyeing

    cotton_prop = clean_num(row.get("cotton_dyed_proportion_cost"), None)
    if cotton_prop is None:
        cotton_prop = cotton_yarn + wastage_amt

    raw = cotton_prop
    for k in [
        "polyester_cost","spandex_cost","melange_cost","kora_yarn_cost","reactive_yarn_cost","cooltex_yarn_cost",
        "recycle_yarn_cost","dyed_poly_yarn_cost","micro_modal","viscose"
    ]:
        v = clean_num(row.get(k), 0)
        if v:
            raw += v

    base_cost = raw + knitting
    waste_after_amt = base_cost * waste_after_pct / 100.0
    costing = base_cost + waste_after_amt
    margin_amt = costing * margin_pct / 100.0
    selling = costing + margin_amt - discount
    price_per_kg = selling
    commission_amt = price_per_kg * commission_pct / 100.0
    total_inr = price_per_kg + freight + commission_amt + lc_int
    price_usd = total_inr / currency if currency else 0
    lm = clean_num(row.get("linear_mtrskg"), 0) or 0
    ly = clean_num(row.get("linear_ydgskg"), 0) or 0

    row.update({
        "wastage": wastage_amt, "dyeing_cost_rs": dyeing, "dyed_yarn_cost_rs": dyed_yarn,
        "cotton_dyed_proportion_cost": cotton_prop, "raw_material_cost": raw,
        "knittng__processing_cost": knitting, "wastage_after_knitting_pct": waste_after_pct,
        "wastage_2": waste_after_amt, "costing": costing, "margin_pct": margin_pct,
        "margin": margin_amt, "selling_price": selling, "currency_rate": currency,
        "discount_if_any": discount, "price_per_kg_inr": price_per_kg,
        "freight_inr_per_kg": freight, "commission_pct": commission_pct,
        "commission": commission_amt, "lc_days_interest": lc_int,
        "total_cost_pricefreightcomlc_int": total_inr,
        "total_cost_pricefreightcomlc_int_inr__kg": total_inr,
        "total_cost_usd__kg": price_usd, "price_usdkg": price_usd,
        "price_usdmtrs": (price_usd / lm if lm else row.get("price_usdmtrs","")),
        "price_usdyds": (price_usd / ly if ly else row.get("price_usdyds","")),
    })
    return row

# ---------- Header / Login ----------
def set_module(module: str):
    st.session_state["module"] = module

def header(title: str = "Costing"):
    username = st.session_state.get("username","")
    role = st.session_state.get("role","")
    active = st.session_state.get("module","Cost Sheet")
    st.markdown(f"""
<div class="topbar">
  <div><div class="logo">RBM AI</div><div class="logosub">Robotic Business Management</div></div>
  <div class="titlebox">Costing</div>
  <div></div>
  <div class="userarea"><span class="pill green">☁ Sync Now</span><span class="pill on">⊙ ON</span><span>User: {username} | Role: {role}</span><span class="pill red">↻ Logout</span></div>
</div>
""", unsafe_allow_html=True)

    nav_items = []
    if has_perm("can_cost_sheet"): nav_items.append(("Cost Sheet","Cost Sheet"))
    if has_perm("can_cost_local"): nav_items.append(("Cost - Local","Cost - Local"))
    if has_perm("can_cost_export"): nav_items.append(("Cost - Export","Cost - Export"))
    if has_perm("can_add_sort"): nav_items.append(("Add Sort","Add Sort"))
    if has_perm("can_add_sort"): nav_items.append(("RM Price","RM Price"))
    if is_developer(): nav_items.append(("Users","Users"))

    st.markdown("<div class='navbar'>", unsafe_allow_html=True)
    cols = st.columns(max(1, len(nav_items)))
    for i, (label, mod) in enumerate(nav_items):
        with cols[i]:
            if st.button(label, key=f"nav_{mod}", type=("primary" if active == mod else "secondary"), on_click=set_module, args=(mod,)):
                pass
    st.markdown("</div>", unsafe_allow_html=True)

    # Separate functional logout button, placed small below if needed because top red pill is visual.
    if st.session_state.get("_do_logout"):
        st.session_state.clear(); st.rerun()

def login_page():
    st.markdown("""
<div class="topbar" style="grid-template-columns:145px 250px 1fr;">
  <div><div class="logo">RBM AI</div><div class="logosub">Robotic Business Management</div></div>
  <div class="titlebox">Costing</div><div></div>
</div>
""", unsafe_allow_html=True)
    c1,c2,c3 = st.columns([1,1.2,1])
    with c2:
        st.markdown("### Secure Client Login")
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", value="", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Login", type="primary")
        if submitted:
            u = find_user(username)
            ok = False
            if u:
                stored = str(u.get("password",""))
                ok = stored == password or stored == hash_password(password)
            if ok:
                st.session_state["username"] = username.strip()
                st.session_state["role"] = u.get("role","User")
                st.session_state["perms"] = {k: bool(u.get(k) in [True, "True", "true", "1", 1]) for k,_ in PERMISSIONS}
                if st.session_state["role"] == "Developer":
                    st.session_state["perms"] = {k: True for k,_ in PERMISSIONS}
                st.session_state["module"] = "Cost Sheet" if st.session_state["perms"].get("can_cost_sheet") else ("Cost - Local" if st.session_state["perms"].get("can_cost_local") else "Cost - Export")
                audit("LOGIN","",username.strip())
                st.rerun()
            else:
                st.error("Wrong username or password.")

def require_login():
    if not st.session_state.get("username"):
        login_page()
        st.stop()

# ---------- UI pages ----------
def report_metrics(row: Dict[str, Any]):
    sort = row.get("dev_sorts") or row.get("sort_no")
    st.markdown(f"""
<div class='report-head'><span>RBM TEXTILE COST SHEET</span><span style='color:#ffe92e'>SORT NO: {sort}</span></div>
<div class='metric-row'>
  <div class='metric bg-teal'><small>Structure</small><b>{row.get('structure','-')}</b></div>
  <div class='metric bg-blue'><small>Finish GSM</small><b>{fmt(row.get('finish_gsm'),0)}</b></div>
  <div class='metric bg-gold'><small>Finish Width</small><b>{fmt(row.get('finish_width'),0)}</b></div>
  <div class='metric bg-green'><small>Selling Price</small><b>{fmt(row.get('selling_price'))}</b></div>
  <div class='metric bg-red'><small>USD/KG</small><b>{fmt(row.get('total_cost_usd__kg') or row.get('price_usdkg'))}</b></div>
</div>
""", unsafe_allow_html=True)

def table_html(title: str, rows: List[tuple], price=False) -> str:
    html = f"<div class='table-box'><table><tr><th colspan='2'>{title}</th></tr>"
    editable = {"Wastage %","Dyeing Cost Rs.","Knitting + Processing Cost","Wastage % After Knitting","Currency Rate","Freight INR/KG","Commission %","LC Days / Interest","Margin"}
    totals = {"Raw Material Cost","Costing","Selling Price","Price USD/KG","Total Cost INR/KG","Total Cost USD/KG"}
    for label, val in rows:
        cls = ""
        if "Discount" in label:
            cls = " class='red-row'"
        elif label in editable:
            cls = " class='green-row'"
        elif label in totals:
            cls = " class='yellow-row'"
        html += f"<tr{cls}><td>{label}</td><td>{fmt(val)}</td></tr>"
    html += "</table></div>"
    return html

def cost_sheet_page():
    header("Costing")
    rows = list_sort_numbers()
    default = st.session_state.get("last_sort") or first_sort()
    idx = rows.index(default) if default in rows else 0

    c0,c1,c2,c3,c4,c5 = st.columns([1.2,2.2,.9,1.25,1.3,4])
    with c0: st.markdown("<b>Sort No (Excel D1):</b>", unsafe_allow_html=True)
    with c1: sort_no = st.selectbox("Sort", rows if rows else [default], index=idx, label_visibility="collapsed", key="cost_sort")
    with c2:
        if st.button("Refresh", type="primary"):
            clear_cache(); st.rerun()
    with c3: st.button("Print Preview")
    with c4: st.button("Export This Sort")
    with c5: st.markdown("<div class='fast'>Fast mode: Cost sheet loads selected sort only</div>", unsafe_allow_html=True)

    st.session_state["last_sort"] = sort_no
    base = get_sort(sort_no)
    if not base:
        st.error("No details found for selected Sort No.")
        return

    # What-if defaults from actual desktop row, not guessed numbers.
    default_what = {
        "wastage": clean_num(base.get("wastage"),0) or 0,
        "dyeing_cost_rs": clean_num(base.get("dyeing_cost_rs"),0) or 0,
        "knittng__processing_cost": clean_num(base.get("knittng__processing_cost"),90) or 90,
        "wastage_after_knitting_pct": derive_after_knitting_pct(base),
        "discount_if_any": clean_num(base.get("discount_if_any"),0) or 0,
        "currency_rate": clean_num(base.get("currency_rate"),87) or 87,
        "freight_inr_per_kg": clean_num(base.get("freight_inr_per_kg"),0) or 0,
        "commission_pct": derive_commission_pct(base),
        "lc_days_interest": clean_num(base.get("lc_days__interest_15_pm"),0) or 0,
        "margin_pct": derive_margin_pct(base),
    }

    with st.form("whatif_form", clear_on_submit=False):
        st.markdown("<div class='report'>", unsafe_allow_html=True)
        row_preview = apply_whatif_to_row(base, default_what)
        report_metrics(row_preview)
        st.markdown("<div class='whatbox'><div class='what-title'>What-If Analysis</div>", unsafe_allow_html=True)
        c = st.columns(9)
        keys_labels = [
            ("wastage","Waste"),("dyeing_cost_rs","Dyeing"),("knittng__processing_cost","Knit"),
            ("wastage_after_knitting_pct","Knit Waste %"),("discount_if_any","Discount"),
            ("currency_rate","Curr"),("freight_inr_per_kg","Freight"),("commission_pct","Comm %"),("lc_days_interest","LC")
        ]
        vals = {}
        for i,(k,l) in enumerate(keys_labels):
            with c[i]:
                vals[k] = st.number_input(l, value=float(default_what[k]), step=0.01, format="%.2f", key=f"wi_{k}_{sort_no}")
        c10,c11,c12,c13 = st.columns([1.1,1,1,5])
        with c10:
            margin_pct = st.number_input("Margin %", value=float(default_what["margin_pct"]), step=0.01, format="%.2f", key=f"wi_margin_{sort_no}")
        with c11:
            country = st.selectbox("Country", ["Bangladesh","Vietnam","SriLanka","Japan","Colombia","Napoli","Nagoya","Istanbul"], key=f"wi_country_{sort_no}")
        with c12:
            submitted = st.form_submit_button("Apply", type="primary")
        vals["margin_pct"] = margin_pct
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    row = apply_whatif_to_row(base, vals if submitted else default_what)

    left_rows = [
        ("Cotton Yarn Costing", row.get("cotton_yarn_costing")),
        ("Wastage %", row.get("wastage")),
        ("Dyeing Cost Rs.", row.get("dyeing_cost_rs")),
        ("Dyed Yarn Cost Rs.", row.get("dyed_yarn_cost_rs")),
        ("Cotton Dyed Proportion Cost", row.get("cotton_dyed_proportion_cost")),
        ("Polyester Cost", row.get("polyester_cost")),
        ("Spandex Cost", row.get("spandex_cost")),
        ("Kora Yarn Cost", row.get("kora_yarn_cost")),
        ("Raw Material Cost", row.get("raw_material_cost")),
        ("Knitting + Processing Cost", row.get("knittng__processing_cost")),
        ("Wastage % After Knitting", row.get("wastage_after_knitting_pct")),
        ("Wastage After Knitting Cost", row.get("wastage_2")),
        ("Costing", row.get("costing")),
        ("Margin", row.get("margin")),
        ("Selling Price", row.get("selling_price")),
    ]
    right_rows = [
        ("Currency Rate", row.get("currency_rate")),
        ("Discount If Any", row.get("discount_if_any")),
        ("Price USD/KG", row.get("price_usdkg")),
        ("Price USD/Mtrs", row.get("price_usdmtrs")),
        ("Price USD/Yds", row.get("price_usdyds")),
        ("Linear Mtrs/Kg", row.get("linear_mtrskg")),
        ("Linear Yds/Kg", row.get("linear_ydgskg")),
        ("Width CMS", row.get("width_cms") or row.get("finish_width")),
        ("Width Inch", row.get("width_inch")),
        ("Weight GSM", row.get("weight_gsm") or row.get("finish_gsm")),
        ("Price Per KG INR", row.get("price_per_kg_inr")),
        ("Freight INR/KG", row.get("freight_inr_per_kg")),
        ("Commission %", row.get("commission_pct")),
        ("Commission Amount", row.get("commission")),
        ("LC Days / Interest", row.get("lc_days_interest")),
        ("Total Cost INR/KG", row.get("total_cost_pricefreightcomlc_int")),
        ("Total Cost USD/KG", row.get("total_cost_usd__kg")),
    ]
    l,r = st.columns(2)
    with l: st.markdown(table_html("▣ Cost Build-up", left_rows), unsafe_allow_html=True)
    with r: st.markdown(table_html("▣ Export / Price Calculation", right_rows), unsafe_allow_html=True)
    st.markdown("<div class='foot'><span>Publisher: <span class='yellow'>RBM Textile Solutions</span></span><span>Offline Textile Costing • Actual Excel Data • Print Preview • Backup</span><span>Made in India 🇮🇳</span></div>", unsafe_allow_html=True)

def vertical_report(title: str, items: List[tuple]):
    header("Costing")
    rows=list_sort_numbers(); default=st.session_state.get("last_sort") or first_sort()
    idx=rows.index(default) if default in rows else 0
    sort=st.selectbox("Sort No", rows if rows else [default], index=idx, key=f"vr_{title}")
    st.session_state["last_sort"]=sort
    row=get_sort(sort)
    if not row:
        st.error("No details found."); return
    calc=apply_whatif_to_row(row)
    st.markdown("<div class='report'>", unsafe_allow_html=True)
    st.markdown(f"<div class='report-head'><span>{title.upper()}</span><span>RBM Textile Costing</span></div>", unsafe_allow_html=True)
    html="<div class='table-box'><table>"
    for label,key in items:
        html += f"<tr><th>{label}</th><td><b>{fmt(calc.get(key)) if key not in ['sort_no','dev_sorts','structure'] else calc.get(key, '')}</b></td></tr>"
    html += "</table></div>"
    st.markdown(html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def sort_form_page(mode="Add"):
    header("Costing")
    st.markdown("<div class='section-head'>Add / Edit Sort Master</div>", unsafe_allow_html=True)
    with st.form("sort_form", clear_on_submit=False):
        c1,c2,c3=st.columns(3)
        with c1:
            sort_no=st.text_input("Sort No")
            structure=st.text_input("Structure")
        with c2:
            finish_gsm=st.number_input("Finish GSM", value=0.0, step=1.0, format="%.2f")
            finish_width=st.number_input("Finish Width", value=0.0, step=1.0, format="%.2f")
        with c3:
            local_cost=st.number_input("Local Cost", value=0.0, step=1.0, format="%.2f")
            sales_price=st.number_input("Sales Price", value=0.0, step=1.0, format="%.2f")
        submitted=st.form_submit_button("Submit", type="primary")
    if submitted:
        st.success("Sort entry received. For permanent cloud update, connect this form to Supabase sort_master.")

def rm_price_page():
    header("Costing")
    rows=load_rm_data()
    st.markdown("<div class='section-head'>RM Price Master</div>", unsafe_allow_html=True)
    st.dataframe(rows, use_container_width=True, height=520)

def users_page():
    header("Costing")
    if not is_developer():
        st.error("Only Developer can manage users.")
        return
    st.markdown("<div class='section-head'>User Management</div>", unsafe_allow_html=True)
    with st.form("user_form"):
        c1,c2,c3=st.columns(3)
        with c1: username=st.text_input("Username")
        with c2: password=st.text_input("Password", type="password")
        with c3: role=st.selectbox("Role", ["Admin","User"])  # Developer hidden
        cols=st.columns(6); perm_values={}
        for i,(k,label) in enumerate(PERMISSIONS):
            with cols[i%6]: perm_values[k]=st.checkbox(label)
        submitted=st.form_submit_button("Save User", type="primary")
    if submitted:
        payload={"username":username.strip(),"password":password.strip(),"role":role,**perm_values,"created_at":now_text()}
        try:
            existing = []
            try: existing = sb_select(TABLE_USERS, {"username":f"eq.{username.strip()}","select":"id","limit":"1"})
            except Exception: pass
            if existing:
                sb_update(TABLE_USERS, {"id":f"eq.{existing[0]['id']}"}, payload)
            else:
                sb_insert(TABLE_USERS, payload)
            st.success("User saved.")
        except Exception as e:
            st.error(str(e))
    st.dataframe(get_users(), use_container_width=True, height=380)

# ---------- Main ----------
require_login()
module = st.session_state.get("module","Cost Sheet")
if module == "Cost Sheet":
    cost_sheet_page()
elif module == "Cost - Local":
    vertical_report("Cost - Local", [
        ("Sort No","dev_sorts"),("Structure","structure"),("Finish GSM","finish_gsm"),("Finish Width","finish_width"),
        ("Local Cost","costing"),("Sales Price","selling_price")
    ])
elif module == "Cost - Export":
    vertical_report("Cost - Export", [
        ("Sort No","dev_sorts"),("Structure","structure"),("Finish GSM","finish_gsm"),("Finish Width","finish_width"),
        ("Price","selling_price"),("Currency Rate","currency_rate"),("USD/Kg","price_usdkg"),
        ("Price USD Mtrs","price_usdmtrs"),("Price USD Yds","price_usdyds"),
        ("Total Cost INR/KG","total_cost_pricefreightcomlc_int"),("Total Cost USD/KG","total_cost_usd__kg")
    ])
elif module == "Add Sort":
    sort_form_page("Add")
elif module == "RM Price":
    rm_price_page()
elif module == "Users":
    users_page()
else:
    cost_sheet_page()
