import streamlit as st
import numpy as np
import os, unicodedata, re
from itertools import product
import pandas as pd

# ==============================
# Load and Parse Ranked Filters
# ==============================
@st.cache_data
def load_ranked_filters(path: str):
    df = pd.read_csv(path)
    cols = df.columns.tolist()
    name_col = next((c for c in cols if 'name' in c.lower()), None)
    type_col = next((c for c in cols if 'type' in c.lower()), None)
    logic_col = next((c for c in cols if 'logic' in c.lower()), None)
    action_col = next((c for c in cols if 'action' in c.lower()), None)
    missing = [label for label, col in [('name', name_col), ('type', type_col), ('logic', logic_col), ('action', action_col)] if col is None]
    if missing:
        st.error(f"Filters CSV missing required columns: {missing}")
        return []
    df = df.rename(columns={name_col: 'name', type_col: 'type', logic_col: 'logic', action_col: 'action'})
    df[['name','type','logic','action']] = df[['name','type','logic','action']].fillna('')
    def normalize_name(raw: str) -> str:
        s = unicodedata.normalize('NFKC', raw)
        s = re.sub(r'^\s*\d+[\.)]\s*', '', s)
        s = s.replace('≥','>=').replace('≤','<=').replace('→','->')
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
    metrics = np.array([sum(int(d) for d in combo) for combo in combos])
    bands = [(0,26),(30,35),(36,43),(50,60),(60,70),(80,83),(93,94)]
    thresholds = {p: np.percentile(metrics,p) for band in bands for p in band}
    keep, removed = [], []
    for combo, m in zip(combos, metrics):
        if any(thresholds[low] <= m <= thresholds[high] for low, high in bands):
            keep.append(combo)
        else:
            removed.append(combo)
    return keep, removed


def apply_deduplication(combos):
    seen, unique, removed = set(), [], []
    for c in combos:
        if c not in seen:
            seen.add(c)
            unique.append(c)
        else:
            removed.append(c)
    return unique, removed


def apply_comparison_filter(enum_pool, seed_pool):
    keep = [c for c in enum_pool if c in seed_pool]
    removed = [c for c in enum_pool if c not in keep]
    return keep, removed


def apply_trap_v3(pool, hot_digits, cold_digits, due_digits):
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
# Permutation check helper
# ==============================
def permutation_exists(combo: str, pool: list) -> bool:
    return ''.join(sorted(combo)) in {''.join(sorted(c)) for c in pool}

# ==============================
# Streamlit App
# ==============================
st.set_page_config(layout="wide")
st.title("DC-5 Midday Blind Predictor with Full Auto and Manual Filters")

# ------------------------------
# Manual Filters (Main)
# ------------------------------
# Initialize session_pool for manual filters
session_pool = st.session_state.get('session_pool', [])
st.write(f"**[DEBUG] Starting manual filters with {len(session_pool)} combos**")
filters = load_ranked_filters('Filters_Ranked_Eliminations.csv')
st.header("🔍 Manual Filters")("🔍 Manual Filters")
if seed and filters:
    session_pool = st.session_state.get('session_pool', [])
    cols = st.columns(3)
    for idx, f in enumerate(filters):
        col = cols[idx % 3]
        name = f['name']
        premise = f.get('logic') or f.get('action') or ''
        key = f"filter_{idx}"
        checked = col.checkbox(name, key=key)
        col.markdown(f'<span title="{premise}" style="cursor: help;">❔</span>', unsafe_allow_html=True)
        if checked:
            # Debug: capture before
            before_count = len(session_pool)
            removed = []  # TODO apply logic to populate removed
            # Debug: simulate removal for test
            # e.g., removed = session_pool[:1]
            session_pool = [c for c in session_pool if c not in removed]
            after_count = len(session_pool)
            st.write(f"{name} removed **{len(removed)}**, remaining **{after_count}**.")
            if removed:
                with st.expander(f"Show combos removed by '{name}'"):
                    st.write(removed)
            # Debug ribbon update
            update_remaining()
    # After all manual filters
    st.session_state.session_pool = session_pool
    st.write(f"**Final pool after manual filters: {len(session_pool)} combos.**")
    st.write(f"**Final pool after manual filters: {len(session_pool)} combos.**")
    if enable_trap:
        trap_pool, trap_removed = apply_trap_v3(session_pool, hot_digits, cold_digits, due_digits)
        session_pool = trap_pool
        st.session_state.session_pool = session_pool
        st.write(f"Trap V3 removed **{len(trap_removed)}**, remaining **{len(session_pool)}**.")
        st.write(f"**Final pool: {len(session_pool)} combos.**")

# ------------------------------
# Permutation Check (Sidebar)
# ------------------------------
if combo_check and 'session_pool' in st.session_state:
    found = permutation_exists(combo_check, st.session_state.session_pool)
    st.sidebar.write(f"Permutation of **{combo_check}** is {'found' if found else 'not found'}." )
