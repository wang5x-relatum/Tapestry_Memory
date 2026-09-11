# rmc-memory

English | [中文](README.zh.md)

**A relational memory engine for traceable, cross-session agent memory.**

RMC stands for Relational Memory Core. The project is named `rmc-memory`; its planned Python import name is `rmc_memory`.

## Current status

This repository is in contract design. Bilingual documentation and documentation checks are available; the standalone memory engine is not implemented, and no installation or usage readiness is claimed. `0.1.0` is the planned first release, not a published version. Package-name availability, license, rights holder, and public hosting address must be confirmed before publication.

## Product boundaries

The target is an embedded graph memory library built on the Python standard library and SQLite: the host decides which nodes and relationships to write, the engine organizes storage and retrieval, and the host model generates answers. It is not a language model, complete agent platform, knowledge-base crawler, or robot control system.

The core targets no third-party runtime dependencies and no network access by default. An optional matching strategy does not imply enabling embeddings by default; a test mock provides no semantic capability. There are no standalone-package performance, isolation, or benchmark results to promise yet.

## Start here

- [Use-case draft](docs/use-cases.md): companionship, customer service, education, robotics, and selection boundaries; awaiting user review.
- [v0.1 contract draft](docs/v0.1-contract.md): scope, data lifecycle, and stage acceptance; not an implemented interface.
- [Bilingual documentation](docs/i18n/README.md): equal language authority, three-file pairing, and checking limits.

## Local documentation development

Python 3.10 or newer is required. Run from the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_docs.py
```

These commands validate documentation tooling and pairing consistency, not the unimplemented memory engine. Code, APIs, and behavior documentation should change together: define acceptance conditions first, then validate implementation through real public entry points.

## Communication and publication

During this stage, local documents are reviewed through existing collaboration channels. No Discord or other community platform requiring additional cross-border network-access tools is required, and no corporate email address, group code, or support channel is invented. Confirm an accessible feedback channel before publication; core use must not depend on a community account or an online documentation site.

Public release has not been authorized, and no license has been selected; an open-source usage license must not be assumed. A future documentation site will be generated from repository sources rather than maintaining a second set of technical content. Validate installation artifacts before publishing those same verified artifacts.
