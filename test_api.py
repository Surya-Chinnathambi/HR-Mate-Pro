#!/usr/bin/env python3
"""
Quick smoke test for HRMS backend API
"""
import requests
import json
from time import sleep

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("Testing /health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_register():
    """Test user registration"""
    print("\nTesting /api/auth/register...")
    payload = {
        "email": "demo@hrms.com",
        "password": "demo123",
        "first_name": "Demo",
        "last_name": "User"
    }
    try:
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Registration successful!")
            print(f"Access token: {data['access_token'][:20]}...")
            return data['access_token']
        else:
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_me(token):
    """Test /api/auth/me endpoint"""
    print("\nTesting /api/auth/me...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ User profile retrieved!")
            print(f"Employee ID: {data.get('employee_id')}")
            print(f"Name: {data.get('first_name')} {data.get('last_name')}")
            print(f"Email: {data.get('email')}")
            return True
        else:
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("=" * 60)
    print("HRMS Backend API Smoke Test")
    print("=" * 60)
    
    # Wait for server to be ready
    print("\nWaiting for server to be ready...")
    sleep(2)
    
    # Test health
    if not test_health():
        print("\n❌ Health check failed. Is the server running?")
        return
    
    # Test registration
    token = test_register()
    if not token:
        print("\n⚠️  Registration failed (user might already exist)")
        # Try login instead
        print("\nSkipping to next test...")
    else:
        # Test /me endpoint
        if test_me(token):
            print("\n✅ All tests passed!")
        else:
            print("\n❌ Profile retrieval failed")

if __name__ == "__main__":
    main()
