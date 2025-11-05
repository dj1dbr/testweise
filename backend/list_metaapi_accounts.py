"""
List all MetaAPI accounts accessible with the provided token
"""
import asyncio
import aiohttp
import os
from dotenv import load_dotenv
import ssl
import json

load_dotenv()

TOKEN = os.environ.get('METAAPI_TOKEN')

# Provisioning API endpoint
PROVISIONING_URL = "https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai/users/current/accounts"

async def list_accounts():
    """List all accounts accessible with the token"""
    print("="*60)
    print("MetaAPI Account Lister")
    print("="*60)
    print(f"Token: {TOKEN[:50]}...\n")
    
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
            async with session.get(PROVISIONING_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    accounts = await response.json()
                    
                    if not accounts:
                        print("❌ No accounts found!")
                        print("\nYou need to add a MetaTrader account to MetaAPI:")
                        print("1. Go to https://app.metaapi.cloud")
                        print("2. Click 'Add Account'")
                        print("3. Enter your MT5 broker credentials")
                        print("4. Deploy the account")
                        return
                    
                    print(f"✅ Found {len(accounts)} account(s):\n")
                    
                    for i, account in enumerate(accounts, 1):
                        print(f"Account #{i}")
                        print(f"  Account ID (UUID): {account.get('_id')}")
                        print(f"  Name: {account.get('name', 'N/A')}")
                        print(f"  Login: {account.get('login', 'N/A')}")
                        print(f"  Server: {account.get('server', 'N/A')}")
                        print(f"  Platform: {account.get('platform', 'N/A')}")
                        print(f"  Broker: {account.get('brokerName', 'N/A')}")
                        print(f"  Region: {account.get('region', 'N/A')}")
                        print(f"  State: {account.get('state', 'N/A')}")
                        print(f"  Connection Status: {account.get('connectionStatus', 'N/A')}")
                        print()
                    
                    print("="*60)
                    print("INSTRUCTIONS")
                    print("="*60)
                    print("\n1. Copy the 'Account ID (UUID)' from above")
                    print("2. Update your /app/backend/.env file:")
                    print(f"   METAAPI_ACCOUNT_ID=<paste_the_UUID_here>")
                    print("\n3. Check the 'Region' field and update metaapi_connector.py:")
                    
                    if accounts:
                        region = accounts[0].get('region', 'new-york')
                        if region == 'new-york':
                            url = "https://mt-client-api-v1.new-york.agiliumtrade.ai"
                        elif region == 'london':
                            url = "https://mt-client-api-v1.london.agiliumtrade.ai"
                        elif region == 'singapore':
                            url = "https://mt-client-api-v1.singapore.agiliumtrade.ai"
                        else:
                            url = f"https://mt-client-api-v1.{region}.agiliumtrade.ai"
                        
                        print(f'   self.base_url = "{url}"')
                    
                else:
                    error_text = await response.text()
                    print(f"❌ Error {response.status}: {error_text}")
                    
                    if response.status == 401:
                        print("\nYour token is invalid or expired!")
                        print("Get a new token from: https://app.metaapi.cloud/api-access")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nPlease check:")
        print("1. Your internet connection")
        print("2. Your MetaAPI token is correct")
        print("3. https://app.metaapi.cloud is accessible")

if __name__ == "__main__":
    asyncio.run(list_accounts())
