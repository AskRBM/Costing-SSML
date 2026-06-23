from __future__ import annotations

import html
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List
from io import BytesIO
import os, json, urllib.request, urllib.parse, urllib.error

import pandas as pd
import streamlit as st

st.set_page_config(page_title="RBM Textile Costing", page_icon="🧵", layout="wide", initial_sidebar_state="collapsed")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
GROUP_CSV = DATA_DIR / "group_costing.csv"
RM_CSV = DATA_DIR / "rm_price_master.csv"
USERS_CSV = DATA_DIR / "users_default.csv"
APP_VERSION = "2026-06-23-online-supabase-specs-force-v7-sort-normalized-live"

# Online app now reads live synced data from Supabase first.
# IMPORTANT: Put these same values in Streamlit Cloud Secrets also.
# This code also has a publishable-key fallback so online data loads even when GitHub CSV is old.
def _secret_or_env(*names: str, default: str = "") -> str:
    for name in names:
        try:
            v = st.secrets.get(name, None)
            if v is not None and str(v).strip():
                return str(v).strip()
        except Exception:
            pass
        try:
            v = os.environ.get(name, "")
            if str(v).strip():
                return str(v).strip()
        except Exception:
            pass
    return default

ONLINE_SUPABASE_URL = _secret_or_env(
    "RBM_SUPABASE_URL", "SUPABASE_URL", "supabase_url",
    default="https://mmzvwlitakluttlnnioh.supabase.co"
).strip().rstrip("/")

# Use publishable/anon key for Streamlit online read. Do NOT use service-role key in public GitHub.
ONLINE_SUPABASE_KEY = _secret_or_env(
    "RBM_SUPABASE_KEY", "SUPABASE_KEY", "SUPABASE_ANON_KEY", "supabase_key",
    default="sb_publishable_OcHaa48FL57wRoRohD6IsQ_7pCJd6LB"
).strip()

MODULES = ["Cost Sheet", "Cost - Local", "Cost - Export", "Add Sort", "RM Price", "Users"]
PERM = {
    "Cost Sheet":"can_cost_sheet",
    "Cost - Local":"can_cost_local",
    "Cost - Export":"can_cost_export",
    "Add Sort":"can_add_sort",
    "RM Price":"can_rm_price",
    "Users":"can_users",
}

st.markdown("""
<style>
:root{--blue:#0b4f73;--green:#0f8d75;--red:#e52525;--bg:#eaf6fb;--line:#222;}
[data-testid="stAppViewContainer"]{background:var(--bg);} 
.block-container{padding:0.08rem 0.28rem 0.25rem 0.28rem; max-width:100%;}
[data-testid="stHeader"], [data-testid="stToolbar"]{display:none!important; height:0!important;}
#MainMenu, footer{visibility:hidden;} div[data-testid="stVerticalBlock"]{gap:0.15rem;}
.rbm-top{background:#0b4f73;color:#fff;height:54px;display:flex;align-items:center;gap:8px;padding:0 10px;border-bottom:2px solid #d6eef8;overflow:hidden;}
.logo{width:145px;min-width:145px}.logo .big{font-size:26px;font-weight:900;line-height:24px}.logo .sub{font-size:8px;font-weight:800;}
.titlebox{background:#108d76;height:54px;width:250px;display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:900;border-bottom:4px solid #d3f5ee;}
.top-kpi-row{display:flex;gap:3px;align-items:center;flex:1;min-width:0;overflow:hidden;}
.top-kpi{height:24px;color:white;font-weight:900;display:flex;align-items:center;padding:0 6px;font-size:10px;white-space:nowrap;border-radius:2px;min-width:auto;width:auto;}
.top-kpi b{margin-right:6px}.top-sort{margin-left:auto;color:#fff200;font-size:14px;font-weight:900;white-space:nowrap;padding-left:6px;}
.nav{display:flex;gap:6px;align-items:center;flex-wrap:nowrap;flex:1;justify-content:center;}
a.navbtn{text-decoration:none;background:#fff;color:#001b34;border:1px solid #b8cee8;border-radius:5px;padding:9px 15px;font-size:14px;font-weight:900;white-space:nowrap;box-shadow:0 1px 2px rgba(0,0,0,.15)}
a.navbtn.active{background:#166fe5;color:white;border-color:#166fe5;}
.top-actions{display:flex;gap:5px;align-items:center;white-space:nowrap;}
.sync,.on,.logout{border-radius:4px;padding:7px 9px;color:#fff;font-weight:900;font-size:11px}.sync{background:#0ab052}.on{background:#087e20}.logout{background:#d81919;text-decoration:none}
.userbox{text-align:right;font-size:11px;font-weight:900;min-width:145px;}
.db-title{color:white;font-size:14px;font-weight:900;white-space:nowrap;margin-left:6px;}
.login-hero{max-width:520px;margin:42px auto 0 auto;background:linear-gradient(135deg,#073e61,#0b5a80);border-radius:16px 16px 0 0;padding:22px 28px 18px 28px;color:#fff;text-align:center;box-shadow:0 10px 28px rgba(0,0,0,.20)}
.login-hero .login-title{font-size:28px;font-weight:950;letter-spacing:.2px;margin-bottom:7px}.login-hero .login-sub{font-size:14px;font-weight:850;color:#d9f7ff}.login-badge{display:inline-block;margin-top:10px;background:#108d76;color:#fff;border-radius:30px;padding:6px 18px;font-size:12px;font-weight:900}
.login-wrap{max-width:520px;margin:0 auto 0 auto;border:1px solid #a8c7dc;border-top:0;border-radius:0 0 16px 16px;padding:24px 28px 26px 28px;background:#ffffff;box-shadow:0 12px 30px rgba(0,0,0,.16)}
.login-wrap label{font-size:13px!important;font-weight:900!important;color:#06334d!important}.login-wrap input{height:42px!important;border-radius:8px!important;border:1px solid #bdd4e4!important;background:#f7fbff!important;font-size:14px!important}.login-wrap .stButton button,.login-wrap .stFormSubmitButton button{height:42px!important;width:100%!important;border-radius:8px!important;font-size:14px!important;font-weight:950!important;background:#ff4d4d!important;border-color:#ff4d4d!important;color:white!important}.login-note{text-align:center;color:#526b7c;font-size:12px;font-weight:700;margin-top:12px}
.control-strip{background:#dedbd5;padding:5px 10px;display:flex;align-items:center;gap:8px;white-space:nowrap;}
.fast{margin-left:18px;color:#008000;font-weight:900;font-size:12px}.label{font-weight:900}.small-note{font-size:11px;color:#095;}
.card-row{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin:2px 0 0 0}.kpi{height:27px;color:white;font-weight:900;display:flex;align-items:center;padding:0 9px;font-size:12px;}
.kpi b{margin-right:14px}.k1{background:#0f8d75}.k2{background:#3159d8}.k3{background:#9a6500}.k4{background:#09a441}.k5{background:#b82e35}
.sheet-head{background:#0b4f73;color:#fff;height:37px;display:flex;align-items:center;padding:0 10px;font-size:17px;font-weight:900;margin-top:3px}.sheet-head .sort{margin-left:auto;color:#fff200;font-size:18px;}
.whatif{border:1px solid #a7b7c6;background:#f7fbff;padding:4px 8px;margin:0 0 2px 0}.whatif-title{font-size:13px;font-weight:900;color:#01223a;margin-bottom:4px}.country-inline-label{font-weight:800;color:#001b34;font-size:12px;padding-top:7px;white-space:nowrap}
.table-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:3px}.tblbox{border:1px solid #b2c1cf;background:white}.tbltitle{background:#0b4f73;color:#fff;font-weight:900;padding:3px 8px;font-size:13px;display:flex;align-items:center;gap:5px;min-height:32px;overflow:hidden}.tbltitle-main{white-space:nowrap;margin-right:6px}.tbl-kpis{display:flex;align-items:center;gap:4px;flex-wrap:nowrap;min-width:0;overflow:hidden}.tbl-kpi{height:23px;color:#fff;font-weight:900;display:flex;align-items:center;justify-content:center;padding:0 6px;font-size:9px;white-space:nowrap;border-radius:3px;line-height:1.05}.tbl-kpi b{margin-right:4px}.rbmtable{width:100%;border-collapse:collapse;font-size:12px;font-weight:700}.rbmtable td{border:1px solid #333;padding:4px 7px}.rbmtable td:nth-child(2){font-weight:700}.row-green td{background:#91f0a0}.row-red td:first-child{background:#ff5555;color:white}.row-red td:nth-child(2){background:#ffc7c7}.row-yellow td{background:#fff3b5}.row-blue td{background:#eef6ff}.footer{position:fixed;bottom:0;left:0;right:0;background:#0b4f73;color:#fff;padding:8px 20px;font-size:13px;font-weight:800;display:flex;justify-content:space-between;z-index:10}.footer b{color:#ffe600}.content-pad{padding-bottom:28px}
.stButton button{height:26px!important;min-height:26px!important;padding:0 5px!important;font-weight:800;border-radius:4px;margin:0!important;white-space:nowrap!important;font-size:10px!important;line-height:1!important}
.stFormSubmitButton button{height:26px!important;min-height:26px!important;padding:0 5px!important;font-weight:800!important;border-radius:4px!important;margin:0!important;white-space:nowrap!important;font-size:10px!important;line-height:1!important}.stSelectbox label,.stNumberInput label,.stTextInput label{font-weight:800;color:#001b34;font-size:12px!important}.stSelectbox div,.stTextInput input,.stNumberInput input{font-size:13px!important}.stNumberInput button{height:32px!important;min-height:32px!important}.warn{background:#fde9ed;color:#9b1230;padding:10px;border-radius:6px;margin:10px 0}.ok{background:#e8fff0;color:#006a24;padding:10px;border-radius:6px;margin:10px 0}
.stButton button[kind="primary"]{background:#ff4d4d!important;border-color:#ff4d4d!important;color:white!important}

.one-line-bar{display:flex;align-items:center;gap:6px;margin:4px 0 5px 0;white-space:nowrap;}
.mini-kpi{height:29px;color:white;font-weight:900;display:flex;align-items:center;justify-content:center;padding:0 7px;font-size:10px;white-space:nowrap;border-radius:4px;line-height:1.05;text-align:center;}
.mini-kpi b{margin-right:5px;}
.top-sort-only{margin-left:auto;color:#fff200;font-size:14px;font-weight:900;white-space:nowrap;padding:0 10px;}
.nav-line-holder .stButton button{width:100%!important;min-width:max-content!important;padding:0 10px!important;}
.nav-line-holder [data-testid="column"]{width:auto!important;min-width:fit-content!important;flex:0 0 auto!important;}
.nav-line-holder{margin-top:2px!important;margin-bottom:2px!important;}
.control-one-line{border:1px solid #c5d6e3;border-radius:4px;background:#f7fbff;padding:6px 8px;margin:4px 0 6px 0;}
.country-inline-label{font-size:12px;font-weight:900;color:#001b34;padding-top:8px;}

@media(max-width:1000px){.rbm-top{height:auto;flex-wrap:wrap;padding:8px}.titlebox{width:220px;height:42px}.nav{justify-content:flex-start;overflow-x:auto}.card-row,.table-grid{grid-template-columns:1fr}.top-actions{flex-wrap:wrap}.footer{position:static}.control-strip{flex-wrap:wrap}a.navbtn{padding:8px 11px;font-size:13px}}
</style>
""", unsafe_allow_html=True)

