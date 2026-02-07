"""
日志文件工具函数
"""

import os
import glob


def find_latest_log():
    """查找最新的日志文件（格式: logs_*.txt）"""
    # 查找 logs/ 目录下的 logs_*.txt 文件
    log_pattern = "logs/logs_*.txt"
    log_files = glob.glob(log_pattern)

    if not log_files:
        # 回退：查找任意 .txt 文件
        log_files = glob.glob("logs/*.txt")

    if not log_files:
        # 最后回退：使用示例文件
        log_files = glob.glob("examples/logs/*.txt")

    if not log_files:
        return None

    # 返回最新的文件（按修改时间排序）
    latest = max(log_files, key=os.path.getmtime)
    return latest


def cleanup_old_logs(max_keep=5):
    """清理旧日志文件，只保留最新的 max_keep 个"""
    log_pattern = "logs/logs_*.txt"
    log_files = glob.glob(log_pattern)

    if len(log_files) <= max_keep:
        return

    # 按修改时间排序（最新的在前）
    log_files.sort(key=os.path.getmtime, reverse=True)

    # 删除超出数量的旧文件
    files_to_delete = log_files[max_keep:]
    for log_file in files_to_delete:
        try:
            os.remove(log_file)
            print(f"✓ 清理旧日志: {log_file}")
        except Exception as e:
            print(f"⚠️  清理失败 {log_file}: {e}")


def validate_log_file(log_file):
    """验证日志文件"""
    if log_file:
        return True

    print("=" * 60)
    print("❌ 错误: 未找到日志文件")
    print("=" * 60)
    print()
    print("请将日志文件放到 logs/ 目录")
    print("推荐命名格式: logs_20260207_153045.txt")
    print("=" * 60)
    return False
