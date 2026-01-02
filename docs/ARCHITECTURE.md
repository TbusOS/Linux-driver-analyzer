# 🏗 架构设计文档

## 概述

Linux Driver Analyzer (LDA) 采用**分层可插拔**架构设计，核心理念是：

1. **多后端支持** - 可根据环境选择不同的分析后端
2. **知识库增强** - 将 Linux 内核领域知识与代码分析结合
3. **统一数据模型** - 不同后端产出统一格式的分析结果
4. **多输出方式** - 支持 JSON、Web、IDE 等多种输出形式

---

## 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Linux Driver Analyzer                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Input Layer                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Single File │  │ Multi-File  │  │ Directory   │  │ Git Repo    │         │
│  │ .c          │  │ .c + .h     │  │ drivers/    │  │ (future)    │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         └────────────────┴─────────────────┴────────────────┘                │
│                                    │                                         │
│  Backend Layer                     ▼                                         │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │                        Backend Selector                        │         │
│  │   根据环境和配置选择最优后端                                    │         │
│  └────────────────────────────────────────────────────────────────┘         │
│         │                    │                    │                          │
│         ▼                    ▼                    ▼                          │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                  │
│  │   Regex     │      │ TreeSitter  │      │   Clang     │                  │
│  │  Backend    │      │  Backend    │      │  Backend    │                  │
│  │             │      │             │      │             │                  │
│  │ • 快速      │      │ • 精确语法  │      │ • 完整语义  │                  │
│  │ • 无依赖    │      │ • 增量解析  │      │ • 类型推导  │                  │
│  │ • 容错性好  │      │ • 浏览器可用│      │ • 宏展开    │                  │
│  └──────┬──────┘      └──────┬──────┘      └──────┬──────┘                  │
│         │                    │                    │                          │
│         └────────────────────┴────────────────────┘                          │
│                              │                                               │
│  Analysis Layer              ▼                                               │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │                      Core Analyzer                             │         │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐   │         │
│  │  │  Symbol   │  │   Call    │  │  Struct   │  │   Async   │   │         │
│  │  │   Table   │  │   Graph   │  │ Relations │  │ Handlers  │   │         │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘   │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                              │                                               │
│  Knowledge Layer             ▼                                               │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │                    Knowledge Base                              │         │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐   │         │
│  │  │ USB驱动   │  │ 字符设备  │  │ 网络设备  │  │ 块设备    │   │         │
│  │  │ Framework │  │ Framework │  │ Framework │  │ Framework │   │         │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘   │         │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐   │         │
│  │  │ 中断处理  │  │ 工作队列  │  │ 定时器    │  │ 内核API   │   │         │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘   │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                              │                                               │
│  Output Layer                ▼                                               │
│  ┌────────────────────────────────────────────────────────────────┐         │
│  │                      Output Generator                          │         │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐   │         │
│  │  │   JSON    │  │   HTML    │  │  GraphViz │  │  VSCode   │   │         │
│  │  │  Export   │  │  Viewer   │  │  Export   │  │  Plugin   │   │         │
│  │  └───────────┘  └───────────┘  └───────────┘  └───────────┘   │         │
│  └────────────────────────────────────────────────────────────────┘         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 核心数据模型

### 1. 符号表 (Symbol Table)

```python
@dataclass
class Symbol:
    name: str
    kind: SymbolKind  # FUNCTION, STRUCT, TYPEDEF, VARIABLE, MACRO
    location: Location
    attributes: Dict[str, Any]

@dataclass
class SymbolTable:
    symbols: Dict[str, Symbol]
    
    def lookup(self, name: str) -> Optional[Symbol]
    def add(self, symbol: Symbol) -> None
    def get_by_kind(self, kind: SymbolKind) -> List[Symbol]
```

### 2. 函数定义 (Function)

```python
@dataclass
class Function:
    name: str
    return_type: str
    parameters: List[Parameter]
    body_range: Range
    attributes: List[str]  # static, inline, __init, __exit
    
    # 分析结果
    calls: List[str]           # 调用的函数
    called_by: List[str]       # 被谁调用
    uses_structs: List[str]    # 使用的结构体
    
    # 回调信息
    is_callback: bool
    callback_context: str      # 如 "usb_driver.probe"
    callback_trigger: str      # 如 "USB设备插入时调用"
```

### 3. 结构体定义 (Struct)

```python
@dataclass
class StructField:
    name: str
    type_name: str
    is_pointer: bool
    is_function_ptr: bool
    func_ptr_signature: Optional[str]
    offset: Optional[int]
    size: Optional[int]

@dataclass
class Struct:
    name: str
    fields: List[StructField]
    size: Optional[int]
    
    # 关系
    references: List[str]      # 引用的其他结构体
    referenced_by: List[str]   # 被谁引用
```

### 4. 调用图 (Call Graph)

```python
@dataclass
class CallEdge:
    caller: str
    callee: str
    location: Location
    is_direct: bool            # True: func(), False: ptr()

@dataclass
class CallGraph:
    nodes: Set[str]
    edges: List[CallEdge]
    
    def get_callees(self, func: str) -> List[str]
    def get_callers(self, func: str) -> List[str]
    def get_call_chain(self, from_func: str, to_func: str) -> List[str]
```

