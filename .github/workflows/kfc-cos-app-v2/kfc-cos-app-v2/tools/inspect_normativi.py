import pandas as pd
from pathlib import Path
p = Path('normativi.xlsx')
print('Exists:', p.exists())
if not p.exists():
    raise SystemExit('normativi.xlsx not found')

df = pd.read_excel(p)
print('Rows:', len(df))
print('Columns:', list(df.columns))
print('\nUnique categories (value counts):')
if 'KATEGORIJA' in df.columns:
    print(df['KATEGORIJA'].value_counts().head(50))
else:
    print('No KATEGORIJA column; showing unique JM and sample SASTOJAK')
    print(df['JM'].value_counts().head(50))

# Find potential drink items miscategorized as OSTALO
candidates = df[(df['KATEGORIJA'].fillna('')=='OSTALO') & df['SASTOJAK'].str.contains('cola|fanta|sprite|yippy|yippy|coca', case=False, na=False)]
print('\nPotential drinks in OSTALO:', len(candidates))
print(candidates[['PROIZVOD','SASTOJAK','JM','UKUPNO']].head(50).to_string(index=False))

# Save a sample CSV for review
df.to_csv('normativi_debug_sample.csv', index=False)
print('\nWrote normativi_debug_sample.csv')
