"""
KFC COS Calculator v2 - Full System
- Multi-restaurant support
- Daily report uploads
- SQLite database storage
- Dashboard with filters
- Forecasting
"""

from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for
import pandas as pd
import numpy as np
from io import BytesIO
import os
import sqlite3
from datetime import datetime, timedelta
import json

app = Flask(__name__)
app.secret_key = 'kfc-cos-secret-key-2025'

# Database path
DB_PATH = os.environ.get('DB_PATH', 'kfc_cos.db')
NORMATIVI_PATH = os.environ.get('NORMATIVI_PATH', 'normativi.xlsx')

# Restaurants
RESTAURANTS = ['KFC SCC', 'KFC MCC', 'KFC BCC', 'KFC STM', 'KFC ICC']
SVIRESTORANI_PATH = os.environ.get('SVIRESTORANI_PATH', 'svirestorani.xlsx')

# ============================================
# DATABASE SETUP
# ============================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Daily consumption table
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_consumption (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant TEXT NOT NULL,
            date DATE NOT NULL,
            category TEXT NOT NULL,
            ingredient TEXT NOT NULL,
            unit TEXT,
            quantity REAL,
            value REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(restaurant, date, category, ingredient)
        )
    ''')
    
    # Daily revenue table
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_revenue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant TEXT NOT NULL,
            date DATE NOT NULL,
            revenue REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(restaurant, date)
        )
    ''')
    
    # Upload log
    c.execute('''
        CREATE TABLE IF NOT EXISTS upload_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurant TEXT NOT NULL,
            date DATE NOT NULL,
            filename TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes for better performance
    c.execute('CREATE INDEX IF NOT EXISTS idx_consumption_restaurant_date ON daily_consumption(restaurant, date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_consumption_category ON daily_consumption(category)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_revenue_restaurant_date ON daily_revenue(restaurant, date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_upload_log_restaurant ON upload_log(restaurant)')
    
    conn.commit()
    conn.close()

# ============================================
# KATEGORIJE SASTOJAKA
# ============================================
def get_category(ingredient):
    if pd.isna(ingredient):
        return ""
    ing = str(ingredient).strip().lower()
    
    if any(x in ing for x in ['bun', 'tortilla']):
        return "PECIVO"
    if any(x in ing for x in ['pileć', 'meso', 'fillet', 'strips', 'krilca', 'chicken']):
        if 'small chicken box' in ing:
            return "AMBALAŽA"
        return "MESO"
    if any(x in ing for x in ['fries', 'pomfrit', 'hashbrown', 'corn stick', 'coleslaw mix', 
                               'salad bowl', 'croutons', 'cesar dres', 'onion ring', 'half corn']):
        return "SIDES/DODACI"
    if any(x in ing for x in ['flour', 'breading']):
        return "BRAŠNO/PANIRANJE"
    if 'marinad' in ing:
        return "MARINADA"
    if any(x in ing for x in ['shortening', 'oil']):
        return "ULJE"
    if any(x in ing for x in ['sauce', 'mayo', 'ketchup', 'sos', 'smoky bbq']):
        return "SOS"
    if any(x in ing for x in ['sirup', 'cola 0,33', 'debic', 'coffee bean', 'milk 3']):
        return "PIĆE"
    if any(x in ing for x in ['iceberg', 'tomato', 'pickle', 'onion ( washed']):
        return "POVRĆE"
    if any(x in ing for x in ['cheese', 'sir']) and 'sauce' not in ing:
        return "SIR"
    if any(x in ing for x in ['donut', 'krofna', 'sladoled', 'ice cream', 'kitkat', 
                               'smarties', 'chocolate sauce', 'toffee', 'strawberry gel', 
                               'soft ice', 'triple choc']):
        return "DESERT"
    if any(x in ing for x in ['napkin', 'wrap', 'box', 'bag', 'tray', 'bucket', 'lid', 
                               'cup', 'čaša', 'straw', 'fork', 'spoon', 'plate', 
                               'poklopac', 'wooden', 'paper bag', 'small chicken box']):
        return "AMBALAŽA"
    if 'yippy' in ing:
        return "PIĆE"
    if 'salt' in ing:
        return "ZAČINI"
    return "OSTALO"


# ============================================
# KALKULACIJA
# ============================================
def _process_consumption_from_df(df_report, normativi_df):
    """Helper function to process consumption from DataFrame"""
    
    # Get dates and revenue
    dates_revenue = df_report.groupby('SHIFTDATE')['PAYSUM'].sum().to_dict()
    
    norm_products = set(normativi_df[normativi_df['PROIZVOD'].notna()]['PROIZVOD'].str.strip().tolist())
    
    # Track products not in normativi for coverage analysis
    products_not_in_norm = set()
    revenue_not_in_norm = {}
    
    postmix_items = ['COCA COLA 0,4', 'COCA COLA 0,5', 'FANTA 0,4', 'FANTA 0,5', 
                     'SPRITE 0,4', 'SPRITE 0,5', 'COCA COLA ZERO 0,4', 'COCA COLA ZERO 0,5']
    
    combo_with_pice = df_report[(df_report['COMBODISH'].notna()) & (df_report['DISH'].isin(postmix_items))]
    combos_sa_picem = set(combo_with_pice['COMBODISH'].unique())
    
    consumption = []
    
    def add_consumption(product, qty_sold, date, skip_pice=False):
        prod_idx = normativi_df[normativi_df['PROIZVOD'] == product].index
        if len(prod_idx) == 0:
            return
        
        start_idx = prod_idx[0]
        next_prods = normativi_df.iloc[start_idx+1:][normativi_df.iloc[start_idx+1:]['PROIZVOD'].notna()]
        end_idx = next_prods.index[0] if len(next_prods) > 0 else len(normativi_df)
        
        ingredients = normativi_df.iloc[start_idx:end_idx][normativi_df.iloc[start_idx:end_idx]['SASTOJAK'].notna()]
        
        for _, ing in ingredients.iterrows():
            cat = get_category(ing['SASTOJAK'])
            sastojak = ing['SASTOJAK']
            kolicina = ing['KOLICINA']
            jm = ing['JM']
            
            if skip_pice and cat == 'PIĆE':
                continue
            if skip_pice and any(x in str(sastojak).lower() for x in ['čaša', 'poklopac', 'straw', 'lid cold']):
                continue
            
            if 'shortening' in str(sastojak).lower() and jm == 'KG':
                kolicina = kolicina * 1.11
                jm = 'L'
            if 'salt' in str(sastojak).lower() and jm == 'L':
                jm = 'KG'
            
            consumption.append({
                'DATE': date,
                'SASTOJAK': sastojak,
                'KATEGORIJA': cat,
                'JM': jm,
                'UKUPNA_KOLICINA': kolicina * qty_sold,
                'UKUPNA_VRIJEDNOST': ing['UKUPNO'] * qty_sold
            })
    
    # Process by date
    for date in df_report['SHIFTDATE'].unique():
        if pd.isna(date):
            continue
            
        day_data = df_report[df_report['SHIFTDATE'] == date]
        
        # COMBO
        combo_rows = day_data[(day_data['COMBODISH'].notna()) & (day_data['COMBO_QTY'] > 0)]
        combo_sales = combo_rows.groupby('COMBODISH')['COMBO_QTY'].sum()
        combo_revenue = combo_rows.groupby('COMBODISH')['PAYSUM'].sum()
        for product, qty in combo_sales.items():
            if product in norm_products:
                add_consumption(product, qty, date, skip_pice=product in combos_sa_picem)
            else:
                products_not_in_norm.add(product)
                if date not in revenue_not_in_norm:
                    revenue_not_in_norm[date] = 0
                revenue_not_in_norm[date] += combo_revenue.get(product, 0)
        
        # Individual
        individual_rows = day_data[day_data['COMBODISH'].isna()]
        individual_sales = individual_rows.groupby('DISH')['QUANTITY3'].sum()
        individual_revenue = individual_rows.groupby('DISH')['PAYSUM'].sum()
        for product, qty in individual_sales.items():
            if product in norm_products:
                add_consumption(product, qty, date, skip_pice=False)
            else:
                products_not_in_norm.add(product)
                if date not in revenue_not_in_norm:
                    revenue_not_in_norm[date] = 0
                revenue_not_in_norm[date] += individual_revenue.get(product, 0)
        
        # Postmix from COMBO
        pica_in_combo = day_data[(day_data['COMBODISH'].notna()) & (day_data['DISH'].isin(postmix_items))]
        pica_combo_sales = pica_in_combo.groupby('DISH')['QUANTITY3'].sum()
        pica_combo_revenue = pica_in_combo.groupby('DISH')['PAYSUM'].sum()
        for product, qty in pica_combo_sales.items():
            if product in norm_products:
                add_consumption(product, qty, date, skip_pice=False)
            else:
                products_not_in_norm.add(product)
                if date not in revenue_not_in_norm:
                    revenue_not_in_norm[date] = 0
                revenue_not_in_norm[date] += pica_combo_revenue.get(product, 0)
    
    df_consumption = pd.DataFrame(consumption)
    
    # Calculate coverage statistics
    total_revenue_all = sum(dates_revenue.values())
    revenue_missing = sum(revenue_not_in_norm.values())
    coverage_percent = round(100 * (1 - revenue_missing / total_revenue_all) if total_revenue_all > 0 else 100, 1)
    
    coverage_info = {
        'products_not_in_norm': len(products_not_in_norm),
        'revenue_missing': revenue_missing,
        'total_revenue': total_revenue_all,
        'coverage_percent': coverage_percent,
        'products_list': list(products_not_in_norm)[:20]  # First 20 for display
    }
    
    return df_consumption, dates_revenue, coverage_info


def calculate_consumption(report_file, normativi_df, restaurant_filter=None):
    """Calculate consumption from sales report
    
    Args:
        report_file: File object or BytesIO
        normativi_df: DataFrame with normativi
        restaurant_filter: Optional restaurant name to filter by
    
    Returns:
        If restaurant_filter is None and multiple restaurants found: dict {restaurant: (df_consumption, dates_revenue)}
        Otherwise: (df_consumption, dates_revenue)
    """
    
    # Handle FileStorage object - read into BytesIO if needed
    if hasattr(report_file, 'read'):
        # If it's a file-like object, read it
        file_content = report_file.read()
        if hasattr(report_file, 'seek'):
            report_file.seek(0)  # Reset file pointer
        report_file = BytesIO(file_content)
    
    # Try to parse uploaded report as HTML table first (old behavior),
    # but also support Excel (.xls/.xlsx) uploads which some POS exports use.
    df_report = None
    parse_error = None
    try:
        df_report = pd.read_html(report_file)[0]
    except Exception as e:
        parse_error = e
        try:
            # reset pointer and try Excel
            report_file.seek(0)
        except Exception:
            pass
        try:
            df_report = pd.read_excel(report_file, header=None)
        except Exception as e2:
            # keep last error for reporting
            raise Exception(f"Ne mogu parsirati fajl kao HTML niti Excel: {e}; {e2}")

    # If dataframe was read from Excel without headers, try to normalize
    # into the expected 10-column layout. If there are >=10 columns, assign
    # the expected column names; otherwise try reading Excel with default
    # header to capture column names from the file.
    if df_report is None:
        raise Exception(f"Prazan izvještaj nakon parsiranja: {parse_error}")

    # If parsed df has fewer than 10 columns, try reading with header=0
    if df_report.shape[1] < 10:
        try:
            report_file.seek(0)
            df_report = pd.read_excel(report_file)
        except Exception:
            pass

    if df_report.shape[1] >= 10:
        # ensure we have at least 10 columns and assign expected names
        df_report.columns = ['SHIFTDATE', 'RESTAURANT', 'COMBODISH', 'DISH', 'QUANTITY3', 
                             'QUANTITY', 'PRLISTSUM', 'PAYSUM', 'COMBO_QTY', 'COMBO_SUM'] + list(df_report.columns[10:])
        # many POS reports include header rows; keep existing logic of dropping first rows
        df_report = df_report.iloc[3:].reset_index(drop=True)
    else:
        raise Exception('Parsirani izvještaj ne sadrži očekivani broj kolona (10). Provjerite format fajla.')
    df_report = df_report[df_report['DISH'] != 'Totals']
    df_report['QUANTITY3'] = pd.to_numeric(df_report['QUANTITY3'], errors='coerce') / 100
    df_report['COMBO_QTY'] = pd.to_numeric(df_report['COMBO_QTY'], errors='coerce') / 100
    df_report['PAYSUM'] = pd.to_numeric(df_report['PAYSUM'], errors='coerce') / 100

    # Ensure normativi DataFrame is available. If caller passed None (server not initialized),
    # attempt to lazy-load from NORMATIVI_PATH so uploads don't fail when the process wasn't restarted.
    if normativi_df is None:
        if os.path.exists(NORMATIVI_PATH):
            try:
                normativi_df = pd.read_excel(NORMATIVI_PATH)
            except Exception as e:
                raise Exception(f"Ne mogu učitati normativi iz {NORMATIVI_PATH}: {e}")
        else:
            raise Exception(f"Normativi nisu učitani i fajl '{NORMATIVI_PATH}' nije pronađen. Restartajte server ili postavite ispravan put do normativi.xlsx.")
    
    # Flexible detection of restaurant column:
    # 1) Prefer explicit 'RESTAURANT' column
    # 2) Find any column whose header contains 'restaur'
    # 3) Otherwise, try to find a column where values match known restaurants
    has_restaurant_data = False
    unique_restaurants = []

    if 'RESTAURANT' in df_report.columns and df_report['RESTAURANT'].notna().any():
        has_restaurant_data = True
        unique_restaurants = df_report['RESTAURANT'].dropna().unique()
    else:
        # search header names
        rest_col = None
        for col in df_report.columns:
            try:
                if 'restaur' in str(col).lower():
                    rest_col = col
                    break
            except Exception:
                continue

        if rest_col is None:
            # try to detect by matching known restaurant names in values
            candidates = {}
            for col in df_report.columns:
                try:
                    vals = df_report[col].dropna().astype(str)
                    matches = vals.isin(RESTAURANTS).sum()
                    candidates[col] = matches
                except Exception:
                    candidates[col] = 0
            # pick column with most matches > 0
            best = max(candidates.items(), key=lambda x: x[1]) if candidates else (None, 0)
            if best and best[1] > 0:
                rest_col = best[0]

        if rest_col is not None:
            # normalize into 'RESTAURANT' column for downstream logic
            df_report['RESTAURANT'] = df_report[rest_col]
            if df_report['RESTAURANT'].notna().any():
                has_restaurant_data = True
                unique_restaurants = df_report['RESTAURANT'].dropna().unique()
    
    # If no restaurant filter and multiple restaurants found, process each separately
    if not restaurant_filter and has_restaurant_data and len(unique_restaurants) > 1:
        restaurant_data = {}
        for restaurant in unique_restaurants:
            restaurant_df = df_report[df_report['RESTAURANT'] == restaurant].copy()
            restaurant_df_consumption, restaurant_dates_revenue, coverage_info = _process_consumption_from_df(restaurant_df, normativi_df)
            restaurant_data[restaurant] = (restaurant_df_consumption, restaurant_dates_revenue, coverage_info)
        return restaurant_data
    
    # Filter by restaurant if specified
    if restaurant_filter:
        df_report = df_report[df_report['RESTAURANT'] == restaurant_filter]
    
    return _process_consumption_from_df(df_report, normativi_df)


def save_to_db(restaurant, df_consumption, dates_revenue):
    """Save consumption data to database"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Basic validation and normalization for df_consumption
    import pandas as _pd

    if df_consumption is None:
        raise Exception('Internal error: df_consumption is None')

    if not isinstance(df_consumption, _pd.DataFrame):
        # try to coerce to DataFrame
        try:
            df_consumption = _pd.DataFrame(df_consumption)
        except Exception:
            raise Exception(f'Internal error: expected DataFrame for df_consumption, got {type(df_consumption)}')

    # If empty, nothing to save
    if df_consumption.empty:
        conn.close()
        return

    # Allow flexible DATE column names (DATE, Date, date)
    cols_upper = {col.upper(): col for col in df_consumption.columns}
    if 'DATE' not in cols_upper:
        # maybe index contains dates
        if df_consumption.index.name and df_consumption.index.name.upper() == 'DATE':
            df_consumption = df_consumption.reset_index()
            cols_upper = {col.upper(): col for col in df_consumption.columns}

    if 'DATE' not in cols_upper:
        # try common alternatives
        for alt in ['date', 'Date', 'shiftdate', 'SHIFTDATE']:
            if alt in df_consumption.columns:
                df_consumption = df_consumption.rename(columns={alt: 'DATE'})
                cols_upper = {col.upper(): col for col in df_consumption.columns}
                break

    if 'DATE' not in cols_upper:
        available = ','.join(list(df_consumption.columns)[:20])
        raise Exception(f"Ne mogu naći kolonu 'DATE' u df_consumption. Dostupne kolone: {available}")

    # Save consumption by date
    for date in df_consumption[cols_upper['DATE']].unique():
        day_data = df_consumption[df_consumption[cols_upper['DATE']] == date]
        summary = day_data.groupby(['KATEGORIJA', 'SASTOJAK', 'JM']).agg({
            'UKUPNA_KOLICINA': 'sum',
            'UKUPNA_VRIJEDNOST': 'sum'
        }).reset_index()
        
        # Parse date
        try:
            parsed_date = datetime.strptime(date.strip(), '%d. %m. %Y.').strftime('%Y-%m-%d')
        except:
            parsed_date = date
        
        for _, row in summary.iterrows():
            c.execute('''
                INSERT OR REPLACE INTO daily_consumption 
                (restaurant, date, category, ingredient, unit, quantity, value)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (restaurant, parsed_date, row['KATEGORIJA'], row['SASTOJAK'], 
                  row['JM'], row['UKUPNA_KOLICINA'], row['UKUPNA_VRIJEDNOST']))
    
    # Save revenue
    for date, revenue in dates_revenue.items():
        try:
            parsed_date = datetime.strptime(date.strip(), '%d. %m. %Y.').strftime('%Y-%m-%d')
        except:
            parsed_date = date
        
        c.execute('''
            INSERT OR REPLACE INTO daily_revenue (restaurant, date, revenue)
            VALUES (?, ?, ?)
        ''', (restaurant, parsed_date, revenue))
    
    conn.commit()
    conn.close()


