"""
Salesforce Integration Designer Agent

An interactive CLI agent that helps users design and execute Salesforce integration
scripts using the Claude Agent SDK and E2B sandboxes.

This agent:
- Asks clarifying questions about data needs
- Uses discovery to understand available Salesforce objects
- Suggests and generates SOQL queries
- Creates executable Python scripts
- Executes scripts in E2B sandboxes via AgentExecutor
- Shows results and iterates based on user feedback

Usage:
    python salesforce_designer_agent.py

Requirements:
    - ANTHROPIC_API_KEY in environment
    - E2B_API_KEY in environment
    - claude-agent-sdk package installed
"""

import os
import sys
import json
import asyncio
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import required libraries
try:
    from claude_agent_sdk.client import ClaudeSDKClient
    from claude_agent_sdk import ClaudeAgentOptions
except ImportError:
    print("ERROR: claude-agent-sdk not installed. Run: pip install claude-agent-sdk")
    sys.exit(1)

try:
    from agent_executor import AgentExecutor
except ImportError:
    print("ERROR: Could not import AgentExecutor. Make sure you're in the right directory.")
    sys.exit(1)


# System prompt for the agent
SYSTEM_PROMPT = """You are an expert Salesforce integration designer assistant. Your role is to help users
design and create Python scripts that interact with Salesforce data using the SalesforceClient driver.

## Your Environment

You are working in an Agent-Based Integration System where:
- Scripts execute in isolated E2B cloud sandboxes (virtual machines)
- A mock Salesforce API runs at localhost:8000 inside the sandbox
- The SalesforceClient driver provides discovery and query capabilities
- All code you generate will be executed in E2B via the AgentExecutor class

## Your Capabilities

You have access to the following tools:
- **Read**: Read files from the codebase (schemas, examples, documentation)
- **Bash**: Execute shell commands (check files, list directories)
- **Write**: Save generated scripts to files
- **Grep**: Search for patterns in code
- **Glob**: Find files by pattern

## The SalesforceClient Driver

The driver is located at `salesforce_driver/` and provides:

```python
from salesforce_driver import SalesforceClient

# Initialize client (inside E2B sandbox)
client = SalesforceClient(
    api_url='http://localhost:8000',  # Always localhost in sandbox
    api_key='your_api_key'
)

# Discovery methods - ALWAYS use these first!
objects = client.list_objects()  # Returns: ["Lead", "Campaign", "CampaignMember"]
schema = client.get_fields("Lead")  # Returns field definitions with types
count = client.get_object_count("Lead")  # Returns total record count

# Build query dynamically from discovered schema
fields = list(schema['fields'].keys())  # e.g., ["Id", "FirstName", "LastName", "Email", ...]
query = f"SELECT {', '.join(fields)} FROM Lead LIMIT 10"
results = client.query(query)  # Returns list of dicts
```

## Discovery-First Approach

ALWAYS start by discovering what's available:
1. Use `list_objects()` to see available Salesforce objects
2. Use `get_fields(object_name)` to understand field schemas
3. Use discovered schemas to build accurate SOQL queries
4. Generate scripts that are self-documenting and robust

## SOQL Query Guidelines

The mock API supports basic SOQL:
- SELECT with field lists
- WHERE with AND conditions
- Date comparisons (must use quotes: `'2024-01-01'`)
- ORDER BY
- LIMIT
- LIKE for pattern matching

IMPORTANT: NEVER hardcode field names! Always discover them first using `get_fields()`.

Example of discovery-first approach:
```python
# Step 1: Discover available fields
schema = client.get_fields("Lead")
available_fields = list(schema['fields'].keys())

# Step 2: Select fields based on discovery
# (You can filter to just the ones you need)
desired_fields = [f for f in available_fields if f in ['Id', 'Email', 'Company', 'Status', 'CreatedDate']]
field_list = ', '.join(desired_fields)

# Step 3: Build query dynamically
query = f"SELECT {field_list} FROM Lead WHERE CreatedDate >= '2024-01-01' AND Status = 'New' ORDER BY CreatedDate DESC LIMIT 100"
results = client.query(query)
```

## Script Generation Pattern

When generating scripts, ALWAYS use discovery-first pattern:

```python
import sys
sys.path.insert(0, '/home/user')
from salesforce_driver import SalesforceClient
import json

# Initialize client (API at localhost:8000 inside sandbox)
client = SalesforceClient(
    api_url='http://localhost:8000',
    api_key='your_api_key_here'
)

try:
    # STEP 1: Discover schema (ALWAYS do this first!)
    print("Discovering Lead fields...")
    schema = client.get_fields("Lead")
    available_fields = list(schema['fields'].keys())
    print(f"Available fields: {', '.join(available_fields)}")

    # STEP 2: Select fields you need from discovered schema
    # (For example, if user wants "contact info", pick email-related fields)
    desired = ['Id', 'Email', 'Company', 'Status', 'CreatedDate']
    fields = [f for f in available_fields if f in desired]

    # STEP 3: Build query dynamically
    query = f"SELECT {', '.join(fields)} FROM Lead LIMIT 10"
    print(f"Executing query: {query}")

    # STEP 4: Execute
    results = client.query(query)

    # STEP 5: Process and display
    print(f"Found {len(results)} records")
    print(json.dumps(results, indent=2))

except Exception as e:
    error_result = {'error': str(e)}
    print(json.dumps(error_result, indent=2))
```

## How to Help Users

1. **Understand Intent**: Ask clarifying questions about:
   - What data they need (which objects?)
   - What filters to apply (date ranges, statuses, etc.)
   - What fields they want returned
   - How many records they expect

2. **Discover Schema**: Use Read tool to check:
   - Available objects (suggest running discovery)
   - Field definitions for the objects they need
   - Example scripts in salesforce_driver/examples/

3. **Design Query**: Based on their needs:
   - Suggest appropriate SOQL query
   - Explain what the query does
   - Show which fields will be returned

4. **Generate Script**: Create complete Python script:
   - Include error handling
   - Add helpful comments
   - Return JSON output for easy parsing
   - Show summary statistics

5. **Execute & Iterate**:
   - The user will execute your script via AgentExecutor
   - Review results together
   - Refine based on feedback
   - Save final version if user approves

## Helpful Context

- Test database has 180 sample records (Leads, Campaigns, CampaignMembers)
- Scripts run in /home/user/ directory inside E2B sandbox
- All components (API, DB, driver) are on the same VM (localhost)
- Use json.dumps() for structured output that's easy to parse

## Example Interaction Flow

User: "I need to get leads created in the last month"

You: "I can help you with that! Let me ask a few questions:
1. What information do you need from each lead? (e.g., contact info, company details, status)
2. Any status filters (New, Qualified, Working, etc.)?
3. Should results be sorted in any particular way?

Since I don't know the exact field names in your Salesforce instance, I'll generate a script that uses discovery to find available fields first, then builds the query dynamically."

You: "Here's a script that will:
1. Discover what fields are available on the Lead object
2. Select relevant fields based on what you need
3. Query for leads from the last 30 days
4. Return results as JSON

This approach ensures the script works regardless of your Salesforce schema.
Would you like me to generate the complete Python script?"

User: "Yes, generate it"

You: "Here's the complete script..."

[Generate script using Write tool or show inline]

You: "This script will:
1. Connect to the Salesforce API
2. Query for leads created since October 10th
3. Display count and sample results
4. Return all data as JSON

Would you like me to save this to a file, or are you ready to execute it with AgentExecutor?"

## Important Notes

- Be conversational and helpful
- Ask questions when requirements are unclear
- Explain your reasoning
- Show examples from the codebase when relevant
- Suggest improvements based on best practices
- Always consider error cases
- Make scripts self-documenting with good variable names and comments

Remember: You're a collaborative partner in designing integration scripts, not just a code generator!
"""


