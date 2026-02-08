# DLD Config Tmp Plugin

配置模板下载插件 - 从远程API下载最新的配置模板

## 功能

从远程API下载最新的Excel模板文件，避免使用过时的本地模板。

**使用场景**:
- CI/CD流程中自动获取最新模板
- 确保团队使用统一版本的模板
- 避免手动更新模板文件

## 配置

```yaml
dld_configtmp:
  enable: false           # 默认禁用
  api_url: "https://api.example.com/templates/latest"
  timeout: 30             # 超时时间（秒）
  cache_dir: ".cache"     # 缓存目录
```

## 依赖

- **Level**: 0 (预处理层)
- **Dependencies**: 无
- **被依赖**: `config_parser`, `excel_writer`

在所有其他插件之前执行，确保使用最新模板。

## 命令行使用

```bash
# 使用本地模板（默认）
python main.py template.xlsx log.txt

# 启用API下载模板
python main.py --download-template log.txt

# 指定API URL
python main.py --api-url https://custom.api.com/template log.txt

# 查看缓存的模板
ls .cache/
```

## API要求

### 请求格式

```http
GET /templates/latest HTTP/1.1
Host: api.example.com
```

### 响应格式

```json
{
    "version": "1.2.3",
    "url": "https://cdn.example.com/template_v1.2.3.xlsx",
    "checksum": "sha256:abc123...",
    "updated_at": "2026-02-09T10:00:00Z"
}
```

### 或直接返回文件

```http
HTTP/1.1 200 OK
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Length: 12345

<binary xlsx data>
```

## 与其他插件的配合

### 工作流位置

```
[dld_configtmp] → config_parser → excel_writer → ...
       ↓
   下载模板
   (可选)
```

### 典型使用场景

**场景1: CI/CD流程**
```bash
#!/bin/bash
# 自动化构建脚本
python main.py --download-template config.log
```

**场景2: 定期更新**
```bash
# 每天凌晨更新模板
0 0 * * * python main.py --download-template --cache-dir /data/templates
```

**场景3: 开发环境**
```bash
# 开发时使用本地模板
python main.py local_template.xlsx log.txt
```

### 配合示例

```yaml
# config/ci_config.yaml
dld_configtmp:
  enable: true
  api_url: "${TEMPLATE_API_URL}"  # 从环境变量读取
  cache_dir: "/tmp/templates"

excel_writer:
  enable: true
  # 使用下载的模板
```

## 缓存机制

### 缓存策略

1. **首次下载**: 从API下载并保存到缓存
2. **后续使用**: 检查缓存是否过期
3. **过期更新**: 自动下载新版本

### 缓存结构

```
.cache/
├── template_v1.2.3.xlsx
├── template_v1.2.4.xlsx
└── metadata.json
```

### metadata.json

```json
{
    "current_version": "1.2.4",
    "downloaded_at": "2026-02-09T10:00:00Z",
    "checksum": "sha256:abc123..."
}
```

## 示例输出

```
[模板下载] 检查模板更新...
  → API: https://api.example.com/templates/latest
  ✓ 发现新版本: v1.2.4 (当前: v1.2.3)
  → 下载中... [=========>] 100%
  ✓ 校验成功: sha256:abc123...
  ✓ 模板已更新: .cache/template_v1.2.4.xlsx

[配置解析] 使用模板: .cache/template_v1.2.4.xlsx
```

## 安全考虑

### HTTPS

始终使用HTTPS API：

```yaml
api_url: "https://secure.example.com/templates"  # ✓ 安全
# 避免: "http://..."  # ✗ 不安全
```

### 校验和验证

启用checksum验证：

```yaml
verify_checksum: true  # 默认启用
```

### 超时设置

避免长时间等待：

```yaml
timeout: 30  # 30秒超时
```

## 错误处理

### API不可用

```
⚠️  API不可用: https://api.example.com/templates
  → 使用缓存模板: .cache/template_v1.2.3.xlsx
```

### 下载失败

```
⚠️  下载失败: Connection timeout
  → 回退到本地模板: template.xlsx
```

### 校验失败

```
✗ 校验失败: checksum不匹配
  → 删除损坏的文件，使用缓存版本
```

## 常见问题

**Q: API需要认证怎么办？**
A: 在配置中添加认证信息：
```yaml
api_headers:
  Authorization: "Bearer ${API_TOKEN}"
```

**Q: 如何强制重新下载？**
A: 删除缓存目录或使用 `--force-download` 选项。

**Q: 下载的模板保存在哪里？**
A: 默认保存在 `.cache/` 目录，可通过 `cache_dir` 配置修改。

**Q: 如何在离线环境使用？**
A: 禁用此插件，使用本地模板文件：
```yaml
dld_configtmp:
  enable: false
```
