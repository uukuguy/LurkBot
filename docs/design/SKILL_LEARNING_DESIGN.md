# 动态技能学习设计文档

## 概述

动态技能学习（Dynamic Skill Learning）是 LurkBot Phase 3-C 的核心功能，旨在使 AI Agent 能够从用户的对话历史中识别重复模式，并自动生成可复用的技能模板。

**核心目标**:
- 自动检测用户对话中的重复模式
- 从模式生成结构化的技能模板
- 持久化保存学习到的技能
- 支持技能的版本管理和使用统计

## 架构设计

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                  Dynamic Skill Learning System                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Conversation History                                            │
│       │                                                          │
│       ▼                                                          │
│  ┌────────────────────┐                                         │
│  │ PatternDetector    │                                         │
│  ├────────────────────┤                                         │
│  │  - Repeated Tasks  │                                         │
│  │  - Sequential Steps│                                         │
│  │  - Data Processing │                                         │
│  └──────────┬─────────┘                                         │
│             │                                                    │
│             ▼                                                    │
│  ┌────────────────────┐                                         │
│  │ TemplateGenerator  │                                         │
│  ├────────────────────┤                                         │
│  │  - LLM Generation  │                                         │
│  │  - Structure Output│                                         │
│  │  - Format Template │                                         │
│  └──────────┬─────────┘                                         │
│             │                                                    │
│             ▼                                                    │
│  ┌────────────────────┐                                         │
│  │  SkillStorage      │                                         │
│  ├────────────────────┤                                         │
│  │  - JSON Files      │                                         │
│  │  - Index Management│                                         │
│  │  - Usage Stats     │                                         │
│  └────────────────────┘                                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 核心组件

#### 1. PatternDetector (模式检测器)

**职责**: 从对话历史中识别重复模式

**文件**: `src/lurkbot/skills/learning/pattern_detector.py`

**核心API**:
- `detect_patterns()` - 检测对话历史中的模式

**检测的模式类型**:
1. **REPEATED_TASK** - 重复任务
   - 用户多次执行相似的操作
   - 基于关键词频率分析

2. **SEQUENTIAL_STEPS** - 顺序步骤
   - 用户在多个会话中执行相似的步骤序列
   - 基于会话内消息序列分析

3. **DATA_PROCESSING** - 数据处理
   - 用户重复执行数据转换、分析等操作
   - 基于数据处理关键词匹配

**配置参数**:
- `min_occurrences`: 最小出现次数（默认: 2）
- `time_window_days`: 时间窗口天数（默认: 7）
- `min_confidence`: 最小置信度（默认: 0.6）

#### 2. TemplateGenerator (模板生成器)

**职责**: 从检测到的模式生成结构化技能模板

**文件**: `src/lurkbot/skills/learning/template_generator.py`

**核心API**:
- `generate_template()` - 生成技能模板
- `format_template_for_user()` - 格式化为用户友好文本

**生成内容**:
- **name**: 技能名称
- **description**: 技能描述
- **skill_type**: 技能类型（workflow/command/analysis等）
- **trigger_keywords**: 触发关键词
- **actions**: 操作步骤列表
- **examples**: 使用示例

#### 3. SkillStorage (技能存储)

**职责**: 持久化保存和管理技能模板

**文件**: `src/lurkbot/skills/learning/skill_storage.py`

**核心API**:
- `save_skill()` - 保存技能
- `load_skill()` - 加载技能
- `list_skills()` - 列出技能
- `delete_skill()` - 删除技能
- `update_usage()` - 更新使用统计

**存储格式**:
- 每个技能一个 JSON 文件
- 统一的索引文件 `skills_index.json`
- 存储目录: `./data/skills/`

## 数据模型

### 核心模型

**文件**: `src/lurkbot/skills/learning/models.py`

1. **SkillTemplate** - 技能模板
   - 完整的技能定义
   - 包含元数据和使用统计

2. **SkillAction** - 技能操作步骤
   - 单个操作的详细定义
   - 包含参数和预期输出

3. **DetectedPattern** - 检测到的模式
   - 模式类型和描述
   - 置信度和出现次数

4. **SkillLearningResult** - 学习结果
   - 检测到的模式列表
   - 建议的技能模板

## 工作流程

### 1. 模式检测流程

```python
# 1. 获取用户对话历史
conversation_history = get_user_conversations(user_id, days=7)

# 2. 检测模式
detector = PatternDetector(min_occurrences=2)
patterns = detector.detect_patterns(conversation_history, user_id)

# 3. 过滤高置信度模式
high_confidence_patterns = [p for p in patterns if p.confidence >= 0.7]
```

### 2. 技能生成流程

```python
# 1. 选择模式
pattern = high_confidence_patterns[0]

# 2. 生成模板
generator = TemplateGenerator()
template = await generator.generate_template(
    pattern=pattern,
    user_id=user_id,
    session_id=session_id,
)

# 3. 格式化并展示给用户
message = generator.format_template_for_user(template)
# 发送给用户确认
```

### 3. 技能保存流程

```python
# 1. 用户确认创建技能
if user_confirms:
    # 2. 保存到存储
    storage = get_skill_storage()
    success = storage.save_skill(template)

    # 3. 通知用户
    if success:
        notify_user(f"技能 '{template.name}' 已创建！")
```

