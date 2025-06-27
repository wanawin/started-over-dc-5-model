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
    # normalize column names
    df.columns = [c.lower().strip() for c in df.columns]
    # map synonyms
    rename_map = {}
    for syn in ['filter name', 'filtername']:
        if syn in df.columns:
            rename_map[syn] = 'name'
    df.rename(columns=rename_map, inplace=True)
    required = {'name', 'type', 'logic', 'action'}
    missing = required - set(df.columns)
    if missing:
        st.sidebar.error(f"Missing columns in filters CSV: {missing}")
        return []
    # return list of filter dicts
    return df.to_dict(orient='records')

# Auto-filter stubs

def apply_primary_percentile(combos):
    """
    Retain only combos falling in predetermined high-yield percentile zones
    of the digit-sum metric: 0–26%, 30–35%, 36–43%, 50–60%, 60–70%, 80–83%, 93–94%.
    """
    # compute digit-sum for each combo
    metrics = np.array([sum(int(d) for d in combo) for combo in combos])
    # predefined percentile bands
    bands = [(0, 26), (30, 35), (36, 43), (50, 60), (60, 70), (80, 83), (93, 94)]
    # calculate threshold values for each percentile
    thresholds = {p: np.percentile(metrics, p) for band in bands for p in band}
    keep, removed = [], []
    for combo, m in zip(combos, metrics):
        # check if metric falls in any high-yield band
        in_zone = any(thresholds[low] <= m <= thresholds[high] for (low, high) in bands)
        if in_zone:
            keep.append(combo)
        else:
            removed.append(combo)
    return keep, removed


def apply_deduplication(combos):
    seen = set()
    unique = []
    removed = []
    for c in combos:
        if c not in seen:
            seen.add(c)
            unique.append(c)
        else:
            removed.append(c)
    return unique, removed


def apply_comparison_filter(enum_pool, seed_pool):
    # intersect enumeration and seed-generated pools
    keep = [c for c in enum_pool if c in seed_pool]
    removed = [c for c in enum_pool if c not in keep]
    return keep, removed


def apply_trap_v3(pool, hot_digits, cold_digits, due_digits):
    """Placeholder for Trap V3 ranking logic"""
    # TODO: implement Trap V3
    return pool, []

# Generate seed-based combos

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
        pairs = set(''.join(sorted((seed_str[i], seed_str[j])))
                    for i in range(len(seed_str))
                    for j in range(i+1, len(seed_str)))
        for pair in pairs:
            for p in product(all_digits, repeat=3):
                combos.add(''.join(sorted(pair + ''.join(p))))
    return sorted(combos)

# ==============================
# Streamlit App
# ==============================
st.set_page_config(layout="wide")
st.title("DC-5 Midday Blind Predictor with Full Auto and Manual Filters")

# Sidebar inputs
st.sidebar.header("🔧 Inputs and Settings")
prev_seed = st.sidebar.text_input("Previous 5-digit seed:")
seed = st.sidebar.text_input("Current 5-digit seed:")
hot_digits = [d for d in st.sidebar.text_input("Hot digits (comma-separated):").replace(' ', '').split(',') if d]
cold_digits = [d for d in st.sidebar.text_input("Cold digits (comma-separated):").replace(' ', '').split(',') if d]
due_digits = [d for d in st.sidebar.text_input("Due digits (comma-separated):").replace(' ', '').split(',') if d]
method = st.sidebar.selectbox("Generation Method:", ["1-digit", "2-digit pair"])
enable_trap = st.sidebar.checkbox("Enable Trap V3 Ranking")

# Load filters
filters = load_ranked_filters('Filters_Ranked_Eliminations.csv')
st.sidebar.header("🔍 Filters Overview")
if filters:
    st.sidebar.write(f"Total filters loaded: **{len(filters)}**")
    counts = pd.Series([f['type'] for f in filters]).value_counts()
    for t, cnt in counts.items():
        st.sidebar.write(f"- {t}: {cnt}")
    if len(filters) != 396:
        st.sidebar.warning(f"Expected 396 filters but got {len(filters)}.")
    else:
        st.sidebar.success("All 396 filters present.")
else:
    st.sidebar.error("No filters loaded.")

# Manual filter selection
filter_names = [f['name'] for f in filters]
selected = st.sidebar.multiselect("Select filters to apply:", filter_names)

# Display seeds
if prev_seed:
    st.sidebar.write(f"Prev seed: {prev_seed}")
if seed:
    st.sidebar.write(f"Seed: {seed}")

# ==============================
# Workflow: Auto Filters + Manual
# ==============================
if seed:
    # 1. Full enumeration
    enum_pool = [str(i).zfill(5) for i in range(100000)]
    st.write(f"Step 1: Enumeration — {len(enum_pool)} combos.")

    # 2. Primary percentile
    pct_pool, pct_removed = apply_primary_percentile(enum_pool)
    st.write(f"Step 2: Primary percentile removed {len(pct_removed)}, remaining {len(pct_pool)}.")

    # 3. Deduplication
    dedup_pool, dedup_removed = apply_deduplication(pct_pool)
    st.write(f"Step 3: Deduplication removed {len(dedup_removed)}, remaining {len(dedup_pool)}.")

    # 4. Seed-based generation
    seed_pool = generate_combinations(seed, method)
    st.write(f"Step 4: Seed-generation ({method}) yields {len(seed_pool)} combos.")

    # 5. Comparison filter
    comp_pool, comp_removed = apply_comparison_filter(dedup_pool, seed_pool)
    st.write(f"Step 5: Comparison removed {len(comp_removed)}, remaining {len(comp_pool)}.")

    # 6. Manual filters
    session_pool = comp_pool
    for name in selected:
        f = next((x for x in filters if x['name']==name), None)
        removed = []
        # TODO: implement f['logic'] to filter session_pool
        session_pool = [c for c in session_pool if c not in removed]
        st.write(f"{name} removed {len(removed)}, remaining {len(session_pool)}.")

    # 7. Trap V3
    if enable_trap:
        trap_pool, trap_removed = apply_trap_v3(session_pool, hot_digits, cold_digits, due_digits)
        session_pool = trap_pool
        st.write(f"Step 7: Trap V3 removed {len(trap_removed)}, remaining {len(session_pool)}.")

    st.write(f"**Final pool: {len(session_pool)} combos.**")
else:
    st.info("Enter a 5-digit seed to begin processing.")
