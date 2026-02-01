"""审计 API 集成测试"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lurkbot.tenants.audit.api import configure_audit_api, create_audit_router
from lurkbot.tenants.audit.models import (
    AuditEvent,
    AuditEventType,
    AuditResult,
    PolicyEvaluation,
    PolicyEvaluationResult,
)
from lurkbot.tenants.audit.storage import MemoryAuditStorage


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def storage():
    """创建内存存储"""
    return MemoryAuditStorage()


@pytest.fixture
def app(storage):
    """创建测试应用"""
    app = FastAPI()
    configure_audit_api(storage=storage)
    router = create_audit_router()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
async def populated_storage(storage):
    """填充测试数据的存储"""
    # 创建审计事件
    for i in range(10):
        await storage.save_event(AuditEvent(
            event_id=f"event-{i}",
            event_type=AuditEventType.API_CALL if i < 7 else AuditEventType.AUTH_FAILURE,
            action=f"action_{i}",
            tenant_id="tenant-1" if i < 5 else "tenant-2",
            user_id=f"user-{i % 3}",
            result=AuditResult.SUCCESS if i < 8 else AuditResult.FAILURE,
        ))

    # 创建策略评估
    for i in range(5):
        await storage.save_policy_evaluation(PolicyEvaluation(
            evaluation_id=f"eval-{i}",
            tenant_id="tenant-1",
            action="read",
            resource_type="document",
            result=PolicyEvaluationResult.ALLOW if i < 3 else PolicyEvaluationResult.DENY,
            matched_policies=["policy-1"] if i < 2 else ["policy-2"],
            denial_code="PERMISSION_DENIED" if i >= 3 else None,
        ))

    return storage


# ============================================================================
# 审计事件 API 测试
# ============================================================================


class TestAuditEventAPI:
    """审计事件 API 测试"""

    @pytest.mark.asyncio
    async def test_list_events_empty(self, client):
        """测试列出空事件列表"""
        response = client.get("/api/v1/audit/events")

        assert response.status_code == 200
        data = response.json()
        assert data["events"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_events(self, client, populated_storage):
        """测试列出事件"""
        response = client.get("/api/v1/audit/events")

        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 10
        assert data["total"] == 10

    @pytest.mark.asyncio
    async def test_list_events_with_tenant_filter(self, client, populated_storage):
        """测试按租户过滤事件"""
        response = client.get("/api/v1/audit/events?tenant_id=tenant-1")

        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 5

    @pytest.mark.asyncio
    async def test_list_events_with_type_filter(self, client, populated_storage):
        """测试按类型过滤事件"""
        response = client.get("/api/v1/audit/events?event_type=api_call")

        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 7

    @pytest.mark.asyncio
    async def test_list_events_with_pagination(self, client, populated_storage):
        """测试分页"""
        response = client.get("/api/v1/audit/events?limit=5&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 5
        assert data["limit"] == 5
        assert data["offset"] == 0

    @pytest.mark.asyncio
    async def test_get_event(self, client, populated_storage):
        """测试获取事件详情"""
        response = client.get("/api/v1/audit/events/event-0")

        assert response.status_code == 200
        data = response.json()
        assert data["event"]["event_id"] == "event-0"

    @pytest.mark.asyncio
    async def test_get_event_not_found(self, client):
        """测试获取不存在的事件"""
        response = client.get("/api/v1/audit/events/nonexistent")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_tenant_events(self, client, populated_storage):
        """测试获取租户事件"""
        response = client.get("/api/v1/audit/tenants/tenant-1/events")

        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 5


# ============================================================================
# 审计统计 API 测试
# ============================================================================


class TestAuditStatsAPI:
    """审计统计 API 测试"""

    @pytest.mark.asyncio
    async def test_get_stats(self, client, populated_storage):
        """测试获取统计"""
        response = client.get("/api/v1/audit/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["stats"]["total_events"] == 10

    @pytest.mark.asyncio
    async def test_get_tenant_stats(self, client, populated_storage):
        """测试获取租户统计"""
        response = client.get("/api/v1/audit/tenants/tenant-1/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["stats"]["total_events"] == 5


# ============================================================================
# 策略评估 API 测试
# ============================================================================


class TestPolicyEvaluationAPI:
    """策略评估 API 测试"""

    @pytest.mark.asyncio
    async def test_list_policy_evaluations(self, client, populated_storage):
        """测试列出策略评估"""
        response = client.get("/api/v1/audit/policy-evaluations")

        assert response.status_code == 200
        data = response.json()
        assert len(data["evaluations"]) == 5

    @pytest.mark.asyncio
    async def test_list_policy_evaluations_with_result_filter(self, client, populated_storage):
        """测试按结果过滤策略评估"""
        response = client.get("/api/v1/audit/policy-evaluations?result=allow")

        assert response.status_code == 200
        data = response.json()
        assert len(data["evaluations"]) == 3

    @pytest.mark.asyncio
    async def test_get_policy_evaluation_stats(self, client, populated_storage):
        """测试获取策略评估统计"""
        response = client.get("/api/v1/audit/policy-evaluations/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["stats"]["total_evaluations"] == 5
        assert data["stats"]["allow_count"] == 3
        assert data["stats"]["deny_count"] == 2

    @pytest.mark.asyncio
    async def test_get_denial_reasons(self, client, populated_storage):
        """测试获取拒绝原因"""
        response = client.get("/api/v1/audit/policy-evaluations/denial-reasons")

        assert response.status_code == 200
        data = response.json()
        assert "PERMISSION_DENIED" in data["reasons"]

    @pytest.mark.asyncio
    async def test_get_policy_hits(self, client, populated_storage):
        """测试获取策略命中统计"""
        response = client.get("/api/v1/audit/policy-evaluations/policy-hits")

        assert response.status_code == 200
        data = response.json()
        assert "policy-1" in data["stats"] or "policy-2" in data["stats"]


# ============================================================================
# 报告 API 测试
# ============================================================================


class TestReportAPI:
    """报告 API 测试"""

    @pytest.mark.asyncio
    async def test_generate_usage_report(self, client, populated_storage):
        """测试生成使用量报告"""
        response = client.get("/api/v1/audit/reports/usage")

        assert response.status_code == 200
        data = response.json()
        assert data["report"]["report_type"] == "usage"
        assert data["report"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_generate_security_report(self, client, populated_storage):
        """测试生成安全审计报告"""
        response = client.get("/api/v1/audit/reports/security")

        assert response.status_code == 200
        data = response.json()
        assert data["report"]["report_type"] == "security_audit"
        assert data["report"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_generate_compliance_report(self, client, populated_storage):
        """测试生成合规检查报告"""
        response = client.get("/api/v1/audit/reports/compliance")

        assert response.status_code == 200
        data = response.json()
        assert data["report"]["report_type"] == "compliance"
        assert data["report"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_formatted_report_markdown(self, client, populated_storage):
        """测试获取 Markdown 格式报告"""
        response = client.get("/api/v1/audit/reports/usage/formatted?format=markdown")

        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "markdown"
        assert "# 使用量报告" in data["content"]

    @pytest.mark.asyncio
    async def test_get_formatted_report_json(self, client, populated_storage):
        """测试获取 JSON 格式报告"""
        response = client.get("/api/v1/audit/reports/usage/formatted?format=json")

        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "json"

    @pytest.mark.asyncio
    async def test_get_formatted_report_invalid_type(self, client):
        """测试无效报告类型"""
        response = client.get("/api/v1/audit/reports/invalid/formatted")

        assert response.status_code == 400
