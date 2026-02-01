"""审计日志记录器

提供审计事件记录功能，支持多种事件类型的便捷记录方法。
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any, Callable

from loguru import logger

from .models import (
    AuditEvent,
    AuditEventType,
    AuditResult,
    AuditSeverity,
    PolicyEvaluation,
    PolicyEvaluationResult,
    ResourceType,
)
from .storage import AuditStorage, MemoryAuditStorage


# ============================================================================
# 审计日志记录器
# ============================================================================


class AuditLogger:
    """审计日志记录器

    提供审计事件的记录功能，支持同步和异步记录。
    """

    def __init__(
        self,
        storage: AuditStorage | None = None,
        async_mode: bool = True,
        batch_size: int = 100,
        flush_interval: float = 5.0,
    ) -> None:
        """初始化审计日志记录器

        Args:
            storage: 审计存储（可选，默认使用内存存储）
            async_mode: 是否异步记录
            batch_size: 批量写入大小
            flush_interval: 刷新间隔（秒）
        """
        self._storage = storage or MemoryAuditStorage()
        self._async_mode = async_mode
        self._batch_size = batch_size
        self._flush_interval = flush_interval

        # 事件缓冲区
        self._event_buffer: list[AuditEvent] = []
        self._evaluation_buffer: list[PolicyEvaluation] = []
        self._lock = asyncio.Lock()

        # 后台任务
        self._flush_task: asyncio.Task | None = None
        self._running = False

        # 事件处理器
        self._event_handlers: list[Callable[[AuditEvent], Any]] = []
        self._evaluation_handlers: list[Callable[[PolicyEvaluation], Any]] = []

        logger.info("审计日志记录器初始化完成")

    # =========================================================================
    # 生命周期管理
    # =========================================================================

    async def start(self) -> None:
        """启动记录器"""
        if self._running:
            return

        self._running = True

        if self._async_mode:
            self._flush_task = asyncio.create_task(self._flush_loop())
            logger.info("审计日志记录器已启动（异步模式）")
        else:
            logger.info("审计日志记录器已启动（同步模式）")

    async def stop(self) -> None:
        """停止记录器"""
        if not self._running:
            return

        self._running = False

        # 停止刷新任务
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None

        # 刷新剩余事件
        await self._flush()

        logger.info("审计日志记录器已停止")

    async def __aenter__(self) -> "AuditLogger":
        """异步上下文管理器入口"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器出口"""
        await self.stop()

    # =========================================================================
    # 属性
    # =========================================================================

    @property
    def storage(self) -> AuditStorage:
        """获取存储"""
        return self._storage

    @property
    def is_running(self) -> bool:
        """检查是否运行中"""
        return self._running

    # =========================================================================
    # 事件处理器
    # =========================================================================

    def add_event_handler(self, handler: Callable[[AuditEvent], Any]) -> None:
        """添加事件处理器

        Args:
            handler: 事件处理函数
        """
        self._event_handlers.append(handler)

    def add_evaluation_handler(self, handler: Callable[[PolicyEvaluation], Any]) -> None:
        """添加策略评估处理器

        Args:
            handler: 评估处理函数
        """
        self._evaluation_handlers.append(handler)

    # =========================================================================
    # 通用事件记录
    # =========================================================================

    async def log_event(
        self,
        event_type: AuditEventType,
        action: str,
        *,
        tenant_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        client_ip: str | None = None,
        user_agent: str | None = None,
        resource_type: ResourceType | None = None,
        resource_id: str | None = None,
        resource_name: str | None = None,
        result: AuditResult = AuditResult.SUCCESS,
        result_code: int | None = None,
        error_message: str | None = None,
        old_value: Any = None,
        new_value: Any = None,
        changes: dict[str, Any] | None = None,
        request_id: str | None = None,
        request_method: str | None = None,
        request_path: str | None = None,
        request_params: dict[str, Any] | None = None,
        response_status: int | None = None,
        response_time_ms: float | None = None,
        severity: AuditSeverity = AuditSeverity.INFO,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        parent_event_id: str | None = None,
        correlation_id: str | None = None,
    ) -> AuditEvent:
        """记录审计事件

        Args:
            event_type: 事件类型
            action: 操作名称
            tenant_id: 租户 ID
            user_id: 用户 ID
            session_id: 会话 ID
            client_ip: 客户端 IP
            user_agent: 用户代理
            resource_type: 资源类型
            resource_id: 资源 ID
            resource_name: 资源名称
            result: 操作结果
            result_code: 结果代码
            error_message: 错误信息
            old_value: 变更前的值
            new_value: 变更后的值
            changes: 变更详情
            request_id: 请求 ID
            request_method: 请求方法
            request_path: 请求路径
            request_params: 请求参数
            response_status: 响应状态码
            response_time_ms: 响应时间
            severity: 严重级别
            metadata: 元数据
            tags: 标签
            parent_event_id: 父事件 ID
            correlation_id: 关联 ID

        Returns:
            创建的审计事件
        """
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            severity=severity,
            timestamp=datetime.now(),
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            client_ip=client_ip,
            user_agent=user_agent,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            result=result,
            result_code=result_code,
            error_message=error_message,
            old_value=old_value,
            new_value=new_value,
            changes=changes or {},
            request_id=request_id,
            request_method=request_method,
            request_path=request_path,
            request_params=request_params or {},
            response_status=response_status,
            response_time_ms=response_time_ms,
            metadata=metadata or {},
            tags=tags or [],
            parent_event_id=parent_event_id,
            correlation_id=correlation_id,
        )

        await self._record_event(event)
        return event

    # =========================================================================
    # 便捷记录方法
    # =========================================================================

    async def log_api_call(
        self,
        action: str,
        *,
        tenant_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        client_ip: str | None = None,
        request_method: str | None = None,
        request_path: str | None = None,
        request_params: dict[str, Any] | None = None,
        response_status: int | None = None,
        response_time_ms: float | None = None,
        result: AuditResult = AuditResult.SUCCESS,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """记录 API 调用

        Args:
            action: 操作名称
            tenant_id: 租户 ID
            user_id: 用户 ID
            session_id: 会话 ID
            client_ip: 客户端 IP
            request_method: 请求方法
            request_path: 请求路径
            request_params: 请求参数
            response_status: 响应状态码
            response_time_ms: 响应时间
            result: 操作结果
            error_message: 错误信息
            metadata: 元数据

        Returns:
            创建的审计事件
        """
        event_type = AuditEventType.API_CALL if result == AuditResult.SUCCESS else AuditEventType.API_ERROR
        severity = AuditSeverity.INFO if result == AuditResult.SUCCESS else AuditSeverity.ERROR

        return await self.log_event(
            event_type=event_type,
            action=action,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            client_ip=client_ip,
            resource_type=ResourceType.API,
            request_method=request_method,
            request_path=request_path,
            request_params=request_params,
            response_status=response_status,
            response_time_ms=response_time_ms,
            result=result,
            error_message=error_message,
            severity=severity,
            metadata=metadata,
        )

    async def log_config_change(
        self,
        action: str,
        *,
        tenant_id: str | None = None,
        user_id: str | None = None,
        config_type: str | None = None,
        config_id: str | None = None,
        config_name: str | None = None,
        old_value: Any = None,
        new_value: Any = None,
        changes: dict[str, Any] | None = None,
        result: AuditResult = AuditResult.SUCCESS,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """记录配置变更

        Args:
            action: 操作名称
            tenant_id: 租户 ID
            user_id: 用户 ID
            config_type: 配置类型
            config_id: 配置 ID
            config_name: 配置名称
            old_value: 变更前的值
            new_value: 变更后的值
            changes: 变更详情
            result: 操作结果
            error_message: 错误信息
            metadata: 元数据

        Returns:
            创建的审计事件
        """
        # 确定事件类型
        if "create" in action.lower():
            event_type = AuditEventType.CONFIG_CREATE
        elif "delete" in action.lower():
            event_type = AuditEventType.CONFIG_DELETE
        else:
            event_type = AuditEventType.CONFIG_UPDATE

        return await self.log_event(
            event_type=event_type,
            action=action,
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type=ResourceType.CONFIG,
            resource_id=config_id,
            resource_name=config_name,
            old_value=old_value,
            new_value=new_value,
            changes=changes,
            result=result,
            error_message=error_message,
            severity=AuditSeverity.WARNING,
            metadata={**(metadata or {}), "config_type": config_type} if config_type else metadata,
        )

    async def log_permission_change(
        self,
        action: str,
        *,
        tenant_id: str | None = None,
        user_id: str | None = None,
        target_user_id: str | None = None,
        permission: str | None = None,
        role: str | None = None,
        old_value: Any = None,
        new_value: Any = None,
        result: AuditResult = AuditResult.SUCCESS,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """记录权限变更

        Args:
            action: 操作名称
            tenant_id: 租户 ID
            user_id: 操作者用户 ID
            target_user_id: 目标用户 ID
            permission: 权限名称
            role: 角色名称
            old_value: 变更前的值
            new_value: 变更后的值
            result: 操作结果
            error_message: 错误信息
            metadata: 元数据

        Returns:
            创建的审计事件
        """
        # 确定事件类型
        if "grant" in action.lower():
            event_type = AuditEventType.PERMISSION_GRANT
        elif "revoke" in action.lower():
            event_type = AuditEventType.PERMISSION_REVOKE
        elif "assign" in action.lower():
            event_type = AuditEventType.ROLE_ASSIGN
        elif "remove" in action.lower():
            event_type = AuditEventType.ROLE_REMOVE
        else:
            event_type = AuditEventType.PERMISSION_GRANT

        return await self.log_event(
            event_type=event_type,
            action=action,
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type=ResourceType.PERMISSION,
            resource_id=target_user_id,
            resource_name=permission or role,
            old_value=old_value,
            new_value=new_value,
            result=result,
            error_message=error_message,
            severity=AuditSeverity.WARNING,
            metadata={
                **(metadata or {}),
                "target_user_id": target_user_id,
                "permission": permission,
                "role": role,
            },
        )

    async def log_security_event(
        self,
        action: str,
        event_type: AuditEventType,
        *,
        tenant_id: str | None = None,
        user_id: str | None = None,
        client_ip: str | None = None,
        user_agent: str | None = None,
        result: AuditResult = AuditResult.SUCCESS,
        error_message: str | None = None,
        severity: AuditSeverity = AuditSeverity.WARNING,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """记录安全事件

        Args:
            action: 操作名称
            event_type: 事件类型
            tenant_id: 租户 ID
            user_id: 用户 ID
            client_ip: 客户端 IP
            user_agent: 用户代理
            result: 操作结果
            error_message: 错误信息
            severity: 严重级别
            metadata: 元数据

        Returns:
            创建的审计事件
        """
        return await self.log_event(
            event_type=event_type,
            action=action,
            tenant_id=tenant_id,
            user_id=user_id,
            client_ip=client_ip,
            user_agent=user_agent,
            result=result,
            error_message=error_message,
            severity=severity,
            metadata=metadata,
            tags=["security"],
        )

    async def log_tenant_operation(
        self,
        action: str,
        event_type: AuditEventType,
        *,
        tenant_id: str,
        user_id: str | None = None,
        old_value: Any = None,
        new_value: Any = None,
        changes: dict[str, Any] | None = None,
        result: AuditResult = AuditResult.SUCCESS,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """记录租户操作

        Args:
            action: 操作名称
            event_type: 事件类型
            tenant_id: 租户 ID
            user_id: 用户 ID
            old_value: 变更前的值
            new_value: 变更后的值
            changes: 变更详情
            result: 操作结果
            error_message: 错误信息
            metadata: 元数据

        Returns:
            创建的审计事件
        """
        return await self.log_event(
            event_type=event_type,
            action=action,
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type=ResourceType.TENANT,
            resource_id=tenant_id,
            old_value=old_value,
            new_value=new_value,
            changes=changes,
            result=result,
            error_message=error_message,
            severity=AuditSeverity.WARNING,
            metadata=metadata,
        )

    async def log_data_operation(
        self,
        action: str,
        event_type: AuditEventType,
        *,
        tenant_id: str | None = None,
        user_id: str | None = None,
        data_type: str | None = None,
        data_id: str | None = None,
        data_name: str | None = None,
        record_count: int | None = None,
        result: AuditResult = AuditResult.SUCCESS,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """记录数据操作

        Args:
            action: 操作名称
            event_type: 事件类型
            tenant_id: 租户 ID
            user_id: 用户 ID
            data_type: 数据类型
            data_id: 数据 ID
            data_name: 数据名称
            record_count: 记录数量
            result: 操作结果
            error_message: 错误信息
            metadata: 元数据

        Returns:
            创建的审计事件
        """
        return await self.log_event(
            event_type=event_type,
            action=action,
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type=ResourceType.DATA,
            resource_id=data_id,
            resource_name=data_name,
            result=result,
            error_message=error_message,
            severity=AuditSeverity.INFO,
            metadata={
                **(metadata or {}),
                "data_type": data_type,
                "record_count": record_count,
            },
        )

    # =========================================================================
    # 策略评估记录
    # =========================================================================

    async def log_policy_evaluation(
        self,
        action: str,
        resource_type: str,
        result: PolicyEvaluationResult,
        *,
        tenant_id: str,
        user_id: str | None = None,
        session_id: str | None = None,
        resource_id: str | None = None,
        context: dict[str, Any] | None = None,
        decision_reason: str = "",
        matched_policies: list[str] | None = None,
        matched_rules: list[str] | None = None,
        denial_code: str | None = None,
        denial_message: str | None = None,
        denial_policy_id: str | None = None,
        denial_rule_id: str | None = None,
        evaluation_time_ms: float = 0.0,
        policies_evaluated: int = 0,
        rules_evaluated: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> PolicyEvaluation:
        """记录策略评估

        Args:
            action: 请求的操作
            resource_type: 资源类型
            result: 评估结果
            tenant_id: 租户 ID
            user_id: 用户 ID
            session_id: 会话 ID
            resource_id: 资源 ID
            context: 评估上下文
            decision_reason: 决策原因
            matched_policies: 匹配的策略列表
            matched_rules: 匹配的规则列表
            denial_code: 拒绝代码
            denial_message: 拒绝消息
            denial_policy_id: 拒绝策略 ID
            denial_rule_id: 拒绝规则 ID
            evaluation_time_ms: 评估耗时
            policies_evaluated: 评估的策略数
            rules_evaluated: 评估的规则数
            metadata: 元数据

        Returns:
            创建的策略评估记录
        """
        evaluation = PolicyEvaluation(
            evaluation_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            context=context or {},
            result=result,
            decision_reason=decision_reason,
            matched_policies=matched_policies or [],
            matched_rules=matched_rules or [],
            denial_code=denial_code,
            denial_message=denial_message,
            denial_policy_id=denial_policy_id,
            denial_rule_id=denial_rule_id,
            evaluation_time_ms=evaluation_time_ms,
            policies_evaluated=policies_evaluated,
            rules_evaluated=rules_evaluated,
            metadata=metadata or {},
        )

        await self._record_evaluation(evaluation)

        # 同时记录审计事件
        event_type = (
            AuditEventType.POLICY_ALLOW
            if result == PolicyEvaluationResult.ALLOW
            else AuditEventType.POLICY_DENY
            if result == PolicyEvaluationResult.DENY
            else AuditEventType.POLICY_EVALUATE
        )

        await self.log_event(
            event_type=event_type,
            action=f"policy_evaluation:{action}",
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
            resource_type=ResourceType.POLICY,
            resource_id=resource_id,
            result=AuditResult.SUCCESS if result == PolicyEvaluationResult.ALLOW else AuditResult.DENIED,
            error_message=denial_message,
            severity=AuditSeverity.INFO if result == PolicyEvaluationResult.ALLOW else AuditSeverity.WARNING,
            metadata={
                "evaluation_id": evaluation.evaluation_id,
                "matched_policies": matched_policies,
                "denial_code": denial_code,
            },
        )

        return evaluation

    # =========================================================================
    # 内部方法
    # =========================================================================

    async def _record_event(self, event: AuditEvent) -> None:
        """记录事件"""
        # 调用处理器
        for handler in self._event_handlers:
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"事件处理器执行失败: {e}")

        if self._async_mode:
            # 异步模式：添加到缓冲区
            async with self._lock:
                self._event_buffer.append(event)

                # 检查是否需要刷新
                if len(self._event_buffer) >= self._batch_size:
                    await self._flush_events()
        else:
            # 同步模式：直接写入
            await self._storage.save_event(event)

    async def _record_evaluation(self, evaluation: PolicyEvaluation) -> None:
        """记录策略评估"""
        # 调用处理器
        for handler in self._evaluation_handlers:
            try:
                result = handler(evaluation)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"评估处理器执行失败: {e}")

        if self._async_mode:
            # 异步模式：添加到缓冲区
            async with self._lock:
                self._evaluation_buffer.append(evaluation)

                # 检查是否需要刷新
                if len(self._evaluation_buffer) >= self._batch_size:
                    await self._flush_evaluations()
        else:
            # 同步模式：直接写入
            await self._storage.save_policy_evaluation(evaluation)

    async def _flush_loop(self) -> None:
        """刷新循环"""
        while self._running:
            try:
                await asyncio.sleep(self._flush_interval)
                await self._flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"刷新审计日志失败: {e}")

    async def _flush(self) -> None:
        """刷新所有缓冲区"""
        await self._flush_events()
        await self._flush_evaluations()

    async def _flush_events(self) -> None:
        """刷新事件缓冲区"""
        async with self._lock:
            if not self._event_buffer:
                return

            events = self._event_buffer.copy()
            self._event_buffer.clear()

        # 批量写入
        for event in events:
            try:
                await self._storage.save_event(event)
            except Exception as e:
                logger.error(f"保存审计事件失败: {e}")

        if events:
            logger.debug(f"刷新了 {len(events)} 条审计事件")

    async def _flush_evaluations(self) -> None:
        """刷新评估缓冲区"""
        async with self._lock:
            if not self._evaluation_buffer:
                return

            evaluations = self._evaluation_buffer.copy()
            self._evaluation_buffer.clear()

        # 批量写入
        for evaluation in evaluations:
            try:
                await self._storage.save_policy_evaluation(evaluation)
            except Exception as e:
                logger.error(f"保存策略评估记录失败: {e}")

        if evaluations:
            logger.debug(f"刷新了 {len(evaluations)} 条策略评估记录")


# ============================================================================
# 全局审计日志记录器
# ============================================================================

# 全局实例
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """获取全局审计日志记录器

    Returns:
        审计日志记录器实例
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def configure_audit_logger(
    storage: AuditStorage | None = None,
    async_mode: bool = True,
    batch_size: int = 100,
    flush_interval: float = 5.0,
) -> AuditLogger:
    """配置全局审计日志记录器

    Args:
        storage: 审计存储
        async_mode: 是否异步记录
        batch_size: 批量写入大小
        flush_interval: 刷新间隔

    Returns:
        配置后的审计日志记录器
    """
    global _audit_logger
    _audit_logger = AuditLogger(
        storage=storage,
        async_mode=async_mode,
        batch_size=batch_size,
        flush_interval=flush_interval,
    )
    return _audit_logger
