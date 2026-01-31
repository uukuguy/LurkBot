"""容器沙箱

使用 Docker 容器技术实现更严格的插件隔离，包括资源配额、网络隔离和文件系统隔离。
"""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any

import docker
from docker.errors import DockerException
from loguru import logger

from .models import PluginConfig, PluginExecutionContext, PluginExecutionResult


# ============================================================================
# 容器沙箱
# ============================================================================


class ContainerSandbox:
    """容器沙箱

    使用 Docker 容器隔离插件执行环境。
    """

    def __init__(
        self,
        config: PluginConfig,
        image: str = "python:3.12-slim",
        network_mode: str = "none",
    ):
        """初始化沙箱

        Args:
            config: 插件配置
            image: Docker 镜像
            network_mode: 网络模式（none, bridge, host）
        """
        self.config = config
        self.image = image
        self.network_mode = network_mode if config.allow_network else "none"

        try:
            self.client = docker.from_env()
            self._ensure_image()
        except DockerException as e:
            logger.error(f"Docker 客户端初始化失败: {e}")
            raise

    def _ensure_image(self) -> None:
        """确保 Docker 镜像存在"""
        try:
            self.client.images.get(self.image)
            logger.debug(f"Docker 镜像已存在: {self.image}")
        except docker.errors.ImageNotFound:
            logger.info(f"拉取 Docker 镜像: {self.image}")
            self.client.images.pull(self.image)

    async def execute(
        self,
        plugin_name: str,
        plugin_code: str,
        context: PluginExecutionContext,
        timeout: float = 30.0,
    ) -> PluginExecutionResult:
        """在容器中执行插件

        Args:
            plugin_name: 插件名称
            plugin_code: 插件代码
            context: 执行上下文
            timeout: 超时时间（秒）

        Returns:
            执行结果
        """
        logger.debug(f"在容器中执行插件: {plugin_name}")

        try:
            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # 写入插件代码
                plugin_file = temp_path / "plugin.py"
                plugin_file.write_text(plugin_code)

                # 写入上下文数据
                context_file = temp_path / "context.json"
                context_file.write_text(context.model_dump_json())

                # 写入执行脚本
                runner_script = temp_path / "runner.py"
                runner_script.write_text(self._generate_runner_script())

                # 创建容器
                container = self._create_container(temp_path, timeout)

                try:
                    # 启动容器
                    container.start()

                    # 等待容器完成
                    result = await self._wait_for_container(container, timeout)

                    return result

                finally:
                    # 清理容器
                    try:
                        container.remove(force=True)
                    except Exception as e:
                        logger.warning(f"清理容器失败: {e}")

        except asyncio.TimeoutError:
            return PluginExecutionResult(
                success=False,
                error="执行超时",
                execution_time=timeout,
            )
        except Exception as e:
            logger.error(f"容器执行失败: {e}")
            return PluginExecutionResult(
                success=False,
                error=str(e),
                execution_time=0.0,
            )

    def _create_container(self, work_dir: Path, timeout: float) -> Any:
        """创建 Docker 容器

        Args:
            work_dir: 工作目录
            timeout: 超时时间

        Returns:
            容器对象
        """
        # 资源限制
        mem_limit = f"{self.config.max_memory_mb}m"
        cpu_quota = int((self.config.max_cpu_percent / 100.0) * 100000)

        # 卷挂载
        volumes = {
            str(work_dir): {"bind": "/workspace", "mode": "rw"}
        }

        # 环境变量
        environment = {
            "PYTHONUNBUFFERED": "1",
            "TIMEOUT": str(timeout),
        }

        # 创建容器
        container = self.client.containers.create(
            image=self.image,
            command=["python", "/workspace/runner.py"],
            working_dir="/workspace",
            volumes=volumes,
            environment=environment,
            network_mode=self.network_mode,
            mem_limit=mem_limit,
            cpu_quota=cpu_quota,
            cpu_period=100000,
            read_only=not self.config.allow_filesystem,
            security_opt=["no-new-privileges"],
            cap_drop=["ALL"],
            detach=True,
            auto_remove=False,
        )

        logger.debug(f"创建容器: {container.short_id}")
        return container

    async def _wait_for_container(
        self, container: Any, timeout: float
    ) -> PluginExecutionResult:
        """等待容器完成

        Args:
            container: 容器对象
            timeout: 超时时间

        Returns:
            执行结果
        """
        try:
            # 等待容器完成（使用 asyncio 包装同步调用）
            loop = asyncio.get_event_loop()
            exit_status = await asyncio.wait_for(
                loop.run_in_executor(None, container.wait),
                timeout=timeout,
            )

            # 获取日志
            logs = container.logs().decode("utf-8")

            # 解析结果 - 尝试从日志中提取 JSON
            try:
                # 查找最后一行 JSON
                for line in reversed(logs.split("\n")):
                    if line.strip().startswith("{"):
                        result_data = json.loads(line)
                        return PluginExecutionResult(**result_data)
            except Exception as e:
                logger.warning(f"解析结果失败: {e}")

            # 如果没有找到 JSON，根据退出码返回结果
            if exit_status["StatusCode"] == 0:
                return PluginExecutionResult(
                    success=True,
                    result=logs,
                    execution_time=0.0,
                )
            else:
                return PluginExecutionResult(
                    success=False,
                    error=f"容器退出码: {exit_status['StatusCode']}",
                    result=logs,
                    execution_time=0.0,
                )

        except asyncio.TimeoutError:
            # 超时，强制停止容器
            try:
                container.kill()
            except Exception:
                pass
            raise

    def _generate_runner_script(self) -> str:
        """生成容器内的执行脚本

        Returns:
            Python 脚本代码
        """
        return '''
import asyncio
import json
import sys
import time
import traceback
from pathlib import Path


async def main():
    """主函数"""
    start_time = time.time()
    try:
        # 读取上下文
        context_file = Path("/workspace/context.json")
        context_data = json.loads(context_file.read_text())

        # 导入插件
        sys.path.insert(0, "/workspace")
        import plugin

        # 执行插件
        if hasattr(plugin, "execute"):
            result = await plugin.execute(context_data)
        else:
            result = {"error": "插件没有 execute 函数"}

        # 输出结果
        execution_time = time.time() - start_time
        output = {
            "success": True,
            "result": result,
            "execution_time": execution_time,
        }
        print(json.dumps(output))

    except Exception as e:
        # 输出错误
        execution_time = time.time() - start_time
        output = {
            "success": False,
            "error": str(e),
            "result": traceback.format_exc(),
            "execution_time": execution_time,
        }
        print(json.dumps(output))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
'''

    def close(self) -> None:
        """关闭沙箱"""
        if hasattr(self, "client"):
            self.client.close()


# ============================================================================
# 工具函数
# ============================================================================


def is_docker_available() -> bool:
    """检查 Docker 是否可用

    Returns:
        是否可用
    """
    try:
        client = docker.from_env()
        client.ping()
        client.close()
        return True
    except Exception:
        return False
