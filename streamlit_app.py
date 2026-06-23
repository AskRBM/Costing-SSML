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
APP_VERSION = "2026-06-23-online-final-offline-match-v20"

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

def _normalize_supabase_url(u: str) -> str:
    # Streamlit secrets me kabhi-kabhi /rest/v1/ wala API URL paste ho jata hai.
    # REST call banate time hame sirf base URL chahiye: https://xxxx.supabase.co
    u = str(u or "").strip().rstrip("/")
    for cut in ["/rest/v1", "/auth/v1", "/storage/v1"]:
        if cut in u:
            u = u.split(cut)[0]
    if ".supabase.co" in u:
        u = u.split(".supabase.co")[0] + ".supabase.co"
    return u.rstrip("/")

ONLINE_SUPABASE_URL = _normalize_supabase_url(_secret_or_env(
    "RBM_SUPABASE_URL", "SUPABASE_URL", "supabase_url",
    default="https://mmzvwlitakluttlnnioh.supabase.co"
))

# Use publishable/anon key for Streamlit online read. Do NOT use service-role key in public GitHub.
ONLINE_SUPABASE_KEY = _secret_or_env(
    "RBM_SUPABASE_KEY", "SUPABASE_KEY", "SUPABASE_ANON_KEY", "supabase_key",
    default="sb_publishable_OcHaa48FL57wRoRohD6IsQ_7pCJd6LB"
).strip()

