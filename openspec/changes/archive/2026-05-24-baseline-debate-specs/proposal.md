## Why

The DebateX system currently operates without formal specifications. To enable Spec-driven development (SDD) and ensure future code changes are predictable, robust, and aligned, we need to establish a persistent baseline specification library for our core features (deliberation pipeline, APIs, and storage).

## What Changes

- Add baseline specification files under the `openspec/specs/` directory to document core system mechanics.
- Register these baseline capabilities using the `spec-driven` schema so that all subsequent change proposals have an authoritative source of truth.

## Capabilities

### New Capabilities
- `core-deliberation`: Covers the 5-round deliberation council logic, provider engines (Groq/OpenRouter), fallback resiliency, and chairman synthesis.
- `api`: Covers the FastAPI router endpoints, CORS configurations, and Server-Sent Events (SSE) streaming lifecycle/payload structure.
- `storage`: Covers JSON conversation serialization schemas, file system directories, and ephemeral metadata vs persisted structures.

### Modified Capabilities
<!-- None -->

## Impact

- **Affected code**: No application code in `backend/` or `frontend/` is modified.
- **APIs**: No endpoint signature changes.
- **Dependencies**: Integrates `@fission-ai/openspec` local CLI configuration in `.agent/` and `openspec/`.