# ---------- Supabase live data helpers ----------
def supabase_enabled() -> bool:
    return bool(ONLINE_SUPABASE_URL and ONLINE_SUPABASE_KEY)

def _sb_headers() -> Dict[str, str]:
    return {
        "apikey": ONLINE_SUPABASE_KEY,
        "Authorization": f"Bearer {ONLINE_SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

def _expand_json_data_column(df: pd.DataFrame) -> pd.DataFrame:
    """Some sync tables may store original row inside a data/json column.
    This expands that JSON so Sort No, STRUCTURE, GSM, WIDTH, etc. are available online.
    """
    if df.empty:
        return df
    if "data" not in df.columns:
        return df
    expanded=[]
    for _, row in df.iterrows():
        base=row.to_dict()
        d=base.get("data", {})
        if isinstance(d, str):
            try:
                d=json.loads(d)
            except Exception:
                d={}
        if isinstance(d, dict):
            for k,v in d.items():
                base[k]=v
        expanded.append(base)
    out=pd.DataFrame(expanded).fillna("")
    out.columns=[norm_col(c) for c in out.columns]
    return out

def supabase_table_df(table: str, limit: int = 100000) -> pd.DataFrame:
    """Always read fresh live synced Supabase table. No Streamlit cache here,
    because offline Sync Now must immediately reflect in online Sort No dropdown.
    """
    if not supabase_enabled():
        st.session_state[f"sb_error_{table}"] = "Supabase URL/key missing"
        return pd.DataFrame()
    try:
        url = f"{ONLINE_SUPABASE_URL}/rest/v1/{urllib.parse.quote(table)}?select=*&limit={int(limit)}"
        headers = _sb_headers()
        headers["Range-Unit"] = "items"
        headers["Range"] = f"0-{int(limit)-1}"
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
        data = json.loads(raw) if raw.strip() else []
        if not data:
            st.session_state[f"sb_error_{table}"] = "Supabase returned 0 rows"
            return pd.DataFrame()
        df = pd.DataFrame(data).fillna("")
        df.columns = [norm_col(c) for c in df.columns]
        df = _expand_json_data_column(df)
        st.session_state[f"sb_error_{table}"] = ""
        st.session_state[f"sb_count_{table}"] = len(df)
        return df
    except Exception as e:
        st.session_state[f"sb_error_{table}"] = str(e)
        return pd.DataFrame()

# ---------- data helpers ----------
def norm_col(c:str)->str:
    return str(c).strip().lower().replace("/", "_").replace(" ", "_").replace(".", "").replace("%", "pct").replace("-", "_").replace("__", "_")

@st.cache_data(show_spinner=False)
def read_csv(path_str: str) -> pd.DataFrame:
    p = Path(path_str)
    # Important: GitHub users sometimes upload CSV files in repository root instead of data/ folder.
    # This fallback prevents FileNotFoundError and keeps the app running.
    candidates = [p]
    if p.parent.name == "data":
        candidates.append(BASE_DIR / p.name)
    else:
        candidates.append(DATA_DIR / p.name)
    for cand in candidates:
        if cand.exists() and cand.stat().st_size > 0:
            df = pd.read_csv(cand, dtype=str).fillna("")
            df.columns = [norm_col(c) for c in df.columns]
            return df
    return pd.DataFrame()

def load_group() -> pd.DataFrame:
    # Live data priority: Supabase sync table, then GitHub CSV fallback.
    df_live = supabase_table_df("group_costing")
    if not df_live.empty:
        return df_live.copy()
    if "group_df" not in st.session_state:
        st.session_state.group_df = read_csv(str(GROUP_CSV))
    return st.session_state.group_df.copy()

def load_specs() -> pd.DataFrame:
    # SPECS is important because newly added sort numbers may exist here before group_costing.
    df_live = supabase_table_df("specs")
    if not df_live.empty:
        return df_live.copy()
    p = DATA_DIR / "specs.csv"
    return read_csv(str(p))

def save_group(df: pd.DataFrame):
    st.session_state.group_df = df.copy()

def load_rm() -> pd.DataFrame:
    df_live = supabase_table_df("rm_current")
    if not df_live.empty:
        return df_live.copy()
    if "rm_df" not in st.session_state:
        st.session_state.rm_df = read_csv(str(RM_CSV))
    return st.session_state.rm_df.copy()

def save_rm(df: pd.DataFrame):
    st.session_state.rm_df = df.copy()

def load_users() -> pd.DataFrame:
    # Live synced users from offline app. Falls back to GitHub users_default.csv.
    df_live = supabase_table_df("app_users")
    if not df_live.empty:
        # Offline app_users may also contain permission columns. If not, merge role_permissions.
        for c in ["can_cost_sheet","can_cost_local","can_cost_export","can_add_sort","can_rm_price","can_users"]:
            if c not in df_live.columns:
                df_live[c] = "False"
        if "is_active" in df_live.columns:
            df_live = df_live[df_live["is_active"].astype(str).str.lower().isin(["1","true","yes",""])]
        rp = supabase_table_df("role_permissions")
        if not rp.empty and {"username","module","can_access"}.issubset(set(rp.columns)):
            for idx, r in df_live.iterrows():
                uname = str(r.get("username","")).lower()
                uperms = rp[(rp["username"].astype(str).str.lower()==uname) & (rp["can_access"].astype(str).str.lower().isin(["1","true","yes"]))]
                for mod, key in PERM.items():
                    if mod in uperms["module"].astype(str).tolist():
                        df_live.loc[idx, key] = "True"
        return df_live.copy()
    if "users_df" not in st.session_state:
        df=read_csv(str(USERS_CSV))
        if df.empty:
            df=pd.DataFrame([{"username":"admin","password":"rbm123","role":"Developer","can_cost_sheet":"True","can_cost_local":"True","can_cost_export":"True","can_add_sort":"True","can_edit_sort":"True","can_delete_sort":"True","can_rm_price":"True","can_users":"True"}])
        st.session_state.users_df=df
    return st.session_state.users_df.copy()

def save_users(df: pd.DataFrame):
    st.session_state.users_df=df.copy()

def to_float(x:Any, default:float=0.0)->float:
    try:
        if x is None: return default
        s=str(x).replace(",","").strip()
        if s=="" or s.lower()=="nan" or s.lower()=="none": return default
        return float(s)
    except Exception:
        return default

def fmt(x:Any, dec:int=2)->str:
    try:
        s=str(x).strip()
        if s=="" or s.lower()=="nan" or s.lower()=="none": return ""
        f=float(str(x).replace(",", ""))
        if abs(f-round(f))<1e-9:
            return str(int(round(f)))
        return f"{f:.{dec}f}"
    except Exception:
        return str(x) if x is not None else ""

def getv(row:Dict[str,Any], *names, default=""):
    for n in names:
        key=norm_col(n)
        if key in row and str(row[key]).strip() not in ("", "nan", "None"):
            return row[key]
    return default

def group_sort_col(df:pd.DataFrame)->str:
    for c in ["dev_sorts","sort_no","sort"]:
        if c in df.columns: return c
    return df.columns[1] if len(df.columns)>1 else "dev_sorts"

def clean_sort_value(v: Any) -> str:
    """Normalize Sort No from Supabase/CSV.
    SQLite often sends 1202 as 1202.0. Online dropdown must show/search it as 1202.
    """
    try:
        s = str(v).strip()
        if s == "" or s.lower() in ("nan", "none", "null", "dev_sorts", "sort_no", "sort"):
            return ""
        if s.endswith(".0"):
            f = float(s)
            if abs(f - int(f)) < 1e-9:
                return str(int(f))
        return s
    except Exception:
        return str(v).strip() if v is not None else ""

def sort_key_value(x: str):
    sx = clean_sort_value(x)
    try:
        return (0, int(float(sx)))
    except Exception:
        return (1, sx)

def sort_options()->List[str]:
    # Force live Supabase SPECS first. This is required because new Sort No
    # added in Offline app is synced to Supabase specs table, not to GitHub CSV.
    vals=[]
    seen=set()
    for df in [load_specs(), load_group()]:
        if df.empty:
            continue
        possible=["dev_sorts","sort_no","sort","dev_sort","sorts","sr_no"]
        found_cols=[x for x in possible if x in df.columns and x != "sr_no"]
        if not found_cols:
            found_cols=[group_sort_col(df)]
        for c in found_cols:
            if c not in df.columns:
                continue
            for raw_v in df[c].tolist():
                v=clean_sort_value(raw_v)
                if v and v not in seen:
                    seen.add(v); vals.append(v)
    return sorted(vals, key=sort_key_value)

FREIGHT_MASTER = {
    "Bangladesh": 15.0,
    "Vietnam": 20.0,
    "Sri Lanka": 18.0,
    "Japan": 45.0,
    "USA": 55.0,
    "UAE": 35.0,
}

def freight_master_rows() -> List[tuple]:
    return [(country, rate) for country, rate in FREIGHT_MASTER.items()]

def get_sort_row(sort_no:str)->Dict[str,Any]:
    target=clean_sort_value(sort_no)
    df=load_group()
    if not df.empty:
        c=group_sort_col(df)
        if c in df.columns:
            m=df[df[c].apply(clean_sort_value)==target]
            if not m.empty:
                return m.iloc[0].to_dict()
    # Fallback: if the sort exists only in SPECS, still show it in online dropdown/pages.
    sdf=load_specs()
    if not sdf.empty:
        c=next((x for x in ["dev_sorts","sort_no","sort"] if x in sdf.columns), group_sort_col(sdf))
        if c in sdf.columns:
            m=sdf[sdf[c].apply(clean_sort_value)==target]
        else:
            m=pd.DataFrame()
        if not m.empty:
            r=m.iloc[0].to_dict()
            return {
                "dev_sorts": str(sort_no),
                "sort_no": str(sort_no),
                "structure": getv(r,"structure","STRUCTURE"),
                "finish_gsm": getv(r,"finish_gsm","FINISH GSM"),
                "finish_width": getv(r,"finish_width","FINISH WIDTH"),
                "selling_price": getv(r,"selling_price","sales_price","local_cost"),
                "price_per_kg_inr": getv(r,"price_per_kg_inr","local_cost","sales_price"),
                "currency_rate": 87,
                "discount_if_any": 0,
                "freight_inr_per_kg": 15,
                "commission_pct": 5,
                "lc_days_interest": 0,
            }
    return {}

# ---------- role/session ----------
def init_state():
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")
    st.session_state.setdefault("role", "")
    st.session_state.setdefault("module", "Cost Sheet")
    st.session_state.setdefault("whatif", {})

init_state()
# Clear old What-If session values once after every new code upload.
# This avoids stale browser session values changing the desktop-correct calculation.
if st.session_state.get("_app_version") != APP_VERSION:
    try:
        st.cache_data.clear()
    except Exception:
        pass
    for _k in list(st.session_state.keys()):
        if str(_k).startswith("wf_") or str(_k).startswith("sb_error_") or str(_k).startswith("sb_count_"):
            st.session_state.pop(_k, None)
    st.session_state["_app_version"] = APP_VERSION


def current_user_row()->Dict[str,Any]:
    df=load_users()
    m=df[df["username"].astype(str).str.lower()==str(st.session_state.username).lower()]
    return m.iloc[0].to_dict() if not m.empty else {}

def has_perm(module:str)->bool:
    if not st.session_state.logged_in: return False
    role=str(st.session_state.role)
    if role=="Developer": return True
    if role=="Admin" and module in ["Cost Sheet","Cost - Local","Cost - Export","Add Sort","RM Price","Users"]: return True
    r=current_user_row()
    key=PERM.get(module, "")
    return str(r.get(key,"False")).lower() in ("true","1","yes")

def first_allowed_module() -> str:
    for m in MODULES:
        if has_perm(m):
            return m
    return "Cost Sheet"

# ---------- UI ----------
def set_module(m:str):
    # Pure Streamlit button navigation. No URL query parameters are used,
    # so clicking module buttons cannot destroy the login session.
    st.session_state.module = m

def do_logout():
    st.session_state.logged_in=False
    st.session_state.username=""
    st.session_state.role=""
    st.session_state.module="Cost Sheet"

def header(title="Costing"):
    role=html.escape(str(st.session_state.role or "")); user=html.escape(str(st.session_state.username or ""))
    s = st.session_state.get("selected_sort", "")
    st.markdown(f"""
<div class="rbm-top">
  <div class="logo"><div class="big">RBM AI</div><div class="sub">Robotic Business Management</div></div>
  <div class="db-title">Siyaram's Costing DB</div>
  <div style="flex:1"></div>
  <div class="top-sort-only">SORT NO: {html.escape(str(s))}</div>
  <div class="top-actions"><span class="sync">☁ Sync Now</span><span class="on">⦿ ON</span></div>
  <div class="userbox">User: {user} | Role: {role}</div>
</div>
""", unsafe_allow_html=True)

    visible=[m for m in MODULES if has_perm(m)]
    if visible:
        st.markdown('<div class="nav-line-holder">', unsafe_allow_html=True)
        # Module buttons only. KPI boxes are now shown inside the dark-blue table headers.
        module_weights = [max(0.62, min(0.98, 0.38 + len(m) * 0.045)) for m in visible]
        cols = st.columns(module_weights + [0.72], gap="small")
        for i, m in enumerate(visible):
            btn_type = "primary" if st.session_state.get("module") == m else "secondary"
            if cols[i].button(m, key=f"nav_btn_{m}", type=btn_type, use_container_width=True):
                st.session_state.module = m
                st.rerun()
        if cols[-1].button("Logout", key="nav_logout_btn", use_container_width=True):
            do_logout(); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

def login_page():
    st.markdown("""
<div class="rbm-top"><div class="logo"><div class="big">RBM AI</div><div class="sub">Robotic Business Management</div></div><div class="titlebox">Costing</div></div>
""", unsafe_allow_html=True)
    st.markdown('<div class="login-hero"><div class="login-title">Secure Client Login</div><div class="login-sub">RBM Textile Costing System</div><div class="login-badge">Siyaram\'s Costing DB</div></div>', unsafe_allow_html=True)
    left, mid, right = st.columns([1.2, 1.0, 1.2])
    with mid:
        st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
        with st.form("login_form", clear_on_submit=False):
            u=st.text_input("Username", value="admin", key="login_u")
            p=st.text_input("Password", value="", type="password", key="login_p")
            submitted=st.form_submit_button("Login", type="primary")
        if submitted:
            users=load_users()
            if "username" in users.columns and "password" in users.columns:
                m=users[(users["username"].astype(str).str.lower()==u.strip().lower()) & (users["password"].astype(str)==p.strip())]
                if not m.empty:
                    st.session_state.logged_in=True
                    st.session_state.username=m.iloc[0]["username"]
                    st.session_state.role=m.iloc[0].get("role","User")
                    st.session_state.module=first_allowed_module()
                    try: st.query_params.clear()
                    except Exception: pass
                    st.rerun()
            st.markdown('<div class="warn">Wrong username or password.</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-note">Publisher: CSTRBM TECH PVT LTD • Made in India</div></div>', unsafe_allow_html=True)

# ---------- calculation ----------
def derive_after_knitting_pct(row:Dict[str,Any])->float:
    amt=to_float(getv(row,"wastage_2"), 0)
    raw=to_float(getv(row,"raw_material_cost"), 0)
    knit=to_float(getv(row,"knittng__processing_cost","knitting_processing_cost"), 0)
    base=raw+knit
    return round(amt/base*100,2) if amt and base else 10.0

def derive_commission_pct(row:Dict[str,Any])->float:
    amt=to_float(getv(row,"commission"), 0)
    base=to_float(getv(row,"price_per_kg_inr","selling_price"), 0)
    return round(amt/base*100,2) if amt and base else 5.0

def derive_margin_pct(row:Dict[str,Any])->float:
    margin=to_float(getv(row,"margin"), 0)
    costing=to_float(getv(row,"costing"), 0)
    return round(margin/costing*100,2) if margin and costing else 10.0

def apply_whatif(row:Dict[str,Any], wf:Dict[str,float])->Dict[str,Any]:
    # This follows the offline desktop formula from Final app_desktop.py.
    r=dict(row)
    currency=to_float(wf.get("currency_rate"), to_float(getv(r,"currency_rate"),87))
    discount=to_float(wf.get("discount_if_any"), to_float(getv(r,"discount_if_any"),0))
    freight=to_float(wf.get("freight_inr_per_kg"), to_float(getv(r,"freight_inr_per_kg"),0))
    commission_pct=to_float(wf.get("commission_pct"), derive_commission_pct(r))
    lc_int=to_float(wf.get("lc_days_interest"), to_float(getv(r,"lc_days_interest","lc_days_interest_amount","lc_days__interest_15_pm"),0))
    wastage_amt=to_float(wf.get("wastage"), to_float(getv(r,"wastage"),0))
    dyeing=to_float(wf.get("dyeing_cost_rs"), to_float(getv(r,"dyeing_cost_rs"),0))
    knitting=to_float(wf.get("knittng__processing_cost"), to_float(getv(r,"knittng__processing_cost"),90))
    waste_after_pct=to_float(wf.get("wastage_after_knitting_pct"), derive_after_knitting_pct(r))
    margin_pct=to_float(wf.get("margin_pct"), derive_margin_pct(r))

    cotton_yarn=to_float(getv(r,"cotton_yarn_costing"),0)
    dyed_yarn=cotton_yarn+wastage_amt+dyeing
    cotton_prop_raw=getv(r,"cotton_dyed_proportion_cost")
    cotton_prop=to_float(cotton_prop_raw, cotton_yarn+wastage_amt)
    raw=cotton_prop
    for k in ['polyester_cost','spandex_cost','melange_cost','kora_yarn_cost','reactive_yarn_cost','cooltex_yarn_cost','recycle_yarn_cost','dyed_poly_yarn_cost','micro_modal','viscose']:
        raw += to_float(getv(r,k),0)
    base_cost=raw+knitting
    waste_after_amt=base_cost*waste_after_pct/100.0
    costing=base_cost+waste_after_amt
    margin_amt=costing*margin_pct/100.0
    selling=costing+margin_amt-discount
    price_per_kg=selling
    commission_amt=price_per_kg*commission_pct/100.0
    total_inr=price_per_kg+freight+commission_amt+lc_int
    price_usd=total_inr/currency if currency else 0
    lm=to_float(getv(r,"linear_mtrskg"),0)
    ly=to_float(getv(r,"linear_ydgskg"),0)
    r.update({
        'wastage':wastage_amt, 'dyeing_cost_rs':dyeing, 'dyed_yarn_cost_rs':dyed_yarn,
        'cotton_dyed_proportion_cost':cotton_prop, 'raw_material_cost':raw,
        'knittng__processing_cost':knitting, 'wastage_after_knitting_pct':waste_after_pct,
        'wastage_2':waste_after_amt, 'costing':costing, 'margin':margin_amt, 'margin_pct':margin_pct,
        'selling_price':selling, 'currency_rate':currency, 'discount_if_any':discount,
        'price_per_kg_inr':price_per_kg, 'freight_inr_per_kg':freight,
        'commission':commission_amt, 'commission_pct':commission_pct, 'lc_days_interest':lc_int,
        'total_cost_pricefreightcomlc_int_inr__kg':total_inr,
        'total_cost_usd__kg':price_usd, 'price_usdkg':price_usd,
        'price_usdmtrs':price_usd/lm if lm else to_float(getv(r,'price_usdmtrs'),0),
        'price_usdyds':price_usd/ly if ly else to_float(getv(r,'price_usdyds'),0),
    })
    return r



def calc_local_cost(row:Dict[str,Any])->float:
    # Local Cost must match offline desktop: Costing value, not Selling Price.
    existing=getv(row,'costing','local_cost','local_cost_inr')
    if str(existing).strip() not in ('','nan','None'):
        return to_float(existing,0)
    raw=to_float(getv(row,'raw_material_cost'),0)
    knit=to_float(getv(row,'knittng__processing_cost','knitting_processing_cost'),0)
    wastage_after=to_float(getv(row,'wastage_2','wastage_after_knitting_cost'),0)
    return raw+knit+wastage_after

def calc_total_inr_kg(row:Dict[str,Any])->float:
    # Total Cost INR/KG must match offline desktop:
    # Price Per KG INR + Freight + Commission Amount + LC Days/Interest.
    existing=getv(row,'total_cost_pricefreightcomlc_int_inr__kg','total_cost_pricefreightcomlc_int','total_cost_inr_kg','total_cost_inr')
    if str(existing).strip() not in ('','nan','None'):
        return to_float(existing,0)
    price=to_float(getv(row,'price_per_kg_inr','selling_price'),0)
    freight=to_float(getv(row,'freight_inr_per_kg'),0)
    commission=to_float(getv(row,'commission'),0)
    if commission==0:
        commission_pct=to_float(getv(row,'commission_pct'), derive_commission_pct(row))
        commission=price*commission_pct/100 if price else 0
    lc=to_float(getv(row,'lc_days_interest','lc_days_interest_amount','lc_days__interest_15_pm'),0)
    return price+freight+commission+lc


def rows_to_df(rows:List[tuple]) -> pd.DataFrame:
    return pd.DataFrame([{"Particulars": str(a), "Value": fmt(b)} for a,b in rows])

def rows_to_excel_bytes(sheet_name:str, rows:List[tuple]) -> bytes:
    # Streamlit Cloud me openpyxl install na ho to .xlsx export error deta hai.
    # Isliye yahan pure HTML based .xls export banaya gaya hai, jo Excel me directly open hota hai
    # aur kisi extra package/openpyxl ki zaroorat nahi hoti.
    safe_sheet = html.escape(str(sheet_name))
    trs = "".join([
        f"<tr><td>{html.escape(str(a))}</td><td>{html.escape(fmt(b))}</td></tr>"
        for a, b in rows
    ])
    xls_html = f"""
    <html>
    <head>
    <meta charset="utf-8">
    <style>
      table{{border-collapse:collapse;font-family:Arial;font-size:12px;}}
      th{{background:#0b4f73;color:white;font-weight:bold;}}
      td,th{{border:1px solid #333;padding:6px;}}
    </style>
    </head>
    <body>
    <h2>Siyaram's Costing DB</h2>
    <h3>{safe_sheet}</h3>
    <table>
      <tr><th>Particulars</th><th>Value</th></tr>
      {trs}
    </table>
    </body>
    </html>
    """
    return xls_html.encode("utf-8")

def rows_report_html(title:str, sort_no:str, rows:List[tuple]) -> str:
    trs = "".join([f"<tr><td>{html.escape(str(a))}</td><td>{html.escape(fmt(b))}</td></tr>" for a,b in rows])
    return f"""
    <div style="background:white;border:1px solid #9fb4c4;padding:14px;margin:8px 0;">
      <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #0b4f73;padding-bottom:6px;margin-bottom:8px;">
        <div><b style="font-size:20px;color:#0b4f73;">Siyaram's Costing DB</b><br><span>{html.escape(title)}</span></div>
        <div style="font-weight:900;color:#0b4f73;">Sort No: {html.escape(str(sort_no))}</div>
      </div>
      <table style="width:100%;border-collapse:collapse;font-size:13px;font-weight:700;">
        <tr style="background:#0b4f73;color:white;"><th style="border:1px solid #333;padding:6px;text-align:left;">Particulars</th><th style="border:1px solid #333;padding:6px;text-align:left;">Value</th></tr>
        {trs}
      </table>
      <div style="margin-top:10px;font-weight:800;color:#0b4f73;">Publisher: RBM Textile Solutions</div>
    </div>
    """

def row_class(label:str)->str:
    l=label.lower()
    if "discount" in l: return "row-red"
    if label in ["Wastage %","Dyeing Cost Rs.","Knitting + Processing Cost","Wastage % After Knitting","Currency Rate","Freight INR/KG","Commission %","LC Days / Interest","Margin"]: return "row-green"
    if label in ["Raw Material Cost","Costing","Selling Price","Price USD/KG","Total Cost INR/KG","Total Cost USD/KG"]: return "row-yellow"
    return "row-blue" if len(label)%2 else ""

def html_table(title:str, rows:List[tuple], header_extra:str="")->str:
    trs=[]
    for label,val in rows:
        trs.append(f'<tr class="{row_class(label)}"><td>{html.escape(label)}</td><td>{html.escape(fmt(val))}</td></tr>')
    extra_html = f'<div class="tbl-kpis">{header_extra}</div>' if header_extra else ''
    return f'<div class="tblbox"><div class="tbltitle"><span class="tbltitle-main">▣ {html.escape(title)}</span>{extra_html}</div><table class="rbmtable">{"".join(trs)}</table></div>'

# ---------- pages ----------
def cost_sheet_page():
    header("Costing")
    sorts=sort_options()
    if not sorts:
        st.error("group_costing.csv not found or empty. Upload group_costing.csv in GitHub root OR data/group_costing.csv.")
        return
    selected=st.session_state.get("selected_sort", sorts[0])
    if selected not in sorts: selected=sorts[0]

    # Top compact control line is outside form so changing Sort No updates values immediately.
    c0,c1,c2,c3,c4,c5,c6,c7,c8,c9,c10=st.columns([1.12,1.38,0.48,0.72,0.82,0.08,0.44,0.78,0.48,0.78,0.44], gap="small")
    with c0: st.markdown('<div class="label">Sort No (Excel D1):</div>', unsafe_allow_html=True)
    with c1:
        sort=st.selectbox("Sort No", sorts, index=sorts.index(selected), label_visibility="collapsed", key="selected_sort")
    with c2:
        if st.button("Refresh", type="primary", key="top_refresh_btn"): st.rerun()
    print_placeholder = c3.empty()
    export_placeholder = c4.empty()
    with c6: st.markdown('<div class="country-inline-label">Country</div>', unsafe_allow_html=True)
    with c7: country_selected = st.selectbox("Country", ["Bangladesh","Vietnam","Sri Lanka","Japan","USA","UAE"], index=0, label_visibility="collapsed", key="country_select")

    base=get_sort_row(sort)
    if not base:
        st.error("Selected Sort No not found.")
        return

    wf_key=f"wf_{sort}"
    applied = st.session_state.get(wf_key)
    row = apply_whatif(base, applied) if applied else base

    st.markdown('<div class="whatif-title">What-If Analysis</div>', unsafe_allow_html=True)
    cols=st.columns(9, gap="small")
    defaults={
        'wastage':to_float(getv(row,'wastage'),0),
        'dyeing_cost_rs':to_float(getv(row,'dyeing_cost_rs'),0),
        'knittng__processing_cost':to_float(getv(row,'knittng__processing_cost'),90),
        'wastage_after_knitting_pct':derive_after_knitting_pct(row),
        'discount_if_any':to_float(getv(row,'discount_if_any'),0),
        'currency_rate':to_float(getv(row,'currency_rate'),87),
        'freight_inr_per_kg':to_float(getv(row,'freight_inr_per_kg'),0),
        'commission_pct':derive_commission_pct(row),
        'lc_days_interest':to_float(getv(row,'lc_days_interest','lc_days_interest_amount'),0),
        'margin_pct':derive_margin_pct(row),
    }
    keys=[('wastage','Waste %'),('dyeing_cost_rs','Dyeing Cost Rs.'),('wastage_after_knitting_pct','Knit Waste %'),('discount_if_any','Discount %'),('currency_rate','Currency Rate'),('freight_inr_per_kg','Freight INR/KG'),('commission_pct','Commission %'),('lc_days_interest','LC Days / Interest'),('margin_pct','Margin %')]
    vals={}
    for i,(k,label) in enumerate(keys):
        with cols[i]: vals[k]=st.number_input(label, value=float(defaults[k]), step=1.0 if k!='wastage' else 0.25, format="%.2f", key=f"num_{sort}_{k}")
    with c8:
        submitted=st.button("Apply", type="primary", key="top_apply_btn")
    with c9:
        freight_clicked=st.button("Freight Master", key="top_freight_btn")
    with c10:
        cleared=st.button("Clear", key="top_clear_btn")
    if submitted:
        st.session_state[wf_key]=vals
        st.rerun()
    if cleared:
        st.session_state.pop(wf_key, None)
        st.session_state.pop("show_freight_master", None)
        st.rerun()
    if freight_clicked:
        st.session_state["show_freight_master"] = not st.session_state.get("show_freight_master", False)
        st.rerun()
    if st.session_state.get("show_freight_master", False):
        st.markdown("<div class='ok'><b>Freight Master</b> - Country wise default freight INR/KG. Select country and click Apply Country Freight.</div>", unsafe_allow_html=True)
        fcols = st.columns([1.5,1,1,6], gap="small")
        with fcols[0]: st.write("Country")
        with fcols[1]: st.write("Freight INR/KG")
        with fcols[2]:
            if st.button("Apply Country Freight", key="apply_country_freight_btn"):
                vals["freight_inr_per_kg"] = FREIGHT_MASTER.get(country_selected, vals.get("freight_inr_per_kg", 0))
                st.session_state[wf_key] = vals
                st.rerun()
        st.table(rows_to_df(freight_master_rows()))

    cost_rows=[
        ("Cotton Yarn Costing",getv(row,'cotton_yarn_costing')),("Wastage %",getv(row,'wastage')),("Dyeing Cost Rs.",getv(row,'dyeing_cost_rs')),
        ("Dyed Yarn Cost Rs.",getv(row,'dyed_yarn_cost_rs')),("Cotton Dyed Proportion Cost",getv(row,'cotton_dyed_proportion_cost')),
        ("Polyester Cost",getv(row,'polyester_cost')),("Spandex Cost",getv(row,'spandex_cost')),("Kora Yarn Cost",getv(row,'kora_yarn_cost')),
        ("Raw Material Cost",getv(row,'raw_material_cost')),("Knitting + Processing Cost",getv(row,'knittng__processing_cost')),
        ("Wastage % After Knitting",getv(row,'wastage_after_knitting_pct', default=derive_after_knitting_pct(row))),
        ("Wastage After Knitting Cost",getv(row,'wastage_2')),("Costing",getv(row,'costing')),("Margin",getv(row,'margin')),("Selling Price",getv(row,'selling_price')),
    ]
    export_rows=[
        ("Currency Rate",getv(row,'currency_rate')),("Discount If Any",getv(row,'discount_if_any')),("Price USD/KG",getv(row,'price_usdkg','total_cost_usd__kg')),
        ("Price USD/Mtrs",getv(row,'price_usdmtrs')),("Price USD/Yds",getv(row,'price_usdyds')),("Linear Mtrs/Kg",getv(row,'linear_mtrskg')),
        ("Linear Yds/Kg",getv(row,'linear_ydgskg')),("Width CMS",getv(row,'width_cms','finish_width')),("Width Inch",getv(row,'width_inch')),
        ("Weight GSM",getv(row,'weight_gsm','finish_gsm')),("Price Per KG INR",getv(row,'price_per_kg_inr','selling_price')),("Freight INR/KG",getv(row,'freight_inr_per_kg')),
        ("Commission %",getv(row,'commission_pct', default=derive_commission_pct(row))),("Commission Amount",getv(row,'commission')),
        ("LC Days / Interest",getv(row,'lc_days_interest','lc_days_interest_amount','lc_days__interest_15_pm')),
        ("Total Cost INR/KG",calc_total_inr_kg(row)),("Total Cost USD/KG",getv(row,'total_cost_usd__kg')),
    ]
    full_export_rows = [("REPORT", "Cost Sheet"), ("Sort No", sort)] + cost_rows + export_rows
    with print_placeholder.container():
        print_clicked = st.button("Print Preview", key=f"print_cost_sheet_{sort}")
    with export_placeholder.container():
        st.download_button("Export This Sort", data=rows_to_excel_bytes("Cost Sheet", full_export_rows), file_name=f"Cost_Sheet_{sort}.xls", mime="application/vnd.ms-excel", key=f"export_cost_sheet_{sort}")
    if print_clicked:
        st.session_state[f"show_print_cost_sheet_{sort}"] = not st.session_state.get(f"show_print_cost_sheet_{sort}", False)
    if st.session_state.get(f"show_print_cost_sheet_{sort}", False):
        st.markdown(rows_report_html("Cost Sheet Print Preview", sort, full_export_rows), unsafe_allow_html=True)
    cost_header_kpis = (
        f'<div class="tbl-kpi k1"><b>Structure</b>{html.escape(fmt(getv(row,"structure")))}</div>'
        f'<div class="tbl-kpi k2"><b>Finish GSM</b>{html.escape(fmt(getv(row,"finish_gsm")))}</div>'
        f'<div class="tbl-kpi k3"><b>Finish Width</b>{html.escape(fmt(getv(row,"finish_width")))}</div>'
    )
    export_header_kpis = (
        f'<div class="tbl-kpi k4"><b>Selling Price</b>{html.escape(fmt(getv(row,"selling_price")))}</div>'
        f'<div class="tbl-kpi k5"><b>USD/KG</b>{html.escape(fmt(getv(row,"total_cost_usd__kg","price_usdkg")))}</div>'
    )
    st.markdown(f'<div class="table-grid">{html_table("Cost Build-up",cost_rows,cost_header_kpis)}{html_table("Export / Price Calculation",export_rows,export_header_kpis)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="footer"><span>Publisher: <b>RBM Textile Solutions</b></span><span>Offline Textile Costing • Actual Excel Data • Print Preview • Backup</span><span>Made in India 🇮🇳</span></div><div class="content-pad"></div>', unsafe_allow_html=True)

def simple_cost_page(kind:str):
    header("Costing")
    sorts=sort_options(); selected=st.session_state.get("selected_sort", sorts[0] if sorts else "")
    st.markdown(f'<div class="sheet-head"><span>{html.escape(kind.upper())}</span></div>', unsafe_allow_html=True)
    if not sorts:
        st.error("No sort data found."); return
    c1,c2,c3=st.columns([2.2,0.8,1.0], gap="small")
    with c1:
        sort=st.selectbox("Sort No", sorts, index=sorts.index(selected) if selected in sorts else 0, key=f"{kind}_sort")
    r=get_sort_row(sort)
    if kind=="Cost - Local":
        rows=[("Sort No",sort),("Structure",getv(r,'structure')),("Finish GSM",getv(r,'finish_gsm')),("Finish Width",getv(r,'finish_width')),("Local Cost",calc_local_cost(r)),("Sales Price",getv(r,'selling_price'))]
    else:
        rows=[("Sort No",sort),("Structure",getv(r,'structure')),("Finish GSM",getv(r,'finish_gsm')),("Finish Width",getv(r,'finish_width')),("Price",getv(r,'selling_price')),("Currency Rate",getv(r,'currency_rate')),("USD/Kg",getv(r,'price_usdkg','total_cost_usd__kg')),("Price USD Mtrs",getv(r,'price_usdmtrs')),("Price USD Yds",getv(r,'price_usdyds')),("Total Cost INR/KG",calc_total_inr_kg(r)),("Total Cost USD/KG",getv(r,'total_cost_usd__kg'))]
    export_rows = [("REPORT", kind), ("Sort No", sort)] + rows
    with c2:
        print_clicked=st.button("Print Preview", key=f"print_{kind}_{sort}")
    with c3:
        st.download_button("Export This Sort", data=rows_to_excel_bytes(kind, export_rows), file_name=f"{kind.replace(' ','_').replace('-','')}_{sort}.xls", mime="application/vnd.ms-excel", key=f"export_{kind}_{sort}")
    if print_clicked:
        st.session_state[f"show_print_{kind}_{sort}"] = not st.session_state.get(f"show_print_{kind}_{sort}", False)
    if st.session_state.get(f"show_print_{kind}_{sort}", False):
        st.markdown(rows_report_html(f"{kind} Print Preview", sort, export_rows), unsafe_allow_html=True)
    st.markdown(html_table(kind, rows), unsafe_allow_html=True)

def add_sort_page():
    header("Costing")
    st.markdown('<div class="sheet-head"><span>Add Sort</span></div>', unsafe_allow_html=True)
    with st.form("add_sort_form"):
        c1,c2,c3=st.columns(3, gap="small")
        sort=c1.text_input("Sort No")
        structure=c1.text_input("Structure")
        gsm=c2.number_input("Finish GSM", value=0.0, step=1.0, format="%.2f")
        width=c2.number_input("Finish Width", value=0.0, step=1.0, format="%.2f")
        local=c3.number_input("Local Cost", value=0.0, step=1.0, format="%.2f")
        sales=c3.number_input("Sales Price", value=0.0, step=1.0, format="%.2f")
        submitted=st.form_submit_button("Submit / Save Sort", type="primary")
        if submitted:
            if not sort.strip(): st.error("Sort No required.")
            else:
                df=load_group(); c=group_sort_col(df) if not df.empty else 'dev_sorts'
                new={col:"" for col in df.columns}
                if c in new: new[c]=sort.strip()
                for col,val in [('structure',structure),('finish_gsm',gsm),('finish_width',width),('selling_price',sales),('price_per_kg_inr',local)]:
                    if col in new: new[col]=val
                df=pd.concat([df,pd.DataFrame([new])], ignore_index=True)
                save_group(df); st.success("Sort saved in current app session.")

def rm_price_page():
    header("Costing")
    st.markdown('<div class="sheet-head"><span>RM Price Master</span></div>', unsafe_allow_html=True)
    df=load_rm()

    mode = st.radio("Mode", ["Add New Price", "Edit Existing Price"], horizontal=True, label_visibility="collapsed")

    if mode == "Add New Price":
        with st.form("rm_form_add"):
            c1,c2,c3,c4=st.columns([2,2,1,1], gap="small")
            parts=sorted([x for x in df.get('particulars',pd.Series(dtype=str)).astype(str).unique() if x])
            prods=sorted([x for x in df.get('product',pd.Series(dtype=str)).astype(str).unique() if x])
            part=c1.selectbox("Particulars", parts+['Add New'], index=0 if parts else 0)
            if part=='Add New': part=c1.text_input("New Particulars")
            prod=c2.selectbox("Product / Yarn", prods+['Add New'], index=0 if prods else 0)
            if prod=='Add New': prod=c2.text_input("New Product / Yarn")
            price=c3.number_input("Price", value=0.0, step=1.0, format="%.2f")
            save=c4.form_submit_button("Save RM Price", type="primary")
            if save and part and prod:
                new={'particulars':part,'product':prod,'price':price,'change_date':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'price_numeric':price}
                df=pd.concat([df,pd.DataFrame([new])], ignore_index=True); save_rm(df); st.success("RM Price saved.")
    else:
        if df.empty:
            st.warning("No RM Price data available for edit.")
        else:
            edit_df = df.reset_index().copy()
            edit_df["select_text"] = edit_df.apply(lambda x: f"{x['index']} | {x.get('particulars','')} | {x.get('product','')} | {x.get('price','')}", axis=1)
            with st.form("rm_form_edit"):
                c0,c1,c2,c3,c4=st.columns([1.4,2,2,1,1], gap="small")
                selected_text = c0.selectbox("Select Row", edit_df["select_text"].tolist())
                row_index = int(str(selected_text).split(" | ")[0])
                old_row = df.loc[row_index].to_dict()
                part = c1.text_input("Particulars", value=str(old_row.get('particulars','')))
                prod = c2.text_input("Product / Yarn", value=str(old_row.get('product','')))
                price = c3.number_input("Price", value=to_float(old_row.get('price'),0), step=1.0, format="%.2f")
                update = c4.form_submit_button("Update Price", type="primary")
                if update:
                    df.loc[row_index, 'particulars'] = part
                    df.loc[row_index, 'product'] = prod
                    df.loc[row_index, 'price'] = price
                    df.loc[row_index, 'price_numeric'] = price
                    df.loc[row_index, 'change_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    save_rm(df)
                    st.success("RM Price updated.")

    st.dataframe(load_rm(), use_container_width=True, height=420)

def users_page():
    header("Costing")
    if st.session_state.role not in ["Developer","Admin"]:
        st.error("You do not have permission for User Management."); return
    st.markdown('<div class="sheet-head"><span>User Management</span></div>', unsafe_allow_html=True)
    df=load_users()

    # Edit existing user option
    edit_df = df.copy()
    if st.session_state.role != "Developer" and 'role' in edit_df.columns:
        edit_df = edit_df[edit_df['role'].astype(str) != "Developer"]
    existing_users = [str(x) for x in edit_df.get('username', pd.Series(dtype=str)).dropna().tolist() if str(x).strip()]
    st.markdown('<div style="font-weight:900;color:#001b34;margin:8px 0 4px 0;">Edit Existing User</div>', unsafe_allow_html=True)
    edit_choice = st.selectbox("Edit Existing User", ["Create New User"] + existing_users, key="edit_existing_user", label_visibility="collapsed")
    edit_row = {}
    if edit_choice != "Create New User" and 'username' in df.columns:
        m = df[df['username'].astype(str).str.lower() == edit_choice.lower()]
        if not m.empty:
            edit_row = m.iloc[0].to_dict()

    with st.form("user_form"):
        c1,c2,c3=st.columns(3, gap="small")
        username=c1.text_input("Username", value=str(edit_row.get('username','')), disabled=(edit_choice != "Create New User"))
        password=c2.text_input("Password", value=str(edit_row.get('password','')))
        role_options=["Admin","User"] if st.session_state.role!="Developer" else ["Admin","User","Developer"]
        default_role = str(edit_row.get('role', 'User' if edit_choice != "Create New User" else 'Admin'))
        role_index = role_options.index(default_role) if default_role in role_options else 0
        role=c3.selectbox("Role", role_options, index=role_index)
        pcols=st.columns(7, gap="small")
        vals={}
        for i,(m,k) in enumerate([(m,PERM[m]) for m in MODULES]):
            saved_val = str(edit_row.get(k, "False")).lower() in ("true","1","yes") if edit_row else (role in ["Admin","Developer"])
            if m=="Users" and role=="User":
                vals[k]=False
            else:
                vals[k]=pcols[i].checkbox(m, value=saved_val, key=f"perm_{k}_{edit_choice}")
        save=st.form_submit_button("Update User" if edit_choice != "Create New User" else "Save User", type="primary")
        if save:
            final_username = edit_choice if edit_choice != "Create New User" else username
            if not final_username or not password: st.error("Username and Password required.")
            else:
                old_created = edit_row.get('created_at', datetime.now().isoformat()) if edit_row else datetime.now().isoformat()
                row={'username':final_username,'password':password,'role':role, **{k:v for k,v in vals.items()}, 'can_edit_sort': vals.get('can_add_sort',False), 'can_delete_sort': vals.get('can_add_sort',False), 'created_at':old_created}
                df=df[df['username'].astype(str).str.lower()!=str(final_username).lower()] if 'username' in df.columns else df
                df=pd.concat([df,pd.DataFrame([row])],ignore_index=True); save_users(df); st.success("User updated." if edit_choice != "Create New User" else "User saved.")
    show=df.copy()
    if st.session_state.role!="Developer" and 'role' in show.columns:
        show=show[show['role'].astype(str)!="Developer"]
    st.dataframe(show, use_container_width=True, height=400)

# ---------- main ----------
if not st.session_state.logged_in:
    login_page()
    st.stop()

module=st.session_state.get("module","Cost Sheet")
if not has_perm(module):
    module=first_allowed_module()
    st.session_state.module=module

if module=="Cost Sheet": cost_sheet_page()
elif module=="Cost - Local": simple_cost_page("Cost - Local")
elif module=="Cost - Export": simple_cost_page("Cost - Export")
elif module=="Add Sort": add_sort_page()
elif module=="RM Price": rm_price_page()
elif module=="Users": users_page()
else: cost_sheet_page()
