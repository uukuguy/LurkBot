"""测试文档生成器

测试 API 文档生成、CLI 文档生成和模板渲染功能。
"""

import tempfile
from pathlib import Path

import pytest

from lurkbot.plugins.doc_generator import (
    ASTDocExtractor,
    CLIDocGenerator,
    DocFormat,
    DocGenerator,
)


# ============================================================================
# 测试数据
# ============================================================================


SAMPLE_PYTHON_CODE = '''
"""示例模块

这是一个示例模块，用于测试文档生成。
"""

from typing import Optional


class SampleClass:
    """示例类

    这是一个示例类，用于演示文档生成功能。
    """

    name: str
    value: int = 0

    def __init__(self, name: str, value: int = 0):
        """初始化示例类

        Args:
            name: 名称
            value: 值，默认为 0
        """
        self.name = name
        self.value = value

    def get_info(self) -> dict:
        """获取信息

        Returns:
            包含名称和值的字典

        Example:
            >>> obj = SampleClass("test", 42)
            >>> obj.get_info()
            {"name": "test", "value": 42}
        """
        return {"name": self.name, "value": self.value}

    async def async_method(self, param: str) -> str:
        """异步方法示例

        Args:
            param: 参数

        Returns:
            处理后的字符串
        """
        return f"Processed: {param}"


def sample_function(x: int, y: int = 10) -> int:
    """示例函数

    计算两个数的和。

    Args:
        x: 第一个数
        y: 第二个数，默认为 10

    Returns:
        两数之和

    Example:
        >>> sample_function(5, 3)
        8
    """
    return x + y
'''


# ============================================================================
# AST 文档提取器测试
# ============================================================================


class TestASTDocExtractor:
    """测试 AST 文档提取器"""

    @pytest.fixture
    def sample_file(self):
        """创建示例 Python 文件"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(SAMPLE_PYTHON_CODE)
            temp_path = Path(f.name)

        yield temp_path

        # 清理
        temp_path.unlink()

    @pytest.fixture
    def extractor(self):
        """创建提取器实例"""
        return ASTDocExtractor()

    def test_extract_module(self, extractor, sample_file):
        """测试提取模块文档"""
        module_doc = extractor.extract_module(sample_file)

        assert module_doc.name == sample_file.stem
        assert module_doc.docstring is not None
        assert "示例模块" in module_doc.docstring
        assert len(module_doc.classes) == 1
        assert len(module_doc.functions) == 1

    def test_extract_class(self, extractor, sample_file):
        """测试提取类文档"""
        module_doc = extractor.extract_module(sample_file)
        class_doc = module_doc.classes[0]

        assert class_doc.name == "SampleClass"
        assert class_doc.docstring is not None
        assert "示例类" in class_doc.docstring
        assert len(class_doc.methods) >= 2  # __init__ 和其他方法
        assert len(class_doc.attributes) == 2  # name 和 value

    def test_extract_function(self, extractor, sample_file):
        """测试提取函数文档"""
        module_doc = extractor.extract_module(sample_file)
        func_doc = module_doc.functions[0]

        assert func_doc.name == "sample_function"
        assert func_doc.docstring is not None
        assert "示例函数" in func_doc.docstring
        assert len(func_doc.parameters) == 2
        assert func_doc.return_type == "int"

    def test_extract_parameters(self, extractor, sample_file):
        """测试提取参数文档"""
        module_doc = extractor.extract_module(sample_file)
        func_doc = module_doc.functions[0]

        # 检查参数
        params = {p.name: p for p in func_doc.parameters}
        assert "x" in params
        assert "y" in params

        # 检查类型提示
        assert params["x"].type_hint == "int"
        assert params["y"].type_hint == "int"

        # 检查默认值
        assert params["x"].default is None
        assert params["y"].default == "10"

        # 检查描述
        assert params["x"].description is not None
        assert "第一个数" in params["x"].description

    def test_extract_async_method(self, extractor, sample_file):
        """测试提取异步方法"""
        module_doc = extractor.extract_module(sample_file)
        class_doc = module_doc.classes[0]

        # 查找异步方法
        async_methods = [m for m in class_doc.methods if m.is_async]
        assert len(async_methods) > 0

        async_method = async_methods[0]
        assert async_method.name == "async_method"
        assert async_method.is_async is True

    def test_extract_examples(self, extractor, sample_file):
        """测试提取示例代码"""
        module_doc = extractor.extract_module(sample_file)
        func_doc = module_doc.functions[0]

        assert len(func_doc.examples) > 0
        example = func_doc.examples[0]
        assert "sample_function" in example

    def test_extract_return_description(self, extractor, sample_file):
        """测试提取返回值描述"""
        module_doc = extractor.extract_module(sample_file)
        func_doc = module_doc.functions[0]

        assert func_doc.return_description is not None
        assert "两数之和" in func_doc.return_description


# ============================================================================
# 文档生成器测试
# ============================================================================


class TestDocGenerator:
    """测试文档生成器"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def sample_source_dir(self, temp_dir):
        """创建示例源代码目录"""
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        # 创建示例文件
        sample_file = source_dir / "sample.py"
        sample_file.write_text(SAMPLE_PYTHON_CODE, encoding="utf-8")

        return source_dir

    @pytest.fixture
    def generator(self):
        """创建生成器实例"""
        return DocGenerator()

    def test_generate_markdown_api_docs(self, generator, sample_source_dir, temp_dir):
        """测试生成 Markdown API 文档"""
        output_file = temp_dir / "api.md"

        generator.generate_api_docs(sample_source_dir, output_file, DocFormat.MARKDOWN)

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")

        # 检查内容
        assert "SampleClass" in content
        assert "sample_function" in content
        assert "示例模块" in content

    def test_generate_html_api_docs(self, generator, sample_source_dir, temp_dir):
        """测试生成 HTML API 文档"""
        output_file = temp_dir / "api.html"

        generator.generate_api_docs(sample_source_dir, output_file, DocFormat.HTML)

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")

        # 检查 HTML 结构
        assert "<!DOCTYPE html>" in content
        assert "<html" in content
        assert "SampleClass" in content

    def test_generate_json_api_docs(self, generator, sample_source_dir, temp_dir):
        """测试生成 JSON API 文档"""
        output_file = temp_dir / "api.json"

        generator.generate_api_docs(sample_source_dir, output_file, DocFormat.JSON)

        assert output_file.exists()

        # 检查 JSON 格式
        import json

        data = json.loads(output_file.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) > 0
        assert "name" in data[0]
        assert "classes" in data[0]

    def test_generate_guide_docs(self, generator, temp_dir):
        """测试生成开发指南"""
        output_file = temp_dir / "guide.md"

        generator.generate_guide_docs(output_file, DocFormat.MARKDOWN)

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")

        # 检查内容
        assert "快速开始" in content
        assert "插件结构" in content
        assert "最佳实践" in content
        assert "常见问题" in content


