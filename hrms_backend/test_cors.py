"""Quick test script to verify backend API endpoints"""
import requests
import json

BASE_URL = "http://localhost:8000"

print("🧪 Testing Backend API Endpoints\n")

# Test 1: Health check
print("1️⃣ Testing Health Check...")
try:
    response = requests.get(f"{BASE_URL}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}\n")
except Exception as e:
    print(f"   ❌ Error: {e}\n")

# Test 2: Register new user
print("2️⃣ Testing User Registration...")
register_data = {
    "email": "test@example.com",
    "password": "Test123!@#",
    "full_name": "Test User",
    "employee_id": "EMP001",
    "department": "IT",
    "position": "Developer"
}
try:
    response = requests.post(f"{BASE_URL}/api/auth/register", json=register_data)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ User created: {data.get('user', {}).get('email')}")
        print(f"   Access Token: {data.get('access_token', 'N/A')[:50]}...\n")
        access_token = data.get('access_token')
    else:
        print(f"   Response: {response.text}\n")
        access_token = None
except Exception as e:
    print(f"   ❌ Error: {e}\n")
    access_token = None

# Test 3: Login
print("3️⃣ Testing Login...")
login_data = {
    "username": "test@example.com",
    "password": "Test123!@#"
}
try:
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        data=login_data,  # OAuth2 uses form data, not JSON
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Login successful!")
        print(f"   Access Token: {data.get('access_token', 'N/A')[:50]}...\n")
        access_token = data.get('access_token')
    else:
        print(f"   Response: {response.text}\n")
except Exception as e:
    print(f"   ❌ Error: {e}\n")

# Test 4: Get current user (authenticated)
if access_token:
    print("4️⃣ Testing Get Current User (Authenticated)...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ User: {data.get('email')}")
            print(f"   Name: {data.get('full_name')}")
            print(f"   Role: {data.get('role')}\n")
        else:
            print(f"   Response: {response.text}\n")
    except Exception as e:
        print(f"   ❌ Error: {e}\n")
else:
    print("4️⃣ Skipping authenticated test (no access token)\n")

print("✅ Test complete!")
