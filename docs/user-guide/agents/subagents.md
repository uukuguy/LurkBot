# Subagents

Subagents are specialized agents that handle specific tasks. They extend LurkBot's capabilities beyond simple chat.

## Overview

The main agent can spawn subagents for:

- **Code execution** - Run and test code
- **Web browsing** - Navigate and interact with websites
- **File operations** - Complex file manipulations
- **Research** - Multi-step information gathering

## Built-in Subagents

| Subagent | Purpose | Tools |
|----------|---------|-------|
| `coder` | Write and execute code | bash, read, write, edit |
| `browser` | Web automation | browser_* tools |
| `researcher` | Information gathering | web_search, read |
| `file_manager` | File operations | read, write, glob, grep |

## How Subagents Work

```
User Message
    ↓
Main Agent (analyzes request)
    ↓
Spawns Subagent (if needed)
    ↓
Subagent executes task
    ↓
Returns result to Main Agent
    ↓
Main Agent responds to user
```

## Configuration

### Enable/Disable Subagents

```bash
# Enable all subagents
LURKBOT_SUBAGENTS_ENABLED=true

# Enable specific subagents
LURKBOT_SUBAGENTS=coder,browser,researcher
```

### Subagent Limits

```bash
# Max concurrent subagents
LURKBOT_MAX_SUBAGENTS=3

# Subagent timeout (seconds)
LURKBOT_SUBAGENT_TIMEOUT=300

# Max subagent iterations
LURKBOT_SUBAGENT_MAX_ITERATIONS=10
```

### Subagent Models

Use different models for subagents:

```bash
# Default subagent model
LURKBOT_SUBAGENT_MODEL=claude-haiku-3-5-20241022

# Per-subagent models
LURKBOT_SUBAGENT_CODER_MODEL=claude-sonnet-4-20250514
LURKBOT_SUBAGENT_BROWSER_MODEL=gpt-4o
```

## Subagent Types

### Coder Subagent

Handles code-related tasks:

```
User: Write a Python script to download images from a URL

Main Agent: I'll use the coder subagent for this.

[Coder Subagent]
- Writes Python script
- Tests execution
- Handles errors
- Returns working code
```

**Tools available:**
- `bash` - Execute commands
- `read` - Read files
- `write` - Write files
- `edit` - Edit files

### Browser Subagent

Handles web automation:

```
User: Go to example.com and fill out the contact form

Main Agent: I'll use the browser subagent for this.

[Browser Subagent]
- Navigates to URL
- Finds form elements
- Fills in fields
- Submits form
```

**Tools available:**
- `browser_navigate` - Go to URL
- `browser_click` - Click elements
- `browser_type` - Type text
- `browser_screenshot` - Capture page

### Researcher Subagent

Handles information gathering:

```
User: Research the latest Python 3.12 features

Main Agent: I'll use the researcher subagent for this.

[Researcher Subagent]
- Searches the web
- Reads documentation
- Compiles findings
- Returns summary
```

**Tools available:**
- `web_search` - Search the web
- `web_fetch` - Fetch web pages
- `read` - Read local files

### File Manager Subagent

Handles complex file operations:

```
User: Organize all images in ~/Downloads by date

Main Agent: I'll use the file_manager subagent for this.

[File Manager Subagent]
- Lists files
- Extracts dates
- Creates directories
- Moves files
```

**Tools available:**
- `glob` - Find files
- `grep` - Search content
- `read` - Read files
- `write` - Write files
- `bash` - Execute commands

## Custom Subagents

Create custom subagents via skills:

```yaml
# ~/.lurkbot/skills/my-subagent.md
---
name: my-subagent
type: subagent
tools:
  - bash
  - read
  - write
---

# My Custom Subagent

You are a specialized agent for...
```

## Subagent Communication

### Spawning Subagents

The main agent uses the `sessions_spawn` tool:

```python
# Internal API
await sessions_spawn(
    subagent="coder",
    task="Write a hello world script",
    tools=["bash", "write"]
)
```

### Subagent Results

Subagents return structured results:

```json
{
  "status": "success",
  "result": "Script created at /tmp/hello.py",
  "artifacts": ["/tmp/hello.py"],
  "iterations": 3,
  "tools_used": ["write", "bash"]
}
```

## Security

### Subagent Isolation

Subagents can be sandboxed:

```bash
# Sandbox all subagents
LURKBOT_SUBAGENT_SANDBOX=true

# Sandbox specific subagents
LURKBOT_SUBAGENT_CODER_SANDBOX=true
LURKBOT_SUBAGENT_BROWSER_SANDBOX=false
```

### Tool Restrictions

Limit tools per subagent:

```bash
# Restrict coder subagent tools
LURKBOT_SUBAGENT_CODER_TOOLS=read,write,edit

# Deny dangerous tools
LURKBOT_SUBAGENT_CODER_DENY_TOOLS=bash
```

## Monitoring

### Subagent Logs

```bash
# View subagent activity
tail -f ~/.lurkbot/logs/subagents.log
```

### Subagent Metrics

```bash
# Show subagent statistics
lurkbot subagents stats
```

Output:

```
Subagent Statistics:
  coder:      15 invocations, 95% success, avg 12s
  browser:     8 invocations, 87% success, avg 25s
  researcher:  5 invocations, 100% success, avg 18s
```

## Troubleshooting

### Subagent timeout

Increase timeout:

```bash
LURKBOT_SUBAGENT_TIMEOUT=600
```

### Subagent loops

Limit iterations:

```bash
LURKBOT_SUBAGENT_MAX_ITERATIONS=5
```

### Subagent errors

Check logs:

```bash
grep "subagent" ~/.lurkbot/logs/gateway.log
```

---

## See Also

- [AI Models](models.md) - Model configuration
- [Sessions](sessions.md) - Session management
- [Tools](../tools/index.md) - Available tools
- [Skills](../../advanced/skills.md) - Custom skills
