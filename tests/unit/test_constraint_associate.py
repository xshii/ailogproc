"""关联约束（associate_by）功能测试"""

import unittest
from unittest.mock import Mock

from src.plugins.constraint_checker.plugin import ConstraintCheckerPlugin


class TestAssociateBy(unittest.TestCase):
    """测试 associate_by 关联约束"""

    def _make_plugin(self, constraint_rules):
        """创建测试用的插件实例"""
        plugin = ConstraintCheckerPlugin.__new__(ConstraintCheckerPlugin)
        plugin.config = {
            "enable": True,
            "generate_report": False,
            "constraint_rules": {"test": constraint_rules},
        }
        return plugin

    def _make_context(self, sections, groups):
        """构建测试上下文"""
        parser = Mock()
        parser.group_by_top_config = Mock(return_value=groups)
        # sections 不能为空，否则 execute 会提前返回
        if not sections:
            sections = [{"name": "opSch", "fields": {"placeholder": "1"}}]
        return {"config_parser": {"sections": sections, "parser": parser}}

    def _make_group(self, op_type, fields, subs=None):
        """创建一个配置组"""
        all_fields = {"opType": op_type}
        all_fields.update(fields)
        group = {
            "top": {"name": "opSch", "fields": all_fields},
            "subs": subs or [],
        }
        return group

    # ==================== 两算子关联测试 ====================

    def test_two_roles_same_field_match_pass(self):
        """两算子同字段关联 - 通过"""
        groups = [
            self._make_group("dma", {"channelId": "ch1", "systemMode": "1"}),
            self._make_group("compute", {"channelId": "ch1", "systemMode": "1"}),
        ]
        rules = {
            "single_constraints": [],
            "multi_constraints": [
                {
                    "name": "通道一致性",
                    "associate_by": {
                        "src1": {"where": {"opSch.opType": "dma"}},
                        "src2": {"where": {"opSch.opType": "compute"}},
                        "links": [
                            {"src1": "opSch.channelId", "src2": "opSch.channelId"}
                        ],
                    },
                    "rules": [
                        {"type": "same_value", "field": "opSch.systemMode"}
                    ],
                }
            ],
        }

        plugin = self._make_plugin(rules)
        context = self._make_context([], groups)
        result = plugin.execute(context)
        self.assertTrue(result["validation_passed"])

    def test_two_roles_same_field_match_fail(self):
        """两算子同字段关联 - 违规"""
        groups = [
            self._make_group("dma", {"channelId": "ch1", "systemMode": "1"}),
            self._make_group("compute", {"channelId": "ch1", "systemMode": "2"}),
        ]
        rules = {
            "single_constraints": [],
            "multi_constraints": [
                {
                    "name": "通道一致性",
                    "associate_by": {
                        "src1": {"where": {"opSch.opType": "dma"}},
                        "src2": {"where": {"opSch.opType": "compute"}},
                        "links": [
                            {"src1": "opSch.channelId", "src2": "opSch.channelId"}
                        ],
                    },
                    "rules": [
                        {"type": "same_value", "field": "opSch.systemMode"}
                    ],
                }
            ],
        }

        plugin = self._make_plugin(rules)
        context = self._make_context([], groups)
        result = plugin.execute(context)
        self.assertFalse(result["validation_passed"])
        self.assertEqual(len(result["violations"]), 1)
        self.assertEqual(result["violations"][0]["type"], "same_value")

    def test_two_roles_cross_field_match(self):
        """两算子跨字段关联（outputPort → inputPort）"""
        groups = [
            self._make_group(
                "producer",
                {"outputPort": "portA", "powerLevel": "10", "systemMode": "1"},
            ),
            self._make_group(
                "consumer",
                {"inputPort": "portA", "powerLevel": "15", "systemMode": "1"},
            ),
        ]
        rules = {
            "single_constraints": [],
            "multi_constraints": [
                {
                    "name": "功率约束",
                    "associate_by": {
                        "src1": {"where": {"opSch.opType": "producer"}},
                        "src2": {"where": {"opSch.opType": "consumer"}},
                        "links": [
                            {"src1": "opSch.outputPort", "src2": "opSch.inputPort"}
                        ],
                    },
                    "rules": [
                        {
                            "type": "conditional",
                            "when_group": "src1",
                            "when_field": "opSch.powerLevel",
                            "when_value": "10",
                            "then_group": "src2",
                            "then_field": "opSch.powerLevel",
                            "only_allow": ["5", "10"],
                        }
                    ],
                }
            ],
        }

        plugin = self._make_plugin(rules)
        context = self._make_context([], groups)
        result = plugin.execute(context)
        self.assertFalse(result["validation_passed"])
        self.assertEqual(result["violations"][0]["type"], "conditional")

    def test_interleaved_groups_correct_matching(self):
        """交错排列的组能正确匹配关联"""
        # 日志顺序: dma(ch1), compute(ch2), compute(ch1), dma(ch2)
        groups = [
            self._make_group("dma", {"channelId": "ch1", "powerLevel": "15"}),
            self._make_group("compute", {"channelId": "ch2", "powerLevel": "5"}),
            self._make_group("compute", {"channelId": "ch1", "powerLevel": "10"}),
            self._make_group("dma", {"channelId": "ch2", "powerLevel": "10"}),
        ]
        rules = {
            "single_constraints": [],
            "multi_constraints": [
                {
                    "name": "功率递减",
                    "associate_by": {
                        "src1": {"where": {"opSch.opType": "dma"}},
                        "src2": {"where": {"opSch.opType": "compute"}},
                        "links": [
                            {"src1": "opSch.channelId", "src2": "opSch.channelId"}
                        ],
                    },
                    "rules": [
                        {
                            "type": "sequence",
                            "groups": ["src1", "src2"],
                            "field": "opSch.powerLevel",
                            "order": "decreasing",
                        }
                    ],
                }
            ],
        }

        plugin = self._make_plugin(rules)
        context = self._make_context([], groups)
        result = plugin.execute(context)
        # ch1: dma(15) > compute(10) ✓
        # ch2: dma(10) > compute(5) ✓
        self.assertTrue(result["validation_passed"])

    def test_no_link_match_skips(self):
        """关联字段不匹配时跳过"""
        groups = [
            self._make_group("dma", {"channelId": "ch1", "systemMode": "1"}),
            self._make_group("compute", {"channelId": "ch2", "systemMode": "2"}),
        ]
        rules = {
            "single_constraints": [],
            "multi_constraints": [
                {
                    "name": "通道一致性",
                    "associate_by": {
                        "src1": {"where": {"opSch.opType": "dma"}},
                        "src2": {"where": {"opSch.opType": "compute"}},
                        "links": [
                            {"src1": "opSch.channelId", "src2": "opSch.channelId"}
                        ],
                    },
                    "rules": [
                        {"type": "same_value", "field": "opSch.systemMode"}
                    ],
                }
            ],
        }

        plugin = self._make_plugin(rules)
        context = self._make_context([], groups)
        result = plugin.execute(context)
        # ch1 != ch2，所以没有关联组合，跳过检查
        self.assertTrue(result["validation_passed"])

    # ==================== 三算子关联测试 ====================

    def test_three_roles_linear_chain_pass(self):
        """三算子线性链关联 - 通过"""
        groups = [
            self._make_group(
                "dma",
                {"channelId": "ch1", "outBufId": "X", "powerLevel": "15"},
            ),
            self._make_group(
                "output",
                {"inBufId": "Y", "powerLevel": "5"},
            ),
            self._make_group(
                "compute",
                {"channelId": "ch1", "outBufId": "Y", "powerLevel": "10"},
            ),
        ]
        rules = {
            "single_constraints": [],
            "multi_constraints": [
                {
                    "name": "三级功率递减",
                    "associate_by": {
                        "src1": {"where": {"opSch.opType": "dma"}},
                        "src2": {"where": {"opSch.opType": "compute"}},
                        "src3": {"where": {"opSch.opType": "output"}},
                        "links": [
                            {"src1": "opSch.channelId", "src2": "opSch.channelId"},
                            {"src2": "opSch.outBufId", "src3": "opSch.inBufId"},
                        ],
                    },
                    "rules": [
                        {
                            "type": "sequence",
                            "groups": ["src1", "src2", "src3"],
                            "field": "opSch.powerLevel",
                            "order": "decreasing",
                        }
                    ],
                }
            ],
        }

        plugin = self._make_plugin(rules)
        context = self._make_context([], groups)
        result = plugin.execute(context)
        # src1=dma(15) > src2=compute(10) > src3=output(5) ✓
        self.assertTrue(result["validation_passed"])

    def test_three_roles_linear_chain_fail(self):
        """三算子线性链关联 - 违规（功率不递减）"""
        groups = [
            self._make_group(
                "dma",
                {"channelId": "ch1", "outBufId": "X", "powerLevel": "10"},
            ),
            self._make_group(
                "output",
                {"inBufId": "Y", "powerLevel": "5"},
            ),
            self._make_group(
                "compute",
                {"channelId": "ch1", "outBufId": "Y", "powerLevel": "15"},
            ),
        ]
        rules = {
            "single_constraints": [],
            "multi_constraints": [
                {
                    "name": "三级功率递减",
                    "associate_by": {
                        "src1": {"where": {"opSch.opType": "dma"}},
                        "src2": {"where": {"opSch.opType": "compute"}},
                        "src3": {"where": {"opSch.opType": "output"}},
                        "links": [
                            {"src1": "opSch.channelId", "src2": "opSch.channelId"},
                            {"src2": "opSch.outBufId", "src3": "opSch.inBufId"},
                        ],
                    },
                    "rules": [
                        {
                            "type": "sequence",
                            "groups": ["src1", "src2", "src3"],
                            "field": "opSch.powerLevel",
                            "order": "decreasing",
                        }
                    ],
                }
            ],
        }

        plugin = self._make_plugin(rules)
        context = self._make_context([], groups)
        result = plugin.execute(context)
        # src1=dma(10) < src2=compute(15) — 不递减！
        self.assertFalse(result["validation_passed"])
        self.assertEqual(result["violations"][0]["type"], "sequence")

    def test_three_roles_combinations(self):
        """三算子组合白名单"""
        groups = [
            self._make_group(
                "dma",
                {"channelId": "ch1", "outBufId": "X", "powerLevel": "15"},
            ),
            self._make_group(
                "compute",
                {"channelId": "ch1", "outBufId": "Y", "powerLevel": "10"},
            ),
            self._make_group(
                "output",
                {"inBufId": "Y", "powerLevel": "8"},
            ),
        ]
        rules = {
            "single_constraints": [],
            "multi_constraints": [
                {
                    "name": "功率组合白名单",
                    "associate_by": {
                        "src1": {"where": {"opSch.opType": "dma"}},
                        "src2": {"where": {"opSch.opType": "compute"}},
                        "src3": {"where": {"opSch.opType": "output"}},
                        "links": [
                            {"src1": "opSch.channelId", "src2": "opSch.channelId"},
                            {"src2": "opSch.outBufId", "src3": "opSch.inBufId"},
                        ],
                    },
                    "only_allow_combinations": [
                        {
                            "src1": {"opSch.powerLevel": "15"},
                            "src2": {"opSch.powerLevel": "10"},
                            "src3": {"opSch.powerLevel": "5"},
                        },
                        {
                            "src1": {"opSch.powerLevel": "10"},
                            "src2": {"opSch.powerLevel": "10"},
                            "src3": {"opSch.powerLevel": "5"},
                        },
                    ],
                }
            ],
        }

        plugin = self._make_plugin(rules)
        context = self._make_context([], groups)
        result = plugin.execute(context)
        # (15, 10, 8) 不在白名单中
        self.assertFalse(result["validation_passed"])
        self.assertEqual(result["violations"][0]["type"], "combinations")

    def test_three_roles_fan_out(self):
        """扇出拓扑：src1 分别关联 src2 和 src3"""
        groups = [
            self._make_group(
                "scheduler",
                {"groupId": "g1", "powerMode": "high"},
            ),
            self._make_group(
                "workerA",
                {"groupId": "g1", "powerMode": "high"},
            ),
            self._make_group(
                "workerB",
                {"groupId": "g1", "powerMode": "low"},
            ),
        ]
        rules = {
            "single_constraints": [],
            "multi_constraints": [
                {
                    "name": "调度器与工作者一致",
                    "associate_by": {
                        "src1": {"where": {"opSch.opType": "scheduler"}},
                        "src2": {"where": {"opSch.opType": "workerA"}},
                        "src3": {"where": {"opSch.opType": "workerB"}},
                        "links": [
                            {"src1": "opSch.groupId", "src2": "opSch.groupId"},
                            {"src1": "opSch.groupId", "src3": "opSch.groupId"},
                        ],
                    },
                    "rules": [
                        {
                            "type": "same_value",
                            "groups": ["src1", "src2", "src3"],
                            "field": "opSch.powerMode",
                        }
                    ],
                }
            ],
        }

        plugin = self._make_plugin(rules)
        context = self._make_context([], groups)
        result = plugin.execute(context)
        # workerB.powerMode=low != scheduler.powerMode=high
        self.assertFalse(result["validation_passed"])

    def test_three_roles_multi_field_link(self):
        """多字段联合匹配"""
        groups = [
            self._make_group(
                "dma",
                {"channelId": "ch1", "bankId": "b0", "powerLevel": "15"},
            ),
            self._make_group(
                "compute",
                {"channelId": "ch1", "bankId": "b0", "powerLevel": "10"},
            ),
        ]
        rules = {
            "single_constraints": [],
            "multi_constraints": [
                {
                    "name": "多字段匹配",
                    "associate_by": {
                        "src1": {"where": {"opSch.opType": "dma"}},
                        "src2": {"where": {"opSch.opType": "compute"}},
                        "links": [
                            {
                                "src1": ["opSch.channelId", "opSch.bankId"],
                                "src2": ["opSch.channelId", "opSch.bankId"],
                            }
                        ],
                    },
                    "rules": [
                        {
                            "type": "sequence",
                            "groups": ["src1", "src2"],
                            "field": "opSch.powerLevel",
                            "order": "decreasing",
                        }
                    ],
                }
            ],
        }

        plugin = self._make_plugin(rules)
        context = self._make_context([], groups)
        result = plugin.execute(context)
        self.assertTrue(result["validation_passed"])

    # ==================== CEL / 表达式测试 ====================

    def test_validate_expression_pass(self):
        """CEL/简单表达式 - 通过"""
        groups = [
            self._make_group(
                "dma",
                {"channelId": "ch1", "dataRate": "100"},
            ),
            self._make_group(
                "compute",
                {"channelId": "ch1", "bufSize": "250"},
            ),
        ]
        rules = {
            "single_constraints": [],
            "multi_constraints": [
                {
                    "name": "缓冲区检查",
                    "associate_by": {
                        "src1": {"where": {"opSch.opType": "dma"}},
                        "src2": {"where": {"opSch.opType": "compute"}},
                        "links": [
                            {"src1": "opSch.channelId", "src2": "opSch.channelId"}
                        ],
                    },
                    "validate": [
                        {
                            "expr": "src2.opSch.bufSize >= src1.opSch.dataRate * 2",
                            "message": "缓冲区不足",
                        }
                    ],
                }
            ],
        }

        plugin = self._make_plugin(rules)
        context = self._make_context([], groups)
        result = plugin.execute(context)
        # bufSize(250) >= dataRate(100) * 2 = 200 ✓
        self.assertTrue(result["validation_passed"])

    def test_validate_expression_fail(self):
        """CEL/简单表达式 - 违规"""
        groups = [
            self._make_group(
                "dma",
                {"channelId": "ch1", "dataRate": "100"},
            ),
            self._make_group(
                "compute",
                {"channelId": "ch1", "bufSize": "150"},
            ),
        ]
        rules = {
            "single_constraints": [],
            "multi_constraints": [
                {
                    "name": "缓冲区检查",
                    "associate_by": {
                        "src1": {"where": {"opSch.opType": "dma"}},
                        "src2": {"where": {"opSch.opType": "compute"}},
                        "links": [
                            {"src1": "opSch.channelId", "src2": "opSch.channelId"}
                        ],
                    },
                    "validate": [
                        {
                            "expr": "src2.opSch.bufSize >= src1.opSch.dataRate * 2",
                            "message": "缓冲区必须≥数据速率的2倍",
                        }
                    ],
                }
            ],
        }

        plugin = self._make_plugin(rules)
        context = self._make_context([], groups)
        result = plugin.execute(context)
        # bufSize(150) < dataRate(100) * 2 = 200 ✗
        self.assertFalse(result["validation_passed"])
        self.assertEqual(result["violations"][0]["type"], "validate")
        self.assertIn("缓冲区必须≥数据速率的2倍", result["violations"][0]["message"])

    # ==================== 边界情况 ====================

    def test_mixed_traditional_and_associated(self):
        """传统约束和关联约束混合使用"""
        groups = [
            self._make_group(
                "dma",
                {"channelId": "ch1", "systemMode": "1", "powerLevel": "15"},
            ),
            self._make_group(
                "compute",
                {"channelId": "ch1", "systemMode": "2", "powerLevel": "10"},
            ),
        ]
        rules = {
            "single_constraints": [],
            "multi_constraints": [
                # 传统滑动窗口约束
                {
                    "name": "连续组系统模式一致",
                    "group_count": 2,
                    "rules": [
                        {"type": "same_value", "field": "opSch.systemMode"}
                    ],
                },
                # 关联约束
                {
                    "name": "关联功率检查",
                    "associate_by": {
                        "src1": {"where": {"opSch.opType": "dma"}},
                        "src2": {"where": {"opSch.opType": "compute"}},
                        "links": [
                            {"src1": "opSch.channelId", "src2": "opSch.channelId"}
                        ],
                    },
                    "rules": [
                        {
                            "type": "sequence",
                            "groups": ["src1", "src2"],
                            "field": "opSch.powerLevel",
                            "order": "decreasing",
                        }
                    ],
                },
            ],
        }

        plugin = self._make_plugin(rules)
        context = self._make_context([], groups)
        result = plugin.execute(context)
        # 传统约束违规: systemMode 不一致
        # 关联约束通过: 15 > 10 递减
        self.assertFalse(result["validation_passed"])
        self.assertEqual(len(result["violations"]), 1)
        self.assertEqual(result["violations"][0]["type"], "same_value")


if __name__ == "__main__":
    unittest.main()
