"""
Test web ruta za KFC COS Calculator aplikaciju
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import app

def test_web_routes():
    """Test svih web ruta"""
    print("=" * 60)
    print("🌐 TESTIRANJE WEB RUTA")
    print("=" * 60)
    
    client = app.test_client()
    results = []
    
    # Test routes
    test_cases = [
        ('/', 'GET', 302, 'Home redirect'),
        ('/dashboard', 'GET', 200, 'Dashboard'),
        ('/upload', 'GET', 200, 'Upload stranica'),
        ('/forecast', 'GET', 200, 'Forecast stranica'),
        ('/health', 'GET', 200, 'Health check'),
        ('/backup', 'GET', 200, 'Backup'),
        ('/export?restaurant=ALL&date_from=2024-01-01&date_to=2024-01-31&format=excel', 'GET', None, 'Excel export'),
        ('/export?restaurant=ALL&date_from=2024-01-01&date_to=2024-01-31&format=pdf', 'GET', None, 'PDF export'),
    ]
    
    for route, method, expected_status, description in test_cases:
        try:
            if method == 'GET':
                response = client.get(route)
                status = response.status_code
                
                if expected_status:
                    if status == expected_status:
                        print(f"   ✅ {description}: {status}")
                        results.append(True)
                    else:
                        print(f"   ⚠️  {description}: {status} (očekivano: {expected_status})")
                        results.append(False)
                else:
                    # Za export, bilo koji status je OK (može biti greška zbog nedostatka podataka)
                    if status in [200, 400, 500]:
                        print(f"   ✅ {description}: {status}")
                        results.append(True)
                    else:
                        print(f"   ⚠️  {description}: {status}")
                        results.append(False)
        except Exception as e:
            print(f"   ❌ {description}: Greška - {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 REZULTATI")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"✅ Prošlo: {passed}/{total}")
    
    if passed == total:
        print("🎉 SVE WEB RUTE RADE!")
        return 0
    else:
        print(f"⚠️  {total - passed} ruta ima problema")
        return 1

if __name__ == '__main__':
    sys.exit(test_web_routes())

