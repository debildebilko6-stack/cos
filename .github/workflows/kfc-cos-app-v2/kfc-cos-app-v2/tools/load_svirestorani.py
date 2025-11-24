import pandas as pd
import os
p = os.path.join(os.path.dirname(__file__),'..','svirestorani.xlsx')
print('looking for', os.path.abspath(p))
if not os.path.exists(p):
    print('NOT FOUND')
    raise SystemExit(1)

df = pd.read_excel(p)
print('shape', df.shape)
print('columns:', list(df.columns))
# try to find name-like column
candidates = ['restaurant','Restaurant','RESTAURANT','name','Name','naziv','NAZIV','naziv_restorana','naziv_restorana']
found = None
for c in df.columns:
    if c in candidates:
        found = c
        break
# fallback: pick first string column
if not found:
    for c in df.columns:
        if df[c].dtype == object:
            found = c
            break

print('picked column:', found)
if found:
    s = df[found].dropna().astype(str).str.strip()
    uniq = s.unique().tolist()
    print('unique_count', len(uniq))
    print('sample', uniq[:10])
else:
    print('no suitable column found')