def create_agent() -> ClaudeSDKClient:
    """
    Create and configure the Salesforce Designer Agent.

    Returns:
        Configured ClaudeSDKClient instance
    """
    options = ClaudeAgentOptions(
        model="claude-haiku-4-5",  # Fast and efficient Haiku model
        system_prompt=SYSTEM_PROMPT,
        allowed_tools=["Read", "Bash", "Write", "Grep", "Glob"],
        cwd=os.getcwd()
    )

    client = ClaudeSDKClient(options=options)
    return client


def print_banner():
    """Print welcome banner."""
    print("\n" + "=" * 80)
    print("  SALESFORCE INTEGRATION DESIGNER AGENT")
    print("  Powered by Claude Agent SDK + E2B Sandboxes")
    print("=" * 80)
    print("\nI'm your Salesforce integration assistant! I can help you:")
    print("  - Discover available Salesforce objects and fields")
    print("  - Design SOQL queries for your data needs")
    print("  - Generate executable Python scripts")
    print("  - Execute scripts in E2B sandboxes and review results")
    print("\nType 'help' for commands, 'quit' to exit")
    print("-" * 80)


def print_help():
    """Print help information."""
    print("\n" + "=" * 80)
    print("  AVAILABLE COMMANDS")
    print("=" * 80)
    print("\nConversation:")
    print("  - Just type your request naturally")
    print("  - Ask questions about Salesforce objects and fields")
    print("  - Request script generation")
    print("\nSpecial Commands:")
    print("  help      - Show this help message")
    print("  clear     - Clear conversation history")
    print("  execute   - Execute the last generated script in E2B")
    print("  save      - Save the last generated script to a file")
    print("  quit/exit - Exit the agent")
    print("\nExamples:")
    print("  'What Salesforce objects are available?'")
    print("  'Show me the fields for the Lead object'")
    print("  'Generate a script to get leads from last 30 days'")
    print("  'Get all campaigns with their associated leads'")
    print("-" * 80)


