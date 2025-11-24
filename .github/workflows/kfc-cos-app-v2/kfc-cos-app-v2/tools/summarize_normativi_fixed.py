import pandas as pd
from pathlib import Path
p = Path(__file__).parent / 'normativi_fixed.xlsx'
if not p.exists():
    p = Path(__file__).parent / 'normativi.xlsx'
    print('normativi_fixed.xlsx not found, using normativi.xlsx')

df = pd.read_excel(p)
print('Using file:', p)
print('Rows:', len(df))
print('\nKATEGORIJA counts:')
print(df['KATEGORIJA'].value_counts())

changes = Path(__file__).parent / 'normativi_fixed_changes.csv'
if changes.exists():
    chg = pd.read_csv(changes)
    print('\nTotal changes rows:', len(chg))
    print('\nSample changed rows (first 50):')
    print(chg[['PROIZVOD','SASTOJAK','OLD_KATEGORIJA','NEW_KATEGORIJA']].head(50).to_string(index=False))
else:
    print('\nNo changes CSV found at', changes)
