"""测试示例插件

测试 weather, translator, skill-exporter 示例插件的功能。
"""

import tempfile
from pathlib import Path

import pytest

from lurkbot.plugins.loader import get_plugin_loader
from lurkbot.plugins.manager import PluginManager
from lurkbot.plugins.manifest import PluginManifest
from lurkbot.plugins.models import PluginExecutionContext
from lurkbot.plugins.registry import PluginRegistry


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def examples_dir():
    """获取示例插件目录"""
    return Path(__file__).parent.parent / "examples" / "plugins"


@pytest.fixture
async def plugin_manager():
    """创建插件管理器实例"""
    loader = get_plugin_loader()
    registry = PluginRegistry()
    manager = PluginManager(loader=loader, registry=registry)
    yield manager
    # 清理
    for plugin in manager.list_plugins():
        await manager.unload_plugin(plugin.name)


# ============================================================================
# Weather Plugin 测试
# ============================================================================


@pytest.mark.asyncio
async def test_weather_plugin_exists(examples_dir):
    """测试 weather 插件是否存在"""
    weather_dir = examples_dir / "weather"
    assert weather_dir.exists()
    assert (weather_dir / "plugin.json").exists()
    assert (weather_dir / "weather.py").exists()


@pytest.mark.asyncio
async def test_weather_plugin_load(plugin_manager, examples_dir):
    """测试加载 weather 插件"""
    weather_dir = examples_dir / "weather"

    # 发现并加载插件
    loaded_count = await plugin_manager.discover_and_load_all(examples_dir)
    assert loaded_count >= 1

    # 检查插件是否加载
    assert plugin_manager.is_loaded("weather-plugin")


@pytest.mark.asyncio
async def test_weather_plugin_execute(plugin_manager, examples_dir):
    """测试执行 weather 插件"""
    # 加载插件
    await plugin_manager.discover_and_load_all(examples_dir)

    # 创建执行上下文
    context = PluginExecutionContext(
        input_data={"city": "Shanghai"},
        parameters={"units": "metric"},
    )

    # 执行插件
    result = await plugin_manager.execute_plugin("weather-plugin", context)

    assert result.success is True
    assert result.error is None
    assert result.result is not None
    assert result.result.get("city") == "Shanghai"
    assert result.result.get("units") == "metric"


@pytest.mark.asyncio
async def test_weather_plugin_imperial_units(plugin_manager, examples_dir):
    """测试 weather 插件使用英制单位"""
    await plugin_manager.discover_and_load_all(examples_dir)

    context = PluginExecutionContext(
        input_data={"city": "New York"},
        parameters={"units": "imperial"},
    )

    result = await plugin_manager.execute_plugin("weather-plugin", context)

    assert result.success is True
    assert result.result.get("units") == "imperial"
    assert result.result.get("temperature") == 77  # Fahrenheit


# ============================================================================
# Translator Plugin 测试
# ============================================================================


@pytest.mark.asyncio
async def test_translator_plugin_exists(examples_dir):
    """测试 translator 插件是否存在"""
    translator_dir = examples_dir / "translator"
    assert translator_dir.exists()
    assert (translator_dir / "plugin.json").exists()
    assert (translator_dir / "translator.py").exists()


@pytest.mark.asyncio
async def test_translator_plugin_load(plugin_manager, examples_dir):
    """测试加载 translator 插件"""
    await plugin_manager.discover_and_load_all(examples_dir)
    assert plugin_manager.is_loaded("translator-plugin")


@pytest.mark.asyncio
async def test_translator_plugin_execute(plugin_manager, examples_dir):
    """测试执行 translator 插件"""
    await plugin_manager.discover_and_load_all(examples_dir)

    context = PluginExecutionContext(
        input_data={"text": "Hello, world!"},
        parameters={"source_lang": "en", "target_lang": "zh"},
    )

    result = await plugin_manager.execute_plugin("translator-plugin", context)

    assert result.success is True
    assert result.error is None
    assert result.result is not None
    assert "translated_text" in result.result
    assert result.result.get("source_lang") == "en"
    assert result.result.get("target_lang") == "zh"


