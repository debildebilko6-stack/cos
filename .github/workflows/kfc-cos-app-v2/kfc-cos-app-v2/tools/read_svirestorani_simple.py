import pandas as pd, os
p=r'C:\Users\Adna-Marketing\Downloads\kfc-cos-app-v2\kfc-cos-app-v2\svirestorani.xlsx'
print('path',p,'exists',os.path.exists(p))
if os.path.exists(p):
    df=pd.read_excel(p)
    print('shape',df.shape)
    print('columns',df.columns.tolist())
    for c in df.columns:
        s=df[c].dropna().astype(str).str.strip()
        if s.shape[0]>0:
            print('picked col',c,'unique_count',len(s.unique()))
            print('sample',s.unique()[:10])
            break
