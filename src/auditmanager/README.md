# Backend source

Python control plane lives here as a modular monolith. Initial skeleton contains boundary READMEs, not speculative framework classes.

Dependency direction inside a context is `api/consumer → application → domain ← ports ← adapters`. Cross-context use goes through public application ports/events/read models, not internal ORM/repository imports.
