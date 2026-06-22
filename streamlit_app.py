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
# CSS - compact professional layout
# -----------------------------
st.markdown(
    """
<style>
[data-testid="stAppViewContainer"] {background:#eaf6fb;}
.block-container {padding-top:0.05rem; padding-left:0.45rem; padding-right:0.45rem; max-width:100%;}
[data-testid="stHeader"] {height:0rem; background:transparent;}
[data-testid="stToolbar"] {display:none;}
#MainMenu, footer {visibility:hidden;}
div[data-testid="stVerticalBlock"] {gap:0.35rem;}
.rbm-top {background:#0b4f73; color:white; padding:5px 10px; border-radius:7px 7px 0 0; display:flex; gap:12px; align-items:center; flex-wrap:wrap;}
.rbm-logo {font-size:28px; font-weight:900; line-height:24px;}
.rbm-sub {font-size:10px; font-weight:700;}
.rbm-title {background:#138b75; color:white; padding:7px 18px; font-size:22px; font-weight:900; min-width:250px; text-align:center;}
.rbm-user {margin-left:auto; font-size:13px; font-weight:700; text-align:right;}
.nav-wrap {background:#0b4f73; padding:0 8px 6px 8px; border-radius:0 0 7px 7px; margin-bottom:5px;}
.section-head {background:#138b75; color:white; font-size:23px; font-weight:900; padding:6px 10px; margin:0 0 6px 0;}
.report {background:white; border:1px solid #d3d3d3; padding:8px; border-radius:8px; box-shadow:0 2px 9px rgba(0,0,0,.12);}
.report-head {background:#0b4f73; color:white; padding:9px 14px; font-size:23px; font-weight:900; display:flex; justify-content:space-between; align-items:center;}
.metric-row {display:grid; grid-template-columns:repeat(5,1fr); gap:6px; margin:7px 0;}
.metric {color:white; padding:7px 10px; border-radius:3px; min-height:43px;}
.metric small{font-weight:800; display:block; font-size:11px;}
.metric b{font-size:19px; display:block;}
.bg-teal{background:#138b75}.bg-blue{background:#405ad9}.bg-gold{background:#9c6a00}.bg-green{background:#10a848}.bg-red{background:#b52e34}.bg-navy{background:#0b4f73}
.table-box table {width:100%; border-collapse:collapse; font-size:14px;}
.table-box th {background:#0b4f73; color:#fff; padding:8px; border:1px solid #111; text-align:left;}
.table-box td {padding:7px; border:1px solid #111; background:#f7fbff;}
.table-box tr:nth-child(even) td {background:#eaf2fb;}
.green-row td {background:#86ee9c !important; font-weight:700;}
.red-row td:first-child {background:#ff4c4c !important; color:#fff; font-weight:800;}
.red-row td:last-child {background:#ffc5c5 !important;}
.yellow-row td {background:#fff4bd !important; font-weight:700;}
.vertical-table th {width:35%;}
.compact-card {background:#e2ded8; padding:6px 8px; border-radius:7px; margin-bottom:6px;}
.stButton > button {font-weight:800; border-radius:7px; padding:0.35rem 0.8rem; min-height:34px;}
.stTextInput > div > div > input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div {min-height:32px;}
label[data-testid="stWidgetLabel"] p {font-weight:700; font-size:13px; margin-bottom:0px;}
@media(max-width:800px){.metric-row{grid-template-columns:1fr 1fr}.rbm-user{margin-left:0}.rbm-title{min-width:100%;}.report-head{font-size:18px}.rbm-logo{font-size:25px}}
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
    try:
        st.query_params["module"] = module_name
    except Exception:
        pass


def header(title: str):
    username = st.session_state.get("username", "")
    role = st.session_state.get("role", "")
    st.markdown(f"""
<div class='rbm-top'>
  <div><div class='rbm-logo'>RBM AI</div><div class='rbm-sub'>Robotic Business Management</div></div>
  <div class='rbm-title'>{title}</div>
  <div class='rbm-user'>{username} | {role}</div>
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

    st.markdown("<div class='nav-wrap'>", unsafe_allow_html=True)
    total = len(nav_items) + 1
    cols = st.columns([1] * len(nav_items) + [2]) if nav_items else st.columns([1])
    for i, (label, module_name) in enumerate(nav_items):
        with cols[i]:
            if st.button(label, key=f"nav_{module_name}"):
                set_module(module_name)
                st.rerun()
    with cols[-1]:
        if st.button("Logout", key="top_logout"):
            st.session_state.clear()
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def login_page():
    st.markdown("""
<div class='rbm-top'>
  <div><div class='rbm-logo'>RBM AI</div><div class='rbm-sub'>Robotic Business Management</div></div>
  <div class='rbm-title'>RBM Textile Costing</div>
</div>
""", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.1, 1])
    with c2:
        st.markdown("### Secure Client Login")
        with st.form("login_form"):
            username = st.text_input("Username", value="admin")
            password = st.text_input("Password", type="password")
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
    # Compact single-row selector: user can type or choose from dropdown.
    c1, c2 = st.columns([1.1, 2.8])
    with c1:
        typed = st.text_input("Sort No", value=default, key="sort_typed")
    with c2:
        idx = rows.index(default) if default in rows else 0
        selected = st.selectbox("Select from list", options=rows, index=idx if rows else None, key="sort_pick") if rows else ""
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


