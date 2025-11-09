# Agent-Based Integration System - Codex Second Opinion Review

**Date**: 2025-11-09
**Reviewed Document**: @docs/prd.md (v0.1)
**Reviewed By**: OpenAI Codex (gpt-5-codex model)

---

## Overall Assessment

| Aspect | Rating | Note |
|--------|--------|------|
| **Completeness** | 🟠 LOW | Missing critical implementation details |
| **Clarity** | 🟡 MEDIUM | Vision + workflow are clear, but details aren't |
| **Actionability** | 🟡 MEDIUM | Some things can be done, but the most important parts are open |

### Summary
> "Vision, core workflow, and driver packaging ideas are clear, but agent orchestration, discovery execution, testing/validation, and safety/governance are undefined. **These gaps block a working prototype** because the agent cannot yet be instantiated or trusted to run scripts."

---

## Sections That Work ✅

These sections can lead to implementation:

- **Vision** — 10% tech, 90% productization
- **Core Concept** — before/after comparison
- **Model Workflow** — concrete example (Lead sync)
- **Driver structure** — repo layout, README, examples
- **Use Cases** — three valid examples
- **Execution environment** — e2b
- **Benefits** — clear for both business and agent

---

## 5 Critical Gaps 🚨

### 1. Agent Orchestration & Prompting ⛔ BLOCKING

**Issue**: No definition of system prompt, instruction-ingestion mechanism, or model/runtime selection.

**What's Missing**:
- What is the exact system prompt for the agent?
- How are instructions "told" to agent? (injected context vs. file reading vs. API)
- How long is onboarding between agent and library?
- What model is used? (Claude Opus? Sonnet?)
- How does agent "prepare" for a new driver?

**Why It Blocks**:
- Can't even start dialog without this
- Agent doesn't know it has instructions and driver documentation
- Can't write orchestration code

**Priority**: MUST RESOLVE FIRST

---

### 2. Discovery Execution Path ⛔ BLOCKING

**Issue**: Discovery is referenced but not specified (API surface, sandbox permissions, result format, error handling).

**What's Missing**:
- How exactly does agent run mini discovery scripts?
- What is the API between orchestration and e2b for execution?
- What is the output format of discovery (JSON? Python dict? String?)
- What are timeouts and error codes?
- What permissions does agent have on e2b? (read-only? can execute?)
- How do results get back into agent context?

**Why It Blocks**:
- Discovery is your key differentiator
- Without clear implementation, can't test or write driver interface
- Agent doesn't know how to discover system structure

**Priority**: MUST RESOLVE FIRST

---

### 3. Error Handling, Validation & Testing ⛔ BLOCKING

**Issue**: No plan for validating generated scripts, handling runtime failures, retries, or dry-run safeguards.

**What's Missing**:
- How is it validated that generated script is correct?
- Dry-run mode — how does it work?
- What testing (unit? integration? e2e)?
- What happens when script fails? Retry logic?
- How does agent verify script works?
- Approval workflow — who approves?

**Why It Blocks**:
- For "production-ready" claim, need concrete validation pipeline
- Can't run script in production without this
- Business user doesn't know how to verify it works

**Priority**: MUST RESOLVE FIRST

---

### 4. Governance, Security & Auditing 🔴 HIGH

**Issue**: Credentials, access scopes, logging, approval loops, and compliance safeguards are unspecified.

**What's Missing**:
- How are credentials securely managed during agent-run discovery?
- What are agent's access scopes? (read-only? can write? can delete?)
- Audit trail — how do you know what agent did?
- Approval loop — who and how approves generated script?
- Compliance — how are GDPR/SOC2 requirements handled?
- Secrets management — are credentials safe?

**Why It Matters**:
- Can't run in production without this
- Security risks
- Compliance issues

**Priority**: SHOULD RESOLVE

---

### 5. Driver Architecture Details 🔴 HIGH

**Issue**: Driver API contract (methods, models, session/caching, rate limiting) remains undefined.

**What's Missing**:
- Exact API Client class (what methods, parameters, return types)
- Models/DTOs — how are objects from remote systems represented?
- Error handling — what exceptions?
- Session management — how long does connection stay alive?
- Connection pooling — shared or per-instance?
- Caching layer — should there be one?
- Rate limiting — in driver or does agent handle it?

**Why It Matters**:
- Driver authors won't know what to implement
- Agent won't be able to write compatible code
- Can't test generated scripts

