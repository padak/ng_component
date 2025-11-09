# Agent-Based Integration System - Product Requirements Document

**Status**: In Development (v0.1 - from discussion 2025-11-09)

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

**What it is**: Python package for integrating a specific system (Salesforce, HubSpot, PostgreSQL, ...).

**Structure** (draft):
```
salesforce_driver/
├── main.py              # Entry point, Client class
├── README.md            # "Hi, this is the Salesforce driver"
├── examples/            # Sample scripts (certified queries)
│   ├── list_leads.py
│   ├── create_opportunity.py
│   └── sync_with_external_db.py
├── docs/                # More detailed documentation
│   ├── SALESFORCE_OVERVIEW.md
│   ├── API_REFERENCE.md
│   └── COMMON_PATTERNS.md
└── src/                 # Implementation details
    ├── client.py
    ├── models.py
    └── utils.py
```

**Key capabilities**:
- `Client` class with methods for working with API
- **Discovery mode**: Agent can call mini scripts to discover structure
  - `client.list_objects()` — what objects exist?
  - `client.get_fields(object_name)` — what fields does an object have?
  - `client.get_relationships(object_name)` — how do objects relate?
- **Documentation**: README + docs/ so agent knows how it works
- **Examples**: examples/ with certified queries so agent has templates

**Authentication**:
- Business user puts credentials in `.env`
- Driver reads them from `os.environ`
- Agent knows from instructions that it expects them in `.env`

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

**What the agent does**:
1. Business user states their use case
2. Agent reads library instructions/documentation
3. Agent asks follow-up questions about requirements
4. Agent runs mini discovery scripts when it needs info
5. Agent writes complete integration script
6. Agent shows it to business user and iterates

**Open**: How does the agent "prepare" for work? Are instructions automatically injected? Manually? Does it read them from the repo?

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

### Modular per system
- Each external system has its own driver (`salesforce_driver/`, `hubspot_driver/`, ...)
- Agent picks the right one based on user request
- Later, drivers can be consolidated into a more universal system

### Execution Environment
- Scripts run in **e2b** (isolated Python environment)
- Business user takes the final script and can deploy it wherever they want

### Credentials Management
- Business user puts credentials in `.env`
- Script reads them at runtime
- Agent knows from instructions that this is how it works

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

## 8. Complete Checklist of Topics

Here's everything we discussed or mentioned — what's covered, what's open.

### 8.1 CLEARLY COVERED ✅

#### Architecture & Design
- [x] Modular approach (driver per system)
- [x] Python package for import
- [x] Entry point (`main.py`)
- [x] Repo structure (draft): examples/, docs/, src/
- [x] Separation: Driver library vs. agent instructions
- [x] Execution environment: e2b

#### Driver Capabilities
- [x] Client class API
- [x] Discovery methods: `list_objects()`, `get_fields()`, `get_relationships()`
- [x] Metadata/schema endpoints
- [x] Runtime discovery (dynamic, not static)

#### Agent Workflow
- [x] Business user → Agent dialog
- [x] Agent asks about requirements
- [x] Just-in-time discovery (agent runs mini scripts when needed)
- [x] Agent writes script
- [x] Iterative process (agent ↔ user)
- [x] Output: Production-ready Python script

#### Instructions & Documentation
- [x] README.md in library
- [x] docs/ folder with details
- [x] Examples/certified queries
- [x] Senior→junior onboarding mentality

#### Credentials & Auth
- [x] Business user puts in `.env`
- [x] Driver reads from `os.environ`
- [x] Agent knows this is how it works

#### Use Cases
- [x] Data sync (Lead→Campaign)
- [x] Analysis (which campaign leads to deals)
- [x] Multi-system integration

---

### 8.2 COVERED, BUT COULD BE MORE SPECIFIC ⚠️

