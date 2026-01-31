# 主动任务识别设计文档

## 概述

主动任务识别（Proactive Task Identification）是 LurkBot Phase 3-B 的核心功能，旨在使 AI Agent 能够主动分析用户输入，识别隐含需求，并提供可操作的任务建议。

**核心目标**:
- 自动分析用户输入的意图和情感
- 识别用户未明说的隐含需求
- 生成具体可执行的任务建议
- 在适当时机主动向用户展示建议

## 架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                  Proactive Task Identification                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User Prompt                                                     │
│       │                                                          │
│       ▼                                                          │
│  ┌────────────────┐                                             │
│  │ Agent Runtime  │                                             │
│  │                │                                             │
│  │  1. Load ctx   │──────┐                                     │
│  │  2. Analyze    │      │                                     │
│  │  3. Suggest    │      │                                     │
│  │  4. Run agent  │      │                                     │
│  └────────────────┘      │                                     │
│                          │                                     │
│                          ▼                                     │
│              ┌─────────────────────┐                           │
│              │  InputAnalyzer      │                           │
│              ├─────────────────────┤                           │
│              │  - Intent           │                           │
│              │  - Sentiment        │                           │
│              │  - Key Topics       │                           │
│              │  - Implicit Needs   │                           │
│              └──────────┬──────────┘                           │
│                         │                                       │
│                         ▼                                       │
│              ┌─────────────────────┐                           │
│              │  TaskSuggester      │                           │
│              ├─────────────────────┤                           │
│              │  - Generate Tasks   │                           │
│              │  - Prioritize       │                           │
│              │  - Format Output    │                           │
│              └─────────────────────┘                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 核心组件

#### 1. InputAnalyzer (输入分析器)

**职责**: 分析用户输入，识别意图、情感和隐含需求

**文件**: `src/lurkbot/agents/proactive/analyzer.py`

**核心API**:
- `analyze()` - 分析用户输入
- `should_trigger_proactive()` - 判断是否应触发主动建议

**分析维度**:
- **Intent (意图)**: question, request, complaint, feedback, exploration, unknown
- **Sentiment (情感)**: positive, neutral, negative
- **Key Topics (关键主题)**: 1-3个最重要的关键词
- **Implicit Needs (隐含需求)**: 用户未明说但暗示的需求
- **Confidence (置信度)**: 0.0-1.0

#### 2. TaskSuggester (任务建议器)

**职责**: 基于分析结果生成可操作的任务建议

**文件**: `src/lurkbot/agents/proactive/suggester.py`

**核心API**:
- `suggest()` - 生成任务建议
- `format_suggestions_for_prompt()` - 格式化建议为 prompt 文本

**建议内容**:
- **task_type**: 任务类型（debug, investigate, optimize, learn, document）
- **description**: 简洁的任务描述
- **priority**: 优先级（high/medium/low）
- **actions**: 3-5个具体操作步骤
- **rationale**: 建议理由
- **confidence**: 建议置信度

#### 3. 数据模型

**文件**: `src/lurkbot/agents/proactive/models.py`

核心模型：
- `InputAnalysis` - 输入分析结果
- `TaskSuggestion` - 任务建议
- `ProactiveResult` - 完整的主动识别结果
- `ContextPattern` - 上下文模式（用于未来的模式识别）

## 集成到 Agent Runtime

修改 `run_embedded_agent()` 函数，在 Step 1.5 添加主动任务识别：

```python
# Step 1.5: Proactive task identification (if enabled)
if enable_proactive:
    # 1. 分析用户输入
    analyzer = InputAnalyzer(model=f"{context.provider}:{context.model_id}")
    analysis = await analyzer.analyze(
        prompt=prompt,
        context_history=message_history,
    )

    # 2. 判断是否应该触发建议
    if analyzer.should_trigger_proactive(analysis):
        # 3. 生成任务建议
        suggester = TaskSuggester(model=f"{context.provider}:{context.model_id}")
        suggestions = await suggester.suggest(
            user_prompt=prompt,
            analysis=analysis,
            context_summary=context_summary,
        )

        # 4. 将建议注入到 system_prompt
        if suggestions:
            suggestions_text = suggester.format_suggestions_for_prompt(suggestions)
            system_prompt = f"{system_prompt}\n\n{suggestions_text}"
```

