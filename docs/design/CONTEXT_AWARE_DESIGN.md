# 上下文感知响应设计文档

## 概述

上下文感知响应（Context-Aware Responses）是 LurkBot Phase 3-A 的核心功能，旨在使 AI Agent 能够理解和利用跨会话的上下文信息，提供更加连贯和智能的响应。

**核心目标**:
- 自动保存会话上下文到向量数据库
- 基于语义相似度检索相关历史上下文
- 在生成响应时融合历史上下文
- 支持跨会话的记忆和连续性

## 架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                      Context-Aware System                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User Prompt                                                     │
│       │                                                          │
│       ▼                                                          │
│  ┌────────────────┐                                             │
│  │ Agent Runtime  │                                             │
│  │                │                                             │
│  │  1. Load ctx   │──────┐                                     │
│  │  2. Run agent  │      │                                     │
│  │  3. Save ctx   │      │                                     │
│  └────────────────┘      │                                     │
│                          │                                     │
│                          ▼                                     │
│              ┌─────────────────────┐                           │
│              │  Context Manager    │                           │
│              ├─────────────────────┤                           │
│              │  - Storage          │                           │
│              │  - Retrieval        │                           │
│              │  - Scoring          │                           │
│              └──────────┬──────────┘                           │
│                         │                                       │
│                         ▼                                       │
│              ┌─────────────────────┐                           │
│              │   ChromaDB          │                           │
│              ├─────────────────────┤                           │
│              │  Collection:        │                           │
│              │  - contexts         │                           │
│              │                     │                           │
│              │  Metadata:          │                           │
│              │  - session_id       │                           │
│              │  - user_id          │                           │
│              │  - timestamp        │                           │
│              │  - context_type     │                           │
│              └─────────────────────┘                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 核心组件

#### 1. ContextStorage (存储层)

**职责**: 管理上下文在 ChromaDB 中的持久化

**文件**: `src/lurkbot/agents/context/storage.py`

**核心API**:
- `save_context()` - 保存单个上下文
- `save_contexts_batch()` - 批量保存
- `delete_context()` - 删除上下文
- `get_collection_stats()` - 统计信息

#### 2. ContextRetrieval (检索层)

**职责**: 基于语义相似度检索相关上下文

**文件**: `src/lurkbot/agents/context/retrieval.py`

**核心API**:
- `find_relevant_contexts()` - 查找相关上下文
- `score_relevance()` - 计算相关性分数
- `get_session_history()` - 获取会话历史

#### 3. ContextManager (管理层)

**职责**: 提供统一的上下文管理接口

**文件**: `src/lurkbot/agents/context/manager.py`

**核心API**:
- `load_context_for_prompt()` - 为输入加载上下文
- `save_interaction()` - 保存交互记录
- `format_contexts_for_prompt()` - 格式化上下文

## 数据模型

### 元数据结构

```python
{
    "context_id": str,        # 唯一标识符
    "session_id": str,        # 会话 ID
    "user_id": str,           # 用户 ID
    "timestamp": float,       # Unix 时间戳
    "context_type": str,      # "user_message" | "assistant_message"
    "message_role": str,      # "user" | "assistant"
}
```

## 集成到 Agent Runtime

修改 `run_embedded_agent()` 函数：

1. **请求前**: 调用 `load_context_for_prompt()` 加载相关上下文
2. **注入上下文**: 将上下文添加到 system_prompt
3. **响应后**: 调用 `save_interaction()` 保存交互

## 配置管理

环境变量：
```bash
LURKBOT_CONTEXT__PERSIST_DIR=./data/chroma_db
LURKBOT_CONTEXT__ENABLE_AUTO_SAVE=true
LURKBOT_CONTEXT__MAX_CONTEXT_LENGTH=5
```

## 测试策略

1. **单元测试**: 存储、检索功能独立测试
2. **集成测试**: 与 Agent Runtime 集成测试
3. **性能测试**: 大量数据下的响应时间

---

**文档版本**: 1.0  
**创建日期**: 2026-01-31
