# tapestry-memory

English | [中文](README.zh.md)

**A relational memory engine for traceable, cross-session agent memory.**

The project and distribution name is `tapestry-memory`; the Python import name is `tapestry_memory`.

## Current status

This repository is in stage 2: local core implementation and artifact validation of the standalone memory library. This is not a published package. Unit, contract, and artifact acceptance are reported separately from documentation checks; this page does not replace those reports. Wheel/sdist installation and offline example validation passed locally; `0.1.0` is the intended version, not a published version. Package-name availability, license, rights holder, and public hosting address must be confirmed before publication.

## Product boundaries

The core is an embedded graph memory library built on Python's standard library and SQLite: the host decides which nodes and relationships to write, the engine organizes storage and retrieval, and the host model generates answers. It is not a language model, complete agent platform, knowledge-base crawler, or robot control system.

The stage-2 contract requires no third-party runtime dependencies, offline operation by default, and no imports from Relatum internals. Omitted namespace means `default`; explicit `None`, empty strings, and whitespace-only strings are rejected. Node identity is a scoped UUID, not a content hash. Retrieval is bounded, deterministic BFS with observable budget exhaustion. Scoped logical deletion, transaction rollback and database reopening, and JSON provenance round-tripping are acceptance requirements, not benchmark claims.

## Limitations

Stage 2 does not provide automatic relation extraction, automatic conflict arbitration, multi-device synchronization, distributed service operation, or arbitrary-scale guarantees. It does not impose 500-character truncation, promise GDPR-complete deletion, or enable embeddings by default. Namespace isolation is not host authentication or authorization. Logical deletion does not erase external source documents, host logs, backups, or storage media. No standalone-package performance or semantic-quality result is claimed.

## Start here

- [Use-case draft](docs/use-cases.md): companionship, customer service, education, robotics, and selection boundaries; awaiting user review.
- [v0.1 contract](docs/v0.1-contract.md): stage-2 behavior, data lifecycle, and acceptance boundaries.
- [Offline example](examples/basic_usage.py): synthetic add, edge, retrieve, delete, and reopen flow using the public API.
- [Bilingual documentation](docs/i18n/README.md): equal language authority, three-file pairing, and checking limits.

## Local development checks

Python 3.10 or newer is required. Run from the repository root:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/check_docs.py
```

Running a command is not an acceptance result. Report unit and contract test outcomes with their scope and counts; documentation checks are separate and do not verify runtime behavior or translation quality. API examples are omitted until the implementation's public interface is reconciled with the contract. Changed bilingual documents require human review before recording new hashes with `--record ... --reviewed`; stale hashes remain visible until that review is complete.

## Communication and publication

During this stage, local documents are reviewed through existing collaboration channels. No Discord or other community platform requiring additional cross-border network-access tools is required, and no corporate email address, group code, or support channel is invented. Confirm an accessible feedback channel before publication; core use must not depend on a community account or an online documentation site.

Public release has not been authorized, and no license has been selected; an open-source usage license must not be assumed. A future documentation site will be generated from repository sources rather than maintaining a second set of technical content. Stage 2.4 must validate installation artifacts before any later authorized publication of those same verified artifacts.
