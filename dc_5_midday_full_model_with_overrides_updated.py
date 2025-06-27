import streamlit as st
import numpy as np
import os, unicodedata, re
from itertools import product
import pandas as pd

# ==============================
# Configuration
# ==============================
FILTERS_CSV_PATH = '/mnt/data/Filters_Ranked_Eliminations.csv'

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

    # Identify required columns
    cols = df.columns.str.lower()
    required = ['name', 'type', 'logic', 'action']
    if not all(any(req in col for col in df.columns) for req in required):
        st.error("Filter CSV missing one of the required columns: name, type, logic, action.")
        return []

    # Standardize column names
    df = df.rename(columns={
        next(c for c in df.columns if 'name' in c.lower()): 'name',
        next(c for c in df.columns if 'type' in c.lower()): 'type',
        next(c for c in df.columns if 'logic' in c.lower()): 'logic',
        next(c for c in df.columns if 'action' in c.lower()): 'action'
    })

    # Filter manual filters only
    return df[df['type'].str.lower() == 'manual'].to_dict('records')

# Load filters
filters = load_ranked_filters(FILTERS_CSV_PATH)

# ==============================
# Main App Interface
# ==============================
st.title("DC-5 Midday Full Model with Updated Manual Filters")

seed = st.sidebar.text_input("Enter 5-digit seed:")

if seed and seed.isdigit() and len(seed) == 5:
    seed_sum = sum(int(d) for d in seed)
    st.sidebar.success(f"Seed sum: {seed_sum}")

    # Generate initial combination pool
    comp_pool = [''.join(p) for p in product(map(str, range(10)), repeat=5)]
    st.write(f"**Pool before manual filters: {len(comp_pool)} combos.**")

    # Apply each manual filter in order
    st.header("🔍 Manual Filters")
    remaining = comp_pool
    for f in filters:
        keep = [combo for combo in remaining if not detect_filter_pattern(f)[0].match(combo)]
        eliminated = len(remaining) - len(keep)
        st.write(f"{f['name']}: eliminated {eliminated} combos.")
        remaining = keep

    st.write(f"**Remaining after manual filters: {len(remaining)} combos.**")
else:
    st.info("Enter a valid 5-digit seed to begin processing.")
