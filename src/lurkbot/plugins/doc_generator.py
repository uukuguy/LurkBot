"""插件文档生成器

自动从代码中提取文档并生成多种格式的文档。
"""

import ast
import inspect
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape
from loguru import logger


# ============================================================================
# 文档格式枚举
# ============================================================================


class DocFormat(str, Enum):
    """文档格式"""

    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"


class DocType(str, Enum):
    """文档类型"""

    API = "api"  # API 参考文档
    GUIDE = "guide"  # 开发指南
    CLI = "cli"  # CLI 命令文档
    TUTORIAL = "tutorial"  # 教程文档


# ============================================================================
# 文档数据模型
# ============================================================================


@dataclass
class ParameterDoc:
    """参数文档"""

    name: str
    type_hint: str | None
    default: str | None
    description: str | None


@dataclass
class FunctionDoc:
    """函数文档"""

    name: str
    signature: str
    docstring: str | None
    parameters: list[ParameterDoc]
    return_type: str | None
    return_description: str | None
    examples: list[str]
    is_async: bool = False


@dataclass
class ClassDoc:
    """类文档"""

    name: str
    docstring: str | None
    bases: list[str]
    methods: list[FunctionDoc]
    attributes: list[ParameterDoc]
    examples: list[str]


@dataclass
class ModuleDoc:
    """模块文档"""

    name: str
    path: str
    docstring: str | None
    classes: list[ClassDoc]
    functions: list[FunctionDoc]
    imports: list[str]


# ============================================================================
# AST 文档提取器
# ============================================================================