# ============================================================================
# CLI 文档生成器测试
# ============================================================================


class TestCLIDocGenerator:
    """测试 CLI 文档生成器"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cli_generator(self):
        """创建 CLI 生成器实例"""
        return CLIDocGenerator()

    @pytest.fixture
    def mock_app(self):
        """创建模拟的 Typer 应用"""
        import typer

        app = typer.Typer()

        @app.command("test")
        def test_command(
            name: str = typer.Argument(..., help="Name parameter"),
            verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
        ):
            """Test command for documentation"""
            pass

        return app

    def test_generate_markdown_cli_docs(self, cli_generator, mock_app, temp_dir):
        """测试生成 Markdown CLI 文档"""
        output_file = temp_dir / "cli.md"

        cli_generator.generate_cli_docs(mock_app, output_file, DocFormat.MARKDOWN)

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")

        # 检查内容
        assert "CLI 命令参考" in content or "test" in content

    def test_generate_html_cli_docs(self, cli_generator, mock_app, temp_dir):
        """测试生成 HTML CLI 文档"""
        output_file = temp_dir / "cli.html"

        cli_generator.generate_cli_docs(mock_app, output_file, DocFormat.HTML)

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")

        # 检查 HTML 结构
        assert "<!DOCTYPE html>" in content
        assert "<html" in content

    def test_generate_json_cli_docs(self, cli_generator, mock_app, temp_dir):
        """测试生成 JSON CLI 文档"""
        output_file = temp_dir / "cli.json"

        cli_generator.generate_cli_docs(mock_app, output_file, DocFormat.JSON)

        assert output_file.exists()

        # 检查 JSON 格式
        import json

        data = json.loads(output_file.read_text(encoding="utf-8"))
        assert isinstance(data, list)


# ============================================================================
# 集成测试
# ============================================================================


class TestDocGenerationIntegration:
    """文档生成集成测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_full_documentation_generation(self, temp_dir):
        """测试完整的文档生成流程"""
        # 创建源代码目录
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        # 创建示例文件
        sample_file = source_dir / "sample.py"
        sample_file.write_text(SAMPLE_PYTHON_CODE, encoding="utf-8")

        # 创建输出目录
        output_dir = temp_dir / "docs"
        output_dir.mkdir()

        # 生成所有类型的文档
        generator = DocGenerator()

        # API 文档
        api_file = output_dir / "api.md"
        generator.generate_api_docs(source_dir, api_file, DocFormat.MARKDOWN)
        assert api_file.exists()

        # 开发指南
        guide_file = output_dir / "guide.md"
        generator.generate_guide_docs(guide_file, DocFormat.MARKDOWN)
        assert guide_file.exists()

        # 验证所有文件都已生成
        assert len(list(output_dir.glob("*.md"))) >= 2

    def test_multiple_format_generation(self, temp_dir):
        """测试生成多种格式的文档"""
        # 创建源代码目录
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        sample_file = source_dir / "sample.py"
        sample_file.write_text(SAMPLE_PYTHON_CODE, encoding="utf-8")

        output_dir = temp_dir / "docs"
        output_dir.mkdir()

        generator = DocGenerator()

        # 生成不同格式
        for format in [DocFormat.MARKDOWN, DocFormat.HTML, DocFormat.JSON]:
            output_file = output_dir / f"api.{format.value}"
            generator.generate_api_docs(source_dir, output_file, format)
            assert output_file.exists()

        # 验证所有格式都已生成
        assert (output_dir / "api.markdown").exists()
        assert (output_dir / "api.html").exists()
        assert (output_dir / "api.json").exists()
