# 🔌 解析后端

本目录用于存放不同的代码解析后端实现。

## 📋 规划中的后端

| 后端 | 版本 | 精确度 | 依赖 | 状态 |
|------|------|--------|------|------|
| 正则匹配 | v0.1 | ⭐⭐ | 无 | ✅ 已完成 |
| tree-sitter | v0.2 | ⭐⭐⭐⭐ | py-tree-sitter | 🚧 规划中 |
| libclang | v0.3 | ⭐⭐⭐⭐⭐ | python-clang | 📅 计划中 |

## 🌳 tree-sitter 后端 (v0.2)

### 优势

- 精确的语法树解析
- 不会被注释/字符串干扰
- 无需编译环境
- 可编译为 WASM 在浏览器运行

### 安装依赖

```bash
pip install tree-sitter tree-sitter-c
```

### 示例代码

```python
import tree_sitter_c as tsc
from tree_sitter import Language, Parser

parser = Parser(Language(tsc.language()))
tree = parser.parse(bytes(code, 'utf8'))

# 遍历语法树
def visit(node):
    if node.type == 'function_definition':
        name = node.child_by_field_name('declarator')
        print(f"Found function: {name.text.decode()}")
    for child in node.children:
        visit(child)
```

## 🔧 libclang 后端 (v0.3)

### 优势

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

所有后端需要实现统一接口：

```python
class AnalyzerBackend:
    def parse(self, source_code: str) -> AST:
        """解析源代码，返回抽象语法树"""
        pass
    
    def find_functions(self, ast: AST) -> List[FunctionDef]:
        """从AST中提取函数定义"""
        pass
    
    def find_structs(self, ast: AST) -> List[StructDef]:
        """从AST中提取结构体定义"""
        pass
```

