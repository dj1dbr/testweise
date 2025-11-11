#!/usr/bin/env python3
"""
Test-Script für Mac Setup
Prüft ob alle Komponenten funktionieren
"""

import sys
import os

print("=" * 60)
print("ROHSTOFF TRADER - MAC SETUP TEST")
print("=" * 60)
print()

# Test 1: MongoDB
print("1. MongoDB Connection Test...")
try:
    from pymongo import MongoClient
    client = MongoClient('mongodb://localhost:27017', serverSelectionTimeoutMS=2000)
    client.server_info()
    print("   ✅ MongoDB läuft auf localhost:27017")
    
    # Check database
    db = client['rohstoff_trader']
    settings = db.trading_settings.find_one({"id": "trading_settings"})
    if settings:
        print(f"   ✅ Trading Settings gefunden")
        print(f"      - Aktive Plattformen: {settings.get('active_platforms', [])}")
        print(f"      - Auto Trading: {settings.get('auto_trading', False)}")
    else:
        print("   ⚠️  Keine Trading Settings in DB - werden beim ersten Start erstellt")
    
except Exception as e:
    print(f"   ❌ MongoDB Fehler: {e}")
    print("   → Starten Sie MongoDB: brew services start mongodb-community")

print()

# Test 2: yfinance
print("2. yfinance Test...")
try:
    import yfinance as yf
    ticker = yf.Ticker("GC=F")
    # Quick check without full download
    info = ticker.info
    print(f"   ✅ yfinance funktioniert")
except Exception as e:
    print(f"   ⚠️  yfinance Problem: {e}")
    print("   → Möglicherweise Rate-Limited, warten Sie 30-60 Minuten")

print()

# Test 3: Backend-Abhängigkeiten
print("3. Backend Dependencies Test...")
missing = []
try:
    import fastapi
    print(f"   ✅ fastapi: {fastapi.__version__}")
except:
    missing.append("fastapi")

try:
    import uvicorn
    print(f"   ✅ uvicorn: {uvicorn.__version__}")
except:
    missing.append("uvicorn")

try:
    import motor
    print(f"   ✅ motor (async MongoDB)")
except:
    missing.append("motor")

try:
    import pandas
    print(f"   ✅ pandas: {pandas.__version__}")
except:
    missing.append("pandas")

try:
    import ta
    print(f"   ✅ ta (Technical Analysis)")
except:
    missing.append("ta")

if missing:
    print(f"   ❌ Fehlende Pakete: {', '.join(missing)}")
    print(f"   → Installieren: pip install {' '.join(missing)}")

print()

# Test 4: .env Datei
print("4. Environment Variables Test...")
if os.path.exists('.env'):
    print("   ✅ .env Datei existiert")
    with open('.env', 'r') as f:
        lines = f.readlines()
        for line in lines:
            if 'METAAPI_ACCOUNT_ID' in line and '=' in line:
                key, value = line.split('=', 1)
                if value.strip() and 'IHR_' not in value and 'multiplatform' not in value:
                    print(f"   ✅ {key.strip()}: Konfiguriert")
                else:
                    print(f"   ⚠️  {key.strip()}: Nicht konfiguriert")
            elif 'BITPANDA_API_KEY' in line and '=' in line:
                key, value = line.split('=', 1)
                if value.strip() and len(value.strip()) > 20:
                    print(f"   ✅ {key.strip()}: Konfiguriert")
                else:
                    print(f"   ⚠️  {key.strip()}: Nicht konfiguriert")
else:
    print("   ❌ .env Datei nicht gefunden!")
    print("   → Erstellen Sie eine .env Datei mit Ihren API-Keys")

print()

# Test 5: Port-Check
print("5. Port Availability Test...")
import socket

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

backend_port = 8001
if is_port_in_use(backend_port):
    print(f"   ⚠️  Port {backend_port} ist bereits belegt")
    print(f"   → Backend läuft möglicherweise bereits")
else:
    print(f"   ✅ Port {backend_port} ist verfügbar")

frontend_port = 3000
if is_port_in_use(frontend_port):
    print(f"   ⚠️  Port {frontend_port} ist bereits belegt")
    print(f"   → Frontend läuft möglicherweise bereits")
else:
    print(f"   ✅ Port {frontend_port} ist verfügbar")

print()
print("=" * 60)
print("Test abgeschlossen!")
print("=" * 60)
print()
print("Nächste Schritte:")
print("1. Stellen Sie sicher, dass MongoDB läuft")
print("2. Konfigurieren Sie .env mit Ihren API-Keys")
print("3. Starten Sie Backend: uvicorn server:app --reload")
print("4. Starten Sie Frontend: yarn start")
print()