## 触发条件

主动建议在以下情况下触发：

1. **消极情感 + 抱怨意图**
   - 用户表达不满或遇到问题
   - 例如："这个 bug 太烦人了"

2. **存在隐含需求**
   - 分析出用户有未明说的需求
   - 例如："部署失败了" → 隐含需求：查看日志、检查配置

3. **置信度 > 0.6**
   - 确保分析结果可靠

## 建议格式

建议以 Markdown 格式注入到 system_prompt：

```markdown
## 💡 主动建议

基于你的输入，我注意到以下可能有帮助的任务：

### 🔴 1. 调查部署失败原因
**类型**: debug
**理由**: 你提到部署失败，这通常需要查看日志和配置
**建议步骤**:
- 查看部署日志
- 检查配置文件
- 验证环境变量
- 测试网络连接

你希望我帮你执行哪个任务，还是继续你的原始请求？
```

## 配置管理

通过函数参数控制：

```python
result = await run_embedded_agent(
    context=context,
    prompt=prompt,
    system_prompt=system_prompt,
    enable_proactive=True,  # 默认启用
)
```

## 测试策略

### 1. 单元测试

**InputAnalyzer 测试** (`tests/test_proactive_analyzer.py`):
- 意图识别准确性
- 情感分析准确性
- 触发条件逻辑
- 初始化和配置

**TaskSuggester 测试** (`tests/test_proactive_suggester.py`):
- 建议生成
- 优先级排序
- 格式化输出
- 空建议处理

### 2. 集成测试

**Runtime 集成** (`tests/test_proactive_integration.py`):
- 端到端流程
- 与 Agent Runtime 集成
- 启用/禁用功能
- 多种意图类型处理

### 3. 测试覆盖

- 不需要 API key 的测试：6个（逻辑验证）
- 需要 API key 的测试：10个（实际 LLM 调用）
- 总计：16个测试

## 性能考虑

1. **异步执行**: 所有分析和建议生成都是异步的
2. **优雅降级**: 如果主动识别失败，不影响主流程
3. **可配置**: 可以通过参数禁用功能
4. **缓存**: 未来可以缓存常见模式的分析结果

## 未来优化方向

### 1. 模式学习
- 记录用户的常见问题模式
- 基于历史数据优化建议

### 2. 个性化
- 根据用户偏好调整建议风格
- 学习用户接受/拒绝建议的模式

### 3. 多轮对话
- 支持对建议的追问和细化
- 记录建议的执行结果

### 4. 与 Phase 3-C 协同
- 将成功的建议转化为可复用技能
- 自动学习和优化建议策略

## 技术栈

- **LLM 框架**: PydanticAI
- **结构化输出**: Pydantic BaseModel
- **日志**: Loguru
- **测试**: pytest + pytest-asyncio

## 示例场景

### 场景 1: 调试问题

**用户输入**: "这个 API 一直返回 500 错误，太烦了"

**分析结果**:
- Intent: COMPLAINT
- Sentiment: NEGATIVE
- Key Topics: ["API", "500 error"]
- Implicit Needs: ["check logs", "investigate error cause"]

**生成建议**:
1. 查看 API 服务器日志
2. 检查数据库连接
3. 验证请求参数
4. 测试 API 端点

### 场景 2: 学习探索

**用户输入**: "我想了解 Kubernetes 部署"

**分析结果**:
- Intent: EXPLORATION
- Sentiment: NEUTRAL
- Key Topics: ["Kubernetes", "deployment"]
- Implicit Needs: ["learn k8s basics", "deployment tutorial"]

**生成建议**:
1. 阅读 Kubernetes 官方文档
2. 创建简单的部署示例
3. 学习 kubectl 命令
4. 了解 Pod 和 Service 概念

---

**文档版本**: 1.0
**创建日期**: 2026-01-31
**状态**: Phase 3-B 完成 ✅
