"""
Test script to find the correct MetaAPI region for Libertex account
"""
import asyncio
import aiohttp
import os
import ssl
from dotenv import load_dotenv

load_dotenv()

METAAPI_TOKEN = os.environ.get('METAAPI_TOKEN')
LIBERTEX_ACCOUNT_ID = os.environ.get('METAAPI_ACCOUNT_ID', 'rohstoff-trader')

# MetaAPI regions
REGIONS = {
    'new-york': 'https://mt-client-api-v1.new-york.agiliumtrade.ai',
    'london': 'https://mt-client-api-v1.london.agiliumtrade.ai',
    'singapore': 'https://mt-client-api-v1.singapore.agiliumtrade.ai'
}

async def test_region(region_name: str, base_url: str):
    """Test if account exists in this region"""
    url = f"{base_url}/users/current/accounts/{LIBERTEX_ACCOUNT_ID}/account-information"
    headers = {
        "auth-token": METAAPI_TOKEN,
        "Content-Type": "application/json"
    }
    
    # Create SSL context that doesn't verify certificates
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    
    try:
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"\n✅ SUCCESS in {region_name.upper()} region!")
                    print(f"   Account: {LIBERTEX_ACCOUNT_ID}")
                    print(f"   Balance: {data.get('balance')} {data.get('currency')}")
                    print(f"   Broker: {data.get('broker')}")
                    print(f"   Server: {data.get('server')}")
                    print(f"   Base URL: {base_url}")
                    return region_name, base_url
                else:
                    error = await response.text()
                    print(f"❌ {region_name}: {response.status} - Account not found")
                    return None
    except Exception as e:
        print(f"❌ {region_name}: Error - {e}")
        return None

async def find_libertex_region():
    """Test all regions to find where Libertex account is deployed"""
    print(f"🔍 Searching for Libertex account: {LIBERTEX_ACCOUNT_ID}")
    print(f"   Testing {len(REGIONS)} regions...\n")
    
    tasks = [test_region(name, url) for name, url in REGIONS.items()]
    results = await asyncio.gather(*tasks)
    
    # Find successful region
    successful = [r for r in results if r is not None]
    
    if successful:
        region_name, base_url = successful[0]
        print(f"\n🎯 Found account in {region_name.upper()} region!")
        print(f"\n📝 Update your configuration:")
        print(f"   Region: {region_name}")
        print(f"   Base URL: {base_url}")
        return region_name, base_url
    else:
        print("\n❌ Account not found in any region!")
        print("   Please verify:")
        print("   1. Account ID is correct")
        print("   2. Account is deployed in MetaAPI")
        print("   3. Token has correct permissions")
        return None, None

if __name__ == "__main__":
    asyncio.run(find_libertex_region())