def execute_with_agent_executor(script: str, description: str = "Generated script") -> dict:
    """
    Execute a generated script using AgentExecutor in E2B sandbox.

    Args:
        script: Python script to execute
        description: Human-readable description

    Returns:
        Execution result dictionary
    """
    print("\n" + "=" * 80)
    print(f"  EXECUTING: {description}")
    print("=" * 80)
    print("\nCreating E2B sandbox and starting Mock API...")

    try:
        # Create executor
        executor = AgentExecutor()

        # Create sandbox (auto-setup uploads files and starts API)
        executor.create_sandbox()

        print(f"Sandbox ready: {executor.sandbox.sandbox_id}")
        print("\nExecuting script...")

        # Execute the script
        result = executor.execute_script(script, description)

        # Display results
        print("\n" + "=" * 80)
        if result['success']:
            print("  EXECUTION SUCCESS")
            print("=" * 80)

            # Show output
            if result['output']:
                print("\nOutput:")
                print("-" * 80)
                print(result['output'])

            # Show parsed data if available
            if result['data']:
                print("\n" + "=" * 80)
                print("  PARSED DATA")
                print("=" * 80)

                # Count records
                if isinstance(result['data'], dict):
                    if 'count' in result['data']:
                        print(f"\nTotal records: {result['data']['count']}")

                    # Show leads if available
                    if 'leads' in result['data']:
                        leads = result['data']['leads']
                        print(f"\nSample leads ({min(3, len(leads))} of {len(leads)}):")
                        for i, lead in enumerate(leads[:3], 1):
                            # Build name from available fields
                            name_parts = []
                            if 'FirstName' in lead:
                                name_parts.append(lead['FirstName'])
                            if 'LastName' in lead:
                                name_parts.append(lead['LastName'])
                            name = ' '.join(name_parts) if name_parts else lead.get('Id', 'N/A')

                            print(f"\n  {i}. {name}")
                            print(f"     Company: {lead.get('Company', 'N/A')}")
                            print(f"     Email: {lead.get('Email', 'N/A')}")
                            print(f"     Status: {lead.get('Status', 'N/A')}")

                    # Show campaign if available
                    if 'campaign' in result['data']:
                        campaign = result['data']['campaign']
                        print(f"\nCampaign: {campaign.get('Name', 'N/A')}")
                        print(f"Status: {campaign.get('Status', 'N/A')}")
                        print(f"Members: {result['data'].get('member_count', 0)}")

                elif isinstance(result['data'], list):
                    print(f"\nReturned {len(result['data'])} records")
                    if result['data']:
                        print(f"\nSample records ({min(3, len(result['data']))}):")
                        for i, record in enumerate(result['data'][:3], 1):
                            print(f"  {i}. {record}")
        else:
            print("  EXECUTION FAILED")
            print("=" * 80)
            print(f"\nError: {result['error']}")

        # Clean up
        print("\n" + "=" * 80)
        print("Closing sandbox...")
        executor.close()
        print("Done!")
        print("=" * 80)

        return result

    except Exception as e:
        print("\n" + "=" * 80)
        print(f"  EXECUTION ERROR: {str(e)}")
        print("=" * 80)
        import traceback
        traceback.print_exc()

        return {
            'success': False,
            'error': str(e),
            'output': '',
            'data': None
        }


def save_script(script: str, filename: Optional[str] = None) -> str:
    """
    Save a script to a file.

    Args:
        script: Script content
        filename: Optional filename (will prompt if not provided)

    Returns:
        Path to saved file
    """
    if not filename:
        filename = input("\nEnter filename (e.g., my_script.py): ").strip()

    if not filename.endswith('.py'):
        filename += '.py'

    # Save to current directory
    filepath = os.path.join(os.getcwd(), filename)

    with open(filepath, 'w') as f:
        f.write(script)

    print(f"\nScript saved to: {filepath}")
    return filepath


