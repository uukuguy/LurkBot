"""测试示例插件的基本功能

这个脚本用于快速验证示例插件是否能正常工作。
"""

import asyncio
from pathlib import Path

from lurkbot.logging import get_logger
from lurkbot.plugins import get_plugin_manager
from lurkbot.plugins.models import PluginExecutionContext

logger = get_logger("test_example_plugins")


async def test_weather_plugin():
    """测试天气插件"""
    logger.info("=" * 60)
    logger.info("测试天气插件")
    logger.info("=" * 60)

    manager = get_plugin_manager()

    try:
        # 创建执行上下文
        context = PluginExecutionContext(
            user_id="test-user",
            channel_id="test-channel",
            session_id="test-session",
            input_data={"query": "北京天气怎么样？"},
            parameters={"city": "Beijing"},
        )

        # 执行插件
        result = await manager.execute_plugin("weather-plugin", context)

        if result.success:
            logger.info("✅ 天气插件执行成功")
            logger.info(f"结果: {result.result}")
            logger.info(f"执行时间: {result.execution_time:.2f}s")
        else:
            logger.error(f"❌ 天气插件执行失败: {result.error}")

    except Exception as e:
        logger.error(f"❌ 天气插件测试失败: {e}")


async def test_time_utils_plugin():
    """测试时间工具插件"""
    logger.info("=" * 60)
    logger.info("测试时间工具插件")
    logger.info("=" * 60)

    manager = get_plugin_manager()

    try:
        # 创建执行上下文
        context = PluginExecutionContext(
            user_id="test-user",
            channel_id="test-channel",
            session_id="test-session",
            input_data={"query": "现在几点了？"},
            parameters={"timezone": "Asia/Shanghai"},
        )

        # 执行插件
        result = await manager.execute_plugin("time-utils-plugin", context)

        if result.success:
            logger.info("✅ 时间工具插件执行成功")
            logger.info(f"结果: {result.result}")
            logger.info(f"执行时间: {result.execution_time:.2f}s")
        else:
            logger.error(f"❌ 时间工具插件执行失败: {result.error}")

    except Exception as e:
        logger.error(f"❌ 时间工具插件测试失败: {e}")


async def test_system_info_plugin():
    """测试系统信息插件"""
    logger.info("=" * 60)
    logger.info("测试系统信息插件")
    logger.info("=" * 60)

    manager = get_plugin_manager()

    try:
        # 创建执行上下文
        context = PluginExecutionContext(
            user_id="test-user",
            channel_id="test-channel",
            session_id="test-session",
            input_data={"query": "系统状态如何？"},
            parameters={},
        )

        # 执行插件
        result = await manager.execute_plugin("system-info-plugin", context)

        if result.success:
            logger.info("✅ 系统信息插件执行成功")
            logger.info(f"结果: {result.result}")
            logger.info(f"执行时间: {result.execution_time:.2f}s")
        else:
            logger.error(f"❌ 系统信息插件执行失败: {result.error}")

    except Exception as e:
        logger.error(f"❌ 系统信息插件测试失败: {e}")


async def test_all_plugins():
    """测试所有示例插件"""
    logger.info("开始测试所有示例插件...")

    # 首先加载所有插件
    manager = get_plugin_manager()
    workspace_root = Path(__file__).parent.parent.parent
    plugin_count = await manager.discover_and_load_all(workspace_root)
    logger.info(f"已加载 {plugin_count} 个插件")

    await test_weather_plugin()
    await test_time_utils_plugin()
    await test_system_info_plugin()

    logger.info("=" * 60)
    logger.info("所有插件测试完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_all_plugins())
