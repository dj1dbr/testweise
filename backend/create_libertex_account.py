"""
Erstelle neuen Libertex MT5-Account bei MetaAPI
"""
import asyncio
import aiohttp
import os
from dotenv import load_dotenv
import json

load_dotenv()

TOKEN = os.environ.get('METAAPI_TOKEN')

# Libertex Zugangsdaten
LIBERTEX_LOGIN = "510038470"
LIBERTEX_PASSWORD = "AZLEaU0/"
LIBERTEX_SERVER = "LibertexCom-MT5 Demo Server"

async def create_account():
    """Erstelle neuen MT5-Account bei MetaAPI"""
    print("="*80)
    print("LIBERTEX MT5-ACCOUNT ERSTELLEN")
    print("="*80)
    print(f"Login: {LIBERTEX_LOGIN}")
    print(f"Server: {LIBERTEX_SERVER}")
    print()
    
    url = "https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai/users/current/accounts"
    
    headers = {
        "auth-token": TOKEN,
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": "Libertex Demo",
        "type": "cloud",
        "login": LIBERTEX_LOGIN,
        "password": LIBERTEX_PASSWORD,
        "server": LIBERTEX_SERVER,
        "platform": "mt5",
        "magic": 123456,
        "application": "MetaApi",
        "region": "new-york"  # Wird automatisch erkannt
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            print("📡 Sende Anfrage an MetaAPI...")
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response_text = await response.text()
                
                if response.status in [200, 201]:
                    account = json.loads(response_text)
                    account_id = account.get('_id') or account.get('id')
                    
                    print("\n✅ ACCOUNT ERFOLGREICH ERSTELLT!")
                    print("="*80)
                    print(f"Account ID: {account_id}")
                    print(f"State: {account.get('state', 'N/A')}")
                    print("="*80)
                    
                    print("\n📋 NÄCHSTE SCHRITTE:")
                    print(f"1. Warten Sie, bis Account deployed ist (Status: DEPLOYED)")
                    print(f"2. Kopieren Sie diese Account ID:")
                    print(f"   {account['_id']}")
                    print(f"3. Account wird automatisch in .env gespeichert...")
                    
                    # Speichere Account ID in .env
                    with open('/app/backend/.env', 'r') as f:
                        env_content = f.read()
                    
                    lines = env_content.split('\n')
                    new_lines = []
                    for line in lines:
                        if line.startswith('METAAPI_ACCOUNT_ID='):
                            new_lines.append(f"METAAPI_ACCOUNT_ID={account_id}")
                        else:
                            new_lines.append(line)
                    
                    with open('/app/backend/.env', 'w') as f:
                        f.write('\n'.join(new_lines))
                    
                    print("\n✅ .env Datei aktualisiert mit Account ID: " + account_id)
                    
                    return account
                    
                else:
                    print(f"\n❌ Fehler {response.status}")
                    print(f"Response: {response_text}")
                    
                    # Prüfe ob Account bereits existiert
                    if response.status == 400 and 'already exists' in response_text.lower():
                        print("\n⚠️  Account existiert bereits!")
                        print("Möchten Sie stattdessen die bestehenden Accounts auflisten?")
                        print("Führen Sie aus: python list_metaapi_accounts.py")
                    
                    return None
                    
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        return None

if __name__ == "__main__":
    account = asyncio.run(create_account())
    
    if account:
        print("\n" + "="*80)
        print("✅ FERTIG! Account wurde erstellt.")
        print("="*80)
        print("\nJetzt können Sie:")
        print("1. Symbol-Mapping ausführen: python auto_map_broker_symbols.py")
        print("2. Backend neu starten: sudo supervisorctl restart backend")
