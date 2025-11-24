import traceback
import sys
import os
import pandas as pd

# Ensure the app package dir is importable when running from repo root
sys.path.insert(0, os.path.join(os.getcwd(), 'kfc-cos-app-v2'))
from app import calculate_consumption

def main():
    path_norm = 'kfc-cos-app-v2/normativi.xlsx'
    report_path = r'c:\Users\Adna-Marketing\Downloads\REPORT BY COMBOS1.xls'

    print('Loading normativi...')
    norm = pd.read_excel(path_norm)
    print('Normativi rows:', len(norm))

    try:
        with open(report_path, 'rb') as f:
            print('Calling calculate_consumption...')
            res = calculate_consumption(f, norm)
            print('Returned type:', type(res))
            if isinstance(res, dict):
                print('Restaurants:', list(res.keys())[:10])
            else:
                df_consumption, dates_revenue, cov = res
                print('df_consumption shape:', df_consumption.shape)
                print('coverage:', cov)
                print(df_consumption.head().to_string())
    except Exception:
        print('Exception during calculate_consumption:')
        traceback.print_exc()

if __name__ == '__main__':
    main()
