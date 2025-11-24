import sqlite3, os, pandas as pd

test_db = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_integration.db'))
print('test_db path:', test_db)
if not os.path.exists(test_db):
    print('test_db not found')
    raise SystemExit(1)
conn = sqlite3.connect(test_db)
try:
    df1 = pd.read_sql_query('SELECT COUNT(*) as cnt FROM upload_log', conn)
    df2 = pd.read_sql_query('SELECT COUNT(*) as cnt FROM daily_consumption', conn)
    print('upload_log rows:', int(df1['cnt'].iloc[0]))
    print('daily_consumption rows:', int(df2['cnt'].iloc[0]))
    recent = pd.read_sql_query("SELECT restaurant, date, filename, uploaded_at FROM upload_log ORDER BY uploaded_at DESC LIMIT 20", conn)
    print('\nRecent uploads:')
    print(recent.to_string(index=False))
finally:
    conn.close()
