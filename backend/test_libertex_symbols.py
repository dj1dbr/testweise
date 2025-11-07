"""
Fetch available symbols from Libertex account
"""
import asyncio
import aiohttp
import os
from dotenv import load_dotenv
import ssl

load_dotenv()

TOKEN = os.environ.get('METAAPI_TOKEN')
LIBERTEX_ACCOUNT_ID = os.environ.get('METAAPI_ACCOUNT_ID')

async def fetch_symbols():
    """Fetch all available symbols"""
    print("="*60)
    print("Libertex Account - Available Symbols")
    print("="*60)
    print(f"Account ID: {LIBERTEX_ACCOUNT_ID}")
    print()
    
    base_url = "https://mt-client-api-v1.london.agiliumtrade.ai"
    url = f"{base_url}/users/current/accounts/{LIBERTEX_ACCOUNT_ID}/symbols"
    
    headers = {
        "auth-token": TOKEN,
        "Content-Type": "application/json"
    }
    
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    symbols = await response.json()
                    
                    # Filter commodity symbols
                    commodity_keywords = ['GOLD', 'XAU', 'SILVER', 'XAG', 'PLAT', 'PALL', 'PA', 'PL',
                                        'OIL', 'BRENT', 'WTI', 'CL', 'USOIL', 'UKOIL', 'GAS', 'NGAS',
                                        'WHEAT', 'CORN', 'SOYBEAN', 'COFFEE', 'SUGAR', 'COTTON', 'COCOA']
                    
                    commodity_symbols = []
                    for symbol in symbols:
                        symbol_name = symbol.upper()
                        if any(keyword in symbol_name for keyword in commodity_keywords):
                            commodity_symbols.append(symbol)
                    
                    print(f"✅ Total Symbols: {len(symbols)}")
                    print(f"✅ Commodity Symbols: {len(commodity_symbols)}")
                    print()
                    print("Commodity Symbols:")
                    print("-" * 60)
                    
                    # Group by category
                    metals = [s for s in commodity_symbols if any(k in s.upper() for k in ['GOLD', 'XAU', 'SILVER', 'XAG', 'PLAT', 'PALL', 'PA', 'PL'])]
                    energy = [s for s in commodity_symbols if any(k in s.upper() for k in ['OIL', 'BRENT', 'WTI', 'CL', 'USOIL', 'UKOIL', 'GAS', 'NGAS'])]
                    agro = [s for s in commodity_symbols if any(k in s.upper() for k in ['WHEAT', 'CORN', 'SOYBEAN', 'COFFEE', 'SUGAR', 'COTTON', 'COCOA'])]
                    
                    if metals:
                        print("\n🥇 METALS:")
                        for s in sorted(metals):
                            print(f"   {s}")
                    
                    if energy:
                        print("\n⚡ ENERGY:")
                        for s in sorted(energy):
                            print(f"   {s}")
                    
                    if agro:
                        print("\n🌾 AGRICULTURAL:")
                        for s in sorted(agro):
                            print(f"   {s}")
                    
                    print("\n" + "="*60)
                    print("✅ Symbols loaded successfully!")
                    print("="*60)
                    return commodity_symbols
                else:
                    error_text = await response.text()
                    print(f"❌ Error {response.status}: {error_text}")
                    return []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

if __name__ == "__main__":
    asyncio.run(fetch_symbols())
