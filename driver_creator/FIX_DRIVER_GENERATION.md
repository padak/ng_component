# Fix Driver Generation - Implementation Plan

**Context:** Driver generation fails repeatedly with same bug (`list_objects` returns `List[Dict]` instead of `List[str]`). Fix-retry loop doesn't work because agents lack visibility and specificity.

**Goal:** Make agent successfully generate working drivers on first try (or fix bugs automatically within 7 iterations).

**Current Status:**
- 3 iterations max (not enough)
- No logging (blind debugging)
- Generic prompts (not specific enough)
- Tester doesn't see current code (can't provide accurate fixes)

---

## Phase 1: Comprehensive Logging (Priority: HIGH)

**Problem:** No visibility into what agents are doing. Can't debug why fixes fail.

**Solution:** Log every agent call (prompt + response) to timestamped directories.

### Implementation:

**File:** `/Users/padak/github/ng_component/driver_creator/agent_tools.py`

**Location:** Add after imports (line ~15)

```python
import json
from datetime import datetime
from pathlib import Path

# Session logging directory
CURRENT_SESSION_DIR = None

def init_session_logging():
    """Initialize logging directory for this driver generation session"""
    global CURRENT_SESSION_DIR
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    CURRENT_SESSION_DIR = Path("logs") / f"session_{timestamp}"
    CURRENT_SESSION_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n📝 Session logs: {CURRENT_SESSION_DIR}\n")
    return CURRENT_SESSION_DIR

def log_agent_interaction(agent_type: str, phase: str, content: dict):
    """
    Log agent prompt/response for debugging.

    Args:
        agent_type: 'research', 'generator', 'tester', 'fixer', 'learning'
        phase: 'input' or 'output'
        content: {'prompt': str, 'response': str, 'metadata': dict}
    """
    if not CURRENT_SESSION_DIR:
        return

    log_file = CURRENT_SESSION_DIR / f"{agent_type}_{phase}.jsonl"

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "agent_type": agent_type,
        "phase": phase,
        **content
    }

    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    # Also write human-readable version
    if phase == 'input' and 'prompt' in content:
        readable_file = CURRENT_SESSION_DIR / f"{agent_type}_prompt.txt"
        with open(readable_file, "a") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Timestamp: {log_entry['timestamp']}\n")
            f.write(f"{'='*80}\n")
            f.write(content['prompt'])
            f.write(f"\n\n")
```

**Usage:** Add logging to each agent call:

1. **Research Agent** (line ~173):
```python
# BEFORE calling claude.messages.create:
log_agent_interaction('research', 'input', {
    'prompt': research_prompt,
    'model': get_agent_model('research'),
    'api_name': api_name,
    'api_url': api_url
})

# AFTER getting response:
log_agent_interaction('research', 'output', {
    'response': research_text,
    'research_data': research_data,
    'endpoints_found': len(research_data.get('endpoints', []))
})
```

2. **Generator Agent** (line ~363):
```python
# BEFORE:
log_agent_interaction('generator', 'input', {
    'prompt': file_prompt,
    'file_path': file_path,
    'model': get_agent_model('generator')
})

# AFTER:
log_agent_interaction('generator', 'output', {
    'file_path': file_path,
    'code_length': len(file_content),
    'response': file_content[:500]  # First 500 chars
})
```

3. **Tester Agent** (line ~543):
```python
# BEFORE:
log_agent_interaction('tester', 'input', {
    'prompt': fix_prompt,
    'errors': errors,
    'iteration': iteration
})

# AFTER:
log_agent_interaction('tester', 'output', {
    'analysis': fix_data.get('analysis'),
    'edits_suggested': len(fix_data.get('edits', [])),
    'response': fix_text
})
```

4. **Code Locator** (line ~658):
```python
# BEFORE:
log_agent_interaction('fixer', 'input', {
    'prompt': locate_prompt,
    'issue': issue,
    'file': file_to_fix
})

# AFTER:
log_agent_interaction('fixer', 'output', {
    'old_string_length': len(old_string),
    'new_string_length': len(new_string),
    'found': old_string in modified_content
})
```

**Call init at start of generation** (line ~115):
```python
def generate_driver_with_agents(...):
    import time
    import json
    import anthropic

    start_time = time.time()

    # Initialize session logging
    session_dir = init_session_logging()
```

---

