#!/usr/bin/env python3
"""
Cache Functionality Test Suite for Gemini Cache Manager

This script tests the cache implementation for the LLM endpoint optimization.
Run this after starting the server to validate cache behavior.
"""

import asyncio
import aiohttp
import json
import time
import logging
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CacheTestSuite:
    def __init__(self, base_url: str = "http://localhost:8000", test_account: str = "test_account", test_user: str = "testuser"):
        self.base_url = base_url
        self.test_account = test_account
        self.test_user = test_user
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def set_auth_headers(self) -> Dict[str, str]:
        """Set up authentication headers for testing"""
        return {
            "Content-Type": "application/json",
            # Add your authentication headers here if needed
            # "Authorization": "Bearer your_token",
            # Or use cookies/session data as needed
        }

    async def test_cache_stats_endpoint(self) -> bool:
        """Test the cache statistics endpoint"""
        logger.info("🧪 Testing cache stats endpoint...")
        
        try:
            headers = await self.set_auth_headers()
            async with self.session.get(f"{self.base_url}/api/cache/stats", headers=headers) as response:
                if response.status == 200:
                    stats = await response.json()
                    logger.info(f"✅ Cache stats retrieved: {stats}")
                    return True
                else:
                    logger.error(f"❌ Cache stats endpoint failed: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Cache stats test error: {e}")
            return False

    async def test_cache_refresh_endpoint(self) -> bool:
        """Test the manual cache refresh endpoint"""
        logger.info("🧪 Testing cache refresh endpoint...")
        
        try:
            headers = await self.set_auth_headers()
            async with self.session.post(f"{self.base_url}/api/cache/refresh", headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ Cache refresh successful: {result}")
                    return True
                else:
                    logger.error(f"❌ Cache refresh endpoint failed: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Cache refresh test error: {e}")
            return False

    async def test_llm_performance_with_cache(self) -> Dict[str, float]:
        """Test LLM endpoint performance with and without cache"""
        logger.info("🧪 Testing LLM performance with cache optimization...")
        
        test_prompt = "Hello, how are you today?"
        headers = await self.set_auth_headers()
        
        performance_results = {}
        
        try:
            # First, clear the cache
            await self.session.post(f"{self.base_url}/api/cache/refresh", headers=headers)
            
            # Test 1: First call (no cache)
            logger.info("Testing first LLM call (cold cache)...")
            start_time = time.time()
            
            async with self.session.post(
                f"{self.base_url}/llm", 
                headers=headers,
                json={"prompt": test_prompt}
            ) as response:
                if response.status == 200:
                    await response.json()
                    cold_time = time.time() - start_time
                    performance_results["cold_cache"] = cold_time
                    logger.info(f"✅ Cold cache LLM call: {cold_time:.2f}s")
                else:
                    logger.error(f"❌ Cold cache LLM call failed: {response.status}")
                    return {}

            # Test 2: Second call (warm cache)
            logger.info("Testing second LLM call (warm cache)...")
            start_time = time.time()
            
            async with self.session.post(
                f"{self.base_url}/llm", 
                headers=headers,
                json={"prompt": test_prompt + " (second call)"}
            ) as response:
                if response.status == 200:
                    await response.json()
                    warm_time = time.time() - start_time
                    performance_results["warm_cache"] = warm_time
                    logger.info(f"✅ Warm cache LLM call: {warm_time:.2f}s")
                    
                    # Calculate improvement
                    if cold_time > 0:
                        improvement = ((cold_time - warm_time) / cold_time) * 100
                        performance_results["improvement_percent"] = improvement
                        logger.info(f"🚀 Performance improvement: {improvement:.1f}%")
                else:
                    logger.error(f"❌ Warm cache LLM call failed: {response.status}")
                    
        except Exception as e:
            logger.error(f"❌ Performance test error: {e}")
            
        return performance_results

    async def test_cache_invalidation(self) -> bool:
        """Test cache invalidation when data is updated"""
        logger.info("🧪 Testing cache invalidation...")
        
        headers = await self.set_auth_headers()
        
        try:
            # First, make an LLM call to populate cache
            await self.session.post(
                f"{self.base_url}/llm", 
                headers=headers,
                json={"prompt": "Test cache population"}
            )
            
            # Get initial cache stats
            async with self.session.get(f"{self.base_url}/api/cache/stats", headers=headers) as response:
                if response.status == 200:
                    initial_stats = await response.json()
                    logger.info(f"Initial cache stats: {initial_stats}")
                else:
                    logger.error("Failed to get initial cache stats")
                    return False

            # Simulate updating user info (should invalidate USER_PROFILE cache)
            test_update = {
                "narrative": "Updated user information for cache test"
            }
            
            async with self.session.post(
                f"{self.base_url}/update-user-info", 
                headers=headers,
                json=test_update
            ) as response:
                if response.status == 200:
                    logger.info("✅ User info updated successfully")
                else:
                    logger.warning(f"User info update returned: {response.status}")

            # Check if cache was invalidated
            await asyncio.sleep(1)  # Give time for invalidation
            
            async with self.session.get(f"{self.base_url}/api/cache/stats", headers=headers) as response:
                if response.status == 200:
                    updated_stats = await response.json()
                    logger.info(f"Updated cache stats: {updated_stats}")
                    
                    # Compare cache timestamps or entries
                    if updated_stats != initial_stats:
                        logger.info("✅ Cache invalidation working - stats changed after update")
                        return True
                    else:
                        logger.warning("⚠️  Cache stats unchanged - invalidation may not be working")
                        return False
                else:
                    logger.error("Failed to get updated cache stats")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Cache invalidation test error: {e}")
            return False

    async def test_concurrent_cache_access(self) -> bool:
        """Test cache behavior under concurrent access"""
        logger.info("🧪 Testing concurrent cache access...")
        
        headers = await self.set_auth_headers()
        
        async def make_llm_call(call_id: int):
            try:
                async with self.session.post(
                    f"{self.base_url}/llm", 
                    headers=headers,
                    json={"prompt": f"Concurrent test call {call_id}"}
                ) as response:
                    if response.status == 200:
                        return f"Call {call_id}: Success"
                    else:
                        return f"Call {call_id}: Failed ({response.status})"
            except Exception as e:
                return f"Call {call_id}: Error ({e})"

        try:
            # Make 5 concurrent calls
            concurrent_calls = [make_llm_call(i) for i in range(5)]
            results = await asyncio.gather(*concurrent_calls)
            
            success_count = sum(1 for result in results if "Success" in result)
            logger.info(f"Concurrent test results: {success_count}/5 successful")
            
            for result in results:
                logger.info(f"  {result}")
                
            return success_count >= 4  # Allow 1 failure
            
        except Exception as e:
            logger.error(f"❌ Concurrent access test error: {e}")
            return False

    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all cache functionality tests"""
        logger.info("🚀 Starting Cache Functionality Test Suite")
        logger.info("=" * 50)
        
        test_results = {}
        
        # Test 1: Cache Stats Endpoint
        test_results["cache_stats"] = await self.test_cache_stats_endpoint()
        
        # Test 2: Cache Refresh Endpoint
        test_results["cache_refresh"] = await self.test_cache_refresh_endpoint()
        
        # Test 3: Performance Testing
        performance_results = await self.test_llm_performance_with_cache()
        test_results["performance_test"] = bool(performance_results)
        if performance_results:
            test_results["performance_data"] = performance_results
        
        # Test 4: Cache Invalidation
        test_results["cache_invalidation"] = await self.test_cache_invalidation()
        
        # Test 5: Concurrent Access
        test_results["concurrent_access"] = await self.test_concurrent_cache_access()
        
        # Summary
        logger.info("=" * 50)
        logger.info("🏁 Test Suite Complete!")
        
        passed_tests = sum(1 for result in test_results.values() if isinstance(result, bool) and result)
        total_tests = sum(1 for result in test_results.values() if isinstance(result, bool))
        
        logger.info(f"Results: {passed_tests}/{total_tests} tests passed")
        
        for test_name, result in test_results.items():
            if isinstance(result, bool):
                status = "✅ PASS" if result else "❌ FAIL"
                logger.info(f"  {test_name}: {status}")
        
        return test_results


async def main():
    """Main test runner"""
    print("Cache Functionality Test Suite")
    print("=" * 50)
    print("Make sure your server is running on http://localhost:8000")
    print("=" * 50)
    
    async with CacheTestSuite() as test_suite:
        results = await test_suite.run_all_tests()
        
        # Print final summary
        print("\n" + "=" * 50)
        print("FINAL RESULTS")
        print("=" * 50)
        
        if results.get("performance_data"):
            perf = results["performance_data"]
            print(f"Performance Results:")
            print(f"  Cold Cache: {perf.get('cold_cache', 0):.2f}s")
            print(f"  Warm Cache: {perf.get('warm_cache', 0):.2f}s")
            if perf.get('improvement_percent'):
                print(f"  Improvement: {perf['improvement_percent']:.1f}%")
        
        return results


if __name__ == "__main__":
    asyncio.run(main())
