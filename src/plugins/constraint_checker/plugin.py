"""
配置约束检查插件 - 验证配置是否满足约束条件
"""

import ast
import json
import os
from datetime import datetime
from itertools import product
from typing import Dict, List

import yaml

from src.plugins.base import Plugin
from src.utils import debug, error, info, warning


class ConstraintCheckerPlugin(Plugin):
    """配置约束检查插件 - Level 2 (Validator)"""

    level = 2  # 验证层，在 config_parser 之后执行
    dependencies = ["config_parser"]  # 依赖配置解析插件

    # ==================== 约束类型注册表 ====================
    # 新增约束类型只需：1) 添加方法 _check_xxx  2) 注册到此表
    _CHECKER_MAP = {
        "same_value": "_check_same_value",
        "sequence": "_check_sequence",
        "conditional": "_check_conditional",
        "combinations": "_check_combinations",
        "validate": "_check_validate_expr",
    }

    def execute(self, context: dict) -> dict:
        """检查配置约束"""
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
        violations.extend(
            self._check_single_constraints(sections, rules, parser, context)
        )
        violations.extend(
            self._check_multi_constraints(sections, rules, parser, context)
        )
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
        """
        # 1. 优先检查配置中的 constraint_rules（用于测试）
        constraint_rules = self.config.get("constraint_rules", {})
        if constraint_rules:
            active_version = self.config.get("active_version")
            if active_version and active_version in constraint_rules:
                return active_version, constraint_rules[active_version]
            versions = sorted(constraint_rules.keys())
            if versions:
                return versions[-1], constraint_rules[versions[-1]]

        # 2. 从 rules/ 目录加载规则文件（生产环境）
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        rules_dir = self.config.get("rules_dir", "rules")
        rules_path = os.path.join(plugin_dir, rules_dir)

        if not os.path.exists(rules_path):
            warning(f"[约束检查] 规则目录不存在: {rules_path}")
            return "none", {"single_constraints": [], "multi_constraints": []}

        import re

        rule_files = [
            f
            for f in os.listdir(rules_path)
            if re.match(r"v\d+\.\d+\.\d+_\d+\.yaml$", f)
        ]

        if not rule_files:
            warning(f"[约束检查] 规则目录中没有规则文件: {rules_path}")
            return "none", {"single_constraints": [], "multi_constraints": []}

        available_versions = [f[1:-5] for f in rule_files]
        active_version = self.config.get("active_version")

        if active_version:
            if active_version not in available_versions:
                warning(f"[约束检查] 指定的规则版本不存在: {active_version}")
                return "none", {"single_constraints": [], "multi_constraints": []}
            target_version = active_version
        else:
            target_version = sorted(available_versions)[-1]

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
        top_keyword = self._get_top_keyword(context)
        groups = parser.group_by_top_config(top_keyword) if parser else []

        for group_idx, group in enumerate(groups):
            flat_fields = self._flatten_group_fields(group)
            for rule in single_constraints:
                violations.extend(
                    self._check_single_rule(flat_fields, rule, group_idx)
                )

        return violations

    def _check_single_rule(
        self, flat_fields: Dict, rule: Dict, group_idx: int
    ) -> List[Dict]:
        """检查单个单组约束规则"""
        violations = []
        when_conditions = rule.get("when", {})
        if not self._match_conditions(flat_fields, when_conditions):
            return violations

        rule_name = rule.get("name", "未命名规则")

        for field, allowed_values in rule.get("only_allow", {}).items():
            if field in flat_fields:
                value = str(flat_fields[field])
                if value not in allowed_values:
                    violations.append(
                        self._make_violation(
                            "only_allow", rule_name, f"组{group_idx}",
                            f"字段 '{field}' 的值 '{value}' "
                            f"不在允许列表 {allowed_values} 中",
                            group=group_idx, field=field,
                            value=value, allowed=allowed_values,
                        )
                    )

        for field, forbidden_values in rule.get("forbid", {}).items():
            if field in flat_fields:
                value = str(flat_fields[field])
                if value in forbidden_values:
                    violations.append(
                        self._make_violation(
                            "forbid", rule_name, f"组{group_idx}",
                            f"字段 '{field}' 的值 '{value}' "
                            f"在禁止列表 {forbidden_values} 中",
                            group=group_idx, field=field,
                            value=value, forbidden=forbidden_values,
                        )
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
                violations.extend(self._check_associated_rule(groups, rule))
            else:
                violations.extend(self._check_sliding_window_rule(groups, rule))

        return violations

    def _check_sliding_window_rule(
        self, groups: List[Dict], rule: Dict
    ) -> List[Dict]:
        """滑动窗口约束：转换为统一角色分配后检查"""
        violations = []
        group_count = rule.get("group_count", 2)

        for start_idx in range(len(groups) - group_count + 1):
            window = groups[start_idx : start_idx + group_count]
            role_assignment = {
                f"group{i}": {
                    "idx": start_idx + i,
                    "fields": self._flatten_group_fields(g),
                }
                for i, g in enumerate(window)
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

        role_defs = self._parse_role_definitions(associate_by)
        if not role_defs:
            warning(f"[约束检查] {rule_name}: associate_by 中未定义有效角色")
            return violations

        flat_groups = [
            {"idx": idx, "fields": self._flatten_group_fields(group)}
            for idx, group in enumerate(groups)
        ]

        role_candidates = self._classify_by_roles(flat_groups, role_defs)

        for role_key in role_defs:
            if not role_candidates.get(role_key):
                debug(
                    f"[约束检查] {rule_name}: 角色 '{role_key}' "
                    f"没有匹配的配置组，跳过"
                )
                return violations

        links = associate_by.get("links", [])
        matched_tuples = self._match_roles(role_defs, role_candidates, links)

        if not matched_tuples:
            debug(f"[约束检查] {rule_name}: 没有找到满足关联条件的组合")
            return violations

        for role_assignment in matched_tuples:
            violations.extend(
                self._check_constraints_on_assignment(rule, role_assignment)
            )

        return violations

    # ==================== 统一约束检查（注册表分发） ====================

    def _check_constraints_on_assignment(
        self, rule: Dict, role_assignment: Dict[str, Dict]
    ) -> List[Dict]:
        """统一约束检查入口：通过注册表分发，一个循环处理所有类型"""
        violations = []
        rule_name = rule.get("name", "未命名规则")
        roles = sorted(role_assignment.keys())
        role_label = self._build_role_label(role_assignment, roles)

        for constraint in rule.get("rules", []):
            constraint_type = constraint.get("type")
            method_name = self._CHECKER_MAP.get(constraint_type)
            if not method_name:
                debug(f"[约束检查] 未知约束类型: {constraint_type}")
                continue
            checker = getattr(self, method_name)
            violation = checker(
                role_assignment, constraint, rule_name, role_label, roles
            )
            if violation:
                violations.append(violation)

        return violations

    # ==================== Violation 工厂 ====================

    def _make_violation(
        self, vtype: str, rule_name: str, role_label: str,
        message: str, **extra
    ) -> Dict:
        """统一构造 violation 字典

        修改消息格式只需改这一处。
        """
        return {
            "type": vtype,
            "rule": rule_name,
            "message": f"[{role_label}] {rule_name}: {message}",
            **extra,
        }

    def _build_role_label(
        self, role_assignment: Dict, roles: List[str]
    ) -> str:
        """构建角色标签用于错误消息"""
        if all(r.startswith("group") for r in roles):
            indices = [role_assignment[r]["idx"] for r in roles]
            return f"组{indices}"
        else:
            return ", ".join(
                f"{role}=组{role_assignment[role]['idx']}" for role in roles
            )

    def _resolve_role_key(self, role_ref, role_assignment: Dict) -> str | None:
        """将约束中的角色引用解析为 role_assignment 中的 key

        支持整数索引 (0→"group0") 和字符串 ("src1"→"src1")。
        """
        if role_ref in role_assignment:
            return role_ref
        if isinstance(role_ref, int):
            key = f"group{role_ref}"
            if key in role_assignment:
                return key
        return None

    # ==================== 约束检查方法（统一签名） ====================
    # 签名: (self, role_assignment, constraint, rule_name, role_label, roles)
    # 新增类型只需：添加方法 + 注册到 _CHECKER_MAP

    def _check_same_value(
        self, role_assignment, constraint, rule_name, role_label, roles,
    ):
        """检查字段在所有角色对应的组中值相同"""
        field = constraint.get("field")
        if not field:
            return None

        check_roles = constraint.get("groups", roles)
        resolved = [r for r in
                     (self._resolve_role_key(r, role_assignment) for r in check_roles)
                     if r is not None]

        values = []
        for role in resolved:
            group = role_assignment.get(role)
            if group:
                val = group["fields"].get(field)
                values.append(str(val) if val is not None else None)

        if len(set(values)) > 1:
            return self._make_violation(
                "same_value", rule_name, role_label,
                f"字段 '{field}' 在各组中的值不一致: {values}",
                field=field, values=values,
            )
        return None

    def _check_sequence(
        self, role_assignment, constraint, rule_name, role_label, roles,
    ):
        """检查字段值序列（递增/递减）"""
        field = constraint.get("field")
        order = constraint.get("order", "increasing")
        if not field:
            return None

        check_roles = constraint.get("groups", roles)
        resolved = [r for r in
                     (self._resolve_role_key(r, role_assignment) for r in check_roles)
                     if r is not None]

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
            return self._make_violation(
                "sequence", rule_name, role_label,
                f"字段 '{field}' 存在空值，无法检查序列",
                field=field,
            )

        if order == "increasing":
            is_valid = all(values[i] < values[i + 1] for i in range(len(values) - 1))
        elif order == "decreasing":
            is_valid = all(values[i] > values[i + 1] for i in range(len(values) - 1))
        else:
            is_valid = True

        if not is_valid:
            order_desc = "递增" if order == "increasing" else "递减"
            return self._make_violation(
                "sequence", rule_name, role_label,
                f"字段 '{field}' 的值 {values} 不满足{order_desc}序列",
                field=field, order=order, values=values,
            )
        return None

    def _check_conditional(
        self, role_assignment, constraint, rule_name, role_label, roles,
    ):
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
            return None

        actual_then_value = str(then_group["fields"].get(then_field, ""))

        only_allow = constraint.get("only_allow", [])
        if only_allow and actual_then_value not in only_allow:
            return self._make_violation(
                "conditional", rule_name, role_label,
                f"当 {when_ref}(组{when_group['idx']}) 的 "
                f"{when_field}={when_value} 时，"
                f"{then_ref}(组{then_group['idx']}) 的 {then_field} "
                f"应在 {only_allow} 中，实际值为 '{actual_then_value}'",
            )

        forbid = constraint.get("forbid", [])
        if forbid and actual_then_value in forbid:
            return self._make_violation(
                "conditional", rule_name, role_label,
                f"当 {when_ref}(组{when_group['idx']}) 的 "
                f"{when_field}={when_value} 时，"
                f"{then_ref}(组{then_group['idx']}) 的 {then_field} "
                f"不应为 '{actual_then_value}'（禁止值: {forbid}）",
            )
        return None

    def _check_combinations(
        self, role_assignment, constraint, rule_name, role_label, roles,
    ):
        """检查字段组合白名单"""
        combinations = constraint.get("allow", [])
        if not combinations:
            return None

        actual_values = {}
        for role in roles:
            group = role_assignment.get(role)
            if group:
                actual_values[role] = group["fields"]

        for combo in combinations:
            if self._match_combination(actual_values, combo, roles):
                return None

        actual_summary_parts = []
        for role in roles:
            if role in actual_values and role in combinations[0]:
                combo_fields = combinations[0][role]
                role_vals = {
                    f: actual_values[role].get(f, "?")
                    for f in (combo_fields if isinstance(combo_fields, dict) else {})
                }
                actual_summary_parts.append(f"{role}={role_vals}")

        return self._make_violation(
            "combinations", rule_name, role_label,
            f"字段组合 ({', '.join(actual_summary_parts)}) "
            f"不在允许的 {len(combinations)} 个组合中",
        )

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
                if str(actual.get(field, "")) != str(expected_val):
                    return False
        return True

    def _check_validate_expr(
        self, role_assignment, constraint, rule_name, role_label, roles,
    ):
        """使用 CEL 或安全表达式检查约束"""
        expr = constraint.get("expr", "")
        custom_message = constraint.get("message", "表达式验证失败")
        if not expr:
            return None

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
                try:
                    field_val = int(field_val)
                except (ValueError, TypeError):
                    try:
                        field_val = float(field_val)
                    except (ValueError, TypeError):
                        pass
                current[parts[-1]] = field_val
            eval_context[role] = role_fields

        result = self._evaluate_cel(expr, eval_context)
        if result is None:
            result = self._evaluate_safe_expr(expr, eval_context)

        if result is False:
            return self._make_violation(
                "validate", rule_name, role_label, custom_message,
                expr=expr,
                roles={r: role_assignment[r]["idx"] for r in role_assignment},
            )
        return None

    # ==================== 表达式求值 ====================

    def _evaluate_cel(self, expr: str, context: Dict) -> bool | None:
        """使用 CEL 引擎求值（可选依赖）"""
        try:
            import celpy

            env = celpy.Environment()
            cel_ast = env.compile(expr)
            prgm = env.program(cel_ast)

            cel_context = {}
            for key, value in context.items():
                cel_context[key] = celpy.json_to_cel(value)

            return bool(prgm.evaluate(cel_context))
        except ImportError:
            return None
        except Exception as e:
            debug(f"[约束检查] CEL 表达式求值失败: {expr}, 错误: {e}")
            return None

    def _evaluate_safe_expr(self, expr: str, context: Dict) -> bool | None:
        """基于 AST 的安全表达式求值（白名单模式）"""
        try:
            tree = ast.parse(expr, mode="eval")
            return bool(self._eval_node(tree.body, context))
        except Exception as e:
            debug(f"[约束检查] 安全表达式求值失败: {expr}, 错误: {e}")
            return None

    def _eval_node(self, node, context: Dict):
        """递归求值 AST 节点"""
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

    def _match_roles(
        self,
        role_defs: Dict,
        role_candidates: Dict[str, List[Dict]],
        links: List[Dict],
    ) -> List[Dict[str, Dict]]:
        """通用 N 角色匹配

        使用 itertools.product 笛卡尔积 + links 过滤，
        自动支持 2、3、...N 个角色，无需为每种数量写专用方法。
        """
        roles = sorted(role_defs.keys())
        matched = []

        for combo in product(*(role_candidates[r] for r in roles)):
            # 每个角色必须对应不同的配置组
            indices = [c["idx"] for c in combo]
            if len(set(indices)) != len(indices):
                continue

            assignment = dict(zip(roles, combo))
            if self._check_links(assignment, links):
                matched.append(assignment)

        return matched

    def _check_links(
        self, assignment: Dict[str, Dict], links: List[Dict]
    ) -> bool:
        """检查角色分配是否满足所有 links 条件"""
        for link in links:
            link_roles = [k for k in link if k in assignment]
            if len(link_roles) != 2:
                continue

            role_a, role_b = link_roles[0], link_roles[1]
            fields_a = link[role_a]
            fields_b = link[role_b]

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

        支持精确匹配和 "*" 通配符（字段存在即可）。
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
        """将 group 的所有字段扁平化为带前缀的字典"""
        flat_fields = {}

        top_section = group.get("top")
        if top_section:
            section_name = top_section.get("name", "")
            for field_name, field_value in top_section.get("fields", {}).items():
                flat_fields[f"{section_name}.{field_name}"] = field_value

        subs = group.get("subs", [])
        section_name_counts = {}
        for sub in subs:
            name = sub.get("name", "")
            section_name_counts[name] = section_name_counts.get(name, 0) + 1

        section_indices = {}
        for sub_section in subs:
            section_name = sub_section.get("name", "")

            if section_name_counts.get(section_name, 0) > 1:
                idx = section_indices.get(section_name, 0)
                section_indices[section_name] = idx + 1
                section_prefix = f"{section_name}.{idx}"
            else:
                section_prefix = section_name

            for field_name, field_value in sub_section.get("fields", {}).items():
                flat_fields[f"{section_prefix}.{field_name}"] = field_value

        return flat_fields

    def _get_top_keyword(self, context: dict = None) -> str:
        """获取 top 配置关键字"""
        if "top_keyword" in self.config:
            return self.config["top_keyword"]
        if context:
            excel_writer_config = context.get("excel_writer_config")
            if excel_writer_config:
                log_keyword = excel_writer_config.get("top_table", {}).get(
                    "log_keyword"
                )
                if log_keyword:
                    return log_keyword
        return "opSch"

    def _generate_report(self, result: dict, _context: dict) -> str:
        """生成 JSON 报告"""
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
