# Agent-Based Integration System - Product Requirements Document

**Status**: ✅ Ready for Implementation (v1.0 - All blocking gaps resolved)
**Version**: 1.0
**Date**: 2025-11-09

---

## 1. Vision

A system that enables **business users** (not programmers) to write integration scripts for any external systems with an **agent**, without knowledge of their internal structure.

> "10% is the technical logic itself, 90% is productization — and the agent handles those 90%."

---

## 2. Core Concept

### Without agent (today)
```
Business user → Developer → Must learn API → Writes script → Months
```

### With agent (future)
```
Business user → Agent (with library) → Dialog → Script → Days/Hours
```

The agent is an intermediary that:
1. Understands the **target system** (from library + knowledge base)
2. Asks about **business requirements**
3. Does **discovery** when needed
4. Writes **production-ready script** in Python
5. Iterates with user until it's right

---

## 3. Model Workflow

```
Business user: "I want to sync leads from Salesforce to PostgreSQL,
                specifically: name, email, how they got to us"

                ↓

Agent: [Reads library README, knows what Salesforce is]
       "OK, Salesforce has a Lead object.
        Do you have a Source field in Salesforce? How do you define 'how they got here'?"

                ↓

Business: "Yes, Source field. I only want leads from the last 30 days."

                ↓

Agent: [Runs mini script via library, discovers Lead structure]
       [Runs mini script on PostgreSQL, sees table structure]
       [Writes integration script]

                ↓

Business: [Runs script in e2b, sees it works]
          "Perfect! But I want this to run every night."

                ↓

Agent: [Updates script for scheduling]
       "Done, here's the new version with APScheduler"

                ↓

Output: Production Python script, tested, ready to deploy
```

---

## 4. System Components

### 4.1 Driver / Library (per system)

**What it is**: Python package for integrating a specific system (Salesforce, HubSpot, PostgreSQL, Weather APIs, ...).

> **📖 Complete specification**: See [Driver Design v2.0](driver_design_v2.md) for production-ready architecture, API contract, and implementation guidelines.

**Core Concept**:
- **Driver documents** how to write Python code (via README, docstrings, examples)
- **Agent generates** integration scripts using driver API
- **Python runtime executes** the generated code (not the agent!)

**Structure**:
```
salesforce_driver/
├── __init__.py          # Version, exports
├── client.py            # BaseDriver implementation
├── exceptions.py        # Structured exception hierarchy
├── README.md            # System overview, quick start, query language
├── examples/            # Certified example scripts (3-5 scripts)
│   ├── list_leads.py
│   ├── query_with_filters.py
│   └── pagination_example.py
└── tests/               # Unit and integration tests
    ├── test_client.py
    └── test_integration.py
```

**Driver API Contract v2.0** (required methods):

| Method | Signature | Purpose |
|--------|-----------|---------|
| `__init__(api_url, api_key, ...)` | Constructor | Initialize with credentials (fail fast!) |
| `from_env()` | `classmethod -> Driver` | Load credentials from environment variables |
| `get_capabilities()` | `() -> DriverCapabilities` | What driver can do (read, write, pagination style, etc.) |
| `list_objects()` | `() -> List[str]` | Discovery: available objects/tables/endpoints |
| `get_fields(object_name)` | `(str) -> Dict[str, Any]` | Discovery: field schema with types and metadata |
| `read(query, limit, offset)` | `(str, int, int) -> List[Dict]` | Execute query, return results |

**Optional methods** (based on capabilities):
- `create(object_name, data)` - Create record
- `update(object_name, id, data)` - Update record
- `delete(object_name, id)` - Delete record (rarely used!)
- `read_batched(query, batch_size)` - Iterator for large datasets
- `call_endpoint(endpoint, method, params)` - Low-level REST API access
- High-level convenience methods (e.g., `create_lead(first_name, last_name, ...)`)

**Key Features**:
- **Hybrid authentication** - `Driver.from_env()` or `Driver(api_key=...)`
- **Automatic retry** - Driver handles rate limiting with exponential backoff
- **Structured exceptions** - `AuthenticationError`, `ObjectNotFoundError`, `RateLimitError`, etc.
- **Both abstraction layers** - Low-level (query/call_endpoint) + high-level (create_lead)
- **Fail fast** - Validate credentials at `__init__` time
- **Debug mode** - `Driver(debug=True)` logs all API calls

**Documentation Requirements**:
- **README.md** - Overview, authentication, query language, common patterns
- **Docstrings** - Type hints + examples in every public method
- **Examples folder** - 3-5 certified scripts for few-shot learning
- **OpenAPI spec** (optional for REST APIs) - Machine-readable endpoint documentation

**Authentication**:
- Business user puts credentials in `.env` file
- Driver loads via `from_env()` or accepts explicit parameters
- Agent generates code that uses `from_env()` (no credentials in code!)

**Error Handling**:
- Driver raises structured exceptions with descriptive messages
- Errors include `details` dict for programmatic handling
- Example: `ObjectNotFoundError("Object 'Leads' not found. Did you mean 'Lead'?", details={"suggestions": ["Lead"]})`

