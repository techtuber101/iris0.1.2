#!/usr/bin/env python3
"""
Test script for streaming functionality.
This script tests the Redis pub/sub streaming pipeline end-to-end.
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from core.services import redis_client

async def test_streaming():
    """Test the streaming pipeline by publishing events and verifying they're received."""
    
    print("🧪 Testing Redis streaming pipeline...")
    
    # Test thread ID
    test_thread_id = "test-thread-123"
    thread_channel = f"thread:{test_thread_id}"
    
    try:
        # Create a subscriber
        print(f"📡 Creating subscriber for channel: {thread_channel}")
        subscriber = await redis_client.create_dedicated_pubsub()
        await subscriber.subscribe(thread_channel)
        
        # Create a publisher
        print("📤 Creating publisher...")
        publisher = await redis_client.get_publisher()
        
        # Set up message collection
        received_messages = []
        
        async def collect_messages():
            """Collect messages from the subscriber."""
            async for message in subscriber.listen():
                if message['type'] == 'message':
                    data = message['data']
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    
                    try:
                        event = json.loads(data)
                        received_messages.append(event)
                        print(f"📨 Received: {event}")
                    except json.JSONDecodeError:
                        print(f"⚠️ Failed to parse message: {data}")
        
        # Start message collection
        collection_task = asyncio.create_task(collect_messages())
        
        # Wait a moment for subscription to be ready
        await asyncio.sleep(0.1)
        
        # Publish test events
        test_events = [
            {
                'type': 'token',
                'threadId': test_thread_id,
                'content': 'Hello',
                'ts': int(datetime.now().timestamp() * 1000)
            },
            {
                'type': 'token',
                'threadId': test_thread_id,
                'content': ' world',
                'ts': int(datetime.now().timestamp() * 1000)
            },
            {
                'type': 'status',
                'threadId': test_thread_id,
                'content': {'status': 'processing'},
                'ts': int(datetime.now().timestamp() * 1000)
            },
            {
                'type': 'done',
                'threadId': test_thread_id,
                'content': {'message': 'Test completed'},
                'ts': int(datetime.now().timestamp() * 1000)
            }
        ]
        
        print(f"📤 Publishing {len(test_events)} test events...")
        for i, event in enumerate(test_events):
            await redis_client.publish_to_channel(thread_channel, json.dumps(event))
            print(f"  ✅ Published event {i+1}: {event['type']}")
            await asyncio.sleep(0.1)  # Small delay between events
        
        # Wait for messages to be received
        print("⏳ Waiting for messages to be received...")
        await asyncio.sleep(1.0)
        
        # Stop collection
        collection_task.cancel()
        try:
            await collection_task
        except asyncio.CancelledError:
            pass
        
        # Verify results
        print(f"\n📊 Results:")
        print(f"  - Published: {len(test_events)} events")
        print(f"  - Received: {len(received_messages)} events")
        
        if len(received_messages) == len(test_events):
            print("✅ SUCCESS: All events were received!")
            return True
        else:
            print("❌ FAILURE: Not all events were received")
            print(f"Missing events: {len(test_events) - len(received_messages)}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
        
    finally:
        # Cleanup
        try:
            await subscriber.unsubscribe(thread_channel)
            await subscriber.close()
            await publisher.close()
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")

async def test_encoding():
    """Test that encoding is consistent between publisher and subscriber."""
    print("\n🔤 Testing encoding consistency...")
    
    test_channel = "test-encoding"
    test_message = "Hello, 世界! 🌍"
    
    try:
        # Create subscriber
        subscriber = await redis_client.create_dedicated_pubsub()
        await subscriber.subscribe(test_channel)
        
        # Create publisher
        publisher = await redis_client.get_publisher()
        
        received_message = None
        
        async def collect_message():
            nonlocal received_message
            async for message in subscriber.listen():
                if message['type'] == 'message':
                    data = message['data']
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    received_message = data
                    break
        
        # Start collection
        collection_task = asyncio.create_task(collect_message())
        await asyncio.sleep(0.1)
        
        # Publish message
        await redis_client.publish_to_channel(test_channel, test_message)
        
        # Wait for message
        await asyncio.sleep(0.5)
        
        # Stop collection
        collection_task.cancel()
        try:
            await collection_task
        except asyncio.CancelledError:
            pass
        
        # Verify
        if received_message == test_message:
            print("✅ SUCCESS: Encoding is consistent!")
            return True
        else:
            print(f"❌ FAILURE: Encoding mismatch")
            print(f"  Expected: {test_message}")
            print(f"  Received: {received_message}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
        
    finally:
        # Cleanup
        try:
            await subscriber.unsubscribe(test_channel)
            await subscriber.close()
            await publisher.close()
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")

async def main():
    """Run all tests."""
    print("🚀 Starting streaming tests...\n")
    
    # Initialize Redis client
    await redis_client.initialize_async()
    
    # Run tests
    test1_passed = await test_streaming()
    test2_passed = await test_encoding()
    
    print(f"\n📋 Test Summary:")
    print(f"  - Streaming test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"  - Encoding test: {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! Streaming pipeline is working correctly.")
        return 0
    else:
        print("\n💥 Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
