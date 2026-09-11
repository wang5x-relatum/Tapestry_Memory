# LongMemEval Historical Evaluation

English | [中文](longmemeval.zh.md)

This document records a historical LongMemEval experiment conducted before `tapestry-memory` was established as an independent package. It is supporting evidence for the broader memory-engine work, not a benchmark claim for the current distribution.

## Recorded result

The archived result covers 90 questions:

| Measure | Correct | Total | Accuracy |
| --- | ---: | ---: | ---: |
| Overall | 73 | 90 | 81.11% |
| Knowledge update | 13 | 15 | 86.67% |
| Multi-session | 6 | 15 | 40.00% |
| Single-session assistant | 15 | 15 | 100.00% |
| Single-session preference | 9 | 15 | 60.00% |
| Single-session user | 15 | 15 | 100.00% |
| Temporal reasoning | 15 | 15 | 100.00% |

## Scope and limits

The source artifact is `results_oracle.json` from the local LongMemEval workspace. The available artifact records outcomes and recalled-item counts, but does not provide a complete reproducibility record for the package version, model, prompt, runtime configuration, or exact command. Accordingly, these figures should be treated as a historical observation under the then-current experiment setup.

The experiment predates the independent `tapestry-memory` package and must not be presented as a result produced by its current API, release, or wheel. It does not establish general performance, semantic quality, throughput, latency, or production readiness. The LongMemEval dataset and raw result files are not redistributed in this package; consult their original workspace and licensing terms for access and reuse.
