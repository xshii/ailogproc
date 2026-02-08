"""
模板下载插件 - 从API下载Excel模板并管理版本
"""

import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

# 可选依赖
try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from src.plugins.base import Plugin
from src.utils import info, warning, error


class DownloadTemplatePlugin(Plugin):
    """模板下载插件 - Level 0 (预处理层)"""

    level = 0  # 最先执行，在所有插件之前
    dependencies = []  # 无依赖

    def execute(self, context: dict) -> dict:
        """下载或准备Excel模板

        Args:
            context: 上下文字典，可能包含：
                - excel_file: 用户指定的模板文件路径（优先使用）
                - template_name: 模板名称（可选）

        Returns:
            {
                'template_path': 模板文件路径,
                'version': 模板版本,
                'downloaded': 是否刚下载,
                'manifest': manifest 信息
            }
        """
        info("[模板下载] 准备Excel模板...")

        # 优先使用 context 中的 excel_file（用户指定的模板）
        user_template = context.get("excel_file")
        if user_template:
            info(f"  ✓ 使用指定模板: {user_template}")
            return {
                "template_path": user_template,
                "version": "user-specified",
                "downloaded": False,
                "manifest": {},
            }

        # 用户未指定模板，使用插件的自动查找/下载逻辑
        info("  未指定模板，自动查找...")

        # 初始化存储目录
        self._init_storage()

        # 加载 manifest
        manifest = self._load_manifest()

        template_path = None
        downloaded = False
        version = None

        # 检查是否需要下载
        if self.config.get("download_enabled", False):
            info("  检查模板更新...")
            download_result = self._download_template(manifest)

            if download_result:
                template_path = download_result["path"]
                version = download_result["version"]
                downloaded = True
                info(f"  ✓ 下载完成: {template_path}")
            else:
                info("  ℹ️  使用本地模板")
                template_path = self._get_latest_local_template(manifest)
                version = manifest.get("current_version")
        else:
            info("  下载功能已禁用，使用本地模板")
            template_path = self._get_latest_local_template(manifest)
            version = manifest.get("current_version")

        if not template_path:
            raise FileNotFoundError(
                "未找到可用的模板文件，请将模板放到 templates/ 目录或通过命令行指定"
            )

        info(f"  ✓ 使用模板: {template_path}")

        # 更新 manifest
        self._update_manifest(manifest, template_path, version, downloaded)

        return {
            "template_path": template_path,
            "version": version,
            "downloaded": downloaded,
            "manifest": manifest,
        }

    def _init_storage(self):
        """初始化存储目录"""
        storage = self.config.get("storage", {})
        templates_dir = storage.get("templates_dir", "templates")
        backup_dir = storage.get("backup_dir", "templates/backups")

        Path(templates_dir).mkdir(parents=True, exist_ok=True)
        Path(backup_dir).mkdir(parents=True, exist_ok=True)

    def _load_manifest(self) -> dict:
        """加载 manifest 文件"""
        storage = self.config.get("storage", {})
        manifest_file = storage.get("manifest_file", "templates/manifest.json")

        if os.path.exists(manifest_file):
            with open(manifest_file, "r", encoding="utf-8") as f:
                return json.load(f)

        # 初始 manifest
        return {
            "current_version": None,
            "current_template": None,
            "last_update": None,
            "history": [],
        }

    def _download_template(self, manifest: dict) -> dict | None:
        """从API下载模板

        Returns:
            {'path': 文件路径, 'version': 版本号} 或 None
        """
        if not HAS_REQUESTS:
            warning("  ⚠️  未安装 requests 模块，无法从API下载模板")
            return None

        api_config = self.config.get("api", {})
        api_url = api_config.get("url")

        if not api_url:
            warning("  ⚠️  未配置 API URL")
            return None

        try:
            headers = self._prepare_request_headers(api_config)
            timeout = api_config.get("timeout", 30)

            metadata = self._fetch_template_metadata(api_url, headers, timeout)
            if not metadata:
                return None

            version = metadata.get("version")
            if version == manifest.get("current_version"):
                info(f"  ✓ 已是最新版本: {version}")
                return None

            file_content = self._download_template_file(metadata, api_url, timeout)
            if not file_content:
                return None

            if not self._validate_hash(file_content, metadata.get("hash")):
                return None

            template_path = self._save_template(file_content, version, manifest)
            return {"path": template_path, "version": version}

        except requests.RequestException as e:
            error(f"  ✗ 下载失败: {e}")
            return None
        except Exception as e:
            error(f"  ✗ 处理失败: {e}")
            return None

    def _prepare_request_headers(self, api_config: dict) -> dict:
        """准备请求头，包括认证信息"""
        headers = api_config.get("headers", {})
        auth_config = api_config.get("auth")

        if auth_config:
            auth_type = auth_config.get("type", "bearer")
            token = auth_config.get("token")

            if auth_type == "bearer":
                headers["Authorization"] = f"Bearer {token}"
            # Note: basic auth can be added here if needed

        return headers

    def _fetch_template_metadata(
        self, api_url: str, headers: dict, timeout: int
    ) -> dict | None:
        """从API获取模板元数据"""
        response = requests.get(api_url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json()

    def _download_template_file(
        self, metadata: dict, api_url: str, timeout: int
    ) -> bytes | None:
        """下载模板文件内容"""
        download_url = metadata.get("download_url") or api_url
        version = metadata.get("version")

        info(f"  正在下载版本: {version}")
        file_response = requests.get(download_url, timeout=timeout)
        file_response.raise_for_status()

        return file_response.content

    def _validate_hash(self, file_content: bytes, expected_hash: str | None) -> bool:
        """验证文件hash"""
        if not expected_hash:
            return True

        if not self.config.get("validation", {}).get("verify_hash", True):
            return True

        file_hash = hashlib.sha256(file_content).hexdigest()
        if file_hash != expected_hash:
            error(f"  ✗ Hash 验证失败: 期望 {expected_hash}, 实际 {file_hash}")
            return False

        return True

    def _save_template(self, file_content: bytes, version: str, manifest: dict) -> str:
        """保存模板文件并备份旧版本"""
        storage = self.config.get("storage", {})
        templates_dir = storage.get("templates_dir", "templates")
        template_filename = f"template_{version}.xlsx"
        template_path = os.path.join(templates_dir, template_filename)

        # 备份旧模板
        if manifest.get("current_template") and os.path.exists(
            manifest["current_template"]
        ):
            self._backup_template(manifest["current_template"])

        # 写入新模板
        with open(template_path, "wb") as f:
            f.write(file_content)

        return template_path

    def _get_latest_local_template(self, manifest: dict) -> str | None:
        """获取本地最新模板路径（支持多目录查找）"""
        current_template = manifest.get("current_template")

        if current_template and os.path.exists(current_template):
            return current_template

        # 获取搜索目录列表
        storage = self.config.get("storage", {})
        search_dirs = storage.get(
            "search_dirs", [storage.get("templates_dir", "templates")]
        )
        if isinstance(search_dirs, str):
            search_dirs = [search_dirs]

        allowed_ext = self.config.get("validation", {}).get(
            "allowed_extensions", [".xlsx", ".xlsm"]
        )

        # 按优先级遍历搜索目录
        for templates_dir in search_dirs:
            if not templates_dir or not os.path.exists(templates_dir):
                continue

            # 查找允许的扩展名文件
            templates = []
            for ext in allowed_ext:
                templates.extend(Path(templates_dir).glob(f"*{ext}"))

            if templates:
                # 返回按名称排序的第一个文件（确保可预测性）
                templates.sort(key=lambda p: p.name)
                return str(templates[0])

        return None

    def _backup_template(self, template_path: str):
        """备份模板文件"""
        storage = self.config.get("storage", {})
        backup_dir = storage.get("backup_dir", "templates/backups")
        max_backups = self.config.get("version", {}).get("max_backups", 5)

        # 生成备份文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(template_path)
        name, ext = os.path.splitext(filename)
        backup_filename = f"{name}_{timestamp}{ext}"
        backup_path = os.path.join(backup_dir, backup_filename)

        # 复制文件
        shutil.copy2(template_path, backup_path)
        info(f"  ✓ 备份旧模板: {backup_filename}")
        # 清理旧备份
        self._cleanup_old_backups(backup_dir, max_backups)

    def _cleanup_old_backups(self, backup_dir: str, max_keep: int):
        """清理旧备份，只保留最新的 max_keep 个"""
        backups = list(Path(backup_dir).glob("*.xlsx")) + list(
            Path(backup_dir).glob("*.xlsm")
        )

        if len(backups) <= max_keep:
            return

        # 按修改时间排序（最新的在前）
        backups.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        # 删除超出的旧备份
        for backup in backups[max_keep:]:
            backup.unlink()
            info(f"  ✓ 清理旧备份: {backup.name}")

    def _update_manifest(
        self, manifest: dict, template_path: str, version: str, downloaded: bool
    ):
        """更新 manifest 文件"""
        now = datetime.now().isoformat()

        # 更新当前状态
        manifest["current_version"] = version
        manifest["current_template"] = template_path
        manifest["last_update"] = now

        # 添加历史记录
        history_entry = {
            "timestamp": now,
            "version": version,
            "path": template_path,
            "action": "downloaded" if downloaded else "used_local",
        }
        manifest.setdefault("history", []).append(history_entry)

        # 只保留最近 50 条历史
        manifest["history"] = manifest["history"][-50:]

        # 保存 manifest
        storage = self.config.get("storage", {})
        manifest_file = storage.get("manifest_file", "templates/manifest.json")

        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, indent=2, fp=f)
