import streamlit as st
import os, unicodedata, re, zipfile
from itertools import product, combinations
import pandas as pd

# ==============================
# Helper functions for parsing manual filters
# ==============================
def strip_prefix(raw_name: str) -> str:
    return re.sub(r'^\s*\d+[\.)]\s*', '', raw_name).strip()

def normalize_name(raw: str) -> str:
    s = unicodedata.normalize('NFKC', raw)
    for a, b in [
        ('≥','>='), ('≤','<='), ('\u2265','>='), ('\u2264','<='),
        ('→','->'), ('\u2192','->'), ('–','-'), ('—','-'),
        ('\u200B',''), ('\u00A0',' ')
    ]:
        s = s.replace(a, b)
    return re.sub(r'\s+', ' ', s).strip().lower()

# Parse manual filters from text
def parse_manual_filters_txt(raw_text: str):
    entries, skipped = [], []
    blocks = [b.strip() for b in raw_text.splitlines() if b.strip()]
    current = {}
    for line in blocks:
        low = line.lower()
        if low.startswith('type:'):
            current['type'] = line.split(':',1)[1].strip() or 'Manual'
        elif low.startswith('logic:'):
            current['logic'] = line.split(':',1)[1].strip()
        elif low.startswith('action:'):
            current['action'] = line.split(':',1)[1].strip()
        else:
            # start of new filter
            if current.get('name'):
                entries.append(current)
                current = {}
            name = normalize_name(strip_prefix(line))
            current = {'name': name, 'type': 'Manual', 'logic': '', 'action': ''}
    if current.get('name'):
        entries.append(current)
    return entries

# ==============================
# Load manual filters from ZIP
# ==============================
zip_path = 'filter intent summary.zip'
if os.path.exists(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        raw = z.read(z.namelist()[0]).decode('utf-8', errors='ignore')
    filters = parse_manual_filters_txt(raw)
else:
    filters = []
    st.error(f"Filter definitions ZIP not found at {zip_path}")

# ==============================
# Generate combinations function
# ==============================
def generate_combinations(seed: str, method: str = "1-digit") -> list[str]:
    all_digits = '0123456789'
    combos = set()
    if len(seed) < 2:
        return []
    if method == "1-digit":
        for d in seed:
            for p in product(all_digits, repeat=4):
                combos.add(''.join(sorted(d + ''.join(p))))
    else:
        for i in range(len(seed)):
            for j in range(i+1, len(seed)):
                pair = ''.join(sorted((seed[i], seed[j])))
                for p in product(all_digits, repeat=3):
                    combos.add(''.join(sorted(pair + ''.join(p))))
    return sorted(combos)

# ==============================
# Streamlit App UI
# ==============================
st.set_page_config(layout='wide')
st.title('DC-5 Midday Blind Predictor')

# Sidebar Inputs
st.sidebar.header('Inputs and Settings')
prev_seed = st.sidebar.text_input('Previous draw (5-digit):')
seed = prev_seed.strip()
hot = st.sidebar.text_input('Hot digits (comma-separated):')
cold = st.sidebar.text_input('Cold digits (comma-separated):')
due = st.sidebar.text_input('Due digits (comma-separated):')
hot_digits = [d for d in hot.replace(' ','').split(',') if d]
cold_digits = [d for d in cold.replace(' ','').split(',') if d]
due_digits = [d for d in due.replace(' ','').split(',') if d]
method = st.sidebar.selectbox('Generation Method', ['1-digit', '2-digit pair'])
enable_trap = st.sidebar.checkbox('Enable Trap V3 Ranking')

# Main Logic
if not seed:
    st.info('Enter the previous draw result to begin.')
else:
    # Step 1: Full enumeration
    all_combos = [f"{i:05d}" for i in range(100000)]
    st.write(f"Step 1: Full enumeration — {len(all_combos)} combos.")

    # Step 2: Placeholder for auto filters & deduplication
    pool = all_combos.copy()
    st.write(f"Step 2: Auto filters removed 0 combos, remaining {len(pool)}.")

    # Step 3: Seed-based generation
    gen = generate_combinations(seed, method)
    st.write(f"Step 3: Seed-based generation ({method}) yields {len(gen)} combos.")

    # Step 4: Comparison filter
    comp_keep = [c for c in pool if c in gen]
    removed_comp = len(pool) - len(comp_keep)
    st.write(f"Step 4: Comparison removed {removed_comp}, remaining {len(comp_keep)}.")

    # Step 5: Manual filters
    st.header('🔍 Manual Filters')
    session_pool = comp_keep.copy()
    cols = st.columns(3)
    for idx, f in enumerate(filters):
        col = cols[idx % 3]
        label = f"{f['name']}"
        if col.checkbox(label, key=f"mf{idx}"):
            # only sum_range logic implemented as example
            m = re.search(r'between\s*(\d+)\s*and\s*(\d+)', f['logic'].lower())
            if m:
                lo, hi = int(m.group(1)), int(m.group(2))
                session_pool = [c for c in session_pool if lo <= sum(int(d) for d in c) <= hi]
    st.write(f"Final pool after manual filters: {len(session_pool)} combos.")
