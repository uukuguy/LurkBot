"""通知服务

提供多渠道告警通知功能。
"""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import httpx
from loguru import logger
from pydantic import BaseModel, Field

from .models import Alert, AlertSeverity, NotificationChannel


# ============================================================================
# 通知渠道抽象基类
# ============================================================================


class NotificationChannelBase(ABC):
    """通知渠道抽象基类"""

    @property
    @abstractmethod
    def channel_type(self) -> NotificationChannel:
        """渠道类型"""
        pass

    @abstractmethod
    async def send(
        self,
        alert: Alert,
        recipients: list[str] | None = None,
    ) -> bool:
        """发送通知

        Args:
            alert: 告警
            recipients: 接收者列表

        Returns:
            是否成功
        """
        pass

    def format_message(self, alert: Alert) -> str:
        """格式化消息

        Args:
            alert: 告警

        Returns:
            格式化后的消息
        """
        severity_emoji = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.ERROR: "❌",
            AlertSeverity.CRITICAL: "🚨",
        }

        emoji = severity_emoji.get(alert.severity, "📢")
        return (
            f"{emoji} [{alert.severity.value.upper()}] {alert.title}\n\n"
            f"{alert.message}\n\n"
            f"租户: {alert.tenant_id}\n"
            f"时间: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )


# ============================================================================
# 系统事件渠道
# ============================================================================


class SystemEventChannel(NotificationChannelBase):
    """系统事件渠道

    将告警发送到系统事件队列。
    """

    def __init__(self) -> None:
        """初始化系统事件渠道"""
        self._event_queue: list[dict[str, Any]] = []

    @property
    def channel_type(self) -> NotificationChannel:
        return NotificationChannel.SYSTEM_EVENT

    async def send(
        self,
        alert: Alert,
        recipients: list[str] | None = None,
    ) -> bool:
        """发送到系统事件队列"""
        try:
            event = {
                "type": "alert",
                "alert_id": alert.alert_id,
                "tenant_id": alert.tenant_id,
                "severity": alert.severity.value,
                "title": alert.title,
                "message": alert.message,
                "timestamp": alert.triggered_at.isoformat(),
            }
            self._event_queue.append(event)

            # 尝试使用系统事件队列（如果可用）
            try:
                from ...infra.system_events import enqueue_system_event

                enqueue_system_event(
                    text=self.format_message(alert),
                    session_key=alert.tenant_id,
                )
            except ImportError:
                pass

            logger.debug(f"发送系统事件: alert={alert.alert_id}")
            return True

        except Exception as e:
            logger.error(f"发送系统事件失败: {e}")
            return False

    def get_events(self, tenant_id: str | None = None) -> list[dict[str, Any]]:
        """获取事件列表

        Args:
            tenant_id: 租户 ID（可选）

        Returns:
            事件列表
        """
        if tenant_id:
            return [e for e in self._event_queue if e.get("tenant_id") == tenant_id]
        return self._event_queue.copy()

    def clear_events(self) -> None:
        """清空事件列表"""
        self._event_queue.clear()


# ============================================================================
# Webhook 渠道
# ============================================================================


class WebhookConfig(BaseModel):
    """Webhook 配置"""

    url: str = Field(description="Webhook URL")
    method: str = Field(default="POST", description="HTTP 方法")
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="HTTP 头",
    )
    timeout: int = Field(default=10, description="超时时间（秒）")


class WebhookChannel(NotificationChannelBase):
    """Webhook 渠道

    通过 HTTP Webhook 发送通知。
    """

    def __init__(self, config: WebhookConfig) -> None:
        """初始化 Webhook 渠道

        Args:
            config: Webhook 配置
        """
        self._config = config

    @property
    def channel_type(self) -> NotificationChannel:
        return NotificationChannel.WEBHOOK

    async def send(
        self,
        alert: Alert,
        recipients: list[str] | None = None,
    ) -> bool:
        """发送 Webhook 通知"""
        try:
            payload = {
                "alert_id": alert.alert_id,
                "tenant_id": alert.tenant_id,
                "alert_type": alert.alert_type.value,
                "severity": alert.severity.value,
                "title": alert.title,
                "message": alert.message,
                "triggered_at": alert.triggered_at.isoformat(),
                "context": alert.context,
            }

            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=self._config.method,
                    url=self._config.url,
                    json=payload,
                    headers=self._config.headers,
                    timeout=self._config.timeout,
                )
                response.raise_for_status()

            logger.debug(f"发送 Webhook 通知: alert={alert.alert_id}")
            return True

        except Exception as e:
            logger.error(f"发送 Webhook 通知失败: {e}")
            return False


# ============================================================================
# 钉钉渠道
# ============================================================================


