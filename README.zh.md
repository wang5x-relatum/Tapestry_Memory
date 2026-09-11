# tapestry-memory

[English](README.md) | 中文

**关系记忆引擎，为跨会话智能体组织可追溯的记忆。**

项目与发行包名称为 `tapestry-memory`，Python 导入名为 `tapestry_memory`。

## 当前状态

本仓库处于阶段 2：独立记忆库的本地核心实现与产物验证。这不是已发布的包。单元、契约和产物验收须与文档检查分开报告；本页不替代这些报告。干净环境下的 wheel 安装及离线示例验证已在本地通过；不宣称 sdist 安装已通过。`0.1.0` 是目标版本，不是已发布版本。本项目采用 Apache-2.0，声明版权主体为 MetaRelatum（越迹科技（宁波）有限公司）；公开发布及公开托管地址仍需最终发布批准。

## 产品边界

核心是基于 Python 标准库和 SQLite 的嵌入式图记忆库：由宿主决定写入哪些节点和关系，由引擎组织存储与检索，由宿主模型生成回答。它不是大模型、完整智能体平台、知识库抓取器或机器人控制系统。

阶段 2 契约要求无第三方运行时依赖、默认离线、不导入 Relatum 内部模块。省略 namespace 时使用 `default`；显式传入 `None`、空字符串或纯空白字符串均拒绝。节点身份为作用域内的 UUID，不使用内容哈希。检索为有界、确定性的 BFS，预算耗尽必须可观察。作用域内逻辑删除、事务回滚与数据库重开、JSON 来源元数据往返均为验收要求，不是评测成绩声明。

## 限制

阶段 2 不提供自动关系抽取、自动矛盾裁决、多设备同步、分布式服务或任意规模保证。不内置 500 字符截断，不承诺 GDPR 彻底删除，也不默认启用 embedding。namespace 隔离不替代宿主认证授权。逻辑删除不擦除外部原文、宿主日志、备份或存储介质。不宣称独立包已有性能或语义质量成绩。

## 从这里开始

- [适用场景初稿](docs/use-cases.zh.md)：陪伴、客服、教育、机器人及选型边界，等待用户审核。
- [v0.1 契约](docs/v0.1-contract.zh.md)：阶段 2 行为、数据生命周期与验收边界。
- [离线示例](examples/basic_usage.py)：使用公开 API 和合成数据演示新增、连边、检索、删除与重开。
- [双语文档规范](docs/i18n/README.zh.md)：中英文同权、三文件配对和检查边界。

## 用法

`tapestry-memory` 是嵌入式记忆引擎：创建作用域，写入记忆节点和有向关系，再检索有界的关系邻域。检索沿已存储的图关系进行，不是关键词搜索或语义搜索。

```python
from tapestry_memory import MemoryStore

with MemoryStore("memory.db", namespace="demo") as store:
    observation = store.add_node(
        "用户喜欢喝咖啡。",
        metadata={"provenance": {"source": "synthetic:example"}},
    )
    sleep = store.add_node("用户昨晚睡眠不好。")
    store.add_edge(observation.id, sleep.id, "相关")
    result = store.retrieve([observation.id], top_k=5)
```

本包专注于记忆引擎这一层——图存储与关系遍历。它也与更广义的关系性 AI 研究系统 Relatum 相关；其他 Relatum 研究或系统组件不属于本发行包，本包不承诺公开集成。项目由越迹科技（宁波）有限公司（MetaRelatum）维护，工程取向包括可追溯、可验证和可信任的系统行为；这些是设计目标，不保证来源元数据证明内容真实。

## 本地开发检查

要求 Python 3.10 或更新版本。从仓库根目录执行：

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 scripts/check_docs.py
```

运行命令不等于验收通过。单元与契约测试结果须分别注明范围与数量；文档检查单独报告，不验证运行时行为或翻译质量。离线示例使用公开 API 和合成数据；其本地验证不能替代单元、契约或产物验收。变更后的双语文档必须经人工复核，才能用 `--record ... --reviewed` 记录新哈希；复核完成前保留可见的哈希漂移。

## 沟通与发布

本阶段通过现有协作渠道审核本地文档，不要求 Discord 或其他需要额外跨境网络访问工具的社区平台，也不编造企业邮箱、群码或支持渠道。公开发布前确认可访问的反馈入口；核心使用不得依赖社区账号或在线文档站。

本仓库现附带标准 Apache-2.0 许可证，声明版权主体为 MetaRelatum（越迹科技（宁波）有限公司）。域名已注册，但本文未记录其确切地址。这不代表 `tapestry-memory` 已注册商标，公开发布仍需最终发布批准。文档站日后从仓库正文生成，不维护第二套技术内容。
