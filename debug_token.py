#!/usr/bin/env python3
"""Debug the refresh token format."""
import json

with open('tokens.json', 'r') as f:
    tokens = json.load(f)

refresh_token = tokens['refresh_token']
print(f"Refresh Token: {refresh_token}")
print(f"Length: {len(refresh_token)}")
print(f"Repr: {repr(refresh_token)}")
print(f"Byte representation: {refresh_token.encode('utf-8')}")

# Check if it's truly meant to have -1
if refresh_token.endswith('-1'):
    print("\n⚠️  Token ends with '-1' - this might be a parsing issue")
    print(f"Token without -1: {refresh_token[:-2]}")
    print(f"Length without -1: {len(refresh_token[:-2])}")
