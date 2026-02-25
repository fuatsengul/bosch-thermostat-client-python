#!/usr/bin/env python3
"""Test OAuth2 gateway initialization for Home Assistant."""

import asyncio
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)

async def test_oauth2_gateway():
    """Test OAuth2 gateway initialization."""
    from bosch_thermostat_client.gateway import Oauth2Gateway
    from bosch_thermostat_client.const.ivt import IVT
    
    # Load tokens
    token_file = Path("tokens.json")
    with open(token_file, "r") as f:
        tokens = json.load(f)
    
    # Create an aiohttp session  (simplified for testing)
    import aiohttp
    async with aiohttp.ClientSession() as session:
        # Initialize gateway like Home Assistant would
        gateway = Oauth2Gateway(
            session=session,
            session_type="OAUTH2",
            device_type=IVT,
            host="101650657",
            access_token=tokens['access_token'],
            refresh_token=tokens['refresh_token'],
            token_file=token_file
        )
        
        print("Gateway created")
        print(f"Initialized: {gateway.initialized}")
        
        # Check connection (what Home Assistant calls)
        try:
            uuid = await gateway.check_connection()
            print(f"Check connection succeeded, UUID: {uuid}")
            print(f"Initialized: {gateway.initialized}")
        except Exception as e:
            print(f"Check connection failed: {e}")
            return False
        
        if not uuid:
            print("ERROR: No UUID obtained from device")
            return False
        
        print("SUCCESS: Gateway initialized properly")
        return True

if __name__ == "__main__":
    result = asyncio.run(test_oauth2_gateway())
    exit(0 if result else 1)
