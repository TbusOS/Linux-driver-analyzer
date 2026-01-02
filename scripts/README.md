# 🔧 脚本目录

本目录包含项目的辅助脚本。

## 📜 脚本列表

| 脚本 | 说明 | 用法 |
|------|------|------|
| `analyze.sh` | 快速分析脚本 | `./analyze.sh driver.c [output.json]` |
| `view_json.py` | JSON结果查看器 | `python view_json.py result.json [--async]` |

## 🚀 快速使用

### analyze.sh

一键分析驱动代码：

```bash
./scripts/analyze.sh my_driver.c result.json
```

### view_json.py

命令行查看分析结果：

```bash
# 查看全部信息
python scripts/view_json.py result.json

# 只看异步处理函数
python scripts/view_json.py result.json --async

# 只看函数调用
python scripts/view_json.py result.json --calls
```

## 📋 选项说明

`view_json.py` 支持以下选项：

- `--all` - 显示全部信息（默认）
- `--funcs` - 只显示函数列表
- `--async` - 只显示异步处理函数
- `--calls` - 显示调用关系
- `--ops` - 显示操作结构体

