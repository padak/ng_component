"""
Test script for agent.py programmatic API.

This demonstrates how to use the DriverCreatorAgent class in Python code.
"""

import asyncio
from agent import DriverCreatorAgent


async def test_agent_initialization():
    """Test that agent initializes correctly"""
    print("Testing agent initialization...")

    try:
        agent = DriverCreatorAgent()
        print("✓ Agent initialized successfully")
        print(f"  Model: {agent.model}")
        print(f"  Prompt Caching: {agent.enable_prompt_caching}")
        print(f"  mem0 Available: {agent.memory_available}")
        print(f"  E2B Available: {agent.e2b_available}")
        return True
    except Exception as e:
        print(f"✗ Agent initialization failed: {e}")
        return False


async def test_agent_validation():
    """Test driver validation method"""
    print("\nTesting validation method...")

    try:
        agent = DriverCreatorAgent()

        # Test with a non-existent driver (should handle gracefully)
        result = await agent.validate_driver("./non_existent_driver")
        print(f"✓ Validation method works (returned: {result.get('valid')})")
        return True
    except Exception as e:
        print(f"✗ Validation test failed: {e}")
        return False


async def test_session_logs():
    """Test session logging"""
    print("\nTesting session logs...")

    try:
        agent = DriverCreatorAgent()
        logs = agent.get_session_logs()
        print(f"✓ Session logs accessible: {logs}")
        return True
    except Exception as e:
        print(f"✗ Session logs test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("="*80)
    print("Agent.py API Test Suite")
    print("="*80 + "\n")

    tests = [
        test_agent_initialization,
        test_agent_validation,
        test_session_logs
    ]

    results = []
    for test in tests:
        result = await test()
        results.append(result)

    print("\n" + "="*80)
    print(f"Test Results: {sum(results)}/{len(results)} passed")
    print("="*80)

    return all(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
