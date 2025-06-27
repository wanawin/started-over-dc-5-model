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
    df['norm_name'] = df['name'].map(lambda raw: unicodedata.normalize('NFKC', raw)
                                     .replace('≥','>=').replace('≤','<=')
                                     .replace('→','->')
                                     .strip().lower())
    records = []
    for idx, row in df.iterrows():
        records.append({
            'id': idx,
            'name': row['name'],
            'type': row['type'],
            'logic': row['logic'],
            'action': row['action'],
            'norm_name': row['norm_name']
        })
    return records

# Load filters once
filters = load_ranked_filters('Filters_Ranked_Eliminations.csv')

# Helper: detect filter type and parameters
def detect_filter_pattern(logic: str):
    low = logic.lower()
    m = re.search(r'between\s*(\d+)\s*and\s*(\d+)', low)
    if m:
        return 'sum_range', {'low': int(m.group(1)), 'high': int(m.group(2))}
    m = re.search(r'sum\s*<\s*(\d+)\s*or\s*>\s*(\d+)', low)
    if m:
        return 'sum_range', {'low': int(m.group(1)), 'high': int(m.group(2))}
    m = re.search(r'seed contains\s*(\d+).*?contain(?:s)? (?:either )?(\d+).*?(\d+)', low)
    if m:
        sd = int(m.group(1)); reqs = [int(m.group(2)), int(m.group(3))]
        return 'conditional_seed_contains', {'seed_digit': sd, 'required': reqs}
    return 'unknown', {}

# Filter application functions
def apply_sum_range_filter(combos, low, high):
    keep = [c for c in combos if low <= sum(int(d) for d in c) <= high]
    removed = [c for c in combos if c not in keep]
    return keep, removed

def apply_conditional_seed_contains(combos, seed_digits, seed_digit, required):
    if str(seed_digit) in seed_digits:
        keep = [c for c in combos if any(str(d) in c for d in required)]
        removed = [c for c in combos if c not in keep]
        return keep, removed
    return combos, []

# ==============================
# Streamlit App
# ==============================
st.set_page_config(layout='wide')
st.title('DC-5 Midday Blind Predictor with Filter Backtester')

# Sidebar inputs
st.sidebar.header('🔧 Settings')
last_draw = st.sidebar.text_input('Last draw result (5 digits):')
seed = last_draw.strip()

# For backtesting only, load test dataset here (not used in prediction)
if seed and st.sidebar.checkbox('🐞 Enable Filter Backtest'):
    try:
        test_df = pd.read_csv('DC5_Midday_Full_With_Features.csv')
        combos = [''.join(re.findall(r'\d', str(c))) for c in test_df['Digits']]
        total = len(combos)
        # Dropdown to select filter
        names = [f['name'] for f in filters]
        sel = st.sidebar.selectbox('Choose filter to test:', names)
        f = next(filt for filt in filters if filt['name'] == sel)
        pattern, params = detect_filter_pattern(f['logic'])
        if pattern == 'sum_range':
            low, high = params['low'], params['high']
            keep, removed = apply_sum_range_filter(combos, low, high)
        elif pattern == 'conditional_seed_contains':
            seed_digits = list(seed)
            keep, removed = apply_conditional_seed_contains(combos, seed_digits,
                                                            params['seed_digit'], params['required'])
        else:
            keep, removed = combos, []
        st.sidebar.write(f"**{sel}** removes {len(removed)} of {total} combos ({len(removed)/total*100:.2f}%).")
        with st.expander('Show removed combos'):
            st.write(removed)
        with st.expander('Show kept combos'):
            st.write(keep[:50], '...')
    except Exception as e:
        st.sidebar.error(f'Backtest load error: {e}')

# Prediction pipeline below (auto + manual filters)
# ...................................................
# (existing logic remains unchanged)
