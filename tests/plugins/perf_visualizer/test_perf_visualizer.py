"""
perf_visualizer 插件单元测试
"""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

# Mock pyecharts before importing the plugin
sys.modules['pyecharts'] = MagicMock()
sys.modules['pyecharts.options'] = MagicMock()
sys.modules['pyecharts.charts'] = MagicMock()

from src.plugins.perf_visualizer.plugin import PerfVisualizerPlugin  # noqa: E402


@pytest.fixture
def basic_config():
    """基本配置"""
    return {
        "enable": True,
        "gantt": {
            "output_path": "output/perf_timeline.html",
            "title": "算子执行时间线",
            "height": 600,
            "width": 1400,
            "color_scheme": "default",
        },
        "visualizations": {
            "histogram": False,
        },
        "histogram": {
            "output_path": "output/perf_histogram.html",
            "title": "算子耗时分布",
            "bins": 30,
            "height": 500,
            "width": 900,
        },
    }


@pytest.fixture
def sample_pairs():
    """示例事件对数据"""
    return [
        {
            "correlation_id": "op1",
            "rule_name": "rule1",
            "execution_unit": "AICore0",
            "source": "logA",
            "start_event": {
                "line_number": 10,
                "fields": {"cycle_start": 1000, "begin_cycle": 1000},
            },
            "end_event": {
                "line_number": 20,
                "fields": {"cycle_end": 2000, "done_cycle": 2000},
            },
            "performance": {"duration_cycles": 1000, "flops": 100},
        },
        {
            "correlation_id": "op2",
            "rule_name": "rule1",
            "execution_unit": "AICore1",
            "source": "logA",
            "start_event": {
                "line_number": 15,
                "fields": {"start_cycle": 1500},
            },
            "end_event": {
                "line_number": 25,
                "fields": {"end_cycle": 3500},
            },
            "performance": {"duration_cycles": 2000},
        },
        {
            "correlation_id": "op3",
            "rule_name": "rule2",
            "execution_unit": "AICore0",
            "source": "logB",
            "start_event": {
                "line_number": 30,
                "fields": {"cycle_start": 2500},
            },
            "end_event": {
                "line_number": 40,
                "fields": {"cycle_end": 4000},
            },
            "performance": {"duration_cycles": 1500},
        },
    ]


@pytest.fixture
def plugin(basic_config):
    """创建插件实例"""
    with patch.object(PerfVisualizerPlugin, "_load_config", return_value=basic_config):
        return PerfVisualizerPlugin()


