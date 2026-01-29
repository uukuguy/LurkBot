"""
TUI 流式响应组装器

对标 MoltBot src/tui/tui-stream-assembler.ts

分离 thinking 块和 content 块，合成显示文本
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RunState:
    """单次运行的状态"""

    thinking: str = ""
    content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)


class TuiStreamAssembler:
    """
    TUI 流式响应组装器

    对标 MoltBot TuiStreamAssembler

    功能:
    - 分离 thinking 块和 content 块
    - 追踪工具调用和结果
    - 合成最终显示文本
    """

    def __init__(self) -> None:
        self._runs: dict[str, RunState] = {}

    def _get_run_state(self, run_id: str) -> RunState:
        """获取或创建运行状态"""
        if run_id not in self._runs:
            self._runs[run_id] = RunState()
        return self._runs[run_id]

    def ingest_delta(
        self,
        run_id: str,
        message: dict[str, Any],
        show_thinking: bool = False,
    ) -> str:
        """
        处理增量消息

        Args:
            run_id: 运行 ID
            message: 增量消息 {"thinking": "...", "content": "...", "tool_call": {...}}
            show_thinking: 是否显示 thinking 块

        Returns:
            新的显示文本
        """
        run_state = self._get_run_state(run_id)

        # 提取 thinking 块
        if "thinking" in message:
            thinking_delta = message["thinking"]
            if thinking_delta:
                run_state.thinking += thinking_delta

        # 提取 content 块
        if "content" in message:
            content_delta = message["content"]
            if content_delta:
                run_state.content += content_delta

        # 提取工具调用
        if "tool_call" in message:
            tool_call = message["tool_call"]
            if tool_call:
                # 查找是否已存在该工具调用
                existing = None
                for tc in run_state.tool_calls:
                    if tc.get("id") == tool_call.get("id"):
                        existing = tc
                        break

                if existing:
                    # 更新现有工具调用
                    if "arguments" in tool_call:
                        existing.setdefault("arguments", "")
                        existing["arguments"] += tool_call["arguments"]
                else:
                    # 添加新工具调用
                    run_state.tool_calls.append(tool_call.copy())

        # 提取工具结果
        if "tool_result" in message:
            tool_result = message["tool_result"]
            if tool_result:
                run_state.tool_results.append(tool_result.copy())

        # 合成显示文本
        return self._compose_display_text(run_state, show_thinking)

    def _compose_display_text(
        self,
        run_state: RunState,
        show_thinking: bool,
    ) -> str:
        """合成显示文本"""
        parts: list[str] = []

        # Thinking 部分
        if show_thinking and run_state.thinking:
            parts.append(f"[thinking]\n{run_state.thinking}\n[/thinking]")

        # 工具调用部分
        if run_state.tool_calls:
            tool_parts: list[str] = []
            for tc in run_state.tool_calls:
                name = tc.get("name", "unknown")
                args = tc.get("arguments", "")
                tool_parts.append(f"  • {name}({args})")
            if tool_parts:
                parts.append("[tools]\n" + "\n".join(tool_parts) + "\n[/tools]")

        # 工具结果部分
        if run_state.tool_results:
            result_parts: list[str] = []
            for tr in run_state.tool_results:
                tool_id = tr.get("tool_use_id", "unknown")
                content = tr.get("content", "")
                if len(content) > 200:
                    content = content[:200] + "..."
                result_parts.append(f"  [{tool_id}]: {content}")
            if result_parts:
                parts.append("[results]\n" + "\n".join(result_parts) + "\n[/results]")

        # Content 部分
        if run_state.content:
            parts.append(run_state.content)

        return "\n\n".join(parts) if parts else ""

    def finalize(self, run_id: str) -> str:
        """
        最终化并清理运行状态

        Args:
            run_id: 运行 ID

        Returns:
            最终内容文本
        """
        run_state = self._runs.pop(run_id, RunState())
        return run_state.content

    def get_thinking(self, run_id: str) -> str:
        """获取 thinking 内容"""
        run_state = self._runs.get(run_id, RunState())
        return run_state.thinking

    def get_content(self, run_id: str) -> str:
        """获取 content 内容"""
        run_state = self._runs.get(run_id, RunState())
        return run_state.content

    def get_tool_calls(self, run_id: str) -> list[dict[str, Any]]:
        """获取工具调用列表"""
        run_state = self._runs.get(run_id, RunState())
        return run_state.tool_calls.copy()

    def get_tool_results(self, run_id: str) -> list[dict[str, Any]]:
        """获取工具结果列表"""
        run_state = self._runs.get(run_id, RunState())
        return run_state.tool_results.copy()

    def clear(self, run_id: str | None = None) -> None:
        """
        清理运行状态

        Args:
            run_id: 指定运行 ID，None 则清理所有
        """
        if run_id is None:
            self._runs.clear()
        elif run_id in self._runs:
            del self._runs[run_id]

    def has_run(self, run_id: str) -> bool:
        """检查是否有指定运行"""
        return run_id in self._runs

    def active_runs(self) -> list[str]:
        """获取所有活跃运行 ID"""
        return list(self._runs.keys())