#### Discovery Mechanism
- [x] Principle: just-in-time discovery
- [ ] Specifically: What does a mini script that the agent runs look like?
- [ ] Specifically: How do discovery results get back into agent context?
- [ ] Specifically: When does discovery run (everything? only what's needed)?

#### Agent Getting Instructions
- [x] Instructions are in library README + docs
- [ ] **SPECIFICALLY SOMEHOW**: How does agent get instructions? Injected? Reads files? Passed as prompt?
- [ ] How long can instructions be (context window limit)?
- [ ] Priority — what must agent read vs. what can it ignore?

#### README Navigation
- [x] Mentioned Claude Skills model
- [ ] **SPECIFICALLY**: What should README look like so agent knows what to do next?
- [ ] Structure: what in README vs. what in docs/?

#### Iterative Improvement
- [x] Mentioned: "author will hit problems and add to instructions"
- [ ] **SPECIFICALLY**: How does feedback from agent get back to author?
- [ ] How do instructions get updated?

#### Scheduling & Long-Running Tasks
- [x] Mentioned in example (APScheduler)
- [ ] How should scheduling be handled? Part of driver? Or agent?

#### Webhook Support
- [x] Mentioned: "trigger action if they supported webhooks"
- [ ] How should webhooks be integrated?

#### Rate Limiting & API Throttling
- [x] Mentioned in instructions
- [ ] How is it specifically handled? In driver? Retry logic?
- [ ] What's the default behavior?

---

### 8.3 OPEN QUESTIONS / NOT ADDRESSED ❌

#### Agent Orchestration & Prompting
- [ ] What is the exact system prompt for the agent?
- [ ] How are instructions communicated to agent? (Injected context? File-based? API call?)
- [ ] How long is onboarding between agent and library?
- [ ] What model is used? (Claude Opus? Sonnet?)
- [ ] How does agent "prepare" for a new driver?

#### Error Handling & Resilience
- [ ] What if discovery fails? (API down, auth failed, schema changed)
- [ ] What if agent writes a bad script?
- [ ] What if script fails during execution?
- [ ] Retry logic — should it be in driver?
- [ ] Fallback strategy?

#### Testing & Validation
- [ ] How is it validated that generated script is correct?
- [ ] Dry-run mode?
- [ ] Unit tests for generated scripts?
- [ ] Integration tests with real system?
- [ ] How does agent verify script works?

#### Governance, Safety & Auditing
- [ ] How do you know what agent did? (logs, audit trail)
- [ ] Approval loop — who approves script before it runs?
- [ ] Security: What if agent writes script that would delete all data?
- [ ] Permissions scoping — should agent have limited access?
- [ ] Compliance — how is GDPR/auditing handled?
- [ ] Secrets management — are credentials securely handled?

#### Learning & Optimization
- [ ] How does system learn from previous customizations?
- [ ] Caching? (so same data isn't pulled repeatedly)
- [ ] How do instructions improve based on learnings?
- [ ] How are instructions updated from failure feedback?

#### Multi-System Integration
- [ ] How does agent use 2+ drivers?
- [ ] How are different auth methods handled?
- [ ] How is sync decided (realtime? batch? event-based)?
- [ ] How are conflicts managed during sync?

#### Driver Architecture Details
- [ ] Exact API Client class (what methods, what parameters)
- [ ] Models/DTOs — how are objects from remote systems represented?
- [ ] Session management — how long does connection stay alive?
- [ ] Connection pooling?
- [ ] Caching layer in driver?
- [ ] Rate limiting handling — built-in, or agent handles it?

#### Certified Queries / Examples
- [ ] How are "certified queries" defined?
- [ ] Who writes them? (framework author? domain expert?)
- [ ] How long can they be? (to fit in agent's context)
- [ ] How are they structured? (by complexity? by use case?)
- [ ] How does agent choose the right example?

#### Documentation Strategy
- [ ] How is README structured for agent?
- [ ] What must be in README vs. docs/ vs. examples/?
- [ ] What's the preferred format? (Markdown? Structured? Code comments?)
- [ ] How detailed should documentation be? (API reference? Tutorials?)

#### MCP Relationship
- [ ] What is the relationship to Model Context Protocol (MCP)?
- [ ] Do we use MCP as base? Complementary? Separate?
- [ ] How is this different from Salesforce MCP server?
- [ ] Should we build on MCP instead of our own solution?

#### Operational Model
- [ ] Where do generated scripts run in production?
- [ ] How are they monitored? (logs, errors, success)
- [ ] How are they deployed? (containerized? Scheduled job?)
- [ ] Rollback strategy?
- [ ] Driver upgrade — how does it propagate to running scripts?

#### Metrics & Success
- [ ] What are success metrics? (integration time? accuracy? uptime?)
- [ ] How is quality of generated scripts measured?
- [ ] How is cost measured?

#### Deployment & Distribution
- [ ] How are drivers distributed? (PyPI? Internal repo? Git submodule?)
- [ ] Versioning strategy?
- [ ] Backward compatibility?

#### Certified Queries Caching
- [ ] Can scripts be cached for future use?
- [ ] How is it detected that we can reuse?
- [ ] How are they parameterized (user inputs)?

---

## 9. Next Steps

1. **Prototype one driver** (Salesforce) — try out the structure
2. **Experiment with agent orchestration** — how to pass instructions to agent
3. **Test with business user** — does it work as intended?
4. **Iterate** based on learnings

---

**Last update**: 2025-11-09 (from discussion)
**Authors**: Discussion padak + Codex second opinion
