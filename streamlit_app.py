import os
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

# -----------------------------
# RBM TEXTILE COSTING - STREAMLIT CLOUD VERSION
# -----------------------------
st.set_page_config(
    page_title="RBM Textile Costing",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="collapsed",
)

TABLE_SORT = "sort_master"
TABLE_RM = "rm_price_master"
TABLE_USERS = "users"
TABLE_AUDIT = "audit_log"

PERMISSIONS = [
    ("can_cost_sheet", "Cost Sheet"),
    ("can_cost_local", "Cost - Local"),
    ("can_cost_export", "Cost - Export"),
    ("can_add_sort", "Add Sort"),
    ("can_edit_sort", "Edit Sort"),
    ("can_delete_sort", "Delete Sort"),
]

DEFAULT_SUPABASE_URL = "https://mmzvwlitakluttlnnioh.supabase.co"

# -----------------------------
# CSS - desktop-like professional compact layout
# -----------------------------
st.markdown(
    """
<style>
[data-testid="stAppViewContainer"] {background:#eaf6fb;}
input, textarea {color:#0b1f35 !important; background:#ffffff !important;}
[data-baseweb="input"] {background:#ffffff !important;}
div[data-testid="stTextInput"] input:disabled, div[data-testid="stNumberInput"] input:disabled {color:#111827 !important; opacity:1 !important;}
.block-container {padding:0.15rem 0.35rem 0.25rem 0.35rem; max-width:100%;}
[data-testid="stHeader"] {height:0rem; background:transparent;}
[data-testid="stToolbar"], #MainMenu, footer {display:none !important; visibility:hidden;}
div[data-testid="stVerticalBlock"] {gap:0.18rem;}
hr {margin:0.15rem 0;}
/* Top desktop-style header */
.rbm-topbar{background:#0b4f73;color:#fff;display:grid;grid-template-columns:145px 250px 1fr 315px;align-items:center;gap:8px;padding:4px 10px;border-radius:4px 4px 0 0;min-height:52px;}
.rbm-logo{font-size:28px;font-weight:900;line-height:25px;letter-spacing:.5px;}
.rbm-sub{font-size:9px;font-weight:700;line-height:11px;}
.rbm-title{background:#128b77;color:#fff;padding:10px 16px;font-size:21px;font-weight:900;text-align:center;border-bottom:4px solid #c8f5e8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.rbm-nav{display:flex;gap:6px;justify-content:center;align-items:center;flex-wrap:nowrap;}
.rbm-nav a{background:#fff;color:#09294a;text-decoration:none;border:1px solid #b8c5d8;border-radius:4px;padding:8px 15px;font-size:14px;font-weight:700;box-shadow:0 1px 2px rgba(0,0,0,.16);white-space:nowrap;}
.rbm-nav a.active{background:#0d6edb;color:#fff;border-color:#0d6edb;}
.rbm-actions{display:flex;gap:7px;align-items:center;justify-content:flex-end;font-size:12px;font-weight:800;}
.navrow{background:#0b4f73;padding:0 330px 6px 405px;margin-top:-45px;border-radius:0 0 4px 4px;min-height:43px;}
.navrow div[data-testid='column']{padding:0 3px;}
.navrow .stButton>button{width:100%;background:#fff;color:#09294a;border:1px solid #b8c5d8;border-radius:4px;font-weight:900;min-height:34px;padding:.25rem .35rem;font-size:13px;}
.navrow .stButton>button[kind='primary']{background:#0d6edb;color:#fff;}
.rbm-actions .sync,.rbm-actions .on,.rbm-actions .logout{padding:8px 12px;border-radius:4px;color:#fff;text-decoration:none;font-weight:900;}
.sync{background:#0aa74d}.on{background:#07892d}.logout{background:#cc1717}.userbox{min-width:120px;text-align:right;}
.section-head{background:#128b77;color:white;font-size:18px;font-weight:900;padding:4px 10px;margin:0;border-radius:0;}
.control-strip{background:#e3ded8;border:1px solid #d2d2d2;padding:4px 8px;display:flex;align-items:center;gap:8px;flex-wrap:nowrap;}
.fast-mode{margin-left:auto;color:#006b16;font-weight:900;font-size:13px;}
.report{background:#f6fbff;border:1px solid #b9cfdf;padding:6px;border-radius:4px;box-shadow:none;}
.report-head{background:#0b4f73;color:white;padding:6px 10px;font-size:18px;font-weight:900;display:flex;justify-content:space-between;align-items:center;}
.metric-row{display:grid;grid-template-columns:repeat(5,1fr);gap:5px;margin:4px 0;}
.metric{color:white;padding:4px 9px;border-radius:2px;min-height:26px;display:flex;align-items:center;gap:12px;}
.metric small{font-weight:900;display:inline;font-size:11px;}
.metric b{font-size:14px;display:inline;}
.bg-teal{background:#138b75}.bg-blue{background:#405ad9}.bg-gold{background:#9c6a00}.bg-green{background:#10a848}.bg-red{background:#b52e34}.bg-navy{background:#0b4f73}
.whatbox{border:1px solid #b9c3cf;background:#f7fbff;padding:5px 7px;margin:3px 0 6px 0;border-radius:3px;}
.what-title{font-weight:900;color:#09294a;margin-bottom:4px;font-size:14px;}
.table-box{border:1px solid #cfd8e2;background:#fff;padding:0;}
.table-box table{width:100%;border-collapse:collapse;font-size:13px;}
.table-box th{background:#0b4f73;color:#fff;padding:6px 8px;border:1px solid #1d1d1d;text-align:left;font-weight:900;}
.table-box td{padding:3px 8px;border:1px solid #1d1d1d;background:#f7fbff;font-weight:700;}
.table-box tr:nth-child(even) td{background:#edf5ff;}
.green-row td{background:#a8f2b2 !important;font-weight:900;}
.red-row td:first-child{background:#ff6262 !important;color:#fff;font-weight:900;}
.red-row td:last-child{background:#ffcaca !important;font-weight:900;}
.yellow-row td{background:#fff3b9 !important;font-weight:900;}
.vertical-table th{width:36%;}
.stButton>button{font-weight:900;border-radius:4px;padding:.30rem .85rem;min-height:32px;}
.stTextInput>div>div>input,.stNumberInput input,.stSelectbox div[data-baseweb="select"]>div{min-height:30px;height:30px;font-size:13px;}
label[data-testid="stWidgetLabel"] p{font-weight:800;font-size:12px;margin-bottom:0px;}
[data-testid="stForm"]{border:1px solid #b9cfdf;padding:8px;background:#f6fbff;border-radius:4px;}
/* hide +/- step buttons in number inputs less visually noisy */
button[aria-label="Step up"],button[aria-label="Step down"]{height:28px;}
@media(max-width:1050px){.rbm-topbar{grid-template-columns:140px 1fr;}.navrow{margin-top:0;padding:0 8px 6px 8px}.rbm-actions{grid-column:1/3;justify-content:flex-start}.metric-row{grid-template-columns:1fr 1fr}.control-strip{flex-wrap:wrap}.fast-mode{margin-left:0}.rbm-title{font-size:18px;}}
</style>
""",
    unsafe_allow_html=True,
)
# -----------------------------
# Helpers
# -----------------------------
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