def cost_sheet_page():
    header("Professional Cost Sheet Report")
    sort_no = pick_sort(st.session_state.get("last_sort", first_sort()))
    st.session_state["last_sort"] = sort_no
    b1, b2, b3, b4 = st.columns([1,1,1,5])
    with b1:
        refresh = st.button("Refresh", type="primary")
    with b2:
        if has_perm("can_edit_sort") and st.button("Edit"):
            st.session_state["edit_sort_no"] = sort_no
            set_module("Edit Sort")
            st.rerun()
    with b3:
        if has_perm("can_delete_sort") and st.button("Delete"):
            st.session_state["delete_confirm"] = sort_no
    row = get_sort(sort_no) if sort_no else None
    if not row:
        st.error("No details found for selected Sort No.")
        return
    with st.container():
        st.markdown("<div class='report'>", unsafe_allow_html=True)
        calc = compute_cost(row)
        report_metrics(calc)
        st.markdown("<b>What-If Analysis</b>", unsafe_allow_html=True)
        w1, w2, w3, w4, w5, w6, w7 = st.columns(7)
        with w1: currency_rate = st.number_input("Currency", value=clean_num(row.get("currency_rate"), 87), step=1.0)
        with w2: discount = st.number_input("Discount", value=0.0, step=1.0)
        with w3: margin = st.number_input("Margin %", value=10.0, step=1.0)
        with w4: freight = st.number_input("Freight", value=0.0, step=1.0)
        with w5: commission = st.number_input("Commission", value=0.0, step=1.0)
        with w6: knit = st.number_input("Knit", value=0.0, step=1.0)
        with w7: wastage = st.number_input("Wastage", value=0.0, step=1.0)
        what_calc = compute_cost(row, {"currency_rate": currency_rate, "discount": discount, "margin": margin, "freight": freight, "commission": commission, "knit": knit, "wastage": wastage})
        left, right = st.columns(2)
        with left:
            st.markdown("""
<div class='table-box'><table><tr><th colspan='2'>Cost Build-up</th></tr>
""" + f"""
<tr><td>Local Cost</td><td>{calc['local_cost']}</td></tr>
<tr><td>Sales Price</td><td>{calc['sales_price']}</td></tr>
<tr class='green-row'><td>What-If Cost</td><td>{what_calc['what_if_cost']}</td></tr>
<tr class='green-row'><td>What-If Sales</td><td>{what_calc['what_if_sales']}</td></tr>
</table></div>
""", unsafe_allow_html=True)
        with right:
            st.markdown("""
<div class='table-box'><table><tr><th colspan='2'>Export / Price Calculation</th></tr>
""" + f"""
<tr class='green-row'><td>Currency Rate</td><td>{what_calc['currency_rate']}</td></tr>
<tr class='red-row'><td>Discount If Any</td><td>{fmt(discount)}</td></tr>
<tr><td>Price USD/KG</td><td>{calc['usd_kg']}</td></tr>
<tr><td>Price USD/Mtrs</td><td>{calc['usd_mtrs']}</td></tr>
<tr><td>Price USD/Yds</td><td>{calc['usd_yds']}</td></tr>
<tr><td>Total Cost INR/KG</td><td>{calc['total_cost_inr_kg']}</td></tr>
<tr><td>Total Cost USD/KG</td><td>{calc['total_cost_usd_kg']}</td></tr>
<tr class='yellow-row'><td>What-If USD/KG</td><td>{what_calc['what_if_usd']}</td></tr>
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
    with st.form("sort_form"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            sort_no = st.text_input("Sort No", value=str(row.get("sort_no", "")), disabled=(mode == "Edit"))
            structure = st.text_input("Structure", value=str(row.get("structure", "")))
        with c2:
            finish_gsm = st.number_input("Finish GSM", value=clean_num(row.get("finish_gsm")), step=1.0)
            finish_width = st.number_input("Finish Width", value=clean_num(row.get("finish_width")), step=1.0)
        with c3:
            local_cost = st.number_input("Local Cost", value=clean_num(row.get("local_cost")), step=1.0)
            sales_price = st.number_input("Sales Price", value=clean_num(row.get("sales_price")), step=1.0)
        with c4:
            currency_rate = st.number_input("Currency Rate", value=clean_num(row.get("currency_rate"), 87), step=1.0)
            usd_kg = st.number_input("USD/KG", value=clean_num(row.get("usd_kg")), step=0.1)
        c5, c6, c7, c8 = st.columns(4)
        with c5: usd_mtrs = st.number_input("USD/Mtrs", value=clean_num(row.get("usd_mtrs")), step=0.1)
        with c6: usd_yds = st.number_input("USD/Yds", value=clean_num(row.get("usd_yds")), step=0.1)
        with c7: total_cost_inr_kg = st.number_input("Total Cost INR/KG", value=clean_num(row.get("total_cost_inr_kg", row.get("total_cost_inr"))), step=1.0)
        with c8: total_cost_usd_kg = st.number_input("Total Cost USD/KG", value=clean_num(row.get("total_cost_usd_kg", row.get("total_cost_usd"))), step=0.1)
        submitted = st.form_submit_button("Save Sort", type="primary")
    if submitted:
        payload = {
            "structure": structure.strip(), "finish_gsm": finish_gsm, "finish_width": finish_width,
            "local_cost": local_cost, "sales_price": sales_price, "currency_rate": currency_rate,
            "usd_kg": usd_kg, "usd_mtrs": usd_mtrs, "usd_yds": usd_yds,
            "total_cost_inr_kg": total_cost_inr_kg, "total_cost_usd_kg": total_cost_usd_kg,
        }
        try:
            if mode == "Add":
                payload.update({"sort_no": sort_no.strip(), "created_by": st.session_state.get("username"), "created_at": now_text()})
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
        with c3: role = st.selectbox("Role", ["Admin", "User", "Developer"])
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


# -----------------------------
# Main router
# -----------------------------
if not st.session_state.get("username"):
    login_page()
else:
    module = st.session_state.get("module") or st.query_params.get("module", "")
    if not module:
        if has_perm("can_cost_sheet"):
            module = "Cost Sheet"
        elif has_perm("can_cost_local"):
            module = "Cost - Local"
        elif has_perm("can_cost_export"):
            module = "Cost - Export"
        else:
            module = "Home"
        st.session_state["module"] = module

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
