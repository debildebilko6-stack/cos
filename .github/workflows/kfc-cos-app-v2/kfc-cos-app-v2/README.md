# 🍗 KFC COS Calculator v2

Web aplikacija za izračunavanje Cost of Sales (COS) za KFC restorane u Bosni i Hercegovini.

## 📋 Funkcionalnosti

- **Multi-restaurant support** - Podrška za više restorana (KFC SCC, KFC MCC, KFC BCC, KFC STM, KFC ICC)
- **Upload dnevnih izvještaja** - Automatska obrada XLS/XLSX prodajnih izvještaja
- **SQLite baza podataka** - Centralizovano čuvanje podataka o potrošnji i prometu
- **Dashboard** - Pregled potrošnje sa filterima po restoranu i datumu
- **Prognoza potrošnje** - Izračun potrebnih sirovina na osnovu planiranog prometa
- **Export u Excel** - Izvoz podataka za dalju analizu

## 🚀 Instalacija

### Windows

1. Instaliraj Python 3.10 ili noviji
2. Otvori PowerShell u folderu projekta
3. Instaliraj zavisnosti:
```powershell
python -m pip install -r requirements.txt
```

### Linux/Mac

```bash
chmod +x setup.sh
./setup.sh
```

Ili ručno:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 📁 Struktura projekta

```
kfc-cos-app-v2/
├── app.py              # Glavna Flask aplikacija
├── normativi.xlsx      # Excel fajl sa normativima proizvoda
├── requirements.txt    # Python zavisnosti
├── setup.sh           # Setup skripta za Linux
├── README.md          # Ovaj fajl
└── .gitignore         # Git ignore fajl
```

## 🎯 Pokretanje aplikacije

### Windows

```powershell
python app.py
```

### Linux/Mac

```bash
source venv/bin/activate
python app.py
```

Ili sa Gunicorn (produkcija):
```bash
gunicorn --bind 0.0.0.0:8080 app:app
```

Aplikacija će biti dostupna na: `http://localhost:8080`

## 📊 Korišćenje

### 1. Upload izvještaja

1. Idi na `/upload` stranicu
2. Odaberi restoran
3. Uploaduj XLS/XLSX prodajni izvještaj
4. Aplikacija će automatski:
   - Parsirati izvještaj
   - Izračunati potrošnju po kategorijama
   - Sačuvati podatke u bazu

### 2. Pregled Dashboard-a

1. Idi na `/dashboard` (ili glavnu stranicu)
2. Filtriraj po:
   - Restoranu (ili "Svi restorani")
   - Datumu (od-do)
3. Pregledaj:
   - Ukupnu potrošnju i promet
   - COS % (Cost of Sales)
   - Potrošnju po kategorijama
   - Dnevnu potrošnju
   - Detaljnu potrošnju po sirovinama

### 3. Prognoza potrošnje

1. Idi na `/forecast`
2. Odaberi restoran
3. Unesi planirani promet (u KM)
4. Aplikacija će izračunati potrebne sirovine na osnovu historijskih podataka

### 4. Export podataka

Na dashboard stranici klikni na "📥 Export Excel" da preuzmeš podatke u Excel formatu.

## 🗄️ Baza podataka

Aplikacija koristi SQLite bazu podataka (`kfc_cos.db`) sa sledećim tabelama:

- `daily_consumption` - Dnevna potrošnja po kategorijama i sirovinama
- `daily_revenue` - Dnevni promet po restoranu
- `upload_log` - Log uploadovanih izvještaja

## 🔧 Konfiguracija

Možeš podesiti putanje preko environment varijabli:

- `DB_PATH` - Putanja do SQLite baze (default: `kfc_cos.db`)
- `NORMATIVI_PATH` - Putanja do normativi.xlsx fajla (default: `normativi.xlsx`)
- `PORT` - Port na kom će aplikacija raditi (default: `8080`)

## 📝 Kategorije sirovina

Aplikacija automatski kategorizuje sirovine u:

- **PECIVO** - Bun, tortilla
- **MESO** - Pileće meso, fillet, strips, krilca
- **SIDES/DODACI** - Pomfrit, hashbrown, coleslaw, itd.
- **BRAŠNO/PANIRANJE** - Flour, breading
- **MARINADA** - Marinade
- **ULJE** - Shortening, oil
- **SOS** - Sauce, mayo, ketchup
- **PIĆE** - Sirup, cola, kafa, mleko
- **POVRĆE** - Iceberg, paradajz, pickle, luk
- **SIR** - Cheese
- **DESERT** - Donut, sladoled, itd.
- **AMBALAŽA** - Box, bag, cup, tray, itd.
- **ZAČINI** - Salt
- **OSTALO** - Sve ostalo

## 🐛 Troubleshooting

### Problem: "ModuleNotFoundError"
**Rešenje:** Instaliraj sve zavisnosti: `pip install -r requirements.txt`

### Problem: "normativi.xlsx not found"
**Rešenje:** Proveri da li fajl `normativi.xlsx` postoji u istom folderu kao `app.py`

### Problem: Aplikacija ne može da parsira XLS fajl
**Rešenje:** Proveri da li je fajl u ispravnom formatu (prodajni izvještaj iz sistema)

## 📄 Licenca

Interni projekat za KFC BiH.

## 👥 Autor

KFC COS Calculator v2

---

**Napomena:** Ova aplikacija je dizajnirana za internu upotrebu u KFC restoranima u Bosni i Hercegovini.

