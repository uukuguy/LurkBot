# Skills

Skills are extensible plugins that add capabilities to LurkBot. They provide specialized knowledge and behaviors.

## Overview

Skills are markdown files with YAML frontmatter that define:

- **Name and description**
- **Dependencies**
- **System prompt additions**
- **Tool configurations**

## Implementation

Source: `src/lurkbot/skills/`

| 组件 | 源文件 | 描述 |
|------|--------|------|
| `SkillFrontmatter` | `frontmatter.py` | YAML Frontmatter 数据模型 |
| `SkillRegistry` | `registry.py` | 技能注册表 |
| `SkillManager` | `registry.py` | 技能生命周期管理器 |
| `SkillEntry` | `workspace.py` | 技能条目 |

## Skill Locations

Skills are loaded from multiple locations:

1. **Built-in skills**: Bundled with LurkBot
2. **User skills**: `~/.lurkbot/skills/`
3. **Workspace skills**: `.lurkbot/skills/`

## Skill Frontmatter

Source: `src/lurkbot/skills/frontmatter.py:56-69`

```python
class SkillFrontmatter(BaseModel):
    """技能 Frontmatter 数据"""

    # 基本元数据
    description: str              # 技能描述（必需）
    tags: list[str] = []          # 标签

    # 调用策略
    user_invocable: bool = True   # 用户可通过 /skill-name 调用
    disable_model_invocation: bool = False  # 禁用模型自动调用

    # Moltbot 特定元数据
    metadata: MoltbotMetadata | None  # Moltbot 元数据
```

## Moltbot Metadata

Source: `src/lurkbot/skills/frontmatter.py:43-54`

```python
class MoltbotMetadata(BaseModel):
    """Moltbot 特定元数据"""

    skill_key: str | None       # 自定义技能 key
    emoji: str | None           # 技能图标 emoji
    homepage: str | None        # 主页 URL
    primary_env: str | None     # 主要环境: node|python|go|rust
    always: bool = False        # 是否总是加载
    os: list[str] = []          # 支持的操作系统
    requires: SkillRequirements | None  # 依赖要求
    install: list[SkillInstallStep] = []  # 安装步骤
```

## Skill Requirements

Source: `src/lurkbot/skills/frontmatter.py:20-27`

```python
class SkillRequirements(BaseModel):
    """技能依赖要求"""

    bins: list[str] = []        # 必需的二进制命令
    any_bins: list[str] = []    # 任一可用的二进制命令
    env: list[str] = []         # 必需的环境变量
    config: list[str] = []      # 必需的配置项
```

## Creating a Skill

### Basic Structure

Create `~/.lurkbot/skills/my-skill.md`:

```markdown
---
description: A custom skill for specific tasks
tags:
  - custom
  - python
userInvocable: true
disableModelInvocation: false
---

# My Skill

You are an expert in [domain]. When helping users with [task]:

1. First, understand the context
2. Then, provide detailed guidance
3. Finally, verify the solution

## Guidelines

- Always follow best practices
- Provide examples when helpful
- Ask clarifying questions if needed
```

### With Dependencies

```markdown
---
description: Python development expertise
tags:
  - python
  - development
metadata: |
  {
    "moltbot": {
      "primaryEnv": "python",
      "requires": {
        "bins": ["python3", "pip"],
        "env": ["VIRTUAL_ENV"]
      }
    }
  }
---

# Python Expert

You are an expert Python developer...
```

### With Emoji and Homepage

```markdown
---
description: Kubernetes expertise
tags:
  - kubernetes
  - devops
metadata: |
  {
    "moltbot": {
      "emoji": "☸️",
      "homepage": "https://kubernetes.io",
      "primaryEnv": "node",
      "requires": {
        "bins": ["kubectl"]
      }
    }
  }
---

# Kubernetes Expert

You are an expert in Kubernetes and container orchestration...
```

## Frontmatter Parsing

Source: `src/lurkbot/skills/frontmatter.py:76-133`

技能文件必须包含 YAML Frontmatter：

```python
def parse_skill_frontmatter(content: str) -> tuple[SkillFrontmatter, str]:
    """解析技能文件的 YAML Frontmatter"""
    # 匹配 YAML Frontmatter (--- ... ---)
    pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
    match = re.match(pattern, content, re.DOTALL)

    if not match:
        raise ValueError("技能文件缺少 YAML Frontmatter (--- ... ---)")

    yaml_content = match.group(1)
    body_content = match.group(2).strip()

    # 解析 YAML
    data = yaml.safe_load(yaml_content)

    # 转换 key 格式：camelCase -> snake_case
    data = _convert_keys_to_snake_case(data)

    # 验证和构造 Pydantic 模型
    frontmatter = SkillFrontmatter(**data)

    return frontmatter, body_content
```

## Skill Registry

Source: `src/lurkbot/skills/registry.py:18-133`

