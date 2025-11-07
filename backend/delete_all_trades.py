"""
Lösche ALLE Trades und setze Stats zurück
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

async def delete_all():
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    print("="*80)
    print("ALLE TRADES LÖSCHEN")
    print("="*80)
    
    # Zähle Trades
    count = await db.trades.count_documents({})
    print(f"\n{count} Trades gefunden")
    
    # Lösche alle
    result = await db.trades.delete_many({})
    print(f"✅ {result.deleted_count} Trades gelöscht!")
    
    # Stats zurücksetzen
    stats_result = await db.stats.update_one(
        {},
        {"$set": {
            "total_trades": 0,
            "open_positions": 0,
            "closed_positions": 0,
            "total_profit_loss": 0.0
        }},
        upsert=True
    )
    print(f"✅ Stats zurückgesetzt!")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(delete_all())
