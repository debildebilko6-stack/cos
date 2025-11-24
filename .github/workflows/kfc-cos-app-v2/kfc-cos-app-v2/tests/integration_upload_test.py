import sys
import os
import io
import sqlite3

sys.path.insert(0, os.path.join(os.getcwd(), 'kfc-cos-app-v2'))
from app import app, init_db


def main():
    # Ensure DB is initialized and use a test DB file
    test_db = os.path.join(os.getcwd(), '..', 'test_integration.db')
    if os.path.exists(test_db):
        os.remove(test_db)

    # Monkeypatch DB_PATH in app module
    import app as appmod
    orig_db = appmod.DB_PATH
    appmod.DB_PATH = test_db
    try:
        init_db()
        # Ensure normativi_df is loaded for the app (some test contexts may not trigger before_request)
        import pandas as pd
        norm_path = os.path.join(os.path.dirname(appmod.__file__), appmod.NORMATIVI_PATH)
        appmod.normativi_df = pd.read_excel(norm_path)

        client = app.test_client()

        report_path = r'C:\Users\Adna-Marketing\Downloads\REPORT BY COMBOS1.xls'
        with open(report_path, 'rb') as f:
            data = {
                # specify a restaurant so upload route will save single-file uploads
                'restaurant': 'KFC SCC',
                'report': (io.BytesIO(f.read()), 'REPORT BY COMBOS1.xls')
            }
            resp = client.post('/upload', data=data, content_type='multipart/form-data')

        print('Upload response status:', resp.status_code)
        body = resp.get_data(as_text=True)
        # Print a snippet to inspect success or error messages
        start = body.find('<div class="alert')
        if start != -1:
            print('Alert snippet:')
            print(body[start:start+400])
        else:
            print('No alert snippet found; printing first 400 chars of response:')
            print(body[:400])

        # Check DB entries
        conn = sqlite3.connect(test_db)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM upload_log")
        uploads = c.fetchone()[0]
        print('upload_log rows:', uploads)
        c.execute("SELECT COUNT(*) FROM daily_consumption")
        cons = c.fetchone()[0]
        print('daily_consumption rows:', cons)
        conn.close()

    finally:
        appmod.DB_PATH = orig_db


if __name__ == '__main__':
    main()
