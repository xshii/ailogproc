"""
commands 模块测试 - 命令注册和执行
"""

import argparse

import pytest

from src.commands import (
    _COMMANDS,
    Command,
    get_all_commands,
    register_command,
    setup_subparsers,
)


class TestCommand:
    """测试 Command 抽象基类"""

    def test_command_is_abstract(self):
        """测试 Command 是抽象类"""
        with pytest.raises(TypeError):
            Command()  # 不能直接实例化抽象类

    def test_command_requires_name(self):
        """测试必须实现 name 属性"""

        class IncompleteCommand(Command):
            @property
            def help(self):
                return "Test help"

            def register_arguments(self, parser):
                pass

            def execute(self, args):
                return 0

        with pytest.raises(TypeError):
            IncompleteCommand()

    def test_command_requires_help(self):
        """测试必须实现 help 属性"""

        class IncompleteCommand(Command):
            @property
            def name(self):
                return "test"

            def register_arguments(self, parser):
                pass

            def execute(self, args):
                return 0

        with pytest.raises(TypeError):
            IncompleteCommand()

    def test_command_requires_register_arguments(self):
        """测试必须实现 register_arguments 方法"""

        class IncompleteCommand(Command):
            @property
            def name(self):
                return "test"

            @property
            def help(self):
                return "Test help"

            def execute(self, args):
                return 0

        with pytest.raises(TypeError):
            IncompleteCommand()

    def test_command_requires_execute(self):
        """测试必须实现 execute 方法"""

        class IncompleteCommand(Command):
            @property
            def name(self):
                return "test"

            @property
            def help(self):
                return "Test help"

            def register_arguments(self, parser):
                pass

        with pytest.raises(TypeError):
            IncompleteCommand()

    def test_complete_command(self):
        """测试完整的命令实现"""

        class CompleteCommand(Command):
            @property
            def name(self):
                return "test"

            @property
            def help(self):
                return "Test help"

            def register_arguments(self, parser):
                parser.add_argument("--test", help="Test argument")

            def execute(self, args):
                return 0

        cmd = CompleteCommand()
        assert cmd.name == "test"
        assert cmd.help == "Test help"
        assert cmd.execute(None) == 0

    def test_add_log_level_argument(self):
        """测试添加日志级别参数"""

        class TestCommand(Command):
            @property
            def name(self):
                return "test"

            @property
            def help(self):
                return "Test"

            def register_arguments(self, parser):
                self.add_log_level_argument(parser)

            def execute(self, args):
                return 0

        cmd = TestCommand()
        parser = argparse.ArgumentParser()
        cmd.register_arguments(parser)

        # 测试有效的日志级别
        args = parser.parse_args(["--log-level", "DEBUG"])
        assert args.log_level == "DEBUG"

        # 测试无效的日志级别
        with pytest.raises(SystemExit):
            parser.parse_args(["--log-level", "INVALID"])


