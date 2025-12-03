"""Test Redis connection to Railway"""
import asyncio
import redis.asyncio as redis
import os
from dotenv import load_dotenv

# Load Railway environment variables
load_dotenv("hrms_backend/.env")

async def test_redis():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    print("🔍 Testing Redis Connection...")
    print(f"Redis URL: {redis_url.split('@')[-1] if '@' in redis_url else redis_url}")
    print("=" * 60)
    
    try:
        # Connect to Redis
        r = await redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        
        # Test 1: Ping
        print("\n1. Testing PING:")
        pong = await r.ping()
        print(f"   ✅ PING response: {pong}")
        
        # Test 2: Set a key
        print("\n2. Testing SET:")
        await r.set("test_key", "Hello from Railway!", ex=60)  # Expire in 60 seconds
        print("   ✅ Key set successfully")
        
        # Test 3: Get the key
        print("\n3. Testing GET:")
        value = await r.get("test_key")
        print(f"   ✅ Retrieved value: {value}")
        
        # Test 4: Store a hash (like conversation context)
        print("\n4. Testing HASH (conversation context):")
        test_conv_id = "test_conversation_123"
        test_message = {
            "role": "user",
            "content": "What is my leave balance?",
            "timestamp": "2025-12-03T14:30:00",
            "intent": "check_leave_balance"
        }
        
        await r.hset(
            f"session:test_user:messages",
            test_conv_id,
            str(test_message)
        )
        print("   ✅ Hash stored successfully")
        
        # Test 5: Retrieve the hash
        print("\n5. Testing HGET:")
        retrieved = await r.hget(f"session:test_user:messages", test_conv_id)
        print(f"   ✅ Retrieved message: {retrieved[:100]}...")
        
        # Test 6: List all keys
        print("\n6. Testing KEYS:")
        keys = await r.keys("test_*")
        print(f"   ✅ Found {len(keys)} test keys: {keys}")
        
        # Test 7: Check conversation history keys
        print("\n7. Checking existing conversation keys:")
        conv_keys = await r.keys("session:*:messages")
        print(f"   Found {len(conv_keys)} conversation sessions")
        if conv_keys:
            for key in conv_keys[:3]:
                print(f"   - {key}")
        
        # Cleanup
        print("\n8. Cleanup:")
        await r.delete("test_key")
        await r.delete(f"session:test_user:messages")
        print("   ✅ Test keys deleted")
        
        await r.close()
        
        print("\n" + "=" * 60)
        print("✅ All Redis tests passed!")
        print("\n🎯 Redis is properly configured and working with Railway!")
        
    except Exception as e:
        print(f"\n❌ Redis connection failed!")
        print(f"Error: {e}")
        print("\nPossible issues:")
        print("1. Check REDIS_URL environment variable")
        print("2. Verify Railway Redis service is running")
        print("3. Check network connectivity")

if __name__ == "__main__":
    asyncio.run(test_redis())
