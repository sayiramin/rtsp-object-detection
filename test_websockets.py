#!/usr/bin/env python3

import asyncio
import websockets
import json

async def test_websocket():
    """Test WebSocket connections"""
    print("Testing WebSocket connections...")
    
    try:
        # Test video WebSocket
        print("Connecting to video WebSocket...")
        async with websockets.connect("ws://localhost:8000/ws/video") as websocket:
            print("✅ Video WebSocket connected!")
            
            # Wait for a message
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(message)
            print(f"📹 Received: {data['type']}")
            
    except Exception as e:
        print(f"❌ Video WebSocket failed: {e}")
    
    try:
        # Test alerts WebSocket
        print("Connecting to alerts WebSocket...")
        async with websockets.connect("ws://localhost:8000/ws/alerts") as websocket:
            print("✅ Alerts WebSocket connected!")
            
            # Wait for a message
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(message)
            print(f"🔔 Received: {data['type']}")
            
    except Exception as e:
        print(f"❌ Alerts WebSocket failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
