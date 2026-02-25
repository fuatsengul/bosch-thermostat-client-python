#!/usr/bin/env python3
"""Test token refresh without Home Assistant."""
import asyncio
import json
import logging
import aiohttp
from bosch_thermostat_client.connectors.oauth2 import Oauth2Connector

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_refresh():
    """Test token refresh."""
    # Load tokens
    with open('tokens.json', 'r') as f:
        tokens = json.load(f)
    
    print(f"📝 Loaded tokens:")
    print(f"  Device ID: {tokens['device_id']}")
    print(f"  Access Token: {tokens['access_token'][:50]}...")
    print(f"  Refresh Token: {tokens['refresh_token']}")
    print(f"  Expires At: {tokens['expires_at']}")
    print()
    
    # Create aiohttp session
    async with aiohttp.ClientSession() as session:
        # Create connector
        connector = Oauth2Connector(
            host=tokens['device_id'],
            access_token=tokens['access_token'],
            refresh_token=tokens['refresh_token'],
            device_type='IVT'
        )
        
        # Manually set the websession (needed for testing)
        connector._websession = session
        
        print("🔄 Testing token refresh...")
        try:
            result = await connector._refresh_access_token()
            print("✅ Token refresh successful!")
            print(f"  New Access Token: {connector._access_token[:50]}...")
            print(f"  Expires At: {connector._token_expires_at}")
            
            # Save new tokens
            tokens['access_token'] = connector._access_token
            tokens['refresh_token'] = connector._refresh_token
            tokens['expires_at'] = connector._token_expires_at.isoformat()
            
            with open('tokens.json', 'w') as f:
                json.dump(tokens, f, indent=2)
            print("💾 Saved new tokens to tokens.json")
            
        except Exception as e:
            print(f"❌ Token refresh failed: {e}")
            print(f"   Error type: {type(e).__name__}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test_refresh())

