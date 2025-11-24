import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'kfc-cos-app-v2'))
import pandas as pd
import app as appmod
from app import calculate_consumption

def find_norm_path():
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
    norm_path = find_norm_path()
    report_path = r'c:\Users\Adna-Marketing\Downloads\REPORT BY COMBOS1.xls'
    if not norm_path:
        raise SystemExit('normativi.xlsx not found')
    print('Loading normativi from', norm_path)
    norm = pd.read_excel(norm_path)

    with open(report_path, 'rb') as f:
        res = calculate_consumption(f, norm)

    if isinstance(res, dict):
        frames = []
        for rest, data in res.items():
            dfc, dr, cov = data
            dfc['RESTAURANT'] = rest
            frames.append(dfc)
        df_all = pd.concat(frames, ignore_index=True)
    else:
        df_all, dr, cov = res

    out = os.path.join(os.getcwd(), '..', '..', 'consumption_REPORT_BY_COMBOS1.csv')
    out = os.path.normpath(out)
    df_all.to_csv(out, index=False, encoding='utf-8-sig')
    print('Exported consumption to', out, 'rows=', len(df_all))

if __name__ == '__main__':
    main()