class TestCommandRegistry:
    """测试命令注册系统"""

    def setup_method(self):
        """每个测试前清空注册表"""
        _COMMANDS.clear()

    def teardown_method(self):
        """每个测试后清空注册表"""
        _COMMANDS.clear()

    def test_register_command(self):
        """测试注册命令"""

        class TestCmd(Command):
            @property
            def name(self):
                return "testcmd"

            @property
            def help(self):
                return "Test command"

            def register_arguments(self, parser):
                pass

            def execute(self, args):
                return 0

        cmd = TestCmd()
        register_command(cmd)

        commands = get_all_commands()
        assert "testcmd" in commands
        assert commands["testcmd"] is cmd

    def test_register_multiple_commands(self):
        """测试注册多个命令"""

        class Cmd1(Command):
            @property
            def name(self):
                return "cmd1"

            @property
            def help(self):
                return "Command 1"

            def register_arguments(self, parser):
                pass

            def execute(self, args):
                return 0

        class Cmd2(Command):
            @property
            def name(self):
                return "cmd2"

            @property
            def help(self):
                return "Command 2"

            def register_arguments(self, parser):
                pass

            def execute(self, args):
                return 0

        cmd1 = Cmd1()
        cmd2 = Cmd2()

        register_command(cmd1)
        register_command(cmd2)

        commands = get_all_commands()
        assert len(commands) == 2
        assert "cmd1" in commands
        assert "cmd2" in commands

    def test_get_all_commands_returns_copy(self):
        """测试 get_all_commands 返回副本"""

        class TestCmd(Command):
            @property
            def name(self):
                return "test"

            @property
            def help(self):
                return "Test"

            def register_arguments(self, parser):
                pass

            def execute(self, args):
                return 0

        cmd = TestCmd()
        register_command(cmd)

        commands1 = get_all_commands()
        commands2 = get_all_commands()

        # 应该是不同的对象
        assert commands1 is not commands2
        # 但内容相同
        assert commands1 == commands2

    def test_register_duplicate_command_name(self):
        """测试注册重复命令名"""

        class Cmd1(Command):
            @property
            def name(self):
                return "duplicate"

            @property
            def help(self):
                return "Command 1"

            def register_arguments(self, parser):
                pass

            def execute(self, args):
                return 1

        class Cmd2(Command):
            @property
            def name(self):
                return "duplicate"

            @property
            def help(self):
                return "Command 2"

            def register_arguments(self, parser):
                pass

            def execute(self, args):
                return 2

        cmd1 = Cmd1()
        cmd2 = Cmd2()

        register_command(cmd1)
        register_command(cmd2)

        # 后注册的会覆盖先注册的
        commands = get_all_commands()
        assert commands["duplicate"].execute(None) == 2


class TestSetupSubparsers:
    """测试子解析器设置"""

    def setup_method(self):
        """每个测试前清空注册表"""
        _COMMANDS.clear()

    def teardown_method(self):
        """每个测试后清空注册表"""
        _COMMANDS.clear()

    def test_setup_subparsers_empty(self):
        """测试空注册表"""
        parser = argparse.ArgumentParser()
        setup_subparsers(parser)

        # 应该可以解析但没有命令
        args = parser.parse_args([])
        assert not hasattr(args, "command") or args.command is None

    def test_setup_subparsers_with_commands(self):
        """测试设置子解析器"""

        class TestCmd(Command):
            @property
            def name(self):
                return "test"

            @property
            def help(self):
                return "Test command"

            def register_arguments(self, parser):
                parser.add_argument("--option", help="Test option")

            def execute(self, args):
                return 0

        cmd = TestCmd()
        register_command(cmd)

        parser = argparse.ArgumentParser()
        setup_subparsers(parser)

        # 解析命令
        args = parser.parse_args(["test", "--option", "value"])
        assert args.command == "test"
        assert args.option == "value"
        assert hasattr(args, "func")
        assert args.func(args) == 0

    def test_setup_subparsers_multiple_commands(self):
        """测试多个命令的子解析器"""

        class Cmd1(Command):
            @property
            def name(self):
                return "cmd1"

            @property
            def help(self):
                return "Command 1"

            def register_arguments(self, parser):
                parser.add_argument("arg1")

            def execute(self, args):
                return 1

        class Cmd2(Command):
            @property
            def name(self):
                return "cmd2"

            @property
            def help(self):
                return "Command 2"

            def register_arguments(self, parser):
                parser.add_argument("arg2")

            def execute(self, args):
                return 2

        register_command(Cmd1())
        register_command(Cmd2())

        parser = argparse.ArgumentParser()
        setup_subparsers(parser)

        # 测试第一个命令
        args1 = parser.parse_args(["cmd1", "value1"])
        assert args1.command == "cmd1"
        assert args1.arg1 == "value1"
        assert args1.func(args1) == 1

        # 测试第二个命令
        args2 = parser.parse_args(["cmd2", "value2"])
        assert args2.command == "cmd2"
        assert args2.arg2 == "value2"
        assert args2.func(args2) == 2

    def test_subparser_help(self):
        """测试子命令帮助信息"""

        class HelpTestCmd(Command):
            @property
            def name(self):
                return "helptest"

            @property
            def help(self):
                return "This is a helpful command"

            def register_arguments(self, parser):
                pass

            def execute(self, args):
                return 0

        register_command(HelpTestCmd())

        parser = argparse.ArgumentParser()
        setup_subparsers(parser)

        # 获取帮助信息
        with pytest.raises(SystemExit):
            parser.parse_args(["helptest", "--help"])
