#!/usr/bin/env python3
"""
配置约束检查复杂场景测试 - 5个top表的综合违规测试
"""

import os
import sys
import unittest
from unittest.mock import Mock

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.plugins.constraint_checker.plugin import ConstraintCheckerPlugin


class TestConstraintCheckerComplex(unittest.TestCase):
    """测试复杂场景：5个top表，多种违规"""

    def setUp(self):
        """测试前准备"""
        self.plugin = ConstraintCheckerPlugin()

    def test_five_tops_with_violations(self):
        """
        测试5个top表的复杂违规场景

        预期违规：
        - 单组违规：组2、4、5
        - 多组违规：涉及组3、4
        """
        print("\n" + "=" * 70)
        print("5个Top表违规测试")
        print("=" * 70)

        # 准备5个top表的配置数据
        sections = [
            # ===== 组1（索引0）：正常配置 =====
            {
                "name": "opSch",
                "fields": {
                    "systemMode": "1",
                    "debugLevel": "2",
                    "powerMode": "high",
                    "configId": "10",
                },
            },
            {"name": "ERCfg", "fields": {"cfgGroup": "0"}},  # 子表
            # ===== 组2（索引1）：违反单组约束 =====
            {
                "name": "opSch",
                "fields": {
                    "systemMode": "1",
                    "debugLevel": "5",  # ✗ 违反only_allow（应在0-3）
                    "powerMode": "medium",
                    "configId": "20",
                },
            },
            {"name": "ERCfg", "fields": {"cfgGroup": "1"}},
            # ===== 组3（索引2）：触发多组违规 =====
            {
                "name": "opSch",
                "fields": {
                    "systemMode": "2",  # 与组2不同 → same_value违规
                    "debugLevel": "1",
                    "powerMode": "low",
                    "configId": "15",  # 不递增(10→20→15) → sequence违规
                },
            },
            {"name": "ERCfg", "fields": {"cfgGroup": "2"}},
            # ===== 组4（索引3）：违反单组约束 + 多组违规 =====
            {
                "name": "opSch",
                "fields": {
                    "systemMode": "1",  # 与组3不同 → same_value违规
                    "debugLevel": "2",
                    "dangerousFlag": "1",  # ✗ 违反forbid（systemMode=1时禁止）
                    "powerMode": "medium",
                    "configId": "5",  # 不递增 → sequence违规
                },
            },
            {"name": "ERCfg", "fields": {"cfgGroup": "3"}},
            # ===== 组5（索引4）：违反单组约束 =====
            {
                "name": "opSch",
                "fields": {
                    "systemMode": "2",
                    "debugLevel": "3",
                    "productionMode": "1",  # ✗ 违反forbid（debugLevel=3且systemMode=2时禁止）
                    "powerMode": "high",
                    "configId": "3",
                },
            },
        ]

        # Mock parser
        parser = Mock()
        parser.group_by_top_config = Mock(
            return_value=[
                {"top": sections[0], "subs": [sections[1]]},
                {"top": sections[2], "subs": [sections[3]]},
                {"top": sections[4], "subs": [sections[5]]},
                {"top": sections[6], "subs": [sections[7]]},
                {"top": sections[8], "subs": []},
            ]
        )

        context = {"config_parser": {"sections": sections, "parser": parser}}

        # 执行约束检查
        result = self.plugin.execute(context)

        # 打印详细结果
        print(f"\n验证结果: {'✓ 通过' if result['validation_passed'] else '✗ 失败'}")
        print(f"使用规则版本: {result['version']}")
        print(f"总违规数: {len(result['violations'])}")

        violations = result["violations"]

        # 按类型分类违规
        single_violations = [
            v for v in violations if v["type"] in ["only_allow", "forbid"]
        ]
        multi_violations = [
            v
            for v in violations
            if v["type"] in ["same_value", "sequence", "conditional"]
        ]

        print(f"\n单组约束违规: {len(single_violations)} 个")
        for idx, v in enumerate(single_violations, 1):
            print(f"  [{idx}] {v['message']}")

        print(f"\n多组约束违规: {len(multi_violations)} 个")
        for idx, v in enumerate(multi_violations, 1):
            print(f"  [{idx}] {v['message']}")

        # 验证预期
        self.assertFalse(result["validation_passed"], "应该检测到违规")
        self.assertGreater(len(violations), 0, "应该有违规记录")

        # 验证单组违规（组2、4、5）
        single_groups = {v.get("group") for v in single_violations}
        print(f"\n单组违规涉及的组: {sorted(single_groups)}")
        self.assertIn(1, single_groups, "组2（索引1）应该违反单组约束")
        self.assertIn(3, single_groups, "组4（索引3）应该违反单组约束")
        self.assertIn(4, single_groups, "组5（索引4）应该违反单组约束")

        # 验证多组违规（涉及组3、4）
        multi_groups = set()
        for v in multi_violations:
            if "groups" in v:
                multi_groups.update(v["groups"])
            if "when_group" in v:
                multi_groups.add(v["when_group"])
            if "then_group" in v:
                multi_groups.add(v["then_group"])

        print(f"多组违规涉及的组: {sorted(multi_groups)}")
        self.assertTrue(
            2 in multi_groups or 3 in multi_groups,
            "应该有涉及组3（索引2）或组4（索引3）的多组违规",
        )

        # 打印总结
        print("\n" + "=" * 70)
        print("违规总结:")
        print("=" * 70)
        print("✗ 组1（索引0）: 无违规 ✓")
        print("✗ 组2（索引1）: 单组违规 - debugLevel=5 超出允许范围")
        print("✗ 组3（索引2）: 多组违规 - systemMode不一致 + configId不递增")
        print("✗ 组4（索引3）: 单组违规 + 多组违规 - dangerousFlag禁止 + 不一致性")
        print("✗ 组5（索引4）: 单组违规 - productionMode在调试模式下禁止")
        print("=" * 70)

    def test_violation_details(self):
        """详细测试每种违规类型"""
        print("\n" + "=" * 70)
        print("详细违规类型测试")
        print("=" * 70)

        sections = [
            # 组1
            {
                "name": "opSch",
                "fields": {
                    "systemMode": "1",
                    "debugLevel": "2",
                    "powerMode": "high",
                    "configId": "10",
                },
            },
            {"name": "ERCfg", "fields": {}},
            # 组2：单组only_allow违规
            {
                "name": "opSch",
                "fields": {
                    "systemMode": "1",
                    "debugLevel": "5",  # only_allow违规
                    "powerMode": "medium",
                    "configId": "20",
                },
            },
            {"name": "ERCfg", "fields": {}},
            # 组3：多组same_value违规
            {
                "name": "opSch",
                "fields": {
                    "systemMode": "2",  # same_value违规
                    "debugLevel": "1",
                    "powerMode": "low",
                    "configId": "15",  # sequence违规
                },
            },
            {"name": "ERCfg", "fields": {}},
            # 组4：单组forbid违规 + 多组违规
            {
                "name": "opSch",
                "fields": {
                    "systemMode": "1",
                    "debugLevel": "2",
                    "dangerousFlag": "1",  # forbid违规
                    "powerMode": "medium",
                    "configId": "5",
                },
            },
            {"name": "ERCfg", "fields": {}},
            # 组5：单组forbid违规（多条件触发）
            {
                "name": "opSch",
                "fields": {
                    "systemMode": "2",
                    "debugLevel": "3",
                    "productionMode": "1",  # forbid违规
                    "powerMode": "high",
                    "configId": "3",
                },
            },
        ]

        parser = Mock()
        parser.group_by_top_config = Mock(
            return_value=[
                {"top": sections[0], "subs": [sections[1]]},
                {"top": sections[2], "subs": [sections[3]]},
                {"top": sections[4], "subs": [sections[5]]},
                {"top": sections[6], "subs": [sections[7]]},
                {"top": sections[8], "subs": []},
            ]
        )

        context = {"config_parser": {"sections": sections, "parser": parser}}
        result = self.plugin.execute(context)

        violations = result["violations"]

        # 统计各类型违规
        violation_types = {}
        for v in violations:
            v_type = v["type"]
            violation_types[v_type] = violation_types.get(v_type, 0) + 1

        print("\n违规类型统计:")
        for v_type, count in sorted(violation_types.items()):
            print(f"  {v_type}: {count} 个")

        # 验证至少有这些违规类型
        self.assertIn("only_allow", violation_types, "应该有only_allow违规")
        self.assertIn("forbid", violation_types, "应该有forbid违规")
        self.assertTrue(
            "same_value" in violation_types or "sequence" in violation_types,
            "应该有多组约束违规",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
