"""
Driver Creator Agent - Main Agent Interface

This module provides a simplified interface to the driver creation system using
the Anthropic SDK. It wraps the existing 3-layer self-healing agent architecture
and provides both CLI and programmatic access.

Architecture:
    Layer 3: Supervisor Agent (handles failures and retries)
    Layer 2: Diagnostic Agent (analyzes errors)
    Layer 1: Defensive Wrappers (validation and recovery)

Key Features:
    - Research Agent: Analyzes API documentation
    - Generator Agent: Creates complete driver code
    - Tester Agent: Validates in E2B sandboxes
    - Self-healing: Automatic error detection and fixing

Usage:
    CLI:
        python agent.py --api-url https://api.example.com --name ExampleAPI

    Python:
        agent = DriverCreatorAgent()
        result = await agent.create_driver("https://api.example.com", "ExampleAPI")

    Web:
        See app.py for WebSocket integration
"""

import os
import sys
import argparse
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional, AsyncIterator
from datetime import datetime

from dotenv import load_dotenv
import anthropic

# Import existing agent tools
from agent_tools import (
    generate_driver_supervised,
    generate_driver_with_agents,
    get_memory_client,
    get_agent_model,
    init_session_logging
)

# Load environment variables
load_dotenv()


class DriverCreatorAgent:
    """
    Main driver creator agent interface.

    This class wraps the existing multi-agent system with a clean API for
    driver creation. It uses the Anthropic SDK with the 3-layer self-healing
    architecture implemented in agent_tools.py.

    Attributes:
        claude_client: Anthropic client for Claude API calls
        model: Claude model to use (defaults to Sonnet 4.5)
        memory: mem0 client for learning from past generations
        session_dir: Directory for logging this session
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        enable_prompt_caching: bool = True
    ):
        """
        Initialize the driver creator agent.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use (defaults to claude-sonnet-4-5)
            enable_prompt_caching: Enable prompt caching for cost savings
        """
        # Get API key
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found. Set it in .env or pass as argument.")

        # Initialize Anthropic client
        self.claude_client = anthropic.Anthropic(api_key=self.api_key)

        # Model configuration
        self.model = model or os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
        self.enable_prompt_caching = enable_prompt_caching

        # Initialize mem0 for learning
        try:
            self.memory = get_memory_client()
            self.memory_available = True
        except Exception as e:
            print(f"⚠️  Warning: mem0 not available: {e}")
            self.memory = None
            self.memory_available = False

        # Session tracking
        self.session_dir = None

        # Check for E2B API key
        self.e2b_available = bool(os.getenv("E2B_API_KEY"))
        if not self.e2b_available:
            print("⚠️  Warning: E2B_API_KEY not set - driver testing will be skipped")

    async def create_driver(
        self,
        api_url: str,
        api_name: str,
        output_dir: Optional[str] = None,
        max_retries: int = 7,
        use_supervisor: bool = True
    ) -> Dict[str, Any]:
        """
        Create a complete driver for the given API.

        This is the main method that orchestrates the entire driver creation process:
        1. Initialize session logging
        2. Launch supervisor (if enabled) or direct generation
        3. Research API structure
        4. Generate driver files
        5. Test in E2B sandbox
        6. Fix any issues (automatic retry loop)
        7. Learn from the process (save to mem0)

        Args:
            api_url: Base URL of the API (e.g., "https://api.example.com/v1")
            api_name: Name of the API (e.g., "ExampleAPI")
            output_dir: Optional output directory (defaults to generated_drivers/<name>)
            max_retries: Maximum fix-retry iterations (default: 7)
            use_supervisor: Use 3-layer self-healing architecture (default: True)

        Returns:
            Dict with results:
            {
                "success": bool,
                "driver_name": str,
                "output_path": str,
                "files_created": List[str],
                "test_results": Dict,
                "iterations": int,
                "execution_time": float,
                "supervisor_attempts": int (if use_supervisor=True),
                "diagnostics_run": int (if use_supervisor=True)
            }

        Raises:
            ValueError: If api_url or api_name is invalid
            RuntimeError: If generation fails after all retries
        """
        # Validate inputs
        if not api_url or not api_url.startswith("http"):
            raise ValueError(f"Invalid api_url: {api_url}")
        if not api_name:
            raise ValueError("api_name cannot be empty")

        # Initialize session logging
        self.session_dir = init_session_logging()

        print("\n" + "="*80)
        print(f"🚀 Driver Creator Agent")
        print("="*80)
        print(f"API: {api_name}")
        print(f"URL: {api_url}")
        print(f"Model: {self.model}")
        print(f"Prompt Caching: {'Enabled' if self.enable_prompt_caching else 'Disabled'}")
        print(f"mem0 Learning: {'Enabled' if self.memory_available else 'Disabled'}")
        print(f"E2B Testing: {'Enabled' if self.e2b_available else 'Disabled'}")
        print(f"Self-Healing: {'Enabled (3-layer)' if use_supervisor else 'Disabled'}")
        print(f"Session: {self.session_dir}")
        print("="*80 + "\n")

        # Run generation (sync in async wrapper)
        loop = asyncio.get_event_loop()

        if use_supervisor:
            # Use 3-layer self-healing architecture
            result = await loop.run_in_executor(
                None,
                generate_driver_supervised,
                api_name,
                api_url,
                output_dir,
                3,  # max_supervisor_attempts
                max_retries
            )
        else:
            # Direct generation without supervisor
            result = await loop.run_in_executor(
                None,
                generate_driver_with_agents,
                api_name,
                api_url,
                output_dir,
                max_retries
            )

        return result

    def create_driver_sync(
        self,
        api_url: str,
        api_name: str,
        output_dir: Optional[str] = None,
        max_retries: int = 7,
        use_supervisor: bool = True
    ) -> Dict[str, Any]:
        """
        Synchronous version of create_driver().

        This is a convenience wrapper for non-async code.
        See create_driver() for full documentation.
        """
        return asyncio.run(
            self.create_driver(
                api_url=api_url,
                api_name=api_name,
                output_dir=output_dir,
                max_retries=max_retries,
                use_supervisor=use_supervisor
            )
        )

    async def validate_driver(self, driver_path: str) -> Dict[str, Any]:
        """
        Validate a generated driver against Driver Design v2.0 specification.

        Args:
            driver_path: Path to the driver directory

        Returns:
            Dict with validation results:
            {
                "valid": bool,
                "checks_passed": List[str],
                "checks_failed": List[str],
                "warnings": List[str],
                "todos_count": int
            }
        """
        from tools import validate_driver

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, validate_driver, driver_path)
        return result

    async def test_driver(
        self,
        driver_path: str,
        driver_name: str,
        test_api_url: Optional[str] = None,
        use_mock_api: bool = False
    ) -> Dict[str, Any]:
        """
        Test a generated driver in an E2B sandbox.

        Args:
            driver_path: Path to the driver directory
            driver_name: Name of the driver package
            test_api_url: Optional API URL for testing (defaults to localhost:8000)
            use_mock_api: Whether to start a mock API in the sandbox

        Returns:
            Dict with test results:
            {
                "success": bool,
                "tests_passed": int,
                "tests_failed": int,
                "errors": List[Dict],
                "output": str
            }
        """
        if not self.e2b_available:
            return {
                "success": False,
                "error": "E2B_API_KEY not set - testing unavailable"
            }

        from tools import test_driver_in_e2b

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            test_driver_in_e2b,
            driver_path,
            driver_name,
            test_api_url,
            use_mock_api
        )
        return result

    def get_session_logs(self) -> str:
        """
        Get logs from the current session.

        Returns:
            String with session log content
        """
        if not self.session_dir:
            return "No session initialized"

        logs = []
        for log_file in sorted(Path(self.session_dir).glob("*.txt")):
            with open(log_file, 'r') as f:
                logs.append(f"=== {log_file.name} ===\n{f.read()}")

        return "\n\n".join(logs)


# CLI Interface
def main():
    """
    Command-line interface for the driver creator agent.

    Usage:
        python agent.py --api-url https://api.example.com --name ExampleAPI
        python agent.py --api-url https://api.example.com --name ExampleAPI --output ./drivers/example
        python agent.py --api-url https://api.example.com --name ExampleAPI --no-supervisor
    """
    parser = argparse.ArgumentParser(
        description="Driver Creator Agent - Create production-ready API drivers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create driver for Open-Meteo API
  python agent.py --api-url https://api.open-meteo.com/v1 --name OpenMeteo

  # Create driver with custom output directory
  python agent.py --api-url https://api.example.com --name Example --output ./my_drivers/example

  # Create driver without self-healing (faster but less reliable)
  python agent.py --api-url https://api.example.com --name Example --no-supervisor

Environment Variables:
  ANTHROPIC_API_KEY  - Required for Claude API access
  E2B_API_KEY        - Optional for driver testing in sandbox
  CLAUDE_MODEL       - Optional model override (default: claude-sonnet-4-5)
        """
    )

    parser.add_argument(
        "--api-url",
        required=True,
        help="Base URL of the API (e.g., https://api.example.com/v1)"
    )
    parser.add_argument(
        "--name",
        required=True,
        help="Name of the API (e.g., ExampleAPI)"
    )
    parser.add_argument(
        "--output",
        help="Output directory for generated driver (optional)"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=7,
        help="Maximum fix-retry iterations (default: 7)"
    )
    parser.add_argument(
        "--no-supervisor",
        action="store_true",
        help="Disable 3-layer self-healing (faster but less reliable)"
    )
    parser.add_argument(
        "--model",
        help="Claude model to use (default: claude-sonnet-4-5)"
    )

    args = parser.parse_args()

    try:
        # Initialize agent
        agent = DriverCreatorAgent(model=args.model)

        # Create driver
        result = agent.create_driver_sync(
            api_url=args.api_url,
            api_name=args.name,
            output_dir=args.output,
            max_retries=args.max_retries,
            use_supervisor=not args.no_supervisor
        )

        # Print results
        print("\n" + "="*80)
        if result.get("success"):
            print("✅ Driver creation successful!")
            print("="*80)
            print(f"Driver: {result.get('driver_name')}")
            print(f"Path: {result.get('output_path')}")
            print(f"Files: {len(result.get('files_created', []))}")
            print(f"Iterations: {result.get('iterations', 0)}")
            print(f"Time: {result.get('execution_time', 0):.1f}s")

            if args.no_supervisor:
                print(f"Tests: {result.get('test_results', {}).get('tests_passed', 0)} passed")
            else:
                print(f"Supervisor attempts: {result.get('supervisor_attempts', 0)}")
                print(f"Diagnostics run: {result.get('diagnostics_run', 0)}")

            print("\nFiles created:")
            for file in result.get('files_created', []):
                print(f"  ✓ {file}")
        else:
            print("❌ Driver creation failed")
            print("="*80)
            print(f"Error: {result.get('error', 'Unknown error')}")
            print(f"Message: {result.get('message', 'No details')}")

            if result.get('supervisor_attempts'):
                print(f"\nSupervisor attempts: {result.get('supervisor_attempts')}")
                print(f"Diagnostics run: {result.get('diagnostics_run', 0)}")

        print("="*80)

        # Exit with appropriate code
        sys.exit(0 if result.get("success") else 1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
