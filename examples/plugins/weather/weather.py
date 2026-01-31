"""Weather Query Plugin

A simple example plugin that queries weather information.
"""

from typing import Any


class WeatherPlugin:
    """Weather query plugin"""

    def __init__(self):
        self.enabled = False

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize plugin"""
        self.config = config
        print(f"Weather plugin initialized with config: {config}")

    async def execute(self, context: dict[str, Any]) -> Any:
        """Execute weather query

        Args:
            context: Execution context containing input_data with 'city' field

        Returns:
            Weather information dict
        """
        city = context.get("input_data", {}).get("city", "Beijing")
        units = context.get("parameters", {}).get("units", "metric")

        # Mock weather data (in real implementation, call weather API)
        weather_data = {
            "city": city,
            "temperature": 25 if units == "metric" else 77,
            "condition": "Sunny",
            "humidity": 60,
            "wind_speed": 10,
            "units": units,
        }

        return weather_data

    async def cleanup(self) -> None:
        """Cleanup resources"""
        print("Weather plugin cleanup")

    async def on_enable(self) -> None:
        """Called when plugin is enabled"""
        self.enabled = True
        print("Weather plugin enabled")

    async def on_disable(self) -> None:
        """Called when plugin is disabled"""
        self.enabled = False
        print("Weather plugin disabled")
