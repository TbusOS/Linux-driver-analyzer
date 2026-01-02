# 示例代码与分析结果

本目录包含示例驱动代码及其分析结果，方便快速了解 Linux Driver Analyzer 的功能。

## 📁 目录结构

```
examples/
├── async_demo/                   # 异步机制演示
│   ├── async_demo_example.c      # 源代码
│   ├── basic_analysis.json       # 基础分析结果
│   ├── advanced_analysis.json    # 高级分析结果
│   └── README.md                 # 详细说明
│
├── usb_serial/                   # USB串口驱动
│   ├── usb_serial_example.c      # 源代码
│   ├── basic_analysis.json       # 基础分析结果
│   ├── advanced_analysis.json    # 高级分析结果
│   └── README.md                 # 详细说明
│
└── README.md                     # 本文件
```

## 🔍 示例概览

| 示例 | 代码行数 | 核心知识点 | 分析特色 |
|------|----------|-----------|---------|
| [async_demo](async_demo/) | 320 | 工作队列、Tasklet、定时器、中断 | 异步机制识别、执行上下文分析 |
| [usb_serial](usb_serial/) | 467 | USB驱动、TTY接口、URB传输 | 回调映射、数据流分析 |

## 🚀 快速体验

### 方式1：在线查看 JSON

直接打开 `*_analysis.json` 文件，JSON 格式清晰可读：

```json
{
  "functions": [...],
  "callbacks": [...],
  "async_handlers": [...],
  "call_graph": [...]
}
```

### 方式2：可视化查看

```bash
# 启动本地服务器
cd /path/to/linux-driver-analyzer
python -m http.server 8080

# 浏览器打开
# 函数调用流：http://localhost:8080/web/templates/call_flow_viewer.html
# 结构体关系：http://localhost:8080/web/templates/struct_viewer.html

# 导入对应的 JSON 文件即可
```

### 方式3：命令行重新分析

```bash
# 使用基础分析器
python src/core/basic_analyzer.py examples/async_demo/async_demo_example.c

# 使用高级分析器（包含结构体分析）
python src/core/advanced_analyzer.py examples/usb_serial/usb_serial_example.c --structs
```

## 📊 分析器对比

| 特性 | basic_analyzer | advanced_analyzer |
|------|----------------|-------------------|
| 函数识别 | ✅ | ✅ |
| 调用关系 | ✅ | ✅ |
| 回调映射 | ✅ | ✅ |
| 异步机制 | ✅ 详细 | ⚪ 基础 |
| 结构体分析 | ❌ | ✅ 详细 |
| 字段类型推断 | ❌ | ✅ |
| 函数参数解析 | ❌ | ✅ |
| 跨文件分析 | ❌ | ❌ (规划中) |

## 🆕 添加新示例

1. 创建新目录：
```bash
mkdir examples/my_driver
```

2. 复制源代码：
```bash
cp /path/to/my_driver.c examples/my_driver/
```

3. 运行分析：
```bash
python src/core/basic_analyzer.py examples/my_driver/my_driver.c \
    -o examples/my_driver/basic_analysis.json

python src/core/advanced_analyzer.py examples/my_driver/my_driver.c \
    --structs -o examples/my_driver/advanced_analysis.json
```

4. 创建 README.md 说明文件

## 📝 贡献示例

欢迎贡献更多驱动示例！理想的示例应该：

- [ ] 代码简洁，便于理解
- [ ] 展示特定驱动模式或内核机制
- [ ] 包含注释说明关键逻辑
- [ ] 能够体现分析器的能力

提交 PR 时请包含：
- 源代码文件
- 分析结果 JSON
- README.md 说明文档

