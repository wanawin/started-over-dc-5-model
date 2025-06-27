import streamlit as st
import numpy as np
import os, unicodedata, re
from itertools import product
import pandas as pd

# ==============================
# Load and Parse Ranked Filters (includes manual, optional, operational)
# ==============================
@st.cache_data
def load_ranked_filters(path: str):
    df = pd.read_csv(path)
    # Auto-detect essential columns
    cols = df.columns.tolist()
    name_col = next((c for c in cols if 'name' in c.lower()), None)
    type_col = next((c for c in cols if 'type' in c.lower()), None)
    logic_col = next((c for c in cols if 'logic' in c.lower()), None)
    action_col = next((c for c in cols if 'action' in c.lower()), None)
    missing = [label for label,col in [('name',name_col),('type',type_col),('logic',logic_col),('action',action_col)] if col is None]
    if missing:
        st.error(f"Filters CSV missing required columns: {missing}")
        return []
    # Rename and normalize
    df = df.rename(columns={name_col: 'name', type_col: 'type', logic_col: 'logic', action_col: 'action'})
    df[['name','type','logic','action']] = df[['name','type','logic','action']].fillna('')
    def normalize_name(raw: str) -> str:
        s = unicodedata.normalize('NFKC', raw)
        s = re.sub(r'^\s*\d+[\.)]\s*', '', s)
        s = s.replace('≥','>=').replace('≤','<=').replace('\u2192','->')
        s = re.sub(r'[–—]','-', s)
        return re.sub(r'\s+', ' ', s.strip()).lower()
    df['name'] = df['name'].map(normalize_name)
    df = df[df['name'] != '']
    df = df.drop_duplicates(subset=['name'])
    return df[['name','type','logic','action']].to_dict(orient='records')

# ==============================
# Auto-filter stubs
# ==============================
def apply_primary_percentile(combos):
    # TODO: implement static percentile zones filtering
    return combos, []

def apply_deduplication(combos):
    seen, unique, removed = set(), [], []
    for c in combos:
        if c not in seen:
            seen.add(c); unique.append(c)
        else:
            removed.append(c)
    return unique, removed

def apply_comparison_filter(enum_pool, seed_pool):
    keep = [c for c in enum_pool if c in seed_pool]
    removed = [c for c in enum_pool if c not in keep]
    return keep, removed

def apply_trap_v3(pool, hot_digits, cold_digits, due_digits):
    # TODO: implement Trap V3 ranking logic
    return pool, []

# ==============================
# Generate seed-based combos
# ==============================
def generate_combinations(seed, method="2-digit pair"):
    all_digits = '0123456789'
    combos = set()
    seed_str = str(seed)
    if len(seed_str) < 2:
        return []
    if method == "1-digit":
        for d in seed_str:
            for p in product(all_digits, repeat=4):
                combos.add(''.join(sorted(d + ''.join(p))))
    else:
        pairs = set(''.join(sorted((seed_str[i], seed_str[j]))) for i in range(len(seed_str)) for j in range(i+1, len(seed_str)))
        for pair in pairs:
            for p in product(all_digits, repeat=3):
                combos.add(''.join(sorted(pair + ''.join(p))))
    return sorted(combos)

# ==============================
# Check permutation helper
# ==============================
def permutation_exists(combo: str, pool: list) -> bool:
    key = ''.join(sorted(combo.strip()))
    return key in pool

# ==============================
# Streamlit App
# ==============================
st.set_page_config(layout="wide")
st.title("DC-5 Midday Blind Predictor with Full Auto and Manual Filters")

# ------------------------------
# Sidebar: Inputs and Settings
# ------------------------------
st.sidebar.header("🔧 Inputs and Settings")
prev_seed = st.sidebar.text_input("Previous 5-digit seed:")
seed = st.sidebar.text_input("Current 5-digit seed:")
hot_digits = [d for d in st.sidebar.text_input("Hot digits (comma-separated):").replace(' ', '').split(',') if d]
cold_digits = [d for d in st.sidebar.text_input("Cold digits (comma-separated):").replace(' ', '').split(',') if d]
due_digits = [d for d in st.sidebar.text_input("Due digits (comma-separated):").replace(' ', '').split(',') if d]
method = st.sidebar.selectbox("Generation Method:", ["1-digit", "2-digit pair"])
enable_trap = st.sidebar.checkbox("Enable Trap V3 Ranking")

# ------------------------------
# Main: Filter Selection
# ------------------------------
filters = load_ranked_filters('Filters_Ranked_Eliminations.csv')
st.header("🔍 Manual Filters")
if not filters:
    st.error("No filters loaded.")
else:
    n_cols = 3
    cols = st.columns(n_cols)
    filter_states = {}
    filter_info = {}
    for idx, f in enumerate(filters):
        col = cols[idx % n_cols]
        name = f['name']
        premise = f.get('logic') or f.get('action') or ''
        filter_info[name] = premise
        key = f"filter_{idx}"
        checked = col.checkbox(name, key=key)
        col.markdown(f'<span title="{premise}" style="cursor: help;">❔</span>', unsafe_allow_html=True)
        filter_states[name] = checked

# ------------------------------
# Processing Workflow
# ------------------------------
if seed:
    enum_pool = [str(i).zfill(5) for i in range(100000)]
    st.write(f"Step 1: Enumeration — {len(enum_pool)} combos.")
    pct_pool, pct_removed = apply_primary_percentile(enum_pool)
    st.write(f"Step 2: Primary percentile removed {len(pct_removed)}, remaining {len(pct_pool)}.")
    dedup_pool, dedup_removed = apply_deduplication(pct_pool)
    st.write(f"Step 3: Deduplication removed {len(dedup_removed)}, remaining {len(dedup_pool)}.")
    seed_pool = generate_combinations(seed, method)
    st.write(f"Step 4: Seed-generation ({method}) yields {len(seed_pool)} combos.")
    comp_pool, comp_removed = apply_comparison_filter(dedup_pool, seed_pool)
    st.write(f"Step 5: Comparison removed {len(comp_removed)}, remaining {len(comp_pool)}.")
    session_pool = comp_pool
    st.write("Step 6: Manual filters applied")
    for name, active in filter_states.items():
        if active:
            removed = []  # TODO: apply logic
            session_pool = [c for c in session_pool if c not in removed]
            st.write(f"{name} removed {len(removed)}, remaining {len(session_pool)}.")
    if enable_trap:
        trap_pool, trap_removed = apply_trap_v3(session_pool, hot_digits, cold_digits, due_digits)
        session_pool = trap_pool
        st.write(f"Step 7: Trap V3 removed {len(trap_removed)}, remaining {len(session_pool)}.")
    st.write(f"**Final pool: {len(session_pool)} combos.**")
    combo_check = st.text_input("Check permutation of combo:")
    if combo_check:
        found = permutation_exists(combo_check, session_pool)
        st.write(f"Permutation of **{combo_check}** is {'found' if found else 'not found'}.")
else:
    st.info("Enter a 5-digit seed to begin processing.")
