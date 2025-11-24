import shutil, os
p = r'C:\Users\Adna-Marketing\Downloads\kfc-cos-app-v2\kfc-cos-app-v2'
src = os.path.join(p,'normativi_fixed.xlsx')
dst = os.path.join(p,'normativi.xlsx')
bak = os.path.join(p,'normativi_backup.xlsx')

print('src=', src)
print('dst=', dst)
print('bak=', bak)

if os.path.exists(dst):
    try:
        shutil.copy2(dst,bak)
        print('backup created', bak)
    except Exception as e:
        print('backup failed:', e)
else:
    print('original not found, skipping backup')

try:
    shutil.copy2(src,dst)
    print('replaced:', dst, 'from', src)
    print('sizes:', os.path.getsize(src), os.path.getsize(dst))
except Exception as e:
    print('replace failed:', e)
