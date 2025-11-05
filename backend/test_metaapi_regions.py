"""
Test MetaAPI account connection across different regions
"""
import asyncio
import aiohttp
import os
from dotenv import load_dotenv
import ssl

load_dotenv()

ACCOUNT_ID = os.environ.get('METAAPI_ACCOUNT_ID')
TOKEN = os.environ.get('METAAPI_TOKEN')

# Different regional endpoints
REGIONS = {
    "new-york": "https://mt-client-api-v1.new-york.agiliumtrade.ai",
    "london": "https://mt-client-api-v1.london.agiliumtrade.ai",
    "singapore": "https://mt-client-api-v1.singapore.agiliumtrade.ai"
}

async def test_region(region_name, base_url):
    """Test account connection in a specific region"""
    print(f"\n🔍 Testing {region_name.upper()} region...")
    print(f"   URL: {base_url}")
    
    url = f"{base_url}/users/current/accounts/{ACCOUNT_ID}/account-information"
    headers = {
        "auth-token": TOKEN,
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
                    print(f"   ✅ SUCCESS! Account found in {region_name.upper()}")
                    print(f"   Balance: {data.get('balance')} {data.get('currency')}")
                    print(f"   Broker: {data.get('broker')}")
                    print(f"   Server: {data.get('server')}")
                    return region_name, base_url, data
                else:
                    error_text = await response.text()
                    print(f"   ❌ Failed: {response.status}")
                    if response.status == 404:
                        print(f"   Account not found in this region")
                    else:
                        print(f"   Error: {error_text[:200]}")
                    return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

async def main():
    print("="*60)
    print("MetaAPI Regional Account Test")
    print("="*60)
    print(f"Account ID: {ACCOUNT_ID}")
    print(f"Token: {TOKEN[:50]}...")
    
    # Test all regions
    tasks = [test_region(name, url) for name, url in REGIONS.items()]
    results = await asyncio.gather(*tasks)
    
    # Find successful region
    successful = [r for r in results if r is not None]
    
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    
    if successful:
        region_name, base_url, data = successful[0]
        print(f"✅ Account found in: {region_name.upper()}")
        print(f"✅ Correct base URL: {base_url}")
        print(f"\nUpdate your metaapi_connector.py:")
        print(f'   self.base_url = "{base_url}"')
    else:
        print("❌ Account not found in any region!")
        print("\nPossible reasons:")
        print("1. Account ID is incorrect")
        print("2. Account is not deployed")
        print("3. Token is invalid or expired")
        print("\nPlease check your MetaAPI dashboard at:")
        print("https://app.metaapi.cloud/api-access/api-urls")

if __name__ == "__main__":
    asyncio.run(main())
