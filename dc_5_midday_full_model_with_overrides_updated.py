import streamlit as st
import numpy as np
import os, unicodedata, re
from itertools import product
import pandas as pd

# ==============================
# Cache and Load Ranked Filters
# ==============================
@st.cache_data
def load_ranked_filters(path: str):
    try:
        df = pd.read_csv(path)
    except Exception as e:
        st.error(f"Failed to load filters CSV: {e}")
        return []
    cols = df.columns.tolist()
    name_col = next((c for c in cols if 'name' in c.lower()), None)
    type_col = next((c for c in cols if 'type' in c.lower()), None)
    logic_col = next((c for c in cols if 'logic' in c.lower()), None)
    action_col = next((c for c in cols if 'action' in c.lower()), None)
    missing = [label for label, col in [('name', name_col), ('type', type_col),
                                        ('logic', logic_col), ('action', action_col)] if col is None]
    if missing:
        st.error(f"Filters CSV missing required columns: {missing}")
        return []
    df = df.rename(columns={name_col: 'name', type_col: 'type',
                             logic_col: 'logic', action_col: 'action'})
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

# Load filters once
filters = load_ranked_filters('Filters_Ranked_Eliminations.csv')

# ==============================
# Auto-filter implementations
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
            seen.add(c); unique.append(c)
        else:
            removed.append(c)
    return unique, removed


def apply_comparison_filter(enum_pool, seed_pool):
    keep = [c for c in enum_pool if c in seed_pool]
    removed = [c for c in enum_pool if c not in keep]
    return keep, removed

# ==============================
# Generate seed-based combos
# ==============================
def generate_combinations(seed, method="2-digit pair"):
    all_digits = '0123456789'; combos = set(); seed_str = str(seed)
    if len(seed_str) < 2:
        return []
    if method == "1-digit":
        for d in seed_str:
            for p in product(all_digits, repeat=4):
                combos.add(''.join(sorted(d + ''.join(p))))
    else:
        pairs = set(''.join(sorted((seed_str[i], seed_str[j])))
                    for i in range(len(seed_str)) for j in range(i+1, len(seed_str)))
        for pair in pairs:
            for p in product(all_digits, repeat=3):
                combos.add(''.join(sorted(pair + ''.join(p))))
    return sorted(combos)

# ==============================
# Manual Filter Logic Helpers
# ==============================
def seed_sum_matches_condition(seed_sum: int, condition_str: str) -> bool:
    s = condition_str.strip()
    if m := re.match(r'[≤<=]\s*(\d+)', s): return seed_sum <= int(m.group(1))
    if m := re.match(r'(?:≥|>=)?\s*(\d+)\s*or\s*higher', s, re.IGNORECASE): return seed_sum >= int(m.group(1))
    if m := re.match(r'(\d+)\s*[–-]\s*(\d+)', s):
        low, high = int(m.group(1)), int(m.group(2))
        return low <= seed_sum <= high
    if s.isdigit(): return seed_sum == int(s)
    return False

def apply_sum_range_filter(combos, min_sum, max_sum):
    keep = [c for c in combos if min_sum <= sum(int(d) for d in c) <= max_sum]
    removed = [c for c in combos if c not in keep]
    return keep, removed

def apply_keep_sum_range_if_seed_sum(combos, seed_sum, min_sum, max_sum, seed_condition_str):
    if seed_sum_matches_condition(seed_sum, seed_condition_str):
        return apply_sum_range_filter(combos, min_sum, max_sum)
    return combos, []

def apply_conditional_seed_contains(combos, seed_digits, seed_digit, required_winners):
    if seed_digit in seed_digits:
        keep, removed = [], []
        for c in combos:
            if any(str(d) in c for d in required_winners): keep.append(c)
            else: removed.append(c)
        return keep, removed
    return combos, []

def detect_filter_pattern(f):
    logic = f.get('logic','') or ''
    low = logic.lower()
    # patterns
    if m := re.search(r'between\s*(\d+)\s*and\s*(\d+).*?if', low):
        return 'conditional_sum_if_seed', {'low': int(m.group(1)), 'high': int(m.group(2)), 'condition': logic}
    if m := re.search(r'sum.*<=\s*(\d+).*>=\s*(\d+)', low) or re.search(r'eliminate if sum\s*<\s*(\d+)\s*or\s*>\s*(\d+)', low):
        return 'sum_range', {'low': int(m.group(1)), 'high': int(m.group(2))}
    if 'seed contains' in low and 'winner must contain' in low:
        sd = int(re.search(r'seed contains\s*(\d+)', low).group(1))
        reqs = [int(x) for x in re.findall(r'(?:contain(?:s)?(?: either)? )?(\d)', low)]
        return 'conditional_seed_contains', {'seed_digit': sd, 'required': reqs}
    return 'unknown', {}

# ==============================
# Permutation Check helper
# ==============================
def permutation_exists(combo: str, pool: list) -> bool:
    return ''.join(sorted(combo.strip())) in {''.join(sorted(c)) for c in pool}