**See also**:
- [Driver Design v2.0](driver_design_v2.md) - Complete specification
- [Current implementation](../examples/e2b_mockup/salesforce_driver/) - Proof-of-concept Salesforce driver
- [Driver Contract](../examples/e2b_mockup/DRIVER_CONTRACT.md) - V1 specification (deprecated in favor of v2)

---

### 4.2 Instructions for Agent

**What it is**: Knowledge about the target system written as a senior would pass it to a junior.

**Content** (like "onboarding"):
- System overview (what Salesforce is, how it works, what the pitfalls are)
- API throttling, rate limits, specifics
- Best practices for writing integration scripts for that system
- How to use the library
- When to call discovery, when not to

**Where it lives**:
- In library's `README.md` + `docs/`
- Agent reads this when first working with the library

---

### 4.3 Agent Orchestration

**Agent Model**: Claude Sonnet 4.5

**Agent Role**: Integration builder - Expert at writing integration scripts between systems

**How agent gets driver**:
- Driver is available as **MCP server** or registered in driver registry
- When user mentions a system (e.g., "Salesforce"), agent automatically looks up and loads the driver
- MCP provides driver capabilities, documentation, and examples

**Documentation Loading**: **Dynamic RAG**
- Agent doesn't load all documentation at once (context window limits)
- Agent retrieves only what it needs at each step
- README → specific docs → examples → as needed

**Agent Bootstrap Flow** (when user says "I want data from Salesforce"):

1. **Load driver** - Agent finds `salesforce_driver` in MCP registry or driver registry
2. **Read capabilities** - What methods does the driver provide? (`list_objects()`, `get_fields()`, etc.)
3. **Read README** - What is Salesforce? How does it work? Key concepts
4. **Read examples** - Look at certified queries for reference patterns
5. **Ask user** - "What specifically do you need?" (clarify requirements)
6. **Discovery** (if needed) - Run mini scripts to discover current state
7. **Write script** - Generate integration code
8. **Validate** - Run in e2b, get user approval
9. **Iterate** - Fix errors, improve based on feedback

**Timing**: **Proactive**
- Agent loads driver immediately when user mentions the system name
- Doesn't wait to understand full requirements before starting to learn about the system

---

### 4.4 Discovery Execution

**How discovery works**:
- Agent **writes mini Python scripts** to discover system structure
- Scripts use the driver Client to call discovery methods
- Example: `client = SalesforceClient(); print(client.get_fields('Lead'))`

**Execution environment**:
- Discovery scripts run in **e2b** (isolated Python sandbox)
- Scripts use **user credentials** from `.env` (loaded in e2b environment)
- No other permissions - scripts cannot modify data

**Output format**:
- Results returned as **Python dict/list** structures
- Agent receives structured data back into context
- Example return: `{'Name': {'type': 'string', 'nullable': False}, 'Email': {'type': 'string', 'nullable': True}, ...}`

**Error handling**:
- If discovery fails (timeout, API down, auth error), agent **fails gracefully**
- Agent informs user what happened: "I couldn't connect to Salesforce. Could you check your credentials?"
- Agent may suggest alternatives: "Would you like to proceed based on standard Salesforce schema instead?"
- Agent does not automatically retry - asks user for guidance