## 技能模板示例

```json
{
  "skill_id": "deploy-app-workflow",
  "name": "部署应用工作流",
  "description": "自动化应用部署流程，包括测试、构建和部署",
  "skill_type": "workflow",
  "pattern_type": "sequential_steps",
  "trigger_keywords": ["deploy", "部署", "发布"],
  "actions": [
    {
      "step_number": 1,
      "action_type": "run_command",
      "description": "运行测试",
      "parameters": {
        "command": "pytest tests/",
        "timeout": 300
      }
    },
    {
      "step_number": 2,
      "action_type": "run_command",
      "description": "构建应用",
      "parameters": {
        "command": "docker build -t myapp .",
        "timeout": 600
      }
    },
    {
      "step_number": 3,
      "action_type": "run_command",
      "description": "部署到生产环境",
      "parameters": {
        "command": "kubectl apply -f deployment.yaml",
        "timeout": 120
      }
    }
  ],
  "learned_from_session": "session-abc-123",
  "learned_from_user": "user-xyz-456",
  "created_at": "2026-01-31T15:00:00",
  "usage_count": 0,
  "version": 1,
  "examples": [
    "部署应用到生产环境",
    "执行完整的部署流程",
    "运行部署工作流"
  ]
}
```

## 测试策略

### 1. 单元测试

**PatternDetector 测试** (`tests/test_skill_learning.py`):
- 初始化和配置
- 空历史处理
- 重复任务检测
- 顺序步骤检测
- 数据处理模式检测

**SkillStorage 测试**:
- 保存和加载
- 列出技能
- 删除技能
- 使用统计更新

**TemplateGenerator 测试**:
- 模板生成（需要 API key）
- 格式化输出

### 2. 测试覆盖

- 不需要 API key 的测试：7个
- 需要 API key 的测试：1个
- 总计：8个测试
- 通过率：100%

## 配置管理

### 环境变量

```bash
# 技能存储目录
LURKBOT_SKILLS_STORAGE_DIR=./data/skills

# 模式检测配置
LURKBOT_PATTERN_MIN_OCCURRENCES=2
LURKBOT_PATTERN_TIME_WINDOW_DAYS=7
LURKBOT_PATTERN_MIN_CONFIDENCE=0.6
```

### 代码配置

```python
# 创建检测器
detector = PatternDetector(
    min_occurrences=2,
    time_window_days=7,
    min_confidence=0.6,
)

# 创建存储
storage = SkillStorage(storage_dir="./data/skills")
```

## 性能考虑

1. **异步执行**: 模板生成使用异步 LLM 调用
2. **批量处理**: 支持批量检测多个用户的模式
3. **缓存**: 索引文件缓存技能元数据
4. **增量更新**: 只分析新的对话记录

## 未来优化方向

### 1. 智能触发
- 自动识别何时应该提示用户创建技能
- 基于模式置信度和用户偏好

### 2. 技能推荐
- 向用户推荐相关的已有技能
- 基于相似度匹配

### 3. 技能组合
- 支持将多个技能组合成工作流
- 技能之间的依赖管理

### 4. 协作学习
- 跨用户的技能共享
- 社区技能库

### 5. 自动优化
- 基于使用反馈优化技能
- 自动生成改进版本

## 与其他模块的集成

### 与 Phase 3-A (上下文感知) 集成
- 使用上下文存储获取对话历史
- 利用 ChromaDB 进行语义搜索

### 与 Phase 3-B (主动任务识别) 集成
- 主动建议可以转化为技能
- 成功的建议自动学习为技能

### 与 Phase 5 (插件系统) 集成
- 技能可以打包为插件
- 支持技能的分发和安装

## 技术栈

- **LLM 框架**: PydanticAI
- **结构化输出**: Pydantic BaseModel
- **存储**: JSON 文件系统
- **日志**: Loguru
- **测试**: pytest

## 示例场景

### 场景 1: 学习部署流程

**用户行为**:
- 第1次: "运行测试" → "构建镜像" → "部署到 k8s"
- 第2次: "先测试" → "然后构建" → "最后部署"
- 第3次: "执行测试" → "打包应用" → "发布到生产"

**系统识别**:
- 模式类型: SEQUENTIAL_STEPS
- 置信度: 0.85
- 步骤序列: ["测试", "构建", "部署"]

**生成技能**:
- 名称: "应用部署工作流"
- 3个操作步骤
- 触发词: ["部署", "发布", "上线"]

### 场景 2: 学习数据处理

**用户行为**:
- 多次请求: "解析 JSON 数据"
- 多次请求: "转换 CSV 格式"
- 多次请求: "提取特定字段"

**系统识别**:
- 模式类型: DATA_PROCESSING
- 置信度: 0.75
- 关键词: ["parse", "transform", "extract"]

**生成技能**:
- 名称: "数据格式转换"
- 数据处理步骤
- 触发词: ["转换", "解析", "处理数据"]

---

**文档版本**: 1.0
**创建日期**: 2026-01-31
**状态**: Phase 3-C 完成 ✅