class ASTDocExtractor:
    """使用 AST 从 Python 代码中提取文档"""

    def extract_module(self, file_path: Path) -> ModuleDoc:
        """提取模块文档

        Args:
            file_path: Python 文件路径

        Returns:
            模块文档对象
        """
        with open(file_path, encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)
        module_name = file_path.stem

        # 提取模块级 docstring
        module_docstring = ast.get_docstring(tree)

        # 提取导入
        imports = self._extract_imports(tree)

        # 提取类和函数
        classes = []
        functions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(self._extract_class(node))
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # 只提取模块级函数
                if self._is_module_level(node, tree):
                    functions.append(self._extract_function(node))

        return ModuleDoc(
            name=module_name,
            path=str(file_path),
            docstring=module_docstring,
            classes=classes,
            functions=functions,
            imports=imports,
        )

    def _extract_imports(self, tree: ast.Module) -> list[str]:
        """提取导入语句"""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")
        return imports

    def _is_module_level(self, node: ast.FunctionDef, tree: ast.Module) -> bool:
        """检查函数是否是模块级的"""
        for item in tree.body:
            if item == node:
                return True
        return False

    def _extract_class(self, node: ast.ClassDef) -> ClassDoc:
        """提取类文档"""
        docstring = ast.get_docstring(node)
        bases = [self._get_name(base) for base in node.bases]

        # 提取方法
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(self._extract_function(item))

        # 提取类属性
        attributes = self._extract_class_attributes(node)

        # 提取示例
        examples = self._extract_examples(docstring)

        return ClassDoc(
            name=node.name,
            docstring=docstring,
            bases=bases,
            methods=methods,
            attributes=attributes,
            examples=examples,
        )

    def _extract_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionDoc:
        """提取函数文档"""
        docstring = ast.get_docstring(node)
        is_async = isinstance(node, ast.AsyncFunctionDef)

        # 提取参数
        parameters = self._extract_parameters(node.args, docstring)

        # 提取返回类型
        return_type = self._get_annotation(node.returns) if node.returns else None

        # 从 docstring 提取返回值描述
        return_description = self._extract_return_description(docstring)

        # 提取示例
        examples = self._extract_examples(docstring)

        # 生成函数签名
        signature = self._generate_signature(node)

        return FunctionDoc(
            name=node.name,
            signature=signature,
            docstring=docstring,
            parameters=parameters,
            return_type=return_type,
            return_description=return_description,
            examples=examples,
            is_async=is_async,
        )

    def _extract_parameters(self, args: ast.arguments, docstring: str | None) -> list[ParameterDoc]:
        """提取函数参数"""
        parameters = []
        param_docs = self._parse_param_docs(docstring) if docstring else {}

        # 处理位置参数
        for i, arg in enumerate(args.args):
            if arg.arg == "self" or arg.arg == "cls":
                continue

            type_hint = self._get_annotation(arg.annotation) if arg.annotation else None
            default = None

            # 检查是否有默认值
            defaults_offset = len(args.args) - len(args.defaults)
            if i >= defaults_offset:
                default_node = args.defaults[i - defaults_offset]
                default = self._get_default_value(default_node)

            description = param_docs.get(arg.arg)

            parameters.append(
                ParameterDoc(
                    name=arg.arg, type_hint=type_hint, default=default, description=description
                )
            )

        return parameters

    def _extract_class_attributes(self, node: ast.ClassDef) -> list[ParameterDoc]:
        """提取类属性"""
        attributes = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                attr_name = item.target.id
                type_hint = self._get_annotation(item.annotation) if item.annotation else None
                default = self._get_default_value(item.value) if item.value else None

                attributes.append(
                    ParameterDoc(name=attr_name, type_hint=type_hint, default=default, description=None)
                )

        return attributes

    def _get_annotation(self, node: ast.expr) -> str:
        """获取类型注解字符串"""
        return ast.unparse(node)

    def _get_name(self, node: ast.expr) -> str:
        """获取节点名称"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        else:
            return ast.unparse(node)

    def _get_default_value(self, node: ast.expr) -> str:
        """获取默认值字符串"""
        return ast.unparse(node)

    def _generate_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """生成函数签名"""
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        args_str = self._format_arguments(node.args)
        return_str = f" -> {self._get_annotation(node.returns)}" if node.returns else ""
        return f"{prefix} {node.name}({args_str}){return_str}"

    def _format_arguments(self, args: ast.arguments) -> str:
        """格式化参数列表"""
        parts = []

        # 位置参数
        defaults_offset = len(args.args) - len(args.defaults)
        for i, arg in enumerate(args.args):
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {self._get_annotation(arg.annotation)}"
            if i >= defaults_offset:
                default = self._get_default_value(args.defaults[i - defaults_offset])
                arg_str += f" = {default}"
            parts.append(arg_str)

        return ", ".join(parts)

    def _parse_param_docs(self, docstring: str) -> dict[str, str]:
        """从 docstring 解析参数文档"""
        param_docs = {}
        if not docstring:
            return param_docs

        lines = docstring.split("\n")
        current_param = None

        for line in lines:
            line = line.strip()
            # 匹配 Args: 或 Parameters: 部分
            if line.startswith("Args:") or line.startswith("Parameters:"):
                continue
            # 匹配参数行 (name: description)
            if ":" in line and not line.startswith("Returns:") and not line.startswith("Raises:"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    param_name = parts[0].strip()
                    param_desc = parts[1].strip()
                    param_docs[param_name] = param_desc
                    current_param = param_name
            elif current_param and line and not line.startswith(("Args:", "Returns:", "Raises:", "Example")):
                # 继续上一个参数的描述
                param_docs[current_param] += " " + line

        return param_docs

    def _extract_return_description(self, docstring: str | None) -> str | None:
        """从 docstring 提取返回值描述"""
        if not docstring:
            return None

        lines = docstring.split("\n")
        in_returns = False
        return_lines = []

        for line in lines:
            line = line.strip()
            if line.startswith("Returns:"):
                in_returns = True
                # 提取 Returns: 后面的内容
                after_returns = line[8:].strip()
                if after_returns:
                    return_lines.append(after_returns)
            elif in_returns:
                if line.startswith(("Args:", "Parameters:", "Raises:", "Example")):
                    break
                if line:
                    return_lines.append(line)

        return " ".join(return_lines) if return_lines else None

    def _extract_examples(self, docstring: str | None) -> list[str]:
        """从 docstring 提取示例代码"""
        if not docstring:
            return []

        examples = []
        lines = docstring.split("\n")
        in_example = False
        current_example = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("Example") or stripped.startswith(">>>"):
                in_example = True
                if stripped.startswith(">>>"):
                    current_example.append(line)
            elif in_example:
                if stripped and not stripped.startswith(("Args:", "Returns:", "Raises:")):
                    current_example.append(line)
                elif current_example:
                    examples.append("\n".join(current_example))
                    current_example = []
                    in_example = False

        if current_example:
            examples.append("\n".join(current_example))

        return examples


# ============================================================================
# 文档生成器
# ============================================================================


class DocGenerator:
    """文档生成器

    使用 Jinja2 模板生成多种格式的文档。
    """

    def __init__(self, template_dir: Path | None = None):
        """初始化文档生成器

        Args:
            template_dir: 模板目录路径，如果为 None 则使用内置模板
        """
        self.extractor = ASTDocExtractor()

        # 初始化 Jinja2 环境
        if template_dir:
            from jinja2 import FileSystemLoader

            loader = FileSystemLoader(str(template_dir))
        else:
            # 使用内置模板
            loader = PackageLoader("lurkbot.plugins", "templates")

        self.env = Environment(loader=loader, autoescape=select_autoescape(["html", "xml"]))

        # 注册自定义过滤器
        self.env.filters["format_type"] = self._format_type
        self.env.filters["format_signature"] = self._format_signature

        # 注册全局函数
        self.env.globals["now"] = self._get_current_time

    def generate_api_docs(
        self, source_dir: Path, output_file: Path, format: DocFormat = DocFormat.MARKDOWN
    ) -> None:
        """生成 API 文档

        Args:
            source_dir: 源代码目录
            output_file: 输出文件路径
            format: 文档格式
        """
        logger.info(f"Generating API docs from {source_dir}")

        # 提取所有模块文档
        modules = []
        for py_file in source_dir.glob("*.py"):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue
            try:
                module_doc = self.extractor.extract_module(py_file)
                modules.append(module_doc)
            except Exception as e:
                logger.warning(f"Failed to extract docs from {py_file}: {e}")

        # 生成文档
        if format == DocFormat.MARKDOWN:
            self._generate_markdown_api(modules, output_file)
        elif format == DocFormat.HTML:
            self._generate_html_api(modules, output_file)
        elif format == DocFormat.JSON:
            self._generate_json_api(modules, output_file)

        logger.info(f"API docs generated: {output_file}")

    def generate_guide_docs(self, output_file: Path, format: DocFormat = DocFormat.MARKDOWN) -> None:
        """生成开发指南

        Args:
            output_file: 输出文件路径
            format: 文档格式
        """
        logger.info("Generating plugin development guide")

        template_name = f"guide.{format.value}.j2"
        template = self.env.get_template(template_name)

        content = template.render(
            title="LurkBot 插件开发指南",
            sections=[
                {
                    "title": "快速开始",
                    "content": self._get_quickstart_content(),
                },
                {
                    "title": "插件结构",
                    "content": self._get_structure_content(),
                },
                {
                    "title": "最佳实践",
                    "content": self._get_best_practices_content(),
                },
                {
                    "title": "常见问题",
                    "content": self._get_faq_content(),
                },
            ],
        )

        output_file.write_text(content, encoding="utf-8")
        logger.info(f"Guide docs generated: {output_file}")

    def _generate_markdown_api(self, modules: list[ModuleDoc], output_file: Path) -> None:
        """生成 Markdown 格式的 API 文档"""
        template = self.env.get_template("api.markdown.j2")
        content = template.render(modules=modules)
        output_file.write_text(content, encoding="utf-8")

    def _generate_html_api(self, modules: list[ModuleDoc], output_file: Path) -> None:
        """生成 HTML 格式的 API 文档"""
        template = self.env.get_template("api.html.j2")
        content = template.render(modules=modules)
        output_file.write_text(content, encoding="utf-8")

    def _generate_json_api(self, modules: list[ModuleDoc], output_file: Path) -> None:
        """生成 JSON 格式的 API 文档"""
        import json

        data = [self._module_to_dict(m) for m in modules]
        output_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _module_to_dict(self, module: ModuleDoc) -> dict[str, Any]:
        """将模块文档转换为字典"""
        return {
            "name": module.name,
            "path": module.path,
            "docstring": module.docstring,
            "classes": [self._class_to_dict(c) for c in module.classes],
            "functions": [self._function_to_dict(f) for f in module.functions],
            "imports": module.imports,
        }

    def _class_to_dict(self, cls: ClassDoc) -> dict[str, Any]:
        """将类文档转换为字典"""
        return {
            "name": cls.name,
            "docstring": cls.docstring,
            "bases": cls.bases,
            "methods": [self._function_to_dict(m) for m in cls.methods],
            "attributes": [self._param_to_dict(a) for a in cls.attributes],
            "examples": cls.examples,
        }

    def _function_to_dict(self, func: FunctionDoc) -> dict[str, Any]:
        """将函数文档转换为字典"""
        return {
            "name": func.name,
            "signature": func.signature,
            "docstring": func.docstring,
            "parameters": [self._param_to_dict(p) for p in func.parameters],
            "return_type": func.return_type,
            "return_description": func.return_description,
            "examples": func.examples,
            "is_async": func.is_async,
        }

    def _param_to_dict(self, param: ParameterDoc) -> dict[str, Any]:
        """将参数文档转换为字典"""
        return {
            "name": param.name,
            "type_hint": param.type_hint,
            "default": param.default,
            "description": param.description,
        }

    def _format_type(self, type_hint: str | None) -> str:
        """格式化类型提示"""
        if not type_hint:
            return "Any"
        return type_hint

    def _format_signature(self, signature: str) -> str:
        """格式化函数签名"""
        return signature

    def _get_current_time(self) -> str:
        """获取当前时间"""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _get_quickstart_content(self) -> str:
        """获取快速开始内容"""
        return """
