# 🗺 开发路线图 (ROADMAP)

本文档详细描述了 Linux Driver Analyzer 项目的开发计划和里程碑。

---

## 📅 版本规划概览

```
Timeline
─────────────────────────────────────────────────────────────────────────────────
2024 Q1          2024 Q2          2024 Q3          2024 Q4          2025 Q1
    │                │                │                │                │
    ▼                ▼                ▼                ▼                ▼
┌───────┐      ┌───────┐      ┌───────┐      ┌───────┐      ┌───────┐
│ v0.1  │ ──▶  │ v0.2  │ ──▶  │ v0.3  │ ──▶  │ v0.4  │ ──▶  │ v1.0  │
│ 基础  │      │ 语法  │      │ 语义  │      │ 跨文件│      │ IDE   │
│ 分析  │      │ 解析  │      │ 分析  │      │ 分析  │      │ 集成  │
└───────┘      └───────┘      └───────┘      └───────┘      └───────┘
    ✅              🚧              📅              📅              📅
```

---

## 🏁 v0.1 - 基础分析 (当前版本) ✅

**目标**: 验证核心概念，提供基本可用的分析能力

### 已完成功能

#### 核心分析
- [x] 正则匹配提取函数定义
- [x] 正则匹配提取函数调用
- [x] 结构体定义解析
- [x] 结构体字段解析
- [x] 函数指针赋值追踪（ops表）
- [x] 结构体关系分析

#### 异步机制识别
- [x] 工作队列 (INIT_WORK)
- [x] 延迟工作 (INIT_DELAYED_WORK)
- [x] Tasklet (tasklet_init)
- [x] 定时器 (timer_setup)
- [x] 高精度定时器 (hrtimer_init)
- [x] 中断处理 (request_irq)
- [x] 线程化中断 (request_threaded_irq)
- [x] 内核线程 (kthread_run)

#### 知识库
- [x] USB驱动框架
- [x] 字符设备框架
- [x] TTY驱动框架
- [x] 平台驱动框架
- [x] I2C/SPI驱动框架
- [x] 网络设备框架
- [x] 常用内核API说明

#### 可视化
- [x] 函数调用流展示
- [x] 入口点分组显示
- [x] 展开/折叠交互
- [x] 搜索功能
- [x] 结构体关系图（基础）

### 已知限制
- 不支持宏展开
- 不支持跨文件分析
- 复杂的函数指针场景可能遗漏
- 正则匹配可能误判

---

## ✅ v0.2 - Tree-sitter 后端 (已完成)

**目标**: 使用tree-sitter实现精确的语法解析

### 已完成功能

#### 1. Tree-sitter 集成 ✅

```python
# 实现的接口
from backends import get_backend, TreeSitterBackend

backend = get_backend('tree-sitter')
result = backend.parse(source_code)

# 访问解析结果
for name, func in result.functions.items():
    print(f"{name}: {len(func.calls)} calls")
```

**完成的任务:**
- [x] 集成 tree-sitter Python 绑定
- [x] 实现函数提取
- [x] 实现结构体提取
- [x] 实现调用提取
- [x] 精确的位置信息（行号、列号）
- [x] 可插拔后端架构
- [x] 后端注册机制
- [ ] 处理预处理器指令（部分支持）
- [ ] 性能优化（增量解析）（待优化）

#### 2. 增强的语法分析

- [x] union 支持 ✅
- [x] enum 支持 ✅
- [x] 函数声明识别 ✅
- [x] 数组类型支持 ✅
- [x] 函数指针类型解析 ✅
- [ ] 完整的类型解析（待优化）
- [ ] 嵌套结构体支持（部分支持）

#### 3. 浏览器端运行

```javascript
// 目标：在浏览器中直接分析代码
import Parser from 'web-tree-sitter';

const parser = new Parser();
await parser.setLanguage(await Parser.Language.load('tree-sitter-c.wasm'));
const tree = parser.parse(sourceCode);
```