def extract_python_code(text: str) -> Optional[str]:
    """
    Extract Python code from markdown code blocks.

    Args:
        text: Text potentially containing code blocks

    Returns:
        Extracted Python code or None
    """
    # Look for ```python or ``` code blocks
    if '```python' in text:
        # Extract content between ```python and ```
        start = text.find('```python') + len('```python')
        end = text.find('```', start)
        if end != -1:
            return text[start:end].strip()
    elif '```' in text:
        # Extract content between ``` and ```
        start = text.find('```') + 3
        end = text.find('```', start)
        if end != -1:
            return text[start:end].strip()

    return None


async def interactive_session():
    """
    Run the interactive agent session (async).
    """
    print_banner()

    # Create agent
    print("\nInitializing agent...")
    client = create_agent()

    # Track last generated script
    last_script = None
    last_description = "Generated script"

    try:
        # Connect to Claude
        await client.connect()
        print("Agent ready! How can I help you design a Salesforce integration?\n")

        # Main conversation loop
        while True:
            try:
                # Get user input
                user_input = input("\nYou: ").strip()

                if not user_input:
                    continue

                # Handle special commands
                if user_input.lower() in ['quit', 'exit']:
                    print("\nGoodbye! Happy integrating!")
                    break

                elif user_input.lower() == 'help':
                    print_help()
                    continue

                elif user_input.lower() == 'clear':
                    # Disconnect and reconnect to clear history
                    print("\nClearing conversation history...")
                    await client.disconnect()
                    await client.connect()
                    last_script = None
                    print("History cleared!")
                    continue

                elif user_input.lower() == 'execute':
                    if last_script:
                        result = execute_with_agent_executor(last_script, last_description)
                        print(f"\nExecution {'succeeded' if result['success'] else 'failed'}.")
                    else:
                        print("\nNo script to execute. Generate a script first!")
                    continue

                elif user_input.lower() == 'save':
                    if last_script:
                        save_script(last_script)
                    else:
                        print("\nNo script to save. Generate a script first!")
                    continue

                # Send message to agent
                await client.query(user_input)

                # Stream response
                print("\nAgent: ", end='', flush=True)

                response_text = ""
                async for message in client.receive_messages():
                    # Handle different message types
                    message_type = type(message).__name__

                    if message_type == 'SystemMessage':
                        # Skip system messages
                        continue

                    elif message_type == 'AssistantMessage':
                        # Extract text from content blocks
                        if hasattr(message, 'content') and isinstance(message.content, list):
                            for block in message.content:
                                block_type = type(block).__name__

                                if block_type == 'TextBlock':
                                    # Print text content
                                    text = block.text
                                    print(text, end='', flush=True)
                                    response_text += text

                                elif block_type == 'ToolUseBlock':
                                    # Show tool usage
                                    tool_name = block.name if hasattr(block, 'name') else 'unknown'
                                    print(f"\n[Using tool: {tool_name}]", flush=True)

                    elif message_type == 'ResultMessage':
                        # End of response
                        break

                print()  # New line after streaming

                # Check if response contains Python code
                extracted_code = extract_python_code(response_text)
                if extracted_code:
                    last_script = extracted_code
                    last_description = "Generated script"

                    # Offer to execute
                    print("\n" + "-" * 80)
                    print("I've generated a script for you!")
                    print("Type 'execute' to run it in E2B, or 'save' to save it to a file.")
                    print("You can also continue the conversation to refine it.")
                    print("-" * 80)

            except KeyboardInterrupt:
                print("\n\nGoodbye! (interrupted)")
                break

            except Exception as e:
                print(f"\n\nError: {str(e)}")
                import traceback
                traceback.print_exc()

    finally:
        # Always disconnect when done
        try:
            await client.disconnect()
        except Exception:
            pass  # Ignore disconnect errors


def main():
    """
    Main entry point.
    """
    # Check for required environment variables
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    e2b_key = os.getenv('E2B_API_KEY')

    if not anthropic_key:
        print("\nERROR: ANTHROPIC_API_KEY not found in environment")
        print("Please set it in your .env file or environment:")
        print("  export ANTHROPIC_API_KEY=your_key_here")
        return 1

    if not e2b_key:
        print("\nWARNING: E2B_API_KEY not found in environment")
        print("You won't be able to execute scripts in E2B sandboxes.")
        print("To fix, set it in your .env file:")
        print("  export E2B_API_KEY=your_key_here")

        response = input("\nContinue anyway? (y/n): ").strip().lower()
        if response != 'y':
            return 1

    # Run interactive session (async)
    try:
        asyncio.run(interactive_session())
        return 0

    except Exception as e:
        print(f"\n\nFatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
