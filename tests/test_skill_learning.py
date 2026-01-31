"""测试动态技能学习模块"""

import os
from datetime import datetime, timedelta

import pytest

from lurkbot.skills.learning import (
    DetectedPattern,
    PatternDetector,
    PatternType,
    SkillStorage,
    SkillTemplate,
    SkillType,
    TemplateGenerator,
)

# Mark for tests that need API key
needs_api = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set"
)


def test_pattern_detector_initialization():
    """测试模式检测器初始化"""
    detector = PatternDetector(min_occurrences=2, time_window_days=7)
    assert detector.min_occurrences == 2
    assert detector.time_window_days == 7


def test_pattern_detector_empty_history():
    """测试空历史记录"""
    detector = PatternDetector()
    patterns = detector.detect_patterns([], "user123")
    assert len(patterns) == 0


def test_pattern_detector_repeated_tasks():
    """测试重复任务检测"""
    detector = PatternDetector(min_occurrences=2)

    # 创建包含重复任务的历史
    history = [
        {
            "session_id": "s1",
            "timestamp": datetime.now(),
            "role": "user",
            "content": "deploy the application to production",
        },
        {
            "session_id": "s2",
            "timestamp": datetime.now(),
            "role": "user",
            "content": "deploy the service to production",
        },
        {
            "session_id": "s3",
            "timestamp": datetime.now(),
            "role": "user",
            "content": "deploy the api to production",
        },
    ]

    patterns = detector.detect_patterns(history, "user123")
    assert len(patterns) > 0
    # Should detect "deploy" and "production" as common keywords
    repeated_pattern = next(
        (p for p in patterns if p.pattern_type == PatternType.REPEATED_TASK), None
    )
    assert repeated_pattern is not None
    assert "deploy" in repeated_pattern.common_keywords or "production" in repeated_pattern.common_keywords


def test_pattern_detector_sequential_steps():
    """测试顺序步骤检测"""
    detector = PatternDetector(min_occurrences=2)

    # 创建包含多步骤的会话
    history = []
    for session_num in range(3):
        session_id = f"session_{session_num}"
        for step in ["check logs", "fix bug", "run tests", "deploy"]:
            history.append({
                "session_id": session_id,
                "timestamp": datetime.now(),
                "role": "user",
                "content": step,
            })

    patterns = detector.detect_patterns(history, "user123")
    sequential_pattern = next(
        (p for p in patterns if p.pattern_type == PatternType.SEQUENTIAL_STEPS), None
    )
    assert sequential_pattern is not None
    assert sequential_pattern.occurrence_count >= 2


def test_skill_storage_save_and_load(tmp_path):
    """测试技能保存和加载"""
    storage = SkillStorage(storage_dir=str(tmp_path))

    # 创建测试技能
    from lurkbot.skills.learning.models import SkillAction

    skill = SkillTemplate(
        skill_id="test-skill-123",
        name="Test Skill",
        description="A test skill",
        skill_type=SkillType.WORKFLOW,
        pattern_type=PatternType.REPEATED_TASK,
        trigger_keywords=["test", "deploy"],
        actions=[
            SkillAction(
                step_number=1,
                action_type="run_command",
                description="Run tests",
                parameters={"command": "pytest"},
            )
        ],
        learned_from_session="session123",
        learned_from_user="user123",
    )

    # 保存
    success = storage.save_skill(skill)
    assert success is True

    # 加载
    loaded_skill = storage.load_skill("test-skill-123")
    assert loaded_skill is not None
    assert loaded_skill.name == "Test Skill"
    assert loaded_skill.skill_id == "test-skill-123"


def test_skill_storage_list_skills(tmp_path):
    """测试列出技能"""
    storage = SkillStorage(storage_dir=str(tmp_path))

    from lurkbot.skills.learning.models import SkillAction

    # 创建多个技能
    for i in range(3):
        skill = SkillTemplate(
            skill_id=f"skill-{i}",
            name=f"Skill {i}",
            description=f"Description {i}",
            skill_type=SkillType.WORKFLOW,
            pattern_type=PatternType.REPEATED_TASK,
            trigger_keywords=[],
            actions=[
                SkillAction(
                    step_number=1,
                    action_type="test",
                    description="test",
                    parameters={},
                )
            ],
            learned_from_session="session123",
            learned_from_user="user123",
        )
        storage.save_skill(skill)

    # 列出所有技能
    skills = storage.list_skills()
    assert len(skills) == 3


def test_skill_storage_delete(tmp_path):
    """测试删除技能"""
    storage = SkillStorage(storage_dir=str(tmp_path))

    from lurkbot.skills.learning.models import SkillAction

    skill = SkillTemplate(
        skill_id="delete-me",
        name="Delete Me",
        description="Will be deleted",
        skill_type=SkillType.WORKFLOW,
        pattern_type=PatternType.REPEATED_TASK,
        trigger_keywords=[],
        actions=[
            SkillAction(
                step_number=1,
                action_type="test",
                description="test",
                parameters={},
            )
        ],
        learned_from_session="session123",
        learned_from_user="user123",
    )

    storage.save_skill(skill)
    assert storage.load_skill("delete-me") is not None

    # 删除
    success = storage.delete_skill("delete-me")
    assert success is True
    assert storage.load_skill("delete-me") is None


@needs_api
@pytest.mark.asyncio
async def test_template_generator():
    """测试模板生成器"""
    generator = TemplateGenerator()

    pattern = DetectedPattern(
        pattern_type=PatternType.REPEATED_TASK,
        description="User repeatedly deploys applications",
        confidence=0.85,
        repeated_actions=["deploy app", "check status", "verify deployment"],
        common_keywords=["deploy", "production", "application"],
        step_sequence=[],
        session_ids=["s1", "s2", "s3"],
        occurrence_count=3,
        first_seen=datetime.now() - timedelta(days=5),
        last_seen=datetime.now(),
    )

    template = await generator.generate_template(
        pattern=pattern,
        user_id="user123",
        session_id="session123",
    )

    assert template is not None
    assert len(template.actions) > 0
    assert len(template.trigger_keywords) > 0