**任务分解:**
- [ ] 编译 tree-sitter-c 为 WASM
- [ ] 实现 JavaScript 分析器
- [ ] 集成到 Web 界面
- [ ] 实时代码分析
- [ ] 语法高亮

#### 4. 可视化增强

- [ ] 更精确的行号显示
- [ ] 代码片段预览
- [ ] 点击跳转到代码
- [ ] 差异对比视图

### 技术实现

**安装 tree-sitter:**
```bash
pip install tree-sitter
pip install tree-sitter-c
```

**查询示例:**
```scheme
; 查询所有函数定义
(function_definition
  type: (_) @return_type
  declarator: (function_declarator
    declarator: (identifier) @function_name
    parameters: (parameter_list) @params)
  body: (compound_statement) @body)

; 查询所有结构体定义
(struct_specifier
  name: (type_identifier) @struct_name
  body: (field_declaration_list) @fields)
```

### 预计完成时间
- 开始：2024 Q1
- 目标完成：2024 Q2

---

## 📅 v0.3 - libclang 后端

**目标**: 对于有编译环境的用户，提供完整的语义分析能力

### 计划功能

#### 1. libclang 集成

```python
# 目标接口
class ClangBackend:
    def __init__(self, compile_commands: str):
        """加载编译数据库"""
        
    def analyze_file(self, filepath: str) -> AnalysisResult:
        """完整的语义分析"""
        
    def resolve_type(self, node) -> Type:
        """类型推导"""
        
    def expand_macros(self, code: str) -> str:
        """宏展开"""
```

**任务分解:**
- [ ] 集成 libclang Python 绑定
- [ ] 支持 compile_commands.json
- [ ] 实现类型推导
- [ ] 实现宏展开
- [ ] 处理内核头文件

#### 2. 编译数据库生成

```bash
# 为内核模块生成 compile_commands.json
lda-generate-compdb -C /lib/modules/$(uname -r)/build M=$(pwd)
```

**任务分解:**
- [ ] Bear 工具集成
- [ ] 手动生成脚本
- [ ] 内核模块专用模板

#### 3. 精确类型分析

- [ ] 函数指针类型匹配
- [ ] typedef 展开
- [ ] 结构体完整成员
- [ ] 宏定义值

#### 4. 高级功能

- [ ] 未使用代码检测
- [ ] 死代码分析
- [ ] API 使用检查
- [ ] 代码复杂度分析

### 预计完成时间
- 开始：2024 Q2
- 目标完成：2024 Q3

---

## 📅 v0.4 - 跨文件分析

**目标**: 支持分析完整的驱动模块（多文件）

### 计划功能

#### 1. 项目级分析

```bash
# 分析整个目录
lda analyze drivers/usb/serial/ -o project_analysis.json

# 指定入口文件
lda analyze --entry main_driver.c drivers/my_driver/
```

**任务分解:**
- [ ] 多文件加载
- [ ] 头文件解析
- [ ] 符号表合并
- [ ] 依赖关系分析