# ============================================================================
# Skill Exporter Plugin 测试
# ============================================================================


@pytest.mark.asyncio
async def test_skill_exporter_plugin_exists(examples_dir):
    """测试 skill-exporter 插件是否存在"""
    exporter_dir = examples_dir / "skill-exporter"
    assert exporter_dir.exists()
    assert (exporter_dir / "plugin.json").exists()
    assert (exporter_dir / "exporter.py").exists()


@pytest.mark.asyncio
async def test_skill_exporter_plugin_load(plugin_manager, examples_dir):
    """测试加载 skill-exporter 插件"""
    await plugin_manager.discover_and_load_all(examples_dir)
    assert plugin_manager.is_loaded("skill-exporter-plugin")


@pytest.mark.asyncio
async def test_skill_exporter_plugin_execute(plugin_manager, examples_dir):
    """测试执行 skill-exporter 插件"""
    await plugin_manager.discover_and_load_all(examples_dir)

    with tempfile.TemporaryDirectory() as tmpdir:
        context = PluginExecutionContext(
            input_data={
                "skill_name": "test-skill",
                "skill_code": "async def execute(context): return {'result': 'success'}",
                "skill_description": "Test skill",
            },
            parameters={"output_dir": tmpdir},
        )

        result = await plugin_manager.execute_plugin("skill-exporter-plugin", context)

        assert result.success is True
        assert result.error is None
        assert result.result is not None

        # 检查生成的文件
        output_dir = Path(tmpdir) / "test-skill"
        if output_dir.exists():
            assert (output_dir / "plugin.json").exists()


# ============================================================================
# 多插件协作测试
# ============================================================================


@pytest.mark.asyncio
async def test_load_all_example_plugins(plugin_manager, examples_dir):
    """测试加载所有示例插件"""
    loaded_count = await plugin_manager.discover_and_load_all(examples_dir)

    # 至少应该加载 3 个插件
    assert loaded_count >= 3

    # 检查所有插件都已加载
    plugins = plugin_manager.list_plugins()
    plugin_names = [p.name for p in plugins]

    assert "weather-plugin" in plugin_names
    assert "translator-plugin" in plugin_names
    assert "skill-exporter-plugin" in plugin_names


@pytest.mark.asyncio
async def test_execute_multiple_plugins_concurrently(plugin_manager, examples_dir):
    """测试并发执行多个插件"""
    await plugin_manager.discover_and_load_all(examples_dir)

    # 创建执行上下文
    context = PluginExecutionContext(
        input_data={"city": "Beijing", "text": "Hello"},
        parameters={"units": "metric"},
    )

    # 并发执行多个插件
    results = await plugin_manager.execute_plugins(
        context, ["weather-plugin", "translator-plugin"]
    )

    assert len(results) == 2
    assert "weather-plugin" in results
    assert "translator-plugin" in results
    assert results["weather-plugin"].success is True
    assert results["translator-plugin"].success is True


# ============================================================================
# 插件生命周期测试
# ============================================================================


@pytest.mark.asyncio
async def test_plugin_lifecycle(plugin_manager, examples_dir):
    """测试插件完整生命周期"""
    # 1. 加载
    await plugin_manager.discover_and_load_all(examples_dir)
    assert plugin_manager.is_loaded("weather-plugin")
    assert plugin_manager.is_enabled("weather-plugin")

    # 2. 禁用
    await plugin_manager.disable_plugin("weather-plugin")
    assert not plugin_manager.is_enabled("weather-plugin")

    # 3. 启用
    await plugin_manager.enable_plugin("weather-plugin")
    assert plugin_manager.is_enabled("weather-plugin")

    # 4. 执行
    context = PluginExecutionContext(input_data={"city": "Beijing"})
    result = await plugin_manager.execute_plugin("weather-plugin", context)
    assert result.success is True

    # 5. 卸载
    await plugin_manager.unload_plugin("weather-plugin")
    assert not plugin_manager.is_loaded("weather-plugin")
