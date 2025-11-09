# Agent-Based Integration System - Research

## Original Concept (Conversation Transcript)

**Date:** 2025-11-09

---

I'm developing a system that I call a **next-generation data connector**. Here's how it works: when you write an integration for Salesforce that's customized, a tremendous amount of energy goes into ensuring that the production solution for that connector works well for all these customized situations.

Meanwhile, an SDK or driver for Salesforce itself is simply straightforward and consistent - it's a set of instructions on how to call the API. Typically, it would be a Python file that gets included in a Python script that does the work.

### Core Idea: 10% vs 90%

I believe that if **10% is the actual technical logic** of the integration, then **90% is productization** - making it work for people and enabling them to use it on "their unique Salesforce installation".

And those 90% should be replaceable by an **agentic system**. This would work by leveraging how Claude Code is capable of iteratively finding solutions forward.

### How It Would Work

I'm thinking I would give it a **Python client** or some **driver** or SDK. SDK might be too complex... just a Python client. The Python client can use an SDK internally, but what's exposed to the Agent is **one file** plus some small instructions. With these, Claude would be able to use that particular system and find the right solution.

It's about the **agent generating code on the fly** that relies on that driver or client, and that then becomes the **config**.

So essentially, when I tell it "I want to download [something] from Salesforce", it uses the client to do **discovery** - what's in that Salesforce, understands relationships, and **writes an ad-hoc script** that does what's needed and relies on that client.

And instead of the config being some JSON, it's **Python**. Python does what the user wanted.

### Key Questions to Explore

Now for the critical part:

1. **What exactly needs to go into the driver or client?**
2. **How does this differ from MCP?**
3. **Isn't the idea really that Salesforce has an MCP server** and what I care about isn't the driver itself, but **building next-generation data connectors**?
4. Maybe it's within MCP, but what seems key to me is that **AI needs to assemble a script that does the specific thing using the driver or MCP**.

### Research Goals

I want to explore this, give it some shape:

- What all needs to be **designed, thought through, and covered**
- Someone might **already be doing** this or articles might be written about it
- I want to **define the architecture of the driver**

---

## Concept Refinement

### Technical Details

**Discovery Mechanism:**
- Agent performs introspection via API (metadata/schema endpoints)
- Discovers data source structure at runtime
- Discovery is dynamic, not static

**Relationship to MCP (Model Context Protocol):**
- Need to explore the relationship between this concept and MCP
- Could be a complementary approach or using MCP as a foundation
- Research question: How does this approach differ/overlap with MCP?

**Client Structure:**
- Python module/package (not necessarily one file)
- Has a clear entry point - a method that provides initial instructions to the agent
- Entry method returns a **combination**: structured data (schema, capabilities) + natural language explanation

**Usage Instructions:**
- README.md describing the client
- Example scripts (examples/)
- Entry method in Python client that returns to the agent:
  - What the client can do (capabilities)
  - How to use it (API reference)
  - Structure of available data/operations

**Agent Output:**
- **Standalone Python script** - user can run directly (`python script.py`)
- **Integrable code** - can be loaded into a running system/orchestrator
- Flexible based on use-case

**System Scope:**
- **General framework** for various data sources:
  - SaaS systems (Salesforce, HubSpot, ...)
  - Databases (PostgreSQL, MongoDB, ...)
  - REST/GraphQL APIs
  - Cloud services (AWS, GCP, ...)
- Goal: unified architecture for all connector types

### Key Principles

1. **10% technique, 90% adaptation** - agent handles customization instead of hardcoding
2. **Runtime discovery** - agent discovers structure at runtime via API
3. **Code as config** - generated Python script instead of JSON config
4. **Generality** - framework for any data source
5. **Flexible output** - standalone and integrable
