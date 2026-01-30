# LurkBot 与 OpenClaw 全局对齐实施方案

**版本**: v2.0 (更新：澄清 Tools vs Skills)
**日期**: 2026-01-31
**文档语言**: 中文

**重要更新**：
- ✅ 澄清了 Tools (22个) 和 Skills (52个) 的概念差异
- ✅ LurkBot 的 22 个 Tools 已完全实现，主要差距在 Skills 生态
- ✅ 调整实施策略：优先 Skills 转换和 ClawHub 集成

---

## 目录

- [一、战略定位与对齐目标](#一战略定位与对齐目标)
- [二、架构对齐分析](#二架构对齐分析)
- [三、核心能力对齐路线](#三核心能力对齐路线)
- [四、国内生态适配方案](#四国内生态适配方案)
- [五、企业级增强规划](#五企业级增强规划)
- [六、实施路线图](#六实施路线图)
- [七、风险管理](#七风险管理)
- [八、成功标准](#八成功标准)

---

## 一、战略定位与对齐目标

### 1.1 项目定位差异

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   OpenClaw (TypeScript)              LurkBot (Python)          │
│   ═══════════════════                ═══════════════            │
│                                                                 │
│   🎯 目标用户                         🎯 目标用户               │
│      个人用户 + 企业                    开发者 + 企业           │
│                                                                 │
│   📱 交付形式                         📱 交付形式               │
│      原生应用 + CLI + Web               CLI + API + Docker     │
│                                                                 │
│   🌐 部署场景                         🌐 部署场景               │
│      桌面 + 移动 + 云                   服务器 + 容器 + 云       │
│                                                                 │
│   🔧 技术生态                         🔧 技术生态               │
│      Node.js + TypeScript               Python + AI/ML 生态    │
│                                                                 │
│   🎨 用户界面                         🎨 用户界面               │
│      A2UI Canvas + 原生 UI              Text + CLI + (Web)     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 对齐战略

**核心原则：架构对齐，生态差异化**

```
┌─────────────────────────────────────────────────────────────────┐
│                      对齐战略框架                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🎯 完全对齐 (100%)                                              │
│     ├── Agent 运行时架构                                         │
│     ├── 九层工具策略系统                                         │
│     ├── WebSocket Gateway 协议                                  │
│     ├── Bootstrap 文件系统                                       │
│     ├── 会话管理机制                                             │
│     ├── 子代理通信协议                                           │
│     └── Heartbeat/Cron 自主系统                                 │
│                                                                 │
│  🔄 选择性对齐 (70%)                                             │
│     ├── Skills 系统 (ClawHub 集成)                              │
│     ├── A2UI Canvas (简化版)                                    │
│     ├── 频道适配器 (优先国内)                                    │
│     └── 基础设施模块 (实用优先)                                  │
│                                                                 │
│  🚫 明确不对齐 (0%)                                              │
│     ├── 原生应用开发                                             │
│     ├── 语音唤醒功能                                             │
│     └── 复杂设备配对流程                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 对齐目标

**核心发现：Tools vs Skills 概念差异**

```
OpenClaw 架构：
├── Tools (约 30 个) - 系统级原子功能
└── Skills (52 个) - 业务级功能包装（包含多个 Tools）

LurkBot 当前状态：
├── Tools (22 个) ✅ 已完全实现
└── Skills (3 个) 🔄 待扩展
```

**对齐目标调整**：

| 维度 | 当前状态 | 目标状态 | 优先级 | 说明 |
|------|---------|---------|--------|------|
| **核心 Tools** | 22/22 (100%) | 22/22 (100%) | ✅ 已完成 | 系统功能已齐全 |
| **Skills 生态** | 3/52 (6%) | 30/52 (58%) | P0 | 引入高优先级 Skills |
| **ClawHub 集成** | 0% | 100% | P0 | 支持 install/search |
| **国内适配** | 0% | 3 个 Skills | P1 | 企业微信/钉钉/飞书 |
| **企业能力** | 60% | 95% | P1 | 加密/审计/高可用 |
| **A2UI Canvas** | 协议定义 | 基础渲染 | P2 | 实用优先 |

---

## 二、架构对齐分析

### 2.1 当前对齐状态评估

```
┌─────────────────────────────────────────────────────────────────┐
│                    架构模块对齐矩阵                               │
├──────────────────┬────────────┬──────────┬────────────┬─────────┤
│ 模块             │ OpenClaw   │ LurkBot  │ 对齐度     │ 差距    │
├──────────────────┼────────────┼──────────┼────────────┼─────────┤
│ Agent Runtime    │ Pi Agent   │ PydanticAI│ 95%       │ 框架差异│
│ Tool Policy      │ 9 层       │ 9 层      │ 100%      │ ✅ 完全 │
│ Gateway Protocol │ WebSocket  │ WebSocket │ 100%      │ ✅ 完全 │
│ Session Mgmt     │ JSONL      │ JSONL     │ 100%      │ ✅ 完全 │
│ Bootstrap        │ 8 文件     │ 8 文件    │ 100%      │ ✅ 完全 │
│ Subagent         │ ACP        │ ACP       │ 100%      │ ✅ 完全 │
│ Heartbeat        │ 10min      │ 5min可配  │ 100%      │ ✅ 完全 │
│ Cron Service     │ 3 调度类型 │ 3 调度类型│ 100%      │ ✅ 完全 │
│ Skills System    │ ClawHub    │ 本地加载  │ 60%       │ 需集成  │
│ Channels         │ 13+ 频道   │ 4 频道    │ 30%       │ 需扩展  │
│ A2UI Canvas      │ 完整       │ 协议定义  │ 40%       │ 需渲染  │
│ Infra Modules    │ 8 模块     │ 8 模块    │ 80%       │ 部分弱  │
│ Browser Auto     │ Playwright │ Playwright│ 90%       │ 功能少  │
│ TTS              │ 4 提供商   │ 4 提供商  │ 95%       │ ✅ 对齐 │
│ Memory/Vector    │ ChromaDB   │ ChromaDB  │ 90%       │ ✅ 对齐 │
│ Security/Audit   │ 完整       │ 基础      │ 60%       │ 需增强  │
├──────────────────┴────────────┴──────────┴────────────┴─────────┤
│ 整体对齐度：82%                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 关键差距分析

#### 差距 1: Skills 生态系统

**核心问题**：LurkBot 的 22 个 Tools 已完全实现 ✅，但缺少 Skills 生态：

```
LurkBot 当前状态：
├── Tools (系统功能层)：22/22 (100%) ✅
│   └── src/lurkbot/tools/builtin/ - 完整实现
└── Skills (业务应用层)：3/52 (6%) ❌
    └── skills/ - 仅 github/weather/web-search

OpenClaw 对比：
├── Tools (系统功能层)：~30 个
└── Skills (业务应用层)：52 个 ✅
    ├── 内置 Skills：包装 Tools + 文档
    └── ClawHub 集成：远程安装
```

**差距明细**：
- ✅ Tools 层已完全对齐（22 个核心功能）
- ❌ Skills 层严重不足（3 vs 52）
- ❌ 无 ClawHub API 客户端
- ❌ 无远程 Skills 下载能力
- ❌ 无 Skills 版本管理
- ❌ 无 Skills 依赖解析

**实施策略**：
1. **Step 0 (前置)**: 将 22 个 Tools 转换为 SKILL.md 格式（便于 ClawHub 分发）
2. **Step 1**: 实现 ClawHub 客户端（搜索/下载/安装）
3. **Step 2**: 引入 OpenClaw 高优先级 Skills（~30 个）

#### 差距 2: 国内聊天应用适配

**OpenClaw 实现**:
```
channels/
├── telegram/      ✅ 完整
├── discord/       ✅ 完整
├── slack/         ✅ 完整
├── whatsapp/      ✅ 完整
├── signal/        ✅ 完整
└── imessage/      ✅ 完整
```

**LurkBot 现状**:
```
channels/
├── telegram/      ✅ 完整
├── discord/       ✅ 完整
├── slack/         ✅ 完整
├── wework/        ❌ 缺失 (企业微信)
├── dingtalk/      ❌ 缺失 (钉钉)
└── feishu/        ❌ 缺失 (飞书)
```

**差距分析**:
- ❌ 国内三大主流 IM 未适配
- ❌ 国内大模型兼容性未验证
- ❌ 国内云部署文档缺失

#### 差距 3: 企业级安全增强

**OpenClaw 实现**:
```typescript
// 会话加密
class EncryptedSessionStore {
  encrypt(data: SessionData): Buffer {
    return aes256.encrypt(key, data);
  }
}

// 审计日志
class AuditLogger {
  async log(event: AuditEvent) {
    await db.insert({
      timestamp, userId, action,
      toolName, result, metadata
    });
  }
}
```

**LurkBot 现状**:
```python
# 会话明文存储
class SessionStore:
    def save(self, session: Session):
        with open(path, 'w') as f:
            json.dump(session.dict(), f)  # ❌ 明文

# 审计日志简单
class AuditLog:
    def log(self, action: str):
        logger.info(f"Action: {action}")  # ❌ 非结构化
```

**差距分析**:
- ❌ 会话数据明文存储
- ❌ 审计日志非结构化
- ❌ 无 RBAC 权限模型
- ❌ 无多租户隔离

---

## 三、核心能力对齐路线

### 3.1 Skills 系统增强 (P0)

#### 3.1.1 ClawHub 集成架构

```
┌─────────────────────────────────────────────────────────────────┐
│                   LurkBot Skills 系统架构                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────┐       │
│  │           lurkbot.skills.clawhub                     │       │
│  │  ┌────────────────┐      ┌─────────────────┐        │       │
│  │  │ ClawHubAPI     │      │ ClawHubCLI      │        │       │
│  │  │ (httpx 客户端) │      │ (subprocess)    │        │       │
│  │  └────────┬───────┘      └────────┬────────┘        │       │
│  │           │                       │                 │       │
│  │           └───────────┬───────────┘                 │       │
│  │                       │                             │       │
│  │              ┌────────▼─────────┐                   │       │
│  │              │ ClawHubClient    │                   │       │
│  │              │ ────────────────│                   │       │
│  │              │ - search()       │                   │       │
│  │              │ - install()      │                   │       │
│  │              │ - info()         │                   │       │
│  │              │ - sync()         │                   │       │
│  │              │ - resolve_deps() │                   │       │
│  │              └──────────────────┘                   │       │
│  └──────────────────────┬───────────────────────────────┘       │
│                         │                                       │
│                         ▼                                       │
│  ┌──────────────────────────────────────────────────────┐       │
│  │           lurkbot.skills.registry                    │       │
│  │  ┌────────────────────────────────────────┐          │       │
│  │  │ SkillRegistry (扩展)                   │          │       │
│  │  │ ────────────────────────────────────  │          │       │
│  │  │ - install_from_clawhub(slug, version) │          │       │
│  │  │ - check_updates()                     │          │       │
│  │  │ - resolve_dependencies()              │          │       │
│  │  │ - verify_signature()                  │          │       │
│  │  └────────────────────────────────────────┘          │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 3.1.2 实施步骤

**Step 0: 将现有 Tools 转换为 Skills** (2 天)

为 22 个 Tools 创建对应的 SKILL.md 文件，建立从 Tools 到 Skills 的映射关系：

```bash
# 新建目录结构
skills/
├── exec/SKILL.md              # exec + process tools
├── filesystem/SKILL.md        # read/write/edit/patch tools
├── sessions/SKILL.md          # 6 个 session 管理 tools
├── memory/SKILL.md            # memory_search/get tools
├── web/SKILL.md               # web_search/fetch tools
├── messaging/SKILL.md         # message tool
├── automation/SKILL.md        # cron tool
├── gateway/SKILL.md           # gateway tool
├── media/SKILL.md             # image/tts tools
├── nodes/SKILL.md             # nodes tool
└── hooks/SKILL.md             # hooks tool
```

每个 SKILL.md 包含：
```yaml
---
name: filesystem
description: File system operations (read, write, edit, patch)
version: 1.0.0
tools:
  - read
  - write
  - edit
  - apply_patch
tags: [filesystem, core]
---
# Filesystem Skill

完整的文件系统操作，包括读取、写入、编辑和补丁应用。

## 使用示例
[用户] 读取 config.yaml 文件
[Bot]  ✅ 文件内容: ...
```

**Step 1: ClawHub API 客户端** (3 天)

新建文件: `src/lurkbot/skills/clawhub.py`

```python
"""ClawHub 技能注册中心客户端"""
import httpx
from pathlib import Path
from pydantic import BaseModel

class ClawHubSkill(BaseModel):
    """ClawHub 技能元数据"""
    slug: str
    name: str
    version: str
    description: str
    author: str
    downloads: int
    dependencies: list[str] = []
    checksum: str

class ClawHubClient:
    """ClawHub API 客户端"""

    BASE_URL = "https://api.clawhub.ai/v1"

    async def search(self, query: str) -> list[ClawHubSkill]:
        """搜索技能"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/search",
                params={"q": query}
            )
            return [ClawHubSkill(**s) for s in resp.json()["skills"]]

    async def download(self, slug: str, version: str = "latest") -> bytes:
        """下载技能"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/download/{slug}/{version}"
            )
            return resp.content

    async def info(self, slug: str) -> ClawHubSkill:
        """获取技能信息"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/info/{slug}")
            return ClawHubSkill(**resp.json())
```

**Step 2: CLI 命令扩展** (2 天)

新建文件: `src/lurkbot/cli/skills.py`

```python
"""技能管理 CLI 命令"""
import typer
from rich.console import Console
from rich.table import Table

from lurkbot.skills.clawhub import ClawHubClient
from lurkbot.skills.registry import get_skill_manager

app = typer.Typer(help="技能管理命令")
console = Console()

@app.command()
def search(query: str):
    """搜索 ClawHub 技能"""
    import asyncio

    async def _search():
        client = ClawHubClient()
        skills = await client.search(query)

        table = Table(title=f"搜索结果: {query}")
        table.add_column("Slug", style="cyan")
        table.add_column("名称", style="green")
        table.add_column("版本", style="yellow")
        table.add_column("下载量", justify="right")

        for skill in skills:
            table.add_row(
                skill.slug, skill.name,
                skill.version, str(skill.downloads)
            )

        console.print(table)

    asyncio.run(_search())

@app.command()
def install(
    slug: str,
    version: str = "latest",
    workspace: str = "~/.lurkbot"
):
    """安装技能"""
    import asyncio

    async def _install():
        manager = get_skill_manager()
        await manager.install_from_clawhub(slug, version, workspace)
        console.print(f"✅ 已安装: {slug}@{version}")

    asyncio.run(_install())

@app.command()
def list(source: str = "all"):
    """列出已安装技能"""
    manager = get_skill_manager()
    skills = manager.list_skills()

    table = Table(title="已安装技能")
    table.add_column("Key", style="cyan")
    table.add_column("来源", style="magenta")
    table.add_column("启用", justify="center")

    for skill in skills:
        if source == "all" or skill.source == source:
            table.add_row(
                skill.key,
                skill.source,
                "✅" if skill.frontmatter.enabled else "❌"
            )

    console.print(table)
```

**Step 3: Registry 扩展** (3 天)

修改文件: `src/lurkbot/skills/registry.py`

```python
class SkillManager:
    """技能管理器 (扩展 ClawHub 支持)"""

    def __init__(self):
        self.registry = SkillRegistry()
        self.clawhub_client = ClawHubClient()

    async def install_from_clawhub(
        self,
        slug: str,
        version: str = "latest",
        workspace: Path | str = "~/.lurkbot"
    ) -> SkillEntry:
        """从 ClawHub 安装技能"""

        # 1. 获取技能信息
        info = await self.clawhub_client.info(slug)

        # 2. 检查依赖
        for dep_slug in info.dependencies:
            if not self.registry.has(dep_slug):
                logger.info(f"安装依赖: {dep_slug}")
                await self.install_from_clawhub(dep_slug, "latest", workspace)

        # 3. 下载技能
        content = await self.clawhub_client.download(slug, version)

        # 4. 验证 checksum
        import hashlib
        actual_checksum = hashlib.sha256(content).hexdigest()
        if actual_checksum != info.checksum:
            raise ValueError(f"Checksum 不匹配: {slug}")

        # 5. 解压到 workspace
        workspace_path = Path(workspace).expanduser()
        skill_dir = workspace_path / "skills" / slug
        skill_dir.mkdir(parents=True, exist_ok=True)

        import zipfile
        import io
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            zf.extractall(skill_dir)

        # 6. 加载技能
        skill = self._load_skill(skill_dir)
        self.registry.register(skill)

        logger.info(f"✅ 已安装: {slug}@{version}")
        return skill

    async def check_updates(self) -> list[tuple[str, str, str]]:
        """检查技能更新"""
        updates = []
        for skill in self.registry.list_all():
            if skill.source == "clawhub":
                info = await self.clawhub_client.info(skill.key)
                if info.version > skill.frontmatter.version:
                    updates.append((
                        skill.key,
                        skill.frontmatter.version,
                        info.version
                    ))
        return updates
```

**Step 4: Agent 自动安装** (2 天)

修改文件: `src/lurkbot/agents/runtime.py`

```python
async def run_embedded_agent(
    context: AgentContext,
    prompt: str,
    ...
) -> AgentRunResult:
    """运行 Agent (支持自动安装技能)"""

    # 技能缺失检测
    required_skills = extract_required_skills(prompt)
    for skill_name in required_skills:
        if not skill_manager.registry.has(skill_name):
            logger.info(f"检测到缺失技能: {skill_name}")

            # 请求用户批准
            if context.auto_install_skills:
                await skill_manager.install_from_clawhub(skill_name)
            else:
                # 发送审批请求
                approval = await request_skill_install_approval(
                    skill_name, context
                )
                if approval:
                    await skill_manager.install_from_clawhub(skill_name)

    # ... 继续原有逻辑
```

#### 3.1.3 OpenClaw Skills 生态对接

**迁移策略**:

1. **Phase 1**: 发布 LurkBot 核心 Skills 包到 ClawHub (2 天)
   - 将 LurkBot 22 个 Tools 转换为 SKILL.md 格式
   - 发布到 ClawHub (命名空间: `lurkbot/core-*`)
   - 目标：让 LurkBot Tools 可被 OpenClaw 生态使用

2. **Phase 2**: 从 ClawHub 引入 OpenClaw 高优先级 Skills (1 周)
   - **高优先级** (~10 个):
     - `openclaw/code-review` - 代码审查
     - `openclaw/file-manager` - 文件管理
     - `openclaw/git-workflow` - Git 工作流
     - `openclaw/notion` - Notion 集成
     - `openclaw/slack` - Slack 集成
   - **中优先级** (~20 个):
     - 应用集成 (Trello/Jira/Linear)
     - AI 能力 (Gemini/Whisper)
     - 开发工具 (Docker/K8s)
   - 使用命令：`lurkbot skills install openclaw/code-review`

3. **Phase 3**: 社区技能生态 (后续)
   - 编写 Skill 开发指南文档
   - 创建 Skill 模板项目
   - 鼓励用户发布自定义 Skills

**重要说明**：
- Tools (22个) 是 LurkBot 的核心优势 ✅，已完全实现
- Skills (3→30) 是生态扩展目标，通过 ClawHub 快速补齐
- 不需要重复实现 Tools，只需包装为 Skills 格式

### 3.2 自主能力增强 (P1)

#### 3.2.1 当前状态评估

| 能力 | OpenClaw | LurkBot | 对齐度 |
|------|----------|---------|--------|
| Heartbeat 周期唤醒 | ✅ 10min | ✅ 5min可配 | 100% |
| Cron 定时任务 | ✅ 3调度 | ✅ 3调度 | 100% |
| 子代理协作 | ✅ ACP | ✅ ACP | 100% |
| **主动任务识别** | ✅ 完整 | ❌ 缺失 | **0%** |
| **技能推荐学习** | ✅ 完整 | ❌ 缺失 | **0%** |

#### 3.2.2 主动任务识别系统

新建目录: `src/lurkbot/autonomous/proactive/`

```python
# proactive/__init__.py
"""主动任务识别系统"""

from pydantic import BaseModel
from datetime import datetime

class ProactiveTask(BaseModel):
    """主动识别的任务"""
    task_id: str
    description: str
    priority: int  # 1-5
    context: dict
    suggested_time: datetime
    confidence: float  # 0-1

class ProactiveTaskIdentifier:
    """主动任务识别器"""

    def __init__(self, config: ProactiveConfig):
        self.triggers = config.triggers
        self.cooldown = config.cooldown
        self.min_confidence = config.min_confidence

    async def analyze_context(
        self,
        session: Session
    ) -> list[ProactiveTask]:
        """分析会话上下文，识别潜在任务"""

        tasks = []

        # 1. 分析最近消息
        recent_messages = session.get_recent_messages(limit=20)

        # 2. 提取待办事项
        todos = self._extract_todos(recent_messages)
        for todo in todos:
            tasks.append(ProactiveTask(
                task_id=f"todo-{hash(todo)}",
                description=todo,
                priority=3,
                context={"source": "conversation"},
                suggested_time=datetime.now(),
                confidence=0.8
            ))

        # 3. 分析时间模式
        time_patterns = self._analyze_time_patterns(session)
        if time_patterns.has_recurring_task:
            tasks.append(ProactiveTask(
                task_id=f"recurring-{time_patterns.pattern_id}",
                description=time_patterns.description,
                priority=4,
                context={"pattern": time_patterns.cron_expr},
                suggested_time=time_patterns.next_occurrence,
                confidence=time_patterns.confidence
            ))

        # 4. 检测失败任务
        failed_tools = self._find_failed_tools(recent_messages)
        for tool_name, error in failed_tools:
            tasks.append(ProactiveTask(
                task_id=f"retry-{tool_name}",
                description=f"重试失败的任务: {tool_name}",
                priority=5,
                context={"tool": tool_name, "error": error},
                suggested_time=datetime.now(),
                confidence=0.9
            ))

        return [t for t in tasks if t.confidence >= self.min_confidence]

    async def should_notify(self, task: ProactiveTask) -> bool:
        """判断是否应该通知用户"""

        # 检查冷却时间
        if not self._check_cooldown(task):
            return False

        # 检查用户在线状态
        if not await self._is_user_available():
            return False

        return True
```

#### 3.2.3 技能自学习机制

新建文件: `src/lurkbot/skills/learning.py`

```python
"""技能学习管理器"""

from collections import defaultdict
from datetime import datetime, timedelta

class SkillUsageStats(BaseModel):
    """技能使用统计"""
    skill_key: str
    total_calls: int
    success_count: int
    failure_count: int
    avg_execution_time: float
    last_used: datetime
    user_rating: float | None = None

class SkillLearningManager:
    """技能学习管理器"""

    def __init__(self):
        self.stats: dict[str, SkillUsageStats] = {}
        self.clawhub_client = ClawHubClient()

    async def suggest_skills(
        self,
        context: AgentContext
    ) -> list[str]:
        """基于上下文推荐技能"""

        # 1. 分析用户意图
        intent = self._analyze_intent(context.prompt)

        # 2. 搜索相关技能
        candidates = await self.clawhub_client.search(intent.keywords)

        # 3. 过滤已安装
        new_skills = [
            s.slug for s in candidates
            if not skill_manager.registry.has(s.slug)
        ]

        # 4. 排序 (下载量 + 相关度)
        ranked = sorted(
            new_skills,
            key=lambda s: self._relevance_score(s, context),
            reverse=True
        )

        return ranked[:3]

    async def learn_from_usage(
        self,
        skill_key: str,
        feedback: SkillFeedback
    ):
        """从使用反馈中学习"""

        if skill_key not in self.stats:
            self.stats[skill_key] = SkillUsageStats(
                skill_key=skill_key,
                total_calls=0,
                success_count=0,
                failure_count=0,
                avg_execution_time=0,
                last_used=datetime.now()
            )

        stats = self.stats[skill_key]
        stats.total_calls += 1
        stats.last_used = datetime.now()

        if feedback.success:
            stats.success_count += 1
        else:
            stats.failure_count += 1

        # 更新平均执行时间
        stats.avg_execution_time = (
            (stats.avg_execution_time * (stats.total_calls - 1) +
             feedback.execution_time) / stats.total_calls
        )

        # 低成功率技能标记
        if stats.total_calls >= 5:
            success_rate = stats.success_count / stats.total_calls
            if success_rate < 0.5:
                logger.warning(
                    f"技能 {skill_key} 成功率低: {success_rate:.1%}"
                )
```

---

## 四、国内生态适配方案

### 4.1 国内聊天应用接入架构

```
┌─────────────────────────────────────────────────────────────────┐
│                  国内 IM 频道适配层架构                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   企业微信    │  │    钉钉      │  │    飞书      │          │
│  │  WeWork      │  │  DingTalk    │  │   Feishu     │          │
│  │              │  │              │  │              │          │
│  │ - 企业应用   │  │ - 企业内部   │  │ - 企业自建   │          │
│  │ - Webhook    │  │ - Stream连接 │  │ - 事件订阅   │          │
│  │ - 主动消息   │  │ - 机器人消息 │  │ - 消息卡片   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                  │
│         └─────────────────┼─────────────────┘                  │
│                           │                                    │
│                    ┌──────▼──────┐                             │
│                    │BaseIMChannel│                             │
│                    │  抽象基类   │                             │
│                    │             │                             │
│                    │ - send()    │                             │
│                    │ - recv()    │                             │
│                    │ - format()  │                             │
│                    └─────────────┘                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 企业微信适配器

新建目录: `src/lurkbot/channels/wework/`

```python
# wework/__init__.py
"""企业微信频道适配器"""

from wechatpy.enterprise import WeChatClient
from wechatpy.enterprise.crypto import WeChatCrypto

class WeWorkConfig(BaseModel):
    """企业微信配置"""
    enabled: bool = False
    corp_id: str  # 企业 ID
    agent_id: int  # 应用 AgentId
    secret: str  # 应用 Secret
    token: str  # 回调 Token
    encoding_aes_key: str  # 加密 Key
    allowlist: list[str] = []  # 白名单用户

class WeWorkChannel(BaseChannel):
    """企业微信频道"""

    def __init__(self, config: WeWorkConfig):
        self.config = config
        self.client = WeChatClient(
            config.corp_id,
            config.secret
        )
        self.crypto = WeChatCrypto(
            config.token,
            config.encoding_aes_key,
            config.corp_id
        )

    async def start(self):
        """启动 Webhook 服务器"""
        from fastapi import FastAPI, Request

        app = FastAPI()

        @app.post("/wework/callback")
        async def callback(request: Request):
            # 1. 验证签名
            signature = request.query_params.get("msg_signature")
            timestamp = request.query_params.get("timestamp")
            nonce = request.query_params.get("nonce")

            body = await request.body()
            decrypted = self.crypto.decrypt_message(
                body, signature, timestamp, nonce
            )

            # 2. 解析消息
            message = parse_wework_message(decrypted)

            # 3. 调用 Agent
            response = await self.handle_message(message)

            # 4. 返回响应
            return self.format_response(response)

        # 启动服务器
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8001)

    async def send(self, message: ChannelMessage):
        """发送消息"""

        # 支持文本、Markdown、卡片
        if message.format == "markdown":
            self.client.message.send_markdown(
                agent_id=self.config.agent_id,
                user_ids=message.to_user,
                content=message.content
            )
        elif message.format == "card":
            self.client.message.send_template_card(
                agent_id=self.config.agent_id,
                user_ids=message.to_user,
                template_card=message.card_data
            )
        else:
            self.client.message.send_text(
                agent_id=self.config.agent_id,
                user_ids=message.to_user,
                content=message.content
            )
```

### 4.3 钉钉适配器

新建目录: `src/lurkbot/channels/dingtalk/`

```python
# dingtalk/__init__.py
"""钉钉频道适配器"""

from dingtalk_sdk import DingTalkClient
from dingtalk_stream import AckMessage

class DingTalkConfig(BaseModel):
    """钉钉配置"""
    enabled: bool = False
    app_key: str
    app_secret: str
    robot_code: str
    coolapp_code: str | None = None  # 酷应用 Code

class DingTalkChannel(BaseChannel):
    """钉钉频道"""

    def __init__(self, config: DingTalkConfig):
        self.config = config
        self.client = DingTalkClient(
            config.app_key,
            config.app_secret
        )

    async def start(self):
        """启动 Stream 连接"""

        # Stream 模式 (长连接)
        from dingtalk_stream import DingTalkStreamClient

        stream_client = DingTalkStreamClient(
            client_id=self.config.app_key,
            client_secret=self.config.app_secret
        )

        @stream_client.on_bot_message()
        async def on_message(msg: dict):
            # 处理消息
            response = await self.handle_message(msg)

            # 回复消息
            await self.send(response)

            return AckMessage.STATUS_OK

        # 启动连接
        await stream_client.start()

    async def send(self, message: ChannelMessage):
        """发送消息"""

        # 支持 Markdown、ActionCard
        if message.format == "actioncard":
            await self.client.robot.send_action_card(
                webhook=message.webhook,
                title=message.title,
                text=message.content,
                btns=message.buttons
            )
        else:
            await self.client.robot.send_markdown(
                webhook=message.webhook,
                title=message.title,
                text=message.content
            )
```

### 4.4 飞书适配器

新建目录: `src/lurkbot/channels/feishu/`

```python
# feishu/__init__.py
"""飞书频道适配器"""

import lark_oapi as lark
from lark_oapi.api.im.v1 import *

class FeishuConfig(BaseModel):
    """飞书配置"""
    enabled: bool = False
    app_id: str
    app_secret: str
    verification_token: str
    encrypt_key: str | None = None

class FeishuChannel(BaseChannel):
    """飞书频道"""

    def __init__(self, config: FeishuConfig):
        self.config = config
        self.client = lark.Client.builder() \
            .app_id(config.app_id) \
            .app_secret(config.app_secret) \
            .build()

    async def start(self):
        """启动事件订阅"""

        from fastapi import FastAPI, Request

        app = FastAPI()

        @app.post("/feishu/event")
        async def event_callback(request: Request):
            # 1. 验证请求
            body = await request.json()

            if body.get("type") == "url_verification":
                return {"challenge": body["challenge"]}

            # 2. 解密事件
            if self.config.encrypt_key:
                encrypted = body["encrypt"]
                decrypted = self._decrypt_event(encrypted)
                event = json.loads(decrypted)
            else:
                event = body["event"]

            # 3. 处理消息
            if event["type"] == "message.receive":
                message = event["message"]
                response = await self.handle_message(message)
                await self.send(response)

            return {"code": 0}

        # 启动服务器
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8002)

    async def send(self, message: ChannelMessage):
        """发送消息"""

        # 构造消息内容
        if message.format == "card":
            content = lark.MessageCard \
                .builder() \
                .title(message.title) \
                .content(message.content) \
                .build()
        else:
            content = lark.MessageText \
                .builder() \
                .text(message.content) \
                .build()

        # 发送消息
        request = CreateMessageRequest.builder() \
            .receive_id_type("chat_id") \
            .receive_id(message.chat_id) \
            .msg_type("interactive" if message.format == "card" else "text") \
            .content(content) \
            .build()

        response = self.client.im.v1.message.create(request)
        return response.success()
```

### 4.5 国内大模型兼容

修改文件: `src/lurkbot/config/models.py`

```python
# 添加国内大模型提供商
class ModelProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"      # 新增
    QWEN = "qwen"              # 新增
    KIMI = "kimi"              # 新增
    GLM = "glm"                # 新增

# 模型映射
CHINA_MODELS = {
    "deepseek": {
        "chat": "deepseek-chat",
        "coder": "deepseek-coder"
    },
    "qwen": {
        "max": "qwen-max",
        "plus": "qwen-plus",
        "turbo": "qwen-turbo"
    },
    "kimi": {
        "default": "moonshot-v1-8k"
    },
    "glm": {
        "4": "glm-4",
        "3-turbo": "glm-3-turbo"
    }
}
```

---

## 五、企业级增强规划

### 5.1 安全增强路线图

```
┌─────────────────────────────────────────────────────────────────┐
│                   企业级安全增强架构                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 1: 数据加密                                               │
│  ┌───────────────────────────────────────────────────┐          │
│  │ - 会话数据 AES-256 加密                            │          │
│  │ - 敏感配置 Secrets Manager                         │          │
│  │ - 传输层 TLS 1.3                                   │          │
│  └───────────────────────────────────────────────────┘          │
│                                                                 │
│  Layer 2: 访问控制                                               │
│  ┌───────────────────────────────────────────────────┐          │
│  │ - RBAC 角色权限                                    │          │
│  │ - API Token 认证                                   │          │
│  │ - IP 白名单/黑名单                                 │          │
│  └───────────────────────────────────────────────────┘          │
│                                                                 │
│  Layer 3: 审计日志                                               │
│  ┌───────────────────────────────────────────────────┐          │
│  │ - 结构化日志 (JSON Lines)                          │          │
│  │ - 操作审计跟踪                                      │          │
│  │ - 异常行为检测                                      │          │
│  └───────────────────────────────────────────────────┘          │
│                                                                 │
│  Layer 4: 合规性                                                 │
│  ┌───────────────────────────────────────────────────┐          │
│  │ - 数据本地化存储                                    │          │
│  │ - 敏感词过滤                                        │          │
│  │ - 内容审核接口                                      │          │
│  └───────────────────────────────────────────────────┘          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 会话加密实现

新建文件: `src/lurkbot/security/encryption.py`

```python
"""会话数据加密"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64

class EncryptionManager:
    """加密管理器"""

    def __init__(self, master_key: str):
        """
        初始化加密管理器

        Args:
            master_key: 主密钥 (应从环境变量或 Secrets Manager 获取)
        """
        self.fernet = self._init_fernet(master_key)

    def _init_fernet(self, master_key: str) -> Fernet:
        """初始化 Fernet 加密器"""
        # 使用 PBKDF2 派生密钥
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"lurkbot-salt-v1",  # 生产环境应使用随机 salt
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(master_key.encode())
        )
        return Fernet(key)

    def encrypt(self, data: str) -> str:
        """加密数据"""
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        """解密数据"""
        return self.fernet.decrypt(encrypted.encode()).decode()

class EncryptedSessionStore(SessionStore):
    """加密会话存储"""

    def __init__(self, encryption_manager: EncryptionManager):
        self.encryption = encryption_manager

    def save(self, session: Session):
        """保存加密会话"""
        # 序列化
        json_data = session.model_dump_json()

        # 加密
        encrypted = self.encryption.encrypt(json_data)

        # 写入文件
        path = self._get_session_path(session.session_id)
        path.write_text(encrypted)

    def load(self, session_id: str) -> Session:
        """加载解密会话"""
        path = self._get_session_path(session_id)

        # 读取加密数据
        encrypted = path.read_text()

        # 解密
        json_data = self.encryption.decrypt(encrypted)

        # 反序列化
        return Session.model_validate_json(json_data)
```

### 5.3 结构化审计日志

新建文件: `src/lurkbot/security/audit.py`

```python
"""结构化审计日志"""

from enum import Enum
from pathlib import Path
import json

class AuditAction(str, Enum):
    """审计动作类型"""
    AGENT_RUN = "agent.run"
    TOOL_EXEC = "tool.execute"
    SESSION_CREATE = "session.create"
    SESSION_DELETE = "session.delete"
    CONFIG_CHANGE = "config.change"
    SKILL_INSTALL = "skill.install"
    USER_LOGIN = "user.login"
    API_CALL = "api.call"

class AuditLevel(str, Enum):
    """审计级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AuditLog(BaseModel):
    """审计日志条目"""
    timestamp: datetime
    level: AuditLevel
    action: AuditAction
    user_id: str
    session_id: str | None = None
    tool_name: str | None = None
    result: str
    metadata: dict = {}
    ip_address: str | None = None
    user_agent: str | None = None

class AuditLogger:
    """审计日志记录器"""

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log(self, entry: AuditLog):
        """记录审计日志"""

        # 按日期分文件
        log_file = self.log_dir / f"audit-{entry.timestamp.date()}.jsonl"

        # 写入 JSON Lines
        with log_file.open("a") as f:
            f.write(entry.model_dump_json() + "\n")

        # 同时记录到系统日志
        logger.bind(
            action=entry.action,
            user_id=entry.user_id
        ).info(f"Audit: {entry.action} by {entry.user_id}")

    async def search(
        self,
        start_date: date,
        end_date: date,
        action: AuditAction | None = None,
        user_id: str | None = None
    ) -> list[AuditLog]:
        """搜索审计日志"""

        results = []
        current_date = start_date

        while current_date <= end_date:
            log_file = self.log_dir / f"audit-{current_date}.jsonl"

            if log_file.exists():
                with log_file.open("r") as f:
                    for line in f:
                        entry = AuditLog.model_validate_json(line)

                        # 过滤
                        if action and entry.action != action:
                            continue
                        if user_id and entry.user_id != user_id:
                            continue

                        results.append(entry)

            current_date += timedelta(days=1)

        return results
```

### 5.4 RBAC 权限模型

新建文件: `src/lurkbot/security/rbac.py`

```python
"""基于角色的访问控制"""

class Permission(str, Enum):
    """权限定义"""
    # Agent 权限
    AGENT_RUN = "agent:run"
    AGENT_CREATE = "agent:create"
    AGENT_DELETE = "agent:delete"

    # 工具权限
    TOOL_EXEC = "tool:execute"
    TOOL_MANAGE = "tool:manage"

    # 会话权限
    SESSION_READ = "session:read"
    SESSION_WRITE = "session:write"
    SESSION_DELETE = "session:delete"

    # 技能权限
    SKILL_INSTALL = "skill:install"
    SKILL_PUBLISH = "skill:publish"

    # 系统权限
    CONFIG_READ = "config:read"
    CONFIG_WRITE = "config:write"
    AUDIT_READ = "audit:read"

class Role(BaseModel):
    """角色定义"""
    name: str
    permissions: list[Permission]
    description: str

# 预定义角色
BUILTIN_ROLES = {
    "admin": Role(
        name="admin",
        permissions=list(Permission),  # 所有权限
        description="系统管理员"
    ),
    "user": Role(
        name="user",
        permissions=[
            Permission.AGENT_RUN,
            Permission.TOOL_EXEC,
            Permission.SESSION_READ,
            Permission.SESSION_WRITE,
        ],
        description="普通用户"
    ),
    "readonly": Role(
        name="readonly",
        permissions=[
            Permission.SESSION_READ,
            Permission.CONFIG_READ,
        ],
        description="只读用户"
    )
}

class RBACManager:
    """RBAC 管理器"""

    def __init__(self):
        self.roles = BUILTIN_ROLES.copy()
        self.user_roles: dict[str, list[str]] = {}

    def assign_role(self, user_id: str, role_name: str):
        """分配角色"""
        if role_name not in self.roles:
            raise ValueError(f"角色不存在: {role_name}")

        if user_id not in self.user_roles:
            self.user_roles[user_id] = []

        self.user_roles[user_id].append(role_name)

    def check_permission(
        self,
        user_id: str,
        permission: Permission
    ) -> bool:
        """检查权限"""
        user_roles = self.user_roles.get(user_id, [])

        for role_name in user_roles:
            role = self.roles[role_name]
            if permission in role.permissions:
                return True

        return False

    def require_permission(self, permission: Permission):
        """权限装饰器"""
        def decorator(func):
            async def wrapper(user_id: str, *args, **kwargs):
                if not self.check_permission(user_id, permission):
                    raise PermissionError(
                        f"用户 {user_id} 无权限: {permission}"
                    )
                return await func(user_id, *args, **kwargs)
            return wrapper
        return decorator
```

### 5.5 高可用部署方案

新建文件: `docs/design/HIGH_AVAILABILITY.md`

```markdown
# LurkBot 高可用部署方案

## 架构设计

\`\`\`
┌─────────────────────────────────────────────────────────────┐
│                     负载均衡层                               │
│                  (Nginx / HAProxy)                          │
└────────────────┬────────────────┬───────────────────────────┘
                 │                │
        ┌────────▼────────┐  ┌────▼──────────┐
        │  LurkBot 实例 1 │  │ LurkBot 实例 2│
        │  (Gateway)      │  │ (Gateway)     │
        └────────┬────────┘  └────┬──────────┘
                 │                │
                 └────────┬───────┘
                          │
        ┌─────────────────▼────────────────────┐
        │         共享状态层                    │
        │  ┌──────────┐     ┌───────────┐      │
        │  │  Redis   │     │ PostgreSQL│      │
        │  │ (会话)   │     │ (审计日志)│      │
        │  └──────────┘     └───────────┘      │
        └──────────────────────────────────────┘
\`\`\`

## 实施步骤

1. **会话共享**: 使用 Redis 存储会话状态
2. **负载均衡**: Nginx 配置 WebSocket 支持
3. **健康检查**: 实现 `/health` 端点
4. **自动扩缩容**: Kubernetes HPA
5. **数据备份**: 定时备份 Redis + PostgreSQL
\`\`\`

---

## 六、实施路线图

### 6.1 总体规划

```
┌─────────────────────────────────────────────────────────────────┐
│                   LurkBot 对齐实施路线图                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Phase 1: 核心 Skills 生态建设 (2-3 周) ───────────────────────┐ │
│  │                                                            │ │
│  ├── Step 0: Tools → Skills 转换                       [P0] │ │
│  │   └── 为 22 个 Tools 创建 SKILL.md                  2天  │ │
│  │                                                            │ │
│  ├── ClawHub 集成                                        [P0]│ │
│  │   ├── API 客户端                                     3天  │ │
│  │   ├── CLI 命令                                       2天  │ │
│  │   ├── Registry 扩展                                  3天  │ │
│  │   └── Agent 自动安装                                 2天  │ │
│  │                                                            │ │
│  ├── 引入 OpenClaw Skills                               [P0]│ │
│  │   ├── 高优先级 Skills (~10个)                        3天  │ │
│  │   └── 中优先级 Skills (~20个)                        5天  │ │
│  │                                                            │ │
│  └── 测试验证                                            [P0]│ │
│      ├── Skills 安装测试                                2天  │ │
│      └── 文档更新                                       2天  │ │
│                                                              │ │
└──────────────────────────────────────────────────────────────┘ │
                                                                 │
│  Phase 2: 国内生态适配 (2-3 周) ────────────────────────────────┐ │
│  │                                                            │ │
│  ├── 国内 IM 适配                                        [P1]│ │
│  │   ├── 企业微信 Adapter                               5天  │ │
│  │   ├── 钉钉 Adapter                                   4天  │ │
│  │   └── 飞书 Adapter                                   4天  │ │
│  │                                                            │ │
│  ├── 国内大模型适配                                      [P1]│ │
│  │   └── DeepSeek/Qwen/Kimi/GLM                         3天  │ │
│  │                                                            │ │
│  └── 测试验证                                            [P0]│ │
│      └── 国内 IM 消息收发测试                            3天  │ │
│                                                              │ │
└──────────────────────────────────────────────────────────────┘ │
│  │                                                            │ │
│  ├── 主动任务识别                                        [P1]│ │
│  │   ├── ProactiveIdentifier                            5天  │ │
│  │   ├── Heartbeat 集成                                 2天  │ │
│  │   └── 通知机制                                       3天  │ │
│  │                                                            │ │
│  Phase 3: 自主能力增强 (2-3 周) ────────────────────────────────┐ │
│  │                                                            │ │
│  ├── 主动任务识别                                        [P1]│ │
│  │   ├── ProactiveIdentifier                            5天  │ │
│  │   ├── Heartbeat 集成                                 2天  │ │
│  │   └── 通知机制                                       3天  │ │
│  │                                                            │ │
│  ├── 技能学习                                            [P2]│ │
│  │   ├── SkillLearningManager                           4天  │ │
│  │   ├── 使用统计                                       2天  │ │
│  │   └── 推荐算法                                       3天  │ │
│  │                                                            │ │
│  └── 测试验证                                            [P0]│ │
│      └── 功能测试                                       3天  │ │
│                                                              │ │
└──────────────────────────────────────────────────────────────┘ │
                                                                 │
│  Phase 4: 企业能力增强 (3-4 周) ────────────────────────────────┐ │
│  │                                                            │ │
│  ├── 安全增强                                            [P0]│ │
│  │   ├── 会话加密                                       4天  │ │
│  │   ├── 结构化审计                                     3天  │ │
│  │   ├── RBAC 权限                                      5天  │ │
│  │   └── 敏感词过滤                                     2天  │ │
│  │                                                            │ │
│  ├── 高可用部署                                          [P1]│ │
│  │   ├── Redis 会话共享                                 3天  │ │
│  │   ├── 健康检查端点                                   1天  │ │
│  │   └── Docker Compose                                 2天  │ │
│  │                                                            │ │
│  └── 前端开发                                            [P2]│ │
│      ├── Web Dashboard 基础                              10天 │ │
│      └── PWA 支持                                       3天  │ │
│                                                              │ │
└──────────────────────────────────────────────────────────────┘ │
                                                                 │
│  Phase 5: 生态完善 (持续) ──────────────────────────────────────┐ │
│  │                                                            │ │
│  ├── 文档完善                                            [P1]│ │
│  │   ├── 部署指南                                       5天  │ │
│  │   ├── 开发手册                                       5天  │ │
│  │   └── API 文档                                       3天  │ │
│  │                                                            │ │
│  ├── 社区建设                                            [P2]│ │
│  │   ├── 示例项目                                       持续 │ │
│  │   ├── 技能生态                                       持续 │ │
│  │   └── 用户反馈                                       持续 │ │
│  │                                                            │ │
│  └── 持续优化                                            [P3]│ │
│      ├── 性能优化                                       持续 │ │
│      └── Bug 修复                                       持续 │ │
│                                                              │ │
└──────────────────────────────────────────────────────────────┘ │
                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 关键里程碑

| 里程碑 | 交付物 | 验收标准 | 预计完成 |
|--------|--------|----------|----------|
| **M0: Tools→Skills** | 22 个 SKILL.md | 所有 Tools 可通过 Skills 格式描述 | Week 1 |
| **M1: ClawHub 集成** | ClawHub 客户端 + CLI | `lurkbot skills install` 正常工作 | Week 2 |
| **M2: Skills 生态** | 引入 30 个 OpenClaw Skills | 高优先级 Skills 可用 | Week 3 |
| **M3: 国内 IM 适配** | 3 个频道适配器 | 企业微信/钉钉/飞书可收发消息 | Week 5 |
| **M4: 自主能力** | 主动任务识别 + 技能学习 | Heartbeat 可推荐任务 | Week 7 |
| **M5: 企业安全** | 加密 + 审计 + RBAC | 会话加密存储，审计日志完整 | Week 10 |
| **M6: 高可用** | Docker Compose + 文档 | 可一键部署生产环境 | Week 11 |
| **M7: Dashboard** | Web 管理界面 | 可管理会话/Skills/配置 | Week 14 |

### 6.3 依赖关系图

```
M0 (Tools→Skills 转换)
    │
    ├─→ M1 (ClawHub 集成)
    │       │
    │       └─→ M2 (Skills 生态)
    │               │
    ├───────────────┘
    │
M3 (国内 IM)
    │
    ├─→ M4 (自主能力)
    │       │
    │       └─→ M5 (企业安全)
    │               │
    │               └─→ M6 (高可用)
    │                       │
    │                       └─→ M7 (Dashboard)
```

**关键路径**：M0 → M1 → M2 → M4 → M5 → M6 → M7
**并行路径**：M3 可与 M1/M2 并行开发

---

## 七、风险管理

### 7.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| **ClawHub API 变更** | 高 | 中 | 版本锁定，本地缓存，fallback 机制 |
| **国内 IM API 限制** | 高 | 中 | 多种认证方式，流量控制，错误重试 |
| **PydanticAI 兼容性** | 中 | 低 | 版本锁定，充分测试，保持上游同步 |
| **性能瓶颈** | 中 | 中 | 性能测试，异步优化，缓存策略 |
| **安全漏洞** | 高 | 低 | 代码审计，依赖扫描，及时更新 |

### 7.2 业务风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| **国内内容审核** | 高 | 高 | 敏感词过滤，人工审核接口，合规文档 |
| **企业部署权限** | 中 | 中 | 私有化部署，权限隔离，审计日志 |
| **用户数据安全** | 高 | 中 | 加密存储，访问控制，定期备份 |
| **OpenClaw 分叉** | 低 | 低 | 架构解耦，保持独立发展路线 |

### 7.3 资源风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| **开发人力不足** | 高 | 中 | 优先级排序，阶段性交付，社区贡献 |
| **测试覆盖不足** | 中 | 中 | 自动化测试，CI/CD 集成，代码审查 |
| **文档滞后** | 中 | 高 | 同步更新，文档模板，示例驱动 |

---

## 八、成功标准

### 8.1 Phase 1 验收标准

#### Step 0: Tools → Skills 转换
```bash
# 验证 SKILL.md 文件创建完成
$ ls skills/*/SKILL.md
skills/exec/SKILL.md
skills/filesystem/SKILL.md
skills/sessions/SKILL.md
skills/memory/SKILL.md
skills/web/SKILL.md
skills/messaging/SKILL.md
skills/automation/SKILL.md
skills/gateway/SKILL.md
skills/media/SKILL.md
skills/nodes/SKILL.md
skills/hooks/SKILL.md

# 验证 Skills 可被加载
$ lurkbot skills list --source local
✅ 发现 11 个本地 Skills (包装 22 个 Tools)
```

#### ClawHub 集成
```bash
# 搜索 Skills
$ lurkbot skills search "weather"
✅ 找到 5 个 Skills

# 安装 Skills
$ lurkbot skills install openclaw/weather-lookup
✅ 已安装: openclaw/weather-lookup@1.0.0

# 列出 Skills
$ lurkbot skills list
┌─────────────────┬──────────┬────────┐
│ Key             │ 来源     │ 启用   │
├─────────────────┼──────────┼────────┤
│ weather-lookup  │ clawhub  │ ✅     │
│ filesystem      │ local    │ ✅     │
└─────────────────┴──────────┴────────┘
```

#### Skills 生态引入
```bash
# 安装高优先级 Skills
$ lurkbot skills install openclaw/code-review
$ lurkbot skills install openclaw/file-manager
$ lurkbot skills install openclaw/notion

# 验证 Skills 可用
$ lurkbot skills list --source clawhub
✅ 已安装 10 个高优先级 Skills
✅ 已安装 20 个中优先级 Skills
```

### 8.2 Phase 2 验收标准

#### 国内 IM 适配
```bash
# 启动企业微信频道
$ lurkbot gateway --channel wework
✅ 企业微信频道已启动

# 发送测试消息
[用户] 你好
[Bot]  你好！我是 LurkBot，有什么可以帮你？

# 验证 Markdown 支持
[用户] 显示代码
[Bot]  ```python
       def hello():
           print("Hello!")
       ```
```

### 8.3 Phase 3 验收标准

### 8.3 Phase 3 验收标准

#### 主动任务识别
```
[Heartbeat 10:00] 检测到 3 个待处理任务:
1. [P5] 重试失败的文件备份
2. [P3] 回复 Alice 的邮件
3. [P2] 准备明天会议材料

是否需要我协助处理这些任务？
```

#### 技能推荐
```
[Agent] 你可能需要 "code-review" 技能来帮助审查代码。
        安装命令: lurkbot skills install code-review

        是否现在安装？
[用户] 是
[Agent] ✅ 已安装 code-review 技能
```

### 8.4 Phase 4 验收标准

#### 安全增强
```bash
# 验证加密
$ ls ~/.lurkbot/agents/default/sessions/
session-abc123.enc  # ✅ 加密文件

# 验证审计日志
$ lurkbot audit search --action tool.execute --user alice
┌──────────────────────┬──────────┬─────────┬────────┐
│ 时间                 │ 用户     │ 工具    │ 结果   │
├──────────────────────┼──────────┼─────────┼────────┤
│ 2026-01-31 10:15:23  │ alice    │ exec    │ 成功   │
│ 2026-01-31 10:16:45  │ alice    │ web_search│成功  │
└──────────────────────┴──────────┴─────────┴────────┘

# 验证 RBAC
$ lurkbot user assign-role bob readonly
✅ 已分配角色 "readonly" 给用户 bob

$ lurkbot --user bob agent run "删除所有文件"
❌ 错误: 用户 bob 无权限: tool:execute
```

#### 高可用部署
```bash
# Docker Compose 部署
$ docker-compose up -d
✅ 创建服务: lurkbot-1, lurkbot-2, redis, postgres, nginx

# 健康检查
$ curl http://localhost:18789/health
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 3600,
  "instances": 2
}
```

### 8.4 最终验收

| 指标 | 目标 | 验证方式 |
|------|------|----------|
| **Tools 完整度** | 22/22 (100%) | ✅ 已完成 |
| **Skills 生态** | 30/52 (58%) | Skills 安装测试 |
| **功能完整度** | 95%+ | 功能清单覆盖 |
| **测试覆盖率** | 85%+ | pytest-cov |
| **性能** | 启动 < 2s | 性能测试 |
| **文档完整性** | 100% | 文档清单 |
| **安全审计** | 无高危漏洞 | bandit + safety |

---

## 附录 A: 关键文件清单

### 需新建的文件

| 文件路径 | 说明 | Phase |
|---------|------|-------|
| `skills/exec/SKILL.md` | exec + process Tools 包装 | Phase 1 |
| `skills/filesystem/SKILL.md` | read/write/edit/patch Tools 包装 | Phase 1 |
| `skills/sessions/SKILL.md` | 6 个 session Tools 包装 | Phase 1 |
| `skills/memory/SKILL.md` | memory Tools 包装 | Phase 1 |
| `skills/web/SKILL.md` | web Tools 包装 | Phase 1 |
| `skills/messaging/SKILL.md` | message Tool 包装 | Phase 1 |
| `skills/automation/SKILL.md` | cron Tool 包装 | Phase 1 |
| `skills/gateway/SKILL.md` | gateway Tool 包装 | Phase 1 |
| `skills/media/SKILL.md` | image/tts Tools 包装 | Phase 1 |
| `skills/nodes/SKILL.md` | nodes Tool 包装 | Phase 1 |
| `skills/hooks/SKILL.md` | hooks Tool 包装 | Phase 1 |
| `src/lurkbot/skills/clawhub.py` | ClawHub 客户端 | Phase 1 |
| `src/lurkbot/skills/learning.py` | 技能学习管理 | Phase 3 |
| `src/lurkbot/cli/skills.py` | skills CLI 命令 | Phase 1 |
| `src/lurkbot/channels/wework/` | 企业微信适配器 | Phase 2 |
| `src/lurkbot/channels/dingtalk/` | 钉钉适配器 | Phase 2 |
| `src/lurkbot/channels/feishu/` | 飞书适配器 | Phase 2 |
| `src/lurkbot/autonomous/proactive/` | 主动任务识别 | Phase 3 |
| `src/lurkbot/security/encryption.py` | 会话加密 | Phase 4 |
| `src/lurkbot/security/audit.py` | 结构化审计 | Phase 4 |
| `src/lurkbot/security/rbac.py` | RBAC 权限 | Phase 4 |
| `src/lurkbot/dashboard/` | Web Dashboard | Phase 4 |

### 需修改的文件

| 文件路径 | 修改内容 | Phase |
|---------|----------|-------|
| `src/lurkbot/skills/registry.py` | 添加 ClawHub 集成 | Phase 1 |
| `src/lurkbot/agents/runtime.py` | 添加 Skills 自动安装 | Phase 1 |
| `src/lurkbot/config/channels.py` | 添加国内 IM 配置 | Phase 2 |
| `src/lurkbot/config/models.py` | 添加国内大模型 | Phase 2 |
| `src/lurkbot/sessions/store.py` | 支持加密存储 | Phase 4 |
| `pyproject.toml` | 添加依赖 | Phase 1-4 |
| `docker-compose.yml` | 高可用配置 | Phase 4 |

---

## 附录 B: 依赖更新

```toml
# pyproject.toml

[project.dependencies]
# ... 现有依赖 ...

# Phase 1: ClawHub & 国内 IM
httpx = ">=0.27.0"           # ClawHub API 客户端
wechatpy = ">=2.0.0"         # 企业微信 SDK
dingtalk-sdk = ">=2.0.0"     # 钉钉 SDK
lark-oapi = ">=1.3.0"        # 飞书 SDK

# Phase 3: 安全增强
cryptography = ">=43.0.0"    # 加密库
redis = ">=5.0.0"            # 会话共享
sqlalchemy = ">=2.0.0"       # 审计日志存储
alembic = ">=1.13.0"         # 数据库迁移

[project.optional-dependencies]
# 国内频道
cn-channels = [
    "wechatpy>=2.0.0",
    "dingtalk-sdk>=2.0.0",
    "lark-oapi>=1.3.0",
]

# 企业部署
enterprise = [
    "cryptography>=43.0.0",
    "redis>=5.0.0",
    "sqlalchemy>=2.0.0",
    "psycopg2-binary>=2.9.0",
]

# 高可用
high-availability = [
    "redis>=5.0.0",
    "prometheus-client>=0.20.0",
]
```

---

**文档结束**

> **版本**: v2.0 (重大更新：澄清 Tools vs Skills 概念差异)
> **日期**: 2026-01-31
> **作者**: Claude (Sonnet 4.5)
> **审核**: 待审核
>
> **v2.0 更新说明**:
> - 澄清核心概念：LurkBot 的 22 个 "skills" 实际是 **Tools**（系统级原子功能）
> - 更新对齐目标：从"实现缺失 Tools"调整为"建设 Skills 生态"
> - 新增 Step 0：将现有 Tools 转换为 SKILL.md 格式
> - 调整实施路线：优先完成 Tools→Skills 转换和 ClawHub 集成
> - 更新所有验收标准以反映正确的 Tools/Skills 术语
