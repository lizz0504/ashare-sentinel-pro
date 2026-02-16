#!/usr/bin/env python
"""
Auth Diagnostic Script - Test JWT Authentication Flow
"""
import os
import sys
import traceback
from datetime import datetime, timedelta

print("=" * 60)
print("JWT Auth Diagnostic Script")
print("=" * 60)
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# 1. Check Environment Variables
print("[Step 1] Check Environment Variables")
print("-" * 40)

supabase_jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
supabase_url = os.getenv("SUPABASE_URL")

print(f"SUPABASE_JWT_SECRET: {'SET' if supabase_jwt_secret else 'NOT SET'}")
print(f"SUPABASE_URL: {'SET' if supabase_url else 'NOT SET'}")
print()

if not supabase_jwt_secret:
    print("ERROR: SUPABASE_JWT_SECRET not set")
    sys.exit(1)

# 2. Test JWT Decode
print("[Step 2] Test JWT Decode")
print("-" * 40)

try:
    import jwt

    # Create a test JWT token
    test_payload = {
        "sub": "test-user-id",
        "email": "test@example.com",
        "role": "authenticated",
        "exp": datetime.now() + timedelta(hours=1)
    }

    test_token = jwt.encode(test_payload, supabase_jwt_secret, algorithm="HS256")
    print(f"OK - Created test token: {test_token[:50]}...")

    # Decode test
    decoded = jwt.decode(test_token, supabase_jwt_secret, algorithms=["HS256"])
    print(f"OK - Decoded token: {decoded}")

except Exception as e:
    print(f"FAIL - JWT test failed: {str(e)}")
    traceback.print_exc()
    sys.exit(1)

print()

# 3. Check main.py for get_current_user function
print("[Step 3] Check get_current_user Function")
print("-" * 40)

try:
    # Read main.py to find get_current_user function
    with open("app/main.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Check if get_current_user exists
    if "get_current_user" in content:
        print("OK - Found get_current_user function")

        # Extract function signature
        import re
        pattern = r"async def get_current_user\([^)]+\):"
        match = re.search(pattern, content)
        if match:
            print(f"  Function signature: get_current_user{match.group(1)}")
        else:
            print("  Cannot parse function signature")
    else:
        print("FAIL - get_current_user function NOT FOUND")

    # Check for Depends(get_current_user)
    if "Depends(get_current_user)" in content:
        print("OK - Found Depends(get_current_user) decorator")
    else:
        print("FAIL - Depends(get_current_user) decorator NOT FOUND")

except Exception as e:
    print(f"FAIL - Cannot read main.py: {str(e)}")
    traceback.print_exc()

print()

# 4. Test Backend Root Path
print("[Step 4] Test Backend API Root Path")
print("-" * 40)

try:
    import requests

    # Test root path
    root_url = "http://localhost:8000/"
    print(f"Testing: {root_url}")

    response = requests.get(root_url, timeout=5)
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        print("OK - Root path is working")
        print(f"Response: {response.text[:200]}")
    else:
        print(f"FAIL - Root path returned error: {response.status_code}")
        print(f"Response: {response.text[:500]}")

except Exception as e:
    print(f"FAIL - Request failed: {str(e)}")
    traceback.print_exc()

print()
print("=" * 60)
print("Diagnostic Complete")
print("=" * 60)
