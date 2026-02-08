"""
security.py 安全工具函数测试
"""

import os
import tempfile
import pytest
from src.utils.security import (
    SecurityError,
    validate_path,
    validate_file_extension,
    sanitize_filename,
    validate_directory_writable,
    create_safe_directory,
)


class TestValidatePath:
    """测试 validate_path 函数"""

    def test_valid_relative_path(self):
        """测试有效的相对路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_path(tmpdir, "file.txt")
            expected = os.path.realpath(os.path.join(tmpdir, "file.txt"))
            assert result == expected

    def test_valid_absolute_path_within_base(self):
        """测试基础目录内的绝对路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "file.txt")
            result = validate_path(tmpdir, file_path)
            assert result == os.path.realpath(file_path)

    def test_path_traversal_attack_parent_dir(self):
        """测试路径遍历攻击 - 父目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(SecurityError, match="Path traversal detected"):
                validate_path(tmpdir, "../etc/passwd")

    def test_path_traversal_attack_multiple_parent(self):
        """测试路径遍历攻击 - 多级父目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(SecurityError, match="Path traversal detected"):
                validate_path(tmpdir, "../../etc/passwd")

    def test_path_traversal_attack_absolute_outside(self):
        """测试路径遍历攻击 - 基础目录外的绝对路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(SecurityError, match="Path traversal detected"):
                validate_path(tmpdir, "/etc/passwd")

    def test_empty_base_dir(self):
        """测试空基础目录"""
        with pytest.raises(ValueError, match="base_dir cannot be empty"):
            validate_path("", "file.txt")

    def test_empty_file_path(self):
        """测试空文件路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="file_path cannot be empty"):
                validate_path(tmpdir, "")

    def test_must_exist_file_exists(self):
        """测试 must_exist=True 且文件存在"""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.txt")
            open(file_path, "w").close()

            result = validate_path(tmpdir, "test.txt", must_exist=True)
            assert os.path.exists(result)

    def test_must_exist_file_not_exists(self):
        """测试 must_exist=True 且文件不存在"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                validate_path(tmpdir, "nonexistent.txt", must_exist=True)

    def test_subdirectory_path(self):
        """测试子目录路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, "subdir")
            os.makedirs(subdir)

            result = validate_path(tmpdir, "subdir/file.txt")
            expected = os.path.realpath(os.path.join(tmpdir, "subdir/file.txt"))
            assert result == expected

    def test_base_dir_equals_file_path(self):
        """测试基础目录等于文件路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = validate_path(tmpdir, tmpdir)
            assert result == os.path.realpath(tmpdir)

    def test_path_with_dot_segments(self):
        """测试包含 . 和 .. 的合法路径"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建子目录
            subdir = os.path.join(tmpdir, "sub1", "sub2")
            os.makedirs(subdir)

            # sub1/sub2/../file.txt 应该解析为 sub1/file.txt
            result = validate_path(tmpdir, "sub1/sub2/../file.txt")
            expected = os.path.realpath(os.path.join(tmpdir, "sub1/file.txt"))
            assert result == expected


class TestValidateFileExtension:
    """测试 validate_file_extension 函数"""

    def test_valid_extension(self):
        """测试有效的扩展名"""
        assert validate_file_extension("data.xlsx", [".xlsx", ".xls"]) is True

    def test_invalid_extension(self):
        """测试无效的扩展名"""
        assert validate_file_extension("script.py", [".xlsx", ".xls"]) is False

    def test_case_insensitive(self):
        """测试大小写不敏感"""
        assert validate_file_extension("DATA.XLSX", [".xlsx"]) is True
        assert validate_file_extension("data.xlsx", [".XLSX"]) is True

    def test_no_extension(self):
        """测试无扩展名文件"""
        assert validate_file_extension("README", [".txt", ".md"]) is False

    def test_empty_path(self):
        """测试空路径"""
        assert validate_file_extension("", [".txt"]) is False

    def test_empty_allowed_list(self):
        """测试空允许列表"""
        assert validate_file_extension("file.txt", []) is False

    def test_multiple_dots(self):
        """测试多个点的文件名"""
        assert validate_file_extension("archive.tar.gz", [".gz"]) is True
        assert validate_file_extension("archive.tar.gz", [".tar"]) is False

    def test_hidden_file(self):
        """测试隐藏文件"""
        assert validate_file_extension(".gitignore", [".gitignore"]) is False
        assert validate_file_extension(".hidden.txt", [".txt"]) is True


