#!/usr/bin/env python3
"""
配置约束检查插件演示

演示如何使用 constraint_checker 插件检查配置约束。
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.plugins.constraint_checker.plugin import ConstraintCheckerPlugin
from unittest.mock import Mock


def demo_single_constraint():
    """演示单组约束检查"""
    print("=" * 60)
    print("演示1: 单组约束检查")
    print("=" * 60)

    plugin = ConstraintCheckerPlugin()

    # 准备测试数据 - 通过的情况
    print("\n[场景1] 配置满足约束:")
    sections_pass = [
        {
            "name": "opSch",
            "fields": {
                "systemMode": "1",
                "debugLevel": "2",  # 允许的值
                "powerMode": "low",  # 允许的值
            },
        }
    ]

    parser_pass = Mock()
    parser_pass.group_by_top_config = Mock(
        return_value=[{"top": sections_pass[0], "subs": []}]
    )

    context_pass = {"config_parser": {"sections": sections_pass, "parser": parser_pass}}

    result = plugin.execute(context_pass)
    print(f"  验证结果: {'✓ 通过' if result['validation_passed'] else '✗ 失败'}")
    print(f"  违规数量: {len(result['violations'])}")

    # 准备测试数据 - 失败的情况
    print("\n[场景2] 配置违反约束:")
    sections_fail = [
        {
            "name": "opSch",
            "fields": {
                "systemMode": "1",
                "debugLevel": "5",  # 不允许的值
                "dangerousFlag": "1",  # 禁止的值
            },
        }
    ]

    parser_fail = Mock()
    parser_fail.group_by_top_config = Mock(
        return_value=[{"top": sections_fail[0], "subs": []}]
    )

    context_fail = {"config_parser": {"sections": sections_fail, "parser": parser_fail}}

    result = plugin.execute(context_fail)
    print(f"  验证结果: {'✓ 通过' if result['validation_passed'] else '✗ 失败'}")
    print(f"  违规数量: {len(result['violations'])}")
    if result["violations"]:
        for idx, violation in enumerate(result["violations"], 1):
            print(f"  [{idx}] {violation['message']}")


def demo_multi_constraint():
    """演示多组约束检查"""
    print("\n" + "=" * 60)
    print("演示2: 多组约束检查")
    print("=" * 60)

    plugin = ConstraintCheckerPlugin()

    # 准备测试数据 - 两组 systemMode 一致
    print("\n[场景1] 两组配置一致:")
    sections_pass = [
        {"name": "opSch", "fields": {"systemMode": "1", "powerLevel": "10"}},
        {"name": "ERCfg", "fields": {}},
        {"name": "opSch", "fields": {"systemMode": "1", "powerLevel": "5"}},
    ]

    parser_pass = Mock()
    parser_pass.group_by_top_config = Mock(
        return_value=[
            {"top": sections_pass[0], "subs": [sections_pass[1]]},
            {"top": sections_pass[2], "subs": []},
        ]
    )

    context_pass = {"config_parser": {"sections": sections_pass, "parser": parser_pass}}

    result = plugin.execute(context_pass)
    print(f"  验证结果: {'✓ 通过' if result['validation_passed'] else '✗ 失败'}")

    # 准备测试数据 - 两组 systemMode 不一致
    print("\n[场景2] 两组配置不一致:")
    sections_fail = [
        {"name": "opSch", "fields": {"systemMode": "1"}},
        {"name": "ERCfg", "fields": {}},
        {"name": "opSch", "fields": {"systemMode": "2"}},  # 不一致
    ]

    parser_fail = Mock()
    parser_fail.group_by_top_config = Mock(
        return_value=[
            {"top": sections_fail[0], "subs": [sections_fail[1]]},
            {"top": sections_fail[2], "subs": []},
        ]
    )

    context_fail = {"config_parser": {"sections": sections_fail, "parser": parser_fail}}

    result = plugin.execute(context_fail)
    print(f"  验证结果: {'✓ 通过' if result['validation_passed'] else '✗ 失败'}")
    if result["violations"]:
        for idx, violation in enumerate(result["violations"], 1):
            print(f"  [{idx}] {violation['message']}")


def demo_version_management():
    """演示版本管理"""
    print("\n" + "=" * 60)
    print("演示3: 版本管理")
    print("=" * 60)

    plugin = ConstraintCheckerPlugin()

    version, rules = plugin._get_active_rules()
    print(f"\n  当前使用版本: {version}")
    print(f"  版本描述: {rules.get('description', '无')}")
    print(f"  单组约束数量: {len(rules.get('single_constraints', []))}")
    print(f"  多组约束数量: {len(rules.get('multi_constraints', []))}")

    # 列出所有可用版本
    all_versions = sorted(plugin.config.get("constraint_rules", {}).keys())
    print(f"\n  所有可用版本:")
    for v in all_versions:
        marker = " (当前使用)" if v == version else ""
        print(f"    - {v}{marker}")


def demo_conditional_constraint():
    """演示条件约束"""
    print("\n" + "=" * 60)
    print("演示4: 条件约束检查")
    print("=" * 60)

    plugin = ConstraintCheckerPlugin()

    # 准备测试数据 - 条件约束
    print("\n[场景] 如果组0 systemMode=1，则组1 powerLevel 必须在允许列表中:")
    sections = [
        {"name": "opSch", "fields": {"systemMode": "1"}},  # 触发条件
        {"name": "ERCfg", "fields": {}},
        {"name": "opSch", "fields": {"powerLevel": "10"}},  # 符合要求
    ]

    parser = Mock()
    parser.group_by_top_config = Mock(
        return_value=[
            {"top": sections[0], "subs": [sections[1]]},
            {"top": sections[2], "subs": []},
        ]
    )

    context = {"config_parser": {"sections": sections, "parser": parser}}

    result = plugin.execute(context)
    print(f"  验证结果: {'✓ 通过' if result['validation_passed'] else '✗ 失败'}")


if __name__ == "__main__":
    print("\n配置约束检查插件演示\n")

    demo_single_constraint()
    demo_multi_constraint()
    demo_version_management()
    demo_conditional_constraint()

    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)
