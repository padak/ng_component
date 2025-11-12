"""
Test mem0 integration with Claude for driver generation learning.

This script tests:
1. Memory initialization with Claude LLM
2. Adding memories (learnings from driver generation)
3. Searching memories (retrieving past lessons)
"""

import os
from dotenv import load_dotenv
from mem0 import Memory

# Load environment variables
load_dotenv()

def test_mem0_basic():
    """Test basic mem0 operations"""

    print("🧪 Testing mem0 Integration")
    print("=" * 60)

    # Check required API keys
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not anthropic_key:
        print("❌ ANTHROPIC_API_KEY not set!")
        return False

    if not openai_key:
        print("❌ OPENAI_API_KEY not set!")
        return False

    print("✅ API keys found")

    # For now, use default mem0 config (OpenAI for both LLM and embeddings)
    # TODO: Fix Claude integration - mem0 sets both temperature and top_p which Claude doesn't allow
    print("\n📝 Initializing Memory with default config (OpenAI)...")
    print("   Note: Using OpenAI for LLM until Claude temperature/top_p conflict is resolved")

    try:
        m = Memory()  # Use default config
        print("✅ Memory initialized!")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return False

    # Test 1: Add a memory about Open-Meteo driver issue
    print("\n📌 Test 1: Adding memory about Open-Meteo driver fix...")

    messages = [
        {
            "role": "user",
            "content": "I generated a driver for Open-Meteo API but the E2B test failed with 'Connection refused to localhost:8000'"
        },
        {
            "role": "assistant",
            "content": "The issue was that the test was using localhost:8000 instead of the real API URL. I fixed it by extracting base_url from research_data and passing it to test_driver_in_e2b()."
        },
        {
            "role": "user",
            "content": "Good! What should I remember for next time?"
        },
        {
            "role": "assistant",
            "content": "Remember: For public APIs (not localhost), always use research_data['base_url'] as test_api_url. Also, public APIs don't need fake API keys in test_credentials."
        }
    ]

    try:
        result = m.add(messages, user_id="driver_creator_agent")
        print(f"✅ Memory added! Results: {result}")
    except Exception as e:
        print(f"❌ Failed to add memory: {e}")
        return False

    # Test 2: Search for related memories
    print("\n🔍 Test 2: Searching for public API testing patterns...")

    try:
        results = m.search(
            "How should I test a public API driver?",
            user_id="driver_creator_agent"
        )
        print(f"✅ Found {len(results)} relevant memories:")
        for i, result in enumerate(results, 1):
            # Results can be string or dict depending on version
            if isinstance(result, dict):
                memory_text = result.get('memory', result.get('text', 'N/A'))
                score = result.get('score', 'N/A')
            else:
                memory_text = str(result)
                score = 'N/A'
            print(f"\n  {i}. {memory_text}")
            print(f"     Score: {score}")
    except Exception as e:
        print(f"❌ Failed to search: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 3: Get all memories
    print("\n📚 Test 3: Getting all memories...")

    try:
        all_memories = m.get_all(user_id="driver_creator_agent")
        print(f"✅ Total memories stored: {len(all_memories)}")
        for i, memory_item in enumerate(all_memories, 1):
            # Handle both dict and string formats
            if isinstance(memory_item, dict):
                memory_text = memory_item.get('memory', memory_item.get('text', str(memory_item)))
            else:
                memory_text = str(memory_item)
            print(f"\n  {i}. {memory_text}")
    except Exception as e:
        print(f"❌ Failed to get all memories: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("\n💡 Memory is stored at:")
    print(f"   - Vector DB: /tmp/qdrant")
    print(f"   - History: ~/.mem0/history.db")

    return True


if __name__ == "__main__":
    success = test_mem0_basic()
    exit(0 if success else 1)
