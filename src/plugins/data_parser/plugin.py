"""
16进制数据解析器插件
"""

import os
import re
import json
from typing import List, Dict, Optional, Any
from src.plugins.base import Plugin
from src.utils import info, warning, error


class DataParserPlugin(Plugin):
    """16进制数据解析器 - Level 1 (Extractor)"""

    level = 1
    dependencies = []

    def execute(self, context: dict) -> dict:
        """
        解析16进制数据

        Args:
            context: 上下文字典，可包含：
                - trace_file: 日志文件路径（如果从日志提取）
                - hex_data: 直接提供的16进制字符串

        Returns:
            {
                'parsed_data': [解析后的数据列表],
                'data_blocks': [数据块列表（支持多个二进制）],
                'binary_files': [导出的二进制文件路径],
                'manifest_path': 'manifest清单路径',
                'report_path': '报告路径'
            }
        """
        info("[数据解析] 开始解析16进制数据")

        # 检查是否为块模式（多个二进制）
        block_mode = self.config["source"].get("block_mode", False)

        if block_mode:
            return self._execute_block_mode(context)
        else:
            return self._execute_simple_mode(context)

    def _execute_simple_mode(self, context: dict) -> dict:
        """简单模式：单一数据流"""
        # 获取数据源
        hex_data_list = self._get_hex_data(context)

        if not hex_data_list:
            warning("[数据解析] 未找到16进制数据")
            return {"parsed_data": [], "raw_data": []}

        info(f"[数据解析] 找到 {len(hex_data_list)} 条数据")

        # 解析每条数据
        parsed_results = []
        for idx, hex_str in enumerate(hex_data_list):
            try:
                parsed = self._parse_hex_string(hex_str, idx)
                if parsed:
                    parsed_results.append(parsed)
            except Exception as e:
                error(f"[数据解析] 解析第{idx+1}条数据失败: {e}")

        # 生成报告
        report_path = self._generate_report(parsed_results, hex_data_list)

        info(f"[数据解析] 解析完成，成功 {len(parsed_results)}/{len(hex_data_list)} 条")

        return {
            "parsed_data": parsed_results,
            "raw_data": hex_data_list,
            "report_path": report_path,
        }

    def _execute_block_mode(self, context: dict) -> dict:
        """块模式：支持多个数据块和二进制导出"""
        trace_file = context.get("trace_file")
        if not trace_file or not os.path.exists(trace_file):
            warning(f"[数据解析] 日志文件不存在: {trace_file}")
            return {
                "data_blocks": [],
                "binary_files": [],
                "manifest_path": None,
            }

        # 生成启动时间戳
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        context["_timestamp"] = timestamp  # 保存到上下文

        # 从日志中提取数据块
        data_blocks = self._extract_data_blocks(trace_file)

        if not data_blocks:
            warning("[数据解析] 未找到数据块")
            return {
                "data_blocks": [],
                "binary_files": [],
                "manifest_path": None,
            }

        info(f"[数据解析] 找到 {len(data_blocks)} 个数据块")

        # 导出二进制文件
        binary_files = []
        if self.config["output"].get("export_binary", True):
            binary_files = self._export_binaries(data_blocks, timestamp)

        # 生成manifest
        manifest_path = None
        if self.config["output"].get("generate_manifest", True):
            manifest_path = self._generate_manifest(data_blocks, binary_files, timestamp)

        info(f"[数据解析] 处理完成，生成 {len(binary_files)} 个二进制文件")

        return {
            "data_blocks": data_blocks,
            "binary_files": binary_files,
            "manifest_path": manifest_path,
            "timestamp": timestamp,
        }

    def _get_hex_data(self, context: dict) -> List[str]:
        """获取16进制数据（从日志或直接输入）"""
        source_type = self.config["source"]["type"]

        if source_type == "direct":
            # 直接从context获取
            hex_data = context.get("hex_data")
            if isinstance(hex_data, str):
                return [hex_data]
            elif isinstance(hex_data, list):
                return hex_data
            else:
                return []

        elif source_type == "log_file":
            # 从日志文件提取
            trace_file = context.get("trace_file")
            if not trace_file or not os.path.exists(trace_file):
                warning(f"[数据解析] 日志文件不存在: {trace_file}")
                return []

            return self._extract_from_log(trace_file)

        return []

    def _extract_from_log(self, log_file: str) -> List[str]:
        """从日志文件中提取16进制数据"""
        pattern = self.config["source"]["pattern"]
        hex_data_list = []

        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    match = re.search(pattern, line)
                    if match:
                        hex_str = match.group(1).strip()
                        hex_data_list.append(hex_str)

            info(f"[数据解析] 从日志中提取到 {len(hex_data_list)} 条数据")
            return hex_data_list

        except Exception as e:
            error(f"[数据解析] 读取日志失败: {e}")
            return []

    def _parse_hex_string(self, hex_str: str, index: int) -> Optional[Dict]:
        """解析单条16进制字符串"""
        # 清理并转换为字节数组
        byte_array = self._hex_to_bytes(hex_str)

        if not byte_array:
            warning(f"[数据解析] 第{index+1}条数据格式错误: {hex_str}")
            return None

        # 验证（可选）
        if not self._validate(byte_array):
            warning(f"[数据解析] 第{index+1}条数据验证失败")
            return None

        # 解析字段
        parsed = {
            "index": index,
            "raw_hex": hex_str,
            "raw_bytes": len(byte_array),
        }

        fields_config = self.config.get("fields", [])
        for field_def in fields_config:
            field_value = self._parse_field(byte_array, field_def, parsed)
            if field_value is not None:
                parsed[field_def["name"]] = field_value

        # 应用值映射
        self._apply_value_mapping(parsed)

        return parsed

    def _hex_to_bytes(self, hex_str: str) -> Optional[List[int]]:
        """将16进制字符串转换为字节数组"""
        format_type = self.config["source"]["format"]

        try:
            # 清理字符串
            hex_str = hex_str.strip()

            if format_type == "spaced":
                # "1A 02 FF" 格式
                hex_parts = hex_str.split()
                byte_array = [int(h, 16) for h in hex_parts]
            else:
                # "1A02FF" 格式
                hex_str = hex_str.replace(" ", "").replace("\n", "")
                byte_array = [int(hex_str[i : i + 2], 16) for i in range(0, len(hex_str), 2)]

            return byte_array

        except ValueError:
            return None

    def _parse_field(
        self, byte_array: List[int], field_def: Dict, parsed_data: Dict
    ) -> Any:
        """解析单个字段"""
        # 计算偏移和长度
        offset = self._calculate_offset(field_def["offset"], byte_array)
        length = self._calculate_length(field_def["length"], byte_array, parsed_data)

        if offset is None or length is None:
            return None

        # 检查边界
        if offset + length > len(byte_array):
            warning(
                f"[数据解析] 字段 {field_def['name']} 超出数据范围 "
                f"(offset={offset}, length={length}, total={len(byte_array)})"
            )
            return None

        # 提取字节
        field_bytes = byte_array[offset : offset + length]

        # 根据类型解析
        field_type = field_def["type"]
        endian = field_def.get("endian", "big")

        if field_type == "uint8":
            return field_bytes[0] if field_bytes else None

        elif field_type == "uint16":
            if len(field_bytes) < 2:
                return None
            if endian == "big":
                return (field_bytes[0] << 8) | field_bytes[1]
            else:
                return (field_bytes[1] << 8) | field_bytes[0]

        elif field_type == "uint32":
            if len(field_bytes) < 4:
                return None
            if endian == "big":
                return (
                    (field_bytes[0] << 24)
                    | (field_bytes[1] << 16)
                    | (field_bytes[2] << 8)
                    | field_bytes[3]
                )
            else:
                return (
                    (field_bytes[3] << 24)
                    | (field_bytes[2] << 16)
                    | (field_bytes[1] << 8)
                    | field_bytes[0]
                )

        elif field_type == "hex":
            return " ".join(f"{b:02X}" for b in field_bytes)

        elif field_type == "string":
            try:
                # 尝试ASCII解码
                return bytes(field_bytes).decode("ascii").rstrip("\x00")
            except UnicodeDecodeError:
                return " ".join(f"{b:02X}" for b in field_bytes)

        return None

    def _calculate_offset(self, offset_def: Any, byte_array: List[int]) -> Optional[int]:
        """计算字段偏移"""
        if isinstance(offset_def, int):
            return offset_def
        elif isinstance(offset_def, str):
            # 支持 "end-1" 这样的表达式
            if offset_def.startswith("end"):
                parts = offset_def.split("-")
                if len(parts) == 2:
                    return len(byte_array) - int(parts[1])
                return len(byte_array)
        return None

    def _calculate_length(
        self, length_def: Any, byte_array: List[int], parsed_data: Dict
    ) -> Optional[int]:
        """计算字段长度"""
        if isinstance(length_def, int):
            return length_def
        elif length_def == "dynamic":
            # 动态长度，需要从其他字段获取
            # 这里简化处理，实际需要更复杂的逻辑
            return len(byte_array) - parsed_data.get("offset", 0) - 1  # 减去checksum
        return None

    def _validate(self, byte_array: List[int]) -> bool:
        """验证数据（可选）"""
        validation_config = self.config.get("validation", {})

        # 验证header
        if validation_config.get("verify_header", False):
            expected = validation_config.get("expected_header", 0)
            if byte_array[0] != expected:
                return False

        # 验证checksum
        if validation_config.get("verify_checksum", False):
            # 简化：这里可以实现各种校验算法
            pass

        return True

    def _apply_value_mapping(self, parsed: Dict):
        """应用值映射"""
        value_mapping = self.config.get("value_mapping", {})

        for field_name, mapping in value_mapping.items():
            if field_name in parsed:
                value = parsed[field_name]
                if value in mapping:
                    parsed[f"{field_name}_name"] = mapping[value]

    def _generate_report(
        self, parsed_results: List[Dict], raw_data: List[str]
    ) -> Optional[str]:
        """生成JSON报告"""
        output_config = self.config.get("output", {})

        if output_config.get("format") != "json":
            return None

        try:
            json_path = output_config.get("json_path", "output/data_parsed.json")
            os.makedirs(os.path.dirname(json_path), exist_ok=True)

            report = {
                "total_count": len(raw_data),
                "parsed_count": len(parsed_results),
                "success_rate": len(parsed_results) / len(raw_data) if raw_data else 0,
                "data": parsed_results,
            }

            if output_config.get("include_raw", True):
                report["raw_data"] = raw_data

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            info(f"[数据解析] 报告已保存: {json_path}")
            return json_path

        except Exception as e:
            error(f"[数据解析] 生成报告失败: {e}")
            return None

    def _extract_data_blocks(self, log_file: str) -> List[Dict]:
        """从日志中提取多个数据块"""
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                raw_blocks = self._parse_log_lines(f)

            processed_blocks = self._finalize_blocks(raw_blocks)
            info(f"[数据解析] 从日志中提取到 {len(processed_blocks)} 个数据块")
            return processed_blocks

        except Exception as e:
            error(f"[数据解析] 提取数据块失败: {e}")
            return []

    def _parse_log_lines(self, file_handle) -> List[Dict]:
        """解析日志文件的每一行，提取数据块"""
        markers = self.config["source"]["block_markers"]
        pattern = self.config["source"]["pattern"]

        data_blocks = []
        current_block = None

        for line_num, line in enumerate(file_handle, 1):
            line = line.strip()

            # 尝试处理各种标记行
            if self._is_type_marker(line, markers["type_marker"]):
                current_block = self._finalize_and_start_new_block(
                    current_block, data_blocks, line, markers["type_marker"], line_num
                )
            elif current_block:
                self._process_marker_line(current_block, line, markers)

            # 检查16进制数据行
            if current_block and re.match(pattern, line):
                current_block["hex_lines"].append(line)

        # 保存最后一个块
        if current_block and current_block.get("hex_lines"):
            data_blocks.append(current_block)

        return data_blocks

    def _is_type_marker(self, line: str, type_marker: str) -> bool:
        """检查是否为类型标记行"""
        return type_marker in line

    def _finalize_and_start_new_block(
        self, current_block: Optional[Dict], data_blocks: List[Dict],
        line: str, type_marker: str, line_num: int
    ) -> Dict:
        """完成当前块并开始新块"""
        # 保存上一个块
        if current_block and current_block.get("hex_lines"):
            data_blocks.append(current_block)

        # 开始新块
        type_value = line.split(type_marker)[-1].strip()
        return {
            "type": type_value,
            "address": None,
            "size": None,
            "name": None,
            "hex_lines": [],
            "start_line": line_num,
        }

    def _process_marker_line(self, block: Dict, line: str, markers: Dict) -> None:
        """处理标记行（地址、大小、名称）"""
        if markers["address_marker"] in line:
            self._parse_address_marker(block, line, markers["address_marker"])
        elif markers.get("size_marker") and markers["size_marker"] in line:
            self._parse_size_marker(block, line, markers["size_marker"])
        elif markers.get("name_marker") and markers["name_marker"] in line:
            self._parse_name_marker(block, line, markers["name_marker"])

    def _parse_address_marker(self, block: Dict, line: str, marker: str) -> None:
        """解析地址标记"""
        addr_str = line.split(marker)[-1].strip()
        if addr_str.startswith(("0x", "0X")):
            block["address"] = int(addr_str, 16)
        elif addr_str.replace(" ", ""):
            block["address"] = int(addr_str, 16)

    def _parse_size_marker(self, block: Dict, line: str, marker: str) -> None:
        """解析大小标记"""
        size_str = line.split(marker)[-1].strip()
        if size_str.isdigit():
            block["size"] = int(size_str)

    def _parse_name_marker(self, block: Dict, line: str, marker: str) -> None:
        """解析名称标记"""
        block["name"] = line.split(marker)[-1].strip()

    def _finalize_blocks(self, raw_blocks: List[Dict]) -> List[Dict]:
        """完成块处理：合并16进制行并转换为字节"""
        for block in raw_blocks:
            hex_str = " ".join(block["hex_lines"])
            block["hex_string"] = hex_str
            block["bytes"] = self._hex_to_bytes(hex_str)
            block["byte_count"] = len(block["bytes"]) if block["bytes"] else 0
            block["end_line"] = block["start_line"] + len(block["hex_lines"]) + 3

        return raw_blocks

    def _export_binaries(self, data_blocks: List[Dict], timestamp: str = None) -> List[str]:
        """导出二进制文件"""
        output_config = self.config["output"]
        output_dir = output_config.get("binary_output_dir", "output/binaries")
        name_template = output_config.get("binary_name_template", "{type}_{address}.bin")

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        binary_files = []

        for idx, block in enumerate(data_blocks):
            if not block.get("bytes"):
                warning(f"[数据解析] 数据块 {idx} 无有效数据，跳过")
                continue

            # 生成文件名
            file_name = name_template.format(
                type=block.get("type", "unknown"),
                address=f"{block.get('address', 0):08X}" if block.get("address") is not None else "noaddr",
                name=block.get("name", "unnamed"),
                index=idx,
                timestamp=timestamp or "notimestamp",
            )

            # 清理文件名中的非法字符
            file_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in file_name)

            file_path = os.path.join(output_dir, file_name)

            try:
                # 写入二进制文件
                with open(file_path, "wb") as f:
                    f.write(bytes(block["bytes"]))

                binary_files.append(file_path)
                block["binary_file"] = file_path
                info(f"[数据解析] 导出二进制: {file_name} ({block['byte_count']} 字节)")

            except Exception as e:
                error(f"[数据解析] 导出二进制失败 ({file_name}): {e}")

        return binary_files

    def _generate_manifest(
        self, data_blocks: List[Dict], binary_files: List[str], timestamp: str = None
    ) -> Optional[str]:
        """生成manifest清单"""
        manifest_path = self.config["output"].get("manifest_path", "output/manifest.json")

        try:
            os.makedirs(os.path.dirname(manifest_path), exist_ok=True)

            # 构建manifest
            manifest = {
                "version": "1.0",
                "generated_at": __import__("datetime").datetime.now().isoformat(),
                "timestamp": timestamp,
                "total_blocks": len(data_blocks),
                "total_bytes": sum(b.get("byte_count", 0) for b in data_blocks),
                "blocks": [],
            }

            for idx, block in enumerate(data_blocks):
                block_info = {
                    "index": idx,
                    "type": block.get("type"),
                    "address": f"0x{block.get('address', 0):08X}" if block.get("address") is not None else None,
                    "size": block.get("byte_count"),
                    "name": block.get("name"),
                    "binary_file": os.path.basename(block.get("binary_file", "")),
                    "start_line": block.get("start_line"),
                    "end_line": block.get("end_line"),
                }
                manifest["blocks"].append(block_info)

            # 写入manifest文件
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)

            info(f"[数据解析] Manifest已保存: {manifest_path}")
            return manifest_path

        except Exception as e:
            error(f"[数据解析] 生成Manifest失败: {e}")
            return None
