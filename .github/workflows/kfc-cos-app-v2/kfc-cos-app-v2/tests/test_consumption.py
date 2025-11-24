import sys
import os
import pandas as pd

# Ensure parent package dir is on sys.path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import _process_consumption_from_df


def approx_equal(a, b, tol=1e-6):
    return abs(a - b) <= tol


def main():
    # Create a minimal 'normativi' DataFrame structure expected by the app
    rows = [
        {'PROIZVOD': 'TEST BURGER', 'SASTOJAK': None, 'KOLICINA': None, 'JM': None, 'UKUPNO': None},
        {'PROIZVOD': None, 'SASTOJAK': 'Chicken Fillet', 'KOLICINA': 0.5, 'JM': 'KG', 'UKUPNO': 2.0},
        {'PROIZVOD': None, 'SASTOJAK': 'Fries', 'KOLICINA': 0.2, 'JM': 'KG', 'UKUPNO': 0.5},
    ]
    normativi_df = pd.DataFrame(rows)

    # Build a simple sales report DataFrame for one sold
    report_one = pd.DataFrame([
        {
            'SHIFTDATE': '01. 01. 2025.',
            'RESTAURANT': 'KFC SCC',
            'COMBODISH': None,
            'DISH': 'TEST BURGER',
            'QUANTITY3': 1,
            'QUANTITY': None,
            'PRLISTSUM': None,
            'PAYSUM': 10.0,
            'COMBO_QTY': 0,
            'COMBO_SUM': None
        }
    ])

    df_consumption1, dates_rev1, coverage1 = _process_consumption_from_df(report_one, normativi_df)

    # Find ingredient rows
    ch = df_consumption1[df_consumption1['SASTOJAK'] == 'Chicken Fillet']
    fr = df_consumption1[df_consumption1['SASTOJAK'] == 'Fries']

    assert not ch.empty, 'Chicken Fillet row missing for single sale'
    assert not fr.empty, 'Fries row missing for single sale'

    ch_qty = float(ch['UKUPNA_KOLICINA'].iloc[0])
    fr_qty = float(fr['UKUPNA_KOLICINA'].iloc[0])

    print(f"Single sale - Chicken Fillet UKUPNA_KOLICINA = {ch_qty}")
    print(f"Single sale - Fries UKUPNA_KOLICINA = {fr_qty}")

    assert approx_equal(ch_qty, 0.5), f'Expected 0.5, got {ch_qty}'
    assert approx_equal(fr_qty, 0.2), f'Expected 0.2, got {fr_qty}'

    print('\n✔ Single-sale quantities are correct')

    # Now test with two sold
    report_two = report_one.copy()
    report_two.at[0, 'QUANTITY3'] = 2

    df_consumption2, dates_rev2, coverage2 = _process_consumption_from_df(report_two, normativi_df)

    ch2 = df_consumption2[df_consumption2['SASTOJAK'] == 'Chicken Fillet']
    fr2 = df_consumption2[df_consumption2['SASTOJAK'] == 'Fries']

    assert not ch2.empty, 'Chicken Fillet row missing for two sales'
    assert not fr2.empty, 'Fries row missing for two sales'

    ch_qty2 = float(ch2['UKUPNA_KOLICINA'].iloc[0])
    fr_qty2 = float(fr2['UKUPNA_KOLICINA'].iloc[0])

    print(f"Double sale - Chicken Fillet UKUPNA_KOLICINA = {ch_qty2}")
    print(f"Double sale - Fries UKUPNA_KOLICINA = {fr_qty2}")

    assert approx_equal(ch_qty2, 1.0), f'Expected 1.0, got {ch_qty2}'
    assert approx_equal(fr_qty2, 0.4), f'Expected 0.4, got {fr_qty2}'

    print('\n✔ Double-sale quantities are correct (doubled)')


if __name__ == '__main__':
    try:
        main()
        print('\nALL CHECKS PASSED')
    except AssertionError as e:
        print('\nTEST FAILED:', e)
        raise
