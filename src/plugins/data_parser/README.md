# 16进制数据解析器插件 (data_parser)

用于解析16进制格式的数据，支持灵活的字段定义和多种数据类型。

## 功能特性

- ✅ **多种格式支持**: 空格分隔 (`1A 02 FF`) 或紧凑格式 (`1A02FF`)
- ✅ **灵活的字段定义**: 通过配置文件定义数据结构
- ✅ **多种数据类型**: uint8, uint16, uint32, hex, string
- ✅ **大小端支持**: 支持big-endian和little-endian
- ✅ **值映射**: 将数值映射为有意义的名称
- ✅ **数据验证**: 可选的header和checksum验证
- ✅ **从日志提取**: 支持从日志文件中提取16进制数据
- ✅ **JSON报告**: 自动生成结构化的JSON报告

## 配置示例

### 基本配置 (config.yaml)

```yaml
enable: true

# 数据源配置
source:
  type: "log_file"  # 或 "direct"
  pattern: "DATA:\\s*([0-9A-Fa-f\\s]+)"  # 日志匹配正则
  format: "spaced"  # "spaced" 或 "compact"

# 字段定义
fields:
  - name: "header"
    offset: 0
    length: 1
    type: "uint8"
    description: "数据包头"

  - name: "length"
    offset: 1
    length: 2
    type: "uint16"
    endian: "big"
    description: "数据长度"

  - name: "cmd"
    offset: 3
    length: 1
    type: "uint8"
    description: "命令类型"

  - name: "data"
    offset: 4
    length: 4
    type: "hex"
    description: "数据内容"

# 值映射
value_mapping:
  cmd:
    0x01: "READ"
    0x02: "WRITE"
    0x03: "STATUS"
```

## 使用方法

### 方式1: 直接解析16进制字符串

```python
from src.plugins.data_parser.plugin import DataParserPlugin

# 创建插件实例
plugin = DataParserPlugin()

# 准备上下文
context = {
    "hex_data": "AA 00 05 01 1A 2B 3C 4D"
}

# 执行解析
result = plugin.execute(context)

# 查看结果
print(result["parsed_data"])
# [
#   {
#     "index": 0,
#     "header": 170,  # 0xAA
#     "length": 5,
#     "cmd": 1,
#     "cmd_name": "READ",
#     "data": "1A 2B 3C 4D"
#   }
# ]
```

### 方式2: 从日志文件提取并解析

日志文件示例 (`device.log`):
```
[2024-01-15 10:30:15] Device connected
[2024-01-15 10:30:16] DATA: AA 00 05 01 1A 2B 3C 4D
[2024-01-15 10:30:17] DATA: BB 00 03 02 FF EE DD
[2024-01-15 10:30:18] Device disconnected
```

代码:
```python
context = {
    "trace_file": "device.log"
}

result = plugin.execute(context)
# 自动提取并解析所有匹配的16进制数据
```

## 数据类型说明

| 类型 | 长度 | 说明 | 示例 |
|------|------|------|------|
| `uint8` | 1字节 | 无符号8位整数 | `0xFF` → 255 |
| `uint16` | 2字节 | 无符号16位整数 | `0x01 0x02` → 258 (big) |
| `uint32` | 4字节 | 无符号32位整数 | `0x01 0x02 0x03 0x04` → 16909060 (big) |
| `hex` | 可变 | 16进制字符串 | `0x1A 0x2B` → "1A 2B" |
| `string` | 可变 | ASCII字符串 | `0x41 0x42 0x43` → "ABC" |

## 偏移量表达式

- **整数**: `offset: 0` - 从第0字节开始
- **end-N**: `offset: "end-1"` - 倒数第1个字节（常用于checksum）

## 应用场景

### 1. 串口协议解析
```yaml
fields:
  - name: "start"
    offset: 0
    length: 1
    type: "uint8"  # 起始符 0xAA

  - name: "addr"
    offset: 1
    length: 1
    type: "uint8"  # 设备地址

  - name: "cmd"
    offset: 2
    length: 1
    type: "uint8"  # 命令码

  - name: "data"
    offset: 3
    length: 8
    type: "hex"  # 数据区

  - name: "checksum"
    offset: "end-1"
    length: 1
    type: "uint8"  # 校验和
```

### 2. 网络包解析
```yaml
fields:
  - name: "magic"
    offset: 0
    length: 2
    type: "uint16"
    endian: "big"

  - name: "version"
    offset: 2
    length: 1
    type: "uint8"

  - name: "packet_type"
    offset: 3
    length: 1
    type: "uint8"

  - name: "payload_length"
    offset: 4
    length: 2
    type: "uint16"
    endian: "big"

  - name: "payload"
    offset: 6
    length: 16
    type: "hex"
```

### 3. 硬件寄存器数据
```yaml
fields:
  - name: "status_reg"
    offset: 0
    length: 4
    type: "uint32"
    endian: "little"

  - name: "error_code"
    offset: 4
    length: 2
    type: "uint16"
    endian: "little"

  - name: "timestamp"
    offset: 6
    length: 4
    type: "uint32"
    endian: "little"
```

## 输出示例

JSON报告 (`output/data_parsed.json`):
```json
{
  "total_count": 2,
  "parsed_count": 2,
  "success_rate": 1.0,
  "data": [
    {
      "index": 0,
      "raw_hex": "AA 00 05 01 1A 2B 3C 4D",
      "raw_bytes": 8,
      "header": 170,
      "length": 5,
      "cmd": 1,
      "cmd_name": "READ",
      "data": "1A 2B 3C 4D"
    },
    {
      "index": 1,
      "raw_hex": "BB 00 03 02 FF EE DD",
      "raw_bytes": 7,
      "header": 187,
      "length": 3,
      "cmd": 2,
      "cmd_name": "WRITE",
      "data": "FF EE DD"
    }
  ],
  "raw_data": [
    "AA 00 05 01 1A 2B 3C 4D",
    "BB 00 03 02 FF EE DD"
  ]
}
```

## 测试

运行测试:
```bash
pytest tests/plugins/data_parser/test_parser.py -v
```

测试覆盖:
- ✅ 多种数据类型解析
- ✅ 大小端转换
- ✅ 边界条件处理
- ✅ 无效数据处理
- ✅ 日志提取
- ✅ 报告生成
- ✅ 大数据集处理

29个测试全部通过 ✅
