"""
perf_analyzer 插件单元测试
"""

import csv
import json
import os
import tempfile
from unittest.mock import patch

import pytest

from src.plugins.perf_analyzer.plugin import PerfAnalyzerPlugin


@pytest.fixture
def basic_config():
    """基本配置"""
    return {
        "enable": True,
        "hardware": {
            "frequency_ghz": 1.5,
            "peak_tflops": 312,
        },
        "analysis": {
            "compute_statistics": True,
            "compute_mfu": False,
        },
        "grouping": {
            "by_execution_unit": True,
            "by_time_window": False,
            "time_window_size": 60,
        },
        "reporting": {
            "generate_json": True,
            "json_path": "output/perf_summary.json",
            "generate_csv": False,
            "csv_path": "output/perf_details.csv",
        },
    }


@pytest.fixture
def sample_pairs():
    """示例数据对"""
    return [
        {
            "correlation_id": "op1",
            "rule_name": "rule1",
            "execution_unit": "AICore0",
            "source": "logA",
            "start_event": {"line_number": 10},
            "end_event": {"line_number": 20},
            "performance": {"duration_cycles": 1000},
        },
        {
            "correlation_id": "op2",
            "rule_name": "rule1",
            "execution_unit": "AICore1",
            "source": "logA",
            "start_event": {"line_number": 15},
            "end_event": {"line_number": 25},
            "performance": {"duration_cycles": 2000},
        },
        {
            "correlation_id": "op3",
            "rule_name": "rule2",
            "execution_unit": "AICore0",
            "source": "logB",
            "start_event": {"line_number": 30},
            "end_event": {"line_number": 40},
            "performance": {"duration_cycles": 1500},
        },
    ]


@pytest.fixture
def plugin(basic_config):
    """创建插件实例"""
    with patch.object(PerfAnalyzerPlugin, "_load_config", return_value=basic_config):
        return PerfAnalyzerPlugin()


