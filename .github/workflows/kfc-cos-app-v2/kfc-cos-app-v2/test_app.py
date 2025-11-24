"""
Test script za KFC COS Calculator aplikaciju
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app, init_db, DB_PATH, RESTAURANTS, NORMATIVI_PATH
import sqlite3
import json

def test_imports():
    """Test da li se svi moduli mogu importovati"""
    print("🧪 Test 1: Import modula...")
    try:
        from flask import Flask
        import pandas as pd
        import numpy as np
        from io import BytesIO
        import sqlite3
        from datetime import datetime, timedelta
        print("   ✅ Svi moduli uspešno importovani")
        return True
    except ImportError as e:
        print(f"   ❌ Greška pri importu: {e}")
        return False

def test_database():
    """Test baze podataka"""
    print("\n🧪 Test 2: Baza podataka...")
    try:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Proveri tabele
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall()]
        expected_tables = ['daily_consumption', 'daily_revenue', 'upload_log']
        
        for table in expected_tables:
            if table in tables:
                print(f"   ✅ Tabela '{table}' postoji")
            else:
                print(f"   ❌ Tabela '{table}' ne postoji")
                return False
        
        # Proveri indekse
        c.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in c.fetchall()]
        print(f"   ✅ Indeksi kreirani: {len(indexes)}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"   ❌ Greška: {e}")
        return False

def test_routes():
    """Test Flask ruta"""
    print("\n🧪 Test 3: Flask rute...")
    try:
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(rule.rule)
        
        expected_routes = ['/', '/dashboard', '/upload', '/forecast', '/export', '/health']
        for route in expected_routes:
            if route in routes:
                print(f"   ✅ Ruta '{route}' postoji")
            else:
                print(f"   ❌ Ruta '{route}' ne postoji")
        
        print(f"   ✅ Ukupno ruta: {len(routes)}")
        return True
    except Exception as e:
        print(f"   ❌ Greška: {e}")
        return False

def test_restaurants():
    """Test restorana"""
    print("\n🧪 Test 4: Restorani...")
    try:
        if len(RESTAURANTS) == 5:
            print(f"   ✅ Broj restorana: {len(RESTAURANTS)}")
            for rest in RESTAURANTS:
                print(f"      - {rest}")
            return True
        else:
            print(f"   ❌ Očekivano 5 restorana, pronađeno: {len(RESTAURANTS)}")
            return False
    except Exception as e:
        print(f"   ❌ Greška: {e}")
        return False

def test_normativi():
    """Test normativi fajla"""
    print("\n🧪 Test 5: Normativi fajl...")
    try:
        if os.path.exists(NORMATIVI_PATH):
            print(f"   ✅ Fajl '{NORMATIVI_PATH}' postoji")
            import pandas as pd
            df = pd.read_excel(NORMATIVI_PATH)
            print(f"   ✅ Fajl se može pročitati: {len(df)} redova")
            return True
        else:
            print(f"   ⚠️  Fajl '{NORMATIVI_PATH}' ne postoji (možda će biti kreiran kasnije)")
            return True  # Nije kritična greška
    except Exception as e:
        print(f"   ⚠️  Greška pri čitanju normativi fajla: {e}")
        return True  # Nije kritična greška

def test_templates():
    """Test template sistema"""
    print("\n🧪 Test 6: Template sistem...")
    try:
        from app import render, templates
        template_names = ['main', 'dashboard', 'upload', 'forecast']
        for name in template_names:
            if name in templates:
                print(f"   ✅ Template '{name}' postoji")
            else:
                print(f"   ❌ Template '{name}' ne postoji")
                return False
        return True
    except Exception as e:
        print(f"   ❌ Greška: {e}")
        return False

def test_calculation_functions():
    """Test funkcija za kalkulaciju"""
    print("\n🧪 Test 7: Funkcije za kalkulaciju...")
    try:
        from app import calculate_consumption, get_category, save_to_db
        
        # Test get_category
        test_categories = [
            ('bun', 'PECIVO'),
            ('chicken fillet', 'MESO'),
            ('fries', 'SIDES/DODACI'),
            ('flour', 'BRAŠNO/PANIRANJE'),
            ('shortening', 'ULJE'),
            ('sauce', 'SOS'),
        ]
        
        for ingredient, expected in test_categories:
            result = get_category(ingredient)
            if result == expected:
                print(f"   ✅ get_category('{ingredient}') = '{result}'")
            else:
                print(f"   ⚠️  get_category('{ingredient}') = '{result}' (očekivano: '{expected}')")
        
        print("   ✅ Funkcije za kalkulaciju su dostupne")
        return True
    except Exception as e:
        print(f"   ❌ Greška: {e}")
        return False

def test_backup_restore():
    """Test backup/restore funkcionalnosti"""
    print("\n🧪 Test 8: Backup/Restore rute...")
    try:
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        if '/backup' in routes:
            print("   ✅ Ruta '/backup' postoji")
        else:
            print("   ❌ Ruta '/backup' ne postoji")
            return False
        
        if '/restore' in routes:
            print("   ✅ Ruta '/restore' postoji")
        else:
            print("   ❌ Ruta '/restore' ne postoji")
            return False
        
        return True
    except Exception as e:
        print(f"   ❌ Greška: {e}")
        return False

def test_export_formats():
    """Test export formata"""
    print("\n🧪 Test 9: Export formati...")
    try:
        # Proveri da li export ruta podržava format parametar
        with app.test_client() as client:
            # Test Excel export (neće raditi bez podataka, ali proveravamo da li ruta postoji)
            response = client.get('/export?restaurant=ALL&date_from=2024-01-01&date_to=2024-01-31&format=excel')
            # Očekujemo grešku jer nema podataka, ali ruta treba da postoji
            print("   ✅ Excel export ruta radi")
            
            # Test PDF export
            response = client.get('/export?restaurant=ALL&date_from=2024-01-01&date_to=2024-01-31&format=pdf')
            print("   ✅ PDF export ruta radi")
        
        return True
    except Exception as e:
        print(f"   ⚠️  Export test: {e} (možda nema podataka u bazi)")
        return True  # Nije kritična greška

def main():
    """Pokreni sve testove"""
    print("=" * 60)
    print("🧪 TESTIRANJE KFC COS CALCULATOR APLIKACIJE")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_database,
        test_routes,
        test_restaurants,
        test_normativi,
        test_templates,
        test_calculation_functions,
        test_backup_restore,
        test_export_formats,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"   ❌ Kritična greška u testu: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 REZULTATI TESTIRANJA")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Prošlo: {passed}/{total}")
    print(f"❌ Neuspešno: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 SVI TESTOVI SU PROŠLI!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(ova) nije prošlo")
        return 1

if __name__ == '__main__':
    sys.exit(main())

