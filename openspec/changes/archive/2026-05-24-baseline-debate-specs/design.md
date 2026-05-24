## Context

DebateX is a self-hosted, multi-LLM deliberation system designed to produce high-confidence answers. Currently, there is no formal spec layer documenting its components, which makes the repository behavior harder for AI agents to follow accurately. OpenSpec will serve as our spec layer.

## Goals / Non-Goals

**Goals:**
- Formulate precise, verifiable, and testable specifications for the core 5-round deliberation council, standard FastAPI REST and SSE endpoints, and JSON conversation storage.
- Document and baseline existing codebase functionality before making any future code modifications.

**Non-Goals:**
- We are NOT modifying or refactoring any application source code in `backend/` or `frontend/` in this proposal.
- We are NOT introducing any database migrations or new external runtime library dependencies.

## Decisions

### Decision: Grouping Specs by Capabilities
We split specifications into three distinct files: `core_deliberation.md`, `api.md`, and `storage.md`.
- *Rationale*: Grouping specs by functional layers ensures the system's requirements remain highly modular, clean, and easily queryable by LLM context windows.

### Decision: Zero Application Code Changes in Baseline
No python or React code is touched during this spec definition.
- *Rationale*: Keeping spec definition isolated from application code changes ensures a pure baseline documentation commit, preventing regression issues.

## Risks / Trade-offs

- **[Risk] Out of Sync Documentation** → *Mitigation*: Ensure any subsequent code modifications always start with an OpenSpec change proposal that updates the active specification, followed by archiving the change to merge deltas into the `openspec/specs/` folder.
