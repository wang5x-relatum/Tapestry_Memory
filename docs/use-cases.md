# Use cases

English | [中文](use-cases.zh.md)

Status: draft awaiting user review. This document describes target applications and suggested acceptance checks, not deployed customer cases, implemented features, or industry compliance certifications. Implementation boundaries belong to the [v0.1 contract](v0.1-contract.md).

## Positioning in one sentence

When an agent needs to connect experiences across time and topics rather than retain only the latest conversation turns, tapestry-memory can serve as an external relational memory layer. The host controls writing, permissions, and responses; the engine handles graph storage and bounded retrieval. These responsibilities must remain distinct.

A memory node can represent an event, an explicit preference, or a confirmed fact; an edge can represent a host-supplied relationship. The engine must not be advertised as automatically identifying truth, understanding every relationship, or guaranteeing that nothing is forgotten. A provenance reference supports tracing, not proof of truth.

## Scenario overview

| Scenario | Useful memory | Intended value | Does not replace |
| --- | --- | --- | --- |
| Companion products | User-confirmed forms of address, preferences, shared experiences, and follow-up topics | Reduce repeated introductions and maintain cross-session continuity | Therapy, crisis response, or emotional-dependency design |
| Customer-service agents | Authorized ticket history, troubleshooting steps, device relationships, and unresolved issues | Continue previous service with traceable context | CRM, live order systems, permission systems, or business sources of truth |
| Educational agents | Learning goals, demonstrated concepts, relationships between mistakes, and recent feedback | Select relevant explanations and exercises from learning history | Academic verdicts, psychological profiles, formal grading, or teacher judgment |
| Robot interaction | Permitted forms of address, interaction preferences, and continuous experiences across devices | Preserve conversational background when changing interaction devices | Motion control, safety planning, real-time perception, or proof of consciousness |

## Companion products: continuity without dependency

Example: a user previously preferred short bedtime stories and later volunteered a travel experience. When that trip comes up again, the host retrieves the related experience and storytelling preference as sourced context for the model instead of placing all history into the prompt.

Write consented preferences and useful events. A momentary emotion inference, an unconfirmed personality label, or a model-invented fact should not become persistent user memory directly. When the user changes their mind, the host confirms the relationship between old and new information; the engine must not be assumed to resolve conflicts automatically.

Acceptance focuses on correct cross-session references, updated preferences replacing old recommendations, and deleted information no longer resurfacing. Measure false memories, not just retained memories. Let users inspect, correct, delete, or disable memory; do not use memory to manufacture exclusivity or pressure retention.

## Customer service: remember the process, query live business facts

Example: a user returns about a device fault. The host first authenticates and authorizes access, reads the latest ticket and warranty status, then uses memory to supply previous troubleshooting steps and related symptoms. Responses should distinguish current business facts from historical service records.

Customer records and shared knowledge require explicit scopes. A namespace is a library-level data scope that still needs validation, not a replacement for host authentication and authorization. Cross-customer traversal, cross-scope deduplication of identical content, and cross-scope deletion need dedicated tests; do not deploy shared-database multi-tenant service before these safety boundaries pass.

Acceptance focuses on continuing the same issue, avoiding obsolete policies presented as current rules, preventing customer-to-customer leakage, and locating sources. Discounts, refunds, and order changes remain business-tool operations governed by permissions; memory cannot authorize them.

## Education: record learning without labeling the learner

Example: a learner can add fractions but repeatedly omits units in conversion exercises. The host connects observed exercise outcomes to concepts and previous explanations, retrieving relevant difficulties and explanations that worked when generating the next exercise.

Memory should distinguish learner statements, exercise evidence, and model inference, retaining timestamps and correctable sources. One mistake must not become a permanent label of poor ability. Use involving minors requires guardian consent where applicable, data minimization, and retention management under relevant law; the product implements these mechanisms, not the library automatically.

Acceptance focuses on citing actual exercises, avoiding repeated ineffective explanations, honoring corrected mastery records, and allowing teachers or learners to correct records. Changes in answer accuracy alone do not establish improved learning outcomes; independent evaluation is needed.

## Robotics: interaction memory, not an entire soul

Example: a user switches from a desktop assistant to a home robot and expects earlier topics and forms of address to continue. After checking identity and device permissions, the host uses the same authorized memory scope or explicitly imports permitted data; the engine does not synchronize devices itself.

Where a product uses “soul” to describe persistent identity and interaction style, tapestry-memory can be its memory component, but does not include identity policy, value policy, an emotional system, or complete behavior orchestration. The host owns perception reliability, identification of multiple people, synchronization, and conflict resolution.

Acceptance focuses on traceable experiences after changing models or devices, separation between users sharing a device, and persistence after offline reopening. Physical actions must pass independent safety controls; a historical permission to approach does not replace current obstacle detection and consent.

## Integration pattern and responsibilities

Recommended flow: obtain consent and scope → select and confirm content → write nodes and relationships → retrieve within bounds for a question → host checks provenance and freshness → model generates → correct or delete as needed. This is integration guidance, not an implemented API example.

| Layer | Responsibility |
| --- | --- |
| Product and host | Authentication, authorization, consent, sensitive-data policy, write extraction, conflict decisions, retention, response safety, and action safety |
| Target memory engine | Scoped storage, relationship traversal, provenance metadata round-tripping, persistence, and an explicit logical-deletion contract |
| External systems | Order and knowledge sources of truth, original-document access, backups, device synchronization, and optional model or vector services |

Deleting a graph node does not automatically delete external source documents, logs, or backups; provenance metadata does not grant access to original content. Important answers should still consult business sources of truth: previously stated does not mean currently correct.

## Fit and non-fit

Prioritize personal assistants and bounded embedded applications that need cross-session, cross-event relationships. Developers must be willing to define when to write, how to relate records, and what should be forgotten. For fixed preferences alone, a configuration file or simple key-value store may be more appropriate.

Do not use it directly for large shared graphs without scale validation, as the sole retrieval layer for massive document search, as the basis for clinical or legal decisions, or for real-time motion control. No public-package throughput, latency, or node-count promise exists yet; internal experimental scale is not a service-level agreement.

## First demonstrations and review questions

Start with two synthetic-data demonstrations that are offline by default: customer-service continuity across two tickets and preference correction in companionship. Both use public write/retrieve/delete entry points to expose provenance and update boundaries; examples are not production integrations and do not begin with paid APIs.

Please review four points: which scenario should lead the first release; whether “robot interaction memory” matches product positioning; which memories must never be written by default; and which effects require evidence before public claims. Finalize demonstration content after review rather than turning four industries into four separate products.
