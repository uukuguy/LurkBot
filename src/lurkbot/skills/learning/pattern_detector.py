"""模式检测器 - 从对话历史中识别重复模式

分析用户的对话历史，识别可以转化为技能的重复模式。
"""

from collections import Counter
from datetime import datetime, timedelta

from loguru import logger

from .models import DetectedPattern, PatternType


class PatternDetector:
    """检测对话中的重复模式"""

    def __init__(
        self,
        min_occurrences: int = 2,
        time_window_days: int = 7,
        min_confidence: float = 0.6,
    ):
        """初始化模式检测器

        Args:
            min_occurrences: 最小出现次数
            time_window_days: 时间窗口（天）
            min_confidence: 最小置信度阈值
        """
        self.min_occurrences = min_occurrences
        self.time_window_days = time_window_days
        self.min_confidence = min_confidence

    def detect_patterns(
        self,
        conversation_history: list[dict],
        user_id: str,
    ) -> list[DetectedPattern]:
        """检测对话历史中的模式

        Args:
            conversation_history: 对话历史，格式: [
                {
                    "session_id": str,
                    "timestamp": datetime,
                    "role": "user"|"assistant",
                    "content": str,
                }
            ]
            user_id: 用户 ID

        Returns:
            list[DetectedPattern]: 检测到的模式列表
        """
        if not conversation_history:
            return []

        patterns = []

        # 过滤时间窗口内的对话
        cutoff_time = datetime.now() - timedelta(days=self.time_window_days)
        recent_conversations = [
            conv
            for conv in conversation_history
            if conv.get("timestamp", datetime.now()) >= cutoff_time
        ]

        if len(recent_conversations) < self.min_occurrences:
            logger.debug(
                f"Not enough recent conversations ({len(recent_conversations)}) "
                f"to detect patterns"
            )
            return []

        # 1. 检测重复任务模式
        repeated_task_pattern = self._detect_repeated_tasks(recent_conversations)
        if repeated_task_pattern:
            patterns.append(repeated_task_pattern)

        # 2. 检测顺序步骤模式
        sequential_pattern = self._detect_sequential_steps(recent_conversations)
        if sequential_pattern:
            patterns.append(sequential_pattern)

        # 3. 检测数据处理模式
        data_processing_pattern = self._detect_data_processing(recent_conversations)
        if data_processing_pattern:
            patterns.append(data_processing_pattern)

        # 过滤低置信度模式
        patterns = [p for p in patterns if p.confidence >= self.min_confidence]

        logger.info(f"Detected {len(patterns)} patterns for user {user_id}")
        return patterns

    def _detect_repeated_tasks(
        self, conversations: list[dict]
    ) -> DetectedPattern | None:
        """检测重复任务模式"""
        # 提取用户消息
        user_messages = [
            conv for conv in conversations if conv.get("role") == "user"
        ]

        if len(user_messages) < self.min_occurrences:
            return None

        # 提取关键词（简单实现：取常见词）
        all_words = []
        for msg in user_messages:
            content = msg.get("content", "").lower()
            words = [w for w in content.split() if len(w) > 3]  # 过滤短词
            all_words.extend(words)

        # 统计词频
        word_counts = Counter(all_words)
        common_words = [word for word, count in word_counts.most_common(10) if count >= self.min_occurrences]

        if not common_words:
            return None

        # 查找包含这些关键词的消息
        matching_messages = []
        session_ids = set()
        for msg in user_messages:
            content = msg.get("content", "").lower()
            if any(word in content for word in common_words):
                matching_messages.append(msg)
                session_ids.add(msg.get("session_id", ""))

        if len(matching_messages) < self.min_occurrences:
            return None

        # 计算置信度
        confidence = min(len(matching_messages) / len(user_messages), 1.0)

        # 提取时间信息
        timestamps = [msg.get("timestamp", datetime.now()) for msg in matching_messages]
        first_seen = min(timestamps)
        last_seen = max(timestamps)

        return DetectedPattern(
            pattern_type=PatternType.REPEATED_TASK,
            description=f"用户重复执行包含关键词 {', '.join(common_words[:3])} 的任务",
            confidence=confidence,
            repeated_actions=[msg.get("content", "")[:100] for msg in matching_messages[:5]],
            common_keywords=common_words[:10],
            step_sequence=[],
            session_ids=list(session_ids),
            occurrence_count=len(matching_messages),
            first_seen=first_seen,
            last_seen=last_seen,
        )

    def _detect_sequential_steps(
        self, conversations: list[dict]
    ) -> DetectedPattern | None:
        """检测顺序步骤模式"""
        # 按会话分组
        sessions = {}
        for conv in conversations:
            session_id = conv.get("session_id", "")
            if session_id not in sessions:
                sessions[session_id] = []
            sessions[session_id].append(conv)

        # 查找包含多个步骤的会话
        multi_step_sessions = []
        for session_id, messages in sessions.items():
            user_messages = [m for m in messages if m.get("role") == "user"]
            if len(user_messages) >= 3:  # 至少3个步骤
                multi_step_sessions.append((session_id, user_messages))

        if len(multi_step_sessions) < self.min_occurrences:
            return None

        # 提取步骤序列
        step_sequences = []
        for session_id, messages in multi_step_sessions:
            steps = [msg.get("content", "")[:50] for msg in messages[:5]]
            step_sequences.append(steps)

        # 计算置信度（简化：基于会话数）
        confidence = min(len(multi_step_sessions) / max(len(sessions), 1), 1.0)

        if confidence < self.min_confidence:
            return None

        # 提取时间信息
        all_messages = [msg for _, messages in multi_step_sessions for msg in messages]
        timestamps = [msg.get("timestamp", datetime.now()) for msg in all_messages]
        first_seen = min(timestamps) if timestamps else datetime.now()
        last_seen = max(timestamps) if timestamps else datetime.now()

        return DetectedPattern(
            pattern_type=PatternType.SEQUENTIAL_STEPS,
            description=f"用户在 {len(multi_step_sessions)} 个会话中执行了多步骤流程",
            confidence=confidence,
            repeated_actions=[],
            common_keywords=[],
            step_sequence=step_sequences[0] if step_sequences else [],
            session_ids=[sid for sid, _ in multi_step_sessions],
            occurrence_count=len(multi_step_sessions),
            first_seen=first_seen,
            last_seen=last_seen,
        )

    def _detect_data_processing(
        self, conversations: list[dict]
    ) -> DetectedPattern | None:
        """检测数据处理模式"""
        # 查找包含数据处理关键词的消息
        data_keywords = [
            "parse",
            "transform",
            "convert",
            "format",
            "extract",
            "filter",
            "process",
            "analyze",
            "数据",
            "转换",
            "处理",
            "分析",
        ]

        matching_messages = []
        session_ids = set()

        for conv in conversations:
            if conv.get("role") != "user":
                continue

            content = conv.get("content", "").lower()
            if any(keyword in content for keyword in data_keywords):
                matching_messages.append(conv)
                session_ids.add(conv.get("session_id", ""))

        if len(matching_messages) < self.min_occurrences:
            return None

        # 计算置信度
        user_messages = [c for c in conversations if c.get("role") == "user"]
        confidence = min(len(matching_messages) / max(len(user_messages), 1), 1.0)

        if confidence < self.min_confidence:
            return None

        # 提取时间信息
        timestamps = [msg.get("timestamp", datetime.now()) for msg in matching_messages]
        first_seen = min(timestamps)
        last_seen = max(timestamps)

        # 提取常见关键词
        all_words = []
        for msg in matching_messages:
            content = msg.get("content", "").lower()
            words = [w for w in content.split() if len(w) > 3]
            all_words.extend(words)

        word_counts = Counter(all_words)
        common_words = [word for word, _ in word_counts.most_common(5)]

        return DetectedPattern(
            pattern_type=PatternType.DATA_PROCESSING,
            description=f"用户重复执行数据处理任务",
            confidence=confidence,
            repeated_actions=[msg.get("content", "")[:100] for msg in matching_messages[:5]],
            common_keywords=common_words,
            step_sequence=[],
            session_ids=list(session_ids),
            occurrence_count=len(matching_messages),
            first_seen=first_seen,
            last_seen=last_seen,
        )
