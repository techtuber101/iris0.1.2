#!/usr/bin/env python3
"""
Test script to verify critical endpoints work properly.

This script tests the main endpoints that were causing 404s and 503s
to ensure they now return appropriate responses.
"""

import asyncio
import httpx
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

async def test_endpoint(method: str, path: str, expected_status: int = 200, **kwargs) -> Dict[str, Any]:
    """Test a single endpoint and return the result."""
    async with httpx.AsyncClient() as client:
        try:
            if method.upper() == "GET":
                response = await client.get(f"{BASE_URL}{path}", **kwargs)
            elif method.upper() == "POST":
                response = await client.post(f"{BASE_URL}{path}", **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            result = {
                "path": path,
                "method": method,
                "status": response.status_code,
                "expected_status": expected_status,
                "success": response.status_code == expected_status,
                "content_type": response.headers.get("content-type", ""),
            }
            
            # Try to parse JSON response
            try:
                result["data"] = response.json()
            except:
                result["text"] = response.text[:200]  # First 200 chars
            
            return result
            
        except Exception as e:
            return {
                "path": path,
                "method": method,
                "status": "ERROR",
                "expected_status": expected_status,
                "success": False,
                "error": str(e)
            }

async def run_tests():
    """Run all endpoint tests."""
    print("🧪 Testing FastAPI endpoints...")
    print("=" * 50)
    
    tests = [
        # Basic endpoints
        ("GET", "/", 200),
        ("GET", "/health", 200),
        
        # API endpoints (should not 404)
        ("GET", "/api/health", 200),
        ("GET", "/api/agents", 200),  # Should return empty list or proper response
        ("GET", "/api/threads", 200),  # Should return empty list or proper response
        
        # Billing endpoints (should return stub responses)
        ("GET", "/billing/check", 200),
        ("GET", "/billing/balance", 200),
        ("GET", "/billing/subscription", 200),
        ("GET", "/billing/available-models", 200),
        
        # Static icon endpoints
        ("GET", "/composio/toolkits/slack.svg", 200),
        ("GET", "/composio/toolkits/gmail.svg", 200),
        ("GET", "/composio/toolkits/notion.svg", 200),
        ("GET", "/composio/toolkits/github.svg", 200),
        
        # Composio API endpoints (should not 404)
        ("GET", "/api/composio/categories", 200),
        ("GET", "/api/composio/toolkits", 200),
    ]
    
    results = []
    for method, path, expected_status in tests:
        print(f"Testing {method} {path}...")
        result = await test_endpoint(method, path, expected_status)
        results.append(result)
        
        if result["success"]:
            print(f"✅ {method} {path} - {result['status']}")
        else:
            print(f"❌ {method} {path} - {result['status']} (expected {expected_status})")
            if "error" in result:
                print(f"   Error: {result['error']}")
    
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    
    passed = sum(1 for r in results if r["success"])
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed < total:
        print("\n❌ Failed Tests:")
        for result in results:
            if not result["success"]:
                print(f"  - {result['method']} {result['path']}: {result.get('status', 'ERROR')}")
    
    return results

if __name__ == "__main__":
    asyncio.run(run_tests())