#### 2. 跨文件调用追踪

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  main.c     │ ───▶ │  usb.c      │ ───▶ │  tty.c      │
│  init()     │      │  probe()    │      │  write()    │
└─────────────┘      └─────────────┘      └─────────────┘
```

- [ ] 跨文件函数调用
- [ ] 全局变量追踪
- [ ] 头文件依赖图

#### 3. 模块化可视化

- [ ] 文件级视图
- [ ] 模块级视图
- [ ] 分层展示

#### 4. 增量分析

- [ ] 文件变更检测
- [ ] 增量重新分析
- [ ] 缓存机制

### 预计完成时间
- 开始：2024 Q3
- 目标完成：2024 Q4

---

## 📅 v1.0 - VSCode 集成

**目标**: 将分析能力集成到开发者日常使用的IDE中

### 计划功能

#### 1. VSCode 扩展

```
┌─────────────────────────────────────────────────────────────┐
│  VSCode                                                      │
├──────────────────┬──────────────────────────────────────────┤
│  Explorer        │  Editor                                   │
│  ─────────────   │  ────────────────────────────────         │
│  📁 drivers/     │  static int my_probe(...) {              │
│    📄 main.c     │      ...                                  │
│    📄 usb.c      │  }                                        │
│                  │                                           │
│  ─────────────   ├──────────────────────────────────────────┤
│  🔬 LDA Panel    │  Call Flow                                │
│  ─────────────   │  ────────────────                         │
│  📊 Call Graph   │  🔌 my_probe()                           │
│  📦 Structures   │    ├── kzalloc()                         │
│  ⚡ Callbacks    │    ├── usb_alloc_urb()                   │
│                  │    └── dev_info()                        │
└──────────────────┴──────────────────────────────────────────┘
```

**任务分解:**
- [ ] VSCode 扩展框架
- [ ] 侧边栏面板
- [ ] 代码高亮集成
- [ ] 悬浮提示 (hover)
- [ ] 跳转支持 (go to definition)

#### 2. 实时分析

- [ ] 文件保存时自动分析
- [ ] 后台分析线程
- [ ] 结果缓存

#### 3. 交互功能

- [ ] 右键菜单
- [ ] 快捷键支持
- [ ] 面包屑导航
- [ ] 调用层级视图

#### 4. 配置界面

- [ ] 分析后端选择
- [ ] 知识库配置
- [ ] 排除文件设置

### 预计完成时间
- 开始：2024 Q4
- 目标完成：2025 Q1

---

## 🔮 未来愿景 (v2.0+)

### 高级功能

- **AI 辅助分析**
  - 使用 LLM 解释代码逻辑
  - 自动生成代码注释
  - 异常模式检测

- **动态分析集成**
  - ftrace 数据导入
  - 运行时数据与静态分析对比
  - 性能热点标注

- **协作功能**
  - 分析结果分享
  - 团队知识库
  - 代码审查集成

### 更多语言支持

- Rust (for Linux)
- 设备树 (DTS)
- Kconfig

### 更多框架支持

- eBPF 程序
- 内核模块依赖
- 用户空间驱动 (UIO/VFIO)

---

## 📊 进度追踪

### 当前状态

| 组件 | 状态 | 进度 |
|------|------|------|
| 核心分析器 | ✅ 完成 | 100% |
| 正则后端 | ✅ 完成 | 100% |
| 知识库 | ✅ 基础完成 | 80% |
| Web可视化 | ✅ 基础完成 | 70% |
| tree-sitter | ✅ 完成 | 100% |
| 后端架构 | ✅ 完成 | 100% |
| libclang | 📅 计划 | 0% |
| 跨文件分析 | 📅 计划 | 0% |
| VSCode扩展 | 📅 计划 | 0% |

### 里程碑

- [x] **M1**: 概念验证 - 基础分析可用 (2024-01)
- [x] **M2**: tree-sitter 集成 (2026-01) ✅
- [ ] **M3**: libclang 集成 (目标: 2026-Q2)
- [ ] **M4**: 跨文件分析 (目标: 2026-Q3)
- [ ] **M5**: VSCode 扩展 Beta (目标: 2026-Q4)
- [ ] **M6**: v1.0 正式发布 (目标: 2027-Q1)

---

## 🤝 如何参与

### 优先级任务

1. **高优先级**
   - tree-sitter 集成
   - 完善测试用例
   - 文档完善

2. **中优先级**
   - 更多知识库条目
   - Web 界面优化
   - 性能优化

3. **探索性**
   - libclang 后端原型
   - VSCode 扩展原型

### 联系方式

- GitHub Issues: 提交 bug 和 feature request
- Discussions: 讨论设计和想法
- Pull Requests: 贡献代码

---

*最后更新: 2024-01*