**Permissions**:
- Discovery scripts have **read-only access** to target system
- Cannot write, update, or delete data
- Scoped by user credentials (whatever permissions the user's API key has)

---

### 4.5 Testing & Validation

**How agent validates generated scripts**:

1. **Run in e2b** - Agent executes the script in isolated environment
2. **User approval** - Agent shows output to user, asks "Does this look right?"

**When script fails**:
- **Agent fixes it** - Agent sees the error, analyzes what went wrong, and rewrites the script
- Iterates until it works or asks user for clarification

**Approval workflow**:
- **First run requires approval** - User must review and approve the first successful execution
- **After first success** - Script can run automatically (user has validated it works correctly)
- **For write operations** - Always requires explicit approval, never automatic

---

## 5. Use Cases

### Use Case 1: Lead Sync
```
Business: "I want leads from Salesforce with campaign info,
           filtered to the last 30 days"

Output: Script that pulls Lead→Campaign data, filters by date, returns CSV/JSON
```

### Use Case 2: Opportunity Analysis
```
Business: "Which campaign brings the highest quality leads (ones that converted)?"

Output: Script that analyzes Lead→Opportunity relationships, returns report
```

### Use Case 3: Multi-System Sync
```
Business: "Sync leads from Salesforce to Hubspot, then to our DB"

Output: Script that uses salesforce_driver + hubspot_driver, syncs data
```

---

## 6. Architecture

### 6.1 Modular per system
- Each external system has its own driver (`salesforce_driver/`, `hubspot_driver/`, ...)
- Agent picks the right one based on user request
- Later, drivers can be consolidated into a more universal system

### 6.2 Execution Environment
- Scripts run in **e2b** (isolated Python environment)
- Business user takes the final script and can deploy it wherever they want

### 6.3 Security & Governance

**Access Permissions**:
- Agent has **read-only access** during discovery (cannot write, update, delete)
- Agent can generate scripts that **write** if user approves
- Agent **never deletes** data (no delete operations allowed)
- Permissions are **scoped by user credentials** (agent has same access as user's API key)

**Audit Trail** (for compliance/debugging):
- **All user prompts** - Log every user request
- **Discovery calls** - What was discovered, which API calls were made
- **User approvals** - When user approved/rejected scripts

**Credentials Management**:
- User credentials stored in `.env` file
- Credentials only exist in **e2b environment** at runtime
- **Agent never sees credentials** - they're loaded by e2b, not passed through agent context
- No credentials in logs, no credentials in generated scripts (use environment variables)

**Safety guardrails**:
- No destructive operations without explicit user approval
- Scripts that modify data must be approved before first run
- Clear error messages when something goes wrong
- Agent explains what each script does before execution

---

## 7. Benefits

**For Business**:
- Integration without API/programming knowledge
- Iterative dialog with AI agent
- Finished, tested script at the end

**For Developer/Agent**:
- Structured knowledge about the system (README, docs, examples)
- Discovery mechanism instead of API memorization
- Best practices built into instructions

---

## 8. Implementation Status

All **critical blocking gaps** from Codex review (Section 5 in @docs/prd-codex-review-en.md) have been resolved:

### 8.1 RESOLVED ✅

#### 1. Agent Orchestration & Prompting
- [x] Model: Claude Sonnet 4.5
- [x] Role: Integration builder
- [x] Driver loading: MCP server or driver registry
- [x] Documentation: Dynamic RAG (loads what's needed)
- [x] Bootstrap flow: capabilities → README → examples → ask user → discovery → write → validate
- [x] Timing: Proactive (loads driver immediately)

#### 2. Discovery Execution Path
- [x] Execution: Agent writes mini Python scripts
- [x] Environment: e2b isolated sandbox
- [x] Credentials: User's `.env` loaded in e2b
- [x] Output format: Python dict/list structures
- [x] Error handling: Fail gracefully, inform user
- [x] Permissions: Read-only during discovery

#### 3. Error Handling & Validation
- [x] Validation: Run in e2b + user approval
- [x] Script failure: Agent fixes and retries
- [x] Approval workflow: First run requires approval, then automatic
- [x] Write operations: Always require explicit approval

#### 4. Governance & Security
- [x] Permissions: Read-only + write (if approved) + no delete + scoped by user
- [x] Audit trail: All prompts, discovery calls, user approvals
- [x] Credentials: E2B env only (agent never sees them)
- [x] Safety: No destructive ops without approval

#### 5. Driver API Contract
- [x] Minimum methods: `list_objects()`, `get_fields(obj)`
- [x] No caching in driver (agent handles caching if needed)
- [x] Rate limiting: Implementation-dependent
- [x] Error handling: Clear exceptions (ConnectionError, AuthError, etc.)

---

### 8.2 DEFERRED (Nice-to-have, not blocking) 📋

These can be addressed during implementation/iteration:

- **Learning & Optimization**: How system learns from previous runs, caching strategies
- **Multi-System Integration**: Handling 2+ drivers simultaneously, conflict resolution
- **MCP Relationship**: Exact integration with Model Context Protocol
- **Operational Model**: Production deployment, monitoring, rollback strategies
- **Metrics & Success**: KPIs, quality measurement
- **Distribution**: PyPI vs internal repo, versioning
- **Advanced features**: Webhooks, scheduling, long-running tasks

---

## 9. Next Steps

Now that all blocking gaps are resolved, we can proceed with implementation:

### Phase 1: First Driver Prototype (1-2 weeks)

1. **Build Salesforce driver** (`salesforce_driver/`)
   - Implement `Client` class with `list_objects()` and `get_fields()`
   - Write README with system overview and best practices
   - Create 2-3 example scripts (list leads, sync with DB)
   - Set up as MCP server or register in driver registry

2. **Set up e2b environment**
   - Configure isolated Python sandbox
   - Test credential loading from `.env`
   - Verify discovery scripts can run

3. **Test agent integration**
   - Agent loads driver from MCP/registry
   - Agent can run discovery scripts
   - Agent generates simple integration script
   - Agent validates script in e2b

### Phase 2: End-to-End Testing (1 week)

4. **Test with real business user**
   - Use case: "Sync leads from Salesforce to CSV"
   - Capture full dialog, discovery, script generation
   - Validate approval workflow works
   - Document pain points and improvements

5. **Iterate based on feedback**
   - Improve README/documentation based on agent behavior
   - Refine error messages and failure modes
   - Optimize RAG retrieval if needed

### Phase 3: Second Driver (1-2 weeks)

6. **Build second driver** (PostgreSQL or HubSpot)
   - Validate that driver contract is general enough
   - Test multi-system integration (Salesforce → PostgreSQL)
   - Refine architecture based on learnings

---

**Last update**: 2025-11-09 (Codex review gaps resolved)
**Status**: Ready for implementation
**Authors**: Discussion padak + Codex review + Gap resolution
