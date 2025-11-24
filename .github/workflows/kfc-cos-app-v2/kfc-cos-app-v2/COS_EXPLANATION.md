# 📊 Objašnjenje razlike u COS-u

## Problem

**Prosječan COS na sve artikle:** 26.50%  
**Dnevni COS u aplikaciji:** 18.4%  
**Razlika:** ~8.1%

## Zašto postoji razlika?

Aplikacija računa COS **samo za proizvode koji su u normativi.xlsx fajlu**. 

### Kako aplikacija računa COS:

1. **Uzima promet** - Svi proizvodi koji su prodati (uključujući i one koji nisu u normativi)
2. **Računa potrošnju** - SAMO za proizvode koji su u normativi fajlu
3. **Formula:** `COS = (Potrošnja / Promet) × 100`

### Problem:

Ako neki proizvodi **nisu u normativi fajlu**:
- ✅ Njihov **promet se uključuje** u ukupan promet
- ❌ Njihova **potrošnja se NE uključuje** (jer nema normativa)
- 📉 Rezultat: **Niži COS** jer imate promet bez potrošnje

### Primer:

```
Ukupan promet: 10,000 KM
Potrošnja (samo proizvodi u normativi): 1,840 KM
COS u aplikaciji: 18.4%

Ali ako imate proizvode koji nisu u normativi:
- Promet tih proizvoda: 2,000 KM (uključeno u 10,000)
- Potrošnja tih proizvoda: ~650 KM (NISU uključene jer nema normativa)

Stvarni COS bi bio:
(1,840 + 650) / 10,000 = 24.9%
```

## Rješenje

### 1. Dodajte sve proizvode u normativi.xlsx

Aplikacija će automatski:
- ✅ Detektovati proizvode koji nisu u normativi
- ✅ Prikazati upozorenje pri uploadu
- ✅ Pokazati koliko % prometa nedostaje

### 2. Proverite coverage upozorenja

Kada uploadujete fajl, aplikacija će prikazati:
```
⚠️ UPOZORENJE - Pokrivenost normativima:
KFC SCC: 85.2% pokrivenost (15 proizvoda nije u normativi, 1,234.56 KM prometa nedostaje)
```

### 3. Ažurirajte normativi.xlsx

Dodajte nedostajuće proizvode sa njihovim normativima (sirovinama i količinama).

## Kako proveriti koje proizvode nedostaju?

1. Uploadujte izvještaj
2. Aplikacija će automatski prikazati upozorenje sa listom proizvoda koji nedostaju
3. Dodajte te proizvode u normativi.xlsx fajl
4. Ponovo uploadujte - COS će biti tačniji

## Napomena

Aplikacija sada prikazuje upozorenje na dashboard-u kada COS može biti niži zbog nedostajućih proizvoda u normativi fajlu.

---

**Trenutno stanje:** Aplikacija računa COS samo za proizvode u normativi, što objašnjava razliku od ~8.1%.

**Rješenje:** Dodajte sve proizvode koji se prodaju u normativi.xlsx fajl.

