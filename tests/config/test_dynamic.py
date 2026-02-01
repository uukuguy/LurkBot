"""动态配置系统单元测试"""

import asyncio
import json
import os
import tempfile
from pathlib import Path

import pytest

from lurkbot.config.dynamic import (
    ConfigEntry,
    ConfigEvent,
    ConfigEventType,
    ConfigSnapshot,
    ConfigSource,
    ConfigStore,
    ConfigValidatorRegistry,
    ConfigVersion,
    ConfigWatcher,
    DynamicConfigManager,
    get_config_manager,
    init_config,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_config_dir():
    """创建临时配置目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def config_store():
    """创建配置存储实例"""
    return ConfigStore()


@pytest.fixture
def validator_registry():
    """创建验证器注册表"""
    return ConfigValidatorRegistry()


@pytest.fixture
async def config_manager(temp_config_dir):
    """创建配置管理器实例"""
    manager = DynamicConfigManager(temp_config_dir)
    await manager.initialize()
    yield manager
    manager.stop_watching()


# ============================================================================
# ConfigEntry Tests
# ============================================================================


class TestConfigEntry:
    """ConfigEntry 测试"""

    def test_create_entry(self):
        """测试创建配置条目"""
        entry = ConfigEntry(
            key="server.port",
            value=8080,
            source=ConfigSource.FILE,
        )

        assert entry.key == "server.port"
        assert entry.value == 8080
        assert entry.source == ConfigSource.FILE
        assert entry.priority == 0

    def test_entry_with_metadata(self):
        """测试带元数据的配置条目"""
        entry = ConfigEntry(
            key="api.key",
            value="secret",
            source=ConfigSource.ENV,
            priority=20,
            metadata={"encrypted": True},
        )

        assert entry.metadata["encrypted"] is True
        assert entry.priority == 20


# ============================================================================
# ConfigVersion Tests
# ============================================================================


class TestConfigVersion:
    """ConfigVersion 测试"""

    def test_create_version(self):
        """测试创建版本信息"""
        version = ConfigVersion(
            version="v1.0.0",
            hash="abc123",
            source=ConfigSource.FILE,
        )

        assert version.version == "v1.0.0"
        assert version.hash == "abc123"
        assert version.author == "system"


# ============================================================================
# ConfigStore Tests
# ============================================================================


class TestConfigStore:
    """ConfigStore 测试"""

    @pytest.mark.asyncio
    async def test_set_and_get(self, config_store):
        """测试设置和获取配置"""
        await config_store.set("server.port", 8080)
        value = await config_store.get("server.port")

        assert value == 8080

    @pytest.mark.asyncio
    async def test_get_default(self, config_store):
        """测试获取默认值"""
        value = await config_store.get("nonexistent", default="default")
        assert value == "default"

    @pytest.mark.asyncio
    async def test_delete(self, config_store):
        """测试删除配置"""
        await config_store.set("to_delete", "value")
        assert await config_store.get("to_delete") == "value"

        result = await config_store.delete("to_delete")
        assert result is True
        assert await config_store.get("to_delete") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, config_store):
        """测试删除不存在的配置"""
        result = await config_store.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_all(self, config_store):
        """测试获取所有配置"""
        await config_store.set("key1", "value1")
        await config_store.set("key2", "value2")

        all_values = await config_store.get_all()

        assert all_values["key1"] == "value1"
        assert all_values["key2"] == "value2"

    @pytest.mark.asyncio
    async def test_create_snapshot(self, config_store):
        """测试创建快照"""
        await config_store.set("key1", "value1")
        await config_store.set("key2", "value2")

        snapshot = await config_store.create_snapshot("v1.0.0")

        assert snapshot.version == "v1.0.0"
        assert snapshot.values["key1"] == "value1"
        assert snapshot.values["key2"] == "value2"
        assert len(snapshot.hash) == 16

    @pytest.mark.asyncio
    async def test_restore_snapshot(self, config_store):
        """测试恢复快照"""
        # 创建初始配置
        await config_store.set("key1", "value1")
        await config_store.create_snapshot("v1.0.0")

        # 修改配置
        await config_store.set("key1", "modified")
        await config_store.set("key2", "new_value")

        # 恢复快照
        result = await config_store.restore_snapshot("v1.0.0")

        assert result is True
        assert await config_store.get("key1") == "value1"
        assert await config_store.get("key2") is None

    @pytest.mark.asyncio
    async def test_restore_nonexistent_snapshot(self, config_store):
        """测试恢复不存在的快照"""
        result = await config_store.restore_snapshot("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_versions(self, config_store):
        """测试获取版本历史"""
        await config_store.create_snapshot("v1")
        await config_store.create_snapshot("v2")

        versions = await config_store.get_versions()

        assert len(versions) == 2
        assert versions[0].version == "v1"
        assert versions[1].version == "v2"


# ============================================================================
# ConfigValidatorRegistry Tests
# ============================================================================


class TestConfigValidatorRegistry:
    """ConfigValidatorRegistry 测试"""

    def test_register_and_validate(self, validator_registry):
        """测试注册和验证"""

        def port_validator(key: str, value) -> tuple[bool, str | None]:
            if not isinstance(value, int) or value < 1 or value > 65535:
                return False, "端口必须是 1-65535 之间的整数"
            return True, None

        validator_registry.register("server.port", port_validator)

        # 有效值
        is_valid, errors = validator_registry.validate("server.port", 8080)
        assert is_valid is True
        assert len(errors) == 0

        # 无效值
        is_valid, errors = validator_registry.validate("server.port", 99999)
        assert is_valid is False
        assert len(errors) == 1

    def test_wildcard_pattern(self, validator_registry):
        """测试通配符模式"""

        def positive_validator(key: str, value) -> tuple[bool, str | None]:
            if not isinstance(value, int) or value < 0:
                return False, "值必须是非负整数"
            return True, None

        validator_registry.register("timeout.*", positive_validator)

        is_valid, _ = validator_registry.validate("timeout.read", 30)
        assert is_valid is True

        is_valid, errors = validator_registry.validate("timeout.write", -1)
        assert is_valid is False

    def test_global_validator(self, validator_registry):
        """测试全局验证器"""

        def not_none_validator(key: str, value) -> tuple[bool, str | None]:
            if value is None:
                return False, f"{key} 不能为 None"
            return True, None

        validator_registry.register_global(not_none_validator)

        is_valid, _ = validator_registry.validate("any.key", "value")
        assert is_valid is True

        is_valid, errors = validator_registry.validate("any.key", None)
        assert is_valid is False


# ============================================================================
# DynamicConfigManager Tests
# ============================================================================


class TestDynamicConfigManager:
    """DynamicConfigManager 测试"""

    @pytest.mark.asyncio
    async def test_initialize(self, temp_config_dir):
        """测试初始化"""
        manager = DynamicConfigManager(temp_config_dir)
        await manager.initialize()

        # 检查默认配置
        value = await manager.get("server.port")
        assert value == 8080

    @pytest.mark.asyncio
    async def test_set_and_get(self, config_manager):
        """测试设置和获取"""
        result = await config_manager.set("test.key", "test_value")
        assert result is True

        value = await config_manager.get("test.key")
        assert value == "test_value"

    @pytest.mark.asyncio
    async def test_nested_key(self, config_manager):
        """测试嵌套键"""
        await config_manager.set("database", {"host": "localhost", "port": 5432})

        host = await config_manager.get("database.host")
        assert host == "localhost"

    @pytest.mark.asyncio
    async def test_delete(self, config_manager):
        """测试删除"""
        await config_manager.set("to_delete", "value")
        result = await config_manager.delete("to_delete")

        assert result is True
        assert await config_manager.get("to_delete") is None

    @pytest.mark.asyncio
    async def test_update_batch(self, config_manager):
        """测试批量更新"""
        results = await config_manager.update({
            "batch.key1": "value1",
            "batch.key2": "value2",
        })

        assert results["batch.key1"] is True
        assert results["batch.key2"] is True
        assert await config_manager.get("batch.key1") == "value1"

    @pytest.mark.asyncio
    async def test_validation_failure(self, config_manager):
        """测试验证失败"""

        def positive_only(key: str, value) -> tuple[bool, str | None]:
            if isinstance(value, int) and value < 0:
                return False, "值必须为正数"
            return True, None

        config_manager.register_validator("positive.*", positive_only)

        result = await config_manager.set("positive.value", -1)
        assert result is False

    @pytest.mark.asyncio
    async def test_create_and_rollback_snapshot(self, config_manager):
        """测试创建和回滚快照"""
        await config_manager.set("rollback.test", "original")

        version = await config_manager.create_snapshot("测试快照")
        assert version is not None

        await config_manager.set("rollback.test", "modified")
        assert await config_manager.get("rollback.test") == "modified"

        result = await config_manager.rollback(version)
        assert result is True
        assert await config_manager.get("rollback.test") == "original"

    @pytest.mark.asyncio
    async def test_get_versions(self, config_manager):
        """测试获取版本历史"""
        await config_manager.create_snapshot("v1")
        await config_manager.create_snapshot("v2")

        versions = await config_manager.get_versions()
        assert len(versions) >= 2

    @pytest.mark.asyncio
    async def test_event_handler(self, config_manager):
        """测试事件处理器"""
        events = []

        def handler(event: ConfigEvent):
            events.append(event)

        config_manager.add_event_handler(handler)
        await config_manager.set("event.test", "value")

        assert len(events) == 1
        assert events[0].event_type == ConfigEventType.UPDATED
        assert events[0].key == "event.test"

    @pytest.mark.asyncio
    async def test_load_from_file(self, temp_config_dir):
        """测试从文件加载配置"""
        # 创建配置文件
        config_file = temp_config_dir / "app.json"
        config_file.write_text(json.dumps({
            "database": {
                "host": "localhost",
                "port": 5432,
            },
            "cache": {
                "enabled": True,
            },
        }))

        manager = DynamicConfigManager(temp_config_dir)
        await manager.initialize()

        assert await manager.get("app.database.host") == "localhost"
        assert await manager.get("app.database.port") == 5432
        assert await manager.get("app.cache.enabled") is True

    @pytest.mark.asyncio
    async def test_load_from_env(self, temp_config_dir, monkeypatch):
        """测试从环境变量加载配置"""
        monkeypatch.setenv("LURKBOT_SERVER__HOST", "0.0.0.0")
        monkeypatch.setenv("LURKBOT_SERVER__PORT", "9000")
        monkeypatch.setenv("LURKBOT_DEBUG", "true")

        manager = DynamicConfigManager(temp_config_dir)
        await manager.initialize()

        assert await manager.get("server.host") == "0.0.0.0"
        assert await manager.get("server.port") == 9000
        assert await manager.get("debug") is True

    @pytest.mark.asyncio
    async def test_reload(self, temp_config_dir):
        """测试重载配置"""
        # 初始配置
        config_file = temp_config_dir / "config.json"
        config_file.write_text(json.dumps({"key": "initial"}))

        manager = DynamicConfigManager(temp_config_dir)
        await manager.initialize()

        assert await manager.get("key") == "initial"

        # 修改配置文件
        config_file.write_text(json.dumps({"key": "updated"}))

        # 重载
        result = await manager.reload()
        assert result is True
        assert await manager.get("key") == "updated"

    @pytest.mark.asyncio
    async def test_validate_all(self, config_manager):
        """测试验证所有配置"""

        def string_only(key: str, value) -> tuple[bool, str | None]:
            if not isinstance(value, str):
                return False, f"{key} 必须是字符串"
            return True, None

        config_manager.register_validator("string.*", string_only)

        await config_manager.set("string.valid", "text", validate=False)
        await config_manager.set("string.invalid", 123, validate=False)

        errors = await config_manager.validate_all()

        assert "string.invalid" in errors
        assert "string.valid" not in errors


# ============================================================================
# ConfigWatcher Tests
# ============================================================================


class TestConfigWatcher:
    """ConfigWatcher 测试"""

    def test_add_callback(self):
        """测试添加回调"""
        watcher = ConfigWatcher()
        callback_called = []

        def callback(path: Path):
            callback_called.append(path)

        watcher.add_callback(callback)
        assert len(watcher._callbacks) == 1

    def test_watch_nonexistent_path(self, temp_config_dir, caplog):
        """测试监控不存在的路径"""
        watcher = ConfigWatcher()
        nonexistent = temp_config_dir / "nonexistent"

        watcher.watch(nonexistent)

        # 应该记录警告
        assert "不存在" in caplog.text or len(watcher._handlers) == 0


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, temp_config_dir):
        """测试完整工作流程"""
        # 创建配置文件
        config_file = temp_config_dir / "config.json"
        config_file.write_text(json.dumps({
            "server": {"host": "localhost", "port": 8080},
            "database": {"url": "sqlite:///test.db"},
        }))

        # 初始化管理器
        manager = DynamicConfigManager(temp_config_dir)
        await manager.initialize()

        # 验证文件配置加载
        assert await manager.get("server.host") == "localhost"

        # 添加验证器
        def port_validator(key: str, value) -> tuple[bool, str | None]:
            if isinstance(value, int) and (value < 1 or value > 65535):
                return False, "无效端口"
            return True, None

        manager.register_validator("*.port", port_validator)

        # 创建快照
        v1 = await manager.create_snapshot("初始版本")

        # 更新配置
        await manager.set("server.port", 9000)
        assert await manager.get("server.port") == 9000

        # 验证失败的情况
        result = await manager.set("server.port", 99999)
        assert result is False

        # 回滚
        await manager.rollback(v1)
        assert await manager.get("server.port") == 8080

        # 清理
        manager.stop_watching()

    @pytest.mark.asyncio
    async def test_priority_override(self, temp_config_dir, monkeypatch):
        """测试优先级覆盖"""
        # 文件配置
        config_file = temp_config_dir / "config.json"
        config_file.write_text(json.dumps({"port": 8080}))

        # 环境变量配置（优先级更高）
        monkeypatch.setenv("LURKBOT_PORT", "9000")

        manager = DynamicConfigManager(temp_config_dir)
        await manager.initialize()

        # 环境变量应该覆盖文件配置
        assert await manager.get("port") == 9000

        # 运行时覆盖（最高优先级）
        await manager.set("port", 10000, source=ConfigSource.OVERRIDE)
        assert await manager.get("port") == 10000


# ============================================================================
# Global Singleton Tests
# ============================================================================


class TestGlobalSingleton:
    """全局单例测试"""

    def test_get_config_manager(self, temp_config_dir):
        """测试获取配置管理器单例"""
        # 重置全局状态
        import lurkbot.config.dynamic as dynamic_module

        dynamic_module._config_manager = None

        manager1 = get_config_manager(temp_config_dir)
        manager2 = get_config_manager()

        assert manager1 is manager2

        # 清理
        dynamic_module._config_manager = None

    @pytest.mark.asyncio
    async def test_init_config(self, temp_config_dir):
        """测试初始化配置"""
        # 重置全局状态
        import lurkbot.config.dynamic as dynamic_module

        dynamic_module._config_manager = None

        manager = await init_config(temp_config_dir)

        assert manager._initialized is True
        assert await manager.get("server.port") == 8080

        # 清理
        dynamic_module._config_manager = None
        manager.stop_watching()