```python
class SkillRegistry:
    """技能注册表"""

    def register(self, skill: SkillEntry) -> None:
        """注册技能"""

    def unregister(self, key: str) -> bool:
        """注销技能"""

    def get(self, key: str) -> SkillEntry | None:
        """获取技能"""

    def has(self, key: str) -> bool:
        """检查技能是否存在"""

    def list_all(self) -> list[SkillEntry]:
        """列出所有技能"""

    def find_by_tag(self, tag: str) -> list[SkillEntry]:
        """按标签查找技能"""

    def find_user_invocable(self) -> list[SkillEntry]:
        """查找用户可调用的技能"""

    def find_model_invocable(self) -> list[SkillEntry]:
        """查找模型可调用的技能"""
```

## Skill Manager

Source: `src/lurkbot/skills/registry.py:140-258`

```python
class SkillManager:
    """技能管理器 - 负责技能的生命周期管理"""

    def load_skills(
        self,
        workspace_root: Path | str | None = None,
        extra_dirs: list[Path | str] | None = None,
        clear: bool = True,
    ) -> int:
        """加载技能"""

    def reload_skills(self) -> int:
        """重载技能"""

    def get_skill(self, key: str) -> SkillEntry | None:
        """获取技能"""

    def list_skills(self) -> list[SkillEntry]:
        """列出所有技能"""

    def search_skills(
        self,
        tag: str | None = None,
        user_invocable: bool | None = None,
        model_invocable: bool | None = None,
    ) -> list[SkillEntry]:
        """搜索技能"""
```

### Using Skill Manager

```python
from lurkbot.skills.registry import get_skill_manager

# 获取全局管理器
manager = get_skill_manager()

# 加载技能
count = manager.load_skills(
    workspace_root="~/my-project",
    extra_dirs=["~/custom-skills"]
)
print(f"Loaded {count} skills")

# 列出所有技能
skills = manager.list_skills()
for skill in skills:
    print(f"- {skill.key}: {skill.frontmatter.description}")

# 搜索技能
python_skills = manager.search_skills(tag="python")
user_skills = manager.search_skills(user_invocable=True)
```

## Using Skills

### Automatic Loading

Skills are automatically loaded based on context:

```
User: Help me with Kubernetes deployment

[kubernetes-expert skill activated]

Claude: I'll help you with Kubernetes deployment...
```

### Manual Invocation

Invoke a skill explicitly:

```
User: /skill python-expert

[python-expert skill activated]

Claude: I'm now in Python expert mode...
```

### In Configuration

Enable skills globally:

```bash
LURKBOT_SKILLS=python-expert,kubernetes-expert,git-workflow
```

## Skill Management

### List Skills

```bash
lurkbot skills list
```

Output:

```
Available Skills:
  Built-in:
    - commit (Git commit workflow)
    - review-pr (PR review)
    - debug (Debugging assistance)

  User (~/.lurkbot/skills/):
    - python-expert (Python development)
    - kubernetes-expert (Kubernetes expertise)

  Workspace (.lurkbot/skills/):
    - project-guide (Project-specific guidance)
```

### Show Skill Details

```bash
lurkbot skills show python-expert
```

### Enable/Disable Skills

```bash
# Disable a skill
lurkbot skills disable python-expert

# Enable a skill
lurkbot skills enable python-expert
```

## Skill Install Steps

Source: `src/lurkbot/skills/frontmatter.py:29-41`

技能可以定义安装步骤：

```python
class SkillInstallStep(BaseModel):
    """技能安装步骤"""

    kind: str           # 安装类型: brew|node|go|uv|download
    id: str             # 技能 ID
    label: str          # 显示名称
    formula: str | None # Homebrew formula
    package: str | None # NPM package
    module: str | None  # Python module
    url: str | None     # 下载 URL
    bins: list[str] = []  # 生成的二进制文件
    os: list[str] = []    # 支持的操作系统
```

示例：

```markdown
---
description: Docker container management
metadata: |
  {
    "moltbot": {
      "requires": {
        "bins": ["docker"]
      },
      "install": [
        {
          "kind": "brew",
          "id": "docker",
          "label": "Docker Desktop",
          "formula": "docker",
          "bins": ["docker"],
          "os": ["darwin", "linux"]
        }
      ]
    }
  }
---
```

## Best Practices

1. **Keep skills focused**: One skill per domain
2. **Provide clear descriptions**: Help users understand what the skill does
3. **Document dependencies**: List required tools and environment variables
4. **Use appropriate tags**: Make skills discoverable
5. **Set invocation policies**: Control when skills can be invoked

## Troubleshooting

### Skill not loading

1. Check file location
2. Verify YAML frontmatter syntax
3. Check dependencies are met

```bash
lurkbot skills validate my-skill
```

### Skill conflicts

If skills conflict, the later-loaded skill takes precedence. Use unique skill keys to avoid conflicts.

---

## See Also

- [Hooks](hooks.md) - Event-driven automation
- [Gateway](gateway.md) - Gateway architecture
- [Configuration](../user-guide/configuration/index.md) - Configuration options
