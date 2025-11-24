import pandas as pd
from pathlib import Path
p = Path(r'c:\Users\Adna-Marketing\Downloads\kfc-cos-app-v2\kfc-cos-app-v2\normativi.xlsx')
print('Path:', p)
print('Exists:', p.exists(), 'Size:', p.stat().st_size)

df = pd.read_excel(p)
print('Rows:', len(df))
print('Columns:', list(df.columns))

# Normalize column names
cols = [c.strip() for c in df.columns]
df.columns = cols

print('\nTop KATEGORIJA values:')
if 'KATEGORIJA' in df.columns:
    print(df['KATEGORIJA'].value_counts().head(50))
else:
    print('No KATEGORIJA column')

# Find obvious drink items not in PIĆE
drink_keywords = ['cola','coca','fanta','sprite','yippy','cappy','postmix','coca cola','fanta 0','fanta 0,33','cola 0,33']
mask_drinks = df['SASTOJAK'].fillna('').str.lower().apply(lambda x: any(k in x for k in drink_keywords))
drink_rows = df[mask_drinks]
print('\nDetected drink-like SASTOJAK rows:', len(drink_rows))
print(drink_rows[['PROIZVOD','SASTOJAK','KATEGORIJA','JM','UKUPNO']].head(100).to_string(index=False))

# Find items with KATEGORIJA == 'OSTALO' that look like drinks
mask_mis = (df['KATEGORIJA'].fillna('')=='OSTALO') & mask_drinks
mis = df[mask_mis]
print('\nPotential miscategorized drinks in OSTALO:', len(mis))
print(mis[['PROIZVOD','SASTOJAK','KATEGORIJA','JM','UKUPNO']].to_string(index=False))

# Save sample for review
df.to_csv('normativi_full_dump.csv', index=False)
print('\nWrote normativi_full_dump.csv')
