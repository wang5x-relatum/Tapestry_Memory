# Terminology

English | [中文](README.zh.md)

Status: design baseline. This list stabilizes technical terms used by the repository; it does not freeze product positioning or API names.

| Term | Preferred meaning | Usage note |
| --- | --- | --- |
| `rmc-memory` | repository and distribution name | Keep the hyphenated spelling for the project name. |
| `rmc_memory` | planned Python import name | Use the underscore spelling only for Python imports and package paths. |
| Relational Memory Core | expansion of RMC | Use on first mention when the abbreviation needs explanation. |
| relational memory | relational memory | Memory organized around nodes and relationships across time and topics. |
| namespace | 命名空间 | Storage and access boundary supplied by the host; not authentication or authorization. |
| scope | 作用域 | The bounded context in which nodes, edges, retrieval, and deletion operate. |
| node | 节点 | A stored memory item; do not imply that every node is a verified fact. |
| edge | 边 | A typed relationship between in-scope nodes. |
| provenance | 来源元数据 | Information that lets the host locate or inspect an original source. A reference is not proof of truth. |
| logical deletion | 逻辑删除 | Package-owned data is marked or excluded from use within its scope; this is not storage-medium erasure. |
| host | 宿主 | The application integrating the library; it controls policy, permissions, writing, and response generation. |
| bounded retrieval | 有界检索 | Retrieval constrained by explicit limits such as `top_k` and traversal budget. |
| robot interaction memory | 机器人交互记忆 | Preferred scope description; it does not mean a complete robot soul or autonomous control system. |
| soul | soul / 灵魂 | Product-language term only. Do not use it to expand the package contract into personality, values, or consciousness. |
| artifact | 产物 | A built wheel or source distribution whose contents and bytes are verified before release. |
| blob hash | blob 哈希 | The Git blob SHA-1 of a document's exact bytes, not a commit hash and not a translation snapshot. |
