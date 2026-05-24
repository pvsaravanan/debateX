## Context

To enhance the depth, specialization, and cognitive diversity of the DebateX council, we are introducing cognitive roles for each council member. By assigning specialized cognitive personalities (Reasoner, Fact-Checker, Devil's Advocate, Steelmanner, Chairman) that rotate and receive unique system prompts based on the query type, the council's responses will be more specialized and accurate.

## Goals / Non-Goals

**Goals:**
- Implement a type-safe `backend/roles.py` module containing the `RoleAssignment` dataclass.
- Build a robust role allocator supporting dynamic list of models (of any size) and five query types (technical, creative, factual, ethical, math).
- Build a deterministic rotation mechanism using a `query_index` to shift the models.
- Support specialized system prompts customized per role and query type.

**Non-Goals:**
- This module is design-isolated; integrating the module into the main debate streaming pipeline inside `debate.py` is out of scope for this specific proposal (but the module will be fully ready and tested for immediate integration).

## Decisions

### Decision: Dataclass-based Return Structure
We define the output structure using a standard Python `@dataclass`.
- *Rationale*: A dataclass provides clean type annotations, field names, and high readability for any caller integrating the role allocator.

### Decision: Shifting/Circular Rotation
We use `query_index` to calculate a shift index: `shift = query_index % len(models)`, then shift the model array: `models_rotated = models[shift:] + models[:shift]`.
- *Rationale*: Shifting ensures that roles rotate deterministically across subsequent queries, giving different models a chance to act as Chairman, Devil's Advocate, etc., preventing bias.

### Decision: Role Allocation Ordering and Fallback
We prioritize core roles when fewer than 5 models are present. The order of assignment from the rotated array is:
1. `Chairman` (1 model)
2. `Devil's Advocate` (1 model)
3. `Reasoner` (1 model)
4. `Fact-Checker` (1 model)
5. `Steelmanner` (1 model)
6. `Reasoner` (additional models, up to 2-3)
- *Rationale*: If `N < 5`, we prioritize Chairman, Devil's Advocate, and Reasoner as they are the most critical components of a dialectic debate.

## Risks / Trade-offs

- **[Risk] High Prompt Token Size** → *Mitigation*: Keep role-specific system prompts concise, descriptive, and focused on clear instructions rather than excessive examples.