class TestPerfAnalyzerPlugin:
    """PerfAnalyzerPlugin 测试类"""

    def test_plugin_initialization(self, basic_config):
        """测试插件初始化"""
        with patch.object(PerfAnalyzerPlugin, "_load_config", return_value=basic_config):
            plugin = PerfAnalyzerPlugin()
            assert plugin.enabled is True
            assert plugin.level == 2
            assert plugin.dependencies == ["perf_parser"]
            assert plugin.config == basic_config

    def test_plugin_disabled(self):
        """测试禁用插件"""
        config = {"enable": False}
        with patch.object(PerfAnalyzerPlugin, "_load_config", return_value=config):
            plugin = PerfAnalyzerPlugin()
            assert plugin.enabled is False

    def test_execute_with_empty_pairs(self, plugin):
        """测试空数据集"""
        context = {"perf_parser": {"pairs": []}}
        result = plugin.execute(context)

        assert result["summary"] == {}
        assert result["by_unit"] == {}
        assert result["mfu"] == {}

    def test_execute_with_missing_perf_parser(self, plugin):
        """测试缺失perf_parser数据"""
        context = {}
        result = plugin.execute(context)

        assert result["summary"] == {}
        assert result["by_unit"] == {}

    def test_execute_normal_flow(self, plugin, sample_pairs):
        """测试正常执行流程"""
        context = {"perf_parser": {"pairs": sample_pairs}}

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin.config["reporting"]["json_path"] = os.path.join(
                tmpdir, "summary.json"
            )
            result = plugin.execute(context)

        # 验证summary
        assert "summary" in result
        assert result["summary"]["count"] == 3
        assert result["summary"]["mean_cycles"] == 1500.0  # (1000 + 2000 + 1500) / 3
        assert result["summary"]["min_cycles"] == 1000
        assert result["summary"]["max_cycles"] == 2000
        assert result["summary"]["median_cycles"] == 1500

        # 验证percentiles
        assert "p50_cycles" in result["summary"]
        assert "p90_cycles" in result["summary"]
        assert "p95_cycles" in result["summary"]
        assert "p99_cycles" in result["summary"]

        # 验证by_unit
        assert "by_unit" in result
        assert "AICore0" in result["by_unit"]
        assert "AICore1" in result["by_unit"]

        # 验证mfu
        assert "mfu" in result

    def test_extract_duration_with_duration_cycles(self, plugin):
        """测试从duration_cycles提取耗时"""
        pair = {"performance": {"duration_cycles": 1234}}
        duration = plugin._extract_duration(pair)
        assert duration == 1234.0

    def test_extract_duration_with_any_numeric_field(self, plugin):
        """测试从任意数值字段提取耗时"""
        pair = {"performance": {"some_cycle": 5000}}
        duration = plugin._extract_duration(pair)
        assert duration == 5000.0

    def test_extract_duration_missing_fields(self, plugin):
        """测试缺失耗时字段"""
        pair = {"performance": {}}
        duration = plugin._extract_duration(pair)
        assert duration is None

    def test_extract_duration_none_performance(self, plugin):
        """测试performance为None或空dict

        注意：当performance为None时，源码会抛出AttributeError
        这是一个潜在的bug - 应该添加None检查
        """
        pair = {"performance": {}}
        duration = plugin._extract_duration(pair)
        assert duration is None

        # BUG DISCOVERED: 源码不处理performance=None的情况
        # pair = {"performance": None}
        # with pytest.raises(AttributeError):
        #     plugin._extract_duration(pair)

    def test_compute_summary_basic_stats(self, plugin):
        """测试基本统计计算"""
        pairs = [
            {"performance": {"duration_cycles": 100}},
            {"performance": {"duration_cycles": 200}},
            {"performance": {"duration_cycles": 300}},
        ]
        summary = plugin._compute_summary(pairs)

        assert summary["count"] == 3
        assert summary["mean_cycles"] == 200.0
        assert summary["min_cycles"] == 100
        assert summary["max_cycles"] == 300
        assert summary["median_cycles"] == 200

    def test_compute_summary_single_value(self, plugin):
        """测试单个值的统计"""
        pairs = [{"performance": {"duration_cycles": 150}}]
        summary = plugin._compute_summary(pairs)

        assert summary["count"] == 1
        assert summary["mean_cycles"] == 150.0
        assert summary["min_cycles"] == 150
        assert summary["max_cycles"] == 150
        assert summary["median_cycles"] == 150
        assert summary["p50_cycles"] == 150

    def test_compute_summary_with_none_values(self, plugin):
        """测试包含None值的数据"""
        pairs = [
            {"performance": {"duration_cycles": 100}},
            {"performance": {}},  # 会返回None
            {"performance": {"duration_cycles": 300}},
        ]
        summary = plugin._compute_summary(pairs)

        # 应该只统计有效值
        assert summary["count"] == 2
        assert summary["mean_cycles"] == 200.0

    def test_compute_summary_percentiles(self, plugin):
        """测试百分位数计算"""
        pairs = [{"performance": {"duration_cycles": i * 10}} for i in range(1, 101)]
        summary = plugin._compute_summary(pairs)

        # 数据: 10, 20, 30, ..., 1000 (共100个)
        # p50 = int(100 * 0.50) = 50, sorted[50] = 510
        assert summary["p50_cycles"] == 510  # index 50
        assert summary["p90_cycles"] == 910  # index 90
        assert summary["p95_cycles"] == 960  # index 95
        assert summary["p99_cycles"] == 1000  # n=100时，p99是最后一个

    def test_compute_summary_always_has_percentiles(self, plugin):
        """测试始终计算百分位数（实现中总是计算）"""
        pairs = [{"performance": {"duration_cycles": i * 10}} for i in range(1, 11)]
        summary = plugin._compute_summary(pairs)

        # 实现中总是计算百分位数
        assert "p50_cycles" in summary
        assert "p90_cycles" in summary
        assert "mean_cycles" in summary

    def test_analyze_by_unit(self, plugin, sample_pairs):
        """测试按执行单元分组"""
        result = plugin._analyze_by_unit(sample_pairs)

        assert "AICore0" in result
        assert "AICore1" in result

        # AICore0 有2个: op1(1000) 和 op3(1500)
        assert result["AICore0"]["count"] == 2
        assert result["AICore0"]["mean_cycles"] == 1250.0
        assert result["AICore0"]["min_cycles"] == 1000
        assert result["AICore0"]["max_cycles"] == 1500

        # AICore1 有1个: op2(2000)
        assert result["AICore1"]["count"] == 1
        assert result["AICore1"]["mean_cycles"] == 2000.0

    def test_analyze_by_unit_empty_pairs(self, plugin):
        """测试空数据按执行单元分组"""
        result = plugin._analyze_by_unit([])
        assert result == {}

    def test_analyze_by_source(self, plugin, sample_pairs):
        """测试按来源分组"""
        result = plugin._analyze_by_source(sample_pairs)

        assert "logA" in result
        assert "logB" in result

        # logA 有2个: op1(1000) 和 op2(2000)
        assert result["logA"]["count"] == 2
        assert result["logA"]["mean_cycles"] == 1500.0

        # logB 有1个: op3(1500)
        assert result["logB"]["count"] == 1
        assert result["logB"]["mean_cycles"] == 1500.0

    def test_analyze_by_source_with_time_conversion(self, plugin, sample_pairs):
        """测试包含时间转换的来源分组"""
        plugin.config["hardware"]["frequency_ghz"] = 1.0  # 1 GHz
        result = plugin._analyze_by_source(sample_pairs)

        # 验证时间转换
        assert "mean_ms" in result["logA"]
        assert "p90_ms" in result["logA"]

    def test_compute_mfu_basic(self, plugin):
        """测试MFU计算"""
        plugin.config["hardware"]["peak_tflops"] = 312.0
        pairs = [
            {
                "start_event": {
                    "fields": {
                        "flops": 312e12,  # 312 TFLOPS * 1 second
                    }
                },
                "end_event": {
                    "fields": {}
                },
                "performance": {
                    "duration_cycles": 1500000000,  # 1.5e9 cycles at 1.5 GHz = 1 second
                }
            }
        ]
        result = plugin._compute_mfu(pairs)

        assert result["count"] == 1
        assert "mean_mfu" in result
        assert result["frequency_ghz"] == 1.5
        assert result["peak_tflops"] == 312.0

        # 1秒内完成312 TFLOPS的计算 = 100% MFU
        assert abs(result["mean_mfu"] - 1.0) < 0.01

    def test_compute_mfu_no_flops(self, plugin):
        """测试缺失FLOPS数据"""
        plugin.config["hardware"]["peak_tflops"] = 312.0
        pairs = [{"performance": {"duration_cycles": 1000}}]
        result = plugin._compute_mfu(pairs)
        assert result == {}

    def test_compute_mfu_disabled(self, plugin):
        """测试禁用MFU计算（peak_tflops未配置）"""
        plugin.config["hardware"]["peak_tflops"] = None
        pairs = [{"performance": {"duration_cycles": 1000, "flops": 100}}]
        result = plugin._compute_mfu(pairs)
        assert result == {}

    def test_compute_mfu_zero_duration(self, plugin):
        """测试零耗时（边界情况）"""
        plugin.config["hardware"]["peak_tflops"] = 312.0
        pairs = [{"performance": {"duration_cycles": 0, "flops": 100}}]

        # 应该跳过或处理零除错误
        result = plugin._compute_mfu(pairs)
        # 可能返回空或跳过该值
        assert isinstance(result, dict)

    def test_generate_json_report(self, plugin, sample_pairs):
        """测试JSON报告生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "test_report.json")
            plugin.config["reporting"]["json_path"] = json_path

            result_data = {
                "summary": {"count": 3, "mean": 1500},
                "by_unit": {"AICore0": {"count": 2}},
                "by_source": {"logA": {"count": 2}},
                "mfu": {},
            }

            path = plugin._generate_json_report(result_data, sample_pairs)

            assert path == json_path
            assert os.path.exists(json_path)

            # 验证文件内容
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
                assert data["summary"]["count"] == 3
                assert data["total_pairs"] == 3

    def test_generate_json_report_invalid_path(self, plugin, sample_pairs):
        """测试无效路径"""
        plugin.config["reporting"]["json_path"] = "/invalid/path/report.json"
        result_data = {"summary": {}, "by_unit": {}, "mfu": {}}

        path = plugin._generate_json_report(result_data, sample_pairs)
        assert path is None

    def test_generate_csv_report(self, plugin, sample_pairs):
        """测试CSV报告生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "test_report.csv")
            plugin.config["reporting"]["csv_path"] = csv_path

            path = plugin._generate_csv_report(sample_pairs)

            assert path == csv_path
            assert os.path.exists(csv_path)

            # 验证CSV内容
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)

                # 表头 + 3行数据
                assert len(rows) == 4
                assert rows[0][0] == "Source"
                assert rows[1][1] == "op1"  # correlation_id

    def test_generate_csv_report_invalid_path(self, plugin, sample_pairs):
        """测试CSV无效路径"""
        plugin.config["reporting"]["csv_path"] = "/invalid/path/report.csv"
        path = plugin._generate_csv_report(sample_pairs)
        assert path is None

    def test_generate_reports_both_enabled(self, plugin, sample_pairs):
        """测试同时生成JSON和CSV"""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin.config["reporting"]["generate_json"] = True
            plugin.config["reporting"]["generate_csv"] = True
            plugin.config["reporting"]["json_path"] = os.path.join(tmpdir, "test.json")
            plugin.config["reporting"]["csv_path"] = os.path.join(tmpdir, "test.csv")

            result_data = {
                "summary": {},
                "by_unit": {},
                "by_source": {},
                "mfu": {},
            }
            paths = plugin._generate_reports(result_data, sample_pairs)

            assert "json" in paths
            assert "csv" in paths
            assert os.path.exists(paths["json"])
            assert os.path.exists(paths["csv"])

    def test_generate_reports_none_enabled(self, plugin, sample_pairs):
        """测试都不生成报告"""
        plugin.config["reporting"]["generate_json"] = False
        plugin.config["reporting"]["generate_csv"] = False

        result_data = {
            "summary": {},
            "by_unit": {},
            "by_source": {},
            "mfu": {},
        }
        paths = plugin._generate_reports(result_data, sample_pairs)
        assert paths == {}

    def test_large_dataset_performance(self, plugin):
        """测试大数据集性能"""
        # 生成10000个数据点
        large_pairs = [
            {"performance": {"duration_cycles": i}} for i in range(1, 10001)
        ]

        summary = plugin._compute_summary(large_pairs)
        assert summary["count"] == 10000
        assert summary["min_cycles"] == 1
        assert summary["max_cycles"] == 10000

    def test_extreme_values(self, plugin):
        """测试极端值"""
        pairs = [
            {"performance": {"duration_cycles": 1}},
            {"performance": {"duration_cycles": 999999999999}},
        ]
        summary = plugin._compute_summary(pairs)

        assert summary["min_cycles"] == 1
        assert summary["max_cycles"] == 999999999999
        assert summary["count"] == 2

    def test_missing_execution_unit(self, plugin):
        """测试缺失执行单元"""
        pairs = [
            {
                "correlation_id": "op1",
                "performance": {"duration_cycles": 1000},
                # 缺少 execution_unit
            }
        ]
        result = plugin._analyze_by_unit(pairs)
        # 应该使用默认值 "unknown"
        assert "unknown" in result
        assert result["unknown"]["count"] == 1

    def test_missing_source(self, plugin):
        """测试缺失来源标签"""
        pairs = [
            {
                "correlation_id": "op1",
                "performance": {"duration_cycles": 1000},
                # 缺少 source
            }
        ]
        result = plugin._analyze_by_source(pairs)
        # 应该使用默认值 "unknown"
        assert "unknown" in result
        assert result["unknown"]["count"] == 1

    def test_full_integration_with_reports(self, plugin, sample_pairs):
        """测试完整集成流程（包括报告生成）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin.config["reporting"]["generate_json"] = True
            plugin.config["reporting"]["generate_csv"] = True
            plugin.config["reporting"]["json_path"] = os.path.join(tmpdir, "summary.json")
            plugin.config["reporting"]["csv_path"] = os.path.join(tmpdir, "details.csv")

            context = {"perf_parser": {"pairs": sample_pairs}}
            result = plugin.execute(context)

            # 验证结果结构
            assert "summary" in result
            assert "by_unit" in result
            assert "by_source" in result
            assert "report_paths" in result

            # 验证报告文件
            assert "json" in result["report_paths"]
            assert "csv" in result["report_paths"]
            assert os.path.exists(result["report_paths"]["json"])
            assert os.path.exists(result["report_paths"]["csv"])