## Phase 2: Fix Generator Prompt - Add Explicit Specs

**Problem:** Generator creates `list_objects()` returning `List[Dict]` because prompt doesn't specify it must be `List[str]`.

**Solution:** Add CRITICAL REQUIREMENTS section with exact expectations.

### Implementation:

**File:** `/Users/padak/github/ng_component/driver_creator/agent_tools.py`

**Location:** Line ~240-280 (where file-specific prompts are built)

**Find this section:**
```python
# File-specific guidance
if file_path == "client.py":
    file_prompt += f"""
- Main driver class: {class_name}Driver
- Inherit from base classes if needed
```

**Replace with:**
```python
# File-specific guidance
if file_path == "client.py":
    file_prompt += f"""
- Main driver class: {class_name}Driver
- Inherit from base classes if needed

**⚠️ CRITICAL REQUIREMENTS (MUST FOLLOW EXACTLY):**

1. **list_objects() signature:**
   ```python
   def list_objects(self) -> List[str]:
       \"\"\"Return list of object names (strings only)\"\"\"
       # WRONG: return [{{'name': 'users', 'path': '/users'}}]  ❌
       # RIGHT: return ['users', 'posts', 'comments']  ✅

       # If API has no schema endpoint, hardcode known objects:
       return ['object1', 'object2', 'object3']  # Simple strings!
   ```

2. **get_fields(object_name: str) signature:**
   ```python
   def get_fields(self, object_name: str) -> Dict[str, Any]:
       \"\"\"Return field schema for object\"\"\"
       return {{
           "field_name": {{
               "type": "string",
               "required": True,
               "nullable": False
           }}
       }}
   ```

3. **If API doesn't provide metadata:**
   - list_objects(): Return hardcoded list of endpoint names as strings
   - get_fields(): Return empty dict {{}} or infer from sample data
   - Document this limitation in docstrings

**VALIDATION (self-check before returning code):**
- [ ] list_objects() returns List[str] (NOT List[Dict])
- [ ] get_fields() returns Dict[str, Any]
- [ ] No import errors (all imports are valid)
- [ ] Proper indentation (no mixed tabs/spaces)
```

**Also add for __init__.py** (line ~306):
```python
elif file_path == "__init__.py":
    file_prompt += f"""
- Export {class_name}Driver
- Export all custom exceptions
- Set __version__ = "1.0.0"

**⚠️ CRITICAL:**
- Import from .client (NOT .driver)
- Proper indentation (4 spaces, no tabs)
- No trailing commas in single-item imports

Example:
```python
from .client import {class_name}Driver
from .exceptions import (
    DriverError,
    AuthenticationError
)
```
```

---

## Phase 3: Show Current Code to Tester

**Problem:** Tester Agent guesses `old_string` without seeing current file content. Guesses are wrong → edits fail.

**Solution:** Read file, include in prompt.

### Implementation:

**File:** `/Users/padak/github/ng_component/driver_creator/agent_tools.py`

**Location:** Line ~560 (in the edits application loop)

**Find:**
```python
# Read current file content
with open(file_path, 'r', encoding='utf-8') as f:
    current_content = f.read()
```

**Add BEFORE the Tester Agent call** (line ~540):

```python
# Read ALL files being tested to show Tester Agent current state
current_files_content = {}
for file_to_check in files_to_fix.keys():
    driver_name = output_dir.name
    if file_to_check.startswith(f"{driver_name}/"):
        relative_path = file_to_check[len(driver_name)+1:]
    else:
        relative_path = file_to_check

    check_path = output_dir / relative_path
    if check_path.exists():
        with open(check_path, 'r', encoding='utf-8') as f:
            current_files_content[file_to_check] = f.read()
```

**Then modify fix_prompt** (line ~440):

**REPLACE:**
```python
fix_prompt = f"""You are a Tester & Debugger Agent. Analyze test failures and suggest EXACT code edits.

**Driver:** {api_name}
**Test Results:** {tests_passed} passed, {tests_failed} failed

**Errors:**
{error_summary}
```

