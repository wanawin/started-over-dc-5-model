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
    # Normalize column names
    df.columns = [c.lower().strip() for c in df.columns]
    # Rename common synonyms to 'name'
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
    # Convert to list of dicts
    return df.to_dict(orient='records')

# Load filters
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
# Warn if count mismatch
if filter_count != 396:
    st.sidebar.warning(f"Expected 396 filters but loaded {filter_count}. Please verify CSV.")
else:
    st.sidebar.success("All 396 filters loaded.")

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

# Filter selection UI
filter_names = [f.get('name', '') for f in filters]
selected = st.sidebar.multiselect("Select filters to apply (any order):", filter_names)

# Display seeds
if prev_seed:
    st.sidebar.write(f"Previous seed: {prev_seed}")
if seed:
    st.sidebar.write(f"Current seed: {seed}")

# ==============================
# Generation and Filtering
# ==============================
if seed:
    session_pool = [str(i).zfill(5) for i in range(100000)]
    initial_count = len(session_pool)
    st.write(f"Initial pool size: **{initial_count}** combos.")

    # Apply selected filters in chosen order
    for fname in selected:
        filt = next((f for f in filters if f.get('name') == fname), None)
        if not filt:
            continue
        logic = filt.get('logic', '')
        # Placeholder: implement logic parsing and application
        removed = []
        session_pool = [c for c in session_pool if c not in removed]
        st.write(f"**{fname}** removed **{len(removed)}** combos — remaining **{len(session_pool)}**.")

    # Trap V3
    if enable_trap:
        session_pool, trap_removed = apply_trap_v3(session_pool, hot_digits, cold_digits, due_digits)
        st.write(f"**Trap V3 Ranking** applied — removed **{len(trap_removed)}** combos, remaining **{len(session_pool)}**.")

    # Final count
    st.write(f"Final pool size: **{len(session_pool)}** combos.")
else:
    st.info("Enter a current 5-digit seed to generate and filter combos.")

# ==============================
# Footer
# ==============================
st.sidebar.write("🛠️ Ready to apply filters and report results.")
