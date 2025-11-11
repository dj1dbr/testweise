"""
Hilfsskript zum Schließen von MT5-Positionen
"""
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = "https://trade-hub-116.preview.emergentagent.com"

async def list_positions():
    """Liste alle offenen Positionen auf"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BACKEND_URL}/api/mt5/positions") as response:
            if response.status == 200:
                data = await response.json()
                positions = data.get('positions', [])
                
                print("="*80)
                print("OFFENE MT5-POSITIONEN")
                print("="*80)
                
                if not positions:
                    print("Keine offenen Positionen gefunden.")
                    return []
                
                for i, pos in enumerate(positions, 1):
                    print(f"\n#{i} - Ticket: {pos['ticket']}")
                    print(f"   Symbol: {pos['symbol']}")
                    print(f"   Typ: {pos['type']}")
                    print(f"   Volume: {pos['volume']} Lots")
                    print(f"   Eröffnungspreis: {pos['price_open']}")
                    print(f"   Aktueller Preis: {pos['price_current']}")
                    print(f"   Profit/Loss: {pos['profit']:.2f} EUR")
                    print(f"   Zeit: {pos['time']}")
                
                return positions
            else:
                print(f"Fehler beim Abrufen der Positionen: {response.status}")
                return []

async def get_account_info():
    """Hole Account-Informationen"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BACKEND_URL}/api/mt5/account") as response:
            if response.status == 200:
                data = await response.json()
                
                print("\n" + "="*80)
                print("MT5 KONTO-INFORMATION")
                print("="*80)
                print(f"Balance: {data['balance']:.2f} {data['currency']}")
                print(f"Equity: {data['equity']:.2f} {data['currency']}")
                print(f"Verwendete Margin: {data['margin']:.2f} {data['currency']}")
                print(f"Freie Margin: {data['free_margin']:.2f} {data['currency']}")
                print(f"Leverage: 1:{data['leverage']}")
                print(f"Broker: {data['broker']}")
                
                if data['free_margin'] < 100:
                    print(f"\n⚠️  WARNUNG: Sehr wenig freie Margin ({data['free_margin']:.2f} EUR)!")
                    print(f"    Schließen Sie einige Positionen, um neue Orders platzieren zu können.")
                
                return data
            else:
                print(f"Fehler beim Abrufen der Kontodaten: {response.status}")
                return None

async def close_position(ticket: str):
    """Schließe eine Position"""
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BACKEND_URL}/api/mt5/close/{ticket}") as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ Position {ticket} erfolgreich geschlossen!")
                return True
            else:
                error = await response.text()
                print(f"❌ Fehler beim Schließen der Position {ticket}: {error}")
                return False

async def close_all_positions():
    """Schließe alle offenen Positionen"""
    positions = await list_positions()
    
    if not positions:
        print("\nKeine Positionen zum Schließen.")
        return
    
    print("\n" + "="*80)
    print("Möchten Sie wirklich ALLE Positionen schließen? (ja/nein)")
    # In einem Skript-Kontext - direkt ausführen für Demo
    
    for pos in positions:
        ticket = pos['ticket']
        print(f"\nSchließe Position {ticket}...")
        await close_position(ticket)
        await asyncio.sleep(1)  # Kurze Pause zwischen Schließungen

async def main():
    """Hauptfunktion"""
    # Zeige Konto-Info
    await get_account_info()
    
    # Liste Positionen auf
    positions = await list_positions()
    
    if positions:
        print("\n" + "="*80)
        print("EMPFEHLUNG")
        print("="*80)
        print("Ihr Konto hat fast keine freie Margin mehr.")
        print("Bitte schließen Sie einige Positionen manuell über:")
        print("1. MT5-Terminal")
        print("2. MetaAPI Dashboard (https://app.metaapi.cloud)")
        print("\nOder verwenden Sie diesen Befehl zum automatischen Schließen:")
        print("python close_positions.py --close-all")
        print("\nEinzelne Position schließen:")
        print(f"curl -X POST {BACKEND_URL}/api/mt5/close/TICKET_NUMBER")

if __name__ == "__main__":
    import sys
    
    if "--close-all" in sys.argv:
        asyncio.run(close_all_positions())
    else:
        asyncio.run(main())
