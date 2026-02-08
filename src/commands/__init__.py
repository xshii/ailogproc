"""
命令模块 - 子命令注册和管理
"""

from abc import ABC, abstractmethod
import argparse


class Command(ABC):
    """命令基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """命令名称"""
        ...

    @property
    @abstractmethod
    def help(self) -> str:
        """命令帮助信息"""
        ...

    @abstractmethod
    def register_arguments(self, parser: argparse.ArgumentParser) -> None:
        """注册命令参数

        Args:
            parser: 该命令的子解析器
        """
        ...

    @abstractmethod
    def execute(self, args: argparse.Namespace) -> int:
        """执行命令

        Args:
            args: 解析后的参数

        Returns:
            退出码 (0 表示成功)
        """
        ...


# 命令注册表
_COMMANDS = {}


def register_command(command: Command) -> None:
    """注册命令"""
    _COMMANDS[command.name] = command


def get_all_commands() -> dict:
    """获取所有已注册的命令"""
    return _COMMANDS.copy()


def setup_subparsers(parser: argparse.ArgumentParser) -> None:
    """设置所有子命令

    Args:
        parser: 主解析器
    """
    subparsers = parser.add_subparsers(
        dest="command",
        help="可用的命令",
        metavar="<command>",
    )

    # 为每个命令创建子解析器
    for cmd_name, command in _COMMANDS.items():
        subparser = subparsers.add_parser(
            cmd_name,
            help=command.help,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        command.register_arguments(subparser)
        subparser.set_defaults(func=command.execute)
