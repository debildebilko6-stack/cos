import json
import sys
from pathlib import Path

path = r"c:\Users\Adna-Marketing\Downloads\COS_Normativi_FINAL (1).xlsx"
if not Path(path).exists():
    print(json.dumps({"error": "file not found", "path": path}, ensure_ascii=False))
    sys.exit(0)

try:
    import pandas as pd
except Exception as e:
    print(json.dumps({"error": f"pandas import error: {e}"}, ensure_ascii=False))
    sys.exit(0)

try:
    xls = pd.ExcelFile(path)
    out = {"sheets": {}}
    for s in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=s, nrows=5)
        out["sheets"][s] = {
            "columns": [str(c) for c in df.columns.tolist()],
            "head": df.fillna("").astype(str).to_dict(orient='records')
        }
    print(json.dumps(out, ensure_ascii=False))
except Exception as e:
    print(json.dumps({"error": str(e)} , ensure_ascii=False))
    sys.exit(0)