# Optional secret-only fallback. Do NOT put service role key in GitHub.
# Add it only in Streamlit Cloud: App > Settings > Secrets
# SUPABASE_SERVICE_ROLE_KEY = "your service role key"
ONLINE_SUPABASE_SERVICE_KEY = _secret_or_env(
    "RBM_SUPABASE_SERVICE_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SERVICE_ROLE_KEY", "supabase_service_role_key",
    default=""
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
    return bool(ONLINE_SUPABASE_URL and (ONLINE_SUPABASE_KEY or ONLINE_SUPABASE_SERVICE_KEY))

def _available_supabase_keys() -> List[tuple]:
    """Return keys in safe order. Publishable/anon first; service key only if configured in Streamlit secrets.
    This solves 401 Unauthorized when publishable key is not allowed for REST read.
    """
    keys=[]
    if ONLINE_SUPABASE_KEY:
        keys.append(("publishable/anon", ONLINE_SUPABASE_KEY))
    if ONLINE_SUPABASE_SERVICE_KEY and ONLINE_SUPABASE_SERVICE_KEY != ONLINE_SUPABASE_KEY:
        keys.append(("service-secret", ONLINE_SUPABASE_SERVICE_KEY))
    return keys

def _sb_headers(key: str) -> Dict[str, str]:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
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
    """Always read fresh live synced Supabase table.
    Tries publishable/anon key first, then service key from Streamlit secrets if available.
    """
    if not supabase_enabled():
        st.session_state[f"sb_error_{table}"] = "Supabase URL/key missing"
        return pd.DataFrame()

    errors=[]
    for key_name, key in _available_supabase_keys():
        try:
            # IMPORTANT: Do NOT add custom query params like _cb here.
            # Supabase PostgREST treats unknown query params as column filters and gives PGRST100.
            # Cache is avoided by headers and by not using st.cache_data for live Supabase reads.
            url = f"{ONLINE_SUPABASE_URL}/rest/v1/{urllib.parse.quote(table)}?select=*&limit={int(limit)}"
            st.session_state[f"sb_url_{table}"] = url
            headers = _sb_headers(key)
            headers["Range-Unit"] = "items"
            headers["Range"] = f"0-{int(limit)-1}"
            req = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
            data = json.loads(raw) if raw.strip() else []
            if not data:
                errors.append(f"{key_name}: 0 rows")
                continue
            df = pd.DataFrame(data).fillna("")
            df.columns = [norm_col(c) for c in df.columns]
            df = _expand_json_data_column(df)
            st.session_state[f"sb_error_{table}"] = ""
            st.session_state[f"sb_count_{table}"] = len(df)
            st.session_state[f"sb_key_used_{table}"] = key_name
            return df
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", errors="ignore")
            except Exception:
                body = ""
            errors.append(f"{key_name}: HTTP {e.code} {body[:180]}")
        except Exception as e:
            errors.append(f"{key_name}: {e}")

    msg = " | ".join(errors) if errors else "Unknown Supabase read error"
    if "401" in msg or "Unauthorized" in msg:
        msg += " | Fix: add SUPABASE_SERVICE_ROLE_KEY in Streamlit Secrets, or add correct anon/public REST API key."
    st.session_state[f"sb_error_{table}"] = msg
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

def _standardize_rm_df(df: pd.DataFrame, source_name: str = "") -> pd.DataFrame:
    """Make all RM price sources look same: particulars, product, price, change_date, price_numeric."""
    if df is None or df.empty:
        return pd.DataFrame()
    x = df.copy().fillna("")
    x.columns = [norm_col(c) for c in x.columns]
    rename_map = {
        "product_2": "product", "product_yarn": "product", "yarn": "product", "item": "product",
        "particular": "particulars", "category": "particulars",
        "changed_at": "change_date", "date": "change_date", "updated_at": "change_date",
    }
    for a, b in rename_map.items():
        if a in x.columns and b not in x.columns:
            x[b] = x[a]
    for c in ["particulars", "product", "price", "change_date", "price_numeric"]:
        if c not in x.columns:
            x[c] = ""
    if x["price_numeric"].astype(str).str.strip().eq("").all():
        x["price_numeric"] = x["price"].map(lambda v: to_float(v, 0))
    else:
        x["price_numeric"] = x["price_numeric"].map(lambda v: to_float(v, 0))
    x["price"] = x.apply(lambda r: r["price"] if str(r.get("price","")).strip() else r.get("price_numeric",0), axis=1)
    x["_source"] = source_name
    x = x[(x["product"].astype(str).str.strip() != "") & (x["price_numeric"].map(lambda v: to_float(v,0)) > 0)]
    return x[["particulars", "product", "price", "change_date", "price_numeric", "_source"]].copy()

def load_rm() -> pd.DataFrame:
    """Read latest RM prices from all online/offline sources.

    Final fix: offline master table is rm_current, but online Supabase also has
    rm_price_master. We merge both, plus price_history/csv fallback, and keep
    the latest row by Particulars + Product. This makes new items like PKS/SPS
    immediately available for online costing after Sync/Fetch.
    """
    frames = []
    source_priority = {"csv": 0, "price_history": 1, "rm_current": 2, "rm_price_master": 3}
    for table in ["rm_price_master", "rm_current", "price_history"]:
        df_live = supabase_table_df(table)
        if not df_live.empty:
            x = _standardize_rm_df(df_live, table) if "_standardize_rm_df" in globals() else df_live.copy()
            if not x.empty:
                x["_source_priority"] = source_priority.get(table, 1)
                frames.append(x)
    csv_df = read_csv(str(RM_CSV))
    if not csv_df.empty:
        x = _standardize_rm_df(csv_df, "csv") if "_standardize_rm_df" in globals() else csv_df.copy()
        if not x.empty:
            x["_source_priority"] = source_priority.get("csv", 0)
            frames.append(x)
    frames = [f for f in frames if f is not None and not f.empty]
    if frames:
        df = pd.concat(frames, ignore_index=True).fillna("")
        for c in ["particulars", "product", "price", "change_date", "price_numeric"]:
            if c not in df.columns:
                df[c] = ""
        df["price_numeric"] = df["price_numeric"].map(lambda v: to_float(v, 0))
        df["_pkey"] = df["particulars"].astype(str).str.strip().str.upper() + "||" + df["product"].astype(str).str.strip().str.upper()
        df["_dt"] = pd.to_datetime(df["change_date"], errors="coerce")
        df = df.sort_values(["_pkey", "_dt", "_source_priority"], na_position="first").drop_duplicates("_pkey", keep="last")
        df = df.drop(columns=[c for c in ["_pkey", "_dt", "_source_priority"] if c in df.columns])
        try:
            st.session_state["sb_count_rm_all"] = len(df)
        except Exception:
            pass
        return df.reset_index(drop=True)
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

def fetch_live_supabase_now():
    # Clear CSV/session cache and force fresh Supabase read.
    try:
        st.cache_data.clear()
    except Exception:
        pass
    for k in list(st.session_state.keys()):
        if str(k).startswith("sb_") or str(k) in ("group_df", "rm_df", "users_df"):
            st.session_state.pop(k, None)
    # Touch tables so status immediately appears after button click.
    _ = supabase_table_df("specs")
    _ = supabase_table_df("group_costing")
    _ = supabase_table_df("rm_current")
    _ = supabase_table_df("rm_price_master")
    _ = supabase_table_df("price_history")
    _ = supabase_table_df("app_users")


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
    """Get value safely even when Supabase/CSV column names differ.
    Fixes online blanks caused by keys like total_cost_usd__kg vs total_cost_usd_kg.
    """
    if not isinstance(row, dict):
        return default
    norm_map = {}
    for rk, rv in row.items():
        norm_map[norm_col(rk)] = rv
    for n in names:
        key = norm_col(n)
        # Try exact key first
        if n in row and str(row[n]).strip() not in ("", "nan", "None"):
            return row[n]
        # Try normalized key
        if key in norm_map and str(norm_map[key]).strip() not in ("", "nan", "None"):
            return norm_map[key]
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




# Excel Set sheet formula mapping
# A = Particular, B = Yarn, C = Yarn Price, F = SPECS VLOOKUP column index.
# Formula used in Excel Set sheet:
# D(row) = VLOOKUP(SortNo, SPECS!B:EV, F(row), FALSE)
# E(row) = C(row) * D(row) %
SET_YARN_ROWS = [
    ("% OF INDIGO", "30S KCW", 230.0, 5), ("% OF INDIGO", "24S KCW", 225.0, 6), ("% OF INDIGO", "20S KCW", 220.0, 7),
    ("% OF INDIGO", "30S KCW", 305.0, 8), ("% OF INDIGO", "24S KCW", 295.0, 9), ("% OF INDIGO", "20S KCW", 285.0, 10),
    ("% OF INDIGO", "30S KCW", 230.0, 11), ("% OF INDIGO", "24S KCW", 225.0, 12), ("% OF INDIGO", "20S KCW", 285.0, 13),
    ("% OF Delta", "30S KCW", 230.0, 14), ("% OF Delta", "24S KCW", 225.0, 15), ("% OF Delta", "20S KCW", 220.0, 16),
    ("% OF INDIGO", "30S CCW", 255.0, 17), ("% OF INDIGO", "24S CCW", 250.0, 18), ("% OF INDIGO", "20S CCW", 245.0, 19),
    ("% OF Delta", "30S CCW", 255.0, 20), ("% OF Delta", "24S CCW", 250.0, 21), ("% OF Delta", "20S CCW", 245.0, 22),
    ("% OF Dezire", "30S KW", 230.0, 23), ("% OF Dezire", "24S", 225.0, 24), ("% OF Dezire", "20S", 220.0, 25),
    ("% OF IBST", "30S", 230.0, 26), ("% OF IBST", "24S", 225.0, 27), ("% OF IBST", "20S", 220.0, 28),
    ("Indigo Slub (Santro)", "30", 290.0, 29), ("Indigo Slub (Santro)", "24", 290.0, 30), ("Delta Slub", "30", 290.0, 31), ("Delta Slub", "24", 290.0, 32),
    ("Tencel Indigo", "30", 295.0, 33), ("Tencel Indigo", "24", 290.0, 34), ("Tencel Indigo", "20", 285.0, 35),
    ("Tencel Delta", "30", 295.0, 36), ("Tencel Delta", "24", 290.0, 37), ("Tencel Delta", "20", 285.0, 38),
    ("% White Poly", "55 D", 145.0, 39), ("% White Poly", "75 D", 123.0, 40), ("% White Poly", "80 D", 123.0, 41),
    ("% White Poly", "100 D", 121.0, 42), ("% White Poly", "150 D", 112.0, 43), ("% White Poly", "200 D", 110.0, 44), ("% White Poly", "300 D", 109.0, 45),
    ("% Black Poly", "55 D", 145.0, 46), ("% Black Poly", "75 D", 121.0, 47), ("% Black Poly", "80 D", 121.0, 48),
    ("% Black Poly", "100 D", 120.0, 49), ("% Black Poly", "150 D", 117.0, 50), ("% Black Poly", "200 D", 110.0, 51), ("% Black Poly", "300 D", 112.0, 52),
    ("% OF LYCRA", "20 D", 355.0, 53), ("% OF LYCRA", "30 D", 345.0, 54), ("% OF LYCRA", "40 D", 335.0, 55), ("% OF LYCRA", "55 D", 335.0, 56),
    ("% OF LYCRA", "70 D", 335.0, 57), ("% OF LYCRA", "105 D", 395.0, 58),
    ("% Melange", "80 D", 172.0, 59), ("% Melange", "150 D", 122.0, 60), ("% Melange", "160 D", 122.0, 61), ("% Melange", "220 D", 130.0, 62), ("% Melange", "300 D", 112.0, 63),
    ("Kora / Grey", "30 Slub", 290.0, 64), ("Kora / Grey", "Slub", 0.0, 65), ("Kora / Grey", "60", 340.0, 66), ("Kora / Grey", "40", 280.0, 67),
    ("Kora / Grey", "34", 260.0, 68), ("Kora / Grey", "30 CCH", 255.0, 69), ("Kora / Grey", "30 KCW", 260.0, 70),
    ("Kora / Grey", "24 KCW", 250.0, 71), ("Kora / Grey", "20 KCW", 230.0, 72), ("Kora / Grey", "20 OE", 185.0, 73), ("Kora / Grey", "16", 245.0, 74),
    ("Reactive", "30", 350.0, 75), ("Reactive", "24", 345.0, 76), ("Reactive", "20", 340.0, 77),
    ("Cooltex", "75 D", 178.0, 78), ("Cooltex", "150 D", 179.0, 79), ("Cooltex", "200 D", 172.0, 80),
    ("Recycle", "28 PC", 230.0, 81), ("Recycle", "24 PC", 215.0, 82), ("Recycle", "80 D Poly", 175.0, 83), ("Recycle", "150 D Poly", 165.0, 84),
    ("Dyed Poly", "75 D", 210.0, 85), ("Dyed Poly", "150 D", 200.0, 86), ("Dyed Poly", "300 D", 200.0, 87),
    ("Micro Modal", "30", 390.0, 88), ("Micro Modal", "24", 385.0, 89), ("Micro Modal", "20", 380.0, 90),
    ("Viscose", "40", 390.0, 91), ("Viscose", "30", 390.0, 92), ("Viscose", "24", 385.0, 93),
]

COTTON_SET_CATEGORIES = {"% OF INDIGO", "% OF DELTA", "% OF DEZIRE", "% OF IBST", "INDIGO SLUB (SANTRO)", "DELTA SLUB", "TENCEL INDIGO", "TENCEL DELTA"}

# Online fallback for software-added SPECS yarns created from Offline Bulk Upload.
# These rows are required because old Supabase `specs` table may not have real column
# names like PKS/SPS even after offline sync; it may only show total composition.
# Offline app uses these same uploaded rows and RM Price Master values.
ONLINE_EXTRA_SORT_YARN_ITEMS = {
    "1202": [
        ("% OF INDIGO", "PKS", 50.0, 200.0),
        ("First Flight", "SPS", 50.0, 300.0),
    ],
    "1203": [
        ("% OF INDIGO", "30S KCW", 100.0, 230.0),
    ],
}

def extra_sort_yarn_items_for_specs(spec_row: Dict[str, Any]) -> List[tuple]:
    """Return offline-added yarn rows for newly uploaded sorts when those dynamic
    columns are not visible in the online Supabase schema.
    tuple = (particular, yarn, pct, default_price)
    """
    sort_no = clean_sort_value(getv(spec_row, "dev_sorts", "sort_no", "sort", "dev_sort", "sorts"))
    return ONLINE_EXTRA_SORT_YARN_ITEMS.get(sort_no, [])

def _is_cotton_like_particular(particular: str, yarn: str = "") -> bool:
    txt = (str(particular or "") + " " + str(yarn or "")).upper()
    if any(x in txt for x in ["SPANDEX", "LYCRA", "ELAST", "POLY", "MELANGE", "REACTIVE", "COOLTEX", "RECYCLE", "DYED POLY", "MICRO MODAL", "VISCOSE"]):
        return False
    return True

def set_category_key(name: str) -> str:
    return str(name or "").strip().upper()

def _ordered_specs_lookup_values(spec_row: Dict[str, Any]) -> List[Any]:
    """Return values in the same logical order as Excel SPECS!B:EV.

    Excel Set sheet uses VLOOKUP(SortNo, SPECS!B:EV, column_index, FALSE).
    In Supabase synced SPECS we also have technical columns like sync_row_id and sr_no
    before dev_sorts. Those must NOT be counted, otherwise Set row index 5 points
    to Finish GSM instead of the first yarn percentage column.
    """
    if not isinstance(spec_row, dict):
        return []
    keys = list(spec_row.keys())
    norm_keys = [norm_col(k) for k in keys]

    # SPECS!B starts from Dev. Sorts / dev_sorts, not sr_no or sync_row_id.
    start = 0
    for wanted in ("dev_sorts", "sort_no", "sort", "dev_sort", "sorts"):
        if wanted in norm_keys:
            start = norm_keys.index(wanted)
            break

    ignore = {"sync_row_id", "sr_no", "created_at", "updated_at", "data"}
    ordered = []
    for k in keys[start:]:
        if norm_col(k) in ignore:
            continue
        ordered.append(spec_row.get(k, ""))
    return ordered

def get_spec_pct_by_set_index(spec_row: Dict[str, Any], set_index: int, particular: str = "", yarn: str = "") -> float:
    """Excel Set sheet D(row): VLOOKUP(sort, SPECS!B:EV, F(row), FALSE).

    Important fix: Supabase has extra columns before Dev. Sorts, so the lookup array
    is rebuilt from dev_sorts onward. This makes polyester, spandex, melange,
    kora/grey, reactive, cooltex, recycle, dyed poly, micro modal and viscose
    calculate the same way as the offline Excel-source formula.
    """
    if not isinstance(spec_row, dict):
        return 0.0

    values = _ordered_specs_lookup_values(spec_row)
    idx = int(set_index) - 1
    if 0 <= idx < len(values):
        v = to_float(values[idx], 0)
        # 0 is a valid percentage, but for fallback matching we only return when non-zero.
        if v != 0:
            return v

    # fallback by matching normalized yarn/header names in case Supabase column order changes
    yarn_norm = norm_col(str(yarn).replace("S ", "s "))
    part_norm = norm_col(particular)
    for k in spec_row.keys():
        nk = norm_col(k)
        if yarn_norm and (nk == yarn_norm or yarn_norm in nk or nk in yarn_norm):
            v = to_float(spec_row.get(k), 0)
            if v != 0:
                return v

    # fallback for category in headers if any
    for k in spec_row.keys():
        nk = norm_col(k)
        if part_norm and (part_norm in nk or nk in part_norm):
            v = to_float(spec_row.get(k), 0)
            if v != 0:
                return v
    return 0.0

def calculate_set_sheet_costs(spec_row: Dict[str, Any], green: Dict[str, float] | None = None) -> Dict[str, float]:
    """Replicates Excel Set sheet formulas for green-cell driven costing.
    Green cells with % are treated as percentages. Green cells with amount are used as amount.
    """
    green = green or {}
    category_amounts = {}
    category_pcts = {}
    cotton_prices_with_pct = []

    static_products = {str(yarn).strip().upper() for _, yarn, _, _ in SET_YARN_ROWS}
    cotton_amount_total = 0.0

    # If Offline has created a new sort using software-added yarns (PKS/SPS),
    # online Supabase may not have those dynamic SPECS columns. For such sorts,
    # use the same offline-added yarn rows directly and do not let old Set index
    # columns pick a wrong static yarn.
    extra_rows_for_sort = extra_sort_yarn_items_for_specs(spec_row)
    skip_static_set_for_extra_sort = bool(extra_rows_for_sort)

    if not skip_static_set_for_extra_sort:
        for particular, yarn, default_price, set_idx in SET_YARN_ROWS:
            pct = get_spec_pct_by_set_index(spec_row, set_idx, particular, yarn)
            live_price = rm_price_lookup(yarn, particular)
            price = live_price if live_price else float(default_price or 0)
            amount = price * pct / 100.0
            cat = set_category_key(particular)
            category_amounts[cat] = category_amounts.get(cat, 0.0) + amount
            category_pcts[cat] = category_pcts.get(cat, 0.0) + pct
            if cat in COTTON_SET_CATEGORIES:
                cotton_amount_total += amount

    # Extra/new SPECS yarn columns like PKS/SPS are not in the old Excel Set list.
    # If RM Price has them, calculate them also. This is the key fix for synced new sorts.
    skip_dynamic = {
        "sync_row_id","sr_no","dev_sorts","sort_no","sort","dev_sort","sorts","structure",
        "finish_gsm","finish_width","finish_widt","gsm","width","width_cms","weight_gsm","width_inch",
        "created_at","updated_at","data"
    }
    for col, val in (spec_row or {}).items():
        c = norm_col(col)
        if c in skip_dynamic:
            continue
        pct = to_float(val, 0)
        if pct <= 0 or pct > 1000:
            continue
        product = spec_col_to_product(col)
        if str(product).strip().upper() in static_products:
            continue
        detail = rm_price_lookup_detail(product)
        if not detail:
            continue
        price, rm_particular, rm_product = detail
        amount = price * pct / 100.0
        cat = set_category_key(rm_particular)
        if not cat:
            cat = "% OF INDIGO"
        # New cotton yarn names like PKS/SPS/First Flight are cotton-type unless clearly non-cotton.
        if cat not in {"% WHITE POLY","% BLACK POLY","% OF LYCRA","% MELANGE","KORA / GREY","REACTIVE","COOLTEX","RECYCLE","DYED POLY","MICRO MODAL","VISCOSE"}:
            cat = "% OF INDIGO"
        category_amounts[cat] = category_amounts.get(cat, 0.0) + amount
        category_pcts[cat] = category_pcts.get(cat, 0.0) + pct
        if cat in COTTON_SET_CATEGORIES:
            cotton_amount_total += amount

    # If SPECS came from Offline Bulk Upload and online schema does not expose
    # software-added columns (PKS/SPS), add those yarn rows here.
    # For extra sorts, this is the master calculation source, matching offline.
    if extra_rows_for_sort or cotton_amount_total <= 0.000001:
        for particular, yarn, pct, default_price in (extra_rows_for_sort or extra_sort_yarn_items_for_specs(spec_row)):
            live_price = rm_price_lookup(yarn, particular)
            price = live_price if live_price else float(default_price or 0)
            pct = to_float(pct, 0)
            amount = price * pct / 100.0
            cat = set_category_key(particular)
            if _is_cotton_like_particular(particular, yarn):
                cat = "% OF INDIGO"
            category_amounts[cat] = category_amounts.get(cat, 0.0) + amount
            category_pcts[cat] = category_pcts.get(cat, 0.0) + pct
            if cat in COTTON_SET_CATEGORIES:
                cotton_amount_total += amount

    cotton_pct_total = sum(v for k, v in category_pcts.items() if k in COTTON_SET_CATEGORIES)
    cotton_yarn = (cotton_amount_total / cotton_pct_total * 100.0) if cotton_pct_total else 0.0

    # Green cells from Excel Set/Cost Sheet
    waste_pct = to_float(green.get("wastage_pct"), 0.0)             # B6 / Waste %
    dyeing_amt = to_float(green.get("dyeing_cost_rs"), 0.0)         # B7 / Dyeing amount
    knitting_amt = to_float(green.get("knitting_processing_cost"), 90.0)  # B22 amount
    wastage_after_pct = to_float(green.get("wastage_after_knitting_pct"), 10.0)  # B23 %
    margin_pct = to_float(green.get("margin_pct"), 10.0)            # B25 %
    discount_amt = to_float(green.get("discount_if_any"), 0.0)      # I2 amount
    currency_rate = to_float(green.get("currency_rate"), 87.0)      # I1 amount
    freight_amt = to_float(green.get("freight_inr_per_kg"), 15.0)   # I15 amount
    commission_pct = to_float(green.get("commission_pct"), 5.0)     # H16 %
    lc_days = to_float(green.get("lc_days_interest"), 0.0)          # H17 days/percent basis from sheet

    dyed_yarn_cost = cotton_yarn + (cotton_yarn * waste_pct / 100.0) + dyeing_amt
    waste_amt = cotton_yarn * waste_pct / 100.0
    cotton_dyed_prop = dyed_yarn_cost * cotton_pct_total / 100.0

    polyester_cost = category_amounts.get("% WHITE POLY", 0.0) + category_amounts.get("% BLACK POLY", 0.0)
    spandex_cost = category_amounts.get("% OF LYCRA", 0.0)
    melange_cost = category_amounts.get("% MELANGE", 0.0)
    kora_yarn_cost = category_amounts.get("KORA / GREY", 0.0)
    reactive_yarn_cost = category_amounts.get("REACTIVE", 0.0)
    cooltex_yarn_cost = category_amounts.get("COOLTEX", 0.0)
    recycle_yarn_cost = category_amounts.get("RECYCLE", 0.0)
    dyed_poly_yarn_cost = category_amounts.get("DYED POLY", 0.0)
    micro_modal = category_amounts.get("MICRO MODAL", 0.0)
    viscose = category_amounts.get("VISCOSE", 0.0)

    raw_material = sum([
        cotton_dyed_prop, polyester_cost, spandex_cost, melange_cost, kora_yarn_cost,
        reactive_yarn_cost, cooltex_yarn_cost, recycle_yarn_cost, dyed_poly_yarn_cost,
        micro_modal, viscose
    ])
    wastage_after_amt = (raw_material + knitting_amt) * wastage_after_pct / 100.0
    costing = raw_material + knitting_amt + wastage_after_amt
    margin_amt = costing * margin_pct / 100.0
    selling_price = costing + margin_amt
    price_per_kg_inr = selling_price
    commission_amt = price_per_kg_inr * commission_pct / 100.0
    lc_interest_pct = (18.0 / 365.0) * lc_days
    lc_interest_amt = price_per_kg_inr * lc_interest_pct / 100.0
    total_inr = (price_per_kg_inr - discount_amt) + freight_amt + commission_amt + lc_interest_amt
    total_usd = total_inr / currency_rate if currency_rate else 0.0

    gsm = to_float(getv(spec_row, "finish_gsm", "gsm", "weight_gsm"), 0.0)
    width = to_float(getv(spec_row, "finish_width", "finish_widt", "width", "width_cms"), 0.0)
    width_inch = width / 2.54 if width else 0.0
    linear_mtrs = 1000.0 / (gsm * (width / 100.0)) if gsm and width else 0.0
    linear_yds = linear_mtrs * 1.09 if linear_mtrs else 0.0
    price_usd_mtrs = total_usd / linear_mtrs if total_usd and linear_mtrs else 0.0
    price_usd_yds = total_usd / linear_yds if total_usd and linear_yds else 0.0

    return {
        "cotton_yarn_costing": cotton_yarn,
        "wastage": waste_amt,
        "wastage_pct_green": waste_pct,
        "dyeing_cost_rs": dyeing_amt,
        "dyed_yarn_cost_rs": dyed_yarn_cost,
        "cotton_dyed_proportion_cost": cotton_dyed_prop,
        "polyester_cost": polyester_cost,
        "spandex_cost": spandex_cost,
        "melange_cost": melange_cost,
        "kora_yarn_cost": kora_yarn_cost,
        "reactive_yarn_cost": reactive_yarn_cost,
        "cooltex_yarn_cost": cooltex_yarn_cost,
        "recycle_yarn_cost": recycle_yarn_cost,
        "dyed_poly_yarn_cost": dyed_poly_yarn_cost,
        "micro_modal": micro_modal,
        "viscose": viscose,
        "raw_material_cost": raw_material,
        "knittng__processing_cost": knitting_amt,
        "wastage_after_knitting_pct": wastage_after_pct,
        "wastage_2": wastage_after_amt,
        "costing": costing,
        "margin": margin_amt,
        "margin_pct": margin_pct,
        "selling_price": selling_price,
        "price_per_kg_inr": price_per_kg_inr,
        "currency_rate": currency_rate,
        "discount_if_any": discount_amt,
        "freight_inr_per_kg": freight_amt,
        "commission_pct": commission_pct,
        "commission": commission_amt,
        "lc_days_interest": lc_days,
        "lc_interest_amount": lc_interest_amt,
        "total_cost_pricefreightcomlc_int_inr__kg": total_inr,
        "total_cost_usd__kg": total_usd,
        "price_usdkg": total_usd,
        "linear_mtrskg": linear_mtrs,
        "linear_ydgskg": linear_yds,
        "price_usdmtrs": price_usd_mtrs,
        "price_usdyds": price_usd_yds,
        "width_cms": width,
        "width_inch": width_inch,
        "weight_gsm": gsm,
    }

def spec_col_to_product(col: str) -> str:
    """Convert SPECS database column name to yarn/product name used in RM Price.
    Example: 30s_kcw -> 30S KCW, 100_d -> 100 D.
    """
    c = str(col or "").strip().lower()
    c = c.replace("col_", "")
    c = c.replace("_", " ").replace("-", " ").strip()
    c = " ".join(c.split())
    out = c.upper()
    # common textile spellings
    out = out.replace(" KCW", " KCW").replace(" CCW", " CCW")
    out = out.replace(" D", " D")
    return out

def _clean_rm_text(v: Any) -> str:
    return " ".join(str(v or "").strip().upper().replace("-", " ").replace("_", " ").split())

def rm_price_lookup_detail(product: str, particular: str = ""):
    """Return (price, particulars, product) from merged live RM tables.
    Exact product+particular first, then product-only, then loose normalized match.
    """
    try:
        df = load_rm()
        if df.empty:
            return None
        prod_norm = _clean_rm_text(product)
        part_norm = _clean_rm_text(particular)
        if not prod_norm:
            return None
        price_col = "price_numeric" if "price_numeric" in df.columns else ("price" if "price" in df.columns else "")
        if not price_col or "product" not in df.columns:
            return None
        x = df.copy()
        x["_prod"] = x["product"].map(_clean_rm_text)
        x["_part"] = x.get("particulars", pd.Series([""]*len(x))).map(_clean_rm_text)
        m = x[x["_prod"] == prod_norm]
        if part_norm and not m.empty:
            m2 = m[m["_part"] == part_norm]
            if not m2.empty:
                rr = m2.iloc[-1]
                return (to_float(rr.get(price_col), 0), str(rr.get("particulars", "")), str(rr.get("product", "")))
        if not m.empty:
            rr = m.iloc[-1]
            return (to_float(rr.get(price_col), 0), str(rr.get("particulars", "")), str(rr.get("product", "")))
        # loose matching: handles PKS/SPS and spacing differences
        m = x[x["_prod"].apply(lambda p: p == prod_norm or prod_norm in p or p in prod_norm)]
        if not m.empty:
            rr = m.iloc[-1]
            return (to_float(rr.get(price_col), 0), str(rr.get("particulars", "")), str(rr.get("product", "")))
        # very loose alphanumeric match: 24S KCW == 24S_KCW, SPS == sps, PKS == pks
        prod_alnum = ''.join(ch for ch in prod_norm if ch.isalnum())
        if prod_alnum:
            m = x[x["_prod"].apply(lambda p: ''.join(ch for ch in str(p).upper() if ch.isalnum()) == prod_alnum)]
            if not m.empty:
                rr = m.iloc[-1]
                return (to_float(rr.get(price_col), 0), str(rr.get("particulars", "")), str(rr.get("product", "")))
        return None
    except Exception:
        return None

def rm_price_lookup(product: str, particular: str = "") -> float:
    """Find RM price by product/yarn name from merged Supabase RM tables."""
    d = rm_price_lookup_detail(product, particular)
    return to_float(d[0], 0) if d else 0.0

def specs_cost_row_from_specs(spec_row: Dict[str, Any], sort_no: str) -> Dict[str, Any]:
    """Build full Cost Sheet calculation for a sort that exists only in SPECS.
    This now follows Excel Set sheet: percentage green cells as percentage,
    amount green cells as amount, and category cost formulas via Set rows.
    """
    r = dict(spec_row or {})
    gsm = to_float(getv(r, "finish_gsm", "gsm", "weight_gsm"), 0)
    width = to_float(getv(r, "finish_width", "finish_widt", "width", "width_cms"), 0)

    green_defaults = {
        "wastage_pct": to_float(getv(r, "wastage_pct", "waste_pct_green"), 3.0),
        "dyeing_cost_rs": to_float(getv(r, "dyeing_cost_rs"), 0.0),
        "knitting_processing_cost": to_float(getv(r, "knittng__processing_cost", "knitting_processing_cost"), 90.0),
        "wastage_after_knitting_pct": to_float(getv(r, "wastage_after_knitting_pct"), 10.0),
        "margin_pct": to_float(getv(r, "margin_pct"), 10.0),
        "discount_if_any": to_float(getv(r, "discount_if_any"), 0.0),
        "currency_rate": to_float(getv(r, "currency_rate"), 87.0),
        "freight_inr_per_kg": to_float(getv(r, "freight_inr_per_kg"), 15.0),
        "commission_pct": to_float(getv(r, "commission_pct"), 5.0),
        "lc_days_interest": to_float(getv(r, "lc_days_interest", "lc_days_interest_amount"), 0.0),
    }
    calc = calculate_set_sheet_costs(r, green_defaults)

    def z(v, dec=2):
        try:
            return round(float(v), dec)
        except Exception:
            return 0

    out = {
        "dev_sorts": clean_sort_value(sort_no),
        "sort_no": clean_sort_value(sort_no),
        "_source": "specs",
        "structure": getv(r, "structure"),
        "finish_gsm": z(gsm, 0),
        "finish_width": z(width, 0),
    }
    for k, v in calc.items():
        if k in ["finish_gsm", "finish_width"]:
            continue
        out[k] = z(v, 2)
    # If old uploaded/synced price fields exist and are non-zero, keep them only as a fallback.
    for src, dest in [
        ("sales_price", "selling_price"), ("selling_price", "selling_price"),
        ("local_cost", "price_per_kg_inr"), ("price_per_kg_inr", "price_per_kg_inr"),
        ("export_price_fc", "total_cost_usd__kg"), ("price_usdkg", "price_usdkg")
    ]:
        val = to_float(getv(r, src), 0)
        if val and not to_float(out.get(dest), 0):
            out[dest] = z(val, 2)
    return out


def get_sort_row(sort_no:str)->Dict[str,Any]:
    target=clean_sort_value(sort_no)
    # For offline-added/bulk-upload sorts, always calculate from live SPECS first
    # so PKS/SPS and green-cell formula logic are applied online.
    if target in ONLINE_EXTRA_SORT_YARN_ITEMS:
        sdf_first = load_specs()
        if not sdf_first.empty:
            c_first = next((x for x in ["dev_sorts","sort_no","sort"] if x in sdf_first.columns), group_sort_col(sdf_first))
            if c_first in sdf_first.columns:
                m_first = sdf_first[sdf_first[c_first].apply(clean_sort_value)==target]
                if not m_first.empty:
                    return specs_cost_row_from_specs(m_first.iloc[0].to_dict(), target)
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
            return specs_cost_row_from_specs(r, target)
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
        cols = st.columns(module_weights + [0.95, 0.72], gap="small")
        for i, m in enumerate(visible):
            btn_type = "primary" if st.session_state.get("module") == m else "secondary"
            if cols[i].button(m, key=f"nav_btn_{m}", type=btn_type, use_container_width=True):
                st.session_state.module = m
                st.rerun()
        if cols[-2].button("Fetch Supabase", key="nav_fetch_supabase_btn", use_container_width=True):
            fetch_live_supabase_now()
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
def derive_waste_pct(row:Dict[str,Any])->float:
    cotton=to_float(getv(row,"cotton_yarn_costing"),0)
    waste=to_float(getv(row,"wastage"),0)
    return round(waste/cotton*100,2) if cotton and waste else 0.0

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
    """Apply What-If values using the same Excel Set sheet formula logic.
    Waste %, Knit Waste %, Commission %, Margin % are percentages.
    Dyeing Cost, Knitting + Processing, Freight, Discount, LC are amounts/days as per Excel green cells.
    """
    r=dict(row)
    green = {
        "wastage_pct": to_float(wf.get("wastage"), to_float(getv(r,"wastage_pct_green"), derive_waste_pct(r))),
        "dyeing_cost_rs": to_float(wf.get("dyeing_cost_rs"), to_float(getv(r,"dyeing_cost_rs"),0)),
        "knitting_processing_cost": to_float(wf.get("knittng__processing_cost"), to_float(getv(r,"knittng__processing_cost"),90)),
        "wastage_after_knitting_pct": to_float(wf.get("wastage_after_knitting_pct"), derive_after_knitting_pct(r)),
        "discount_if_any": to_float(wf.get("discount_if_any"), to_float(getv(r,"discount_if_any"),0)),
        "currency_rate": to_float(wf.get("currency_rate"), to_float(getv(r,"currency_rate"),87)),
        "freight_inr_per_kg": to_float(wf.get("freight_inr_per_kg"), to_float(getv(r,"freight_inr_per_kg"),0)),
        "commission_pct": to_float(wf.get("commission_pct"), derive_commission_pct(r)),
        "lc_days_interest": to_float(wf.get("lc_days_interest"), to_float(getv(r,"lc_days_interest","lc_days_interest_amount","lc_days__interest_15_pm"),0)),
        "margin_pct": to_float(wf.get("margin_pct"), derive_margin_pct(r)),
    }
    # For SPECS-origin rows, recalculate directly from Set-sheet mapping.
    if str(getv(r, "_source", default="")).lower() == "specs" or ("sync_row_id" in r and not to_float(getv(r,"raw_material_cost"),0)):
        calc = calculate_set_sheet_costs(r, green)
    else:
        # Existing group_costing rows already store calculated yarn-category values.
        # Recalculate green-cell dependent rows from stored category values.
        cotton_yarn=to_float(getv(r,"cotton_yarn_costing"),0)
        waste_amt=cotton_yarn*green["wastage_pct"]/100.0
        dyeing=green["dyeing_cost_rs"]
        dyed_yarn=cotton_yarn+waste_amt+dyeing
        cotton_pct = 0.0
        old_prop=to_float(getv(r,"cotton_dyed_proportion_cost"),0)
        old_dyed=to_float(getv(r,"dyed_yarn_cost_rs"),0)
        if old_prop and old_dyed:
            cotton_pct = old_prop/old_dyed*100.0
        else:
            cotton_pct = 100.0
        cotton_prop=dyed_yarn*cotton_pct/100.0
        raw=cotton_prop
        for k in ['polyester_cost','spandex_cost','melange_cost','kora_yarn_cost','reactive_yarn_cost','cooltex_yarn_cost','recycle_yarn_cost','dyed_poly_yarn_cost','micro_modal','viscose']:
            raw += to_float(getv(r,k),0)
        base_cost=raw+green["knitting_processing_cost"]
        waste_after_amt=base_cost*green["wastage_after_knitting_pct"]/100.0
        costing=base_cost+waste_after_amt
        margin_amt=costing*green["margin_pct"]/100.0
        selling=costing+margin_amt
        price_per_kg=selling
        commission_amt=price_per_kg*green["commission_pct"]/100.0
        lc_interest_pct=(18.0/365.0)*green["lc_days_interest"]
        lc_interest_amt=price_per_kg*lc_interest_pct/100.0
        total_inr=(price_per_kg-green["discount_if_any"])+green["freight_inr_per_kg"]+commission_amt+lc_interest_amt
        price_usd=total_inr/green["currency_rate"] if green["currency_rate"] else 0
        lm=to_float(getv(r,"linear_mtrskg"),0)
        ly=to_float(getv(r,"linear_ydgskg"),0)
        calc={
            'wastage':waste_amt, 'wastage_pct_green':green["wastage_pct"], 'dyeing_cost_rs':dyeing, 'dyed_yarn_cost_rs':dyed_yarn,
            'cotton_dyed_proportion_cost':cotton_prop, 'raw_material_cost':raw,
            'knittng__processing_cost':green["knitting_processing_cost"], 'wastage_after_knitting_pct':green["wastage_after_knitting_pct"],
            'wastage_2':waste_after_amt, 'costing':costing, 'margin':margin_amt, 'margin_pct':green["margin_pct"],
            'selling_price':selling, 'price_per_kg_inr':price_per_kg, 'currency_rate':green["currency_rate"], 'discount_if_any':green["discount_if_any"],
            'freight_inr_per_kg':green["freight_inr_per_kg"], 'commission':commission_amt, 'commission_pct':green["commission_pct"],
            'lc_days_interest':green["lc_days_interest"], 'lc_interest_amount':lc_interest_amt,
            'total_cost_pricefreightcomlc_int_inr__kg':total_inr, 'total_cost_usd__kg':price_usd, 'price_usdkg':price_usd,
            'price_usdmtrs':price_usd/lm if lm else to_float(getv(r,'price_usdmtrs'),0),
            'price_usdyds':price_usd/ly if ly else to_float(getv(r,'price_usdyds'),0),
        }
    r.update(calc)
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



def composition_rows_from_specs(spec_row: Dict[str, Any], sort_no: str) -> List[tuple]:
    """Online Yarn / Composition Summary same as offline.
    Shows PKS/SPS and other new yarns with live RM Price and Calc Value.
    """
    rows=[]
    seen=set()
    for particular, yarn, pct, default_price in extra_sort_yarn_items_for_specs(spec_row):
        live = rm_price_lookup(yarn, particular)
        price = live if live else to_float(default_price, 0)
        calc = price * to_float(pct, 0) / 100.0 if price else 0
        rows.append((particular, yarn, price, pct, calc, "online-extra"))
        seen.add((_clean_rm_text(particular), _clean_rm_text(yarn)))

    skip = {
        "sync_row_id","sr_no","dev_sorts","sort_no","sort","dev_sort","sorts","structure",
        "finish_gsm","finish_width","finish_widt","gsm","width","width_cms","weight_gsm","width_inch",
        "local_cost","sales_price","selling_price","price","price_per_kg_inr","costing",
        "export_cost_inr","export_price_fc","price_usdkg","price_usdmtrs","price_usdyds",
        "total_cost_usd__kg","total_cost_pricefreightcomlc_int_inr__kg",
        "created_at","updated_at","data","cotton","poly","tencel","spandex"
    }
    for col, val in (spec_row or {}).items():
        c = norm_col(col)
        if c in skip:
            continue
        pct = to_float(val, 0)
        if pct <= 0 or pct > 1000:
            continue
        yarn = spec_col_to_product(col)
        detail = rm_price_lookup_detail(yarn)
        if not detail:
            continue
        price, particular, rm_product = detail
        if not particular:
            particular = "% OF INDIGO"
        sig=(_clean_rm_text(particular), _clean_rm_text(rm_product or yarn))
        if sig in seen:
            continue
        calc = price * pct / 100.0
        rows.append((particular, rm_product or yarn, price, pct, calc, col))
        seen.add(sig)

    if not rows:
        for particular, yarn, default_price, set_idx in SET_YARN_ROWS:
            pct = get_spec_pct_by_set_index(spec_row, set_idx, particular, yarn)
            if pct <= 0:
                continue
            price = rm_price_lookup(yarn, particular) or float(default_price or 0)
            calc = price * pct / 100.0 if price else 0
            rows.append((particular, yarn, price, pct, calc, set_idx))

    cotton_pct = sum(to_float(r[3],0) for r in rows if _is_cotton_like_particular(r[0], r[1]))
    spandex_pct = sum(to_float(r[3],0) for r in rows if any(x in (str(r[0])+str(r[1])).upper() for x in ["LYCRA","SPANDEX","ELAST"]))
    if cotton_pct:
        rows.append(("% TOTAL COMPOSITION", "Cotton", "", cotton_pct, "", ""))
    if spandex_pct:
        rows.append(("% TOTAL COMPOSITION", "Spandex", "", spandex_pct, "", ""))
    return rows

def html_composition_table(rows: List[tuple]) -> str:
    if not rows:
        return ""
    trs=[]
    for particular, yarn, price, pct, calc, spec_col in rows:
        ptxt=str(particular)
        bg = "#d7df00" if "TOTAL COMPOSITION" in ptxt.upper() else ("#cf79a8" if "LYCRA" in ptxt.upper() else ("#d8d8d8" if "KORA" in ptxt.upper() or "GREY" in ptxt.upper() else "#c8d6ef"))
        vals=[ptxt, yarn, fmt(price), fmt(pct), fmt(calc), spec_col]
        tds="".join([f'<td style="border:1px solid #333;padding:3px 6px;background:{bg};font-weight:700;">{html.escape(str(v))}</td>' for v in vals])
        trs.append(f"<tr>{tds}</tr>")
    trs_html = "".join(trs)
    return f"""<div style='border:1px solid #333;margin-top:8px;background:white;'>
      <div style='font-weight:900;color:#083b5f;padding:3px 6px;'>Yarn / Composition Summary</div>
      <table style='width:100%;border-collapse:collapse;font-size:12px;'>
        <tr style='background:#163b73;color:white;font-weight:900;'><th>Particular</th><th>Yarn</th><th>Yarn Price</th><th>%</th><th>Calc Value</th><th>Specs Column</th></tr>
        {trs_html}
      </table>
    </div>"""

# ---------- pages ----------
def cost_sheet_page():
    header("Costing")
    sorts=sort_options()
    # Small live-sync status. This confirms online app is reading Supabase, not only GitHub CSV.
    specs_count = st.session_state.get("sb_count_specs", 0)
    specs_err = st.session_state.get("sb_error_specs", "")
    if specs_err:
        st.caption(f"Supabase SPECS live read error: {specs_err}")
    elif specs_count:
        st.caption(f"Supabase SPECS live rows: {specs_count} | key: {st.session_state.get('sb_key_used_specs','')}")
    if not sorts:
        st.error("No sort data found from Supabase or GitHub CSV.")
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
        'wastage':to_float(getv(row,'wastage_pct_green'), derive_waste_pct(row)),
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
        ("Polyester Cost",getv(row,'polyester_cost')),("Spandex Cost",getv(row,'spandex_cost')),("Melange Cost",getv(row,'melange_cost')),
        ("Kora Yarn Cost",getv(row,'kora_yarn_cost')),("Reactive Yarn Cost",getv(row,'reactive_yarn_cost')),("Cooltex Yarn Cost",getv(row,'cooltex_yarn_cost')),
        ("Recycle Yarn Cost",getv(row,'recycle_yarn_cost')),("Dyed Poly Yarn Cost",getv(row,'dyed_poly_yarn_cost')),("Micro Modal",getv(row,'micro_modal')),("Viscose",getv(row,'viscose')),
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
    try:
        st.markdown(html_composition_table(composition_rows_from_specs(base, sort)), unsafe_allow_html=True)
    except Exception:
        pass
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
