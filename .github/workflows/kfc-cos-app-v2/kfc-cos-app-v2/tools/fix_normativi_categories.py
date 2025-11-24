import pandas as pd
from pathlib import Path
import sys
from pathlib import Path as P
# Ensure project root is on path so we can import app.py
proj_root = P(__file__).resolve().parents[1]
sys.path.insert(0, str(proj_root))
import app as appmod

p = Path(r'c:\Users\Adna-Marketing\Downloads\kfc-cos-app-v2\kfc-cos-app-v2\normativi.xlsx')
print('Loading', p)
df = pd.read_excel(p)
print('Rows:', len(df))

# Normalize columns
df.columns = [c.strip() for c in df.columns]
if 'SASTOJAK' not in df.columns:
    raise SystemExit('SASTOJAK column missing')

# Compute new categories using get_category from app.py
new_cats = []
for s in df['SASTOJAK'].fillna(''):
    new_cats.append(appmod.get_category(s))

df['NEW_KATEGORIJA'] = new_cats

# Compare
df['OLD_KATEGORIJA'] = df['KATEGORIJA'].fillna('')
mask_diff = df['OLD_KATEGORIJA'] != df['NEW_KATEGORIJA']
changes = df[mask_diff]
print('Total changes detected:', len(changes))

# Show top changes sample
if len(changes) > 0:
    print('\nSample changes:')
    print(changes[['PROIZVOD','SASTOJAK','OLD_KATEGORIJA','NEW_KATEGORIJA']].head(50).to_string(index=False))

# Apply changes automatically
apply_auto = True
if apply_auto and len(changes) > 0:
    df['KATEGORIJA'] = df['NEW_KATEGORIJA']
    out_xlsx = p.parent / 'normativi_fixed.xlsx'
    df.to_excel(out_xlsx, index=False)
    out_csv = p.parent / 'normativi_fixed_changes.csv'
    changes.to_csv(out_csv, index=False)
    print('\nWrote fixed file to', out_xlsx)
    print('Wrote changes CSV to', out_csv)
else:
    print('No changes applied.')
