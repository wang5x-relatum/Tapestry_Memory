# Project Status and Evidence

English | [中文](project-status.zh.md)

## Current state

`tapestry-memory` is a stage-2 standalone Python library: an offline, namespace-scoped SQLite graph memory engine with no third-party runtime dependencies. The package is maintained by MetaRelatum (越迹科技（宁波）有限公司) and is licensed under Apache-2.0.

The public package currently provides graph storage, directed relationships, bounded deterministic BFS retrieval, provenance round-tripping, logical deletion, transaction rollback, and database reopening. The host application remains responsible for authentication, consent, write policy, conflict decisions, source freshness, response generation, and action safety.

## Verification record

- Python 3.10+ requirement checked.
- Runtime dependencies: none.
- Wheel and sdist built locally with the license included.
- Clean wheel installation and offline example validation passed.
- Unit and contract regression suite: 32/32 passed at the latest documentation update.
- `git diff --check`: passed.
- Documentation checks remain a separate gate; stale bilingual manifest entries for files outside the latest change set must be refreshed during the next documentation maintenance pass.

## Historical LongMemEval evidence

A pre-package LongMemEval experiment is recorded separately in [Historical LongMemEval evaluation](evaluations/longmemeval.md). It covers 90 questions with 73 correct (81.11%). Because it predates the standalone package and lacks a complete reproducibility record, it is historical supporting evidence—not a benchmark result, performance guarantee, or claim about the current wheel.

## Boundaries and next steps

This repository does not claim automatic relation extraction, semantic truth validation, conflict arbitration, synchronization, distributed operation, arbitrary-scale performance, or production readiness. The next release decision should preserve the separation between package behavior, historical experiments, and broader Relatum research components.
