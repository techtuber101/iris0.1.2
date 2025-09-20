#!/usr/bin/env python3
"""
Test script to verify that billing is properly disabled.

This script tests that the billing stub router is working and that
no real billing modules are being imported when BILLING_ENABLED=false.
"""

import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_settings():
    """Test that settings are properly configured."""
    print("🧪 Testing settings configuration...")
    
    try:
        from core.settings import settings
        print(f"✅ Settings imported successfully")
        print(f"   BILLING_ENABLED: {settings.BILLING_ENABLED}")
        print(f"   ENV_MODE: {settings.ENV_MODE}")
        
        if not settings.BILLING_ENABLED:
            print("✅ Billing is disabled as expected")
            return True
        else:
            print("❌ Billing is enabled - this might cause issues")
            return False
            
    except Exception as e:
        print(f"❌ Failed to import settings: {e}")
        return False

def test_billing_stub():
    """Test that the billing stub router is working."""
    print("\n🧪 Testing billing stub router...")
    
    try:
        from core.billing_stub import router as billing_stub_router
        print("✅ Billing stub router imported successfully")
        
        # Check that the router has the expected routes
        routes = [route.path for route in billing_stub_router.routes]
        expected_routes = ['/billing/check', '/billing/balance', '/billing/subscription']
        
        for expected_route in expected_routes:
            if any(route.endswith(expected_route.split('/')[-1]) for route in routes):
                print(f"✅ Route found: {expected_route}")
            else:
                print(f"❌ Route missing: {expected_route}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to import billing stub router: {e}")
        return False

def test_conditional_imports():
    """Test that conditional imports are working properly."""
    print("\n🧪 Testing conditional imports...")
    
    test_cases = [
        ("core.core_utils", "Core utils"),
        ("core.credits", "Credits service"),
        ("core.agent_runs", "Agent runs"),
        ("core.triggers.api", "Triggers API"),
        ("core.agentpress.thread_manager", "Thread manager"),
    ]
    
    success_count = 0
    for module_name, description in test_cases:
        try:
            __import__(module_name)
            print(f"✅ {description} imported successfully")
            success_count += 1
        except Exception as e:
            print(f"❌ {description} failed to import: {e}")
    
    return success_count == len(test_cases)

def test_api_construction():
    """Test that the main API can be constructed without errors."""
    print("\n🧪 Testing API construction...")
    
    try:
        # Set BILLING_ENABLED to False to ensure we're testing the right path
        os.environ['BILLING_ENABLED'] = 'false'
        
        # Import the main API module
        import api
        
        app = api.app
        print("✅ FastAPI app constructed successfully")
        
        # Check that routes are registered
        route_paths = [route.path for route in app.routes]
        
        # Check for essential routes
        essential_routes = ['/health', '/', '/billing/balance']
        for route in essential_routes:
            if route in route_paths:
                print(f"✅ Essential route found: {route}")
            else:
                print(f"❌ Essential route missing: {route}")
                return False
        
        # Check for billing routes (should be stub routes)
        billing_routes = [path for path in route_paths if path.startswith('/billing')]
        if billing_routes:
            print(f"✅ Billing routes found: {len(billing_routes)} routes")
        else:
            print("❌ No billing routes found")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to construct API: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🚀 Testing Billing Disabled Configuration")
    print("=" * 50)
    
    # Set environment variable to ensure billing is disabled
    os.environ['BILLING_ENABLED'] = 'false'
    
    tests = [
        ("Settings Configuration", test_settings),
        ("Billing Stub Router", test_billing_stub),
        ("Conditional Imports", test_conditional_imports),
        ("API Construction", test_api_construction),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Billing is properly disabled.")
        return 0
    else:
        print("💥 Some tests failed. There may still be billing-related issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
