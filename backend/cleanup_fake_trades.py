"""
Script zum Löschen aller Fake-Trades (nur Metall-Trades behalten)
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

# Erlaubte Commodities (nur Metalle)
ALLOWED_COMMODITIES = ['GOLD', 'SILVER', 'PLATINUM', 'PALLADIUM']

async def cleanup_trades():
    """Lösche alle Trades außer Metall-Trades"""
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    print("="*80)
    print("DATENBANK-BEREINIGUNG: Fake-Trades löschen")
    print("="*80)
    
    # Zeige alle Trades
    all_trades = await db.trades.find().to_list(1000)
    print(f"\nGefunden: {len(all_trades)} Trades insgesamt")
    
    # Zähle Trades nach Commodity
    commodity_counts = {}
    for trade in all_trades:
        commodity = trade.get('commodity', 'UNKNOWN')
        commodity_counts[commodity] = commodity_counts.get(commodity, 0) + 1
    
    print("\nTrades nach Commodity:")
    for commodity, count in sorted(commodity_counts.items()):
        status = "✅ BEHALTEN" if commodity in ALLOWED_COMMODITIES else "❌ LÖSCHEN"
        print(f"  {commodity}: {count} Trades - {status}")
    
    # Lösche alle nicht-Metall-Trades
    delete_query = {"commodity": {"$nin": ALLOWED_COMMODITIES}}
    result = await db.trades.delete_many(delete_query)
    
    print(f"\n{'='*80}")
    print(f"✅ {result.deleted_count} Fake-Trades gelöscht!")
    print(f"{'='*80}")
    
    # Zeige verbleibende Trades
    remaining_trades = await db.trades.find().to_list(1000)
    print(f"\nVerbleibende Trades: {len(remaining_trades)}")
    
    for trade in remaining_trades:
        print(f"  - {trade['commodity']}: {trade['type']} @ {trade.get('entry_price', 'N/A')} (Status: {trade['status']})")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(cleanup_trades())
