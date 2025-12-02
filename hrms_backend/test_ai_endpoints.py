"""Test AI Command Center endpoints"""
import requests
import json

BASE_URL = "http://localhost:8000"

# Get test user credentials
def get_test_token():
    """Login and get token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        data={
            "username": "surya.chandra@company.com",
            "password": "Surya@2024"
        }
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    print(f"Login failed: {response.status_code} - {response.text}")
    return None

def test_ai_endpoints():
    """Test all AI endpoints used by AICommandCenter.tsx"""
    token = get_test_token()
    if not token:
        print("❌ Failed to get authentication token")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    tests = [
        # 1. GET /ai/balance/quick-summary - Used by loadBalanceSummary()
        {
            "method": "GET",
            "endpoint": "/api/ai/balance/quick-summary",
            "description": "Quick Balance Summary (for widget)"
        },
        # 2. GET /ai/history - Used by loadConversation()
        {
            "method": "GET",
            "endpoint": "/api/ai/history",
            "params": {"limit": 50},
            "description": "Chat History"
        },
        # 3. GET /ai/conversations - Used by ChatHistorySidebar
        {
            "method": "GET",
            "endpoint": "/api/ai/conversations",
            "params": {"limit": 20},
            "description": "List of Conversations"
        },
        # 4. POST /ai/chat - Used by handleSend()
        {
            "method": "POST",
            "endpoint": "/api/ai/chat",
            "params": {
                "prompt": "What is my leave balance?",
                "context": json.dumps({
                    "employee": "Test Employee",
                    "role": "Software Engineer"
                })
            },
            "description": "AI Chat"
        },
        # 5. DELETE /ai/history - Used by handleClear()
        {
            "method": "DELETE",
            "endpoint": "/api/ai/history",
            "description": "Clear Chat History"
        }
    ]
    
    print("=" * 80)
    print("Testing AI Command Center Endpoints")
    print("=" * 80)
    
    results = []
    for test in tests:
        print(f"\n🔍 Testing: {test['description']}")
        print(f"   {test['method']} {test['endpoint']}")
        
        try:
            if test["method"] == "GET":
                response = requests.get(
                    f"{BASE_URL}{test['endpoint']}",
                    headers=headers,
                    params=test.get("params", {}),
                    timeout=10
                )
            elif test["method"] == "POST":
                response = requests.post(
                    f"{BASE_URL}{test['endpoint']}",
                    headers=headers,
                    params=test.get("params", {}),
                    json=test.get("json", None),
                    timeout=15  # AI chat might take longer
                )
            elif test["method"] == "DELETE":
                response = requests.delete(
                    f"{BASE_URL}{test['endpoint']}",
                    headers=headers,
                    timeout=10
                )
            
            status_icon = "✅" if response.status_code in [200, 201] else "❌"
            print(f"   {status_icon} Status: {response.status_code}")
            
            # Show response preview
            if response.status_code in [200, 201]:
                try:
                    data = response.json()
                    print(f"   📄 Response preview: {json.dumps(data, indent=2)[:200]}...")
                except:
                    print(f"   📄 Response: {response.text[:200]}")
            else:
                print(f"   ⚠️  Error: {response.text[:300]}")
            
            results.append({
                "endpoint": test['endpoint'],
                "status": response.status_code,
                "success": response.status_code in [200, 201]
            })
            
        except requests.exceptions.ConnectionError:
            print(f"   ❌ CONNECTION ERROR - Backend not running on {BASE_URL}")
            results.append({
                "endpoint": test['endpoint'],
                "status": "Connection Error",
                "success": False
            })
        except requests.exceptions.Timeout:
            print(f"   ❌ TIMEOUT - Request took too long")
            results.append({
                "endpoint": test['endpoint'],
                "status": "Timeout",
                "success": False
            })
        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            results.append({
                "endpoint": test['endpoint'],
                "status": str(e),
                "success": False
            })
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    working = sum(1 for r in results if r["success"])
    total = len(results)
    
    print(f"\n✅ Working: {working}/{total}")
    print(f"❌ Failing: {total - working}/{total}")
    
    if working == total:
        print("\n🎉 ALL AI ENDPOINTS ARE WORKING!")
    else:
        print("\n⚠️  SOME ENDPOINTS NEED ATTENTION:")
        for r in results:
            if not r["success"]:
                print(f"   ❌ {r['endpoint']} - Status: {r['status']}")
    
    print("=" * 80)

if __name__ == "__main__":
    test_ai_endpoints()
