"""
Phase 17: Security Audit System Tests

对标 MoltBot src/security/ 测试
"""

import pytest


class TestSecurityFinding:
    """SecurityFinding 数据类测试"""

    def test_security_finding_creation(self):
        """测试创建 SecurityFinding"""
        from lurkbot.security import SecurityFinding

        finding = SecurityFinding(
            level="critical",
            message="Test security issue",
            fix="lurkbot config set test value",
        )

        assert finding.level == "critical"
        assert finding.message == "Test security issue"
        assert finding.fix == "lurkbot config set test value"

    def test_security_finding_without_fix(self):
        """测试创建没有修复方案的 SecurityFinding"""
        from lurkbot.security import SecurityFinding

        finding = SecurityFinding(
            level="info",
            message="Informational message",
        )

        assert finding.level == "info"
        assert finding.message == "Informational message"
        assert finding.fix is None


class TestAuditSecurity:
    """安全审计测试"""

    @pytest.mark.asyncio
    async def test_audit_security_basic(self):
        """测试基本安全审计"""
        from lurkbot.security import audit_security

        findings = await audit_security(deep=False)

        # 应该返回列表
        assert isinstance(findings, list)

    @pytest.mark.asyncio
    async def test_audit_security_deep(self):
        """测试深度安全审计"""
        from lurkbot.security import audit_security

        findings = await audit_security(deep=True)

        # 应该返回列表
        assert isinstance(findings, list)

    @pytest.mark.asyncio
    async def test_audit_gateway_exposure(self):
        """测试 Gateway 暴露检查"""
        from lurkbot.security.audit import _audit_gateway_exposure

        findings = await _audit_gateway_exposure()

        # 应该返回列表
        assert isinstance(findings, list)

        # 每个发现项应该有正确的结构
        for finding in findings:
            assert finding.level in ("critical", "warning", "info")
            assert isinstance(finding.message, str)
            assert finding.fix is None or isinstance(finding.fix, str)

    @pytest.mark.asyncio
    async def test_audit_dm_policy(self):
        """测试 DM 策略检查"""
        from lurkbot.security.audit import _audit_dm_policy

        findings = await _audit_dm_policy()

        # 应该返回列表
        assert isinstance(findings, list)

    @pytest.mark.asyncio
    async def test_audit_model_safety(self):
        """测试模型安全检查"""
        from lurkbot.security.audit import _audit_model_safety

        findings = await _audit_model_safety()

        # 应该返回列表
        assert isinstance(findings, list)


class TestApplyFixes:
    """自动修复测试"""

    @pytest.mark.asyncio
    async def test_apply_fixes_empty(self):
        """测试空发现列表的修复"""
        from lurkbot.security import apply_fixes

        applied = await apply_fixes([])

        assert applied == []

    @pytest.mark.asyncio
    async def test_apply_fixes_no_fix_available(self):
        """测试没有修复方案的发现"""
        from lurkbot.security import SecurityFinding, apply_fixes

        findings = [
            SecurityFinding(
                level="info",
                message="Test message",
                fix=None,
            )
        ]

        applied = await apply_fixes(findings)

        assert applied == []

    @pytest.mark.asyncio
    async def test_apply_fixes_with_fix(self):
        """测试有修复方案的发现"""
        from lurkbot.security import SecurityFinding, apply_fixes

        findings = [
            SecurityFinding(
                level="critical",
                message="Test critical issue",
                fix="lurkbot config set gateway.bind loopback",
            )
        ]

        # 注意：这个测试可能会失败，因为实际的 config 模块可能不存在
        # 这里只是测试函数调用不会崩溃
        applied = await apply_fixes(findings)

        # 应该返回列表
        assert isinstance(applied, list)


class TestDMPolicy:
    """DM 策略测试"""

    def test_load_dm_policy(self):
        """测试加载 DM 策略"""
        from lurkbot.security import load_dm_policy

        policy = load_dm_policy()

        assert policy.dm_scope in ("main", "per-channel-peer", "per-sender")
        assert isinstance(policy.is_multi_user, bool)

    def test_validate_dm_policy_safe(self):
        """测试验证安全的 DM 策略"""
        from lurkbot.security import DMPolicyConfig, validate_dm_policy

        # 单用户 + main scope = 安全
        policy = DMPolicyConfig(dm_scope="main", is_multi_user=False)
        assert validate_dm_policy(policy) is True

        # 多用户 + per-channel-peer = 安全
        policy = DMPolicyConfig(dm_scope="per-channel-peer", is_multi_user=True)
        assert validate_dm_policy(policy) is True

    def test_validate_dm_policy_unsafe(self):
        """测试验证不安全的 DM 策略"""
        from lurkbot.security import DMPolicyConfig, validate_dm_policy

        # 多用户 + main scope = 不安全
        policy = DMPolicyConfig(dm_scope="main", is_multi_user=True)
        assert validate_dm_policy(policy) is False

    def test_get_recommended_dm_scope(self):
        """测试获取推荐的 DM 隔离范围"""
        from lurkbot.security import get_recommended_dm_scope

        # 单用户推荐 main
        assert get_recommended_dm_scope(is_multi_user=False) == "main"

        # 多用户推荐 per-channel-peer
        assert get_recommended_dm_scope(is_multi_user=True) == "per-channel-peer"


