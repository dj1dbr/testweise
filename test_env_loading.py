#!/usr/bin/env python3
"""
Test .env loading und MetaAPI Account IDs
"""

import os
from pathlib import Path
from dotenv import load_dotenv

print("=" * 60)
print("ENV LOADING TEST")
print("=" * 60)

ROOT_DIR = Path(__file__).parent / "backend"
env_file = ROOT_DIR / '.env'

print(f"\n1. .env file path: {env_file}")
print(f"   Exists: {env_file.exists()}")

if env_file.exists():
    print(f"   File size: {env_file.stat().st_size} bytes")

print("\n2. Loading .env...")
load_dotenv(env_file)
print("   ✅ Loaded")

print("\n3. Environment variables:")
print(f"   MONGO_URL: {os.environ.get('MONGO_URL', 'NOT SET')}")
print(f"   DB_NAME: {os.environ.get('DB_NAME', 'NOT SET')}")
print(f"   METAAPI_ACCOUNT_ID: {os.environ.get('METAAPI_ACCOUNT_ID', 'NOT SET')}")
print(f"   METAAPI_ICMARKETS_ACCOUNT_ID: {os.environ.get('METAAPI_ICMARKETS_ACCOUNT_ID', 'NOT SET')}")

# Check if MetaAPI Token is set (nur ersten 20 Zeichen)
token = os.environ.get('METAAPI_TOKEN', '')
if token:
    print(f"   METAAPI_TOKEN: {token[:20]}... (length: {len(token)})")
else:
    print(f"   METAAPI_TOKEN: NOT SET")

bitpanda_key = os.environ.get('BITPANDA_API_KEY', '')
if bitpanda_key:
    print(f"   BITPANDA_API_KEY: {bitpanda_key[:20]}... (length: {len(bitpanda_key)})")
else:
    print(f"   BITPANDA_API_KEY: NOT SET")

print(f"   BITPANDA_EMAIL: {os.environ.get('BITPANDA_EMAIL', 'NOT SET')}")

print("\n4. Testing MultiPlatformConnector initialization...")
try:
    import sys
    sys.path.insert(0, str(ROOT_DIR))
    
    from multi_platform_connector import MultiPlatformConnector
    
    connector = MultiPlatformConnector()
    
    print(f"   ✅ MultiPlatformConnector created")
    print(f"\n   Platform configurations:")
    for platform_name, platform_info in connector.platforms.items():
        print(f"   - {platform_name}:")
        if 'account_id' in platform_info:
            print(f"     Account ID: {platform_info['account_id']}")
        if 'api_key' in platform_info:
            key = platform_info['api_key']
            print(f"     API Key: {key[:20] if key else 'NOT SET'}...")
        print(f"     Active: {platform_info.get('active', False)}")
        
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