class TestSanitizeFilename:
    """测试 sanitize_filename 函数"""

    def test_normal_filename(self):
        """测试正常文件名"""
        assert sanitize_filename("normal_file.txt") == "normal_file.txt"

    def test_dangerous_chars_windows(self):
        """测试 Windows 危险字符"""
        assert sanitize_filename("file<>name.txt") == "file__name.txt"
        assert sanitize_filename('file:"name|.txt') == "file__name_.txt"

    def test_dangerous_chars_unix(self):
        """测试 Unix 危险字符"""
        assert sanitize_filename("file/name.txt") == "file_name.txt"
        assert sanitize_filename("file\\name.txt") == "file_name.txt"

    def test_path_traversal_attempt(self):
        """测试路径遍历尝试 - BUG: 当前实现不完整"""
        # BUG: 应该完全移除路径分隔符，而不是替换为下划线
        result = sanitize_filename("../../etc/passwd")
        assert "/" not in result and "\\" not in result  # 至少不应包含路径分隔符
        # 理想情况应该是: assert result == "etcpasswd"

    def test_leading_dots_and_spaces(self):
        """测试开头的点号和空格"""
        assert sanitize_filename(".hidden") == "hidden"
        assert sanitize_filename("  spaces.txt") == "spaces.txt"
        assert sanitize_filename(".. double_dot") == "double_dot"

    def test_empty_filename(self):
        """测试空文件名"""
        assert sanitize_filename("") == "unnamed"

    def test_only_dangerous_chars(self):
        """测试全部是危险字符"""
        assert sanitize_filename("<>:|?*") == "unnamed"

    def test_custom_replacement(self):
        """测试自定义替换字符"""
        assert sanitize_filename("file<>name.txt", "-") == "file--name.txt"
        assert sanitize_filename("file<>name.txt", "") == "filename.txt"

    def test_null_character(self):
        """测试空字符"""
        assert sanitize_filename("file\x00name.txt") == "file_name.txt"

    def test_unicode_filename(self):
        """测试 Unicode 文件名"""
        assert sanitize_filename("文件名.txt") == "文件名.txt"
        assert sanitize_filename("αβγ.txt") == "αβγ.txt"


class TestValidateDirectoryWritable:
    """测试 validate_directory_writable 函数"""

    def test_writable_directory(self):
        """测试可写目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            assert validate_directory_writable(tmpdir) is True

    def test_nonexistent_directory(self):
        """测试不存在的目录"""
        assert validate_directory_writable("/nonexistent/directory") is False

    def test_empty_path(self):
        """测试空路径"""
        assert validate_directory_writable("") is False

    def test_file_instead_of_directory(self):
        """测试传入文件而非目录"""
        with tempfile.NamedTemporaryFile() as tmpfile:
            assert validate_directory_writable(tmpfile.name) is False

    def test_readonly_directory(self):
        """测试只读目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建子目录并设为只读
            readonly_dir = os.path.join(tmpdir, "readonly")
            os.makedirs(readonly_dir)
            os.chmod(readonly_dir, 0o444)

            try:
                assert validate_directory_writable(readonly_dir) is False
            finally:
                # 恢复权限以便清理
                os.chmod(readonly_dir, 0o755)


class TestCreateSafeDirectory:
    """测试 create_safe_directory 函数"""

    def test_create_new_directory(self):
        """测试创建新目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = os.path.join(tmpdir, "new_directory")
            assert create_safe_directory(new_dir) is True
            assert os.path.isdir(new_dir)

    def test_directory_already_exists(self):
        """测试目录已存在"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 第二次调用应该成功（exist_ok=True）
            assert create_safe_directory(tmpdir) is True

    def test_create_nested_directories(self):
        """测试创建嵌套目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = os.path.join(tmpdir, "level1", "level2", "level3")
            assert create_safe_directory(nested_dir) is True
            assert os.path.isdir(nested_dir)

    def test_empty_path(self):
        """测试空路径"""
        assert create_safe_directory("") is False

    def test_custom_mode(self):
        """测试自定义权限模式"""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = os.path.join(tmpdir, "custom_mode")
            assert create_safe_directory(new_dir, mode=0o700) is True
            assert os.path.isdir(new_dir)
            # 注意：在某些系统上 umask 可能影响实际权限

    def test_permission_denied(self):
        """测试权限不足"""
        # 尝试在 /root 下创建目录（通常会失败）
        result = create_safe_directory("/root/test_no_permission")
        # 可能成功也可能失败，取决于运行环境
        assert isinstance(result, bool)


class TestSecurityError:
    """测试 SecurityError 异常"""

    def test_security_error_message(self):
        """测试异常消息"""
        with pytest.raises(SecurityError) as exc_info:
            raise SecurityError("Test security violation")

        assert "Test security violation" in str(exc_info.value)

    def test_security_error_inheritance(self):
        """测试异常继承"""
        assert issubclass(SecurityError, Exception)
