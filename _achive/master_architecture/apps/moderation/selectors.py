"""Provide reusable, side-effect-free domain read operations.

Responsibilities:
- Provide reusable, side-effect-free domain read operations.
- Preserve the architectural boundary and requirement traceability.

May depend on:
- The moderation domain's models and explicit cross-domain read contracts.

Must not:
- Mutate state, perform delivery, or weaken eligibility exclusions.

Requirement coverage:
- MOD requirements, as assigned in docs/TRACEABILITY.md.

Status:
- Scaffold only; implementation pending.
"""