**Priority**: SHOULD RESOLVE

---

## Priority Open Questions

### MUST RESOLVE FIRST (blocking prototype)

#### Q1: Agent Orchestration Model
- What specific orchestration/prompting model does agent use?
  - System prompt draft?
  - Context windows?
  - Method for injecting instructions/README?
  - Target model (Opus/Sonnet)?
- **Why**: Without this, can't even start dialog or ensure agent sees instructions and driver code.

#### Q2: Discovery Execution Flow
- How exactly does agent run discovery scripts?
  - API surface for calling?
  - Sandbox permissions?
  - Return format?
  - Error handling?
- **Why**: Discovery is key differentiator; without clear implementation, can't test or write driver interface.

#### Q3: Validation & Testing Pipeline
- How is generated script validated and approved?
  - Tests (unit/integration)?
  - Dry-run mode?
  - Approval workflow?
  - What happens on failure?
- **Why**: For "production-ready" claim, need concrete validation pipeline and failure strategy.

---

### SHOULD RESOLVE (enables implementation)

#### Q4: Driver API Contract
- What is minimal API contract for `Client` class?
  - Mandatory methods (signatures)?
  - Expected responses?
  - Error types?
  - Rate limit behavior?
- **Why**: Both driver authors and agent need stable interface, otherwise can't write compatible scripts.

#### Q5: Governance & Security Model
- How will governance/security be handled?
  - Credential scoping?
  - Audit logs?
  - Approvals?
  - Secrets handling?
- **Why**: Without these rules, security risks exist and solution can't be used on real data.

---

### CAN DEFER (not blocking, but important)

#### Q6: MCP Relationship & Metrics
- What will be relationship to MCP or other standards?
- How will success metrics be measured?
- **Why**: Important for long-term strategy, but doesn't block first prototype if other areas are defined.

---

## Recommended Immediate Actions (Before Implementation)

1. **Specify Agent Orchestration Blueprint**
   - System prompt draft
   - Context window strategy
   - Method for injecting instructions/README
   - Model selection (Opus/Sonnet)
   - Agent role definition

2. **Design Discovery Execution Interface**
   - API from agent orchestration to e2b
   - Output format (JSON schema?)
   - Timeouts and error codes
   - Permission model (what can agent execute?)

3. **Define Minimal Driver API Contract**
   - Table of mandatory Client class methods
   - DTOs/Models structure
   - Authentication handling
   - Rate limiting behavior
   - Error types and handling

4. **Write Validation and Security Process**
   - Testing strategy (unit/integration/e2e)
   - Dry-run mode specification
   - Approval workflow
   - Audit logging
   - Secret management
   - Access scopes

---

## Suggested Document Improvements

### 1. Section 4.1 — Driver / Library

**Suggestion**: Add table of mandatory `Client` class methods (signatures, expected responses, error behavior) and description of models/DTOs.

**Example**:
```markdown
#### Required Client Methods

| Method | Signature | Returns | Errors |
|--------|-----------|---------|--------|
| `list_objects()` | `() -> List[str]` | List of object names | `ConnectionError`, `AuthError` |
| `get_fields(obj)` | `(str) -> List[Field]` | List of Field objects | `ObjectNotFoundError`, `ConnectionError` |
| `get_relationships(obj)` | `(str) -> Dict[str, str]` | Relationship map | `ObjectNotFoundError` |
```

**Rationale**: Enables driver authors to implement compatible libraries and agents to rely on consistent API.

---

### 2. Section 4.3 — Agent Orchestration

**Suggestion**: Expand on specific prompting pipeline: system prompt, role prompt, where instructions are loaded, how agent prepares for new driver.

**Example Content**:
```markdown
#### Orchestration Flow

1. User invokes agent with use case
2. Agent loads driver (if specified) or asks which system
3. Agent reads driver README into context
4. Agent reads examples/ into context
5. Agent reads driver API reference
6. Agent has context: [System Prompt] + [Driver Docs] + [User Input]
7. Agent starts dialog with user
```

**Rationale**: This section is currently only descriptive; without concrete flow, can't assign tasks to orchestration team.

---

### 3. Section 6 — Architecture

**Suggestion**: Add security and governance subsection (access scoping, audit logs, approval steps, secrets handling).

