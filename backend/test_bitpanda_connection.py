"""
Test Bitpanda API Verbindung
Prüft ob Bitpanda API erreichbar ist und API-Key funktioniert
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def test_bitpanda():
    print("="*80)
    print("BITPANDA API VERBINDUNGSTEST")
    print("="*80)
    
    api_key = os.environ.get('BITPANDA_API_KEY')
    
    if not api_key:
        print("❌ Kein BITPANDA_API_KEY in .env gefunden!")
        print("\nBitte fügen Sie hinzu:")
        print("BITPANDA_API_KEY=ihr-api-key-hier")
        return
    
    print(f"\n✅ API-Key gefunden: {api_key[:20]}...")
    
    # Test 1: Public API (ohne Auth)
    print("\n" + "-"*80)
    print("TEST 1: Bitpanda Public API (Erreichbarkeit)")
    print("-"*80)
    
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.exchange.bitpanda.com/public/v1/time",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Bitpanda API ist erreichbar!")
                    print(f"   Server Zeit: {data}")
                else:
                    print(f"⚠️  Status {response.status}")
                    text = await response.text()
                    print(f"   Response: {text[:200]}")
    except Exception as e:
        print(f"❌ Bitpanda API nicht erreichbar!")
        print(f"   Fehler: {e}")
        print("\n💡 Wenn Sie in der Cloud sind:")
        print("   -> Bitpanda ist von Cloud-Netzwerken oft blockiert")
        print("   -> Funktioniert aber lokal auf Ihrem Mac!")
        return
    
    # Test 2: Account API (mit Auth)
    print("\n" + "-"*80)
    print("TEST 2: Bitpanda Account API (Authentifizierung)")
    print("-"*80)
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            # Account Balances
            async with session.get(
                "https://api.exchange.bitpanda.com/public/v1/account/balances",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    balances = data.get('balances', [])
                    
                    print(f"✅ Authentifizierung erfolgreich!")
                    print(f"   Account-Balances: {len(balances)} Währungen")
                    
                    # Zeige Balances
                    if balances:
                        print("\n   💰 Ihre Guthaben:")
                        for balance in balances[:5]:  # Zeige ersten 5
                            currency = balance.get('currency_code', 'N/A')
                            available = float(balance.get('available', 0))
                            locked = float(balance.get('locked', 0))
                            
                            if available > 0 or locked > 0:
                                print(f"      {currency}: {available:.4f} (verfügbar) + {locked:.4f} (gesperrt)")
                    else:
                        print("   ℹ️  Noch kein Guthaben vorhanden")
                
                elif response.status == 401:
                    print(f"❌ Authentifizierung fehlgeschlagen!")
                    print(f"   API-Key ist ungültig oder abgelaufen")
                    print(f"\n💡 Erstellen Sie einen neuen API-Key:")
                    print(f"   1. Gehen Sie zu https://www.bitpanda.com/pro/api")
                    print(f"   2. Erstellen Sie einen neuen API-Key mit Trading-Rechten")
                    print(f"   3. Kopieren Sie den Key in die .env Datei")
                else:
                    print(f"⚠️  Status {response.status}")
                    text = await response.text()
                    print(f"   Response: {text[:300]}")
                    
    except Exception as e:
        print(f"❌ Fehler bei Account API!")
        print(f"   Fehler: {e}")
    
    # Test 3: Trading Pairs
    print("\n" + "-"*80)
    print("TEST 3: Verfügbare Trading-Paare")
    print("-"*80)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.exchange.bitpanda.com/public/v1/instruments",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    instruments = data
                    
                    # Filter für relevante Pairs
                    btc_pairs = [i for i in instruments if 'BTC' in i.get('base', {}).get('code', '')]
                    eth_pairs = [i for i in instruments if 'ETH' in i.get('base', {}).get('code', '')]
                    
                    print(f"✅ {len(instruments)} Trading-Paare verfügbar")
                    print(f"   BTC-Paare: {len(btc_pairs)}")
                    print(f"   ETH-Paare: {len(eth_pairs)}")
                    
                    print("\n   📊 Beispiel BTC-Paare:")
                    for pair in btc_pairs[:3]:
                        code = pair.get('code', 'N/A')
                        state = pair.get('state', 'N/A')
                        print(f"      {code} - {state}")
                else:
                    print(f"⚠️  Status {response.status}")
    except Exception as e:
        print(f"❌ Fehler bei Trading-Pairs!")
        print(f"   Fehler: {e}")
    
    print("\n" + "="*80)
    print("TEST ABGESCHLOSSEN")
    print("="*80)
    print("\n💡 Zusammenfassung:")
    print("   ✅ API erreichbar -> Bitpanda-Integration funktioniert")
    print("   ✅ Auth erfolgreich -> API-Key ist gültig")
    print("   ❌ API nicht erreichbar -> Läuft in Cloud (lokal auf Mac funktioniert es)")
    print("   ❌ Auth fehlgeschlagen -> API-Key prüfen/erneuern")

if __name__ == "__main__":
    asyncio.run(test_bitpanda())
