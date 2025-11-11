#!/usr/bin/env python3
"""
WebSocket Test Client

Simple test client to verify the WebSocket backend works correctly.
Tests basic message flow and agent responses.

Usage:
    python web_ui/test_websocket.py
"""

import asyncio
import json
import websockets
from datetime import datetime


async def test_websocket():
    """Test the WebSocket endpoint."""
    uri = "ws://localhost:8080/chat"

    print("=" * 80)
    print("WebSocket Test Client")
    print("=" * 80)
    print(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected!")
            print("\nWaiting for messages from server...")
            print("-" * 80)

            # Track if we received initialization message
            initialized = False
            message_count = 0
            start_time = datetime.now()

            # Send a test message after initialization
            test_message_sent = False

            while True:
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=60.0  # 60 second timeout
                    )

                    message_count += 1
                    data = json.loads(message)
                    msg_type = data.get('type', 'unknown')
                    timestamp = data.get('timestamp', '')

                    print(f"\n[{message_count}] Received {msg_type}:")

                    # Handle different message types
                    if msg_type == 'status':
                        content = data.get('content', '')
                        print(f"  Status: {content}")

                        # Check for initialization complete
                        if 'ready' in content.lower():
                            initialized = True
                            print("  ✓ Agent initialized!")

                    elif msg_type == 'agent_message':
                        content = data.get('content', '')
                        print(f"  Agent: {content}")

                        # Send test message after welcome
                        if not test_message_sent and initialized:
                            test_message_sent = True

                            # Wait a moment
                            await asyncio.sleep(1)

                            # Send a test query
                            print("\n" + "=" * 80)
                            print("Sending test message: 'What objects are available?'")
                            print("=" * 80)

                            await websocket.send(json.dumps({
                                "type": "message",
                                "content": "What objects are available?"
                            }))

                    elif msg_type == 'tool':
                        tool = data.get('tool', 'unknown')
                        status = data.get('status', 'unknown')
                        print(f"  Tool: {tool} ({status})")

                    elif msg_type == 'result':
                        success = data.get('success', False)
                        result_data = data.get('data', {})
                        description = data.get('description', 'N/A')

                        print(f"  Success: {success}")
                        print(f"  Description: {description}")

                        if result_data:
                            # Show summary of data
                            if isinstance(result_data, dict):
                                print(f"  Data keys: {', '.join(result_data.keys())}")

                                if 'count' in result_data:
                                    print(f"  Count: {result_data['count']}")

                                if 'objects' in result_data:
                                    objects = result_data['objects']
                                    print(f"  Objects: {', '.join(objects)}")
                            else:
                                print(f"  Data: {result_data}")

                        # After receiving results, we're done testing
                        print("\n" + "=" * 80)
                        print("✓ Test completed successfully!")
                        print(f"  Total messages: {message_count}")
                        elapsed = (datetime.now() - start_time).total_seconds()
                        print(f"  Elapsed time: {elapsed:.1f}s")
                        print("=" * 80)
                        return

                    elif msg_type == 'error':
                        error = data.get('error', 'Unknown error')
                        print(f"  ✗ Error: {error}")

                    elif msg_type == 'typing':
                        is_typing = data.get('is_typing', False)
                        print(f"  Typing: {is_typing}")

                    else:
                        print(f"  Data: {json.dumps(data, indent=2)}")

                except asyncio.TimeoutError:
                    print("\n✗ Timeout waiting for message")
                    break

                except websockets.exceptions.ConnectionClosed:
                    print("\n✗ Connection closed by server")
                    break

    except ConnectionRefusedError:
        print("✗ Connection refused!")
        print("  Make sure the server is running:")
        print("  uvicorn web_ui.app:app --reload --port 8080")
        return

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()


async def test_simple_message():
    """Test sending a simple message and receiving response."""
    uri = "ws://localhost:8080/chat"

    print("=" * 80)
    print("Simple Message Test")
    print("=" * 80)

    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected")

            # Wait for welcome message
            print("\nWaiting for welcome message...")
            for i in range(10):
                message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                data = json.loads(message)

                if data.get('type') == 'agent_message':
                    print(f"✓ Received: {data['content'][:100]}...")
                    break
                elif data.get('type') == 'status' and 'ready' in data.get('content', '').lower():
                    print(f"✓ Status: {data['content']}")

            # Send help message
            print("\nSending: 'help'")
            await websocket.send(json.dumps({
                "type": "message",
                "content": "help"
            }))

            # Wait for response
            print("\nWaiting for response...")
            for i in range(5):
                message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                data = json.loads(message)

                if data.get('type') == 'agent_message':
                    content = data['content']
                    print(f"\n✓ Agent Response:")
                    print(f"  {content}")
                    print("\n✓ Test passed!")
                    return

    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")


async def main():
    """Run tests."""
    print("\n\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "WebSocket Backend Test Suite" + " " * 30 + "║")
    print("╚" + "=" * 78 + "╝")
    print("\n")

    # Check if server is running
    try:
        async with websockets.connect("ws://localhost:8080/chat") as ws:
            await ws.close()
    except:
        print("✗ Server not running on ws://localhost:8080/chat")
        print("\nPlease start the server first:")
        print("  uvicorn web_ui.app:app --reload --port 8080")
        print("\nOr:")
        print("  python -m web_ui.app")
        return

    print("✓ Server is running\n")

    # Run tests
    tests = [
        ("Full WebSocket Flow", test_websocket),
        ("Simple Message Test", test_simple_message),
    ]

    for i, (name, test_func) in enumerate(tests, 1):
        print(f"\n{'#' * 80}")
        print(f"Test {i}/{len(tests)}: {name}")
        print('#' * 80)

        try:
            await test_func()
        except KeyboardInterrupt:
            print("\n\n⚠ Tests interrupted by user")
            return
        except Exception as e:
            print(f"\n✗ Test failed with exception: {str(e)}")
            import traceback
            traceback.print_exc()

        if i < len(tests):
            print("\n" + "-" * 80)
            print("Press Ctrl+C to stop, or wait 3 seconds for next test...")
            try:
                await asyncio.sleep(3)
            except KeyboardInterrupt:
                print("\n⚠ Tests interrupted")
                return

    print("\n\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠ Tests interrupted by user")