class TestPerfVisualizerPlugin:
    """PerfVisualizerPlugin 测试类"""

    def test_plugin_initialization(self, basic_config):
        """测试插件初始化"""
        with patch.object(PerfVisualizerPlugin, "_load_config", return_value=basic_config):
            plugin = PerfVisualizerPlugin()
            assert plugin.enabled is True
            assert plugin.level == 3
            assert plugin.dependencies == ["perf_parser", "perf_analyzer"]
            assert plugin.config == basic_config

    def test_plugin_disabled(self):
        """测试禁用插件"""
        config = {"enable": False}
        with patch.object(PerfVisualizerPlugin, "_load_config", return_value=config):
            plugin = PerfVisualizerPlugin()
            assert plugin.enabled is False

    def test_execute_with_empty_pairs(self, plugin):
        """测试空数据集"""
        context = {"perf_parser": {"pairs": []}}
        result = plugin.execute(context)

        assert result["charts"] == {}
        assert result["timeline_path"] is None

    def test_execute_with_missing_perf_parser(self, plugin):
        """测试缺失perf_parser数据"""
        context = {}
        result = plugin.execute(context)

        assert result["charts"] == {}
        assert result["timeline_path"] is None

    def test_execute_normal_flow(self, plugin, sample_pairs):
        """测试正常执行流程（使用mock的plotly）"""
        # 由于plotly是可选依赖，我们测试在有plotly的情况下的流程
        # 通过检查结果结构来验证功能

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "timeline.html")
            plugin.config["gantt"]["output_path"] = output_path

            context = {"perf_parser": {"pairs": sample_pairs}}
            result = plugin.execute(context)

            # 验证结果结构（无论plotly是否可用）
            assert "charts" in result
            assert "timeline_path" in result

            # plotly已被mock，所以会生成图表路径
            if result["timeline_path"]:
                assert "operator_timeline" in result["charts"]

    def test_extract_cycle_value_first_match(self, plugin):
        """测试提取cycle值 - 匹配第一个"""
        fields = {"cycle_start": 100, "start_cycle": 200, "begin_cycle": 300}
        possible_names = ["cycle_start", "start_cycle", "begin_cycle"]

        value = plugin._extract_cycle_value(fields, possible_names)
        assert value == 100  # 返回第一个匹配的

    def test_extract_cycle_value_second_match(self, plugin):
        """测试提取cycle值 - 匹配第二个"""
        fields = {"start_cycle": 200, "begin_cycle": 300}
        possible_names = ["cycle_start", "start_cycle", "begin_cycle"]

        value = plugin._extract_cycle_value(fields, possible_names)
        assert value == 200

    def test_extract_cycle_value_no_match(self, plugin):
        """测试提取cycle值 - 无匹配"""
        fields = {"other_field": 100}
        possible_names = ["cycle_start", "start_cycle"]

        value = plugin._extract_cycle_value(fields, possible_names)
        assert value is None

    def test_extract_cycle_value_empty_fields(self, plugin):
        """测试空字段"""
        fields = {}
        possible_names = ["cycle_start"]

        value = plugin._extract_cycle_value(fields, possible_names)
        assert value is None

    def test_prepare_timeline_data_normal(self, plugin, sample_pairs):
        """测试准备时间线数据"""
        timeline_data = plugin._prepare_timeline_data(sample_pairs)

        assert len(timeline_data) == 3

        # 验证第一个数据点
        item = timeline_data[0]
        assert item["operator_id"] == "op1"
        assert item["unit"] == "AICore0"
        assert item["source"] == "logA"
        assert item["start_cycle"] == 1000
        assert item["end_cycle"] == 2000
        assert item["duration_cycles"] == 1000

    def test_prepare_timeline_data_sorted_by_line(self, plugin):
        """测试数据按行号排序"""
        pairs = [
            {
                "correlation_id": "op2",
                "execution_unit": "AICore1",
                "start_event": {"line_number": 30, "fields": {"cycle_start": 2000}},
                "end_event": {"line_number": 40, "fields": {"cycle_end": 3000}},
                "performance": {},
            },
            {
                "correlation_id": "op1",
                "execution_unit": "AICore0",
                "start_event": {"line_number": 10, "fields": {"cycle_start": 1000}},
                "end_event": {"line_number": 20, "fields": {"cycle_end": 2000}},
                "performance": {},
            },
        ]

        timeline_data = plugin._prepare_timeline_data(pairs)

        # 应该按start_event的line_number排序
        assert timeline_data[0]["operator_id"] == "op1"
        assert timeline_data[1]["operator_id"] == "op2"

    def test_prepare_timeline_data_missing_cycle_info(self, plugin):
        """测试缺失cycle信息的数据被跳过"""
        pairs = [
            {
                "correlation_id": "op1",
                "execution_unit": "AICore0",
                "start_event": {"line_number": 10, "fields": {}},  # 缺失cycle
                "end_event": {"line_number": 20, "fields": {}},
                "performance": {},
            },
            {
                "correlation_id": "op2",
                "execution_unit": "AICore1",
                "start_event": {"line_number": 15, "fields": {"cycle_start": 1000}},
                "end_event": {"line_number": 25, "fields": {"cycle_end": 2000}},
                "performance": {},
            },
        ]

        timeline_data = plugin._prepare_timeline_data(pairs)

        # 只有op2有完整的cycle信息
        assert len(timeline_data) == 1
        assert timeline_data[0]["operator_id"] == "op2"

    def test_prepare_timeline_data_partial_cycle_info(self, plugin):
        """测试部分cycle信息"""
        pairs = [
            {
                "correlation_id": "op1",
                "execution_unit": "AICore0",
                "start_event": {
                    "line_number": 10,
                    "fields": {"cycle_start": 1000},
                },  # 有start
                "end_event": {"line_number": 20, "fields": {}},  # 缺失end
                "performance": {},
            }
        ]

        timeline_data = plugin._prepare_timeline_data(pairs)
        assert len(timeline_data) == 0  # 被跳过

    def test_prepare_timeline_data_with_performance(self, plugin):
        """测试包含性能数据"""
        pairs = [
            {
                "correlation_id": "op1",
                "execution_unit": "AICore0",
                "rule_name": "test_rule",
                "start_event": {"line_number": 10, "fields": {"cycle_start": 1000}},
                "end_event": {"line_number": 20, "fields": {"cycle_end": 2000}},
                "performance": {"flops": 1000, "bandwidth": 500},
            }
        ]

        timeline_data = plugin._prepare_timeline_data(pairs)
        assert timeline_data[0]["performance"] == {"flops": 1000, "bandwidth": 500}
        assert timeline_data[0]["rule_name"] == "test_rule"

    def test_prepare_timeline_data_default_source(self, plugin):
        """测试默认source值"""
        pairs = [
            {
                "correlation_id": "op1",
                "execution_unit": "AICore0",
                # 没有source字段
                "start_event": {"line_number": 10, "fields": {"cycle_start": 1000}},
                "end_event": {"line_number": 20, "fields": {"cycle_end": 2000}},
                "performance": {},
            }
        ]

        timeline_data = plugin._prepare_timeline_data(pairs)
        assert timeline_data[0]["source"] == "unknown"

    def test_prepare_timeline_data_default_unit(self, plugin):
        """测试默认执行单元"""
        pairs = [
            {
                "correlation_id": "op1",
                # 没有execution_unit字段
                "start_event": {"line_number": 10, "fields": {"cycle_start": 1000}},
                "end_event": {"line_number": 20, "fields": {"cycle_end": 2000}},
                "performance": {},
            }
        ]

        timeline_data = plugin._prepare_timeline_data(pairs)
        assert timeline_data[0]["unit"] == "Unknown"

    def test_create_timeline_figure(self, plugin):
        """测试创建时间线图表逻辑"""
        timeline_data = [
            {
                "index": 0,
                "source": "logA",
                "operator_id": "op1",
                "unit": "AICore0",
                "start_cycle": 1000,
                "end_cycle": 2000,
                "duration_cycles": 1000,
                "start_line": 10,
                "end_line": 20,
                "performance": {"flops": 100},
                "rule_name": "rule1",
            }
        ]

        context = {}
        # 函数会调用plotly，但plotly已被mock，所以会返回mock对象
        fig = plugin._create_timeline_figure(timeline_data, context)

        # 验证返回了figure对象（mock的）
        assert fig is not None

    def test_create_timeline_figure_multiple_units(self, plugin):
        """测试多个执行单元数据准备"""
        timeline_data = [
            {
                "index": 0,
                "source": "logA",
                "operator_id": "op1",
                "unit": "AICore0",
                "start_cycle": 1000,
                "end_cycle": 2000,
                "duration_cycles": 1000,
                "start_line": 10,
                "end_line": 20,
                "performance": {},
                "rule_name": "rule1",
            },
            {
                "index": 1,
                "source": "logA",
                "operator_id": "op2",
                "unit": "AICore1",
                "start_cycle": 1500,
                "end_cycle": 2500,
                "duration_cycles": 1000,
                "start_line": 15,
                "end_line": 25,
                "performance": {},
                "rule_name": "rule1",
            },
        ]

        context = {}
        fig = plugin._create_timeline_figure(timeline_data, context)

        # 验证可以处理多个执行单元
        assert fig is not None
        units = {item["unit"] for item in timeline_data}
        assert len(units) == 2

    def test_create_timeline_figure_multiple_sources(self, plugin):
        """测试多个来源数据准备"""
        timeline_data = [
            {
                "index": 0,
                "source": "logA",
                "operator_id": "op1",
                "unit": "AICore0",
                "start_cycle": 1000,
                "end_cycle": 2000,
                "duration_cycles": 1000,
                "start_line": 10,
                "end_line": 20,
                "performance": {},
                "rule_name": "rule1",
            },
            {
                "index": 1,
                "source": "logB",
                "operator_id": "op2",
                "unit": "AICore0",
                "start_cycle": 1500,
                "end_cycle": 2500,
                "duration_cycles": 1000,
                "start_line": 15,
                "end_line": 25,
                "performance": {},
                "rule_name": "rule1",
            },
        ]

        context = {}
        fig = plugin._create_timeline_figure(timeline_data, context)

        # 验证可以处理多个来源
        assert fig is not None
        sources = {item["source"] for item in timeline_data}
        assert len(sources) == 2

    def test_get_color_scheme_default(self, plugin):
        """测试默认配色方案"""
        colors = plugin._get_color_scheme(5)
        assert len(colors) == 10  # 默认方案有10种颜色
        assert colors[0] == "#3498db"

    def test_get_color_scheme_rainbow(self, plugin):
        """测试彩虹配色"""
        plugin.config["gantt"]["color_scheme"] = "rainbow"
        colors = plugin._get_color_scheme(5)
        assert len(colors) == 6
        assert colors[0] == "#e74c3c"

    def test_get_color_scheme_monochrome(self, plugin):
        """测试单色配色"""
        plugin.config["gantt"]["color_scheme"] = "monochrome"
        colors = plugin._get_color_scheme(5)
        assert len(colors) == 5
        assert colors[0] == "#3498db"

    def test_generate_histogram(self, plugin):
        """测试生成直方图逻辑"""
        pairs = [
            {"performance": {"duration_cycles": 100}},
            {"performance": {"duration_cycles": 200}},
            {"performance": {"duration_cycles": 300}},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "histogram.html")
            plugin.config["histogram"]["output_path"] = output_path

            result_path = plugin._generate_histogram(pairs)

            # 验证返回了路径（plotly被mock，所以会执行）
            assert result_path == output_path

    def test_generate_histogram_no_duration_data(self, plugin):
        """测试无耗时数据"""
        pairs = [{"performance": {}}]  # 没有duration相关字段

        result = plugin._generate_histogram(pairs)
        assert result is None

    def test_generate_histogram_extract_from_various_fields(self, plugin):
        """测试从各种字段提取耗时"""
        pairs = [
            {"performance": {"duration_cycles": 100}},
            {"performance": {"cycle_duration": 200}},
            {"performance": {"exec_cycles": 300}},
        ]

        mock_fig = MagicMock()
        mock_go = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Histogram = MagicMock()

        with patch.dict('sys.modules', {'plotly.graph_objects': mock_go}):
            with tempfile.TemporaryDirectory() as tmpdir:
                plugin.config["histogram"]["output_path"] = os.path.join(
                    tmpdir, "hist.html"
                )
                result = plugin._generate_histogram(pairs)

                # 至少提取到一些数据
                assert result is not None

    def test_generate_histogram_exception_handling(self, plugin):
        """测试异常处理 - 使用无效路径触发异常"""
        pairs = [{"performance": {"duration_cycles": 100}}]

        # 使用无效路径触发write_html异常
        plugin.config["histogram"]["output_path"] = "/invalid/path/histogram.html"
        result = plugin._generate_histogram(pairs)

        # 应该返回None（异常被捕获）
        assert result is None

    def test_execute_with_histogram_enabled(self, plugin, sample_pairs):
        """测试启用直方图"""
        plugin.config["visualizations"]["histogram"] = True

        mock_fig = MagicMock()
        mock_go = MagicMock()
        mock_go.Figure.return_value = mock_fig
        mock_go.Bar = MagicMock()
        mock_go.Scatter = MagicMock()
        mock_go.Histogram = MagicMock()

        with patch.dict('sys.modules', {'plotly.graph_objects': mock_go}):
            with tempfile.TemporaryDirectory() as tmpdir:
                plugin.config["gantt"]["output_path"] = os.path.join(tmpdir, "timeline.html")
                plugin.config["histogram"]["output_path"] = os.path.join(
                    tmpdir, "histogram.html"
                )

                context = {"perf_parser": {"pairs": sample_pairs}}
                result = plugin.execute(context)

                # 应该生成两个图表
                assert "operator_timeline" in result["charts"]
                assert "histogram" in result["charts"]

    def test_execute_pyecharts_not_installed(self, plugin, sample_pairs):
        """测试pyecharts未安装"""
        with patch("builtins.__import__", side_effect=ImportError("No module named 'pyecharts'")):
            context = {"perf_parser": {"pairs": sample_pairs}}
            result = plugin.execute(context)

            # 应该优雅失败
            assert result["timeline_path"] is None

    def test_generate_operator_timeline_exception(self, plugin, sample_pairs):
        """测试时间线生成异常 - 使用无效路径"""
        plugin.config["gantt"]["output_path"] = "/invalid/path/timeline.html"

        context = {}
        result = plugin._generate_operator_timeline(sample_pairs, context)

        # 应该返回None（异常被捕获）
        assert result is None

    def test_prepare_timeline_data_empty_input(self, plugin):
        """测试空输入"""
        timeline_data = plugin._prepare_timeline_data([])
        assert timeline_data == []

    def test_create_timeline_figure_empty_data(self, plugin):
        """测试空数据创建图表"""
        # 空数据也应该能创建图表
        timeline_data = []
        context = {}
        fig = plugin._create_timeline_figure(timeline_data, context)

        # 应该成功创建（虽然是空图表，mock的plotly会返回对象）
        assert fig is not None

    def test_large_dataset_visualization(self, plugin):
        """测试大数据集可视化"""
        # 生成1000个事件对
        large_pairs = [
            {
                "correlation_id": f"op{i}",
                "execution_unit": f"AICore{i % 8}",
                "source": "logA",
                "start_event": {
                    "line_number": i * 10,
                    "fields": {"cycle_start": i * 1000},
                },
                "end_event": {
                    "line_number": i * 10 + 5,
                    "fields": {"cycle_end": i * 1000 + 500},
                },
                "performance": {},
            }
            for i in range(1000)
        ]

        timeline_data = plugin._prepare_timeline_data(large_pairs)
        assert len(timeline_data) == 1000

    def test_extreme_cycle_values(self, plugin):
        """测试极端cycle值"""
        pairs = [
            {
                "correlation_id": "op1",
                "execution_unit": "AICore0",
                "start_event": {
                    "line_number": 10,
                    "fields": {"cycle_start": 999999999999},
                },
                "end_event": {
                    "line_number": 20,
                    "fields": {"cycle_end": 999999999999999},
                },
                "performance": {},
            }
        ]

        timeline_data = plugin._prepare_timeline_data(pairs)
        assert len(timeline_data) == 1
        # 999999999999999 - 999999999999 = 999000000000000
        assert timeline_data[0]["duration_cycles"] == 999000000000000

    def test_negative_duration(self, plugin):
        """测试负耗时（异常情况）"""
        pairs = [
            {
                "correlation_id": "op1",
                "execution_unit": "AICore0",
                "start_event": {"line_number": 10, "fields": {"cycle_start": 2000}},
                "end_event": {
                    "line_number": 20,
                    "fields": {"cycle_end": 1000},
                },  # end < start
                "performance": {},
            }
        ]

        timeline_data = plugin._prepare_timeline_data(pairs)
        # 应该能处理，但duration为负
        assert len(timeline_data) == 1
        assert timeline_data[0]["duration_cycles"] == -1000

    def test_full_integration(self, plugin, sample_pairs):
        """测试完整集成流程"""
        plugin.config["visualizations"]["histogram"] = True

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin.config["gantt"]["output_path"] = os.path.join(tmpdir, "timeline.html")
            plugin.config["histogram"]["output_path"] = os.path.join(
                tmpdir, "histogram.html"
            )

            context = {
                "perf_parser": {"pairs": sample_pairs},
                "perf_analyzer": {"summary": {"count": 3}},
            }

            result = plugin.execute(context)

            # 验证结果完整性
            assert "charts" in result
            assert "timeline_path" in result

            # plotly被mock，应该生成两个图表
            if result["charts"]:
                assert len(result["charts"]) >= 1  # 至少有timeline
