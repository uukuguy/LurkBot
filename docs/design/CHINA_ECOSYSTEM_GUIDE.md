# 国内生态适配使用指南

> **文档版本**: 1.0
> **更新日期**: 2026-02-01
> **适用范围**: LurkBot Phase 2 及以上版本

---

## 📋 目录

- [一、概述](#一概述)
- [二、企业通讯平台配置](#二企业通讯平台配置)
  - [2.1 企业微信 (WeWork)](#21-企业微信-wework)
  - [2.2 钉钉 (DingTalk)](#22-钉钉-dingtalk)
  - [2.3 飞书 (Feishu)](#23-飞书-feishu)
- [三、国内 LLM 配置](#三国内-llm-配置)
  - [3.1 DeepSeek (深度求索)](#31-deepseek-深度求索)
  - [3.2 Qwen (通义千问)](#32-qwen-通义千问)
  - [3.3 Kimi (月之暗面)](#33-kimi-月之暗面)
  - [3.4 ChatGLM (智谱)](#34-chatglm-智谱)
- [四、快速开始示例](#四快速开始示例)
- [五、常见问题](#五常见问题)

---

## 一、概述

LurkBot 完整支持国内企业生态系统，包括：

### 1.1 支持的企业通讯平台

| 平台 | 英文名 | 支持功能 | 状态 |
|------|--------|----------|------|
| 企业微信 | WeWork/WeCom | 文本/Markdown/图片/加密 | ✅ |
| 钉钉 | DingTalk | 文本/Markdown/卡片/@提及 | ✅ |
| 飞书 | Feishu/Lark | 文本/卡片/富文本/双模式 | ✅ |

### 1.2 支持的国内 LLM

| 提供商 | 模型数量 | 特色 | 状态 |
|--------|----------|------|------|
| DeepSeek | 3 | 推理能力强、编程专用 | ✅ |
| Qwen | 3 | 多模态、长上下文 | ✅ |
| Kimi | 3 | 超长上下文 (128K) | ✅ |
| ChatGLM | 3 | 双语对话、视觉支持 | ✅ |

---

## 二、企业通讯平台配置

### 2.1 企业微信 (WeWork)

#### 2.1.1 前置准备

1. **注册企业微信**
   - 访问: https://work.weixin.qq.com/
   - 注册企业账号

2. **创建企业应用**
   - 进入「管理后台」→「应用管理」→「创建应用」
   - 记录以下信息：
     - `Corp ID` (企业 ID)
     - `Agent ID` (应用 ID)
     - `Secret` (应用密钥)

3. **配置接收消息**
   - 进入应用详情 → 「接收消息」
   - 设置 URL、Token、EncodingAESKey
   - 记录 `Token` 和 `EncodingAESKey`

#### 2.1.2 环境变量配置

```bash
# .env 文件
WEWORK_CORP_ID="ww1234567890abcdef"
WEWORK_SECRET="your_secret_here"
WEWORK_AGENT_ID="1000001"
WEWORK_TOKEN="your_token_here"
WEWORK_ENCODING_AES_KEY="your_aes_key_here"
```

#### 2.1.3 Python 代码示例

```python
from lurkbot.channels.wework import WeWorkChannel, WeWorkConfig

# 创建配置
config = WeWorkConfig(
    corp_id="ww1234567890abcdef",
    secret="your_secret_here",
    agent_id="1000001",
    token="your_token_here",
    encoding_aes_key="your_aes_key_here"
)

# 初始化渠道
channel = WeWorkChannel(config.model_dump())

# 发送文本消息
result = await channel.send(
    channel_id="user_id",  # 用户 ID
    content="你好！我是 LurkBot"
)

# 发送 Markdown 消息
result = await channel.send_markdown(
    channel_id="user_id",
    content="# 标题\n\n**粗体** *斜体*"
)

# 上传并发送图片
media_result = channel.upload_media("image", "/path/to/image.jpg")
media_id = media_result["media_id"]
result = await channel.send_image("user_id", media_id)

# 群发消息（部门）
result = await channel.send(
    channel_id="",  # 留空
    content="部门通知",
    to_party="1|2"  # 部门 ID，用 | 分隔
)
```

#### 2.1.4 回调消息处理

```python
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/wework/callback")
async def wework_callback(request: Request):
    # 获取参数
    params = request.query_params
    signature = params.get("msg_signature")
    timestamp = params.get("timestamp")
    nonce = params.get("nonce")

    # 获取加密消息
    body = await request.body()
    raw_message = body.decode("utf-8")

    # 解密并解析消息
    msg = channel.parse_callback_message(
        raw_message, signature, timestamp, nonce
    )

    # 处理消息
    if msg.type == "text":
        print(f"收到文本: {msg.content}")
        # 回复消息
        response_xml = channel.create_callback_response(
            "收到！", msg
        )
        return Response(content=response_xml, media_type="application/xml")

    return "success"
```

---

### 2.2 钉钉 (DingTalk)

#### 2.2.1 前置准备

1. **注册钉钉开放平台**
   - 访问: https://open.dingtalk.com/
   - 创建企业内部应用

2. **获取凭证**
   - 记录 `Client ID` 和 `Client Secret`

3. **配置权限**
   - 开通「消息发送」权限
   - 配置 Stream 推送（可选）

#### 2.2.2 环境变量配置

```bash
# .env 文件
DINGTALK_CLIENT_ID="dingxxxxxxxx"
DINGTALK_CLIENT_SECRET="your_secret_here"
```

#### 2.2.3 Python 代码示例

```python
from lurkbot.channels.dingtalk import DingTalkChannel, DingTalkConfig

# 创建配置
config = DingTalkConfig(
    client_id="dingxxxxxxxx",
    client_secret="your_secret_here"
)

# 初始化渠道
channel = DingTalkChannel(config.model_dump())

# 发送文本消息
result = await channel.send(
    channel_id="conversation_id",  # 会话 ID
    content="你好！我是 LurkBot"
)

# 发送消息并 @用户
result = await channel.send(
    channel_id="conversation_id",
    content="@张三 请查看这个问题",
    at_users=["user_id_123"]  # 用户 ID 列表
)

# @所有人
result = await channel.send(
    channel_id="conversation_id",
    content="重要通知！",
    is_at_all=True
)

# 发送 Markdown 消息
result = await channel.send_markdown(
    channel_id="conversation_id",
    title="周报",
    content="# 本周工作总结\n\n- 完成功能 A\n- 修复 Bug B"
)

# 发送卡片消息
result = await channel.send_card(
    channel_id="conversation_id",
    title="任务提醒",
    text="您有一个新任务待处理",
    buttons=[
        {"title": "查看详情", "url": "https://example.com/task/123"},
        {"title": "标记完成", "url": "https://example.com/task/123/done"}
    ]
)
```

---

### 2.3 飞书 (Feishu)

#### 2.3.1 前置准备

飞书支持两种模式：

**模式 1: Webhook 模式（简单）**
1. 在飞书群聊中添加机器人
2. 获取 Webhook URL

**模式 2: OpenAPI 模式（完整功能）**
1. 访问: https://open.feishu.cn/
2. 创建企业自建应用
3. 获取 `App ID` 和 `App Secret`

#### 2.3.2 环境变量配置

```bash
# Webhook 模式
FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx"

# 或 OpenAPI 模式
FEISHU_APP_ID="cli_xxxxxxxx"
FEISHU_APP_SECRET="your_secret_here"
```

#### 2.3.3 Python 代码示例

**Webhook 模式**:

```python
from lurkbot.channels.feishu import FeishuChannel, FeishuConfig

# Webhook 配置
config = FeishuConfig(
    webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx"
)

channel = FeishuChannel(config.model_dump())

# 发送文本消息
result = await channel.send(
    channel_id="",  # Webhook 模式留空
    content="你好！我是 LurkBot"
)

# 发送卡片消息
result = await channel.send_card(
    channel_id="",
    title="任务提醒",
    content="您有一个新任务待处理",
    url="https://example.com/task/123"
)
```

**OpenAPI 模式**:

```python
# OpenAPI 配置
config = FeishuConfig(
    app_id="cli_xxxxxxxx",
    app_secret="your_secret_here"
)

channel = FeishuChannel(config.model_dump())

# 发送给用户
result = await channel.send(
    channel_id="ou_xxxxxxxx",  # 用户 Open ID
    content="你好！我是 LurkBot"
)

# 发送给群聊
result = await channel.send(
    channel_id="oc_xxxxxxxx",  # 群聊 Chat ID
    content="群聊消息"
)

# 发送富文本消息
result = await channel.send_rich_text(
    channel_id="ou_xxxxxxxx",
    title="周报",
    content=[
        [{"tag": "text", "text": "本周工作总结：\n"}],
        [{"tag": "text", "text": "1. 完成功能 A\n", "style": ["bold"]}],
        [{"tag": "text", "text": "2. 修复 Bug B\n"}],
    ]
)
```

---

## 三、国内 LLM 配置

### 3.1 DeepSeek (深度求索)

#### 3.1.1 获取 API Key

1. 访问: https://platform.deepseek.com/
2. 注册账号并创建 API Key

#### 3.1.2 环境变量配置

```bash
# .env 文件
DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
```

#### 3.1.3 使用示例

```python
from lurkbot.config.models import get_client_config
from openai import AsyncOpenAI
import os

# 获取配置
config = get_client_config('deepseek', 'deepseek-chat')

# 创建客户端
client = AsyncOpenAI(
    base_url=config["base_url"],
    api_key=os.getenv(config["api_key_env"])
)

# 调用模型
response = await client.chat.completions.create(
    model=config["model"],
    messages=[
        {"role": "user", "content": "你好！"}
    ]
)

print(response.choices[0].message.content)
```

#### 3.1.4 可用模型

| 模型 ID | 显示名称 | 特点 | 上下文 |
|---------|----------|------|--------|
| `deepseek-chat` | DeepSeek V3 | 通用模型 | 64K |
| `deepseek-reasoner` | DeepSeek R1 | 推理模型 | 64K |
| `deepseek-coder` | DeepSeek Coder | 编程专用 | 64K |

---

### 3.2 Qwen (通义千问)

#### 3.2.1 获取 API Key

1. 访问: https://dashscope.aliyun.com/
2. 开通 DashScope 服务
3. 创建 API Key

#### 3.2.2 环境变量配置

```bash
# .env 文件
DASHSCOPE_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
```

#### 3.2.3 使用示例

```python
from lurkbot.config.models import get_client_config
from openai import AsyncOpenAI
import os

# 获取配置
config = get_client_config('qwen', 'qwen3-max-2026-01-23')

# 创建客户端
client = AsyncOpenAI(
    base_url=config["base_url"],
    api_key=os.getenv(config["api_key_env"])
)

# 调用模型（支持视觉）
response = await client.chat.completions.create(
    model=config["model"],
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "这张图片里有什么？"},
                {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
            ]
        }
    ]
)

print(response.choices[0].message.content)
```

#### 3.2.4 可用模型

| 模型 ID | 显示名称 | 特点 | 上下文 |
|---------|----------|------|--------|
| `qwen3-max-2026-01-23` | Qwen3 Max | 最新多模态 | 128K |
| `qwen-plus` | Qwen Plus | 增强通用 | 128K |
| `qwen-turbo` | Qwen Turbo | 快速高效 | 8K |

---

### 3.3 Kimi (月之暗面)

#### 3.3.1 获取 API Key

1. 访问: https://platform.moonshot.cn/
2. 注册账号并创建 API Key

#### 3.3.2 环境变量配置

```bash
# .env 文件
MOONSHOT_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxx"
```

#### 3.3.3 使用示例

```python
from lurkbot.config.models import get_client_config
from openai import AsyncOpenAI
import os

# 获取配置（使用 128K 超长上下文模型）
config = get_client_config('kimi', 'moonshot-v1-128k')

# 创建客户端
client = AsyncOpenAI(
    base_url=config["base_url"],
    api_key=os.getenv(config["api_key_env"])
)

# 调用模型（支持超长上下文）
response = await client.chat.completions.create(
    model=config["model"],
    messages=[
        {"role": "user", "content": "请总结这篇长文档..."}
    ]
)

print(response.choices[0].message.content)
```

#### 3.3.4 可用模型

| 模型 ID | 显示名称 | 特点 | 上下文 |
|---------|----------|------|--------|
| `moonshot-v1-8k` | Kimi 8K | 标准版 | 8K |
| `moonshot-v1-32k` | Kimi 32K | 长上下文 | 32K |
| `moonshot-v1-128k` | Kimi 128K | 超长上下文 | 128K |

---

### 3.4 ChatGLM (智谱)

#### 3.4.1 获取 API Key

1. 访问: https://open.bigmodel.cn/
2. 注册账号并创建 API Key

#### 3.4.2 环境变量配置

```bash
# .env 文件
ZHIPUAI_API_KEY="xxxxxxxxxxxxxxxxxxxxxxxx.xxxxxxxx"
```

#### 3.4.3 使用示例

```python
from lurkbot.config.models import get_client_config
from openai import AsyncOpenAI
import os

# 获取配置
config = get_client_config('glm', 'glm-4-plus')

# 创建客户端
client = AsyncOpenAI(
    base_url=config["base_url"],
    api_key=os.getenv(config["api_key_env"])
)

# 调用模型（支持视觉）
response = await client.chat.completions.create(
    model=config["model"],
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "分析这张图片"},
                {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
            ]
        }
    ]
)

print(response.choices[0].message.content)
```

#### 3.4.4 可用模型

| 模型 ID | 显示名称 | 特点 | 上下文 |
|---------|----------|------|--------|
| `glm-4-plus` | GLM-4 Plus | 增强版+视觉 | 128K |
| `glm-4` | GLM-4 | 标准版 | 128K |
| `glm-3-turbo` | GLM-3 Turbo | 快速版 | 128K |

---

## 四、快速开始示例

### 4.1 完整的企业微信机器人

```python
import asyncio
from lurkbot.channels.wework import WeWorkChannel, WeWorkConfig
from lurkbot.config.models import get_client_config
from openai import AsyncOpenAI
import os

async def main():
    # 1. 初始化企业微信渠道
    wework_config = WeWorkConfig(
        corp_id=os.getenv("WEWORK_CORP_ID"),
        secret=os.getenv("WEWORK_SECRET"),
        agent_id=os.getenv("WEWORK_AGENT_ID"),
        token=os.getenv("WEWORK_TOKEN"),
        encoding_aes_key=os.getenv("WEWORK_ENCODING_AES_KEY")
    )
    channel = WeWorkChannel(wework_config.model_dump())

    # 2. 初始化 DeepSeek LLM
    llm_config = get_client_config('deepseek', 'deepseek-chat')
    llm_client = AsyncOpenAI(
        base_url=llm_config["base_url"],
        api_key=os.getenv(llm_config["api_key_env"])
    )

    # 3. 接收用户消息（假设从回调获取）
    user_message = "你好！请介绍一下你自己"
    user_id = "user123"

    # 4. 调用 LLM 生成回复
    response = await llm_client.chat.completions.create(
        model=llm_config["model"],
        messages=[
            {"role": "system", "content": "你是一个友好的企业助手"},
            {"role": "user", "content": user_message}
        ]
    )

    reply = response.choices[0].message.content

    # 5. 发送回复到企业微信
    result = await channel.send(user_id, reply)

    if result["sent"]:
        print(f"✅ 消息已发送: {result['message_id']}")
    else:
        print(f"❌ 发送失败: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 4.2 钉钉群聊机器人

```python
import asyncio
from lurkbot.channels.dingtalk import DingTalkChannel, DingTalkConfig
from lurkbot.config.models import get_client_config
from openai import AsyncOpenAI
import os

async def main():
    # 1. 初始化钉钉渠道
    dingtalk_config = DingTalkConfig(
        client_id=os.getenv("DINGTALK_CLIENT_ID"),
        client_secret=os.getenv("DINGTALK_CLIENT_SECRET")
    )
    channel = DingTalkChannel(dingtalk_config.model_dump())

    # 2. 初始化 Qwen LLM
    llm_config = get_client_config('qwen', 'qwen3-max-2026-01-23')
    llm_client = AsyncOpenAI(
        base_url=llm_config["base_url"],
        api_key=os.getenv(llm_config["api_key_env"])
    )

    # 3. 群聊消息处理
    conversation_id = "cidxxxxxxxx"
    user_message = "@机器人 今天天气怎么样？"

    # 4. 调用 LLM
    response = await llm_client.chat.completions.create(
        model=llm_config["model"],
        messages=[
            {"role": "user", "content": user_message}
        ]
    )

    reply = response.choices[0].message.content

    # 5. 发送回复并 @用户
    result = await channel.send(
        conversation_id,
        f"@张三 {reply}",
        at_users=["user_id_123"]
    )

    print(f"✅ 消息已发送")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 五、常见问题

### 5.1 企业通讯平台

**Q: 企业微信消息发送失败，提示 "invalid signature"？**

A: 检查以下几点：
1. `Token` 和 `EncodingAESKey` 是否正确
2. 回调 URL 是否配置正确
3. 服务器时间是否同步（时间戳验证）

**Q: 钉钉机器人无法发送消息？**

A: 确认：
1. `Client ID` 和 `Client Secret` 是否正确
2. 应用是否开通「消息发送」权限
3. 会话 ID 是否有效

**Q: 飞书 Webhook 模式和 OpenAPI 模式有什么区别？**

A:
- **Webhook 模式**: 简单快速，只能发送到特定群聊，功能有限
- **OpenAPI 模式**: 功能完整，可发送给任意用户/群聊，支持更多消息类型

### 5.2 国内 LLM

**Q: DeepSeek API 调用失败，提示 "invalid api key"？**

A: 检查：
1. API Key 是否正确设置在环境变量 `DEEPSEEK_API_KEY`
2. API Key 是否已激活（需要充值）
3. 是否使用了正确的 base_url

**Q: Qwen 模型不支持视觉输入？**

A: 只有 `qwen3-max-2026-01-23` 和 `qwen-vl-plus` 支持视觉输入，其他模型仅支持文本。

**Q: Kimi 128K 模型调用很慢？**

A: 超长上下文模型处理时间较长，建议：
1. 仅在需要时使用 128K 模型
2. 对于短文本，使用 8K 或 32K 模型
3. 使用流式输出提升用户体验

**Q: ChatGLM API 返回错误码 1301？**

A: 错误码 1301 表示 API Key 无效或已过期，请：
1. 检查 `ZHIPUAI_API_KEY` 环境变量
2. 确认 API Key 格式正确（包含 `.` 分隔符）
3. 在智谱开放平台重新生成 API Key

### 5.3 通用问题

**Q: 如何查看所有可用的模型？**

A:
```python
from lurkbot.config.models import list_models, list_providers

# 查看所有提供商
providers = list_providers()
for p in providers:
    print(f"{p.display_name}: {len(p.models)} 个模型")

# 查看所有模型
models = list_models()
for m in models:
    print(f"{m.provider}:{m.model_id} - {m.display_name}")

# 仅查看国内提供商
domestic_providers = list_providers(domestic_only=True)

# 仅查看支持视觉的模型
vision_models = list_models(supports_vision=True)
```

**Q: 如何切换不同的 LLM 提供商？**

A: 只需修改 `get_client_config` 的参数：
```python
# 使用 DeepSeek
config = get_client_config('deepseek', 'deepseek-chat')

# 切换到 Qwen
config = get_client_config('qwen', 'qwen3-max-2026-01-23')

# 切换到 Kimi
config = get_client_config('kimi', 'moonshot-v1-128k')
```

**Q: 环境变量配置太多，有没有更好的管理方式？**

A: 推荐使用 `.env` 文件：
```bash
# .env
# 企业通讯平台
WEWORK_CORP_ID=xxx
WEWORK_SECRET=xxx
DINGTALK_CLIENT_ID=xxx
FEISHU_APP_ID=xxx

# 国内 LLM
DEEPSEEK_API_KEY=sk-xxx
DASHSCOPE_API_KEY=sk-xxx
MOONSHOT_API_KEY=sk-xxx
ZHIPUAI_API_KEY=xxx
```

然后使用 `python-dotenv` 加载：
```python
from dotenv import load_dotenv
load_dotenv()  # 自动加载 .env 文件
```

---

## 📚 相关文档

- [Phase 2 完成报告](./PHASE2_CHINA_ECOSYSTEM_REPORT.md)
- [LurkBot 完整设计文档](../design/LURKBOT_COMPLETE_DESIGN.md)
- [工作日志](./WORK_LOG.md)

---

**文档维护**: LurkBot Development Team
**最后更新**: 2026-02-01
