"""
Example: How to integrate agent.py with web applications.

This shows different ways to use the DriverCreatorAgent:
1. Simple synchronous usage
2. Async streaming usage
3. Integration with FastAPI/WebSocket
"""

import asyncio
from agent import DriverCreatorAgent


# Example 1: Simple synchronous usage
def example_simple():
    """
    Simplest usage - synchronous API creation
    """
    print("Example 1: Simple Synchronous Usage")
    print("="*80)

    # Initialize agent
    agent = DriverCreatorAgent()

    # Create driver (blocks until complete)
    result = agent.create_driver_sync(
        api_url="https://api.open-meteo.com/v1",
        api_name="OpenMeteo"
    )

    if result["success"]:
        print(f"✓ Driver created: {result['output_path']}")
        print(f"  Files: {len(result['files_created'])}")
        print(f"  Time: {result['execution_time']:.1f}s")
    else:
        print(f"✗ Failed: {result['error']}")


# Example 2: Async usage with progress monitoring
async def example_async():
    """
    Async usage - can be integrated with event loops
    """
    print("\nExample 2: Async Usage")
    print("="*80)

    # Initialize agent
    agent = DriverCreatorAgent()

    # Create driver asynchronously
    result = await agent.create_driver(
        api_url="https://api.open-meteo.com/v1",
        api_name="OpenMeteo",
        max_retries=3
    )

    if result["success"]:
        print(f"✓ Driver created: {result['output_path']}")

        # Can also validate
        validation = await agent.validate_driver(result['output_path'])
        print(f"  Validation: {validation['checks_passed']}/{validation['checks_passed'] + len(validation['checks_failed'])} checks passed")
    else:
        print(f"✗ Failed: {result['error']}")


# Example 3: Integration with FastAPI WebSocket (pseudocode)
async def example_websocket_integration():
    """
    How to integrate with WebSocket for streaming updates.

    This is pseudocode showing the pattern used in app.py.
    """
    print("\nExample 3: WebSocket Integration Pattern")
    print("="*80)

    # Pseudocode showing the pattern:
    print("""
    from fastapi import WebSocket
    from agent import DriverCreatorAgent

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()

        # Initialize agent
        agent = DriverCreatorAgent()

        # Receive user request
        data = await websocket.receive_json()
        api_url = data["api_url"]
        api_name = data["api_name"]

        # Send status updates
        await websocket.send_json({
            "type": "status",
            "message": "Creating driver..."
        })

        # Create driver
        result = await agent.create_driver(api_url, api_name)

        # Send result
        await websocket.send_json({
            "type": "result",
            "success": result["success"],
            "data": result
        })
    """)


# Example 4: Batch processing multiple APIs
async def example_batch():
    """
    Create drivers for multiple APIs in sequence
    """
    print("\nExample 4: Batch Processing")
    print("="*80)

    apis = [
        ("https://api.open-meteo.com/v1", "OpenMeteo"),
        ("https://jsonplaceholder.typicode.com", "JSONPlaceholder"),
    ]

    agent = DriverCreatorAgent()

    results = []
    for api_url, api_name in apis:
        print(f"\nCreating driver for {api_name}...")
        result = await agent.create_driver(api_url, api_name, max_retries=2)
        results.append((api_name, result["success"]))

    print("\n" + "="*80)
    print("Batch Results:")
    for api_name, success in results:
        status = "✓" if success else "✗"
        print(f"  {status} {api_name}")


# Example 5: Custom configuration
async def example_custom_config():
    """
    Using custom configuration
    """
    print("\nExample 5: Custom Configuration")
    print("="*80)

    # Initialize with custom settings
    agent = DriverCreatorAgent(
        model="claude-haiku-4-5",  # Use cheaper/faster model
        enable_prompt_caching=True
    )

    # Create driver with custom output directory
    result = await agent.create_driver(
        api_url="https://api.open-meteo.com/v1",
        api_name="OpenMeteo",
        output_dir="./my_custom_drivers/open_meteo",
        max_retries=2,
        use_supervisor=False  # Faster but less reliable
    )

    print(f"Result: {result['success']}")


async def main():
    """
    Run all examples (commented out to avoid long execution)
    """
    print("="*80)
    print("Agent.py Usage Examples")
    print("="*80)

    # Uncomment to run examples:
    # example_simple()
    # await example_async()
    await example_websocket_integration()
    # await example_batch()
    # await example_custom_config()


if __name__ == "__main__":
    asyncio.run(main())
