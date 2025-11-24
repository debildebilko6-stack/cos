import sys
from pathlib import Path

# Ensure project root is on sys.path so we can import app
proj_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(proj_root))

from app import init_db, DB_PATH, RESTAURANTS
import sqlite3
from datetime import datetime, timedelta

# Initialize DB and insert sample revenue data for the first restaurant
init_db()
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

restaurant = RESTAURANTS[0]
# Clear existing revenue for safety
c.execute("DELETE FROM daily_revenue WHERE restaurant = ?", (restaurant,))

# Insert 10 days of revenue
today = datetime.now().date()
for i in range(10):
    d = (today - timedelta(days=10-i)).strftime('%Y-%m-%d')
    revenue = 1000 + i * 50  # increasing revenue
    c.execute('INSERT OR REPLACE INTO daily_revenue (restaurant, date, revenue) VALUES (?, ?, ?)',
              (restaurant, d, revenue))

conn.commit()
conn.close()

# Use Flask test client to POST to /forecast
from app import app

with app.test_client() as client:
    resp = client.post('/forecast', data={'restaurant': restaurant, 'forecast_type': 'auto'})
    print('Status code:', resp.status_code)
    # Print a short excerpt of the response text to confirm forecast shows up
    text = resp.get_data(as_text=True)
    print(text[:1000])
    # Optionally save full HTML to file
    with open('forecast_test_output.html', 'w', encoding='utf-8') as f:
        f.write(text)
    print('Full output saved to forecast_test_output.html')
