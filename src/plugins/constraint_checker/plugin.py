"""
配置约束检查插件 - 验证配置是否满足约束条件
"""

import ast
import json
import os
from datetime import datetime
from typing import Dict, List

import yaml

from src.plugins.base import Plugin
from src.utils import debug, error, info, warning


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
        sections, parser = self._extract_config_data(context)

        if not sections:
            return self._handle_empty_config()

        info("[约束检查] 开始检查配置约束...")

        version, rules = self._get_active_rules()
        info(f"[约束检查] 使用规则版本: {version}")

        violations = self._run_all_checks(sections, rules, parser, context)
        result = self._build_result(violations, version)
        result = self._add_report_if_needed(result, context)
        result = self._apply_check_only_mode(result)

        return result

    def _extract_config_data(self, context: dict) -> tuple:
        """提取配置数据"""
        config_data = context.get("config_parser", {})
        sections = config_data.get("sections", [])
        parser = config_data.get("parser")
        return sections, parser

    def _handle_empty_config(self) -> dict:
        """处理空配置的情况"""
        info("[约束检查] 无配置数据，跳过检查")
        result = {"validation_passed": True, "violations": []}

        if self.config.get("check_only", False):
            info("[约束检查] 仅检查模式：跳过后续插件执行")
            result["stop_pipeline"] = True

        return result

    def _run_all_checks(
        self, sections: list, rules: dict, parser, context: dict
    ) -> list:
        """运行所有约束检查"""
        violations = []

        # 检查单组约束
        single_violations = self._check_single_constraints(
            sections, rules, parser, context
        )
        violations.extend(single_violations)

        # 检查多组约束
        multi_violations = self._check_multi_constraints(
            sections, rules, parser, context
        )
        violations.extend(multi_violations)

        return violations

    def _build_result(self, violations: list, version: str) -> dict:
        """构建检查结果"""
        if violations:
            error(f"[约束检查] ✗ 发现 {len(violations)} 个违规")
            for idx, violation in enumerate(violations, 1):
                error(f"  [{idx}] {violation['message']}")

            return {
                "validation_passed": False,
                "violations": violations,
                "version": version,
            }
        else:
            info("[约束检查] ✓ 所有约束检查通过")
            return {
                "validation_passed": True,
                "violations": [],
                "version": version,
            }

    def _add_report_if_needed(self, result: dict, context: dict) -> dict:
        """如果需要，添加报告"""
        if self.config.get("generate_report", False):
            report_path = self._generate_report(result, context)
            if report_path:
                result["report_path"] = report_path
                debug(f"[约束检查] 报告已生成: {report_path}")

        return result

    def _apply_check_only_mode(self, result: dict) -> dict:
        """应用仅检查模式"""
        if self.config.get("check_only", False):
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
            with open(rule_file, encoding="utf-8") as f:
                rules = yaml.safe_load(f)

            if not rules:
                warning(f"[约束检查] 规则文件为空: {rule_file}")
                return "none", {"single_constraints": [], "multi_constraints": []}

            return target_version, rules

        except Exception as e:
            error(f"[约束检查] 加载规则文件失败: {rule_file}, 错误: {e}")
            return "none", {"single_constraints": [], "multi_constraints": []}

    # ==================== 单组约束 ====================

    def _check_single_constraints(
        self, _sections: List[Dict], rules: Dict, parser, context: dict
    ) -> List[Dict]:
        """检查单组约束"""
        violations = []
        single_constraints = rules.get("single_constraints", [])

        # 获取 top 配置关键字
        top_keyword = self._get_top_keyword(context)

        # 将配置按 top 分组
        groups = parser.group_by_top_config(top_keyword) if parser else []

        for group_idx, group in enumerate(groups):
            flat_fields = self._flatten_group_fields(group)

            for rule in single_constraints:
                rule_violations = self._check_single_rule(flat_fields, rule, group_idx)
                violations.extend(rule_violations)

        return violations

    def _check_single_rule(
        self, flat_fields: Dict, rule: Dict, group_idx: int
    ) -> List[Dict]:
        """检查单个单组约束规则"""
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
                            "message": (
                                f"[组{group_idx}] {rule_name}: 字段 '{field}' "
                                f"的值 '{value}' 不在允许列表 {allowed_values} 中"
                            ),
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
                            "message": (
                                f"[组{group_idx}] {rule_name}: "
                                f"字段 '{field}' 的值 '{value}' "
                                f"在禁止列表 {forbidden_values} 中"
                            ),
                        }
                    )

        return violations

    # ==================== 多组约束（统一架构） ====================

    def _check_multi_constraints(
        self, _sections: List[Dict], rules: Dict, parser, context: dict
    ) -> List[Dict]:
        """检查多组约束（统一处理滑动窗口和关联约束）"""
        violations = []
        multi_constraints = rules.get("multi_constraints", [])

        if not multi_constraints:
            return violations

        top_keyword = self._get_top_keyword(context)
        groups = parser.group_by_top_config(top_keyword) if parser else []

        if len(groups) < 2:
            return violations

        for rule in multi_constraints:
            if "associate_by" in rule:
                rule_violations = self._check_associated_rule(groups, rule)
            else:
                rule_violations = self._check_sliding_window_rule(groups, rule)
            violations.extend(rule_violations)

        return violations

    def _check_sliding_window_rule(
        self, groups: List[Dict], rule: Dict
    ) -> List[Dict]:
        """滑动窗口约束：转换为统一角色分配后检查"""
        violations = []
        group_count = rule.get("group_count", 2)

        for start_idx in range(len(groups) - group_count + 1):
            window = groups[start_idx : start_idx + group_count]

            # 转换为统一的角色分配格式（group0, group1, ...）
            role_assignment = {}
            for i, g in enumerate(window):
                role_key = f"group{i}"
                role_assignment[role_key] = {
                    "idx": start_idx + i,
                    "fields": self._flatten_group_fields(g),
                }

            violations.extend(
                self._check_constraints_on_assignment(rule, role_assignment)
            )

        return violations

    def _check_associated_rule(
        self, groups: List[Dict], rule: Dict
    ) -> List[Dict]:
        """关联约束：匹配角色后使用统一检查"""
        violations = []
        rule_name = rule.get("name", "未命名规则")
        associate_by = rule.get("associate_by", {})

        # 1. 解析角色定义
        role_defs = self._parse_role_definitions(associate_by)
        if not role_defs:
            warning(f"[约束检查] {rule_name}: associate_by 中未定义有效角色")
            return violations

        # 2. 扁平化所有组的字段
        flat_groups = []
        for idx, group in enumerate(groups):
            flat_fields = self._flatten_group_fields(group)
            flat_groups.append({"idx": idx, "fields": flat_fields})

        # 3. 按角色分类候选组
        role_candidates = self._classify_by_roles(flat_groups, role_defs)

        for role_key in role_defs:
            if not role_candidates.get(role_key):
                debug(
                    f"[约束检查] {rule_name}: 角色 '{role_key}' "
                    f"没有匹配的配置组，跳过"
                )
                return violations

        # 4. 查找满足所有 links 条件的关联组合
        links = associate_by.get("links", [])
        matched_tuples = self._find_matched_tuples(
            role_defs, role_candidates, links
        )

        if not matched_tuples:
            debug(f"[约束检查] {rule_name}: 没有找到满足关联条件的组合")
            return violations

        # 5. 对每个匹配的组合，使用统一检查
        for role_assignment in matched_tuples:
            violations.extend(
                self._check_constraints_on_assignment(rule, role_assignment)
            )

        return violations

    # ==================== 统一约束检查 ====================

    def _check_constraints_on_assignment(
        self, rule: Dict, role_assignment: Dict[str, Dict]
    ) -> List[Dict]:
        """统一的约束检查入口

        无论来源是滑动窗口还是关联匹配，都使用相同的检查逻辑。

        Args:
            rule: 约束规则
            role_assignment: 角色分配 {"group0": {...}, "group1": {...}}
                           或 {"src1": {...}, "src2": {...}, "src3": {...}}
        """
        violations = []
        rule_name = rule.get("name", "未命名规则")
        roles = sorted(role_assignment.keys())
        role_label = self._build_role_label(role_assignment, roles)

        # 1. rules 中的约束
        for constraint in rule.get("rules", []):
            constraint_type = constraint.get("type")
            violation = None

            if constraint_type == "same_value":
                violation = self._check_same_value(
                    role_assignment, constraint, rule_name, role_label, roles
                )
            elif constraint_type == "sequence":
                violation = self._check_sequence(
                    role_assignment, constraint, rule_name, role_label, roles
                )
            elif constraint_type == "conditional":
                violation = self._check_conditional(
                    role_assignment, constraint, rule_name, role_label
                )

            if violation:
                violations.append(violation)

        # 2. only_allow_combinations
        combinations = rule.get("only_allow_combinations", [])
        if combinations:
            violation = self._check_combinations(
                role_assignment, combinations, rule_name, role_label, roles
            )
            if violation:
                violations.append(violation)

        # 3. validate（CEL / 安全表达式）
        for validate_rule in rule.get("validate", []):
            violation = self._check_validate_expr(
                role_assignment, validate_rule, rule_name, role_label
            )
            if violation:
                violations.append(violation)

        return violations

    def _build_role_label(
        self, role_assignment: Dict, roles: List[str]
    ) -> str:
        """构建角色标签用于错误消息"""
        if all(r.startswith("group") for r in roles):
            # 滑动窗口格式：组[0, 1]
            indices = [role_assignment[r]["idx"] for r in roles]
            return f"组{indices}"
        else:
            # 关联约束格式：src1=组0, src2=组1
            return ", ".join(
                f"{role}=组{role_assignment[role]['idx']}" for role in roles
            )

    def _resolve_role_key(self, role_ref, role_assignment: Dict) -> str | None:
        """将约束中的角色引用解析为 role_assignment 中的 key

        支持：
        - 整数索引 (0, 1) → 映射到 "group0", "group1"
        - 字符串角色名 ("src1", "group0") → 直接匹配
        """
        # 直接匹配
        if role_ref in role_assignment:
            return role_ref
        # 整数到 "group{n}" 的映射
        if isinstance(role_ref, int):
            key = f"group{role_ref}"
            if key in role_assignment:
                return key
        return None

    def _check_same_value(
        self,
        role_assignment: Dict[str, Dict],
        constraint: Dict,
        rule_name: str,
        role_label: str,
        roles: List[str],
    ) -> Dict | None:
        """检查字段在所有角色对应的组中值相同"""
        field = constraint.get("field")
        if not field:
            return None

        check_roles = constraint.get("groups", roles)
        resolved = [self._resolve_role_key(r, role_assignment) for r in check_roles]
        resolved = [r for r in resolved if r is not None]

        values = []
        for role in resolved:
            group = role_assignment.get(role)
            if group:
                val = group["fields"].get(field)
                values.append(str(val) if val is not None else None)

        if len(set(values)) > 1:
            return {
                "type": "same_value",
                "rule": rule_name,
                "field": field,
                "values": values,
                "message": (
                    f"[{role_label}] {rule_name}: "
                    f"字段 '{field}' 在各组中的值不一致: {values}"
                ),
            }

        return None

    def _check_sequence(
        self,
        role_assignment: Dict[str, Dict],
        constraint: Dict,
        rule_name: str,
        role_label: str,
        roles: List[str],
    ) -> Dict | None:
        """检查字段值序列（递增/递减）"""
        field = constraint.get("field")
        order = constraint.get("order", "increasing")
        if not field:
            return None

        check_roles = constraint.get("groups", roles)
        resolved = [self._resolve_role_key(r, role_assignment) for r in check_roles]
        resolved = [r for r in resolved if r is not None]

        values = []
        for role in resolved:
            group = role_assignment.get(role)
            if group:
                val = group["fields"].get(field)
                try:
                    values.append(int(val) if val is not None else None)
                except (ValueError, TypeError):
                    values.append(None)

        if None in values:
            return {
                "type": "sequence",
                "rule": rule_name,
                "field": field,
                "message": (
                    f"[{role_label}] {rule_name}: "
                    f"字段 '{field}' 存在空值，无法检查序列"
                ),
            }

        is_valid = True
        if order == "increasing":
            is_valid = all(values[i] < values[i + 1] for i in range(len(values) - 1))
        elif order == "decreasing":
            is_valid = all(values[i] > values[i + 1] for i in range(len(values) - 1))

        if not is_valid:
            order_desc = "递增" if order == "increasing" else "递减"
            return {
                "type": "sequence",
                "rule": rule_name,
                "field": field,
                "order": order,
                "values": values,
                "message": (
                    f"[{role_label}] {rule_name}: "
                    f"字段 '{field}' 的值 {values} 不满足{order_desc}序列"
                ),
            }

        return None

    def _check_conditional(
        self,
        role_assignment: Dict[str, Dict],
        constraint: Dict,
        rule_name: str,
        role_label: str,
    ) -> Dict | None:
        """检查条件约束

        when_group/then_group 支持整数索引(0, 1)和字符串角色名("src1", "src2")。
        """
        when_ref = constraint.get("when_group", 0)
        when_field = constraint.get("when_field")
        when_value = str(constraint.get("when_value", ""))

        then_ref = constraint.get("then_group", 1)
        then_field = constraint.get("then_field")

        when_key = self._resolve_role_key(when_ref, role_assignment)
        then_key = self._resolve_role_key(then_ref, role_assignment)

        if when_key is None or then_key is None:
            return None

        when_group = role_assignment[when_key]
        then_group = role_assignment[then_key]

        actual_when_value = str(when_group["fields"].get(when_field, ""))
        if actual_when_value != when_value:
            return None  # 条件不满足，跳过

        actual_then_value = str(then_group["fields"].get(then_field, ""))

        # 检查 only_allow
        only_allow = constraint.get("only_allow", [])
        if only_allow and actual_then_value not in only_allow:
            return {
                "type": "conditional",
                "rule": rule_name,
                "message": (
                    f"[{role_label}] {rule_name}: "
                    f"当 {when_ref}(组{when_group['idx']}) 的 "
                    f"{when_field}={when_value} 时，"
                    f"{then_ref}(组{then_group['idx']}) 的 {then_field} "
                    f"应在 {only_allow} 中，实际值为 '{actual_then_value}'"
                ),
            }

        # 检查 forbid
        forbid = constraint.get("forbid", [])
        if forbid and actual_then_value in forbid:
            return {
                "type": "conditional",
                "rule": rule_name,
                "message": (
                    f"[{role_label}] {rule_name}: "
                    f"当 {when_ref}(组{when_group['idx']}) 的 "
                    f"{when_field}={when_value} 时，"
                    f"{then_ref}(组{then_group['idx']}) 的 {then_field} "
                    f"不应为 '{actual_then_value}'（禁止值: {forbid}）"
                ),
            }

        return None

    def _check_combinations(
        self,
        role_assignment: Dict[str, Dict],
        combinations: List[Dict],
        rule_name: str,
        role_label: str,
        roles: List[str],
    ) -> Dict | None:
        """检查字段组合白名单

        组合中的 key 与 role_assignment 的 key 对应（group0/group1 或 src1/src2/src3）。
        """
        actual_values = {}
        for role in roles:
            group = role_assignment.get(role)
            if group:
                actual_values[role] = group["fields"]

        for combo in combinations:
            if self._match_combination(actual_values, combo, roles):
                return None  # 匹配成功

        # 所有组合都不匹配
        actual_summary_parts = []
        for role in roles:
            if role in actual_values and role in combinations[0]:
                combo_fields = combinations[0][role]
                role_vals = {
                    f: actual_values[role].get(f, "?")
                    for f in (combo_fields if isinstance(combo_fields, dict) else {})
                }
                actual_summary_parts.append(f"{role}={role_vals}")

        return {
            "type": "combinations",
            "rule": rule_name,
            "message": (
                f"[{role_label}] {rule_name}: "
                f"字段组合 ({', '.join(actual_summary_parts)}) "
                f"不在允许的 {len(combinations)} 个组合中"
            ),
        }

    def _match_combination(
        self, actual_values: Dict, combo: Dict, roles: List[str]
    ) -> bool:
        """检查实际值是否匹配一个允许的组合"""
        for role in roles:
            if role not in combo:
                continue
            expected = combo[role]
            if not isinstance(expected, dict):
                continue
            actual = actual_values.get(role, {})

            for field, expected_val in expected.items():
                actual_val = str(actual.get(field, ""))
                if actual_val != str(expected_val):
                    return False

        return True

    # ==================== 表达式验证 ====================

    def _check_validate_expr(
        self,
        role_assignment: Dict[str, Dict],
        validate_rule: Dict,
        rule_name: str,
        role_label: str,
    ) -> Dict | None:
        """使用 CEL 或安全表达式检查约束

        validate_rule 格式:
          expr: "src2.opSch.bufSize >= src1.opSch.dataRate * 2"
          message: "上游功率不能低于下游"
        """
        expr = validate_rule.get("expr", "")
        custom_message = validate_rule.get("message", "表达式验证失败")

        if not expr:
            return None

        # 构建执行上下文：将扁平字段转为嵌套字典
        eval_context = {}
        for role, group in role_assignment.items():
            role_fields = {}
            for field_key, field_val in group["fields"].items():
                parts = field_key.split(".")
                current = role_fields
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                # 尝试转为数值以支持比较运算
                try:
                    field_val = int(field_val)
                except (ValueError, TypeError):
                    try:
                        field_val = float(field_val)
                    except (ValueError, TypeError):
                        pass
                current[parts[-1]] = field_val
            eval_context[role] = role_fields

        # 优先尝试 CEL 引擎
        result = self._evaluate_cel(expr, eval_context)

        if result is None:
            # CEL 不可用，使用 AST 安全求值
            result = self._evaluate_safe_expr(expr, eval_context)

        if result is False:
            return {
                "type": "validate",
                "rule": rule_name,
                "roles": {r: role_assignment[r]["idx"] for r in role_assignment},
                "expr": expr,
                "message": f"[{role_label}] {rule_name}: {custom_message}",
            }

        return None

    def _evaluate_cel(self, expr: str, context: Dict) -> bool | None:
        """使用 CEL 引擎求值（可选依赖）

        Returns:
            True/False 表示结果，None 表示 CEL 不可用
        """
        try:
            import celpy

            env = celpy.Environment()
            cel_ast = env.compile(expr)
            prgm = env.program(cel_ast)

            cel_context = {}
            for key, value in context.items():
                cel_context[key] = celpy.json_to_cel(value)

            result = prgm.evaluate(cel_context)
            return bool(result)
        except ImportError:
            return None  # CEL 不可用
        except Exception as e:
            debug(f"[约束检查] CEL 表达式求值失败: {expr}, 错误: {e}")
            return None

    def _evaluate_safe_expr(self, expr: str, context: Dict) -> bool | None:
        """基于 AST 的安全表达式求值

        仅支持：比较(>=, <=, >, <, ==, !=)、算术(+, -, *, /)、
        逻辑(and, or, not)、属性访问(src1.opSch.powerLevel)、常量。
        不支持函数调用、下标访问、import 等危险操作。
        """
        try:
            tree = ast.parse(expr, mode="eval")
            return bool(self._eval_node(tree.body, context))
        except Exception as e:
            debug(f"[约束检查] 安全表达式求值失败: {expr}, 错误: {e}")
            return None

    def _eval_node(self, node, context: Dict):
        """递归求值 AST 节点（白名单模式）"""
        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left, context)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, context)
                op_map = {
                    ast.GtE: lambda a, b: a >= b,
                    ast.LtE: lambda a, b: a <= b,
                    ast.Gt: lambda a, b: a > b,
                    ast.Lt: lambda a, b: a < b,
                    ast.Eq: lambda a, b: a == b,
                    ast.NotEq: lambda a, b: a != b,
                }
                op_func = op_map.get(type(op))
                if op_func is None:
                    raise ValueError(f"不支持的比较运算: {type(op).__name__}")
                if not op_func(left, right):
                    return False
                left = right
            return True

        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, context)
            right = self._eval_node(node.right, context)
            op_map = {
                ast.Add: lambda a, b: a + b,
                ast.Sub: lambda a, b: a - b,
                ast.Mult: lambda a, b: a * b,
                ast.Div: lambda a, b: a / b,
                ast.Mod: lambda a, b: a % b,
            }
            op_func = op_map.get(type(node.op))
            if op_func is None:
                raise ValueError(f"不支持的算术运算: {type(node.op).__name__}")
            return op_func(left, right)

        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand, context)
            if isinstance(node.op, ast.USub):
                return -operand
            elif isinstance(node.op, ast.Not):
                return not operand
            raise ValueError(f"不支持的一元运算: {type(node.op).__name__}")

        elif isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                return all(self._eval_node(v, context) for v in node.values)
            elif isinstance(node.op, ast.Or):
                return any(self._eval_node(v, context) for v in node.values)
            raise ValueError(f"不支持的逻辑运算: {type(node.op).__name__}")

        elif isinstance(node, ast.Attribute):
            value = self._eval_node(node.value, context)
            if isinstance(value, dict):
                return value.get(node.attr)
            raise ValueError(f"属性访问目标不是字典: {type(value).__name__}")

        elif isinstance(node, ast.Name):
            if node.id not in context:
                raise ValueError(f"未知变量: {node.id}")
            return context[node.id]

        elif isinstance(node, ast.Constant):
            return node.value

        raise ValueError(f"不支持的 AST 节点: {type(node).__name__}")

    # ==================== 关联约束辅助方法 ====================

    def _parse_role_definitions(self, associate_by: Dict) -> Dict:
        """解析角色定义（src1/src2/src3）"""
        role_defs = {}
        for key in ["src1", "src2", "src3"]:
            if key in associate_by:
                role_def = associate_by[key]
                if isinstance(role_def, dict):
                    role_defs[key] = role_def
        return role_defs

    def _classify_by_roles(
        self, flat_groups: List[Dict], role_defs: Dict
    ) -> Dict[str, List[Dict]]:
        """将配置组按角色分类"""
        role_candidates = {role: [] for role in role_defs}

        for fg in flat_groups:
            for role, role_def in role_defs.items():
                where = role_def.get("where", {})
                if self._match_conditions(fg["fields"], where):
                    role_candidates[role].append(fg)

        return role_candidates

    def _find_matched_tuples(
        self,
        role_defs: Dict,
        role_candidates: Dict[str, List[Dict]],
        links: List[Dict],
    ) -> List[Dict[str, Dict]]:
        """查找满足所有 links 条件的角色组合"""
        roles = sorted(role_defs.keys())

        if len(roles) == 2:
            return self._match_two_roles(roles, role_candidates, links)
        elif len(roles) == 3:
            return self._match_three_roles(roles, role_candidates, links)

        return []

    def _match_two_roles(
        self,
        roles: List[str],
        role_candidates: Dict[str, List[Dict]],
        links: List[Dict],
    ) -> List[Dict[str, Dict]]:
        """匹配两个角色的组合"""
        matched = []
        r1, r2 = roles[0], roles[1]

        for c1 in role_candidates[r1]:
            for c2 in role_candidates[r2]:
                if c1["idx"] == c2["idx"]:
                    continue

                assignment = {r1: c1, r2: c2}
                if self._check_links(assignment, links):
                    matched.append(assignment)

        return matched

    def _match_three_roles(
        self,
        roles: List[str],
        role_candidates: Dict[str, List[Dict]],
        links: List[Dict],
    ) -> List[Dict[str, Dict]]:
        """匹配三个角色的组合"""
        matched = []
        r1, r2, r3 = roles[0], roles[1], roles[2]

        for c1 in role_candidates[r1]:
            for c2 in role_candidates[r2]:
                if c1["idx"] == c2["idx"]:
                    continue
                for c3 in role_candidates[r3]:
                    if c3["idx"] in (c1["idx"], c2["idx"]):
                        continue

                    assignment = {r1: c1, r2: c2, r3: c3}
                    if self._check_links(assignment, links):
                        matched.append(assignment)

        return matched

    def _check_links(
        self, assignment: Dict[str, Dict], links: List[Dict]
    ) -> bool:
        """检查角色分配是否满足所有 links 条件

        每条 link 格式: {"src1": "opSch.outPort", "src2": "opSch.inPort"}
        或多字段: {"src1": ["opSch.chId", "opSch.bankId"], "src2": [...]}
        """
        for link in links:
            link_roles = [k for k in link if k in assignment]
            if len(link_roles) != 2:
                continue

            role_a, role_b = link_roles[0], link_roles[1]
            fields_a = link[role_a]
            fields_b = link[role_b]

            # 统一为列表
            if isinstance(fields_a, str):
                fields_a = [fields_a]
            if isinstance(fields_b, str):
                fields_b = [fields_b]

            if len(fields_a) != len(fields_b):
                return False

            group_a = assignment[role_a]
            group_b = assignment[role_b]

            for fa, fb in zip(fields_a, fields_b):
                val_a = str(group_a["fields"].get(fa, ""))
                val_b = str(group_b["fields"].get(fb, ""))
                if val_a != val_b or val_a == "":
                    return False

        return True

    # ==================== 通用工具方法 ====================

    def _match_conditions(self, fields: Dict, conditions: Dict) -> bool:
        """检查字段是否匹配条件

        支持：
        - 精确匹配: {"field": "value"}
        - 通配符: {"field": "*"} 表示字段只要存在即可
        """
        for field, expected_value in conditions.items():
            actual_value = fields.get(field)
            if expected_value == "*":
                if actual_value is None:
                    return False
            else:
                actual_str = str(actual_value) if actual_value is not None else ""
                if actual_str != str(expected_value):
                    return False
        return True

    def _flatten_group_fields(self, group: Dict) -> Dict:
        """将 group 的所有字段扁平化为一个字典（所有字段都带前缀）

        Args:
            group: 包含 top 和 subs 的组字典

        Returns:
            扁平化的字段字典：
                {
                    "opSch.powerLevel": "5",    # top 字段
                    "I2C.0.speed": "100K",      # 重复 section 添加索引
                    "I2C.1.speed": "400K",
                    "SPI.mode": "master"        # 单个 section 不添加索引
                }
        """
        flat_fields = {}

        # 添加 top 字段（带前缀）
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

        # 添加 sub 字段（重复名称添加索引）
        section_indices = {}
        for sub_section in subs:
            section_name = sub_section.get("name", "")
            sub_fields = sub_section.get("fields", {})

            if section_name_counts.get(section_name, 0) > 1:
                idx = section_indices.get(section_name, 0)
                section_indices[section_name] = idx + 1
                section_prefix = f"{section_name}.{idx}"
            else:
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
        """
        if "top_keyword" in self.config:
            return self.config["top_keyword"]

        if context:
            excel_writer_config = context.get("excel_writer_config")
            if excel_writer_config:
                top_table = excel_writer_config.get("top_table", {})
                log_keyword = top_table.get("log_keyword")
                if log_keyword:
                    return log_keyword

        return "opSch"

    def _generate_report(self, result: dict, _context: dict) -> str:
        """生成极简 JSON 报告"""
        try:
            report_path = self.config.get("report_path")
            if not report_path:
                output_dir = "output"
                os.makedirs(output_dir, exist_ok=True)
                report_path = os.path.join(output_dir, "constraint_report.json")

            report = {
                "timestamp": datetime.now().isoformat(),
                "passed": result["validation_passed"],
                "version": result["version"],
                "violations": len(result["violations"]),
            }

            if result["violations"]:
                by_type = {}
                for v in result["violations"]:
                    vtype = v.get("type", "unknown")
                    by_type[vtype] = by_type.get(vtype, 0) + 1

                report["summary"] = by_type

                report["errors"] = [
                    {
                        "type": v.get("type"),
                        "rule": v.get("rule"),
                        "field": v.get("field"),
                        "value": v.get("value"),
                        "message": v.get("message"),
                    }
                    for v in result["violations"]
                ]

            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            info(f"[约束检查] 报告已保存: {report_path}")
            return report_path

        except Exception as e:
            error(f"[约束检查] 生成报告失败: {e}")
            return None
