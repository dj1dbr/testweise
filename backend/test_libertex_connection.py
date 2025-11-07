"""
Test connection to Libertex account
"""
import asyncio
import aiohttp
import os
from dotenv import load_dotenv
import ssl
import json

load_dotenv()

TOKEN = os.environ.get('METAAPI_TOKEN')
LIBERTEX_ACCOUNT_ID = os.environ.get('METAAPI_ACCOUNT_ID')

async def test_connection():
    """Test connection to Libertex account"""
    print("="*60)
    print("Testing Libertex Account Connection")
    print("="*60)
    print(f"Account ID: {LIBERTEX_ACCOUNT_ID}")
    print(f"Region: london")
    print()
    
    base_url = "https://mt-client-api-v1.london.agiliumtrade.ai"
    url = f"{base_url}/users/current/accounts/{LIBERTEX_ACCOUNT_ID}/account-information"
    
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
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ CONNECTION SUCCESSFUL!")
                    print()
                    print(f"Balance: {data.get('balance')} {data.get('currency')}")
                    print(f"Equity: {data.get('equity')} {data.get('currency')}")
                    print(f"Margin: {data.get('margin')} {data.get('currency')}")
                    print(f"Free Margin: {data.get('freeMargin')} {data.get('currency')}")
                    print(f"Leverage: 1:{data.get('leverage')}")
                    print(f"Broker: {data.get('broker')}")
                    print(f"Server: {data.get('server')}")
                    print(f"Name: {data.get('name')}")
                    print(f"Login: {data.get('login')}")
                    print()
                    print("="*60)
                    print("✅ Account is ready to use!")
                    print("="*60)
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ Error {response.status}: {error_text}")
                    return False
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_connection())