class DingTalkConfig(BaseModel):
    """钉钉配置"""

    webhook_url: str = Field(description="钉钉机器人 Webhook URL")
    secret: str | None = Field(default=None, description="加签密钥")
    at_mobiles: list[str] = Field(
        default_factory=list,
        description="@的手机号列表",
    )
    at_all: bool = Field(default=False, description="是否@所有人")


class DingTalkChannel(NotificationChannelBase):
    """钉钉渠道

    通过钉钉机器人发送通知。
    """

    def __init__(self, config: DingTalkConfig) -> None:
        """初始化钉钉渠道

        Args:
            config: 钉钉配置
        """
        self._config = config

    @property
    def channel_type(self) -> NotificationChannel:
        return NotificationChannel.DINGTALK

    async def send(
        self,
        alert: Alert,
        recipients: list[str] | None = None,
    ) -> bool:
        """发送钉钉通知"""
        try:
            # 构建消息
            message = self._build_message(alert)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._config.webhook_url,
                    json=message,
                    timeout=10,
                )
                response.raise_for_status()

                result = response.json()
                if result.get("errcode") != 0:
                    logger.error(f"钉钉返回错误: {result}")
                    return False

            logger.debug(f"发送钉钉通知: alert={alert.alert_id}")
            return True

        except Exception as e:
            logger.error(f"发送钉钉通知失败: {e}")
            return False

    def _build_message(self, alert: Alert) -> dict[str, Any]:
        """构建钉钉消息

        Args:
            alert: 告警

        Returns:
            钉钉消息格式
        """
        severity_color = {
            AlertSeverity.INFO: "#1890ff",
            AlertSeverity.WARNING: "#faad14",
            AlertSeverity.ERROR: "#ff4d4f",
            AlertSeverity.CRITICAL: "#cf1322",
        }

        color = severity_color.get(alert.severity, "#1890ff")

        return {
            "msgtype": "markdown",
            "markdown": {
                "title": alert.title,
                "text": (
                    f"### {alert.title}\n\n"
                    f"> **级别**: {alert.severity.value}\n\n"
                    f"> **租户**: {alert.tenant_id}\n\n"
                    f"> **时间**: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"---\n\n"
                    f"{alert.message}"
                ),
            },
            "at": {
                "atMobiles": self._config.at_mobiles,
                "isAtAll": self._config.at_all,
            },
        }


# ============================================================================
# 飞书渠道
# ============================================================================


class FeishuConfig(BaseModel):
    """飞书配置"""

    webhook_url: str = Field(description="飞书机器人 Webhook URL")
    secret: str | None = Field(default=None, description="签名密钥")


class FeishuChannel(NotificationChannelBase):
    """飞书渠道

    通过飞书机器人发送通知。
    """

    def __init__(self, config: FeishuConfig) -> None:
        """初始化飞书渠道

        Args:
            config: 飞书配置
        """
        self._config = config

    @property
    def channel_type(self) -> NotificationChannel:
        return NotificationChannel.FEISHU

    async def send(
        self,
        alert: Alert,
        recipients: list[str] | None = None,
    ) -> bool:
        """发送飞书通知"""
        try:
            message = self._build_message(alert)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._config.webhook_url,
                    json=message,
                    timeout=10,
                )
                response.raise_for_status()

                result = response.json()
                if result.get("code") != 0:
                    logger.error(f"飞书返回错误: {result}")
                    return False

            logger.debug(f"发送飞书通知: alert={alert.alert_id}")
            return True

        except Exception as e:
            logger.error(f"发送飞书通知失败: {e}")
            return False

    def _build_message(self, alert: Alert) -> dict[str, Any]:
        """构建飞书消息

        Args:
            alert: 告警

        Returns:
            飞书消息格式
        """
        severity_color = {
            AlertSeverity.INFO: "blue",
            AlertSeverity.WARNING: "yellow",
            AlertSeverity.ERROR: "red",
            AlertSeverity.CRITICAL: "red",
        }

        color = severity_color.get(alert.severity, "blue")

        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": alert.title,
                    },
                    "template": color,
                },
                "elements": [
                    {
                        "tag": "div",
                        "fields": [
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**级别**: {alert.severity.value}",
                                },
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**租户**: {alert.tenant_id}",
                                },
                            },
                        ],
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": alert.message,
                        },
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": f"时间: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}",
                            },
                        ],
                    },
                ],
            },
        }


# ============================================================================
# 企业微信渠道
# ============================================================================


class WeWorkConfig(BaseModel):
    """企业微信配置"""

    webhook_url: str = Field(description="企业微信机器人 Webhook URL")
    mentioned_list: list[str] = Field(
        default_factory=list,
        description="@的用户 ID 列表",
    )
    mentioned_mobile_list: list[str] = Field(
        default_factory=list,
        description="@的手机号列表",
    )


