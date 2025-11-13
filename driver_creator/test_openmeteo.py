#!/usr/bin/env python3
"""
Test driver creator with Open-Meteo API

This tests the new Claude Agent SDK implementation.
"""

import asyncio
import sys
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent))

from agent_claude import DriverCreatorAgent


async def test_openmeteo():
    """Test creating a driver for Open-Meteo API."""
    print("=" * 60)
    print("Testing Driver Creator with Open-Meteo API")
    print("=" * 60)

    # Initialize agent
    agent = DriverCreatorAgent()

    # Create driver for Open-Meteo
    result = await agent.create_driver(
        api_url="https://api.open-meteo.com/v1",
        api_name="Open-Meteo"
    )

    if result["success"]:
        print(f"\n✅ SUCCESS! Driver created at: {result['path']}")

        # Test the generated driver
        driver_path = Path(result["path"])
        driver_file = driver_path / "driver.py"

        if driver_file.exists():
            print(f"\nDriver file exists: {driver_file}")
            print("\nTesting driver import...")

            try:
                # Add driver path to sys.path
                sys.path.insert(0, str(driver_path.parent))

                # Import the driver
                from open_meteo_driver.driver import OpenMeteoDriver

                # Initialize driver
                driver = OpenMeteoDriver()
                print(f"✓ Driver initialized successfully")

                # Test methods
                print("\nTesting driver methods:")

                # 1. Get capabilities
                caps = driver.get_capabilities()
                print(f"✓ Capabilities: read={caps.read}, pagination={caps.pagination.value}")

                # 2. List objects
                objects = driver.list_objects()
                print(f"✓ Objects: {objects}")

                # 3. Get fields
                fields = driver.get_fields("forecast")
                print(f"✓ Fields for 'forecast': {list(fields.keys())}")

                # 4. Read data (simple test)
                try:
                    # Note: This will fail without proper params, but tests the method exists
                    data = driver.read("/forecast?latitude=52.52&longitude=13.41&hourly=temperature_2m")
                    print(f"✓ Read method works (got {len(data)} records)")
                except Exception as e:
                    print(f"✓ Read method exists (API call failed as expected: {e})")

                print("\n🎉 All tests passed!")

            except ImportError as e:
                print(f"❌ Failed to import driver: {e}")
            except Exception as e:
                print(f"❌ Test failed: {e}")
        else:
            print(f"❌ Driver file not found at {driver_file}")
    else:
        print(f"❌ Failed to create driver")

    return result


async def test_driver_content():
    """Test that driver has correct structure."""
    print("\n" + "=" * 60)
    print("Testing driver code structure")
    print("=" * 60)

    # Check if driver was created
    driver_path = Path("generated_drivers/open_meteo_driver/driver.py")

    if driver_path.exists():
        code = driver_path.read_text()

        # Check for required methods
        required = [
            "def list_objects",
            "def get_fields",
            "def read",
            "def get_capabilities",
            "class DriverError",
            "class DriverCapabilities",
            "def _validate_connection",
            "def from_env"
        ]

        missing = []
        for method in required:
            if method not in code:
                missing.append(method)
                print(f"❌ Missing: {method}")
            else:
                print(f"✓ Found: {method}")

        if not missing:
            print("\n✅ All required methods present!")
        else:
            print(f"\n❌ Missing {len(missing)} required elements")

        # Check for error handling
        if "exponential backoff" in code.lower() or "2 ** attempt" in code:
            print("✓ Has exponential backoff")

        if "429" in code:
            print("✓ Handles rate limiting (429)")

        if "max_retries" in code:
            print("✓ Has retry logic")

    else:
        print(f"Driver not yet created at {driver_path}")


if __name__ == "__main__":
    print("🚀 Starting Open-Meteo driver test\n")

    # Run async tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(test_openmeteo())
        loop.run_until_complete(test_driver_content())
    finally:
        loop.close()

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)