import sys
import os
import sqlite3
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import app as appmod
from app import (_process_consumption_from_df, calculate_consumption,
                 save_to_db, NORMATIVI_PATH)


def load_normativi():
    candidates = []
    # 1) direct path as configured
    candidates.append(NORMATIVI_PATH)
    # 2) relative to app module
    app_dir = os.path.dirname(appmod.__file__)
    candidates.append(os.path.join(app_dir, NORMATIVI_PATH))
    # 3) workspace root
    candidates.append(os.path.join(os.getcwd(), NORMATIVI_PATH))

    for path in candidates:
        if path and os.path.exists(path):
            print(f"Loading normativi from: {path}")
            df = pd.read_excel(path)
            print(f"Normativi rows: {len(df)}")
            return df

    print(f"Normativi file not found. Tried: {candidates}")
    return None


def pick_complex_product(norm_df):
    # Try to find a product with multiple ingredients
    if norm_df is None:
        return None
    prods = norm_df[norm_df['PROIZVOD'].notna()]['PROIZVOD'].str.strip().unique()
    for p in prods:
        idx = norm_df[norm_df['PROIZVOD'] == p].index[0]
        next_prods = norm_df.iloc[idx+1:][norm_df.iloc[idx+1:]['PROIZVOD'].notna()]
        end_idx = next_prods.index[0] if len(next_prods) > 0 else len(norm_df)
        ingredients = norm_df.iloc[idx:end_idx][norm_df.iloc[idx:end_idx]['SASTOJAK'].notna()]
        if len(ingredients) >= 2:
            return p, ingredients
    return None


def test_single_and_double(norm_df):
    pick = pick_complex_product(norm_df)
    if not pick:
        print("No complex product found in normativi to test")
        return

    product, ingredients = pick
    print(f"Testing product: {product} with {len(ingredients)} ingredients")

    # Build report for single and double
    base_row = {
        'SHIFTDATE': '01. 01. 2025.',
        'RESTAURANT': 'KFC SCC',
        'COMBODISH': None,
        'DISH': product,
        'QUANTITY3': 1,
        'QUANTITY': None,
        'PRLISTSUM': None,
        'PAYSUM': 10.0,
        'COMBO_QTY': 0,
        'COMBO_SUM': None
    }

    df1 = pd.DataFrame([base_row])
    df2 = pd.DataFrame([dict(base_row, QUANTITY3=2)])

    df_c1, dr1, cov1 = _process_consumption_from_df(df1, norm_df)
    df_c2, dr2, cov2 = _process_consumption_from_df(df2, norm_df)

    print("Coverage single:", cov1.get('coverage_percent'))
    print("Coverage double:", cov2.get('coverage_percent'))

    # Compare ingredient totals doubling
    for _, ing in ingredients.iterrows():
        s = str(ing['SASTOJAK'])
        row1 = df_c1[df_c1['SASTOJAK'] == s]
        row2 = df_c2[df_c2['SASTOJAK'] == s]
        if row1.empty or row2.empty:
            print(f"Missing ingredient in outputs: {s}")
            continue
        q1 = float(row1['UKUPNA_KOLICINA'].iloc[0])
        q2 = float(row2['UKUPNA_KOLICINA'].iloc[0])
        print(f"{s}: 1x={q1} | 2x={q2}")
        if abs(q2 - 2*q1) > 1e-6:
            print(f"ERROR: not doubled for {s}: {q1} -> {q2}")


def test_shortening_and_salt(norm_df):
    if norm_df is None:
        print("Skipping shortening/salt test (no normativi)")
        return

    # Create normativi entries for shortening and salt under a product
    rows = [
        {'PROIZVOD': 'TEST_CONV', 'SASTOJAK': None, 'KOLICINA': None, 'JM': None, 'UKUPNO': None},
        {'PROIZVOD': None, 'SASTOJAK': 'shortening', 'KOLICINA': 1.0, 'JM': 'KG', 'UKUPNO': 5.0},
        {'PROIZVOD': None, 'SASTOJAK': 'salt', 'KOLICINA': 0.1, 'JM': 'L', 'UKUPNO': 0.2},
    ]
    test_norm = pd.DataFrame(rows)

    df_report = pd.DataFrame([
        {'SHIFTDATE': '02. 01. 2025.', 'RESTAURANT': 'KFC SCC', 'COMBODISH': None, 'DISH':'TEST_CONV', 'QUANTITY3':1,
         'QUANTITY':None,'PRLISTSUM':None,'PAYSUM':5.0,'COMBO_QTY':0,'COMBO_SUM':None}
    ])

    df_c, dr, cov = _process_consumption_from_df(df_report, test_norm)
    print("Shortening/Salt test coverage:", cov.get('coverage_percent'))
    for _, r in df_c.iterrows():
        print(r['SASTOJAK'], r['JM'], r['UKUPNA_KOLICINA'])


def test_save_to_db(norm_df):
    # Use temporary test DB
    test_db = 'temp_test_save.db'
    if os.path.exists(test_db):
        os.remove(test_db)

    # Pick any product to produce consumption data
    pick = pick_complex_product(norm_df) if norm_df is not None else None
    if not pick:
        print("No product to test save_to_db")
        return
    product, ingredients = pick
    df_report = pd.DataFrame([
        {'SHIFTDATE': '03. 01. 2025.', 'RESTAURANT': 'KFC SCC', 'COMBODISH': None, 'DISH': product, 'QUANTITY3':1,
         'QUANTITY':None,'PRLISTSUM':None,'PAYSUM':10.0,'COMBO_QTY':0,'COMBO_SUM':None}
    ])

    df_c, dr, cov = _process_consumption_from_df(df_report, norm_df)

    # Temporarily override DB path by connecting directly
    # Initialize DB via app module
    import app as appmod
    orig_db = appmod.DB_PATH
    try:
        appmod.DB_PATH = test_db
        # initialize tables
        appmod.init_db()
        save_to_db('KFC SCC', df_c, dr)

        # Verify rows
        conn = sqlite3.connect(test_db)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM daily_consumption")
        cnt = c.fetchone()[0]
        print(f"Rows in daily_consumption: {cnt}")
        c.execute("SELECT COUNT(*) FROM daily_revenue")
        rcnt = c.fetchone()[0]
        print(f"Rows in daily_revenue: {rcnt}")
        conn.close()
    finally:
        # Restore DB_PATH
        appmod.DB_PATH = orig_db


def main():
    norm_df = load_normativi()
    print('\n-- Single/Double product tests --')
    test_single_and_double(norm_df)
    print('\n-- Shortening/Salt special cases --')
    test_shortening_and_salt(norm_df)
    print('\n-- DB save verification --')
    test_save_to_db(norm_df)


if __name__ == '__main__':
    main()
