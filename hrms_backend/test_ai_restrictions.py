#!/usr/bin/env python3
"""
Test script to verify AI chatbot restrictions
Tests that AI rejects non-HR queries and only responds to HR-related topics
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def get_test_token() -> str:
    """Login and get auth token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={
            "email": "admin@company.com",
            "password": "Admin@123"
        }
    )
    return response.json()["access_token"]

def test_ai_chat(token: str, message: str) -> Dict[str, Any]:
    """Send a message to AI and get response"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BASE_URL}/api/ai/chat",
        headers=headers,
        json={"message": message}
    )
    return response.json()

def main():
    print("=" * 100)
    print("AI CHATBOT RESTRICTION TEST")
    print("Testing that AI only responds to HR-related queries")
    print("=" * 100)
    print()
    
    # Get auth token
    token = get_test_token()
    
    # Test cases
    test_cases = [
        {
            "category": "❌ NON-HR: Grocery List",
            "message": "Give me a grocery list for this week",
            "should_reject": True
        },
        {
            "category": "❌ NON-HR: Recipe",
            "message": "How do I make chocolate cake?",
            "should_reject": True
        },
        {
            "category": "❌ NON-HR: General Knowledge",
            "message": "What is the capital of France?",
            "should_reject": True
        },
        {
            "category": "❌ NON-HR: Math Help",
            "message": "Solve this equation: 2x + 5 = 15",
            "should_reject": True
        },
        {
            "category": "❌ NON-HR: Travel Advice",
            "message": "What are the best places to visit in Italy?",
            "should_reject": True
        },
        {
            "category": "✅ HR: Leave Request",
            "message": "I want to apply for leave on December 25th",
            "should_reject": False
        },
        {
            "category": "✅ HR: Attendance Query",
            "message": "What's my attendance status this month?",
            "should_reject": False
        },
        {
            "category": "✅ HR: Task Management",
            "message": "Show me my pending tasks",
            "should_reject": False
        },
        {
            "category": "✅ HR: Team Workload",
            "message": "How is my team's workload this week?",
            "should_reject": False
        },
        {
            "category": "✅ HR: Company Policy",
            "message": "What is the leave policy for sick leave?",
            "should_reject": False
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n{'='*100}")
        print(f"🧪 Test: {test_case['category']}")
        print(f"📝 Message: {test_case['message']}")
        print("-" * 100)
        
        try:
            response = test_ai_chat(token, test_case['message'])
            ai_response = response.get('response', '')
            
            print(f"🤖 AI Response:\n{ai_response}\n")
            
            # Check if AI properly rejected/accepted based on query type
            rejection_keywords = [
                "specifically designed to assist with HR",
                "HR and workplace-related tasks only",
                "outside your scope",
                "not authorized",
                "HR-related tasks only"
            ]
            
            is_rejected = any(keyword.lower() in ai_response.lower() for keyword in rejection_keywords)
            
            if test_case['should_reject']:
                if is_rejected:
                    print("✅ PASS: AI correctly rejected non-HR query")
                    results.append(("PASS", test_case['category']))
                else:
                    print("❌ FAIL: AI should have rejected this non-HR query but didn't")
                    results.append(("FAIL", test_case['category']))
            else:
                if not is_rejected:
                    print("✅ PASS: AI correctly responded to HR query")
                    results.append(("PASS", test_case['category']))
                else:
                    print("❌ FAIL: AI rejected a valid HR query")
                    results.append(("FAIL", test_case['category']))
                    
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            results.append(("ERROR", test_case['category']))
    
    # Final Summary
    print("\n" + "=" * 100)
    print("FINAL SUMMARY")
    print("=" * 100)
    
    passed = sum(1 for r in results if r[0] == "PASS")
    failed = sum(1 for r in results if r[0] == "FAIL")
    errors = sum(1 for r in results if r[0] == "ERROR")
    total = len(results)
    
    print(f"\n📊 Results:")
    print(f"   Total Tests: {total}")
    print(f"   ✅ Passed: {passed} ({passed/total*100:.1f}%)")
    print(f"   ❌ Failed: {failed} ({failed/total*100:.1f}%)")
    print(f"   ⚠️  Errors: {errors} ({errors/total*100:.1f}%)")
    
    print("\n📋 Details:")
    for status, category in results:
        icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"   {icon} {category}")
    
    if failed == 0 and errors == 0:
        print("\n🎉 All tests passed! AI is properly restricted to HR queries only.")
    else:
        print("\n⚠️  Some tests failed. AI restrictions may need adjustment.")
    
    print("=" * 100)

if __name__ == "__main__":
    main()
