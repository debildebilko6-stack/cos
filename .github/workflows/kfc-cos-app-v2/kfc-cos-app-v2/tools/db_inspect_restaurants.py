import sqlite3, pandas as pd, os
DB = os.path.join(os.path.dirname(__file__), '..', 'kfc_cos.db')
DB = os.path.abspath(DB)
print('DB path:', DB)
if not os.path.exists(DB):
    print('DB not found')
    raise SystemExit(1)
conn = sqlite3.connect(DB)
try:
    df = pd.read_sql_query("SELECT restaurant, COUNT(*) as cnt FROM daily_consumption GROUP BY restaurant ORDER BY cnt DESC", conn)
    print('daily_consumption counts per restaurant:')
    print(df.to_string(index=False))
except Exception as e:
    print('Error querying daily_consumption:', e)

try:
    logs = pd.read_sql_query("SELECT restaurant, COUNT(*) as uploads FROM upload_log GROUP BY restaurant ORDER BY uploads DESC", conn)
    print('\nupload_log counts per restaurant:')
    print(logs.to_string(index=False))
except Exception as e:
    print('Error querying upload_log:', e)

# show last 10 upload_log rows
try:
    recent = pd.read_sql_query("SELECT restaurant, date, filename, uploaded_at FROM upload_log ORDER BY uploaded_at DESC LIMIT 20", conn)
    print('\nRecent upload_log (last 20):')
    print(recent.to_string(index=False))
except Exception as e:
    print('Error querying recent logs:', e)

conn.close()
