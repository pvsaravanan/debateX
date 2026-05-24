## Why

The LLM council currently treats all models as generic nodes with identical default prompts (except for the anonymization and chairman roles). Assigning distinct cognitive roles (Reasoner, Fact-Checker, Devil's Advocate, Steelmanner, Chairman) tailored to the query type will allow for deeper, more specialized debates and higher-quality syntheses.

## What Changes

- Create a new module `backend/roles.py` implementing role allocation, rotation, and custom system prompts.
- Define a structured `RoleAssignment` dataclass returned from the allocation process.
- Map query types (technical, creative, factual, ethical, math) to specialized cognitive prompts.

## Capabilities

### New Capabilities
- `dynamic-roles`: Assigns and rotates council roles (Reasoner, Fact-Checker, Devil's Advocate, Steelmanner, Chairman) for any list of models and query types, generating custom system prompts.

### Modified Capabilities
<!-- None -->

## Impact

- **Affected code**: Adds `backend/roles.py`.
- **APIs**: Standalone module; no immediate breaking change to the existing endpoints unless integrated.
- **Dependencies**: Uses standard Python `dataclasses` and `hashlib`.