def clean_num(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "" or str(v).strip() in ["-", "#VALUE!", "nan", "None"]:
            return default
        return float(str(v).replace(",", ""))
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
        st.error("SUPABASE_SECRET_KEY missing. Add it in Streamlit Secrets.")
        st.stop()
    return {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


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
    headers = sb_headers()
    headers["Prefer"] = "return=minimal"
    r = requests.delete(sb_url(table), headers=headers, params=filters, timeout=25)
    if r.status_code >= 300:
        raise RuntimeError(f"Supabase delete failed {table}: {r.status_code} {r.text}")
    clear_cache()


def clear_cache():
    try:
        list_sort_numbers.clear()
        get_sort.clear()
        get_rm_rows.clear()
    except Exception:
        pass


@st.cache_data(ttl=180)
def list_sort_numbers() -> List[str]:
    rows = sb_select(TABLE_SORT, {"select": "sort_no", "order": "id.asc", "limit": "2000"})
    return [str(r.get("sort_no")) for r in rows if r.get("sort_no") is not None]


@st.cache_data(ttl=180)
def get_sort(sort_no: str) -> Optional[Dict[str, Any]]:
    rows = sb_select(TABLE_SORT, {"sort_no": f"eq.{sort_no}", "select": "*", "limit": "1"})
    return rows[0] if rows else None


@st.cache_data(ttl=180)
def get_rm_rows() -> List[Dict[str, Any]]:
    return sb_select(TABLE_RM, {"select": "*", "order": "id.asc", "limit": "1000"})


def first_sort() -> str:
    rows = list_sort_numbers()
    return rows[0] if rows else ""


def compute_cost(row: Dict[str, Any], what_if: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    what_if = what_if or {}
    currency_rate = clean_num(what_if.get("currency_rate", row.get("currency_rate", 87)), 87)
    local_cost = clean_num(row.get("local_cost"), 0)
    sales_price = clean_num(row.get("sales_price"), local_cost)
    usd_kg = clean_num(row.get("usd_kg"), sales_price / currency_rate if currency_rate else 0)
    usd_mtrs = clean_num(row.get("usd_mtrs"), 0)
    usd_yds = clean_num(row.get("usd_yds"), 0)
    total_inr = clean_num(row.get("total_cost_inr_kg", row.get("total_cost_inr", local_cost)), local_cost)
    total_usd = clean_num(row.get("total_cost_usd_kg", row.get("total_cost_usd", usd_kg)), usd_kg)

    discount = clean_num(what_if.get("discount"), 0)
    margin = clean_num(what_if.get("margin"), 10)
    freight = clean_num(what_if.get("freight"), 0)
    commission = clean_num(what_if.get("commission"), 0)
    knit = clean_num(what_if.get("knit"), 0)
    wastage = clean_num(what_if.get("wastage"), 0)

    adjusted_cost = max(0, local_cost + knit + freight + commission + wastage - discount)
    adjusted_sales = adjusted_cost + (adjusted_cost * margin / 100)
    adjusted_usd = adjusted_sales / currency_rate if currency_rate else 0

    return {
        "sort_no": row.get("sort_no"),
        "structure": row.get("structure"),
        "finish_gsm": fmt(row.get("finish_gsm"), 0),
        "finish_width": fmt(row.get("finish_width"), 0),
        "local_cost": fmt(local_cost),
        "sales_price": fmt(sales_price),
        "currency_rate": fmt(currency_rate),
        "usd_kg": fmt(usd_kg),
        "usd_mtrs": fmt(usd_mtrs),
        "usd_yds": fmt(usd_yds),
        "total_cost_inr_kg": fmt(total_inr),
        "total_cost_usd_kg": fmt(total_usd),
        "what_if_cost": fmt(adjusted_cost),
        "what_if_sales": fmt(adjusted_sales),
        "what_if_usd": fmt(adjusted_usd),
    }


def audit(action: str, old_value: str = "", new_value: str = "") -> None:
    try:
        sb_insert(TABLE_AUDIT, {
            "username": st.session_state.get("username", "system"),
            "action": action,
            "old_value": old_value,
            "new_value": new_value,
            "created_at": now_text(),
        })
    except Exception:
        pass


def is_developer() -> bool:
    return st.session_state.get("role") == "Developer"


def has_perm(perm: str) -> bool:
    if is_developer():
        return True
    return bool(st.session_state.get("perms", {}).get(perm))


def require_login():
    if not st.session_state.get("username"):
        login_page()
        st.stop()


def set_module(module_name: str):
    st.session_state["module"] = module_name


def header(title: str):
    """Professional top header. Navigation uses Streamlit buttons so module click does NOT logout."""
    username = st.session_state.get("username", "")
    role = st.session_state.get("role", "")
    active = st.session_state.get("module", "Cost Sheet")

    display_title = "Costing"
    st.markdown(f"""
<div class='rbm-topbar'>
  <div><div class='rbm-logo'>RBM AI</div><div class='rbm-sub'>Robotic Business Management</div></div>
  <div class='rbm-title'>{display_title}</div>
  <div></div>
  <div class='rbm-actions'>
    <a class='sync'>☁ Sync Now</a>
    <a class='on'>⊙ ON</a>
    <div class='userbox'>User: {username} | Role: {role}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    nav_items = []
    if has_perm("can_cost_sheet"):
        nav_items.append(("Cost Sheet", "Cost Sheet"))
    if has_perm("can_cost_local"):
        nav_items.append(("Cost - Local", "Cost - Local"))
    if has_perm("can_cost_export"):
        nav_items.append(("Cost - Export", "Cost - Export"))
    if has_perm("can_add_sort"):
        nav_items.append(("Add Sort", "Add Sort"))
        nav_items.append(("RM Price", "RM Price"))
    if is_developer():
        nav_items.append(("Users", "Users"))

    # Button navigation does not clear session and does not reload/login.
    st.markdown("<div class='navrow'>", unsafe_allow_html=True)
    cols = st.columns([1,1,1,1,1,1,0.05,0.05,0.05])
    for i, (label, module) in enumerate(nav_items):
        with cols[i]:
            if st.button(label, key=f"nav_{module}", type=("primary" if active == module else "secondary")):
                st.session_state["module"] = module
                st.rerun()
    with cols[-1]:
        if st.button("Logout", key="nav_logout"):
            st.session_state.clear()
            try:
                st.query_params.clear()
            except Exception:
                pass
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def login_page():
    st.markdown("""
<div class='rbm-topbar' style='grid-template-columns:145px 260px 1fr 120px;'>
  <div><div class='rbm-logo'>RBM AI</div><div class='rbm-sub'>Robotic Business Management</div></div>
  <div class='rbm-title'>Costing</div>
  <div></div><div></div>
</div>
""", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.1, 1])
    with c2:
        st.markdown("### Secure Client Login")
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", value=st.session_state.get("login_username", "admin"), key="login_username_input", placeholder="Enter username")
            password = st.text_input("Password", value="", type="password", key="login_password_input", placeholder="Enter password")
            submitted = st.form_submit_button("Login", type="primary")
        if submitted:
            try:
                rows = sb_select(TABLE_USERS, {"username": f"eq.{username.strip()}", "select": "*", "limit": "1"})
                user = rows[0] if rows else None
                ok = False
                if user:
                    stored = str(user.get("password") or "")
                    ok = stored == password or stored == hash_password(password)
                if ok:
                    st.session_state["username"] = username.strip()
                    st.session_state["role"] = user.get("role", "User")
                    st.session_state["perms"] = {k: bool(user.get(k)) for k, _ in PERMISSIONS}
                    st.session_state["module"] = "Cost Sheet" if bool(user.get("can_cost_sheet")) or user.get("role") == "Developer" else "Cost - Local"
                    audit("LOGIN", "", username.strip())
                    st.rerun()
                else:
                    st.error("Wrong username or password.")
            except Exception as e:
                st.error(str(e))


def pick_sort(default: str = "") -> str:
    rows = list_sort_numbers()
    if not default:
        default = first_sort()
    # One compact combo-style selector: type is allowed and list is available.
    idx = rows.index(default) if default in rows else 0
    selected = st.selectbox("Sort No (Excel D1):", options=rows if rows else [default], index=idx if rows else 0, key="sort_pick")
    typed = st.text_input("", value=selected or default, key="sort_typed", label_visibility="collapsed")
    return (typed.strip() or selected or "").strip()

def report_metrics(calc: Dict[str, Any]):
    st.markdown(f"""
<div class='report-head'><span>RBM TEXTILE COST SHEET</span><span style='color:#ffe92e'>SORT NO: {calc['sort_no']}</span></div>
<div class='metric-row'>
  <div class='metric bg-teal'><small>Structure</small><b>{calc['structure']}</b></div>
  <div class='metric bg-blue'><small>Finish GSM</small><b>{calc['finish_gsm']}</b></div>
  <div class='metric bg-gold'><small>Finish Width</small><b>{calc['finish_width']}</b></div>
  <div class='metric bg-green'><small>Selling Price</small><b>{calc['sales_price']}</b></div>
  <div class='metric bg-red'><small>USD/KG</small><b>{calc['usd_kg']}</b></div>
</div>
""", unsafe_allow_html=True)


def detailed_cost_rows(row: Dict[str, Any], what_if: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Excel-style textile costing calculation.
    Formula is kept close to the desktop sheet:
    dyed yarn = cotton yarn + cotton wastage + dyeing
    cotton dyed proportion = dyed yarn * cotton composition %
    raw material = cotton dyed proportion + polyester + spandex + kora
    costing = raw material + knitting + wastage after knitting
    selling = costing + margin - discount.
    """
    what_if = what_if or {}
    cotton = clean_num(row.get("cotton_yarn_cost", row.get("cotton_cost", row.get("cotton_yarn", 225))), 225)
    waste_pct = clean_num(what_if.get("wastage_pct", row.get("wastage_pct", 6.75)), 6.75)
    dyeing = clean_num(what_if.get("dyeing_cost", row.get("dyeing_cost", row.get("dying_cost", 110))), 110)

    # composition percentage defaults follow existing textile sheet style: Cotton 96 + Spandex 4
    cotton_pct = clean_num(row.get("cotton_pct", row.get("cotton", 96)), 96)
    polyester_pct = clean_num(row.get("poly_pct", row.get("poly", 0)), 0)
    tencel_pct = clean_num(row.get("tencel_pct", row.get("tencel", 0)), 0)
    spandex_pct = clean_num(row.get("spandex_pct", row.get("spandex", 4)), 4)

    dyed_yarn = cotton + (cotton * waste_pct / 100) + dyeing
    cotton_prop = dyed_yarn * cotton_pct / 100
    polyester = clean_num(row.get("polyester_cost"), 0)
    tencel = clean_num(row.get("tencel_cost"), 0)
    # If spandex cost not stored, use desktop default value for 4% spandex.
    spandex_cost = clean_num(row.get("spandex_cost"), 13.40 if spandex_pct else 0)
    kora = clean_num(row.get("kora_yarn_cost"), 0)
    raw_material = cotton_prop + polyester + tencel + spandex_cost + kora

    knit = clean_num(what_if.get("knit", row.get("knitting_processing_cost", 90)), 90)
    knit_waste_pct = clean_num(what_if.get("knit_waste_pct", row.get("knit_waste_pct", 10)), 10)
    waste_after_cost = (raw_material + knit) * knit_waste_pct / 100
    costing = raw_material + knit + waste_after_cost
    margin_pct = clean_num(what_if.get("margin", row.get("margin_pct", 10)), 10)
    margin_value = costing * margin_pct / 100
    discount_pct = clean_num(what_if.get("discount", 0), 0)
    selling_before_discount = costing + margin_value
    selling = max(0, selling_before_discount - (selling_before_discount * discount_pct / 100))
    return {
        "cotton": cotton, "waste_pct": waste_pct, "dyeing": dyeing, "dyed_yarn": dyed_yarn,
        "cotton_prop": cotton_prop, "polyester": polyester, "tencel": tencel,
        "spandex": spandex_cost, "kora": kora, "raw_material": raw_material,
        "knit": knit, "knit_waste_pct": knit_waste_pct,
        "waste_after_cost": waste_after_cost, "costing": costing,
        "margin_value": margin_value, "selling": selling, "margin_pct": margin_pct,
        "cotton_pct": cotton_pct, "polyester_pct": polyester_pct, "tencel_pct": tencel_pct,
        "spandex_pct": spandex_pct, "discount_pct": discount_pct,
    }

def fmt2(v: Any) -> str:
    return fmt(v, 2)


def cost_sheet_page():
    header("Professional Cost Sheet Report")
    rows = list_sort_numbers()
    default_sort = st.session_state.get("last_sort", first_sort())

    # Desktop-like control strip directly below top header.
    c0, c1, c2, c3, c4, c5 = st.columns([1.25, 2.15, .85, 1.15, 1.25, 4.2])
    with c0:
        st.markdown("<div style='font-weight:900;padding-top:7px'>Sort No (Excel D1):</div>", unsafe_allow_html=True)
    with c1:
        idx = rows.index(default_sort) if default_sort in rows else 0
        selected = st.selectbox("Sort No", options=rows if rows else [default_sort], index=idx if rows else 0, label_visibility="collapsed", key="cost_sort_select")
    with c2:
        if st.button("Refresh", type="primary", key="refresh_cost"):
            clear_cache(); st.rerun()
    with c3:
        st.button("Print Preview", key="print_preview")
    with c4:
        st.button("Export This Sort", key="export_sort")
    with c5:
        st.markdown("<div class='fast-mode'>Fast mode: Cost sheet loads selected sort only</div>", unsafe_allow_html=True)

    sort_no = selected
    st.session_state["last_sort"] = sort_no
    row = get_sort(sort_no) if sort_no else None
    if not row:
        st.error("No details found for selected Sort No.")
        return

    base = detailed_cost_rows(row)
    currency_default = clean_num(row.get("currency_rate"), 87)
    calc = {
        "sort_no": row.get("sort_no"),
        "structure": row.get("structure"),
        "finish_gsm": fmt(row.get("finish_gsm"), 0),
        "finish_width": fmt(row.get("finish_width"), 0),
        "sales_price": fmt(clean_num(row.get("sales_price"), base["selling"])),
        "usd_kg": fmt(clean_num(row.get("usd_kg"), clean_num(row.get("sales_price"), base["selling"]) / currency_default if currency_default else 0)),
    }

    st.markdown("<div class='report'>", unsafe_allow_html=True)
    report_metrics(calc)
    st.markdown("<div class='whatbox'><div class='what-title'>What-If Analysis</div>", unsafe_allow_html=True)

    w1,w2,w3,w4,w5,w6,w7,w8,w9 = st.columns([1,1,1,1,1,1,1,1,1])
    with w1: waste_pct = st.number_input("Waste %", value=float(base['waste_pct']), step=0.25, key="wi_waste", format="%.2f")
    with w2: dyeing = st.number_input("Dyeing Cost Rs.", value=float(base['dyeing']), step=1.0, key="wi_dye", format="%.2f")
    with w3: knit_waste_pct = st.number_input("Knit Waste %", value=float(base['knit_waste_pct']), step=0.25, key="wi_kwaste", format="%.2f")
    with w4: discount = st.number_input("Discount %", value=0.0, step=1.0, key="wi_disc", format="%.2f")
    with w5: currency_rate = st.number_input("Currency Rate", value=float(currency_default), step=1.0, key="wi_curr", format="%.2f")
    with w6: freight = st.number_input("Freight INR/KG", value=15.0, step=1.0, key="wi_freight", format="%.2f")
    with w7: commission = st.number_input("Commission %", value=5.0, step=1.0, key="wi_comm", format="%.2f")
    with w8: lc_days = st.number_input("LC Days / Interest", value=0.0, step=1.0, key="wi_lc", format="%.2f")
    with w9: margin_pct = st.number_input("Margin %", value=float(base['margin_pct']), step=1.0, key="wi_margin", format="%.2f")

    cc1,cc2,cc3,cc4 = st.columns([1.4,1,1.2,7])
    with cc1:
        country = st.selectbox("Country", ["Bangladesh", "Vietnam", "Sri Lanka", "Japan", "Colombia", "Nagpur", "Istanbul"], key="wi_country")
    with cc2:
        st.button("Apply", type="primary", key="wi_apply")
    with cc3:
        st.button("Freight Master", key="freight_master")
    st.markdown("</div>", unsafe_allow_html=True)

    d = detailed_cost_rows(row, {
        "wastage_pct": waste_pct, "dyeing_cost": dyeing,
        "knit_waste_pct": knit_waste_pct, "margin": margin_pct,
        "knit": base['knit'], "discount": discount,
    })
    # Desktop/SPECS values uploaded in Supabase are source of truth for normal view.
    # This prevents Streamlit from showing a different calculation than the desktop app.
    DEFAULT_WASTE = 6.75
    DEFAULT_DYE = 110.0
    DEFAULT_KNIT = 90.0
    DEFAULT_KNIT_WASTE = 10.0
    DEFAULT_MARGIN = 10.0
    DEFAULT_CURR = 87.0
    DEFAULT_FREIGHT = 15.0
    DEFAULT_COMM = 5.0
    DEFAULT_LC = 0.0
    defaults_unchanged = (
        abs(waste_pct - DEFAULT_WASTE) < 1e-9 and
        abs(dyeing - DEFAULT_DYE) < 1e-9 and
        abs(knit_waste_pct - DEFAULT_KNIT_WASTE) < 1e-9 and
        abs(margin_pct - DEFAULT_MARGIN) < 1e-9 and
        abs(discount) < 1e-9 and
        abs(currency_rate - DEFAULT_CURR) < 1e-9 and
        abs(freight - DEFAULT_FREIGHT) < 1e-9 and
        abs(commission - DEFAULT_COMM) < 1e-9 and
        abs(lc_days - DEFAULT_LC) < 1e-9
    )
    saved_local = clean_num(row.get("local_cost"), d['costing'])
    saved_sales = clean_num(row.get("sales_price"), d['selling'])
    if defaults_unchanged:
        # Back-solve raw material and margin from desktop stored totals, so totals match desktop exactly.
        d['costing'] = saved_local
        d['selling'] = saved_sales
        d['margin_value'] = max(0, saved_sales - saved_local)
        d['raw_material'] = (saved_local / (1 + DEFAULT_KNIT_WASTE/100.0)) - DEFAULT_KNIT
        d['waste_after_cost'] = saved_local - d['raw_material'] - DEFAULT_KNIT
        # Keep row-level components if present; otherwise balance goes to cotton dyed proportion.
        known = clean_num(d.get('polyester')) + clean_num(d.get('tencel')) + clean_num(d.get('spandex')) + clean_num(d.get('kora'))
        d['cotton_prop'] = max(0, d['raw_material'] - known)
    selling = d['selling']
    price_usd_kg = clean_num(row.get("usd_kg"), selling / currency_rate if currency_rate else 0) if defaults_unchanged else (selling / currency_rate if currency_rate else 0)
    commission_amt = selling * commission / 100
    lc_interest = clean_num(lc_days, 0)
    total_inr = clean_num(row.get("total_cost_inr_kg", row.get("total_cost_inr")), selling + freight + commission_amt + lc_interest) if defaults_unchanged else (selling + freight + commission_amt + lc_interest)
    total_usd = clean_num(row.get("total_cost_usd_kg", row.get("total_cost_usd")), total_inr / currency_rate if currency_rate else 0) if defaults_unchanged else (total_inr / currency_rate if currency_rate else 0)

    # Refresh metric cards after what-if values.
    calc2 = dict(calc)
    calc2["sales_price"] = fmt(selling)
    calc2["usd_kg"] = fmt(price_usd_kg)
    # show cards again is avoided to keep compact; values above use base, tables use applied what-if.

    left, right = st.columns(2)
    with left:
        st.markdown("""
<div class='table-box'><table><tr><th colspan='2'>▮ Cost Build-up</th></tr>
""" + f"""
<tr><td>Cotton Yarn Costing</td><td>{fmt2(d['cotton'])}</td></tr>
<tr class='green-row'><td>Wastage %</td><td>{fmt2(d['waste_pct'])}</td></tr>
<tr class='green-row'><td>Dyeing Cost Rs.</td><td>{fmt2(d['dyeing'])}</td></tr>
<tr><td>Dyed Yarn Cost Rs.</td><td>{fmt2(d['dyed_yarn'])}</td></tr>
<tr><td>Cotton Dyed Proportion Cost</td><td>{fmt2(d['cotton_prop'])}</td></tr>
<tr><td>Polyester Cost</td><td>{fmt2(d['polyester'])}</td></tr>
<tr><td>Spandex Cost</td><td>{fmt2(d['spandex'])}</td></tr>
<tr><td>Kora Yarn Cost</td><td>{fmt2(d['kora'])}</td></tr>
<tr class='yellow-row'><td>Raw Material Cost</td><td>{fmt2(d['raw_material'])}</td></tr>
<tr class='green-row'><td>Knitting + Processing Cost</td><td>{fmt2(d['knit'])}</td></tr>
<tr class='green-row'><td>Wastage % After Knitting</td><td>{fmt2(d['knit_waste_pct'])}</td></tr>
<tr><td>Wastage After Knitting Cost</td><td>{fmt2(d['waste_after_cost'])}</td></tr>
<tr class='yellow-row'><td>Costing</td><td>{fmt2(d['costing'])}</td></tr>
<tr class='green-row'><td>Margin</td><td>{fmt2(d['margin_value'])}</td></tr>
<tr class='yellow-row'><td>Selling Price</td><td>{fmt2(selling)}</td></tr>
</table></div>
""", unsafe_allow_html=True)
    with right:
        st.markdown("""
<div class='table-box'><table><tr><th colspan='2'>▣ Export / Price Calculation</th></tr>
""" + f"""
<tr class='green-row'><td>Currency Rate</td><td>{fmt2(currency_rate)}</td></tr>
<tr class='red-row'><td>Discount If Any</td><td>{fmt2(discount)}</td></tr>
<tr class='yellow-row'><td>Price USD/KG</td><td>{fmt2(price_usd_kg)}</td></tr>
<tr><td>Price USD/Mtrs</td><td>{fmt2(price_usd_kg / max(clean_num(row.get('linear_mtrs_kg', 1.70), 1.70), 0.0001))}</td></tr>
<tr><td>Price USD/Yds</td><td>{fmt2(price_usd_kg / max(clean_num(row.get('linear_yds_kg', 1.85), 1.85), 0.0001))}</td></tr>
<tr><td>Linear Mtrs/Kg</td><td>{fmt2(row.get('linear_mtrs_kg', 1.70))}</td></tr>
<tr><td>Linear Yds/Kg</td><td>{fmt2(row.get('linear_yds_kg', 1.85))}</td></tr>
<tr><td>Width CMS</td><td>{calc['finish_width']}</td></tr>
<tr><td>Width Inch</td><td>{fmt2(clean_num(row.get('finish_width'))/2.54 if clean_num(row.get('finish_width')) else 0)}</td></tr>
<tr><td>Weight GSM</td><td>{calc['finish_gsm']}</td></tr>
<tr><td>Price Per KG INR</td><td>{fmt2(selling)}</td></tr>
<tr class='green-row'><td>Freight INR/KG</td><td>{fmt2(freight)}</td></tr>
<tr class='green-row'><td>Commission %</td><td>{fmt2(commission)}</td></tr>
<tr><td>Commission Amount</td><td>{fmt2(commission_amt)}</td></tr>
<tr class='green-row'><td>LC Days / Interest</td><td>{fmt2(lc_interest)}</td></tr>
<tr class='yellow-row'><td>Total Cost INR/KG</td><td>{fmt2(total_inr)}</td></tr>
<tr class='yellow-row'><td>Total Cost USD/KG</td><td>{fmt2(total_usd)}</td></tr>
</table></div>
""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def vertical_report(title: str, items: List[tuple]):
    header(title)
    sort_no = pick_sort(st.session_state.get("last_sort", first_sort()))
    st.session_state["last_sort"] = sort_no
    row = get_sort(sort_no) if sort_no else None
    if not row:
        st.error("No details found.")
        return
    calc = compute_cost(row)
    st.markdown("<div class='report'>", unsafe_allow_html=True)
    st.markdown(f"<div class='report-head'><span>{title.upper()}</span><span>RBM Textile Costing</span></div>", unsafe_allow_html=True)
    html = "<div class='table-box vertical-table'><table>"
    for label, key in items:
        val = calc.get(key, "-")
        cls = ""
        if label in ["Price", "Local Cost", "Sales Price", "Total Cost USD/KG"]:
            cls = " class='yellow-row'"
        html += f"<tr{cls}><th>{label}</th><td><b>{val}</b></td></tr>"
    html += "</table></div>"
    st.markdown(html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def sort_form_page(mode="Add"):
    title = "Add Sort" if mode == "Add" else "Edit Sort"
    header(title)
    row = {}
    sort_no_fixed = ""
    if mode == "Edit":
        sort_no_fixed = st.session_state.get("edit_sort_no") or st.session_state.get("last_sort", first_sort())
        row = get_sort(sort_no_fixed) or {}

    st.markdown("<div class='section-head'>Add / Edit Sort Master</div>", unsafe_allow_html=True)
    st.markdown("<div class='report'>", unsafe_allow_html=True)
    with st.form("sort_form", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            sort_no = st.text_input("Sort No", value=str(row.get("sort_no", "")), disabled=(mode == "Edit"))
            structure = st.text_input("Structure", value=str(row.get("structure", "")))
        with c2:
            finish_gsm = st.number_input("Finish GSM", value=float(clean_num(row.get("finish_gsm"), 0.0)), step=1.0, format="%.2f")
            finish_width = st.number_input("Finish Width", value=float(clean_num(row.get("finish_width"), 0.0)), step=1.0, format="%.2f")
        with c3:
            local_cost = st.number_input("Local Cost", value=float(clean_num(row.get("local_cost"), 0.0)), step=1.0, format="%.2f")
            sales_price = st.number_input("Sales Price", value=float(clean_num(row.get("sales_price"), 0.0)), step=1.0, format="%.2f")

        c4, c5, c6, c7 = st.columns(4)
        with c4:
            currency_rate = st.number_input("Currency Rate", value=float(clean_num(row.get("currency_rate"), 87.0)), step=1.0, format="%.2f")
            usd_kg = st.number_input("USD/KG", value=float(clean_num(row.get("usd_kg"), 0.0)), step=0.10, format="%.2f")
        with c5:
            usd_mtrs = st.number_input("USD/Mtrs", value=float(clean_num(row.get("usd_mtrs"), 0.0)), step=0.10, format="%.2f")
            usd_yds = st.number_input("USD/Yds", value=float(clean_num(row.get("usd_yds"), 0.0)), step=0.10, format="%.2f")
        with c6:
            total_cost_inr_kg = st.number_input("Total Cost INR/KG", value=float(clean_num(row.get("total_cost_inr_kg", row.get("total_cost_inr")), 0.0)), step=1.0, format="%.2f")
            total_cost_usd_kg = st.number_input("Total Cost USD/KG", value=float(clean_num(row.get("total_cost_usd_kg", row.get("total_cost_usd")), 0.0)), step=0.10, format="%.2f")
        with c7:
            st.write("")
            st.write("")
            submitted = st.form_submit_button("Submit", type="primary")
    st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        if not str(sort_no).strip():
            st.error("Sort No required.")
            return
        payload = {
            "structure": structure.strip(), "finish_gsm": float(finish_gsm), "finish_width": float(finish_width),
            "local_cost": float(local_cost), "sales_price": float(sales_price), "currency_rate": float(currency_rate),
            "usd_kg": float(usd_kg), "usd_mtrs": float(usd_mtrs), "usd_yds": float(usd_yds),
            "total_cost_inr_kg": float(total_cost_inr_kg), "total_cost_usd_kg": float(total_cost_usd_kg),
        }
        try:
            if mode == "Add":
                payload.update({"sort_no": str(sort_no).strip(), "created_by": st.session_state.get("username"), "created_at": now_text()})
                existing = sb_select(TABLE_SORT, {"sort_no": f"eq.{str(sort_no).strip()}", "select": "id", "limit": "1"})
                if existing:
                    st.error("This Sort No already exists. Use Edit Sort instead.")
                    return
                sb_insert(TABLE_SORT, payload)
                audit("ADD_SORT", "", str(payload))
                st.success("Sort added successfully.")
            else:
                sb_update(TABLE_SORT, {"sort_no": f"eq.{sort_no_fixed}"}, payload)
                audit("EDIT_SORT", str(row), str(payload))
                st.success("Sort updated successfully.")
        except Exception as e:
            st.error(str(e))

def rm_price_page():
    header("RM Price Master")
    rows = get_rm_rows()
    particulars_list = sorted({str(r.get("particulars")) for r in rows if r.get("particulars")})
    product_list = sorted({str(r.get("product")) for r in rows if r.get("product")})
    st.markdown("<div class='compact-card'>", unsafe_allow_html=True)
    with st.form("rm_form"):
        c1, c2, c3, c4 = st.columns([2,2,1,1])
        with c1:
            particulars_pick = st.selectbox("Particulars Dropdown", [""] + particulars_list)
            particulars_new = st.text_input("New / Selected Particulars", value=particulars_pick)
        with c2:
            product_pick = st.selectbox("Product/Yarn Dropdown", [""] + product_list)
            product_new = st.text_input("New / Selected Product", value=product_pick)
        with c3:
            price = st.number_input("Price", value=0.0, step=1.0)
        with c4:
            st.write("")
            save = st.form_submit_button("Save RM Price", type="primary")
    st.markdown("</div>", unsafe_allow_html=True)
    if save:
        try:
            existing = sb_select(TABLE_RM, {"particulars": f"eq.{particulars_new.strip()}", "product": f"eq.{product_new.strip()}", "select": "*", "limit": "1"})
            payload = {"particulars": particulars_new.strip(), "product": product_new.strip(), "price": price, "changed_by": st.session_state.get("username"), "changed_at": now_text()}
            if existing:
                sb_update(TABLE_RM, {"id": f"eq.{existing[0]['id']}"}, payload)
                audit("EDIT_RM_PRICE", str(existing[0]), str(payload))
            else:
                sb_insert(TABLE_RM, payload)
                audit("ADD_RM_PRICE", "", str(payload))
            st.success("RM Price saved.")
        except Exception as e:
            st.error(str(e))
    st.dataframe(rows, use_container_width=True, height=430)


def users_page():
    header("User Management")
    if not is_developer():
        st.error("Only Developer can manage users.")
        return
    with st.form("user_form"):
        c1, c2, c3 = st.columns(3)
        with c1: username = st.text_input("Username")
        with c2: password = st.text_input("Password", help="blank = keep old password for existing user")
        with c3: role = st.selectbox("Role", ["Admin", "User"], help="Developer role is hidden from client Admin/User creation.")
        cols = st.columns(6)
        perm_values = {}
        for i, (k, label) in enumerate(PERMISSIONS):
            with cols[i % 6]:
                perm_values[k] = st.checkbox(label)
        submitted = st.form_submit_button("Save User", type="primary")
    if submitted:
        try:
            payload = {"username": username.strip(), "password": password, "role": role}
            payload.update(perm_values)
            existing = sb_select(TABLE_USERS, {"username": f"eq.{username.strip()}", "select": "*", "limit": "1"})
            if existing:
                if not password:
                    payload.pop("password")
                sb_update(TABLE_USERS, {"username": f"eq.{username.strip()}"}, payload)
                audit("EDIT_USER", str(existing[0]), str(payload))
            else:
                if not password:
                    st.error("Password required for new user.")
                    return
                sb_insert(TABLE_USERS, payload)
                audit("ADD_USER", "", username.strip())
            st.success("User saved.")
        except Exception as e:
            st.error(str(e))
    users = sb_select(TABLE_USERS, {"select": "*", "order": "id.asc"})
    st.dataframe(users, use_container_width=True, height=300)


def delete_area():
    target = st.session_state.get("delete_confirm")
    if target:
        st.warning(f"Delete Sort No {target}?")
        c1, c2 = st.columns([1,5])
        with c1:
            if st.button("Confirm Delete"):
                try:
                    old = get_sort(target)
                    sb_delete(TABLE_SORT, {"sort_no": f"eq.{target}"})
                    audit("DELETE_SORT", str(old), "")
                    st.session_state.pop("delete_confirm", None)
                    st.success("Deleted.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        with c2:
            if st.button("Cancel Delete"):
                st.session_state.pop("delete_confirm", None)
                st.rerun()



def first_allowed_module() -> str:
    if has_perm("can_cost_sheet"):
        return "Cost Sheet"
    if has_perm("can_cost_local"):
        return "Cost - Local"
    if has_perm("can_cost_export"):
        return "Cost - Export"
    if has_perm("can_add_sort"):
        return "Add Sort"
    return "Home"

def module_allowed(module: str) -> bool:
    if is_developer():
        return True
    mapping = {
        "Cost Sheet": "can_cost_sheet",
        "Cost - Local": "can_cost_local",
        "Cost - Export": "can_cost_export",
        "Add Sort": "can_add_sort",
        "RM Price": "can_add_sort",
        "Edit Sort": "can_edit_sort",
    }
    # Users and Developer role options are never shown to Admin/User.
    if module == "Users":
        return False
    perm = mapping.get(module)
    return bool(perm and has_perm(perm))

# -----------------------------
# Main router
# -----------------------------
if str(st.query_params.get("logout", "")) == "1":
    st.session_state.clear()
    try:
        st.query_params.clear()
    except Exception:
        pass
    st.rerun()

if not st.session_state.get("username"):
    login_page()
else:
    module = st.session_state.get("module", "")
    if not module:
        module = first_allowed_module()
        st.session_state["module"] = module

    # Never logout on module click. If user opens a disallowed module URL, redirect to first allowed module.
    if not module_allowed(module):
        st.session_state["module"] = first_allowed_module()
        try:
            st.query_params["module"] = st.session_state["module"]
        except Exception:
            pass
        st.warning("You do not have permission for that module.")
        st.rerun()

    try:
        if module == "Cost Sheet":
            cost_sheet_page()
            delete_area()
        elif module == "Cost - Local":
            vertical_report("Cost - Local", [("Sort No", "sort_no"), ("Structure", "structure"), ("Finish GSM", "finish_gsm"), ("Finish Width", "finish_width"), ("Local Cost", "local_cost"), ("Sales Price", "sales_price")])
        elif module == "Cost - Export":
            vertical_report("Cost - Export", [("Sort No", "sort_no"), ("Structure", "structure"), ("Finish GSM", "finish_gsm"), ("Finish Width", "finish_width"), ("Price", "sales_price"), ("Currency Rate", "currency_rate"), ("USD/Kg", "usd_kg"), ("Price USD Mtrs", "usd_mtrs"), ("Price USD Yds", "usd_yds"), ("Total Cost INR/KG", "total_cost_inr_kg"), ("Total Cost USD/KG", "total_cost_usd_kg")])
        elif module == "Add Sort":
            sort_form_page("Add")
        elif module == "Edit Sort":
            sort_form_page("Edit")
        elif module == "RM Price":
            rm_price_page()
        elif module == "Users":
            users_page()
        else:
            header("RBM Textile Costing")
            st.info("No module permission available for this user.")
    except Exception as e:
        st.error(str(e))
