"""
Test script to verify all frontend API connections
Tests that all endpoints used by frontend components exist in the backend
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api"

# Test credentials (using one of our generated employees)
TEST_USER = {
    "username": "febby.thomas@company.com",
    "password": "Febby@2024"
}

def get_auth_token():
    """Login and get JWT token"""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data=TEST_USER
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None

def test_endpoint(method, endpoint, token, description, params=None, data=None):
    """Test a single API endpoint"""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, params=params)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        
        status = "✅" if response.status_code in [200, 201] else "⚠️" if response.status_code == 404 else "❌"
        print(f"{status} {method:6} {endpoint:60} - {response.status_code} - {description}")
        
        if response.status_code == 404:
            print(f"   ⚠️  Endpoint not found - needs to be created")
        elif response.status_code >= 400 and response.status_code != 404:
            print(f"   Error: {response.text[:100]}")
        
        return response
    except Exception as e:
        print(f"❌ {method:6} {endpoint:60} - ERROR - {str(e)}")
        return None

def main():
    print("=" * 100)
    print("🔍 TESTING FRONTEND API CONNECTIONS")
    print("=" * 100)
    print()
    
    # Login
    print("📝 Logging in...")
    token = get_auth_token()
    if not token:
        print("❌ Cannot proceed without authentication")
        return
    print(f"✅ Authentication successful\n")
    
    # Test categories
    tests = {
        "🏠 Home Dashboard": [
            ("GET", "/employees/current", "Get current employee info"),
            ("GET", "/attendance/today", "Today's attendance status"),
            ("GET", "/inbox/notifications", "Get notifications"),
            ("GET", "/inbox/stats", "Get inbox stats"),
        ],
        
        "📊 Analytics Dashboard": [
            ("GET", "/analytics/dashboard", "Dashboard overview"),
            ("GET", "/analytics/overview", "Analytics overview"),
            ("GET", "/analytics/attendance-trends", "Attendance trends"),
            ("GET", "/analytics/leave-trends", "Leave trends"),
            ("GET", "/analytics/department-stats", "Department statistics"),
            ("GET", "/analytics/performance-metrics", "Performance metrics"),
            ("GET", "/analytics/workload-distribution", "Workload distribution"),
        ],
        
        "👥 Employee Management": [
            ("GET", "/employees/current", "Current employee"),
            ("GET", "/employees/all/list", "All employees list"),
            ("GET", "/employees/directory", "Employee directory"),
            ("GET", "/employees/organization-tree", "Organization tree"),
            ("GET", "/employees/teammates", "Team members"),
        ],
        
        "⏰ Attendance Module": [
            ("GET", "/attendance/today", "Today's status"),
            ("GET", "/attendance/records", "Attendance records"),
            ("GET", "/attendance/stats", "Attendance statistics"),
        ],
        
        "🏖️ Leave Management": [
            ("GET", "/leaves/types", "Leave types"),
            ("GET", "/leaves/balance", "Leave balance"),
            ("GET", "/leaves/applications", "Leave applications"),
            ("GET", "/leaves/requests", "Leave requests"),
        ],
        
        "👨‍💼 Team Management": [
            ("GET", "/team/members", "Team members"),
            ("GET", "/team/workload", "Team workload"),
            ("GET", "/team/attendance", "Team attendance"),
            ("GET", "/team/leaves", "Team leaves"),
            ("GET", "/team/stats", "Team statistics"),
            ("GET", "/team/tasks", "Team tasks"),
            ("GET", "/team/performance-summary", "Performance summary"),
        ],
        
        "💰 Expenses": [
            ("GET", "/expenses/", "Get expenses"),
            ("GET", "/expenses/stats", "Expense statistics"),
            ("GET", "/expenses/pending-approvals", "Pending approvals"),
        ],
        
        "💸 Payroll": [
            ("GET", "/payroll/payslips", "Get payslips"),
            ("GET", "/payroll/history", "Payroll history"),
        ],
        
        "🎯 Performance": [
            ("GET", "/performance/my-goals", "My goals"),
            ("GET", "/performance/reviews", "Performance reviews"),
            ("GET", "/performance/feedback", "Feedback"),
            ("GET", "/performance/stats", "Performance stats"),
            ("GET", "/performance/goals", "All goals"),
        ],
        
        "🎫 Helpdesk": [
            ("GET", "/helpdesk/tickets", "Get tickets"),
            ("GET", "/helpdesk/stats", "Helpdesk stats"),
        ],
        
        "📋 Policies": [
            ("GET", "/policies", "Get policies"),
            ("GET", "/policies/categories", "Policy categories"),
            ("GET", "/policies/stats", "Policy stats"),
        ],
        
        "🏢 Organization": [
            ("GET", "/organization/departments", "Departments"),
            ("GET", "/organization/tree", "Organization tree"),
        ],
        
        "💬 Messaging": [
            ("GET", "/messages/inbox", "Message inbox"),
            ("GET", "/broadcasts", "Broadcasts"),
            ("GET", "/chat/conversations", "Chat conversations"),
            ("GET", "/chat/active", "Active chats"),
        ],
        
        "📢 Broadcasts": [
            ("GET", "/broadcasts", "Get broadcasts"),
            ("GET", "/broadcasts/teams/", "Get teams"),
        ],
        
        "📝 Tasks": [
            ("GET", "/tasks/", "Get tasks"),
        ],
    }
    
    # Run tests by category
    total_tests = 0
    passed_tests = 0
    missing_endpoints = []
    
    for category, endpoints in tests.items():
        print(f"\n{category}")
        print("-" * 100)
        
        for test_data in endpoints:
            method = test_data[0]
            endpoint = test_data[1]
            description = test_data[2]
            params = test_data[3] if len(test_data) > 3 and isinstance(test_data[3], dict) and 'params' in str(test_data) else None
            data = test_data[4] if len(test_data) > 4 else (test_data[3] if len(test_data) > 3 and isinstance(test_data[3], dict) and 'data' in str(test_data) else None)
            
            # Handle params/data from named arguments
            if len(test_data) > 3:
                for i, item in enumerate(test_data[3:], 3):
                    if isinstance(item, dict):
                        # Check if this was meant as params or data based on method
                        if 'params' in locals() and params is None:
                            params = item
                        elif 'data' in locals() and data is None:
                            data = item
            
            total_tests += 1
            response = test_endpoint(method, endpoint, token, description, params=params, data=data)
            
            if response and response.status_code in [200, 201]:
                passed_tests += 1
            elif response and response.status_code == 404:
                missing_endpoints.append(f"{method} {endpoint} - {description}")
    
    # Summary
    print("\n" + "=" * 100)
    print("📊 TEST SUMMARY")
    print("=" * 100)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests} ✅")
    print(f"Failed: {total_tests - passed_tests} ❌")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
    
    if missing_endpoints:
        print(f"\n⚠️  Missing Endpoints ({len(missing_endpoints)}):")
        for endpoint in missing_endpoints:
            print(f"   - {endpoint}")
    
    print("\n" + "=" * 100)

if __name__ == "__main__":
    main()
