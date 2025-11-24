import os
import pandas as pd
import sys
import os
# ensure app package dir is importable
sys.path.insert(0, os.path.join(os.getcwd(), 'kfc-cos-app-v2'))
import app as appmod


def find_normativi_path():
    candidates = []
    candidates.append(getattr(appmod, 'NORMATIVI_PATH', 'normativi.xlsx'))
    app_dir = os.path.dirname(appmod.__file__)
    candidates.append(os.path.join(app_dir, getattr(appmod, 'NORMATIVI_PATH', 'normativi.xlsx')))
    candidates.append(os.path.join(os.getcwd(), getattr(appmod, 'NORMATIVI_PATH', 'normativi.xlsx')))

    for p in candidates:
        if p and os.path.exists(p):
            return os.path.normpath(p)
    return None


def main():
    path = find_normativi_path()
    if not path:
        print('normativi.xlsx not found. Tried defaults relative to app module and cwd.')
        return 1

    df = pd.read_excel(path)
    if 'UKUPNO' not in df.columns:
        print('Column UKUPNO not found in normativi.xlsx')
        return 1

    mask = df['UKUPNO'].isna() & df['SASTOJAK'].notna()
    missing = df[mask].copy()

    if missing.empty:
        print('No missing prices found.')
        return 0

    # Group by SASTOJAK and collect context
    def join_unique(s):
        vals = [str(x).strip() for x in s.dropna().unique()]
        return '; '.join([v for v in vals if v and v.lower() not in ['nan', 'none']])

    grouped = missing.groupby('SASTOJAK').agg({
        'PROIZVOD': join_unique,
        'JM': join_unique,
        'KOLICINA': 'mean'
    }).reset_index()

    out_path = os.path.join(os.getcwd(), 'missing_prices.csv')
    grouped.rename(columns={'PROIZVOD': 'PROIZVOD_LIST', 'KOLICINA': 'AVG_KOLICINA'}, inplace=True)
    grouped.to_csv(out_path, index=False, encoding='utf-8-sig')

    print(f'Wrote {out_path} ({len(grouped)} items)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
