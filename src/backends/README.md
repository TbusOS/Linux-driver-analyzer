# 🔌 解析后端

本目录存放不同的代码解析后端实现，采用可插拔架构设计。

## 📋 后端状态

| 后端 | 版本 | 精确度 | 依赖 | 状态 |
|------|------|--------|------|------|
| regex | v0.1 | ⭐⭐ | 无 | ✅ 已完成 |
| tree-sitter | v0.2 | ⭐⭐⭐⭐ | tree-sitter, tree-sitter-c | ✅ 已完成 |
| libclang | v0.3 | ⭐⭐⭐⭐⭐ | libclang | 📅 计划中 |

## 🚀 快速使用

```python
from backends import get_backend, list_backends

# 查看可用后端
print(list_backends())  # ['regex', 'tree-sitter']

# 获取最佳可用后端（优先级: clang > tree-sitter > regex）
backend = get_backend()

# 或指定后端
backend = get_backend('tree-sitter')

# 解析代码
result = backend.parse(source_code)

# 访问解析结果
for name, func in result.functions.items():
    print(f"{name}: {len(func.calls)} calls")
```

## 📁 文件结构

```
backends/
├── __init__.py           # 模块入口，提供 get_backend 等接口
├── base.py               # 抽象基类和数据结构定义
├── regex_backend.py      # 正则匹配后端
├── treesitter_backend.py # tree-sitter 后端
└── README.md             # 本文档
```

## 🔧 正则后端 (RegexBackend)

### 特点

- ✅ 无外部依赖，使用纯 Python 标准库
- ✅ 速度快，容错性好
- ✅ 适合快速预览
- ⚠️ 可能被复杂注释/字符串干扰

### 使用

```python
from backends import RegexBackend

backend = RegexBackend()
result = backend.parse(source_code)
```

## 🌳 Tree-sitter 后端 (TreeSitterBackend)

### 特点

- ✅ 基于真实语法树，精确解析
- ✅ 不受注释/字符串干扰
- ✅ 精确的位置信息（行号、列号）
- ✅ 支持增量解析
- ✅ 可编译为 WASM 在浏览器运行

### 安装依赖

```bash
pip install tree-sitter tree-sitter-c
```

### 使用

```python
from backends import TreeSitterBackend, is_treesitter_available

if is_treesitter_available():
    backend = TreeSitterBackend()
    result = backend.parse(source_code)
```

## 🔧 libclang 后端 (计划中)

### 特点

- 完整的语义分析
- 类型推导和宏展开
- 理解 typedef 和复杂类型

### 依赖

```bash
pip install libclang
```

### 注意事项

需要正确的头文件路径和编译选项才能工作。

## 📝 后端接口规范

所有后端继承 `AnalyzerBackend` 抽象基类：

```python
from backends.base import AnalyzerBackend, BackendCapability, ParseResult

class MyBackend(AnalyzerBackend):
    @property
    def name(self) -> str:
        return "my-backend"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def is_available(self) -> bool:
        """检查依赖是否可用"""
        return True
    
    def capabilities(self) -> set:
        """返回支持的能力"""
        return {
            BackendCapability.PARSE_FUNCTIONS,
            BackendCapability.PARSE_STRUCTS,
        }
    
    def parse(self, source_code: str, filename: str = "<string>") -> ParseResult:
        """解析源代码，返回 ParseResult"""
        result = ParseResult()
        # ... 解析逻辑
        return result

# 注册后端
from backends.base import BackendRegistry
BackendRegistry.register(MyBackend)
```

## 📊 能力对比

| 能力 | Regex | TreeSitter | Clang |
|------|-------|------------|-------|
| PARSE_FUNCTIONS | ✅ | ✅ | ✅ |
| PARSE_STRUCTS | ✅ | ✅ | ✅ |
| PARSE_CALLS | ✅ | ✅ | ✅ |
| PARSE_TYPEDEFS | ✅ | ✅ | ✅ |
| TYPE_INFERENCE | ❌ | ⚠️ | ✅ |
| MACRO_EXPANSION | ❌ | ❌ | ✅ |
| CROSS_FILE | ❌ | ⚠️ | ✅ |
| BROWSER_COMPATIBLE | ✅ | ✅ | ❌ |
| INCREMENTAL | ❌ | ✅ | ⚠️ |

## 🧪 测试

```bash
# 运行后端测试
pytest tests/test_backends.py -v

# 只测试 regex 后端
pytest tests/test_backends.py::TestRegexBackend -v

# 测试 tree-sitter 后端（需要安装依赖）
pytest tests/test_backends.py::TestTreeSitterBackend -v
```


