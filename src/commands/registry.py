"""
命令注册 - 注册所有可用命令
"""

from src.commands import register_command
from src.commands.cfg2excel import Cfg2ExcelCommand
from src.commands.cfglimit import CfgLimitCommand
from src.commands.perflog import PerfLogCommand


def register_all_commands():
    """注册所有命令"""
    register_command(Cfg2ExcelCommand())
    register_command(CfgLimitCommand())
    register_command(PerfLogCommand())
