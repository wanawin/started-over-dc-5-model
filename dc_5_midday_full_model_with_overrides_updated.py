import streamlit as st
import os, unicodedata, re
from itertools import product
import pandas as pd

# ==============================
# Load and Parse Filters
# ==============================
@st.cache_data
def load_ranked_filters(path: str):
    df = pd.read_csv(path)
    df.columns = [c.lower().strip() for c in df.columns]
    rename_map = {}
    for syn in ['filter name', 'filtername']:
        if syn in df.columns:
            rename_map[syn] = 'name'
    df.rename(columns=rename_map, inplace=True)
    expected = {'name', 'type', 'logic', 'action'}
    missing = expected - set(df.columns)
    if missing:
        st.sidebar.error(f"Filters CSV missing required columns: {missing}")
        return []
    return df.to_dict(orient='records')

# Load filters from external CSV
filters = load_ranked_filters('Filters_Ranked_Eliminations.csv')
filter_count = len(filters)

# ==============================
# Sidebar: Filter Overview
# ==============================
st.sidebar.header("🔍 Filters Overview")
st.sidebar.write(f"Total filters loaded: **{filter_count}**")
if filter_count > 0:
    types = pd.Series([f['type'] for f in filters]).value_counts().to_dict()
    for t, cnt in types.items():
        st.sidebar.write(f"- {t.title()}: {cnt}")
if filter_count != 396:
    st.sidebar.warning(f"Expected 396 filters but loaded {filter_count}. Please verify CSV.")
else:
    st.sidebar.success("All 396 filters loaded.")

# ==============================
# Auto-Filter Stubs
# ==============================
def apply_primary_percentile(combos):
    # TODO: implement primary percentile filtering
    return combos, []

def apply_deduplication(combos):
    # Remove any duplicates
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

# ==============================
# Trap V3 stub
# ==============================
def apply_trap_v3(pool, hot_digits, cold_digits, due_digits):
    # TODO: implement Trap V3 ranking logic
    return pool, []

# ==============================
# UI Inputs
# ==============================
st.set_page_config(layout="wide")
st.title("DC-5 Midday Blind Predictor")
st.sidebar.header("🔧 Inputs and Settings")
prev_seed = st.sidebar.text_input("Previous 5-digit seed:")
seed = st.sidebar.text_input("Current 5-digit seed:")
hot_digits = [d for d in st.sidebar.text_input("Hot digits (comma-separated):").replace(' ', '').split(',') if d]
cold_digits = [d for d in st.sidebar.text_input("Cold digits (comma-separated):").replace(' ', '').split(',') if d]
due_digits = [d for d in st.sidebar.text_input("Due digits (comma-separated):").replace(' ', '').split(',') if d]
method = st.sidebar.selectbox("Generation Method:", ["1-digit", "2-digit pair"])
enable_trap = st.sidebar.checkbox("Enable Trap V3 Ranking")
filter_names = [f.get('name', '') for f in filters]
selected = st.sidebar.multiselect("Select filters to apply (any order):", filter_names)

if prev_seed:
    st.sidebar.write(f"Previous seed: {prev_seed}")
if seed:
    st.sidebar.write(f"Current seed: {seed}")

# ==============================
# Generation and Filtering Flow
# ==============================
if seed:
    # 1. Full enumeration of all combos
    full_enum = [str(i).zfill(5) for i in range(100000)]
    st.write(f"Step 1: Full enumeration — **{len(full_enum)}** combos.")

    # 2. Primary percentile filter
    pct_filtered, pct_removed = apply_primary_percentile(full_enum)
    st.write(f"Step 2: Primary percentile filter removed **{len(pct_removed)}**, remaining **{len(pct_filtered)}**.")

    # 3. Deduplication
    deduped, dedup_removed = apply_deduplication(pct_filtered)
    st.write(f"Step 3: Deduplication removed **{len(dedup_removed)}**, remaining **{len(deduped)}**.")

    # 4. Generate combos based on seed
    if method == "1-digit":
        # Example: each combo must contain at least one digit of the seed
        seed_pool = [c for c in deduped if any(d in c for d in seed)]
    else:
        # 2-digit pair method: at least one adjacent seed pair
        pairs = [seed[i:i+2] for i in range(4)]
        seed_pool = [c for c in deduped if any(p in c for p in pairs)]
    st.write(f"Step 4: Seed-based generation ({method}) yields **{len(seed_pool)}** combos.")

    # 5. Comparison filter: intersect enumeration and seed pools
    session_pool = [c for c in deduped if c in seed_pool]
    removed_cmp = len(deduped) - len(session_pool)
    st.write(f"Step 5: Comparison filter removed **{removed_cmp}**, remaining **{len(session_pool)}**.")

    # 6. Apply selected manual filters in chosen order
    for fname in selected:
        filt = next((f for f in filters if f.get('name') == fname), None)
        if not filt:
            continue
        # TODO: hook up filt['logic'] to actual removal
        removed = []
        session_pool = [c for c in session_pool if c not in removed]
        st.write(f"**{fname}** removed **{len(removed)}**, remaining **{len(session_pool)}**.")

    # 7. Optional Trap V3
    if enable_trap:
        session_pool, trap_removed = apply_trap_v3(session_pool, hot_digits, cold_digits, due_digits)
        st.write(f"Trap V3 removed **{len(trap_removed)}**, remaining **{len(session_pool)}**.")

    st.write(f"**Final pool size:** **{len(session_pool)}** combos.")
else:
    st.info("Enter a current 5-digit seed to generate and filter combos.")

# ==============================
# Footer
# ==============================
st.sidebar.write("🛠️ Workflow: enumeration → percentile → dedupe → seed gen → compare → manual filters → trapV3.")
