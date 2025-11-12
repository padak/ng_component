"""
Quick test script for generated drivers

Usage:
    python test_generated_driver.py open_meteo_driver
"""

import sys
import os
from pathlib import Path

def test_driver(driver_name: str):
    """Test a generated driver"""

    # Add generated driver to path
    driver_path = Path(__file__).parent / "generated_drivers" / driver_name
    if not driver_path.exists():
        print(f"❌ Driver not found: {driver_path}")
        sys.exit(1)

    sys.path.insert(0, str(driver_path.parent))

    print(f"🧪 Testing driver: {driver_name}")
    print(f"📁 Path: {driver_path}")
    print("=" * 60)

    try:
        # Import the driver
        module_name = driver_name
        driver_module = __import__(module_name)

        # Get the client class
        client_class = None
        for attr_name in dir(driver_module):
            attr = getattr(driver_module, attr_name)
            if isinstance(attr, type) and attr_name.endswith("Driver"):
                client_class = attr
                break

        if not client_class:
            print("❌ Could not find driver class")
            sys.exit(1)

        print(f"✅ Found driver class: {client_class.__name__}")

        # Try to initialize (without credentials for now)
        print("\n📋 Testing initialization...")

        # For Open-Meteo, we know it doesn't need auth
        # Let's try with dummy values
        try:
            client = client_class(
                api_url="https://api.open-meteo.com/v1",
                api_key="not_needed"  # Open-Meteo doesn't require auth
            )
            print("✅ Client initialized")

            # Test capabilities
            print("\n🔍 Testing get_capabilities()...")
            caps = client.get_capabilities()
            print(f"   Read: {caps.read}")
            print(f"   Write: {caps.write}")
            print(f"   Pagination: {caps.pagination.value}")

            # Test discovery (this will likely fail with TODO implementation)
            print("\n🔍 Testing list_objects()...")
            try:
                objects = client.list_objects()
                print(f"✅ Found {len(objects)} objects: {objects}")
            except Exception as e:
                print(f"⚠️  list_objects() not implemented yet: {e}")

            # Cleanup
            client.close()
            print("\n✅ Driver test completed!")

        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            print("\n💡 This is expected - the generated driver has TODO placeholders.")
            print("   You need to implement the actual API calls in client.py")

    except ImportError as e:
        print(f"❌ Import failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_generated_driver.py <driver_name>")
        print("\nAvailable drivers:")
        drivers_dir = Path(__file__).parent / "generated_drivers"
        if drivers_dir.exists():
            for d in drivers_dir.iterdir():
                if d.is_dir() and not d.name.startswith("."):
                    print(f"  - {d.name}")
        sys.exit(1)

    driver_name = sys.argv[1]
    test_driver(driver_name)
