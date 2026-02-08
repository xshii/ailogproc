"""
插件注册表和调度器
"""

from src.plugins.dld_configtmp import DownloadTemplatePlugin
from src.plugins.config_parser import ConfigParserPlugin
from src.plugins.constraint_checker import ConstraintCheckerPlugin
from src.plugins.excel_writer import ExcelWriterPlugin
from src.plugins.auto_filename import AutoFilenamePlugin


from src.utils import info, warning, error
# 插件注册表
PLUGIN_REGISTRY = {
    "dld_configtmp": DownloadTemplatePlugin,
    "config_parser": ConfigParserPlugin,
    "constraint_checker": ConstraintCheckerPlugin,
    "excel_writer": ExcelWriterPlugin,
    "auto_filename": AutoFilenamePlugin,
}


def load_plugins() -> tuple:
    """
    加载所有已启用的插件（插件自动从各自目录加载配置）

    Returns:
        (plugins, plugin_configs) 元组
        - plugins: 按 level 排序的插件列表
        - plugin_configs: {plugin_key: config} 字典
    """
    plugins = []
    plugin_configs = {}

    for key, cls in PLUGIN_REGISTRY.items():
        try:
            plugin = cls()  # 插件自动加载配置
            if plugin.enabled:
                plugins.append(plugin)
                plugin_configs[key] = plugin.config  # 保存配置
        except Exception as e:
            error(f"  ⚠️  加载插件 '{key}' 失败: {e}")
    # 按 level 排序：Level 1 (Extractor) -> Level 2 (Processor) -> Level 3 (小插件)
    plugins.sort(key=lambda p: p.level)

    return plugins, plugin_configs


def run_plugins(plugins: list, plugin_configs: dict, initial_context: dict) -> dict:
    """按层级顺序执行所有插件，传递上下文"""
    context = initial_context.copy()

    for plugin_key, config in plugin_configs.items():
        context[f"{plugin_key}_config"] = config

    _print_plugin_header()

    for plugin in plugins:
        _execute_single_plugin(plugin, context)

    _print_plugin_footer()

    return context


def _print_plugin_header():
    """打印插件执行头部"""
    info("\n" + "=" * 60)
    info("开始执行插件")
    info("=" * 60)
def _print_plugin_footer():
    """打印插件执行尾部"""
    info("\n" + "=" * 60)
    info("插件执行完成")
    info("=" * 60)
def _execute_single_plugin(plugin, context):
    """执行单个插件"""
    plugin_key = _get_plugin_key(plugin)
    info(f"\n[Level {plugin.level}] 执行插件: {plugin_key}")
    if not _check_dependencies(plugin, context):
        warning("  ⚠️  跳过: 依赖未满足")
        return

    try:
        result = plugin.execute(context)

        if result:
            context[plugin_key] = result
            info("  ✓ 完成")
        else:
            info("  ✓ 完成（无输出）")
    except Exception as e:
        error(f"  ❌ 失败: {e}")
        import traceback

        traceback.print_exc()


def _get_plugin_key(plugin) -> str:
    """获取插件的注册键名"""
    for key, cls in PLUGIN_REGISTRY.items():
        if isinstance(plugin, cls):
            return key
    return plugin.__class__.__name__


def _check_dependencies(plugin, context: dict) -> bool:
    """检查插件的依赖是否满足"""
    for dep in plugin.dependencies:
        if dep not in context:
            return False
    return True
