"""
Script zum Aktualisieren der Settings auf nur Metalle
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

async def update_settings():
    """Update settings to only metals"""
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    print("="*80)
    print("SETTINGS UPDATE: Nur Edelmetalle aktivieren")
    print("="*80)
    
    # Update settings
    result = await db.trading_settings.update_one(
        {"id": "trading_settings"},
        {"$set": {
            "enabled_commodities": ["GOLD", "SILVER", "PLATINUM", "PALLADIUM", "WTI_CRUDE", "BRENT_CRUDE", "NATURAL_GAS", "WHEAT", "CORN", "SOYBEANS", "COFFEE", "SUGAR", "COTTON", "COCOA"],
            "mode": "MT5"
        }}
    )
    
    print(f"\n✅ Settings aktualisiert!")
    print(f"   Matched: {result.matched_count}")
    print(f"   Modified: {result.modified_count}")
    
    # Zeige aktuelle Settings
    settings = await db.trading_settings.find_one({"id": "trading_settings"})
    if settings:
        print(f"\nAktivierte Commodities:")
        for commodity in settings.get('enabled_commodities', []):
            print(f"  ✓ {commodity}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(update_settings())
