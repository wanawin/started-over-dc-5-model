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
    # Normalize columns
    df.columns = [c.lower().strip() for c in df.columns]
    expected = {'name','type','logic','action'}
    missing = expected - set(df.columns)
    if missing:
        st.sidebar.error(f"Filters CSV missing required columns: {missing}")
        return []
    return df.to_dict(orient='records')

filters = load_ranked_filters('Filters_Ranked_Eliminations.csv')
filter_count = len(filters)

# Display filter count and types
st.sidebar.header("🔍 Filters Overview")
st.sidebar.write(f"Total filters loaded: **{filter_count}**")
types = pd.Series([f['type'] for f in filters]).value_counts().to_dict()
for t, cnt in types.items():
    st.sidebar.write(f"- {t.title()}: {cnt}")

# Warning if not 396
if filter_count != 396:
    st.sidebar.warning(f"Expected 396 filters but loaded {filter_count}. Please verify CSV.")
else:
    st.sidebar.success("All 396 filters loaded.")

# ==============================
# Trap V3 stub
# ==============================
def apply_trap_v3(pool, hot_digits, cold_digits, due_digits):
    # Placeholder: implement ranking logic here
    # For now, just return pool unchanged
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
due_digits  = [d for d in st.sidebar.text_input("Due digits (comma-separated):").replace(' ', '').split(',') if d]
method      = st.sidebar.selectbox("Generation Method:", ["1-digit", "2-digit pair"])
enable_trap = st.sidebar.checkbox("Enable Trap V3 Ranking")

# Filter selection UI
filter_names = [f['name'] for f in filters]
selected = st.sidebar.multiselect("Select filters to apply (any order):", filter_names)

# Show provided seeds
if prev_seed:
    st.sidebar.write(f"Previous seed: {prev_seed}")
if seed:
    st.sidebar.write(f"Current seed: {seed}")

# ==============================
# Generation and Filtering
# ==============================
if seed:
    # Initialize pool of all combos
    session_pool = [str(i).zfill(5) for i in range(100000)]
    initial_count = len(session_pool)
    st.write(f"Initial pool size: **{initial_count}** combos.")

    # Apply selected filters in chosen order
    for fname in selected:
        filt = next(f for f in filters if f['name'] == fname)
        logic = filt['logic']
        # TODO: parse `logic` into actionable code or mapping
        # For now, placeholder removes zero combos
        removed = []
        # example: removed = apply_specific_filter(session_pool, logic)
        session_pool = [c for c in session_pool if c not in removed]
        st.write(f"**{fname}** removed **{len(removed)}** combos — remaining **{len(session_pool)}**.")

    # Automatic Trap V3
    if enable_trap:
        session_pool, trap_removed = apply_trap_v3(session_pool, hot_digits, cold_digits, due_digits)
        st.write(f"**Trap V3 Ranking** applied — removed **{len(trap_removed)}** combos, remaining **{len(session_pool)}**.")

    # Final pool
    st.write(f"Final pool size: **{len(session_pool)}** combos.")
else:
    st.info("Enter a current 5-digit seed to generate and filter combos.")

# ==============================
# Footer / Debug
# ==============================
st.sidebar.write("🛠️ Ready to apply any selected filters and report results.")
