import pandas as pd
from pathlib import Path
p = Path('svirestorani.xlsx')
if not p.exists():
    print('svirestorani.xlsx not found in current folder:', p.resolve())
    raise SystemExit(1)

df = pd.read_excel(p)
print('Columns:', list(df.columns))
# Try common column names
candidates = ['restaurant','Restaurant','RESTAURANT','name','Name','naziv']
for c in candidates:
    if c in df.columns:
        vals = df[c].dropna().astype(str).str.strip().unique()
        print(f"Found column '{c}' with {len(vals)} unique values:")
        for v in list(vals)[:100]:
            print('-', v)
        break
else:
    # Fallback: print first column values
    first = df.columns[0]
    print(f"No obvious restaurant column. Showing first column '{first}':")
    vals = df[first].dropna().astype(str).str.strip().unique()
    for v in list(vals)[:100]:
        print('-', v)
