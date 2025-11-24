import sys, os, io
sys.path.insert(0, os.path.join(os.getcwd(), 'kfc-cos-app-v2'))
from app import app, init_db

def run():
    # Use temp DB
    test_db = os.path.join(os.getcwd(), '..', 'test_verbose.db')
    if os.path.exists(test_db):
        os.remove(test_db)
    import app as appmod
    orig_db = appmod.DB_PATH
    appmod.DB_PATH = test_db
    try:
        init_db()
        client = app.test_client()
        report_path = r'C:\Users\Adna-Marketing\Downloads\REPORT BY COMBOS1.xls'
        with open(report_path, 'rb') as f:
            data = {'restaurant': '', 'report': (io.BytesIO(f.read()), 'REPORT BY COMBOS1.xls')}
            resp = client.post('/upload', data=data, content_type='multipart/form-data')
        print('status:', resp.status_code)
        body = resp.get_data(as_text=True)
        # print full body
        print('\n--- RESPONSE BODY START ---\n')
        print(body)
        print('\n--- RESPONSE BODY END ---\n')
    finally:
        appmod.DB_PATH = orig_db

if __name__ == '__main__':
    run()
