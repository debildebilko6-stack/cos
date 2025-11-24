from pathlib import Path
s = Path('forecast_test_output.html').read_text(encoding='utf-8')
keys = ['Trend analiza', 'PROGNOZIRANI PROMET', 'Automatska prognoza', 'PROGNOZIRANI', 'Prognoza', 'PROGNOZIRANI PROMET', '7 dana']
for key in keys:
    if key in s:
        i = s.index(key)
        print('---', key, '---')
        print(s[i-200:i+200])
    else:
        print('Not found:', key)
