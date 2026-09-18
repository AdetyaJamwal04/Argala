---
description: Documentation-first development workflow — this project exists to learn while building, so every unit of work starts with a plan and leaves a written trail of design, decisions, and flow.
trigger: always_on
---

# Documentation-First Development

## Why this rule exists
This project began as a learning exercise as much as a build exercise. The point isn't only working code — it's a written record that explains what was built, why it was built that way, and how it actually behaves once it's running. Every agent or contributor working in this repo follows the workflow below, without exception.

## The four documents
Location: `docs/` at the project root (create it if it doesn't exist yet). All four are living documents — created once, then kept current as the project evolves. None of them is a one-and-done deliverable.

### 1. `plan.md` — written first, before any code
Before starting a new feature, phase, or non-trivial piece of work, write a detailed plan covering:
- What is being built and why
- Scope, and explicit non-goals for this unit of work
- Step-by-step approach
- Open questions or assumptions being made

Do not start writing implementation code until `plan.md` reflects the current unit of work. If the plan changes mid-flight, update the file rather than letting it drift out of sync with reality.

### 2. `design.md` — the system design
Explains how the system is structured:
- Components/modules and their responsibilities
- How they interact — boundaries, contracts, data flow between them
- Key architectural choices (patterns, frameworks, state management, etc.)

Write it at a level where someone new to the codebase could read it and understand the shape of the system without reading the code itself.

### 3. `decisions.md` — the decision log
A running log of decisions made during development and the reasoning behind them. For each entry, capture:
- What was decided
- What alternatives were considered
- Why this option won out over the others
- When it was decided (date or phase)

This is the "why" record. Append to it whenever a non-trivial decision is made — a stack choice, a pattern choice, a trade-off, a previously-deferred item getting resolved.

### 4. `flow.md` — the end-to-end application flow
Explains how the complete application actually behaves at runtime:
- The path a request or user action takes from entry point to completion
- Where control passes between components
- Error paths and edge-case handling, at a high level

Useful both as an onboarding document and as a sanity check that the design still matches what's actually running.

## Working agreement
- `plan.md` is written or updated at the **start** of a unit of work — it comes before the code, not after.
- `design.md`, `decisions.md`, and `flow.md` are updated **as work progresses** — treat updating them as part of finishing the work, not an optional follow-up.
- Keep entries concise and in plain language. The goal is to teach the reader (including future-you), not to impress anyone.
- If a decision or design choice isn't written down, treat it as not yet final.