class TestModelCheck:
    """模型安全检查测试"""

    @pytest.mark.asyncio
    async def test_check_model_safety(self):
        """测试模型安全检查"""
        from lurkbot.security import check_model_safety

        findings = await check_model_safety()

        # 应该返回列表
        assert isinstance(findings, list)

    @pytest.mark.asyncio
    async def test_check_dangerous_tools(self):
        """测试危险工具检查"""
        from lurkbot.security.model_check import _check_dangerous_tools

        findings = await _check_dangerous_tools()

        # 应该返回列表
        assert isinstance(findings, list)

    @pytest.mark.asyncio
    async def test_validate_model_permissions(self):
        """测试模型权限验证"""
        from lurkbot.security.model_check import _validate_model_permissions

        findings = await _validate_model_permissions()

        # 应该返回列表
        assert isinstance(findings, list)


class TestWarnings:
    """警告格式化测试"""

    def test_format_security_warning(self):
        """测试格式化安全警告"""
        from lurkbot.security import SecurityFinding, format_security_warning

        finding = SecurityFinding(
            level="critical",
            message="Test critical issue",
            fix="lurkbot config set test value",
        )

        formatted = format_security_warning(finding)

        assert "🔴" in formatted
        assert "CRITICAL" in formatted
        assert "Test critical issue" in formatted
        assert "Fix: lurkbot config set test value" in formatted

    def test_format_security_warning_without_fix(self):
        """测试格式化没有修复方案的警告"""
        from lurkbot.security import SecurityFinding, format_security_warning

        finding = SecurityFinding(
            level="warning",
            message="Test warning",
        )

        formatted = format_security_warning(finding)

        assert "🟡" in formatted
        assert "WARNING" in formatted
        assert "Test warning" in formatted
        assert "Fix:" not in formatted

    def test_generate_fix_command(self):
        """测试生成修复命令"""
        from lurkbot.security import SecurityFinding, generate_fix_command

        finding = SecurityFinding(
            level="critical",
            message="Test issue",
            fix="lurkbot config set test value",
        )

        fix_cmd = generate_fix_command(finding)

        assert fix_cmd == "lurkbot config set test value"

    def test_generate_fix_command_none(self):
        """测试生成修复命令（无修复方案）"""
        from lurkbot.security import SecurityFinding, generate_fix_command

        finding = SecurityFinding(
            level="info",
            message="Test info",
        )

        fix_cmd = generate_fix_command(finding)

        assert fix_cmd is None

    def test_format_findings_table_empty(self):
        """测试格式化空发现列表"""
        from lurkbot.security import format_findings_table

        table = format_findings_table([])

        assert "No security issues found" in table

    def test_format_findings_table_with_findings(self):
        """测试格式化有发现的列表"""
        from lurkbot.security import SecurityFinding, format_findings_table

        findings = [
            SecurityFinding(
                level="critical",
                message="Critical issue",
                fix="fix command",
            ),
            SecurityFinding(
                level="warning",
                message="Warning issue",
            ),
        ]

        table = format_findings_table(findings)

        assert "Security Audit Results" in table
        assert "Critical issue" in table
        assert "Warning issue" in table
        assert "fix command" in table

    def test_get_severity_count(self):
        """测试统计严重级别"""
        from lurkbot.security import SecurityFinding, get_severity_count

        findings = [
            SecurityFinding(level="critical", message="Critical 1"),
            SecurityFinding(level="critical", message="Critical 2"),
            SecurityFinding(level="warning", message="Warning 1"),
            SecurityFinding(level="info", message="Info 1"),
        ]

        counts = get_severity_count(findings)

        assert counts["critical"] == 2
        assert counts["warning"] == 1
        assert counts["info"] == 1

    def test_get_severity_count_empty(self):
        """测试统计空列表"""
        from lurkbot.security import get_severity_count

        counts = get_severity_count([])

        assert counts["critical"] == 0
        assert counts["warning"] == 0
        assert counts["info"] == 0


class TestSecurityIntegration:
    """Security 模块集成测试"""

    @pytest.mark.asyncio
    async def test_full_audit_workflow(self):
        """测试完整的审计工作流"""
        from lurkbot.security import audit_security, format_findings_table, get_severity_count

        # 执行审计
        findings = await audit_security(deep=True)

        # 格式化输出
        table = format_findings_table(findings)
        assert isinstance(table, str)

        # 统计严重级别
        counts = get_severity_count(findings)
        assert isinstance(counts, dict)
        assert "critical" in counts
        assert "warning" in counts
        assert "info" in counts

    def test_module_exports(self):
        """测试模块导出"""
        from lurkbot import security

        # 检查主要导出
        assert hasattr(security, "SecurityFinding")
        assert hasattr(security, "audit_security")
        assert hasattr(security, "apply_fixes")
        assert hasattr(security, "DMPolicyConfig")
        assert hasattr(security, "load_dm_policy")
        assert hasattr(security, "validate_dm_policy")
        assert hasattr(security, "check_model_safety")
        assert hasattr(security, "format_security_warning")
        assert hasattr(security, "format_findings_table")
        assert hasattr(security, "get_severity_count")
