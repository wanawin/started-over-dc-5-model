import streamlit as st
import numpy as np
import os, unicodedata, re
from itertools import product
import pandas as pd

# ==============================
# Configuration
# ==============================
FILTERS_CSV_PATH = '/mnt/data/manual_filters_ranked_by_elimination.csv'

# ==============================
# Helper Functions
# ==============================

def detect_auto_filters():
    # Define automatic filters as (name, function) tuples
    # Example: lambda combo,...: True to keep, False to remove
    return [
        # ('Repeating Digit Filter', lambda c, pd, h, cl, d: True),
        # Add your actual auto-filter functions here
    ]

def detect_trap_v3_rankings(pool, previous_draw, hot_pool, cold_pool, due_pool):
    # Implement Trap V3: flag or remove based on ranking logic
    # For now, return unchanged pool and zero removed
    return pool, 0

def detect_filter_pattern(filter_dict):
    # Convert filter_dict['logic'] into regex or callable
    # Placeholder: match nothing
    return re.compile(r"^$"), {}

# ==============================
# Load and Parse Ranked Filters
# ==============================
@st.cache_data
def load_ranked_filters(path: str):
    try:
        df = pd.read_csv(path)
    except Exception as e:
        st.error(f"Failed to load filters CSV: {e}")
        return []
    # Normalize column names
    df = df.rename(columns={
        next(c for c in df.columns if 'name' in c.lower()): 'name',
        next(c for c in df.columns if 'type' in c.lower()): 'type',
        next(c for c in df.columns if 'logic' in c.lower()): 'logic',
        next(c for c in df.columns if 'action' in c.lower()): 'action'
    })
    return df[df['type'].str.lower() == 'manual'].to_dict('records')

# Load filters
auto_filters = detect_auto_filters()
manual_filters = load_ranked_filters(FILTERS_CSV_PATH)

# ==============================
# Streamlit App UI
# ==============================
st.set_page_config(layout="wide")
st.title("DC-5 Midday Blind Predictor")

# Sidebar Inputs
with st.sidebar:
    st.header("Inputs and Settings")
    previous_draw = st.text_input("Previous draw (5-digit):")
    hot_digits = st.text_input("Hot digits (comma-separated):")
    cold_digits = st.text_input("Cold digits (comma-separated):")
    due_digits = st.text_input("Due digits (comma-separated):")
    generation_method = st.selectbox("Generation Method", ["1-digit", "2-digit", "3-digit"])
    enable_trap_v3 = st.checkbox("Enable Trap V3 Ranking")

# Main Logic
if not (previous_draw.isdigit() and len(previous_draw) == 5):
    st.info("Enter the previous draw result to begin.")
else:
    # Parse digit pools
    hot_pool = [d.strip() for d in hot_digits.split(',') if d.strip().isdigit()]
    cold_pool = [d.strip() for d in cold_digits.split(',') if d.strip().isdigit()]
    due_pool = [d.strip() for d in due_digits.split(',') if d.strip().isdigit()]

    # Generate base combination pool
    digit_sets = {
        "1-digit": list(map(str, range(10))),
        "2-digit": [''.join(p) for p in product(map(str, range(10)), repeat=2)],
        "3-digit": [''.join(p) for p in product(map(str, range(10)), repeat=3)]
    }
    base_set = digit_sets.get(generation_method, digit_sets["1-digit"])
    comp_pool = [''.join(p) for p in product(base_set, repeat=5)]

    # Display count ribbon
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Generated", len(comp_pool))

    # Automatic filters
    pool_after_auto = comp_pool.copy()
    for name, func in auto_filters:
        filtered = [c for c in pool_after_auto if func(c, previous_draw, hot_pool, cold_pool, due_pool)]
        c2.metric(f"Auto: {name}", len(filtered), -(len(pool_after_auto)-len(filtered)))
        pool_after_auto = filtered
    if not auto_filters:
        c2.metric("After Auto Filters", len(pool_after_auto))

    # Trap V3
    if enable_trap_v3:
        pool_after_trap, removed = detect_trap_v3_rankings(pool_after_auto, previous_draw, hot_pool, cold_pool, due_pool)
        c3.metric("After Trap V3", len(pool_after_trap), -removed)
    else:
        pool_after_trap = pool_after_auto
        c3.metric("Trap V3 Disabled", "—")

    # Manual filters
    pool_after_manual = pool_after_trap.copy()
    for f in manual_filters:
        pattern, _ = detect_filter_pattern(f)
        before = len(pool_after_manual)
        pool_after_manual = [c for c in pool_after_manual if not pattern.match(c)]
        c4.metric(f['name'], len(pool_after_manual), -(before-len(pool_after_manual)))
    if not manual_filters:
        c4.metric("After Manual Filters", len(pool_after_manual))

    # Show final combos
    st.header("Final Combination Pool")
    st.write(f"First 100 of {len(pool_after_manual)} combos:")
    st.dataframe(pd.DataFrame(pool_after_manual, columns=["combo"]).head(100))
