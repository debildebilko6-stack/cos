import os
import pandas as pd

path = os.path.join(os.path.dirname(__file__), '..', 'normativi.xlsx')
path = os.path.normpath(path)
if not os.path.exists(path):
    print('normativi.xlsx not found at', path)
    raise SystemExit(1)

df = pd.read_excel(path)
total = len(df)
if 'UKUPNO' not in df.columns:
    print('Column UKUPNO not present in normativi.xlsx')
    raise SystemExit(1)

missing = df['UKUPNO'].isna().sum()
print(f"normativi: {path}")
print(f"rows: {total}")
print(f"missing UKUPNO: {missing}")

if missing > 0:
    sample = df[df['UKUPNO'].isna() & df['SASTOJAK'].notna()]['SASTOJAK'].dropna().unique()[:50]
    print('\nSample missing (up to 50):')
    for s in sample:
        print(' -', s)