class WeWorkChannel(NotificationChannelBase):
    """企业微信渠道

    通过企业微信机器人发送通知。
    """

    def __init__(self, config: WeWorkConfig) -> None:
        """初始化企业微信渠道

        Args:
            config: 企业微信配置
        """
        self._config = config

    @property
    def channel_type(self) -> NotificationChannel:
        return NotificationChannel.WEWORK

    async def send(
        self,
        alert: Alert,
        recipients: list[str] | None = None,
    ) -> bool:
        """发送企业微信通知"""
        try:
            message = self._build_message(alert)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self._config.webhook_url,
                    json=message,
                    timeout=10,
                )
                response.raise_for_status()

                result = response.json()
                if result.get("errcode") != 0:
                    logger.error(f"企业微信返回错误: {result}")
                    return False

            logger.debug(f"发送企业微信通知: alert={alert.alert_id}")
            return True

        except Exception as e:
            logger.error(f"发送企业微信通知失败: {e}")
            return False

    def _build_message(self, alert: Alert) -> dict[str, Any]:
        """构建企业微信消息

        Args:
            alert: 告警

        Returns:
            企业微信消息格式
        """
        severity_info = {
            AlertSeverity.INFO: ("info", "ℹ️"),
            AlertSeverity.WARNING: ("warning", "⚠️"),
            AlertSeverity.ERROR: ("warning", "❌"),
            AlertSeverity.CRITICAL: ("warning", "🚨"),
        }

        _, emoji = severity_info.get(alert.severity, ("info", "📢"))

        content = (
            f"{emoji} **{alert.title}**\n"
            f"> 级别: <font color=\"warning\">{alert.severity.value}</font>\n"
            f"> 租户: {alert.tenant_id}\n"
            f"> 时间: {alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"{alert.message}"
        )

        return {
            "msgtype": "markdown",
            "markdown": {
                "content": content,
                "mentioned_list": self._config.mentioned_list,
                "mentioned_mobile_list": self._config.mentioned_mobile_list,
            },
        }


# ============================================================================
# 邮件渠道
# ============================================================================


class EmailConfig(BaseModel):
    """邮件配置"""

    smtp_host: str = Field(description="SMTP 服务器地址")
    smtp_port: int = Field(default=587, description="SMTP 端口")
    username: str = Field(description="SMTP 用户名")
    password: str = Field(description="SMTP 密码")
    from_addr: str = Field(description="发件人地址")
    use_tls: bool = Field(default=True, description="是否使用 TLS")


