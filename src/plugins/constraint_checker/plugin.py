"""
配置约束检查插件 - 验证配置是否满足约束条件
"""

import os
import yaml
from typing import List, Dict
from src.plugins.base import Plugin
from src.utils import info, warning, error


class ConstraintCheckerPlugin(Plugin):
    """配置约束检查插件 - Level 2 (Validator)"""

    level = 2  # 验证层，在 config_parser 之后执行
    dependencies = ["config_parser"]  # 依赖配置解析插件

    def execute(self, context: dict) -> dict:
        """检查配置约束

        Args:
            context: 上下文字典，需要包含：
                - config_parser.sections: 配置块列表
                - config_parser.parser: ConfigParser实例

        Returns:
            {
                'validation_passed': True/False,
                'violations': 违规列表,
                'version': 使用的规则版本
            }
        """
        # 获取 config_parser 的输出
        config_data = context.get("config_parser", {})
        sections = config_data.get("sections", [])
        parser = config_data.get("parser")

        if not sections:
            info("[约束检查] 无配置数据，跳过检查")
            result = {"validation_passed": True, "violations": []}
            # 检查是否为仅检查模式
            if self.config.get("check_only", False):
                info("[约束检查] 仅检查模式：跳过后续插件执行")
                result["stop_pipeline"] = True
            return result

        info("[约束检查] 开始检查配置约束...")

        # 获取激活的规则版本
        version, rules = self._get_active_rules()
        info(f"[约束检查] 使用规则版本: {version}")

        violations = []

        # 1. 检查单组约束
        single_violations = self._check_single_constraints(
            sections, rules, parser, context
        )
        violations.extend(single_violations)

        # 2. 检查多组约束
        multi_violations = self._check_multi_constraints(
            sections, rules, parser, context
        )
        violations.extend(multi_violations)

        # 检查是否为仅检查模式
        check_only = self.config.get("check_only", False)

        # 输出结果
        if violations:
            error(f"[约束检查] ✗ 发现 {len(violations)} 个违规")
            for idx, violation in enumerate(violations, 1):
                error(f"  [{idx}] {violation['message']}")
            result = {
                "validation_passed": False,
                "violations": violations,
                "version": version,
            }
        else:
            info("[约束检查] ✓ 所有约束检查通过")
            result = {
                "validation_passed": True,
                "violations": [],
                "version": version,
            }

        # 如果是仅检查模式，设置停止标志
        if check_only:
            info("[约束检查] 仅检查模式：跳过后续插件执行")
            result["stop_pipeline"] = True

        return result

    def _get_active_rules(self) -> tuple:
        """获取激活的规则版本

        优先级：
        1. 配置中的 constraint_rules（用于测试）
        2. rules/ 目录中的规则文件（生产环境）

        Returns:
            (version, rules): 版本名称和规则字典
        """
        # 1. 优先检查配置中的 constraint_rules（用于测试）
        constraint_rules = self.config.get("constraint_rules", {})
        if constraint_rules:
            active_version = self.config.get("active_version")

            # 如果指定了版本，使用指定版本
            if active_version and active_version in constraint_rules:
                return active_version, constraint_rules[active_version]

            # 否则使用最新版本（按版本号排序）
            versions = sorted(constraint_rules.keys())
            if versions:
                latest_version = versions[-1]
                return latest_version, constraint_rules[latest_version]

        # 2. 从 rules/ 目录加载规则文件（生产环境）
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        rules_dir = self.config.get("rules_dir", "rules")
        rules_path = os.path.join(plugin_dir, rules_dir)

        if not os.path.exists(rules_path):
            warning(f"[约束检查] 规则目录不存在: {rules_path}")
            return "none", {"single_constraints": [], "multi_constraints": []}

        # 获取所有规则文件（格式: v1.0.0_20240115.yaml）
        import re

        rule_files = [
            f
            for f in os.listdir(rules_path)
            if re.match(r"v\d+\.\d+\.\d+_\d+\.yaml$", f)
        ]

        if not rule_files:
            warning(f"[约束检查] 规则目录中没有规则文件: {rules_path}")
            return "none", {"single_constraints": [], "multi_constraints": []}

        # 提取版本号（去掉 "v" 前缀和 ".yaml" 后缀）
        # v1.3.0_20240208.yaml -> 1.3.0_20240208
        available_versions = [f[1:-5] for f in rule_files]

        # 确定要使用的版本
        active_version = self.config.get("active_version")

        if active_version:
            # 使用指定版本
            if active_version not in available_versions:
                warning(f"[约束检查] 指定的规则版本不存在: {active_version}")
                warning(f"[约束检查] 可用版本: {', '.join(sorted(available_versions))}")
                return "none", {"single_constraints": [], "multi_constraints": []}
            target_version = active_version
        else:
            # 使用最新版本（按版本号排序）
            target_version = sorted(available_versions)[-1]

        # 加载规则文件
        rule_file = os.path.join(rules_path, f"v{target_version}.yaml")
        try:
            with open(rule_file, "r", encoding="utf-8") as f:
                rules = yaml.safe_load(f)

            if not rules:
                warning(f"[约束检查] 规则文件为空: {rule_file}")
                return "none", {"single_constraints": [], "multi_constraints": []}

            return target_version, rules

        except Exception as e:
            error(f"[约束检查] 加载规则文件失败: {rule_file}, 错误: {e}")
            return "none", {"single_constraints": [], "multi_constraints": []}

    def _check_single_constraints(
        self, sections: List[Dict], rules: Dict, parser, context: dict
    ) -> List[Dict]:
        """检查单组约束"""
        violations = []
        single_constraints = rules.get("single_constraints", [])

        # 获取 top 配置关键字
        top_keyword = self._get_top_keyword(context)

        # 将配置按 top 分组
        groups = parser.group_by_top_config(top_keyword) if parser else []

        for group_idx, group in enumerate(groups):
            # 扁平化 group：合并 top 和 subs 的字段
            # top 字段：不加前缀
            # sub 字段：加前缀 "sectionName.fieldName"
            flat_fields = self._flatten_group_fields(group)

            # 检查每个单组约束规则
            for rule in single_constraints:
                rule_violations = self._check_single_rule(flat_fields, rule, group_idx)
                violations.extend(rule_violations)

        return violations

    def _check_single_rule(
        self, flat_fields: Dict, rule: Dict, group_idx: int
    ) -> List[Dict]:
        """检查单个单组约束规则

        Args:
            flat_fields: 扁平化的字段字典，包含：
                - top 字段（不带前缀）: {"powerLevel": "5"}
                - sub 字段（带前缀）: {"subTable1.mode": "A"}
            rule: 约束规则
            group_idx: 组索引
        """
        violations = []
        fields = flat_fields

        # 检查触发条件
        when_conditions = rule.get("when", {})
        if not self._match_conditions(fields, when_conditions):
            return violations  # 条件不匹配，跳过

        rule_name = rule.get("name", "未命名规则")

        # 检查 only_allow 约束
        only_allow = rule.get("only_allow", {})
        for field, allowed_values in only_allow.items():
            if field in fields:
                value = str(fields[field])
                if value not in allowed_values:
                    violations.append(
                        {
                            "type": "only_allow",
                            "rule": rule_name,
                            "group": group_idx,
                            "field": field,
                            "value": value,
                            "allowed": allowed_values,
                            "message": f"[组{group_idx}] {rule_name}: 字段 '{field}' 的值 '{value}' 不在允许列表 {allowed_values} 中",
                        }
                    )

        # 检查 forbid 约束
        forbid = rule.get("forbid", {})
        for field, forbidden_values in forbid.items():
            if field in fields:
                value = str(fields[field])
                if value in forbidden_values:
                    violations.append(
                        {
                            "type": "forbid",
                            "rule": rule_name,
                            "group": group_idx,
                            "field": field,
                            "value": value,
                            "forbidden": forbidden_values,
                            "message": f"[组{group_idx}] {rule_name}: 字段 '{field}' 的值 '{value}' 在禁止列表中",
                        }
                    )

        return violations

    def _check_multi_constraints(
        self, sections: List[Dict], rules: Dict, parser, context: dict
    ) -> List[Dict]:
        """检查多组约束"""
        violations = []
        multi_constraints = rules.get("multi_constraints", [])

        if not multi_constraints:
            return violations

        # 获取 top 配置关键字并分组
        top_keyword = self._get_top_keyword(context)
        groups = parser.group_by_top_config(top_keyword) if parser else []

        if len(groups) < 2:
            return violations  # 少于2组，无法检查多组约束

        # 检查每个多组约束规则
        for rule in multi_constraints:
            rule_violations = self._check_multi_rule(groups, rule)
            violations.extend(rule_violations)

        return violations

    def _check_multi_rule(self, groups: List[Dict], rule: Dict) -> List[Dict]:
        """检查单个多组约束规则"""
        violations = []
        group_count = rule.get("group_count", 2)
        rule_name = rule.get("name", "未命名规则")
        constraint_rules = rule.get("rules", [])

        # 检查连续的 group_count 个组
        for start_idx in range(len(groups) - group_count + 1):
            target_groups = groups[start_idx : start_idx + group_count]

            # 对每条规则进行检查
            for constraint in constraint_rules:
                constraint_type = constraint.get("type")

                if constraint_type == "same_value":
                    # 检查指定字段在所有组中值相同
                    violation = self._check_same_value(
                        target_groups, constraint, rule_name, start_idx
                    )
                    if violation:
                        violations.append(violation)

                elif constraint_type == "sequence":
                    # 检查字段值序列（递增/递减）
                    violation = self._check_sequence(
                        target_groups, constraint, rule_name, start_idx
                    )
                    if violation:
                        violations.append(violation)

                elif constraint_type == "conditional":
                    # 条件约束：如果组A满足条件，则组B必须满足约束
                    violation = self._check_conditional(
                        target_groups, constraint, rule_name, start_idx
                    )
                    if violation:
                        violations.append(violation)

        return violations

    def _check_same_value(
        self, groups: List[Dict], constraint: Dict, rule_name: str, start_idx: int
    ) -> Dict | None:
        """检查字段在所有组中值相同

        支持 top 字段和带前缀的 sub 字段，例如：
        - field: "powerLevel"         # top 字段
        - field: "subTable1.mode"     # sub 字段
        """
        field = constraint.get("field")
        if not field:
            return None

        values = []
        for group in groups:
            # 使用扁平化字段
            flat_fields = self._flatten_group_fields(group)
            value = flat_fields.get(field)
            values.append(str(value) if value is not None else None)

        # 检查是否所有值相同
        if len(set(values)) > 1:
            group_indices = [start_idx + i for i in range(len(groups))]
            return {
                "type": "same_value",
                "rule": rule_name,
                "groups": group_indices,
                "field": field,
                "values": values,
                "message": f"[组{group_indices}] {rule_name}: 字段 '{field}' 在各组中的值不一致: {values}",
            }

        return None

    def _check_sequence(
        self, groups: List[Dict], constraint: Dict, rule_name: str, start_idx: int
    ) -> Dict | None:
        """检查字段值序列

        支持 top 字段和带前缀的 sub 字段，例如：
        - field: "powerLevel"         # top 字段
        - field: "subTable1.index"    # sub 字段
        """
        field = constraint.get("field")
        order = constraint.get("order", "increasing")  # increasing 或 decreasing

        if not field:
            return None

        values = []
        for group in groups:
            # 使用扁平化字段
            flat_fields = self._flatten_group_fields(group)
            value = flat_fields.get(field)
            try:
                values.append(int(value) if value is not None else None)
            except (ValueError, TypeError):
                values.append(None)

        # 检查序列
        if None in values:
            return {
                "type": "sequence",
                "rule": rule_name,
                "field": field,
                "message": f"{rule_name}: 字段 '{field}' 存在空值，无法检查序列",
            }

        is_valid = True
        if order == "increasing":
            is_valid = all(values[i] < values[i + 1] for i in range(len(values) - 1))
        elif order == "decreasing":
            is_valid = all(values[i] > values[i + 1] for i in range(len(values) - 1))

        if not is_valid:
            group_indices = [start_idx + i for i in range(len(groups))]
            return {
                "type": "sequence",
                "rule": rule_name,
                "groups": group_indices,
                "field": field,
                "order": order,
                "values": values,
                "message": f"[组{group_indices}] {rule_name}: 字段 '{field}' 的值 {values} 不满足{order}序列",
            }

        return None

    def _check_conditional(
        self, groups: List[Dict], constraint: Dict, rule_name: str, start_idx: int
    ) -> Dict | None:
        """检查条件约束

        支持 top 字段和带前缀的 sub 字段，例如：
        - when_field: "opSch.powerLevel"     # top 字段
        - then_field: "subTable1.mode"       # sub 字段
        """
        when_group = constraint.get("when_group", 0)
        when_field = constraint.get("when_field")
        when_value = str(constraint.get("when_value", ""))

        then_group = constraint.get("then_group", 1)
        then_field = constraint.get("then_field")

        if when_group >= len(groups) or then_group >= len(groups):
            return None

        # 使用扁平化字段检查触发条件
        when_flat_fields = self._flatten_group_fields(groups[when_group])
        actual_when_value = str(when_flat_fields.get(when_field, ""))

        if actual_when_value != when_value:
            return None  # 条件不满足，跳过

        # 使用扁平化字段检查约束
        then_flat_fields = self._flatten_group_fields(groups[then_group])
        actual_then_value = str(then_flat_fields.get(then_field, ""))

        # 检查 only_allow
        only_allow = constraint.get("only_allow", [])
        if only_allow and actual_then_value not in only_allow:
            return {
                "type": "conditional",
                "rule": rule_name,
                "when_group": start_idx + when_group,
                "then_group": start_idx + then_group,
                "message": f"[组{start_idx + when_group}->{start_idx + then_group}] {rule_name}: "
                f"当组{start_idx + when_group}的 {when_field}={when_value} 时，"
                f"组{start_idx + then_group}的 {then_field} 应在 {only_allow} 中，实际值为 {actual_then_value}",
            }

        # 检查 forbid
        forbid = constraint.get("forbid", [])
        if forbid and actual_then_value in forbid:
            return {
                "type": "conditional",
                "rule": rule_name,
                "when_group": start_idx + when_group,
                "then_group": start_idx + then_group,
                "message": f"[组{start_idx + when_group}->{start_idx + then_group}] {rule_name}: "
                f"当组{start_idx + when_group}的 {when_field}={when_value} 时，"
                f"组{start_idx + then_group}的 {then_field} 不应为 {actual_then_value}",
            }

        return None

    def _match_conditions(self, fields: Dict, conditions: Dict) -> bool:
        """检查字段是否匹配条件（所有条件必须同时满足）"""
        for field, expected_value in conditions.items():
            actual_value = str(fields.get(field, ""))
            if actual_value != str(expected_value):
                return False
        return True

    def _flatten_group_fields(self, group: Dict) -> Dict:
        """将 group 的所有字段扁平化为一个字典（所有字段都带前缀）

        Args:
            group: 包含 top 和 subs 的组字典
                {
                    "top": {"name": "opSch", "fields": {"powerLevel": "5"}},
                    "subs": [
                        {"name": "I2C", "fields": {"speed": "100K"}},
                        {"name": "I2C", "fields": {"speed": "400K"}},  # 同名！
                        {"name": "SPI", "fields": {"mode": "master"}}
                    ]
                }

        Returns:
            扁平化的字段字典（所有字段都带前缀）：
                {
                    "opSch.powerLevel": "5",    # top 字段
                    "I2C.0.speed": "100K",      # 重复的 section 添加索引
                    "I2C.1.speed": "400K",
                    "SPI.mode": "master"        # 单个 section 不添加索引
                }
        """
        flat_fields = {}

        # 添加 top 字段（也加前缀）
        top_section = group.get("top")
        if top_section:
            section_name = top_section.get("name", "")
            top_fields = top_section.get("fields", {})

            for field_name, field_value in top_fields.items():
                prefixed_name = f"{section_name}.{field_name}"
                flat_fields[prefixed_name] = field_value

        # 统计 sub section 的名称出现次数
        subs = group.get("subs", [])
        section_name_counts = {}
        for sub in subs:
            name = sub.get("name", "")
            section_name_counts[name] = section_name_counts.get(name, 0) + 1

        # 添加 sub 字段（如果有重复的 section 名称，添加索引）
        section_indices = {}  # 记录每个 section 当前的索引
        for sub_section in subs:
            section_name = sub_section.get("name", "")
            sub_fields = sub_section.get("fields", {})

            # 如果该 section 名称出现多次，使用索引
            if section_name_counts.get(section_name, 0) > 1:
                idx = section_indices.get(section_name, 0)
                section_indices[section_name] = idx + 1
                section_prefix = f"{section_name}.{idx}"
            else:
                # 单个 section，不使用索引
                section_prefix = section_name

            for field_name, field_value in sub_fields.items():
                prefixed_name = f"{section_prefix}.{field_name}"
                flat_fields[prefixed_name] = field_value

        return flat_fields

    def _get_top_keyword(self, context: dict = None) -> str:
        """获取 top 配置关键字

        优先级：
        1. constraint_checker 自己的配置（top_keyword）
        2. context 中的 excel_writer_config（top_table.log_keyword）
        3. 默认值 "opSch"

        Args:
            context: 上下文字典（可选）

        Returns:
            top 表的关键字
        """
        # 1. 优先使用 constraint_checker 自己的配置
        if "top_keyword" in self.config:
            return self.config["top_keyword"]

        # 2. 尝试从 context 的 excel_writer_config 获取
        if context:
            excel_writer_config = context.get("excel_writer_config")
            if excel_writer_config:
                top_table = excel_writer_config.get("top_table", {})
                log_keyword = top_table.get("log_keyword")
                if log_keyword:
                    return log_keyword

        # 3. 使用默认值
        return "opSch"
