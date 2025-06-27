import streamlit as st
import numpy as np
import os, unicodedata, re
from itertools import product
import pandas as pd

# ==============================
# Configuration
# ==============================
FILTERS_CSV_PATH = '/mnt/data/Filters_Ranked_Eliminations.csv'.join(p) for p in product(base_set, repeat=5)]

    # Column ribbon for counts
    c1, c2, c3, c4 = st.columns([1,1,1,1])
    c1.metric("Total Generated", len(comp_pool))

    # Apply automatic filters
    pool_after_auto = comp_pool.copy()
    for name, func in auto_filters:
        new_pool = [c for c in pool_after_auto if func(c, previous_draw, hot_pool, cold_pool, due_pool)]
        pool_after_auto = new_pool
    c2.metric("After Auto Filters", len(pool_after_auto))

    # Apply Trap V3 if enabled
    if enable_trap_v3:
        pool_after_trap, removed = detect_trap_v3_rankings(pool_after_auto, previous_draw, hot_pool, cold_pool, due_pool)
        c3.metric("After Trap V3", len(pool_after_trap), -removed)
    else:
        pool_after_trap = pool_after_auto
        c3.metric("Trap V3 Disabled", "—")

    # Apply manual filters
    pool_after_manual = pool_after_trap.copy()
    for f in manual_filters:
        pattern, _ = detect_filter_pattern(f)
        pool_after_manual = [c for c in pool_after_manual if not pattern.match(c)]
    c4.metric("After Manual Filters", len(pool_after_manual))

    # Show summary table if desired
    st.header("Final Combination Pool")
    st.write(f"Displaying up to first 100 combos below ({len(pool_after_manual)} total)")
    st.dataframe(pd.DataFrame(pool_after_manual, columns=["combo"]).head(100))