**Example**:
```markdown
### Security & Governance

**Access Scoping**:
- Agent has read-only access to target system APIs during discovery
- Agent generates scripts but cannot execute them without approval
- Business user must approve scripts before e2b execution

**Audit & Logging**:
- Every discovery call is logged (timestamp, query, results)
- Every generated script is versioned and tracked
- User approvals are recorded with reason

**Secrets Management**:
- Credentials are stored in .env
- Agent never logs or stores credentials
- Scripts receive credentials at runtime from environment
```

**Rationale**: For production environment, document must clearly define how data and access are protected.

---

### 4. Section 8.2–8.3 — Open Topics

**Suggestion**: Transform main open questions into concrete decisions with owner and deadline; distinguish blocking vs. nice-to-have.

**Example**:
```markdown
### Open Decisions (Blocking Prototype)

| Decision | Owner | Target Date | Status |
|----------|-------|-------------|--------|
| Agent orchestration blueprint | [TBD] | 2025-11-15 | OPEN |
| Discovery API specification | [TBD] | 2025-11-15 | OPEN |
| Driver API contract | [TBD] | 2025-11-16 | OPEN |
| Testing & validation process | [TBD] | 2025-11-17 | OPEN |

### Open Questions (Can Defer)

- MCP relationship
- Metrics & success KPIs
- Learning & optimization from prior customizations
```

**Rationale**: List is useful, but in form of action items better guides progress toward prototype.

---

### 5. Section 9 — Next Steps

**Suggestion**: Expand with explicit deliverables and completion criteria.

**Example**:
```markdown
## 9. Next Steps

### Phase 0: Blocking Decisions (Nov 9-17)

1. **Draft Agent Orchestration Blueprint**
   - Deliverable: `docs/agent-orchestration-blueprint.md`
   - Criteria: System prompt, context injection method, model choice documented
   - Owner: [TBD]

2. **Specify Discovery Execution API**
   - Deliverable: `docs/discovery-api-spec.md`
   - Criteria: Complete API contract, error codes, examples
   - Owner: [TBD]

3. **Define Driver API Contract**
   - Deliverable: `docs/driver-api-contract.md`
   - Criteria: Client method signatures, DTOs, error handling specified
   - Owner: [TBD]

4. **Design Testing & Validation**
   - Deliverable: `docs/testing-validation-spec.md`
   - Criteria: Testing strategy, dry-run behavior, approval workflow
   - Owner: [TBD]

### Phase 1: Prototype First Driver (Nov 18+)

1. **Prototype Salesforce Driver**
   - Deliverable: `salesforce_driver/` (working package)
   - Criteria: Implements API contract, examples work, agent can use it
   - Owner: [TBD]

2. **Test Agent + Driver Integration**
   - Deliverable: Test script showing agent ↔ driver interaction
   - Criteria: Agent can discover Lead object, generate simple script
   - Owner: [TBD]

3. **Test with Business User**
   - Deliverable: Recording of interaction
   - Criteria: Business user can ask for integration, gets working script
   - Owner: [TBD]
```

**Rationale**: Current list is too general and doesn't say when steps can be considered complete.

---

## Key Takeaways

### What's Strong
✅ Business vision is clear
✅ Driver architecture makes sense
✅ Workflow example is compelling
✅ Use cases are realistic

### What's Blocking
⛔ Agent orchestration undefined
⛔ Discovery execution unspecified
⛔ Testing/validation pipeline missing

### What You Need to Do NOW
1. Answer the 3 MUST-RESOLVE questions
2. Create 4 supporting documents (orchestration, discovery API, driver contract, testing)
3. Only then start coding the first driver

### Timeline Estimate (Codex Opinion)
- Phase 0 (decisions): 1 week
- Phase 1 (prototype): 2-3 weeks
- Phase 2 (refinement): ongoing

---

## Codex Recommends

Before you write a single line of implementation code, you need these 4 documents:

1. **Agent Orchestration Blueprint** — How agent gets instructions, what's the system prompt
2. **Discovery API Spec** — How agent calls discovery and gets results back
3. **Driver API Contract** — What Client class methods must exist
4. **Testing & Validation Spec** — How you validate that scripts work

Once these are defined, implementing the first Salesforce driver becomes straightforward.

---

**Review Date**: 2025-11-09
**Reviewer**: OpenAI Codex (gpt-5-codex)
**Status**: Complete
**Confidence**: High (blocking items are real, actionable)