### 5. 分析结果 (AnalysisResult)

```python
@dataclass
class AnalysisResult:
    file: str
    symbols: SymbolTable
    functions: Dict[str, Function]
    structs: Dict[str, Struct]
    call_graph: CallGraph
    
    # 增强信息
    entry_points: List[EntryPoint]
    async_handlers: List[AsyncHandler]
    func_ptr_mappings: List[FuncPtrMapping]
    
    # 元数据
    analysis_time: float
    backend_used: str
    warnings: List[str]
```

---

## 后端接口

所有后端实现统一接口：

```python
class AnalysisBackend(ABC):
    """分析后端抽象基类"""
    
    @abstractmethod
    def name(self) -> str:
        """后端名称"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查后端是否可用"""
        pass
    
    @abstractmethod
    def analyze_file(self, filepath: str) -> AnalysisResult:
        """分析单个文件"""
        pass
    
    @abstractmethod
    def analyze_files(self, filepaths: List[str]) -> AnalysisResult:
        """分析多个文件"""
        pass
    
    def capabilities(self) -> Set[str]:
        """返回后端能力集"""
        return set()
```

### 后端能力对比

| 能力 | Regex | TreeSitter | Clang |
|------|-------|------------|-------|
| `PARSE_FUNCTIONS` | ✅ | ✅ | ✅ |
| `PARSE_STRUCTS` | ✅ | ✅ | ✅ |
| `PARSE_CALLS` | ✅ | ✅ | ✅ |
| `TYPE_INFERENCE` | ❌ | ⚠️ | ✅ |
| `MACRO_EXPANSION` | ❌ | ❌ | ✅ |
| `CROSS_FILE` | ❌ | ⚠️ | ✅ |
| `BROWSER_COMPATIBLE` | ✅ | ✅ | ❌ |
| `INCREMENTAL` | ❌ | ✅ | ⚠️ |

---

## 知识库设计

### 结构

```json
{
  "frameworks": {
    "usb_driver": {
      "description": "USB驱动框架",
      "header": "linux/usb.h",
      "callbacks": {
        "probe": {
          "trigger": "USB设备插入且ID匹配",
          "context": "进程上下文",
          "params": ["struct usb_interface *", "const struct usb_device_id *"],
          "return": "0成功，负数失败"
        }
      }
    }
  },
  "async_patterns": {
    "work_struct": {
      "init": ["INIT_WORK", "INIT_WORK_ONSTACK"],
      "trigger": ["schedule_work", "queue_work"],
      "context": "进程上下文，可睡眠"
    }
  },
  "kernel_apis": {
    "kzalloc": {
      "description": "分配并清零内存",
      "may_sleep": true,
      "params": ["size", "gfp_flags"]
    }
  }
}
```

### 扩展机制

用户可以添加自定义知识库：

```bash
# 使用自定义知识库
lda analyze driver.c --knowledge-base my_framework.json
```

---

## 可视化组件

### Web 可视化架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Visualization                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Call Flow  │  │   Struct     │  │   Timeline   │       │
│  │   Viewer     │  │   Viewer     │  │   Viewer     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│          │                │                │                 │
│          └────────────────┴────────────────┘                 │
│                           │                                  │
│                   ┌───────▼───────┐                          │
│                   │  Data Layer   │                          │
│                   │  (JSON API)   │                          │
│                   └───────────────┘                          │
│                                                              │
│  Features:                                                   │
│  • 响应式布局                                                │
│  • 深色/浅色主题                                             │
│  • 交互式展开/折叠                                           │
│  • 搜索和过滤                                                │
│  • 导出为图片                                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 扩展点

### 1. 添加新后端

```python
# src/backends/my_backend.py
from core.backend import AnalysisBackend

class MyBackend(AnalysisBackend):
    def name(self) -> str:
        return "my-backend"
    
    def analyze_file(self, filepath: str) -> AnalysisResult:
        # 实现分析逻辑
        pass

# 注册后端
BackendRegistry.register(MyBackend)
```

### 2. 添加新知识库条目

```json
// 在 knowledge_base.json 中添加
{
  "my_framework": {
    "description": "自定义框架",
    "callbacks": {
      "my_callback": {
        "trigger": "何时被调用",
        "context": "执行上下文"
      }
    }
  }
}
```

### 3. 添加新输出格式

```python
# src/output/graphviz.py
from core.output import OutputGenerator

class GraphvizGenerator(OutputGenerator):
    def generate(self, result: AnalysisResult) -> str:
        # 生成 DOT 格式
        pass
```

---

## 性能考虑

### 大文件处理

- 分块读取和处理
- 增量解析（tree-sitter）
- 结果缓存

### 多文件项目

- 并行分析
- 依赖排序
- 增量更新

### 内存优化

- 符号表使用字符串池
- 懒加载函数体
- LRU 缓存

---

## 安全考虑

- 输入验证：防止路径遍历
- 资源限制：限制分析时间和内存
- 沙箱：Web 版在浏览器沙箱中运行

---

*文档版本: 1.0*
*最后更新: 2024-01*

