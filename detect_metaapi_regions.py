#!/usr/bin/env python3
"""
MetaAPI Region Auto-Detection Script
Findet automatisch die richtige Region für alle MT5 Accounts
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
ROOT_DIR = Path(__file__).parent / "backend"
load_dotenv(ROOT_DIR / '.env')

# MetaAPI Regionen
REGIONS = [
    'london',
    'new-york', 
    'singapore',
    'mumbai',
    'toronto'
]

async def test_account_in_region(session, account_id, token, region):
    """Test if account exists in specific region"""
    url = f"https://mt-client-api-v1.{region}.agiliumtrade.ai/users/current/accounts/{account_id}"
    headers = {"auth-token": token}
    
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
            if response.status == 200:
                data = await response.json()
                return True, data
            elif response.status == 404:
                return False, "Account not found in this region"
            elif response.status == 401:
                return False, "Invalid token"
            else:
                text = await response.text()
                return False, f"Error {response.status}: {text[:100]}"
    except asyncio.TimeoutError:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)

async def find_account_region(account_id, account_name, token):
    """Find the correct region for an account"""
    print(f"\n{'='*60}")
    print(f"Testing {account_name}")
    print(f"Account ID: {account_id}")
    print(f"{'='*60}")
    
    async with aiohttp.ClientSession() as session:
        for region in REGIONS:
            print(f"\nTesting region: {region}...", end=" ")
            
            success, result = await test_account_in_region(session, account_id, token, region)
            
            if success:
                print(f"✅ FOUND!")
                print(f"\n📍 Account Details:")
                print(f"   Region: {region}")
                print(f"   Name: {result.get('name', 'N/A')}")
                print(f"   Login: {result.get('login', 'N/A')}")
                print(f"   Server: {result.get('server', 'N/A')}")
                print(f"   Type: {result.get('type', 'N/A')}")
                print(f"   State: {result.get('state', 'N/A')}")
                return region, result
            else:
                print(f"❌ {result}")
    
    print(f"\n⚠️  Account not found in any region!")
    return None, None

async def main():
    print("=" * 60)
    print("MetaAPI Region Auto-Detection")
    print("=" * 60)
    
    # Get credentials
    libertex_id = os.environ.get('METAAPI_ACCOUNT_ID')
    icmarkets_id = os.environ.get('METAAPI_ICMARKETS_ACCOUNT_ID')
    token = os.environ.get('METAAPI_TOKEN')
    
    if not token:
        print("❌ METAAPI_TOKEN not found in .env!")
        return
    
    print(f"\nToken length: {len(token)} chars")
    
    results = {}
    
    # Test Libertex Account
    if libertex_id:
        region, data = await find_account_region(libertex_id, "MT5 Libertex", token)
        results['libertex'] = {'region': region, 'data': data}
    else:
        print("\n⚠️  METAAPI_ACCOUNT_ID (Libertex) not set")
    
    # Test ICMarkets Account
    if icmarkets_id:
        region, data = await find_account_region(icmarkets_id, "MT5 ICMarkets", token)
        results['icmarkets'] = {'region': region, 'data': data}
    else:
        print("\n⚠️  METAAPI_ICMARKETS_ACCOUNT_ID not set")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for account_name, result in results.items():
        region = result.get('region')
        if region:
            print(f"\n✅ {account_name.upper()}: Found in region '{region}'")
        else:
            print(f"\n❌ {account_name.upper()}: Not found in any region")
    
    # Generate code suggestions
    if any(r.get('region') for r in results.values()):
        print("\n" + "=" * 60)
        print("SUGGESTED .env CONFIGURATION")
        print("=" * 60)
        
        libertex_region = results.get('libertex', {}).get('region')
        icmarkets_region = results.get('icmarkets', {}).get('region')
        
        if libertex_region:
            print(f"\nMETAAPI_REGION_LIBERTEX={libertex_region}")
        if icmarkets_region:
            print(f"METAAPI_REGION_ICMARKETS={icmarkets_region}")
        
        print("\nAdd these to your backend/.env file!")

if __name__ == "__main__":
    asyncio.run(main())
