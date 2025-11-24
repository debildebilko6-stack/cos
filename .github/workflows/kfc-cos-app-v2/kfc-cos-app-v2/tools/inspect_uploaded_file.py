import sys
import os
from pathlib import Path
fp = Path(r"C:\Users\Adna-Marketing\OneDrive - APTHA Corp. Sarajevo\Desktop\REPORT BY COMBOS.xls")
print('File path:', fp)
print('Exists:', fp.exists())
if not fp.exists():
    sys.exit(1)

# Read first bytes
with open(fp, 'rb') as f:
    head = f.read(512)
print('\nFirst 256 bytes (repr):')
print(repr(head[:256]))
print('\nFirst 512 bytes hexdump (start):')
print(head[:128].hex())

# Try reading as text to search for HTML markers
try:
    with open(fp, 'r', encoding='utf-8', errors='replace') as f:
        txt = f.read(4096)
    snippet = txt[:1000]
    print('\nFirst characters as text (utf-8 replacement):')
    print(snippet[:1000])
    if '<table' in snippet.lower() or '<html' in snippet.lower():
        print('\nDetected HTML markers in text content (<table> or <html>).')
    else:
        print('\nNo obvious HTML markers found in first text chunk.')
except Exception as e:
    print('\nCould not read as text:', e)

import traceback

# Try pandas HTML
try:
    import pandas as pd
    print('\nTrying pandas.read_html...')
    tables = pd.read_html(str(fp), flavor='bs4')
    print('read_html succeeded, number of tables =', len(tables))
except Exception as e:
    print('read_html failed:')
    traceback.print_exc()

# Try pandas read_excel with different engines
engines = ['openpyxl', 'xlrd', 'pyxlsb']
for eng in engines:
    try:
        print(f"\nTrying pandas.read_excel with engine='{eng}'...")
        df = pd.read_excel(str(fp), engine=eng)
        print(f"read_excel succeeded with engine={eng}; shape={df.shape}")
        break
    except Exception as e:
        print(f"read_excel with engine={eng} failed:")
        traceback.print_exc()

# Try reading as CSV with common separators
seps = [';', ',', '\t', '|']
for s in seps:
    try:
        print(f"\nTrying pandas.read_csv with sep='{s}'...")
        df = pd.read_csv(str(fp), sep=s, encoding='utf-8', nrows=5)
        print('read_csv succeeded; columns:', list(df.columns))
        break
    except Exception as e:
        print(f"read_csv sep={s} failed:")
        traceback.print_exc()

print('\nInspection complete.')
