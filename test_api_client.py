#!/usr/bin/env python3
"""
Example client for testing the Razorpay Card Checker API
"""

import requests
import asyncio
import aiohttp
import time
import json
from typing import List

API_BASE_URL = "http://localhost:8000"
AUTH_TOKEN = "technopile"


class CardCheckerClient:
    def __init__(self, base_url: str = API_BASE_URL, auth_token: str = AUTH_TOKEN):
        self.base_url = base_url
        self.auth_token = auth_token
        self.session = None

    async def check_card(
        self,
        cc: str,
        mm: str,
        yy: str,
        cvv: str,
        proxy: str = None,
        amount: int = 1
    ) -> dict:
        """Check a single card"""
        payload = {
            "cc": cc,
            "mm": mm,
            "yy": yy,
            "cvv": cvv,
            "auth": self.auth_token,
            "amount": amount,
        }
        if proxy:
            payload["proxy"] = proxy

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/check",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    return await resp.json()
        except Exception as e:
            return {"error": str(e), "status": "error"}

    async def check_bulk(
        self,
        cards: List[str],
        proxy: str = None,
        amount: int = 1
    ) -> dict:
        """Check multiple cards concurrently"""
        payload = {
            "cards": cards,
            "auth": self.auth_token,
            "amount": amount,
        }
        if proxy:
            payload["proxy"] = proxy

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/check-bulk",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as resp:
                    return await resp.json()
        except Exception as e:
            return {"error": str(e), "status": "error"}

    def get_stats(self) -> dict:
        """Get API statistics"""
        try:
            resp = requests.get(f"{self.base_url}/stats", timeout=5)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def health_check(self) -> dict:
        """Check API health"""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=5)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}


async def test_single_card():
    """Test single card checking"""
    print("\n" + "=" * 60)
    print("Testing Single Card Check")
    print("=" * 60)

    client = CardCheckerClient()

    # Check API health first
    print("\n🔍 Checking API health...")
    health = client.health_check()
    print(f"✅ Health: {health}")

    # Test single card
    print("\n🎯 Testing single card...")
    result = await client.check_card(
        cc="4111111111111111",
        mm="12",
        yy="25",
        cvv="123"
    )
    print(f"📊 Result: {json.dumps(result, indent=2)}")

    return result


async def test_bulk_cards():
    """Test bulk card checking"""
    print("\n" + "=" * 60)
    print("Testing Bulk Card Check")
    print("=" * 60)

    client = CardCheckerClient()

    test_cards = [
        "4111111111111111|12|25|123",
        "5555555555554444|01|26|456",
        "378282246310005|03|25|789",
        "6011111111111117|12|24|999",
    ]

    print(f"\n🎯 Checking {len(test_cards)} cards...")
    start = time.time()

    result = await client.check_bulk(cards=test_cards)

    elapsed = time.time() - start

    print(f"📊 Result Summary:")
    print(f"   Total: {result.get('total', 0)}")
    print(f"   Charged: {result.get('stats', {}).get('charged', 0)}")
    print(f"   Live: {result.get('stats', {}).get('live', 0)}")
    print(f"   CCN: {result.get('stats', {}).get('ccn', 0)}")
    print(f"   Dead: {result.get('stats', {}).get('dead', 0)}")
    print(f"   Errors: {result.get('stats', {}).get('errors', 0)}")
    print(f"⏱️  Elapsed: {elapsed:.2f}s")

    return result


async def test_concurrent_requests(num_requests: int = 50):
    """Test concurrent requests for throughput"""
    print("\n" + "=" * 60)
    print(f"Testing {num_requests} Concurrent Requests")
    print("=" * 60)

    client = CardCheckerClient()

    test_cards = [
        ("4111111111111111", "12", "25", "123"),
        ("5555555555554444", "01", "26", "456"),
        ("378282246310005", "03", "25", "789"),
    ]

    async def make_request(idx: int):
        card = test_cards[idx % len(test_cards)]
        return await client.check_card(*card)

    print(f"\n🚀 Sending {num_requests} concurrent requests...")
    start = time.time()

    tasks = [make_request(i) for i in range(num_requests)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.time() - start
    successful = sum(1 for r in results if not isinstance(r, Exception) and r.get("status") != "error")
    failed = num_requests - successful

    print(f"\n📊 Results:")
    print(f"   Total: {num_requests}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")
    print(f"   Time: {elapsed:.2f}s")
    print(f"   RPS: {num_requests / elapsed:.2f} requests/second")

    return results


def show_stats():
    """Show API statistics"""
    print("\n" + "=" * 60)
    print("API Statistics")
    print("=" * 60)

    client = CardCheckerClient()
    stats = client.get_stats()

    if "stats" in stats:
        s = stats["stats"]
        print(f"\n📈 Stats:")
        print(f"   Charged: {s.get('charged', 0)}")
        print(f"   Live: {s.get('live', 0)}")
        print(f"   CCN: {s.get('ccn', 0)}")
        print(f"   Dead: {s.get('dead', 0)}")
        print(f"   Errors: {s.get('errors', 0)}")
        print(f"   Total Requests: {s.get('total_requests', 0)}")
        print(f"\n⏱️  Uptime: {stats.get('uptime_seconds', 0):.0f}s")
        print(f"📊 RPS: {stats.get('requests_per_second', 0):.2f}")


async def main():
    """Main test suite"""
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     Razorpay Card Checker API - Client Test Suite          ║")
    print("╚════════════════════════════════════════════════════════════╝")

    try:
        # Test 1: Single card
        await test_single_card()

        # Test 2: Bulk cards
        await test_bulk_cards()

        # Test 3: Concurrent requests
        await test_concurrent_requests(20)

        # Show stats
        show_stats()

        print("\n✅ All tests completed!")

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