class EmailChannel(NotificationChannelBase):
    """邮件渠道

    通过 SMTP 发送邮件通知。
    """

    def __init__(self, config: EmailConfig) -> None:
        """初始化邮件渠道

        Args:
            config: 邮件配置
        """
        self._config = config

    @property
    def channel_type(self) -> NotificationChannel:
        return NotificationChannel.EMAIL

    async def send(
        self,
        alert: Alert,
        recipients: list[str] | None = None,
    ) -> bool:
        """发送邮件通知"""
        if not recipients:
            logger.warning("邮件通知没有接收者")
            return False

        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            # 构建邮件
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[{alert.severity.value.upper()}] {alert.title}"
            msg["From"] = self._config.from_addr
            msg["To"] = ", ".join(recipients)

            # 纯文本内容
            text_content = self.format_message(alert)
            msg.attach(MIMEText(text_content, "plain", "utf-8"))

            # HTML 内容
            html_content = self._build_html(alert)
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            # 发送邮件（在线程池中执行）
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._send_email,
                msg,
                recipients,
            )

            logger.debug(f"发送邮件通知: alert={alert.alert_id}")
            return True

        except Exception as e:
            logger.error(f"发送邮件通知失败: {e}")
            return False

    def _send_email(self, msg: Any, recipients: list[str]) -> None:
        """发送邮件（同步）

        Args:
            msg: 邮件消息
            recipients: 接收者列表
        """
        import smtplib

        with smtplib.SMTP(self._config.smtp_host, self._config.smtp_port) as server:
            if self._config.use_tls:
                server.starttls()
            server.login(self._config.username, self._config.password)
            server.sendmail(self._config.from_addr, recipients, msg.as_string())

    def _build_html(self, alert: Alert) -> str:
        """构建 HTML 邮件内容

        Args:
            alert: 告警

        Returns:
            HTML 内容
        """
        severity_color = {
            AlertSeverity.INFO: "#1890ff",
            AlertSeverity.WARNING: "#faad14",
            AlertSeverity.ERROR: "#ff4d4f",
            AlertSeverity.CRITICAL: "#cf1322",
        }

        color = severity_color.get(alert.severity, "#1890ff")

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="border-left: 4px solid {color}; padding-left: 16px;">
                <h2 style="color: {color}; margin: 0 0 16px 0;">{alert.title}</h2>
                <table style="border-collapse: collapse;">
                    <tr>
                        <td style="padding: 4px 16px 4px 0; color: #666;">级别:</td>
                        <td style="padding: 4px 0;"><strong>{alert.severity.value}</strong></td>
                    </tr>
                    <tr>
                        <td style="padding: 4px 16px 4px 0; color: #666;">租户:</td>
                        <td style="padding: 4px 0;">{alert.tenant_id}</td>
                    </tr>
                    <tr>
                        <td style="padding: 4px 16px 4px 0; color: #666;">时间:</td>
                        <td style="padding: 4px 0;">{alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}</td>
                    </tr>
                </table>
                <hr style="border: none; border-top: 1px solid #eee; margin: 16px 0;">
                <p style="color: #333; line-height: 1.6;">{alert.message}</p>
            </div>
        </body>
        </html>
        """


# ============================================================================
# 通知服务
# ============================================================================


class NotificationService:
    """通知服务

    统一管理多个通知渠道。
    """

    def __init__(self) -> None:
        """初始化通知服务"""
        self._channels: dict[NotificationChannel, NotificationChannelBase] = {}
        self._default_channel = SystemEventChannel()
        self._channels[NotificationChannel.SYSTEM_EVENT] = self._default_channel

    def register_channel(self, channel: NotificationChannelBase) -> None:
        """注册通知渠道

        Args:
            channel: 通知渠道
        """
        self._channels[channel.channel_type] = channel
        logger.info(f"注册通知渠道: {channel.channel_type.value}")

    def unregister_channel(self, channel_type: NotificationChannel) -> None:
        """注销通知渠道

        Args:
            channel_type: 渠道类型
        """
        if channel_type in self._channels:
            del self._channels[channel_type]
            logger.info(f"注销通知渠道: {channel_type.value}")

    def get_channel(
        self, channel_type: NotificationChannel
    ) -> NotificationChannelBase | None:
        """获取通知渠道

        Args:
            channel_type: 渠道类型

        Returns:
            通知渠道
        """
        return self._channels.get(channel_type)

    def list_channels(self) -> list[NotificationChannel]:
        """列出所有渠道

        Returns:
            渠道类型列表
        """
        return list(self._channels.keys())

    async def send(
        self,
        alert: Alert,
        channels: list[NotificationChannel] | None = None,
        recipients: dict[NotificationChannel, list[str]] | None = None,
    ) -> dict[NotificationChannel, bool]:
        """发送通知

        Args:
            alert: 告警
            channels: 通知渠道列表（默认使用系统事件）
            recipients: 各渠道接收者

        Returns:
            各渠道发送结果
        """
        if channels is None:
            channels = [NotificationChannel.SYSTEM_EVENT]

        results: dict[NotificationChannel, bool] = {}
        recipients = recipients or {}

        for channel_type in channels:
            channel = self._channels.get(channel_type)
            if not channel:
                logger.warning(f"通知渠道未注册: {channel_type.value}")
                results[channel_type] = False
                continue

            channel_recipients = recipients.get(channel_type)
            success = await channel.send(alert, channel_recipients)
            results[channel_type] = success

        return results

    async def broadcast(
        self,
        alert: Alert,
        recipients: dict[NotificationChannel, list[str]] | None = None,
    ) -> dict[NotificationChannel, bool]:
        """广播通知到所有渠道

        Args:
            alert: 告警
            recipients: 各渠道接收者

        Returns:
            各渠道发送结果
        """
        return await self.send(
            alert=alert,
            channels=list(self._channels.keys()),
            recipients=recipients,
        )


# ============================================================================
# 全局实例
# ============================================================================


_notification_service: NotificationService | None = None


def get_notification_service() -> NotificationService:
    """获取通知服务

    Returns:
        通知服务实例
    """
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


def configure_notification_service(
    dingtalk_config: DingTalkConfig | None = None,
    feishu_config: FeishuConfig | None = None,
    wework_config: WeWorkConfig | None = None,
    email_config: EmailConfig | None = None,
    webhook_configs: list[WebhookConfig] | None = None,
) -> NotificationService:
    """配置通知服务

    Args:
        dingtalk_config: 钉钉配置
        feishu_config: 飞书配置
        wework_config: 企业微信配置
        email_config: 邮件配置
        webhook_configs: Webhook 配置列表

    Returns:
        通知服务实例
    """
    service = get_notification_service()

    if dingtalk_config:
        service.register_channel(DingTalkChannel(dingtalk_config))

    if feishu_config:
        service.register_channel(FeishuChannel(feishu_config))

    if wework_config:
        service.register_channel(WeWorkChannel(wework_config))

    if email_config:
        service.register_channel(EmailChannel(email_config))

    if webhook_configs:
        for config in webhook_configs:
            service.register_channel(WebhookChannel(config))

    return service
