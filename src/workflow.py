"""
业务流程模块 - 插件调度
"""

from src.plugins import load_plugins, run_plugins


def process_log_to_excel(excel_file, log_file, output_file=None, sheet_name=None):
    """
    主处理流程：通过插件系统解析日志并填充到Excel

    插件执行顺序：
    Level 1: config_extractor - 提取配置
    Level 2: excel_writer - 写入Excel
    Level 3: auto_filename - 自动重命名（小插件）

    Args:
        excel_file: Excel模板文件路径
        log_file: 日志文件路径
        output_file: 输出文件路径（可选）
        sheet_name: 工作表名称（可选）

    Returns:
        最终输出文件路径
    """
    # 准备初始上下文
    initial_context = {
        "log_file": log_file,
        "excel_file": excel_file,
        "output_file": output_file,
        "sheet_name": sheet_name,
    }

    # 加载插件（按 level 排序，插件自动加载各自的配置）
    plugins, plugin_configs = load_plugins()

    # 执行插件
    final_context = run_plugins(plugins, plugin_configs, initial_context)

    # 返回最终输出文件路径
    output_file = final_context.get("auto_filename", {}).get("output_file")
    if not output_file:
        output_file = final_context.get("excel_writer", {}).get("output_file")

    if output_file:
        print("\n✅ 处理完成！")
        print(f"输出文件: {output_file}")
    else:
        print("\n⚠️  处理完成，但未生成输出文件")

    return output_file
