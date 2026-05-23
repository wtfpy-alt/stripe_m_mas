#!/usr/bin/env python3
"""
Quick API Test Script
"""
import asyncio
import aiohttp

API_URL = "http://localhost:8000"
AUTH_TOKEN = "technopile"


async def test_single():
    """Test single card"""
    payload = {
        "cc": "4111111111111111",
        "mm": "12",
        "yy": "25",
        "cvv": "123",
        "auth": AUTH_TOKEN,
        "amount": 1
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_URL}/check", json=payload) as resp:
            result = await resp.json()
            print(f"Status: {result.get('status')}")
            print(f"Message: {result.get('message')}")
            print(f"Time: {result.get('time_taken')}s")


async def test_bulk():
    """Test bulk cards"""
    payload = {
        "cards": [
            "4111111111111111|12|25|123",
            "5555555555554444|01|26|456",
        ],
        "auth": AUTH_TOKEN,
        "amount": 1
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_URL}/check-bulk", json=payload) as resp:
            result = await resp.json()
            print(f"Total: {result.get('total')}")
            print(f"Stats: {result.get('stats')}")


if __name__ == "__main__":
    print("Testing Single Card...")
    asyncio.run(test_single())
    print("\nTesting Bulk Cards...")
    asyncio.run(test_bulk())
