# Machine contracts

`contracts/` is the coordination surface for independently changing components. Files here are owned by the contract owner/integrator of a wave and become read-only to consumer tasks after freeze.

Bootstrap schemas are **drafts for CP-00**. They deliberately cover identity/state/error and engine package boundaries before implementation. OpenAPI endpoints/events grow per vertical slice instead of being guessed wholesale up front.