创建一个简单的插件只需要几个步骤：

1. 创建插件目录和 manifest.json
2. 实现插件类
3. 注册插件

示例代码：

```python
from lurkbot.plugins import Plugin

class MyPlugin(Plugin):
    async def execute(self, context):
        return {"message": "Hello from my plugin!"}
```
"""

    def _get_structure_content(self) -> str:
        """获取插件结构内容"""
        return """
标准插件目录结构：

```
my-plugin/
├── manifest.json      # 插件清单
├── plugin.py          # 插件实现
├── config.json        # 配置文件
└── README.md          # 说明文档
```
"""

    def _get_best_practices_content(self) -> str:
        """获取最佳实践内容"""
        return """
1. 使用异步方法提高性能
2. 正确处理错误和异常
3. 遵循资源限制
4. 编写完整的文档
5. 添加单元测试
"""

    def _get_faq_content(self) -> str:
        """获取常见问题内容"""
        return """
Q: 如何访问文件系统？
A: 需要在 manifest.json 中声明 filesystem 权限。

Q: 如何调试插件？
A: 使用 loguru 记录日志，通过 CLI 查看日志输出。

Q: 如何发布插件？
A: 将插件打包并提交到插件市场。
"""


# ============================================================================
# CLI 文档生成器
# ============================================================================


@dataclass
class CLICommandDoc:
    """CLI 命令文档"""

    name: str
    help_text: str | None
    params: list[dict[str, Any]]
    subcommands: list["CLICommandDoc"]


class CLIDocGenerator:
    """CLI 文档生成器

    从 Typer CLI 应用中提取命令文档。
    """

    def __init__(self):
        """初始化 CLI 文档生成器"""
        self.env = Environment(
            loader=PackageLoader("lurkbot.plugins", "templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self.env.globals["now"] = self._get_current_time

    def generate_cli_docs(
        self, app: Any, output_file: Path, format: DocFormat = DocFormat.MARKDOWN
    ) -> None:
        """生成 CLI 文档

        Args:
            app: Typer 应用实例
            output_file: 输出文件路径
            format: 文档格式
        """
        logger.info("Generating CLI documentation")

        # 提取命令文档
        commands = self._extract_commands(app)

        # 生成文档
        if format == DocFormat.MARKDOWN:
            self._generate_markdown_cli(commands, output_file)
        elif format == DocFormat.HTML:
            self._generate_html_cli(commands, output_file)
        elif format == DocFormat.JSON:
            self._generate_json_cli(commands, output_file)

        logger.info(f"CLI docs generated: {output_file}")

    def _extract_commands(self, app: Any) -> list[CLICommandDoc]:
        """提取 CLI 命令文档"""
        commands = []

        # 从 Typer 应用中提取命令
        if hasattr(app, "registered_commands"):
            for cmd in app.registered_commands:
                commands.append(self._extract_command_doc(cmd))
        elif hasattr(app, "commands"):
            for name, cmd in app.commands.items():
                commands.append(self._extract_command_doc(cmd, name))

        return commands

    def _extract_command_doc(self, cmd: Any, name: str | None = None) -> CLICommandDoc:
        """提取单个命令的文档"""
        cmd_name = name or getattr(cmd, "name", "unknown")
        help_text = getattr(cmd, "help", None) or getattr(cmd, "__doc__", None)

        # 提取参数
        params = []
        if hasattr(cmd, "params"):
            for param in cmd.params:
                params.append(
                    {
                        "name": param.name,
                        "type": str(param.type) if hasattr(param, "type") else "str",
                        "required": param.required if hasattr(param, "required") else False,
                        "default": param.default if hasattr(param, "default") else None,
                        "help": param.help if hasattr(param, "help") else None,
                    }
                )

        # 提取子命令
        subcommands = []
        if hasattr(cmd, "commands"):
            for subcmd_name, subcmd in cmd.commands.items():
                subcommands.append(self._extract_command_doc(subcmd, subcmd_name))

        return CLICommandDoc(
            name=cmd_name, help_text=help_text, params=params, subcommands=subcommands
        )

    def _generate_markdown_cli(self, commands: list[CLICommandDoc], output_file: Path) -> None:
        """生成 Markdown 格式的 CLI 文档"""
        template = self.env.get_template("cli.markdown.j2")
        content = template.render(commands=commands)
        output_file.write_text(content, encoding="utf-8")

    def _generate_html_cli(self, commands: list[CLICommandDoc], output_file: Path) -> None:
        """生成 HTML 格式的 CLI 文档"""
        template = self.env.get_template("cli.html.j2")
        content = template.render(commands=commands)
        output_file.write_text(content, encoding="utf-8")

    def _generate_json_cli(self, commands: list[CLICommandDoc], output_file: Path) -> None:
        """生成 JSON 格式的 CLI 文档"""
        import json

        data = [self._command_to_dict(c) for c in commands]
        output_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _command_to_dict(self, cmd: CLICommandDoc) -> dict[str, Any]:
        """将命令文档转换为字典"""
        return {
            "name": cmd.name,
            "help": cmd.help_text,
            "params": cmd.params,
            "subcommands": [self._command_to_dict(sc) for sc in cmd.subcommands],
        }

    def _get_current_time(self) -> str:
        """获取当前时间"""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
