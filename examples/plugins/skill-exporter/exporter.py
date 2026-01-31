"""Skill Exporter Plugin

Exports learned skills from Phase 3-C as standalone plugins.
"""

import json
from pathlib import Path
from typing import Any


class SkillExporterPlugin:
    """Skill exporter plugin - integrates with Phase 3-C skill learning"""

    def __init__(self):
        self.enabled = False
        self.skills_dir = Path("data/skills")
        self.output_dir = Path(".plugins/exported")

    async def initialize(self, config: dict[str, Any]) -> None:
        """Initialize plugin"""
        self.config = config
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Skill exporter initialized, output dir: {self.output_dir}")

    async def execute(self, context: dict[str, Any]) -> Any:
        """Export a skill as a plugin

        Args:
            context: Execution context containing:
                - input_data.skill_name: Name of the skill to export
                - parameters.plugin_name: Optional custom plugin name

        Returns:
            Export result dict
        """
        skill_name = context.get("input_data", {}).get("skill_name")
        plugin_name = context.get("parameters", {}).get("plugin_name")

        if not skill_name:
            return {"success": False, "error": "No skill_name provided"}

        # Load skill from Phase 3-C storage
        skill_file = self.skills_dir / f"{skill_name}.json"
        if not skill_file.exists():
            return {
                "success": False,
                "error": f"Skill '{skill_name}' not found in {self.skills_dir}",
            }

        try:
            with open(skill_file) as f:
                skill_data = json.load(f)

            # Generate plugin name
            if not plugin_name:
                plugin_name = f"skill-{skill_name}"

            # Create plugin directory
            plugin_dir = self.output_dir / plugin_name
            plugin_dir.mkdir(parents=True, exist_ok=True)

            # Generate plugin manifest
            manifest = {
                "name": plugin_name,
                "version": "1.0.0",
                "description": skill_data.get("description", f"Exported skill: {skill_name}"),
                "type": "skill",
                "language": "python",
                "entry": "skill.py",
                "main_class": "ExportedSkill",
                "tags": ["exported", "skill"],
                "enabled": True,
            }

            # Write manifest
            with open(plugin_dir / "plugin.json", "w") as f:
                json.dump(manifest, f, indent=2)

            # Generate plugin code
            plugin_code = self._generate_plugin_code(skill_name, skill_data)
            with open(plugin_dir / "skill.py", "w") as f:
                f.write(plugin_code)

            return {
                "success": True,
                "skill_name": skill_name,
                "plugin_name": plugin_name,
                "plugin_dir": str(plugin_dir),
                "message": f"Skill '{skill_name}' exported as plugin '{plugin_name}'",
            }

        except Exception as e:
            return {"success": False, "error": f"Export failed: {e}"}

    def _generate_plugin_code(self, skill_name: str, skill_data: dict) -> str:
        """Generate plugin Python code from skill data"""
        actions = skill_data.get("actions", [])
        description = skill_data.get("description", "")

        code = f'''"""Exported Skill: {skill_name}

{description}
"""

from typing import Any


class ExportedSkill:
    """Exported skill plugin"""

    def __init__(self):
        self.skill_name = "{skill_name}"
        self.actions = {actions!r}

    async def execute(self, context: dict[str, Any]) -> Any:
        """Execute skill actions"""
        results = []
        for action in self.actions:
            # Execute each action
            result = await self._execute_action(action, context)
            results.append(result)
        return {{"skill": self.skill_name, "results": results}}

    async def _execute_action(self, action: dict, context: dict) -> Any:
        """Execute a single action"""
        # Mock implementation - in real plugin, implement actual logic
        return {{"action": action, "status": "executed"}}

    async def on_enable(self) -> None:
        print(f"Skill '{{self.skill_name}}' enabled")

    async def on_disable(self) -> None:
        print(f"Skill '{{self.skill_name}}' disabled")
'''
        return code

    async def cleanup(self) -> None:
        """Cleanup resources"""
        print("Skill exporter cleanup")

    async def on_enable(self) -> None:
        """Called when plugin is enabled"""
        self.enabled = True
        print("Skill exporter enabled")

    async def on_disable(self) -> None:
        """Called when plugin is disabled"""
        self.enabled = False
        print("Skill exporter disabled")
