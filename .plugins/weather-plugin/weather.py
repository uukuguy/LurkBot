"""Weather plugin for LurkBot.

This plugin queries weather information using the wttr.in API.
"""

import time

import httpx
from lurkbot.logging import get_logger
from lurkbot.plugins.models import (
    PluginExecutionContext,
    PluginExecutionResult,
)

logger = get_logger("weather-plugin")


class WeatherPlugin:
    """天气查询插件

    使用 wttr.in API 查询指定城市的天气信息。

    示例:
        >>> plugin = WeatherPlugin()
        >>> context = PluginExecutionContext(
        ...     user_id="user123",
        ...     channel_id="channel456",
        ...     session_id="session789",
        ...     input_data={"query": "北京天气怎么样？"},
        ...     parameters={"city": "Beijing"},
        ... )
        >>> result = await plugin.execute(context)
        >>> print(result.data)
        {'city': 'Beijing', 'temperature': '25', 'condition': 'Sunny', ...}
    """

    def __init__(self):
        """初始化天气插件"""
        self.api_base = "https://wttr.in"
        self.timeout = 10.0

    async def execute(
        self, context: PluginExecutionContext
    ) -> PluginExecutionResult:
        """执行天气查询

        Args:
            context: 插件执行上下文，包含用户输入和参数

        Returns:
            PluginExecutionResult: 包含天气数据或错误信息的执行结果
        """
        start_time = time.time()

        try:
            # 从上下文获取城市名称
            city = context.parameters.get("city")

            # 如果没有指定城市，尝试从用户输入中提取
            if not city:
                city = self._extract_city_from_query(
                    context.input_data.get("query", "")
                )

            # 如果仍然没有城市，使用默认值
            if not city:
                city = "Beijing"

            logger.info(f"查询城市天气: {city}")

            # 调用 wttr.in API
            weather_data = await self._fetch_weather(city)

            execution_time = time.time() - start_time
            return PluginExecutionResult(
                success=True,
                result=self._format_weather_text(weather_data),
                error=None,
                execution_time=execution_time,
                metadata={"city": city, "data": weather_data},
            )

        except httpx.HTTPError as e:
            logger.error(f"HTTP 请求失败: {e}")
            execution_time = time.time() - start_time
            return PluginExecutionResult(
                success=False,
                result=None,
                error=f"HTTP 请求失败: {str(e)}",
                execution_time=execution_time,
            )
        except Exception as e:
            logger.error(f"天气查询异常: {e}")
            execution_time = time.time() - start_time
            return PluginExecutionResult(
                success=False,
                result=None,
                error=str(e),
                execution_time=execution_time,
            )

    async def _fetch_weather(self, city: str) -> dict:
        """从 wttr.in API 获取天气数据

        Args:
            city: 城市名称

        Returns:
            dict: 天气数据字典

        Raises:
            httpx.HTTPError: HTTP 请求失败
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/{city}?format=j1",
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

        # 提取关键信息
        current = data["current_condition"][0]
        weather_info = {
            "city": city,
            "temperature": current["temp_C"],
            "feels_like": current["FeelsLikeC"],
            "condition": current["weatherDesc"][0]["value"],
            "humidity": current["humidity"],
            "wind_speed": current["windspeedKmph"],
            "wind_direction": current["winddir16Point"],
            "pressure": current["pressure"],
            "visibility": current["visibility"],
            "uv_index": current["uvIndex"],
        }

        return weather_info

    def _extract_city_from_query(self, query: str) -> str | None:
        """从用户查询中提取城市名称

        Args:
            query: 用户查询文本

        Returns:
            str | None: 提取的城市名称，如果未找到则返回 None
        """
        # 简单的城市名称提取逻辑
        # 实际应用中可以使用 NLP 或正则表达式
        common_cities = {
            "北京": "Beijing",
            "上海": "Shanghai",
            "广州": "Guangzhou",
            "深圳": "Shenzhen",
            "杭州": "Hangzhou",
            "成都": "Chengdu",
            "重庆": "Chongqing",
            "西安": "Xian",
            "武汉": "Wuhan",
            "南京": "Nanjing",
        }

        query_lower = query.lower()
        for cn_name, en_name in common_cities.items():
            if cn_name in query or en_name.lower() in query_lower:
                return en_name

        return None

    def _format_weather_text(self, weather_data: dict) -> str:
        """格式化天气数据为文本

        Args:
            weather_data: 天气数据字典

        Returns:
            str: 格式化的天气文本
        """
        return (
            f"{weather_data['city']} 当前天气：\n"
            f"- 温度：{weather_data['temperature']}°C "
            f"(体感 {weather_data['feels_like']}°C)\n"
            f"- 天气：{weather_data['condition']}\n"
            f"- 湿度：{weather_data['humidity']}%\n"
            f"- 风速：{weather_data['wind_speed']} km/h "
            f"({weather_data['wind_direction']})\n"
            f"- 气压：{weather_data['pressure']} mb\n"
            f"- 能见度：{weather_data['visibility']} km\n"
            f"- 紫外线指数：{weather_data['uv_index']}"
        )