# ============================================
# HTML TEMPLATES
# ============================================
MAIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>KFC COS Calculator</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            margin: 0; padding: 0;
            background: #f5f5f5;
        }
        .navbar {
            background: #b5002a;
            color: white;
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .navbar h1 { margin: 0; font-size: 24px; }
        .navbar a { color: white; text-decoration: none; margin-left: 20px; }
        .navbar a:hover { text-decoration: underline; }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .card {
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin: 20px 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .card h2 { margin-top: 0; color: #333; border-bottom: 2px solid #b5002a; padding-bottom: 10px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; color: #555; }
        select, input[type="date"], input[type="file"] {
            width: 100%; padding: 10px; border: 1px solid #ddd;
            border-radius: 5px; font-size: 14px;
        }
        .btn {
            background: #b5002a; color: white; padding: 12px 25px;
            border: none; border-radius: 5px; cursor: pointer;
            font-size: 16px; display: inline-block; text-decoration: none;
        }
        .btn:hover { background: #8a0020; }
        .btn-secondary { background: #666; }
        .btn-secondary:hover { background: #444; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #b5002a; color: white; }
        tr:hover { background: #f9f9f9; }
        .stat-box {
            background: linear-gradient(135deg, #b5002a, #d4003a);
            color: white; padding: 20px; border-radius: 10px; text-align: center;
        }
        .stat-box h3 { margin: 0; font-size: 14px; opacity: 0.9; }
        .stat-box .value { font-size: 32px; font-weight: bold; margin: 10px 0; }
        .stat-box .sub { font-size: 12px; opacity: 0.8; }
        .restaurant-cards { display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px; margin: 20px 0; }
        .restaurant-card {
            background: white; padding: 15px; border-radius: 8px;
            text-align: center; cursor: pointer; transition: all 0.3s;
            border: 2px solid transparent;
        }
        .restaurant-card:hover { border-color: #b5002a; transform: translateY(-2px); }
        .restaurant-card.active { border-color: #b5002a; background: #fff5f5; }
        .restaurant-card h4 { margin: 0 0 5px 0; color: #333; }
        .restaurant-card .mini-stat { font-size: 12px; color: #666; }
        .alert { padding: 15px; border-radius: 5px; margin: 15px 0; }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .progress-bar { height: 8px; background: #eee; border-radius: 4px; overflow: hidden; }
        .progress-bar .fill { height: 100%; background: #b5002a; }
        .tabs { display: flex; border-bottom: 2px solid #ddd; margin-bottom: 20px; }
        .tab { padding: 10px 20px; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; }
        .tab:hover { background: #f5f5f5; }
        .tab.active { border-bottom-color: #b5002a; color: #b5002a; font-weight: bold; }
        .forecast-item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }
        .forecast-item:last-child { border-bottom: none; }
        .chart-container { position: relative; height: 300px; margin: 20px 0; }
        .chart-container-large { height: 400px; }
        .loading { display: none; text-align: center; padding: 20px; }
        .loading.active { display: block; }
        .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #b5002a; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .alert-warning { background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }
        .alert-info { background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        .comparison-box { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 15px 0; }
        .comparison-item { padding: 15px; background: #f8f9fa; border-radius: 5px; }
        .comparison-item.positive { border-left: 4px solid #28a745; }
        .comparison-item.negative { border-left: 4px solid #dc3545; }
        .comparison-item.neutral { border-left: 4px solid #6c757d; }
        .search-box { margin: 15px 0; }
        .search-box input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        .sortable { cursor: pointer; user-select: none; }
        .sortable:hover { background: #f0f0f0; }
        .sortable::after { content: ' ↕'; opacity: 0.5; }
        .sortable.asc::after { content: ' ↑'; opacity: 1; }
        .sortable.desc::after { content: ' ↓'; opacity: 1; }
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr !important; }
            .comparison-box { grid-template-columns: 1fr; }
            .navbar { flex-direction: column; padding: 10px; }
            .navbar h1 { margin-bottom: 10px; }
            .chart-container { height: 250px; }
        }
        .top-items { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .top-item { background: #fff; padding: 15px; border-radius: 8px; border-left: 4px solid #b5002a; }
        .top-item .rank { font-size: 24px; font-weight: bold; color: #b5002a; }
        .top-item .name { font-weight: bold; margin: 5px 0; }
        .top-item .value { color: #666; }
        .backup-section { margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 5px; }
        .file-input-wrapper { position: relative; overflow: hidden; display: inline-block; }
        .file-input-wrapper input[type=file] { position: absolute; left: -9999px; }
        .file-input-label { background: #b5002a; color: white; padding: 10px 20px; border-radius: 5px; cursor: pointer; display: inline-block; }
        .file-input-label:hover { background: #8a0020; }
    </style>
    <script>
        // Global utility functions
        function showLoading() {
            const loading = document.getElementById('loading');
            if (loading) loading.classList.add('active');
        }
        function hideLoading() {
            const loading = document.getElementById('loading');
            if (loading) loading.classList.remove('active');
        }
        function formatNumber(num) {
            return new Intl.NumberFormat('bs-BA', {minimumFractionDigits: 2, maximumFractionDigits: 2}).format(num);
        }
        // Table search functionality
        function initTableSearch(tableId, searchId) {
            const searchInput = document.getElementById(searchId);
            const table = document.getElementById(tableId);
            if (!searchInput || !table) return;
            
            searchInput.addEventListener('keyup', function() {
                const filter = this.value.toLowerCase();
                const rows = table.getElementsByTagName('tr');
                for (let i = 1; i < rows.length; i++) {
                    const row = rows[i];
                    const text = row.textContent || row.innerText;
                    row.style.display = text.toLowerCase().indexOf(filter) > -1 ? '' : 'none';
                }
            });
        }
        // Table sorting functionality
        function initTableSort(tableId) {
            const table = document.getElementById(tableId);
            if (!table) return;
            
            const headers = table.querySelectorAll('th.sortable');
            headers.forEach((header, index) => {
                header.addEventListener('click', function() {
                    const tbody = table.querySelector('tbody');
                    const rows = Array.from(tbody.querySelectorAll('tr'));
                    const isAsc = this.classList.contains('asc');
                    
                    // Remove all sort classes
                    headers.forEach(h => {
                        h.classList.remove('asc', 'desc');
                    });
                    
                    // Sort rows
                    rows.sort((a, b) => {
                        const aText = a.cells[index].textContent.trim();
                        const bText = b.cells[index].textContent.trim();
                        const aNum = parseFloat(aText.replace(/[^0-9.-]/g, ''));
                        const bNum = parseFloat(bText.replace(/[^0-9.-]/g, ''));
                        
                        if (!isNaN(aNum) && !isNaN(bNum)) {
                            return isAsc ? bNum - aNum : aNum - bNum;
                        }
                        return isAsc ? bText.localeCompare(aText) : aText.localeCompare(bText);
                    });
                    
                    // Reorder rows
                    rows.forEach(row => tbody.appendChild(row));
                    
                    // Add sort class
                    this.classList.add(isAsc ? 'desc' : 'asc');
                });
            });
        }
    </script>
</head>
<body>
    <div class="navbar">
        <h1>🍗 KFC COS Calculator</h1>
        <div>
            <a href="/">Dashboard</a>
            <a href="/upload">Upload</a>
            <a href="/forecast">Prognoza</a>
        </div>
    </div>
    
    <div class="container">
        <div id="loading" class="loading">
            <div class="spinner"></div>
            <p>Učitavanje...</p>
        </div>
        {% block content %}{% endblock %}
    </div>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
{% extends "main" %}
{% block content %}
<div class="card">
    <h2>📊 Dashboard - Pregled potrošnje</h2>
    
    <form method="GET" action="/dashboard">
        <div class="grid">
            <div class="form-group">
                <label>Restoran:</label>
                <select name="restaurant">
                    <option value="ALL" {% if selected_restaurant == 'ALL' %}selected{% endif %}>Svi restorani</option>
                    {% for r in restaurants %}
                    <option value="{{ r }}" {% if selected_restaurant == r %}selected{% endif %}>{{ r }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="form-group">
                <label>Od datuma:</label>
                <input type="date" name="date_from" value="{{ date_from }}">
            </div>
            <div class="form-group">
                <label>Do datuma:</label>
                <input type="date" name="date_to" value="{{ date_to }}">
            </div>
            <div class="form-group">
                <label>&nbsp;</label>
                <button type="submit" class="btn">🔍 Prikaži</button>
            </div>
        </div>
    </form>
</div>

{% if has_data %}
{% if cos_alert %}
<div class="alert alert-{{ 'error' if cos_alert.type == 'error' else 'warning' }}">
    {{ cos_alert.message }}
</div>
{% endif %}

{% if coverage_note %}
<div class="alert alert-warning">
    <strong>ℹ️ Važno:</strong> {{ coverage_note }}
    <br><small>Da biste dobili tačniji COS, dodajte sve proizvode koji se prodaju u normativi.xlsx fajl.</small>
</div>
{% endif %}

<div class="grid" style="grid-template-columns: repeat(4, 1fr);">
    <div class="stat-box">
        <h3>UKUPNA POTROŠNJA</h3>
        <div class="value">{{ total_consumption }}</div>
        <div class="sub">KM</div>
    </div>
    <div class="stat-box" style="background: linear-gradient(135deg, #28a745, #34ce57);">
        <h3>UKUPAN PROMET</h3>
        <div class="value">{{ total_revenue }}</div>
        <div class="sub">KM</div>
    </div>
    <div class="stat-box" style="background: linear-gradient(135deg, #17a2b8, #20c9e3);">
        <h3>COS %</h3>
        <div class="value">{{ cos_percent }}%</div>
        <div class="sub">Cost of Sales</div>
        {% if coverage_note %}
        <div class="sub" style="font-size: 10px; margin-top: 5px; opacity: 0.8;">
            ⚠️ Samo proizvodi u normativi
        </div>
        {% endif %}
    </div>
    <div class="stat-box" style="background: linear-gradient(135deg, #6f42c1, #8b5cf6);">
        <h3>BROJ DANA</h3>
        <div class="value">{{ num_days }}</div>
        <div class="sub">u periodu</div>
    </div>
</div>

{% if comparison %}
<div class="card">
    <h2>📊 Poređenje sa prethodnim periodom</h2>
    <div class="comparison-box">
        <div class="comparison-item {{ 'positive' if comparison.consumption_change < 0 else 'negative' if comparison.consumption_change > 0 else 'neutral' }}">
            <strong>Potrošnja:</strong><br>
            Trenutno: {{ total_consumption }} KM<br>
            Prethodno: {{ "%.2f"|format(comparison.prev_consumption) }} KM<br>
            Promjena: {{ comparison.consumption_change }}%
        </div>
        <div class="comparison-item {{ 'positive' if comparison.revenue_change > 0 else 'negative' if comparison.revenue_change < 0 else 'neutral' }}">
            <strong>Promet:</strong><br>
            Trenutno: {{ total_revenue }} KM<br>
            Prethodno: {{ "%.2f"|format(comparison.prev_revenue) }} KM<br>
            Promjena: {{ comparison.revenue_change }}%
        </div>
        <div class="comparison-item {{ 'positive' if comparison.cos_change < 0 else 'negative' if comparison.cos_change > 0 else 'neutral' }}">
            <strong>COS %:</strong><br>
            Trenutno: {{ cos_percent }}%<br>
            Prethodno: {{ comparison.prev_cos }}%<br>
            Promjena: {{ comparison.cos_change }}%
        </div>
    </div>
</div>
{% endif %}

{% if restaurant_comparison %}
<div class="card">
    <h2>🏪 Poređenje restorana</h2>
    <div class="chart-container">
        <canvas id="restaurantChart"></canvas>
    </div>
</div>
{% endif %}

<div class="card">
    <h2>📈 Potrošnja po kategorijama</h2>
    {% if chart_data %}
    <div class="chart-container">
        <canvas id="categoryChart"></canvas>
    </div>
    {% endif %}
    <table id="categoryTable">
        <thead>
            <tr>
                <th class="sortable">Kategorija</th>
                <th class="sortable">Vrijednost (KM)</th>
                <th class="sortable">%</th>
                <th>Vizualizacija</th>
            </tr>
        </thead>
        <tbody>
            {% for cat in categories %}
            <tr>
                <td><strong>{{ cat.name }}</strong></td>
                <td>{{ cat.value }}</td>
                <td>{{ cat.pct }}%</td>
                <td>
                    <div class="progress-bar" style="width: 200px;">
                        <div class="fill" style="width: {{ cat.pct }}%;"></div>
                    </div>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

{% if top_items %}
<div class="card">
    <h2>🏆 Top 10 najskupljih sirovina</h2>
    <div class="top-items">
        {% for item in top_items %}
        <div class="top-item">
            <div class="rank">#{{ item.rank }}</div>
            <div class="name">{{ item.name }}</div>
            <div class="value">{{ item.value }} KM</div>
        </div>
        {% endfor %}
    </div>
</div>
{% endif %}

<div class="card">
    <h2>📅 Potrošnja po danima</h2>
    {% if chart_data %}
    <div class="chart-container chart-container-large">
        <canvas id="dailyChart"></canvas>
    </div>
    {% endif %}
    <div class="search-box">
        <input type="text" id="dailySearch" placeholder="🔍 Pretraži po datumu, prometu, potrošnji...">
    </div>
    <table id="dailyTable">
        <thead>
            <tr>
                <th class="sortable">Datum</th>
                <th class="sortable">Promet (KM)</th>
                <th class="sortable">Potrošnja (KM)</th>
                <th class="sortable">COS %</th>
            </tr>
        </thead>
        <tbody>
            {% for day in daily_data %}
            <tr>
                <td>{{ day.date }}</td>
                <td>{{ day.revenue }}</td>
                <td>{{ day.consumption }}</td>
                <td>{{ day.cos }}%</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
    <div style="margin-top: 15px;">
        <a href="/export?restaurant={{ selected_restaurant }}&date_from={{ date_from }}&date_to={{ date_to }}&format=excel" class="btn btn-secondary">📥 Export Excel</a>
        <a href="/export?restaurant={{ selected_restaurant }}&date_from={{ date_from }}&date_to={{ date_to }}&format=pdf" class="btn btn-secondary" style="margin-left: 10px;">📄 Export PDF</a>
    </div>
</div>

<div class="card">
    <h2>📦 Detaljna potrošnja po sirovinama</h2>
    <div class="search-box">
        <input type="text" id="detailSearch" placeholder="🔍 Pretraži po kategoriji, sirovini...">
    </div>
    {% set current_cat = namespace(value='') %}
    <table id="detailTable">
        <thead>
            <tr>
                <th class="sortable">Kategorija</th>
                <th class="sortable">Sirovina</th>
                <th class="sortable">Količina</th>
                <th>JM</th>
                <th class="sortable">Vrijednost (KM)</th>
            </tr>
        </thead>
        <tbody>
            {% for item in detailed_items %}
            <tr {% if item.category != current_cat.value %}style="border-top: 2px solid #b5002a;"{% endif %}>
                <td><strong>{% if item.category != current_cat.value %}{{ item.category }}{% set current_cat.value = item.category %}{% endif %}</strong></td>
                <td>{{ item.ingredient }}</td>
                <td>{{ item.quantity }}</td>
                <td>{{ item.unit }}</td>
                <td>{{ item.value }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

{% if chart_data %}
<script>
    // Initialize table search and sort
    document.addEventListener('DOMContentLoaded', function() {
        initTableSearch('dailyTable', 'dailySearch');
        initTableSearch('detailTable', 'detailSearch');
        initTableSort('dailyTable');
        initTableSort('detailTable');
        initTableSort('categoryTable');
        
        // Category Pie Chart
        const categoryCtx = document.getElementById('categoryChart');
        if (categoryCtx) {
            new Chart(categoryCtx, {
                type: 'pie',
                data: {
                    labels: {{ chart_data.categories|tojson }},
                    datasets: [{
                        data: {{ chart_data.category_values|tojson }},
                        backgroundColor: [
                            '#b5002a', '#28a745', '#17a2b8', '#ffc107', '#6f42c1',
                            '#dc3545', '#20c997', '#fd7e14', '#6c757d', '#e83e8c'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'right' },
                        title: { display: true, text: 'Potrošnja po kategorijama' }
                    }
                }
            });
        }
        
        // Daily Line Chart
        const dailyCtx = document.getElementById('dailyChart');
        if (dailyCtx) {
            new Chart(dailyCtx, {
                type: 'line',
                data: {
                    labels: {{ chart_data.daily_dates|tojson }},
                    datasets: [
                        {
                            label: 'Promet (KM)',
                            data: {{ chart_data.daily_revenue|tojson }},
                            borderColor: '#28a745',
                            backgroundColor: 'rgba(40, 167, 69, 0.1)',
                            yAxisID: 'y'
                        },
                        {
                            label: 'Potrošnja (KM)',
                            data: {{ chart_data.daily_consumption|tojson }},
                            borderColor: '#b5002a',
                            backgroundColor: 'rgba(181, 0, 42, 0.1)',
                            yAxisID: 'y'
                        },
                        {
                            label: 'COS %',
                            data: {{ chart_data.daily_cos|tojson }},
                            borderColor: '#17a2b8',
                            backgroundColor: 'rgba(23, 162, 184, 0.1)',
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    scales: {
                        y: { type: 'linear', position: 'left', title: { display: true, text: 'KM' } },
                        y1: { type: 'linear', position: 'right', title: { display: true, text: 'COS %' }, grid: { drawOnChartArea: false } }
                    },
                    plugins: {
                        title: { display: true, text: 'Dnevni trend - Promet, Potrošnja i COS' }
                    }
                }
            });
        }
        
        {% if restaurant_comparison %}
        // Restaurant Comparison Chart
        const restCtx = document.getElementById('restaurantChart');
        if (restCtx) {
            const restData = {{ restaurant_comparison|tojson }};
            new Chart(restCtx, {
                type: 'bar',
                data: {
                    labels: restData.map(r => r.name),
                    datasets: [
                        {
                            label: 'Potrošnja (KM)',
                            data: restData.map(r => parseFloat(r.consumption.replace(/,/g, ''))),
                            backgroundColor: '#b5002a'
                        },
                        {
                            label: 'Promet (KM)',
                            data: restData.map(r => parseFloat(r.revenue.replace(/,/g, ''))),
                            backgroundColor: '#28a745'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, title: { display: true, text: 'KM' } }
                    },
                    plugins: {
                        title: { display: true, text: 'Poređenje restorana' }
                    }
                }
            });
        }
        {% endif %}
    });
</script>
{% endif %}
{% else %}
<div class="card">
    <p>Nema podataka za odabrani period. <a href="/upload">Uploadaj izvještaj</a></p>
</div>
{% endif %}
{% endblock %}
'''

UPLOAD_TEMPLATE = '''
{% extends "main" %}
{% block content %}
<div class="card">
    <h2>📤 Upload dnevnog izvještaja</h2>
    
    {% if message %}
    <div class="alert {{ 'alert-success' if success else 'alert-error' }}">
        {{ message }}
    </div>
    {% endif %}
    
    <div class="alert" style="background: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; margin-bottom: 20px;">
        <strong>💡 Napomena:</strong> Ako vaš Excel fajl sadrži kolonu "RESTAURANT" sa nazivima restorana, 
        aplikacija će automatski prepoznati i obraditi podatke za sve restorane u fajlu. 
        U tom slučaju, odabir restorana nije obavezan.
    </div>
    
    <form action="/upload" method="post" enctype="multipart/form-data">
        <div class="grid">
            <div class="form-group">
                <label>Restoran (opciono - ako fajl ima kolonu RESTAURANT):</label>
                <select name="restaurant">
                    <option value="">-- Odaberi restoran (opciono) --</option>
                    {% for r in restaurants %}
                    <option value="{{ r }}">{{ r }}</option>
                    {% endfor %}
                </select>
                <small style="color: #666; font-size: 12px;">Ako fajl sadrži više restorana, oni će biti automatski prepoznati</small>
            </div>
            <div class="form-group">
                <label>Prodajni izvještaj (XLS/XLSX):</label>
                <input type="file" name="report" id="reportFile" accept=".xls,.xlsx" required>
                <small style="color: #666; font-size: 12px; display: block; margin-top: 5px;">Možete odabrati jedan ili više fajlova (držite Ctrl za više fajlova)</small>
            </div>
            <div class="form-group">
                <label>
                    <input type="checkbox" name="bulk_upload" value="1"> Bulk upload (više fajlova odjednom)
                </label>
            </div>
        </div>
        <button type="submit" class="btn" onclick="showLoading()">📊 Učitaj i obradi</button>
        <div id="uploadProgress" style="display: none; margin-top: 15px;">
            <div class="progress-bar">
                <div class="fill" id="progressFill" style="width: 0%;"></div>
            </div>
            <p id="progressText">Učitavanje...</p>
        </div>
    </form>
</div>

<div class="card">
    <h2>📋 Zadnji uploadovi</h2>
    <table>
        <tr>
            <th>Restoran</th>
            <th>Datum podataka</th>
            <th>Uploadano</th>
        </tr>
        {% for log in upload_logs %}
        <tr>
            <td>{{ log.restaurant }}</td>
            <td>{{ log.date }}</td>
            <td>{{ log.uploaded_at }}</td>
        </tr>
        {% endfor %}
    </table>
</div>
{% endblock %}
'''

FORECAST_TEMPLATE = '''
{% extends "main" %}
{% block content %}
<div class="card">
    <h2>🔮 Prognoza potrošnje</h2>
    <p>Na osnovu historijskih podataka, izračunaj potrebne sirovine za planirani promet.</p>
    
    <form method="POST" action="/forecast">
        <div class="grid">
            <div class="form-group">
                <label>Restoran:</label>
                <select name="restaurant">
                    {% for r in restaurants %}
                    <option value="{{ r }}" {% if selected_restaurant == r %}selected{% endif %}>{{ r }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="form-group">
                <label>Tip prognoze:</label>
                <select name="forecast_type" id="forecastType" onchange="toggleRevenueInput()">
                    <option value="revenue" {% if forecast_type == 'revenue' %}selected{% endif %}>Unesi planirani promet</option>
                    <option value="auto" {% if forecast_type == 'auto' %}selected{% endif %}>Automatska prognoza prometa</option>
                </select>
            </div>
            <div class="form-group" id="revenueInputGroup">
                <label>Planirani promet (KM):</label>
                <input type="number" name="planned_revenue" id="plannedRevenue" value="{{ planned_revenue or 5000 }}" step="100">
            </div>
            <div class="form-group">
                <label>Period za izračun:</label>
                <select name="period">
                    <option value="all" {% if period == 'all' %}selected{% endif %}>Svi podaci</option>
                    <option value="7" {% if period == '7' %}selected{% endif %}>Zadnjih 7 dana</option>
                    <option value="30" {% if period == '30' %}selected{% endif %}>Zadnjih 30 dana (mjesec)</option>
                    <option value="90" {% if period == '90' %}selected{% endif %}>Zadnjih 90 dana (kvartal)</option>
                </select>
            </div>
            <div class="form-group">
                <label>&nbsp;</label>
                <button type="submit" class="btn">📊 Izračunaj prognozu</button>
            </div>
        </div>
    </form>
</div>

{% if forecast %}
<div class="card">
    <h2>📋 Prognoza potrošnje i prometa</h2>
    
    {% if revenue_forecast and revenue_forecast.forecasted %}
    <div class="alert alert-info">
        <strong>🔮 Automatska prognoza prometa:</strong> {{ "%.2f"|format(revenue_forecast.value) }} KM<br>
        <small>Metoda: {{ revenue_forecast.method }}</small>
    </div>
    {% endif %}
    
    <div class="grid" style="grid-template-columns: repeat(2, 1fr); margin: 20px 0;">
        <div class="stat-box" style="max-width: 100%;">
            <h3>PROGNOZIRANI PROMET</h3>
            <div class="value">{{ "%.2f"|format(planned_revenue) }}</div>
            <div class="sub">KM</div>
        </div>
        <div class="stat-box" style="max-width: 100%; background: linear-gradient(135deg, #b5002a, #d4003a);">
            <h3>PROGNOZIRANA POTROŠNJA</h3>
            <div class="value">{{ forecast_total }}</div>
            <div class="sub">KM</div>
        </div>
    </div>
    
    <p><em>Bazirano na prosjeku: {{ avg_cos }}% COS (period: {{ period_label }})</em></p>
    
    <h3>Po kategorijama:</h3>
    {% for cat in forecast %}
    <div class="forecast-item">
        <span><strong>{{ cat.name }}</strong></span>
        <span>{{ cat.value }} KM ({{ cat.pct }}%)</span>
    </div>
    {% endfor %}
    
    <h3 style="margin-top: 30px;">Sve sirovine po kategorijama:</h3>
    {% set current_cat = namespace(value='') %}
    <table>
        <tr><th>Kategorija</th><th>Sirovina</th><th>Količina</th><th>JM</th><th>Vrijednost (KM)</th></tr>
        {% for item in key_items %}
        <tr {% if item.category != current_cat.value %}style="border-top: 2px solid #b5002a;"{% endif %}>
            <td><strong>{% if item.category != current_cat.value %}{{ item.category }}{% set current_cat.value = item.category %}{% endif %}</strong></td>
            <td>{{ item.name }}</td>
            <td>{{ item.qty }}</td>
            <td>{{ item.unit }}</td>
            <td>{{ item.value }}</td>
        </tr>
        {% endfor %}
    </table>
</div>
{% endif %}

<script>
    function toggleRevenueInput() {
        const forecastType = document.getElementById('forecastType').value;
        const revenueInputGroup = document.getElementById('revenueInputGroup');
        const plannedRevenue = document.getElementById('plannedRevenue');
        
        if (forecastType === 'auto') {
            revenueInputGroup.style.display = 'none';
            plannedRevenue.removeAttribute('required');
        } else {
            revenueInputGroup.style.display = 'block';
            plannedRevenue.setAttribute('required', 'required');
        }
    }
    
    // Initialize on page load
    document.addEventListener('DOMContentLoaded', function() {
        toggleRevenueInput();
    });
</script>
{% endblock %}
'''


# ============================================
# TEMPLATE RENDERING
# ============================================
from jinja2 import Environment, BaseLoader

templates = {
    'main': MAIN_TEMPLATE,
    'dashboard': DASHBOARD_TEMPLATE,
    'upload': UPLOAD_TEMPLATE,
    'forecast': FORECAST_TEMPLATE
}

class TemplateLoader(BaseLoader):
    def get_source(self, environment, template):
        if template in templates:
            return templates[template], template, lambda: True
        raise Exception(f"Template {template} not found")

jinja_env = Environment(loader=TemplateLoader())

def render(template_name, **kwargs):
    template = jinja_env.get_template(template_name)
    return template.render(**kwargs)


# ============================================
# ROUTES
# ============================================
normativi_df = None

@app.before_request
def setup():
    global normativi_df
    global RESTAURANTS
    init_db()
    if normativi_df is None and os.path.exists(NORMATIVI_PATH):
        normativi_df = pd.read_excel(NORMATIVI_PATH)
    # Try to load external restaurant list if available
    try:
        if os.path.exists(SVIRESTORANI_PATH):
            try:
                df_rest = pd.read_excel(SVIRESTORANI_PATH)
                # common column names to look for
                for col in ['restaurant','Restaurant','RESTAURANT','name','Name','naziv','NAZIV']:
                    if col in df_rest.columns:
                        vals = df_rest[col].dropna().astype(str).str.strip().unique().tolist()
                        if len(vals) > 0:
                            RESTAURANTS = vals
                            app.logger.info(f'Loaded {len(vals)} restaurants from {SVIRESTORANI_PATH}')
                            break
                else:
                    # Fallback: try to extract names from any column that contains KFC-like values
                    for col in df_rest.columns:
                        try:
                            vals = df_rest[col].dropna().astype(str).str.strip()
                        except Exception:
                            continue
                        # filter out obvious header or date-like rows
                        cleaned = [v for v in vals if not any(tok in v.lower() for tok in ['shiftdate', 'shift', 'date', 'total', 'smena'])]
                        unique_vals = []
                        for v in cleaned:
                            if v not in unique_vals:
                                unique_vals.append(v)
                        # require at least 2 items and at least one KFC-like token
                        if len(unique_vals) >= 2 and any('kfc' in str(x).lower() for x in unique_vals):
                            # Filter out header-like rows (e.g. 'RESTAURANTNAME') and very short entries
                            filtered = [v for v in unique_vals if v and 'restaurant' not in v.lower() and len(v.strip()) > 2]
                            if len(filtered) >= 1:
                                RESTAURANTS = filtered
                                app.logger.info(f'Loaded {len(filtered)} restaurants from {SVIRESTORANI_PATH} (fallback col: {col})')
                                break
            except Exception as e:
                app.logger.warning(f'Could not load restaurants from {SVIRESTORANI_PATH}: {e}')
    except Exception:
        pass


@app.route('/')
def index():
    return redirect('/dashboard')


@app.route('/dashboard')
def dashboard():
    restaurant = request.args.get('restaurant', 'ALL')
    date_from = request.args.get('date_from', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.args.get('date_to', datetime.now().strftime('%Y-%m-%d'))
    
    conn = sqlite3.connect(DB_PATH)
    
    # Get consumption data
    if restaurant == 'ALL':
        consumption_query = '''
            SELECT date, category, SUM(value) as value 
            FROM daily_consumption 
            WHERE date BETWEEN ? AND ?
            GROUP BY date, category
        '''
        revenue_query = '''
            SELECT date, SUM(revenue) as revenue 
            FROM daily_revenue 
            WHERE date BETWEEN ? AND ?
            GROUP BY date
        '''
        params = (date_from, date_to)
    else:
        consumption_query = '''
            SELECT date, category, SUM(value) as value 
            FROM daily_consumption 
            WHERE restaurant = ? AND date BETWEEN ? AND ?
            GROUP BY date, category
        '''
        revenue_query = '''
            SELECT date, SUM(revenue) as revenue 
            FROM daily_revenue 
            WHERE restaurant = ? AND date BETWEEN ? AND ?
            GROUP BY date
        '''
        params = (restaurant, date_from, date_to)
    
    df_consumption = pd.read_sql_query(consumption_query, conn, params=params)
    df_revenue = pd.read_sql_query(revenue_query, conn, params=params)
    conn.close()
    
    has_data = len(df_consumption) > 0
    
    if has_data:
        # Category summary
        cat_summary = df_consumption.groupby('category')['value'].sum().sort_values(ascending=False)
        total_consumption = cat_summary.sum()
        total_revenue = df_revenue['revenue'].sum()
        cos_percent = round(100 * total_consumption / total_revenue, 1) if total_revenue > 0 else 0
        
        categories = []
        for cat, val in cat_summary.items():
            categories.append({
                'name': cat,
                'value': f'{val:,.2f}',
                'pct': round(100 * val / total_consumption, 1)
            })
        
        # Daily data
        daily_consumption = df_consumption.groupby('date')['value'].sum()
        daily_revenue = df_revenue.set_index('date')['revenue']
        
        daily_data = []
        for date in sorted(daily_consumption.index):
            cons = daily_consumption.get(date, 0)
            rev = daily_revenue.get(date, 0)
            cos = round(100 * cons / rev, 1) if rev > 0 else 0
            daily_data.append({
                'date': date,
                'revenue': f'{rev:,.2f}',
                'consumption': f'{cons:,.2f}',
                'cos': cos
            })
        
        num_days = len(daily_data)
        
        # Top 10 najskupljih sirovina
        if restaurant == 'ALL':
            top_query = '''
                SELECT ingredient, SUM(value) as total_value
                FROM daily_consumption
                WHERE date BETWEEN ? AND ?
                GROUP BY ingredient
                ORDER BY total_value DESC
                LIMIT 10
            '''
            top_params = (date_from, date_to)
        else:
            top_query = '''
                SELECT ingredient, SUM(value) as total_value
                FROM daily_consumption
                WHERE restaurant = ? AND date BETWEEN ? AND ?
                GROUP BY ingredient
                ORDER BY total_value DESC
                LIMIT 10
            '''
            top_params = (restaurant, date_from, date_to)
        
        conn3 = sqlite3.connect(DB_PATH)
        df_top = pd.read_sql_query(top_query, conn3, params=top_params)
        conn3.close()
        
        top_items = []
        for idx, row in df_top.iterrows():
            top_items.append({
                'rank': idx + 1,
                'name': row['ingredient'],
                'value': f'{row["total_value"]:,.2f}'
            })
        
        # Comparison with previous period
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            period_days = (date_to_obj - date_from_obj).days + 1
            
            prev_date_from = (date_from_obj - timedelta(days=period_days)).strftime('%Y-%m-%d')
            prev_date_to = (date_from_obj - timedelta(days=1)).strftime('%Y-%m-%d')
            
            if restaurant == 'ALL':
                prev_consumption_query = '''
                    SELECT SUM(value) as total_value FROM daily_consumption 
                    WHERE date BETWEEN ? AND ?
                '''
                prev_revenue_query = '''
                    SELECT SUM(revenue) as total_revenue FROM daily_revenue 
                    WHERE date BETWEEN ? AND ?
                '''
                prev_params = (prev_date_from, prev_date_to)
            else:
                prev_consumption_query = '''
                    SELECT SUM(value) as total_value FROM daily_consumption 
                    WHERE restaurant = ? AND date BETWEEN ? AND ?
                '''
                prev_revenue_query = '''
                    SELECT SUM(revenue) as total_revenue FROM daily_revenue 
                    WHERE restaurant = ? AND date BETWEEN ? AND ?
                '''
                prev_params = (restaurant, prev_date_from, prev_date_to)
            
            conn4 = sqlite3.connect(DB_PATH)
            prev_consumption = pd.read_sql_query(prev_consumption_query, conn4, params=prev_params)
            prev_revenue = pd.read_sql_query(prev_revenue_query, conn4, params=prev_params)
            conn4.close()
            
            prev_total_consumption = prev_consumption['total_value'].iloc[0] or 0
            prev_total_revenue = prev_revenue['total_revenue'].iloc[0] or 0
            prev_cos = round(100 * prev_total_consumption / prev_total_revenue, 1) if prev_total_revenue > 0 else 0
            
            comparison = {
                'consumption_change': round(((total_consumption - prev_total_consumption) / prev_total_consumption * 100) if prev_total_consumption > 0 else 0, 1),
                'revenue_change': round(((total_revenue - prev_total_revenue) / prev_total_revenue * 100) if prev_total_revenue > 0 else 0, 1),
                'cos_change': round(cos_percent - prev_cos, 1),
                'prev_consumption': prev_total_consumption,
                'prev_revenue': prev_total_revenue,
                'prev_cos': prev_cos
            }
        except:
            comparison = None
        
        # Restaurant comparison (if ALL selected)
        restaurant_comparison = None
        if restaurant == 'ALL':
            conn5 = sqlite3.connect(DB_PATH)
            rest_comp_query = '''
                SELECT c.restaurant, 
                       SUM(c.value) as total_consumption,
                       SUM(r.revenue) as total_revenue
                FROM daily_consumption c
                LEFT JOIN daily_revenue r ON c.restaurant = r.restaurant AND c.date = r.date
                WHERE c.date BETWEEN ? AND ?
                GROUP BY c.restaurant
            '''
            df_rest_comp = pd.read_sql_query(rest_comp_query, conn5, params=(date_from, date_to))
            conn5.close()
            
            restaurant_comparison = []
            for _, row in df_rest_comp.iterrows():
                rest_cos = round(100 * row['total_consumption'] / row['total_revenue'], 1) if row['total_revenue'] > 0 else 0
                restaurant_comparison.append({
                    'name': row['restaurant'],
                    'consumption': f'{row["total_consumption"]:,.2f}',
                    'revenue': f'{row["total_revenue"]:,.2f}',
                    'cos': rest_cos
                })
        
        # COS Alert
        cos_alert = None
        if cos_percent > 40:
            cos_alert = {
                'type': 'error',
                'message': f'⚠️ UPOZORENJE: COS je {cos_percent}%, što je iznad preporučenog nivoa (40%)!'
            }
        elif cos_percent > 35:
            cos_alert = {
                'type': 'warning',
                'message': f'⚠️ Pažnja: COS je {cos_percent}%, blizu preporučenog nivoa (40%).'
            }
        
        # Coverage note - always show warning about COS calculation
        coverage_note = "Napomena: COS se računa samo za proizvode koji su u normativi.xlsx fajlu. Ako neki proizvodi nisu u normativi, njihov promet se uključuje ali potrošnja ne, što može dati niži COS od stvarnog. Da biste dobili tačniji COS, dodajte sve proizvode koji se prodaju u normativi fajl."
        estimated_full_cos = None
        
        # Chart data for visualization
        chart_data = {
            'categories': [cat['name'] for cat in categories],
            'category_values': [float(cat['value'].replace(',', '')) for cat in categories],
            'daily_dates': [day['date'] for day in daily_data],
            'daily_revenue': [float(day['revenue'].replace(',', '')) for day in daily_data],
            'daily_consumption': [float(day['consumption'].replace(',', '')) for day in daily_data],
            'daily_cos': [day['cos'] for day in daily_data]
        }
        
        # Detailed items
        if restaurant == 'ALL':
            detail_query = '''
                SELECT category, ingredient, unit, SUM(quantity) as quantity, SUM(value) as value
                FROM daily_consumption
                WHERE date BETWEEN ? AND ?
                GROUP BY category, ingredient, unit
                ORDER BY category, value DESC
            '''
            detail_params = (date_from, date_to)
        else:
            detail_query = '''
                SELECT category, ingredient, unit, SUM(quantity) as quantity, SUM(value) as value
                FROM daily_consumption
                WHERE restaurant = ? AND date BETWEEN ? AND ?
                GROUP BY category, ingredient, unit
                ORDER BY category, value DESC
            '''
            detail_params = (restaurant, date_from, date_to)
        
        conn2 = sqlite3.connect(DB_PATH)
        df_detail = pd.read_sql_query(detail_query, conn2, params=detail_params)
        conn2.close()
        
        detailed_items = []
        for _, row in df_detail.iterrows():
            detailed_items.append({
                'category': row['category'],
                'ingredient': row['ingredient'],
                'unit': row['unit'] if pd.notna(row['unit']) else '',
                'quantity': f'{row["quantity"]:,.2f}',
                'value': f'{row["value"]:,.2f}'
            })
    else:
        categories = []
        daily_data = []
        detailed_items = []
        top_items = []
        comparison = None
        restaurant_comparison = None
        cos_alert = None
        chart_data = None
        coverage_note = None
        estimated_full_cos = None
        total_consumption = 0
        total_revenue = 0
        cos_percent = 0
        num_days = 0
    
    return render('dashboard',
                  restaurants=RESTAURANTS,
                  selected_restaurant=restaurant,
                  date_from=date_from,
                  date_to=date_to,
                  has_data=has_data,
                  categories=categories,
                  daily_data=daily_data,
                  detailed_items=detailed_items,
                  top_items=top_items,
                  comparison=comparison,
                  restaurant_comparison=restaurant_comparison,
                  cos_alert=cos_alert,
                  chart_data=chart_data,
                  total_consumption=f'{total_consumption:,.2f}',
                  total_revenue=f'{total_revenue:,.2f}',
                  cos_percent=cos_percent,
                  num_days=num_days,
                  coverage_note=coverage_note,
                  estimated_full_cos=estimated_full_cos)


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    message = None
    success = False
    
    if request.method == 'POST':
        restaurant = request.form.get('restaurant')
        file = request.files.get('report')
        
        files = request.files.getlist('report')  # Support multiple files
        bulk_upload = request.form.get('bulk_upload') == '1'
        
        if not files or (len(files) == 1 and not files[0].filename):
            message = "Molimo odaberite fajl(ove)."
        else:
            try:
                global normativi_df
                all_results = []
                validation_errors = []
                
                # Validate files
                for idx, file in enumerate(files):
                    if not file.filename:
                        continue
                    
                    # Validate file extension
                    if not (file.filename.endswith('.xls') or file.filename.endswith('.xlsx')):
                        validation_errors.append(f"{file.filename}: Neispravan format fajla. Dozvoljeni su samo .xls i .xlsx fajlovi.")
                        continue
                    
                    # Validate file size (max 50MB)
                    file.seek(0, os.SEEK_END)
                    file_size = file.tell()
                    file.seek(0)
                    # Reject empty files early with a friendly message
                    if file_size == 0:
                        validation_errors.append(f"{file.filename}: Fajl je prazan (0 bajtova). Molimo provjerite da li je fajl ispravno sačuvan i dostupan lokalno (OneDrive placeholder može biti prazan).")
                        continue
                    if file_size > 50 * 1024 * 1024:  # 50MB
                        validation_errors.append(f"{file.filename}: Fajl je prevelik (max 50MB).")
                        continue
                    
                    try:
                        result = calculate_consumption(file, normativi_df)
                        all_results.append((file.filename, result))
                    except Exception as e:
                        import traceback
                        tb = traceback.format_exc()
                        # store full traceback for debugging in validation errors
                        validation_errors.append(f"{file.filename}: Greška pri obradi - {str(e)}\nTRACEBACK:\n{tb}")
                
                if validation_errors:
                    message = "Greške pri validaciji:\n" + "\n".join(validation_errors)
                elif not all_results:
                    message = "Nijedan fajl nije uspješno obrađen."
                else:
                    # Before saving, check for any missing products in normativi across all results
                    missing_products = set()
                    for filename, result in all_results:
                        # result can be dict (multiple restaurants) or tuple
                        if isinstance(result, dict):
                            for rest_name, data in result.items():
                                if len(data) == 3:
                                    _, _, coverage_info = data
                                else:
                                    coverage_info = None
                                if coverage_info and coverage_info.get('products_not_in_norm', 0) > 0:
                                    # coverage_info['products_list'] contains sample of products
                                    for p in coverage_info.get('products_list', []):
                                        missing_products.add(p)
                        else:
                            if len(result) == 3:
                                _, _, coverage_info = result
                            else:
                                coverage_info = None
                            if coverage_info and coverage_info.get('products_not_in_norm', 0) > 0:
                                for p in coverage_info.get('products_list', []):
                                    missing_products.add(p)

                    # If there are missing products, do NOT save to DB and show full list to user
                    if len(missing_products) > 0:
                        sample_list = list(missing_products)
                        # Provide full list in the message (limit to first 500 items to avoid huge responses)
                        display_list = sample_list[:500]
                        message = (
                            "⚠️ Detektovani artikli koji NISU u `normativi.xlsx`.\n"
                            "Molimo dodajte ove proizvode u `normativi.xlsx` pa ponovo uploadajte fajl.\n"
                            f"Broj različitih nepoznatih artikala: {len(missing_products)}.\n"
                            "Prvih 500 nedostajućih (ako ih ima više):\n"
                            + "\n".join(display_list)
                        )
                        success = False
                    else:
                        # No missing products -> proceed to save all results
                        processed_restaurants = []
                        total_days = 0
                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()

                        coverage_warnings = []
                        for filename, result in all_results:
                            # Check if result is dict (multiple restaurants) or tuple (single restaurant)
                            if isinstance(result, dict):
                                for rest_name, data in result.items():
                                    if len(data) == 3:
                                        df_consumption, dates_revenue, coverage_info = data
                                    else:
                                        df_consumption, dates_revenue = data
                                        coverage_info = None
                                    actual_restaurant = rest_name if rest_name else restaurant
                                    save_to_db(actual_restaurant, df_consumption, dates_revenue)
                                    if actual_restaurant not in processed_restaurants:
                                        processed_restaurants.append(actual_restaurant)
                                    total_days += len(dates_revenue)

                                    # Check coverage
                                    if coverage_info and coverage_info['coverage_percent'] < 90:
                                        coverage_warnings.append(
                                            f"{actual_restaurant}: {coverage_info['coverage_percent']}% pokrivenost "
                                            f"({coverage_info['products_not_in_norm']} proizvoda nije u normativi, "
                                            f"{coverage_info['revenue_missing']:,.2f} KM prometa nedostaje)"
                                        )

                                    for date in dates_revenue.keys():
                                        try:
                                            parsed_date = datetime.strptime(date.strip(), '%d. %m. %Y.').strftime('%Y-%m-%d')
                                        except:
                                            parsed_date = date
                                        c.execute('INSERT INTO upload_log (restaurant, date, filename) VALUES (?, ?, ?)',
                                                  (actual_restaurant, parsed_date, filename))
                            else:
                                # Single restaurant (use selected or default)
                                if len(result) == 3:
                                    df_consumption, dates_revenue, coverage_info = result
                                else:
                                    df_consumption, dates_revenue = result
                                    coverage_info = None

                                if not restaurant and not bulk_upload:
                                    # Try to infer restaurant automatically:
                                    inferred_rest = None
                                    # If only one restaurant configured, use it
                                    try:
                                        if isinstance(RESTAURANTS, (list, tuple)) and len(RESTAURANTS) == 1:
                                            inferred_rest = RESTAURANTS[0]
                                    except Exception:
                                        inferred_rest = None

                                    # Try filename matching against known restaurants
                                    if not inferred_rest and file and getattr(file, 'filename', None):
                                        fname = file.filename.lower()
                                        for r in RESTAURANTS:
                                            try:
                                                if r.lower() in fname:
                                                    inferred_rest = r
                                                    break
                                            except Exception:
                                                continue

                                    if inferred_rest:
                                        restaurant_to_use = inferred_rest
                                    else:
                                        message = "Molimo odaberite restoran ili uploadajte fajl sa restoranima u koloni RESTAURANT."
                                        continue

                                    # Use inferred restaurant
                                    save_to_db(restaurant_to_use, df_consumption, dates_revenue)
                                    if restaurant_to_use not in processed_restaurants:
                                        processed_restaurants.append(restaurant_to_use)
                                    total_days += len(dates_revenue)

                                    # For bulk upload or when restaurant explicitly provided
                                    if restaurant:
                                        save_to_db(restaurant, df_consumption, dates_revenue)
                                        if restaurant not in processed_restaurants:
                                            processed_restaurants.append(restaurant)
                                        total_days += len(dates_revenue)

                                        for date in dates_revenue.keys():
                                            try:
                                                parsed_date = datetime.strptime(date.strip(), '%d. %m. %Y.').strftime('%Y-%m-%d')
                                            except:
                                                parsed_date = date
                                            c.execute('INSERT INTO upload_log (restaurant, date, filename) VALUES (?, ?, ?)',
                                                      (restaurant, parsed_date, filename))

                        conn.commit()
                        conn.close()

                        if processed_restaurants:
                            restaurants_str = ', '.join(processed_restaurants)
                            message = f"Uspješno učitano {len(all_results)} fajl(ova), {total_days} dana za restorane: {restaurants_str}!"
                            if coverage_warnings:
                                message += "\n\n⚠️ UPOZORENJE - Pokrivenost normativima:\n" + "\n".join(coverage_warnings)
                            success = True
                        else:
                            message = "Nijedan restoran nije pronađen u fajlovima."
            except Exception as e:
                import traceback
                message = f"Greška: {str(e)}\n{traceback.format_exc()}"
    
    # Get upload logs
    conn = sqlite3.connect(DB_PATH)
    logs = pd.read_sql_query('''
        SELECT restaurant, date, uploaded_at 
        FROM upload_log 
        ORDER BY uploaded_at DESC 
        LIMIT 20
    ''', conn)
    conn.close()
    
    upload_logs = logs.to_dict('records')
    
    return render('upload',
                  restaurants=RESTAURANTS,
                  message=message,
                  success=success,
                  upload_logs=upload_logs)


@app.route('/forecast', methods=['GET', 'POST'])
def forecast():
    restaurant = request.form.get('restaurant') or request.args.get('restaurant') or RESTAURANTS[0]
    planned_revenue = request.form.get('planned_revenue', type=float)
    forecast_type = request.form.get('forecast_type') or request.args.get('forecast_type') or 'revenue'  # 'revenue' or 'auto'
    period = request.form.get('period') or request.args.get('period') or 'all'
    
    forecast_data = None
    key_items = []
    avg_cos = 0
    forecast_total = 0
    forecast_revenue = None
    period_label = 'Svi podaci'
    revenue_forecast_data = None
    
    # Calculate date filter based on period
    date_filter_consumption = ""
    date_filter_revenue = ""
    params_list = [restaurant]
    
    if period == '7':
        date_filter_consumption = "AND c.date >= date('now', '-7 days')"
        date_filter_revenue = "AND date >= date('now', '-7 days')"
        period_label = 'Zadnjih 7 dana'
    elif period == '30':
        date_filter_consumption = "AND c.date >= date('now', '-30 days')"
        date_filter_revenue = "AND date >= date('now', '-30 days')"
        period_label = 'Zadnjih 30 dana (mjesec)'
    elif period == '90':
        date_filter_consumption = "AND c.date >= date('now', '-90 days')"
        date_filter_revenue = "AND date >= date('now', '-90 days')"
        period_label = 'Zadnjih 90 dana (kvartal)'
    else:
        period_label = 'Svi podaci'
    
    if request.method == 'POST':
        conn = sqlite3.connect(DB_PATH)

        # Get historical averages with date filter
        df = pd.read_sql_query(f'''
            SELECT c.category, c.ingredient, c.unit, 
                   SUM(c.value) as total_value,
                   SUM(c.quantity) as total_qty
            FROM daily_consumption c
            WHERE c.restaurant = ? {date_filter_consumption}
            GROUP BY c.category, c.ingredient, c.unit
        ''', conn, params=tuple(params_list))

        revenue_query = f'''
            SELECT SUM(revenue) as total_revenue
            FROM daily_revenue
            WHERE restaurant = ? {date_filter_revenue}
        '''
        revenue_data = pd.read_sql_query(revenue_query, conn, params=tuple(params_list))

        # Safely extract total historical revenue
        if len(revenue_data) > 0 and 'total_revenue' in revenue_data.columns and pd.notna(revenue_data['total_revenue'].iloc[0]):
            total_hist_revenue = float(revenue_data['total_revenue'].iloc[0])
            if total_hist_revenue == 0:
                total_hist_revenue = 1.0
        else:
            total_hist_revenue = 1.0

        total_hist_consumption = df['total_value'].sum() if 'total_value' in df.columns else 0.0
        avg_cos = round(100 * total_hist_consumption / total_hist_revenue, 1)

        # Revenue forecast (if auto mode or if we need to forecast revenue)
        if forecast_type == 'auto' or not planned_revenue:
            # Get daily revenue data for trend analysis (keep using same open conn)
            daily_rev_query = f'''
                SELECT date, revenue
                FROM daily_revenue
                WHERE restaurant = ? {date_filter_revenue}
                ORDER BY date
            '''
            daily_rev_df = pd.read_sql_query(daily_rev_query, conn, params=tuple(params_list))

            if len(daily_rev_df) > 0 and 'revenue' in daily_rev_df.columns:
                # Simple trend: average daily revenue
                avg_daily_revenue = daily_rev_df['revenue'].mean()
                # Use last 7 days average for recent trend if available
                if len(daily_rev_df) >= 7:
                    recent_avg = daily_rev_df.tail(7)['revenue'].mean()
                    forecast_revenue = recent_avg * 7  # Forecast for next 7 days
                    method = 'Trend analiza (prosjek zadnjih 7 dana)'
                else:
                    forecast_revenue = avg_daily_revenue * 7
                    method = 'Prosjek historijskih podataka (skalirano na 7 dana)'
            else:
                # Fallback
                forecast_revenue = total_hist_revenue / 30 * 7 if total_hist_revenue > 0 else 5000
                method = 'Fallback procjena'

            planned_revenue = forecast_revenue
            revenue_forecast_data = {
                'forecasted': True,
                'value': forecast_revenue,
                'method': method
            }
        else:
            revenue_forecast_data = {
                'forecasted': False,
                'value': planned_revenue,
                'method': 'Korisnički uneseno'
            }

        # Close connection after all reads
        conn.close()
        
        # Calculate forecast
        ratio = planned_revenue / total_hist_revenue if total_hist_revenue > 0 else 0
        
        # Category forecast
        cat_forecast = df.groupby('category')['total_value'].sum() * ratio
        forecast_total = cat_forecast.sum()
        
        forecast_data = []
        for cat, val in cat_forecast.sort_values(ascending=False).items():
            forecast_data.append({
                'name': cat,
                'value': f'{val:,.2f}',
                'pct': round(100 * val / forecast_total, 1) if forecast_total > 0 else 0
            })
        
        # ALL items forecast (grouped by category)
        df['forecast_qty'] = df['total_qty'] * ratio
        df['forecast_value'] = df['total_value'] * ratio
        df_sorted = df.sort_values(['category', 'forecast_value'], ascending=[True, False])
        
        for _, row in df_sorted.iterrows():
            key_items.append({
                'category': row['category'],
                'name': row['ingredient'],
                'qty': f'{row["forecast_qty"]:,.2f}',
                'unit': row['unit'],
                'value': f'{row["forecast_value"]:,.2f}'
            })
    
    return render('forecast',
                  restaurants=RESTAURANTS,
                  selected_restaurant=restaurant,
                  planned_revenue=planned_revenue,
                  forecast_type=forecast_type,
                  period=period,
                  period_label=period_label,
                  forecast=forecast_data,
                  key_items=key_items,
                  avg_cos=avg_cos,
                  forecast_total=f'{forecast_total:,.2f}',
                  revenue_forecast=revenue_forecast_data)


@app.route('/export')
def export():
    restaurant = request.args.get('restaurant', 'ALL')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    format_type = request.args.get('format', 'excel')  # 'excel' or 'pdf'
    
    conn = sqlite3.connect(DB_PATH)
    
    if restaurant == 'ALL':
        df = pd.read_sql_query('''
            SELECT restaurant, date, category, ingredient, unit, quantity, value
            FROM daily_consumption
            WHERE date BETWEEN ? AND ?
            ORDER BY date, category
        ''', conn, params=(date_from, date_to))
        
        revenue_df = pd.read_sql_query('''
            SELECT date, SUM(revenue) as revenue
            FROM daily_revenue
            WHERE date BETWEEN ? AND ?
            GROUP BY date
        ''', conn, params=(date_from, date_to))
    else:
        df = pd.read_sql_query('''
            SELECT restaurant, date, category, ingredient, unit, quantity, value
            FROM daily_consumption
            WHERE restaurant = ? AND date BETWEEN ? AND ?
            ORDER BY date, category
        ''', conn, params=(restaurant, date_from, date_to))
        
        revenue_df = pd.read_sql_query('''
            SELECT date, revenue
            FROM daily_revenue
            WHERE restaurant = ? AND date BETWEEN ? AND ?
        ''', conn, params=(restaurant, date_from, date_to))
    
    conn.close()
    
    if format_type == 'pdf':
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            
            output = BytesIO()
            doc = SimpleDocTemplate(output, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#b5002a'),
                spaceAfter=30,
                alignment=1  # Center
            )
            elements.append(Paragraph(f'KFC COS Izvještaj - {restaurant}', title_style))
            elements.append(Paragraph(f'Period: {date_from} - {date_to}', styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
            
            # Summary
            total_consumption = df['value'].sum()
            total_revenue = revenue_df['revenue'].sum() if len(revenue_df) > 0 else 0
            cos_percent = round(100 * total_consumption / total_revenue, 1) if total_revenue > 0 else 0
            
            summary_data = [
                ['Ukupna potrošnja', f'{total_consumption:,.2f} KM'],
                ['Ukupan promet', f'{total_revenue:,.2f} KM'],
                ['COS %', f'{cos_percent}%']
            ]
            summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#b5002a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Category summary
            elements.append(Paragraph('Potrošnja po kategorijama', styles['Heading2']))
            category_summary = df.groupby('category')['value'].sum().sort_values(ascending=False)
            cat_data = [['Kategorija', 'Vrijednost (KM)', '%']]
            for cat, val in category_summary.items():
                pct = round(100 * val / total_consumption, 1)
                cat_data.append([cat, f'{val:,.2f}', f'{pct}%'])
            
            cat_table = Table(cat_data, colWidths=[3*inch, 2*inch, 1*inch])
            cat_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#b5002a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            elements.append(cat_table)
            elements.append(PageBreak())
            
            # Detailed items (first 100 rows to avoid huge PDFs)
            elements.append(Paragraph('Detaljna potrošnja (prvih 100 redova)', styles['Heading2']))
            detail_df = df.head(100)
            detail_data = [['Datum', 'Kategorija', 'Sirovina', 'Količina', 'JM', 'Vrijednost']]
            for _, row in detail_df.iterrows():
                detail_data.append([
                    str(row['date']),
                    str(row['category']),
                    str(row['ingredient'])[:30],  # Truncate long names
                    f'{row["quantity"]:,.2f}',
                    str(row['unit']),
                    f'{row["value"]:,.2f}'
                ])
            
            detail_table = Table(detail_data, colWidths=[0.8*inch, 1*inch, 1.5*inch, 0.8*inch, 0.5*inch, 1*inch])
            detail_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#b5002a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            elements.append(detail_table)
            
            doc.build(elements)
            output.seek(0)
            return send_file(output,
                           mimetype='application/pdf',
                           as_attachment=True,
                           download_name=f'cos_export_{date_from}_{date_to}.pdf')
        except ImportError:
            # Fallback to Excel if reportlab not installed
            format_type = 'excel'
    
    # Excel export (default or fallback)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Detalji', index=False)
        
        # Summary
        summary = df.groupby('category')['value'].sum().reset_index()
        summary.columns = ['Kategorija', 'Vrijednost (KM)']
        summary.to_excel(writer, sheet_name='Sumarno', index=False)
    
    output.seek(0)
    return send_file(output,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True,
                     download_name=f'cos_export_{date_from}_{date_to}.xlsx')


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/backup')
def backup():
    """Create backup of database"""
    try:
        backup_filename = f'kfc_cos_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        backup_path = os.path.join(os.path.dirname(DB_PATH), backup_filename)
        
        # Copy database
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        
        return send_file(backup_path,
                        mimetype='application/x-sqlite3',
                        as_attachment=True,
                        download_name=backup_filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/restore', methods=['POST'])
def restore():
    """Restore database from backup"""
    try:
        file = request.files.get('backup_file')
        if not file:
            return jsonify({'error': 'No file provided'}), 400
        
        # Save uploaded file
        backup_path = os.path.join(os.path.dirname(DB_PATH), 'restore_backup.db')
        file.save(backup_path)
        
        # Backup current database first
        current_backup = f'{DB_PATH}.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        import shutil
        shutil.copy2(DB_PATH, current_backup)
        
        # Restore
        shutil.copy2(backup_path, DB_PATH)
        
        # Clear cached normativi
        global normativi_df
        normativi_df = None
        
        return jsonify({'success': True, 'message': 'Database restored successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