**WITH:**
```python
# Build current code section
current_code_section = ""
for file_name, file_content in current_files_content.items():
    current_code_section += f"""
**Current {file_name}:**
```python
{file_content}
```

"""

fix_prompt = f"""You are a Tester & Debugger Agent. Analyze test failures and suggest EXACT code edits.

**Driver:** {api_name}
**Test Results:** {tests_passed} passed, {tests_failed} failed

**CURRENT CODE (what's in the files NOW):**
{current_code_section}

**Errors:**
{error_summary}

**Test Output:**
{test_results.get('output', 'N/A')[:2000]}

**Your Task:**
1. READ the current code above carefully
2. FIND the exact lines causing the errors
3. Provide old_string that EXACTLY matches what's in the file (including indentation!)
4. Provide new_string with the fix

**CRITICAL for old_string:**
- Copy EXACT text from current code above (with correct whitespace)
- Include enough context to make it unique
- Match indentation precisely (count spaces!)
```

---

## Phase 4: Increase Max Retries

**Problem:** 3 iterations not enough. First 2 fix imports/indentation, never gets to actual bug.

**Solution:** Increase to 7 iterations.

### Implementation:

**File:** `/Users/padak/github/ng_component/driver_creator/agent_tools.py`

**Location:** Line ~22

**REPLACE:**
```python
def generate_driver_with_agents(
    api_name: str,
    api_url: str,
    output_dir: Optional[str] = None,
    max_retries: int = 3
```

**WITH:**
```python
def generate_driver_with_agents(
    api_name: str,
    api_url: str,
    output_dir: Optional[str] = None,
    max_retries: int = 7  # Increased from 3 - need more iterations for complex fixes
```

**Also update in app.py** (Web UI) if called from there:

**File:** `/Users/padak/github/ng_component/driver_creator/app.py`

Search for `generate_driver_with_agents` calls and ensure they don't override max_retries with lower value.

---

## Phase 5: Error Prioritization (Future Enhancement)

**Problem:** Errors are fixed in random order. Import errors should be fixed before type errors.

**Solution:** Categorize and sort errors by priority.

### Implementation:

**File:** `/Users/padak/github/ng_component/driver_creator/agent_tools.py`

**Location:** Add new function before `generate_driver_with_agents`

```python
def prioritize_errors(errors: List[Dict]) -> List[Dict]:
    """
    Sort errors by priority (P0 = most critical).

    Priority levels:
    - P0: Import errors, syntax errors (block everything)
    - P1: Type errors in core methods (list_objects, get_fields)
    - P2: Test failures, runtime errors
    - P3: Style issues, warnings
    """
    def get_priority(error):
        error_str = str(error.get('error', '')).lower()
        test_name = str(error.get('test', '')).lower()

        # P0: Syntax and import errors
        if any(keyword in error_str for keyword in ['syntaxerror', 'importerror', 'modulenotfounderror', 'indentationerror']):
            return 0

        # P1: Core method type errors
        if 'list_objects' in test_name or 'get_fields' in test_name:
            if 'expected str instance' in error_str or 'typeerror' in error_str:
                return 1

        # P2: Other test failures
        if 'failed' in test_name or 'error' in error_str:
            return 2

        # P3: Everything else
        return 3

    return sorted(errors, key=get_priority)
```

**Usage:** In fix-retry loop (line ~420):

**REPLACE:**
```python
errors = test_results.get("errors", [])
if not errors:
    print(f"   ⚠ No specific errors to fix - stopping here")
    break
```

**WITH:**
```python
errors = test_results.get("errors", [])
if not errors:
    print(f"   ⚠ No specific errors to fix - stopping here")
    break

# Prioritize errors (fix critical ones first)
errors = prioritize_errors(errors)
print(f"   📋 Prioritized {len(errors)} error(s) (P0=critical → P3=minor)")
for i, err in enumerate(errors[:3], 1):  # Show top 3
    priority = ['P0 🔴', 'P1 🟡', 'P2 🟢', 'P3 ⚪'][min(3, i-1)]
    print(f"      {priority} {err.get('test', 'unknown')}: {err.get('error', '')[:60]}...")
```

---

## Parallel Implementation Strategy

**Use Task tool to spawn parallel sub-agents for different phases:**

### Sub-Agent 1: Logging Implementation
- **Focus:** Phase 1 only
- **Files:** `agent_tools.py` (add logging functions, instrument all agent calls)
- **Deliverable:** Logging works, creates `logs/session_*/` directories
- **Time:** 30-45 minutes

