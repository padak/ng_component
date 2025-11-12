# Self-Healing Agent System - Implementation Spec

**Status:** Ready to Implement
**Priority:** HIGH - Makes driver generation rock-solid
**Estimated Time:** 2-3 hours (with parallel sub-agents)
**Context:** We've fixed P0/P1 bugs, now adding multi-layer self-healing

---

## 🎯 Goal

Transform driver generation from fragile to **rock-solid** by implementing 3-layer self-healing architecture:

1. **Layer 1 (Defensive Wrappers)** - Try-catch + validation at every step
2. **Layer 2 (Diagnostic Agent)** - Analyzes failures and suggests fixes
3. **Layer 3 (Supervisor Agent)** - Orchestrates retries with adaptive strategies

**Inspiration:** Claude Code's Task tool pattern - spawn specialized agents for diagnostics and recovery.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│ generate_driver_supervised() - NEW MAIN ENTRY POINT     │
│ (Supervisor Agent - Layer 3)                            │
│                                                         │
│ for attempt in range(max_attempts):                    │
│   try:                                                  │
│     └─> generate_driver_with_agents_resilient()        │
│           │                                             │
│           ├─> Research Agent (existing, now wrapped)   │
│           │                                             │
│           ├─> Generator Agent (Layer 1 wrappers)       │
│           │     └─> generate_file_resilient()          │
│           │           ├─> try: claude.messages.create() │
│           │           ├─> validate output               │
│           │           └─> catch: diagnose & retry       │
│           │                                             │
│           ├─> Tester Agent (existing)                  │
│           │                                             │
│           └─> Fix-Retry Loop (existing, enhanced)      │
│                                                         │
│   except GenerationFailure:                            │
│     └─> LAUNCH DIAGNOSTIC AGENT (Layer 2)              │
│           └─> Returns diagnosis + fix strategy         │
│                                                         │
│   └─> Apply fix & retry (Supervisor logic)             │
└─────────────────────────────────────────────────────────┘
```

---

## 📋 Layer 1: Defensive Wrappers

### Implementation File: `agent_tools.py`

### 1.1 Wrap File Generation

**Add new function before `generate_driver_with_agents()`:**

```python
def generate_file_resilient(
    file_path: str,
    file_prompt: str,
    research_data: Dict,
    class_name: str,
    max_retries: int = 3
) -> str:
    """
    Generate a single file with automatic error recovery.

    Layer 1 defense: Try-catch, validation, fallback strategies.

    Returns:
        Generated file content as string

    Raises:
        GenerationError: If all retry strategies fail
    """

    for attempt in range(max_retries):
        try:
            # Log attempt
            log_agent_interaction('generator', 'input', {
                'file': file_path,
                'attempt': attempt + 1,
                'prompt_length': len(file_prompt)
            })

            # Call Claude
            response = claude.messages.create(
                model=get_agent_model('generator'),
                max_tokens=8000,
                system=GENERATOR_SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": file_prompt
                }]
            )

            # Extract content
            file_content = response.content[0].text

            # VALIDATION LAYER
            validation_errors = validate_generated_file(file_path, file_content)

            if not validation_errors:
                # Success!
                log_agent_interaction('generator', 'output', {
                    'file': file_path,
                    'length': len(file_content),
                    'attempt': attempt + 1
                })
                return file_content

            # Has validation errors - try to self-correct
            print(f"   ⚠️  Validation errors on attempt {attempt+1}: {len(validation_errors)}")

            if attempt < max_retries - 1:
                # Add validation feedback to prompt for next attempt
                file_prompt = add_validation_feedback(file_prompt, validation_errors)
                continue
            else:
                # Last attempt failed
                raise GenerationError(
                    f"File {file_path} failed validation after {max_retries} attempts",
                    errors=validation_errors
                )

        except json.JSONDecodeError as e:
            # JSON parsing failed
            print(f"   ⚠️  JSON parse error on attempt {attempt+1}: {e}")

            if attempt < max_retries - 1:
                # Retry with stronger JSON guidance
                file_prompt = add_json_strict_mode(file_prompt)
                continue
            else:
                raise GenerationError(f"JSON parsing failed: {e}")

        except AnthropicAPIError as e:
            # API error (overloaded, timeout, etc.)
            if 'overloaded' in str(e).lower():
                wait_time = 5 * (attempt + 1)
                print(f"   ⏳ API overloaded, waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                raise

    # All retries exhausted
    raise GenerationError(f"Failed to generate {file_path} after {max_retries} attempts")


def validate_generated_file(file_path: str, content: str) -> List[str]:
    """
    Validate generated file content.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # 1. Python syntax check
    if file_path.endswith('.py'):
        try:
            compile(content, file_path, 'exec')
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")

    # 2. Check for required elements
    if file_path == 'client.py':
        # Must have list_objects() returning List[str]
        if 'def list_objects(self) -> List[str]:' not in content:
            errors.append("Missing correct list_objects() signature")

        # Check for common mistake: returning Dict
        if re.search(r"return \[{['\"]name['\"]:", content):
            errors.append("list_objects() returns List[Dict] instead of List[str]")

    # 3. Check for placeholder text
    if 'TODO' in content or 'FIXME' in content or '...' in content:
        errors.append("Contains placeholder text (TODO/FIXME/...)")

    return errors


def add_validation_feedback(prompt: str, errors: List[str]) -> str:
    """
    Add validation error feedback to prompt for retry.
    """
    feedback = "\n\n**⚠️ PREVIOUS ATTEMPT HAD THESE ERRORS - FIX THEM:**\n"
    for i, error in enumerate(errors, 1):
        feedback += f"{i}. {error}\n"

    return prompt + feedback


def add_json_strict_mode(prompt: str) -> str:
    """
    Add strict JSON formatting requirements to prompt.
    """
    return prompt + """

**⚠️ JSON FORMATTING REQUIREMENTS:**
- Return ONLY valid JSON
- No markdown code blocks
- No explanatory text before or after JSON
- All strings must use double quotes "
- No trailing commas
"""


class GenerationError(Exception):
    """Raised when file generation fails after all retries."""
    def __init__(self, message: str, errors: List[str] = None):
        super().__init__(message)
        self.errors = errors or []
```

### 1.2 Update `generate_driver_with_agents()` to use resilient generation

**Find the file generation loop (around line 450-570) and replace:**

```python
# OLD:
response = claude.messages.create(...)
file_content = response.content[0].text

# NEW:
file_content = generate_file_resilient(
    file_path=file_path,
    file_prompt=file_prompt,
    research_data=research_data,
    class_name=class_name,
    max_retries=3
)
```

---

## 📋 Layer 2: Diagnostic Agent

### Implementation File: `agent_tools.py`

### 2.1 Add Diagnostic Agent Function

**Add after Layer 1 functions:**

```python
def launch_diagnostic_agent(
    failure_context: Dict[str, Any],
    session_dir: Path,
    attempt: int
) -> Dict[str, Any]:
    """
    Launch specialized Diagnostic Agent to analyze generation failure.

    Uses Claude Haiku for fast, cheap diagnosis.

    Args:
        failure_context: Dict with error details, result, etc.
        session_dir: Path to session logs
        attempt: Current retry attempt number

    Returns:
        {
            "error_type": "formatting|logic|timeout|api|unknown",
            "root_cause": "Description of what went wrong",
            "can_fix": true|false,
            "fix_strategy": "prompt_adjustment|simplify|fallback|abort",
            "fix_description": "Human readable fix description",
            "prompt_modification": "Specific change to make to prompts"
        }
    """

    print(f"   🔍 Diagnostic Agent analyzing failure...")

    # Build diagnostic prompt
    diagnostic_prompt = build_diagnostic_prompt(failure_context, session_dir)

    # Log diagnostic call
    log_agent_interaction('diagnostic', 'input', {
        'attempt': attempt,
        'context': str(failure_context)[:500]
    })

    try:
        response = claude.messages.create(
            model="claude-haiku-4",  # Fast & cheap
            max_tokens=2000,
            system="""You are a Diagnostic Agent specialized in analyzing driver generation failures.

Your job: Quickly identify root cause and suggest concrete fix.

Return ONLY valid JSON with this structure:
{
    "error_type": "formatting|logic|timeout|api|unknown",
    "root_cause": "...",
    "can_fix": true|false,
    "fix_strategy": "prompt_adjustment|simplify|fallback|abort",
    "fix_description": "...",
    "prompt_modification": "..."
}""",
            messages=[{
                "role": "user",
                "content": diagnostic_prompt
            }]
        )

        # Parse diagnosis
        diagnosis_text = response.content[0].text

        # Extract JSON (handle both raw JSON and markdown-wrapped)
        diagnosis = extract_json_from_response(diagnosis_text)

        # Log result
        log_agent_interaction('diagnostic', 'output', {
            'diagnosis': diagnosis
        })

        print(f"   ✓ Diagnosis: {diagnosis['error_type']} - {diagnosis['root_cause'][:60]}...")

        return diagnosis

    except Exception as e:
        print(f"   ⚠️  Diagnostic Agent failed: {e}")
        # Return safe default
        return {
            "error_type": "unknown",
            "root_cause": str(e),
            "can_fix": False,
            "fix_strategy": "abort",
            "fix_description": "Diagnostic agent failed",
            "prompt_modification": ""
        }


def build_diagnostic_prompt(context: Dict, session_dir: Path) -> str:
    """
    Build diagnostic prompt with all available context.
    """
    # Read recent logs
    logs = read_recent_logs(session_dir, max_lines=100)

    prompt = f"""Analyze this driver generation failure:

**Attempt:** {context.get('attempt', 0)}/3

**Error Type:** {context.get('error_type', 'Unknown')}

**Error Message:**
{context.get('error_message', 'No error message')}

**Generation Result:**
```json
{json.dumps(context.get('result', {}), indent=2)[:1000]}
```

**Recent Logs:**
```
{logs}
```

**Context:**
- API: {context.get('api_name', 'Unknown')}
- Files generated: {context.get('files_generated', [])}
- Test results: {context.get('test_results', {})}

**Your Task:**

1. **Classify error type:**
   - formatting: JSON/syntax/string formatting issues
   - logic: Wrong implementation (e.g., list_objects returns Dict)
   - timeout: Took too long
   - api: Anthropic API issues (overload, rate limit)
   - unknown: Can't determine

2. **Identify root cause:** What specifically went wrong?

3. **Determine if fixable:** Can we recover by adjusting prompts?

4. **Suggest fix strategy:**
   - prompt_adjustment: Add specific instruction to prompt
   - simplify: Reduce complexity, use simpler approach
   - fallback: Use template-based generation
   - abort: Fatal error, can't recover

5. **Describe fix:** Concrete change to make

Return JSON with your analysis.
"""

    return prompt


def read_recent_logs(session_dir: Path, max_lines: int = 100) -> str:
    """
    Read most recent log entries from session.
    """
    logs = []

    # Read from .txt logs (human-readable)
    for log_file in sorted(session_dir.glob("*.txt"), reverse=True):
        try:
            with open(log_file, 'r') as f:
                content = f.read()
                logs.append(f"=== {log_file.name} ===\n{content[-1000:]}")  # Last 1000 chars
        except:
            pass

    full_log = "\n\n".join(logs)

    # Truncate if too long
    lines = full_log.split('\n')
    if len(lines) > max_lines:
        return '\n'.join(lines[-max_lines:])

    return full_log


def extract_json_from_response(text: str) -> Dict:
    """
    Extract JSON from Claude response (handles markdown wrapping).
    """
    # Try direct JSON parse first
    try:
        return json.loads(text)
    except:
        pass

    # Look for JSON in markdown code block
    import re
    match = re.search(r'```(?:json)?\n(.*?)\n```', text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    # Look for JSON object
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError(f"No valid JSON found in response: {text[:200]}")
```

---

## 📋 Layer 3: Supervisor Agent

### Implementation File: `agent_tools.py`

### 3.1 Add Main Supervisor Function

**Add as NEW main entry point:**

```python
def generate_driver_supervised(
    api_name: str,
    api_url: str,
    output_dir: Optional[str] = None,
    max_supervisor_attempts: int = 3,
    max_retries: int = 7
) -> Dict[str, Any]:
    """
    🏆 MAIN ENTRY POINT for self-healing driver generation.

    This function wraps generate_driver_with_agents() with supervisor-level
    retry logic that:
    1. Monitors the entire generation process
    2. Launches Diagnostic Agent on failures
    3. Applies fixes and retries with adaptive strategies
    4. Learns from failures for future generations

    Architecture:
        Layer 3 (This): Supervisor orchestration
        Layer 2: Diagnostic Agent for failure analysis
        Layer 1: Defensive wrappers in generate_file_resilient()

    Args:
        api_name: Name of API (e.g., "Open-Meteo")
        api_url: Base URL of API
        output_dir: Optional output directory
        max_supervisor_attempts: Max supervisor-level retries (default: 3)
        max_retries: Max fix-retry iterations per attempt (default: 7)

    Returns:
        Same format as generate_driver_with_agents() but with added fields:
        {
            "success": bool,
            "supervisor_attempts": int,
            "diagnostics_run": int,
            "fixes_applied": List[str],
            ...
        }
    """

    print("=" * 80)
    print("🏆 SUPERVISOR: Self-Healing Driver Generation")
    print("=" * 80)
    print(f"Max supervisor attempts: {max_supervisor_attempts}")
    print(f"Max fix-retry iterations per attempt: {max_retries}")
    print()

    session_dir = init_session_logging()

    supervisor_context = {
        'api_name': api_name,
        'api_url': api_url,
        'attempts': [],
        'diagnostics_run': 0,
        'fixes_applied': []
    }

    for attempt in range(max_supervisor_attempts):
        print(f"\n{'='*80}")
        print(f"🔄 SUPERVISOR ATTEMPT {attempt + 1}/{max_supervisor_attempts}")
        print(f"{'='*80}\n")

        attempt_context = {
            'attempt_num': attempt + 1,
            'start_time': time.time()
        }

        try:
            # === CORE GENERATION ===
            result = generate_driver_with_agents(
                api_name=api_name,
                api_url=api_url,
                output_dir=output_dir,
                max_retries=max_retries
            )

            attempt_context['result'] = result
            attempt_context['duration'] = time.time() - attempt_context['start_time']

            # === CHECK SUCCESS ===
            if result.get('success'):
                print(f"\n✅ SUPERVISOR: Generation successful on attempt {attempt + 1}")

                # Add supervisor metadata
                result['supervisor_attempts'] = attempt + 1
                result['diagnostics_run'] = supervisor_context['diagnostics_run']
                result['fixes_applied'] = supervisor_context['fixes_applied']

                return result

            # === GENERATION FAILED ===
            print(f"\n⚠️  SUPERVISOR: Generation failed on attempt {attempt + 1}")
            print(f"   Reason: {result.get('error', 'Unknown')}")

            # Don't retry if this was the last attempt
            if attempt >= max_supervisor_attempts - 1:
                print(f"\n❌ SUPERVISOR: Max attempts reached")
                result['supervisor_attempts'] = attempt + 1
                result['diagnostics_run'] = supervisor_context['diagnostics_run']
                result['fixes_applied'] = supervisor_context['fixes_applied']
                return result

            # === LAUNCH DIAGNOSTIC AGENT ===
            print(f"\n🔍 SUPERVISOR: Launching Diagnostic Agent...")
            supervisor_context['diagnostics_run'] += 1

            diagnosis = launch_diagnostic_agent(
                failure_context={
                    'attempt': attempt + 1,
                    'error_type': 'generation_failed',
                    'error_message': result.get('error', ''),
                    'result': result,
                    'api_name': api_name,
                    'files_generated': result.get('files_created', []),
                    'test_results': {
                        'passed': result.get('tests_passed', 0),
                        'failed': result.get('tests_failed', 0)
                    }
                },
                session_dir=session_dir,
                attempt=attempt
            )

            attempt_context['diagnosis'] = diagnosis

            # === CHECK IF FIXABLE ===
            if not diagnosis.get('can_fix'):
                print(f"\n❌ SUPERVISOR: Diagnostic says cannot fix: {diagnosis.get('root_cause')}")
                result['diagnosis'] = diagnosis
                result['supervisor_attempts'] = attempt + 1
                return result

            # === APPLY FIX ===
            print(f"\n🔧 SUPERVISOR: Applying fix...")
            print(f"   Strategy: {diagnosis.get('fix_strategy')}")
            print(f"   Description: {diagnosis.get('fix_description')}")

            fix_result = apply_diagnostic_fix(diagnosis, api_name, api_url)

            supervisor_context['fixes_applied'].append({
                'attempt': attempt + 1,
                'strategy': diagnosis.get('fix_strategy'),
                'description': diagnosis.get('fix_description')
            })

            if not fix_result['success']:
                print(f"   ⚠️  Fix application failed: {fix_result.get('error')}")
                # Continue to retry anyway
            else:
                print(f"   ✓ Fix applied successfully")

            # Retry on next iteration
            print(f"\n🔄 SUPERVISOR: Retrying with applied fixes...")

        except GenerationError as e:
            # Layer 1 defensive wrapper raised error
            print(f"\n💥 SUPERVISOR: Generation error caught: {e}")

            attempt_context['crash'] = {
                'type': type(e).__name__,
                'message': str(e),
                'errors': getattr(e, 'errors', [])
            }

            # Last attempt?
            if attempt >= max_supervisor_attempts - 1:
                return {
                    'success': False,
                    'error': str(e),
                    'supervisor_attempts': attempt + 1,
                    'diagnostics_run': supervisor_context['diagnostics_run'],
                    'crash': attempt_context['crash']
                }

            # Diagnose crash
            print(f"🔍 SUPERVISOR: Diagnosing crash...")
            supervisor_context['diagnostics_run'] += 1

            diagnosis = launch_diagnostic_agent(
                failure_context={
                    'attempt': attempt + 1,
                    'error_type': 'crash',
                    'error_message': str(e),
                    'crash_details': attempt_context['crash'],
                    'api_name': api_name
                },
                session_dir=session_dir,
                attempt=attempt
            )

            if diagnosis.get('can_fix'):
                apply_diagnostic_fix(diagnosis, api_name, api_url)
                supervisor_context['fixes_applied'].append({
                    'attempt': attempt + 1,
                    'type': 'crash_recovery',
                    'description': diagnosis.get('fix_description')
                })

            # Retry
            continue

        except Exception as e:
            # Unexpected error
            print(f"\n💥 SUPERVISOR: Unexpected error: {type(e).__name__}: {e}")

            if attempt >= max_supervisor_attempts - 1:
                return {
                    'success': False,
                    'error': f"Unexpected: {e}",
                    'supervisor_attempts': attempt + 1,
                    'diagnostics_run': supervisor_context['diagnostics_run']
                }

            # Last-resort: wait and retry
            print(f"⏳ Waiting 10s before retry...")
            time.sleep(10)
            continue

        finally:
            # Record attempt
            supervisor_context['attempts'].append(attempt_context)

    # All attempts exhausted
    print(f"\n❌ SUPERVISOR: All {max_supervisor_attempts} attempts failed")

    return {
        'success': False,
        'error': 'All supervisor attempts exhausted',
        'supervisor_attempts': max_supervisor_attempts,
        'diagnostics_run': supervisor_context['diagnostics_run'],
        'fixes_applied': supervisor_context['fixes_applied'],
        'attempts': supervisor_context['attempts']
    }


def apply_diagnostic_fix(
    diagnosis: Dict[str, Any],
    api_name: str,
    api_url: str
) -> Dict[str, bool]:
    """
    Apply fix suggested by Diagnostic Agent.

    Args:
        diagnosis: Output from launch_diagnostic_agent()
        api_name: API name
        api_url: API URL

    Returns:
        {"success": bool, "error": str}
    """

    strategy = diagnosis.get('fix_strategy')

    try:
        if strategy == 'prompt_adjustment':
            # Modify prompts globally
            modification = diagnosis.get('prompt_modification', '')

            # This would need to modify the prompt templates
            # For now, we'll store it in a global that gets picked up next iteration
            global DIAGNOSTIC_PROMPT_ADJUSTMENTS
            DIAGNOSTIC_PROMPT_ADJUSTMENTS.append(modification)

            return {'success': True}

        elif strategy == 'simplify':
            # Reduce complexity - use simpler prompts
            global USE_SIMPLIFIED_PROMPTS
            USE_SIMPLIFIED_PROMPTS = True

            return {'success': True}

        elif strategy == 'fallback':
            # Would trigger fallback generation
            global USE_FALLBACK_GENERATION
            USE_FALLBACK_GENERATION = True

            return {'success': True}

        elif strategy == 'abort':
            # Don't retry
            return {'success': False, 'error': 'Diagnostic says abort'}

        else:
            return {'success': False, 'error': f'Unknown strategy: {strategy}'}

    except Exception as e:
        return {'success': False, 'error': str(e)}


# Global state for diagnostic fixes (will be checked in generate_file_resilient)
DIAGNOSTIC_PROMPT_ADJUSTMENTS = []
USE_SIMPLIFIED_PROMPTS = False
USE_FALLBACK_GENERATION = False
```

---

## 🔗 Integration Points

### Update `app.py` to use Supervisor

**Find the `generate_driver_with_agents` tool handler (around line 640) and replace:**

```python
# OLD:
result = await loop.run_in_executor(
    None,
    lambda: generate_driver_with_agents(
        api_name=api_name,
        api_url=api_url,
        output_dir=output_dir,
        max_retries=max_retries
    )
)

# NEW:
result = await loop.run_in_executor(
    None,
    lambda: generate_driver_supervised(  # Changed from generate_driver_with_agents
        api_name=api_name,
        api_url=api_url,
        output_dir=output_dir,
        max_supervisor_attempts=3,  # Supervisor-level retries
        max_retries=max_retries  # Fix-retry iterations per attempt
    )
)
```

**Update tool description in Claude tools:**

```python
{
    "name": "generate_driver_with_agents",
    "description": "🚀 SELF-HEALING: Generate driver with 3-layer self-healing architecture. Automatically diagnoses failures and retries with adaptive strategies. Rock-solid generation with Supervisor Agent + Diagnostic Agent + defensive wrappers.",
    ...
}
```

---

## 🧪 Testing Strategy

### Test 1: Normal Generation (Should Work First Try)

```bash
# Simple API that should work immediately
curl -X POST http://localhost:8080/generate \
  -d '{"api_name": "JSONPlaceholder", "api_url": "https://jsonplaceholder.typicode.com"}'

# Expected:
# - Supervisor attempt 1 succeeds
# - No diagnostic needed
# - supervisor_attempts: 1, diagnostics_run: 0
```

### Test 2: Recoverable Failure (Should Auto-Fix)

```bash
# Complex API that might fail first time
curl -X POST http://localhost:8080/generate \
  -d '{"api_name": "OpenMeteo", "api_url": "https://api.open-meteo.com/v1"}'

# Expected:
# - Attempt 1: May fail with list_objects bug
# - Diagnostic Agent identifies issue
# - Attempt 2: Succeeds with adjusted prompts
# - supervisor_attempts: 2, diagnostics_run: 1, fixes_applied: [...]
```

### Test 3: Fatal Error (Should Gracefully Fail)

```bash
# Invalid API
curl -X POST http://localhost:8080/generate \
  -d '{"api_name": "Invalid", "api_url": "https://nonexistent.api.com"}'

# Expected:
# - All attempts fail
# - Diagnostic Agent says "cannot fix"
# - supervisor_attempts: 3, diagnostics_run: 3, success: false
```

---

## 📊 Success Metrics

After implementation, we should see:

| Metric | Before | Target |
|--------|--------|--------|
| Success rate (first try) | ~30% | ~60% |
| Success rate (after retries) | ~30% | ~95% |
| Average supervisor attempts | N/A | 1.5 |
| Crash recovery rate | 0% | ~80% |
| Unhandled exceptions | Common | Rare |

---

## 🚀 Implementation Plan (Parallel Sub-Agents)

Use **Task tool** to spawn 3 parallel agents:

### Sub-Agent 1: Layer 1 (Defensive Wrappers)
**File:** `agent_tools.py`
**Task:** Implement `generate_file_resilient()` and helpers
**Time:** 30-40 min

### Sub-Agent 2: Layer 2 (Diagnostic Agent)
**File:** `agent_tools.py`
**Task:** Implement `launch_diagnostic_agent()` and helpers
**Time:** 40-50 min

### Sub-Agent 3: Layer 3 (Supervisor Agent)
**File:** `agent_tools.py` + `app.py`
**Task:** Implement `generate_driver_supervised()` and integrate
**Time:** 50-60 min

**Total Time:** ~60 min (parallel) vs ~120 min (sequential) = **2x speedup**

---

## 📝 Files to Modify

1. **`agent_tools.py`** - Add all 3 layers (~400 new lines)
2. **`app.py`** - Update tool handler to use supervisor (~5 line change)
3. **New exception:** `GenerationError` class

---

## 🎯 Next Session Instructions

When you return to this task:

1. Read this file completely
2. Spawn 3 parallel sub-agents using Task tool:
   - Agent 1: Layer 1 implementation
   - Agent 2: Layer 2 implementation
   - Agent 3: Layer 3 implementation
3. After all complete, test with Open-Meteo
4. Verify logs show diagnostic agent running
5. Commit as "feat: Add 3-layer self-healing agent system"

---

## 🔗 Related Files

- `FIX_DRIVER_GENERATION.md` - Original Phase 1-5 plan
- `BUGFIX_SUMMARY.md` - P0/P1 bugfixes completed
- `IMPLEMENTATION_SUMMARY.md` - Phase 1-5 implementation

**This builds on top of all previous work to make the system truly production-ready!**
