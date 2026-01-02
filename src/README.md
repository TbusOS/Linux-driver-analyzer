# 🔬 源代码目录

本目录包含 Linux Driver Analyzer 的核心源代码。

## 📁 目录结构

```
src/
├── core/           # 核心分析模块
│   ├── basic_analyzer.py      # 基础分析器
│   ├── advanced_analyzer.py   # 高级分析器
│   └── knowledge_base.json    # Linux内核知识库
│
├── backends/       # 可插拔解析后端
│   ├── base.py                # 后端抽象基类
│   ├── regex_backend.py       # 正则匹配后端 (v0.1)
│   ├── treesitter_backend.py  # tree-sitter 后端 (v0.2) ✅
│   └── (clang_backend.py)     # libclang 后端 (计划中)
│
└── visualizers/    # 可视化生成器（规划中）
    └── (HTML生成器等)
```

## 🚀 快速使用

### 使用新的后端 API（推荐）

```python
from backends import get_backend, list_backends

# 查看可用后端
print(list_backends())  # ['regex', 'tree-sitter']

# 自动选择最佳后端
backend = get_backend()
result = backend.parse_file('driver.c')

# 或指定后端
backend = get_backend('tree-sitter')
result = backend.parse(source_code)

# 访问解析结果
for name, func in result.functions.items():
    print(f"{name}: 调用了 {len(func.calls)} 个函数")

for name, struct in result.structs.items():
    print(f"{name}: 有 {len(struct.fields)} 个字段")
```

### 使用命令行

```bash
# 基础分析
python src/core/basic_analyzer.py driver.c -o result.json

# 高级分析（包含结构体）
python src/core/advanced_analyzer.py driver.c --structs -o result.json
```

## 🔧 核心模块

### backends/ - 可插拔后端

支持多种解析后端，可按需选择：

| 后端 | 精确度 | 依赖 | 状态 |
|------|--------|------|------|
| regex | ⭐⭐ | 无 | ✅ 完成 |
| tree-sitter | ⭐⭐⭐⭐ | tree-sitter | ✅ 完成 |
| clang | ⭐⭐⭐⭐⭐ | libclang | 📅 计划 |

```python
from backends import RegexBackend, TreeSitterBackend

# 正则后端（无依赖，速度快）
regex = RegexBackend()

# tree-sitter 后端（精确解析）
ts = TreeSitterBackend()
```

### core/basic_analyzer.py

基础分析器，使用正则表达式进行代码分析：

- 函数定义识别
- 函数调用提取
- 回调函数映射
- 异步机制识别（工作队列、定时器、中断等）

### core/advanced_analyzer.py

高级分析器，增加了结构体分析能力：

- 结构体定义解析
- 字段类型推断
- 结构体嵌套关系
- 函数指针赋值追踪

### core/knowledge_base.json

Linux内核知识库，包含：

- 驱动框架定义（usb_driver, platform_driver 等）
- 回调函数时机说明
- 异步机制上下文信息

## 🗺️ 版本历史

- [x] v0.1: 基础分析器 + 正则后端
- [x] v0.2: tree-sitter 后端 + 可插拔架构
- [ ] v0.3: libclang 后端（计划中）
- [ ] v0.4: 跨文件分析支持（计划中）
