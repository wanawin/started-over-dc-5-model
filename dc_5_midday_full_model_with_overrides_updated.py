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
# Helper Functions
# ==============================

def detect_auto_filters():
    # Define automatic filters as (name, function)
    return []


def detect_trap_v3_rankings(pool, previous_draw, hot_pool, cold_pool, due_pool):
    # Placeholder: implement Trap V3 logic
    return pool, 0


def detect_filter_pattern(filter_dict):
    # Compile a regex from filter_dict['logic'] or other
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
    # Rename needed columns
    df = df.rename(columns={
        next(c for c in df.columns if 'name' in c.lower()): 'name',
        next(c for c in df.columns if 'type' in c.lower()): 'type',
        next(c for c in df.columns if 'logic' in c.lower()): 'logic',
        next(c for c in df.columns if 'action' in c.lower()): 'action'
    })
    # Filter only manual
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
    # Parse pools
    hot_pool = [d.strip() for d in hot_digits.split(',') if d.strip().isdigit()]
    cold_pool = [d.strip() for d in cold_digits.split(',') if d.strip().isdigit()]
    due_pool = [d.strip() for d in due_digits.split(',') if d.strip().isdigit()]

    # Generate combination pool
    digit_sets = {
        "1-digit": list(map(str, range(10))),
        "2-digit": [''.join(p) for p in product(map(str, range(10)), repeat=2)],
        "3-digit": [''.join(p) for p in product(map(str, range(10)), repeat=3)]
    }
    base_set = digit_sets.get(generation_method, digit_sets["1-digit"])
    pool = [''.join(p) for p in product(base_set, repeat=5)]

    # Display metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Generated", len(pool))

    # Auto filters
    for name, func in auto_filters:
        filtered = [c for c in pool if func(c, previous_draw, hot_pool, cold_pool, due_pool)]
        c2.metric(f"Auto: {name}", len(filtered), -(len(pool)-len(filtered)))
        pool = filtered
    if not auto_filters:
        c2.metric("After Auto Filters", len(pool))

    # Trap V3
    if enable_trap_v3:
        pool, removed = detect_trap_v3_rankings(pool, previous_draw, hot_pool, cold_pool, due_pool)
        c3.metric("After Trap V3", len(pool), -removed)
    else:
        c3.metric("Trap V3 Disabled", "—")

    # Manual filters
    for f in manual_filters:
        before = len(pool)
        pattern, _ = detect_filter_pattern(f)
        pool = [c for c in pool if not pattern.match(c)]
        c4.metric(f['name'], len(pool), -(before-len(pool)))
    if not manual_filters:
        c4.metric("After Manual Filters", len(pool))

    # Final display
    st.header("Final Combination Pool")
    st.write(f"Showing first 100 of {len(pool)} combos")
    st.dataframe(pd.DataFrame(pool, columns=["combo"]).head(100))