# ==============================
# Streamlit App
# ==============================
st.set_page_config(layout="wide")
st.title("DC-5 Midday Blind Predictor with Full Auto and Manual Filters")

# Sidebar
st.sidebar.header("🔧 Inputs and Settings")
pos_remaining = st.sidebar.empty()

# functions

def update_remaining():
    if 'session_pool' in st.session_state:
        pos_remaining.metric("Remaining Combos", len(st.session_state.session_pool))

# inputs
prev_seed = st.sidebar.text_input("Previous 5-digit seed:")
seed = st.sidebar.text_input("Current 5-digit seed:")
hot_digits = [d for d in st.sidebar.text_input("Hot digits (comma-separated):").replace(' ','').split(',') if d]
cold_digits = [d for d in st.sidebar.text_input("Cold digits (comma-separated):").replace(' ','').split(',') if d]
due_digits = [d for d in st.sidebar.text_input("Due digits (comma-separated):").replace(' ','').split(',') if d]
method = st.sidebar.selectbox("Generation Method:", ["1-digit","2-digit pair"])
enable_trap = st.sidebar.checkbox("Enable Trap V3 Ranking")
combo_check = st.sidebar.text_input("Check permutation of combo:")
# End inputs

# Main pipeline
if seed:
    enum_pool = [str(i).zfill(5) for i in range(100000)]
    st.write(f"Step 1: Enumeration — **{len(enum_pool)}** combos.")
    pct_pool, pct_removed = apply_primary_percentile(enum_pool)
    st.write(f"Step 2: Primary percentile removed **{len(pct_removed)}**, remaining **{len(pct_pool)}**.")
    dedup_pool, dedup_removed = apply_deduplication(pct_pool)
    st.write(f"Step 3: Deduplication removed **{len(dedup_removed)}**, remaining **{len(dedup_pool)}**.")
    seed_pool = generate_combinations(seed, method)
    st.write(f"Step 4: Seed-generation ({method}) yields **{len(seed_pool)}** combos.")
    comp_pool, comp_removed = apply_comparison_filter(dedup_pool, seed_pool)
    st.write(f"Step 5: Comparison removed **{len(comp_removed)}**, remaining **{len(comp_pool)}**.")
    st.session_state.session_pool = comp_pool
    update_remaining()
    st.write(f"**Pool before manual filters: {len(comp_pool)} combos.**")
else:
    st.info("Enter a 5-digit seed to begin processing.")

# Debug pattern detection
if st.sidebar.checkbox("🐞 Debug: Show detected filter patterns"):
    det = [{'name': f['name'], 'pattern': detect_filter_pattern(f)[0], 'params': detect_filter_pattern(f)[1]} for f in filters]
    st.sidebar.dataframe(pd.DataFrame(det))

# Manual filters
st.header("🔍 Manual Filters")
if seed and filters:
    session_pool = st.session_state.get('session_pool', [])
    cols = st.columns(3)
    for idx, f in enumerate(filters):
        col = cols[idx % 3]
        name = f['name']; premise = f.get('logic') or f.get('action') or ''
        checked = col.checkbox(name, key=f"filter_{idx}")
        col.markdown(f'<span title="{premise}" style="cursor: help;">❔</span>', unsafe_allow_html=True)
        if checked:
            pattern, params = detect_filter_pattern(f)
            seed_sum = sum(int(d) for d in seed) if seed.isdigit() else 0
            seed_digits = list(seed)
            if pattern == 'sum_range':
                pool, removed = apply_sum_range_filter(session_pool, params['low'], params['high'])
            elif pattern == 'conditional_sum_if_seed':
                pool, removed = apply_keep_sum_range_if_seed_sum(session_pool, seed_sum, params['low'], params['high'], params['condition'])
            elif pattern == 'conditional_seed_contains':
                pool, removed = apply_conditional_seed_contains(session_pool, seed_digits, params['seed_digit'], params['required'])
            else:
                pool, removed = session_pool, []
            before = len(session_pool)
            session_pool = pool
            st.write(f"{name} removed **{len(removed)}**, remaining **{len(session_pool)}**.")
            if removed:
                with st.expander(f"Show combos removed by '{name}'"):
                    st.write(removed)
            st.session_state.session_pool = session_pool
            update_remaining()
    st.write(f"**Final pool after manual filters: {len(session_pool)} combos.**")
    if enable_trap:
        trap_pool, trap_removed = apply_trap_v3(session_pool, hot_digits, cold_digits, due_digits)
        session_pool = trap_pool
        st.session_state.session_pool = session_pool
        st.write(f"Trap V3 removed **{len(trap_removed)}**, remaining **{len(session_pool)}**.")
        update_remaining()

# Permutation check
if combo_check and 'session_pool' in st.session_state:
    found = permutation_exists(combo_check, st.session_state.session_pool)
    st.sidebar.write(f"Permutation of **{combo_check}** is {'found' if found else 'not found'}.")