### Sub-Agent 2: Prompt Enhancement
- **Focus:** Phase 2 only
- **Files:** `agent_tools.py` (add CRITICAL REQUIREMENTS to prompts)
- **Deliverable:** Generator prompts have explicit specs for `list_objects()` and `get_fields()`
- **Time:** 20-30 minutes

### Sub-Agent 3: Tester Visibility
- **Focus:** Phase 3 only
- **Files:** `agent_tools.py` (read files before Tester call, add to prompt)
- **Deliverable:** Tester sees current code in prompt
- **Time:** 25-35 minutes

### Sub-Agent 4: Config Updates
- **Focus:** Phase 4 only
- **Files:** `agent_tools.py`, `app.py`
- **Deliverable:** max_retries = 7
- **Time:** 5 minutes

### Sub-Agent 5: Error Prioritization
- **Focus:** Phase 5 only
- **Files:** `agent_tools.py` (add prioritize_errors function, integrate)
- **Deliverable:** Errors sorted by priority
- **Time:** 20-30 minutes

---

## Testing Strategy

After implementation, test with:

1. **Open-Meteo API** (current failing case)
   ```bash
   cd /Users/padak/github/ng_component/driver_creator
   uvicorn app:app --port 8080
   # Create driver for https://open-meteo.com/en/docs
   ```

2. **Verify logging:**
   ```bash
   ls -la logs/session_*/
   cat logs/session_*/research_prompt.txt
   cat logs/session_*/generator_output.jsonl
   ```

3. **Check success criteria:**
   - [ ] Driver generates without errors OR
   - [ ] Errors are fixed within 7 iterations
   - [ ] `list_objects()` returns `List[str]`
   - [ ] `get_fields()` returns `Dict[str, Any]`
   - [ ] Logs show what each agent did

---

## Success Criteria

**Must have:**
- ✅ Driver generation succeeds on first try (or fixes bugs automatically)
- ✅ `list_objects()` always returns `List[str]`
- ✅ Comprehensive logs show agent interactions
- ✅ Max 7 iterations available

**Nice to have:**
- ✅ Error prioritization working
- ✅ Logs are human-readable
- ✅ Cost tracking per agent

---

## Files to Modify

1. **agent_tools.py** - Main implementation file
   - Add logging functions (line ~15)
   - Add logging calls to all agents
   - Fix Generator prompts (line ~240)
   - Fix Tester prompt (line ~440)
   - Add error prioritization (new function)
   - Increase max_retries (line ~22)

2. **app.py** - Web UI
   - Verify max_retries not overridden
   - Optional: Stream logs to UI

---

## Rollback Plan

If anything breaks:

```bash
git diff agent_tools.py
git checkout agent_tools.py  # Revert
```

Or commit before changes:
```bash
git add -A
git commit -m "feat: Before fixing driver generation loop"
```

---

## Post-Implementation

After all phases work:

1. **Update CLAUDE.md** with new logging paths
2. **Document** error prioritization in comments
3. **Create examples** of good logs
4. **Consider** external prompt files (Phase 6)

---

## Quick Start (For New Session)

```bash
# 1. Read this file
Read /Users/padak/github/ng_component/driver_creator/FIX_DRIVER_GENERATION.md

# 2. Spawn parallel sub-agents (if using Task tool)
Task(subagent_type="general-purpose", description="Implement Phase 1: Logging", prompt="[Phase 1 section from this file]")
Task(subagent_type="general-purpose", description="Implement Phase 2: Prompts", prompt="[Phase 2 section from this file]")
Task(subagent_type="general-purpose", description="Implement Phase 3: Tester", prompt="[Phase 3 section from this file]")
Task(subagent_type="general-purpose", description="Implement Phase 4: Config", prompt="[Phase 4 section from this file]")

# 3. After all complete, test
cd /Users/padak/github/ng_component/driver_creator
uvicorn app:app --port 8080

# 4. Verify logs
ls -la logs/
```

---

## Context for New Session

**Problem:** Driver generation agent repeatedly fails with `list_objects()` returning `List[Dict]` instead of `List[str]`. Fix-retry loop doesn't work because:

1. No logging (can't see what agents are doing)
2. Generic prompts (not specific enough about requirements)
3. Tester doesn't see current code (can't provide accurate fixes)
4. Only 3 iterations (not enough to fix all issues)
5. No error prioritization (fixes minor issues first, runs out of retries before fixing critical bugs)

**This plan fixes all 5 issues systematically.**
