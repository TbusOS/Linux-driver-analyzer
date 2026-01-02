# 🔬 源代码目录

本目录包含 Linux Driver Analyzer 的核心源代码。

## 📁 目录结构

```
src/
├── core/           # 核心分析模块
│   ├── basic_analyzer.py      # 基础分析器（正则匹配）
│   ├── advanced_analyzer.py   # 高级分析器（结构体分析）
│   └── knowledge_base.json    # Linux内核知识库
│
├── backends/       # 解析后端（规划中）
│   └── (tree-sitter, libclang 后端)
│
└── visualizers/    # 可视化生成器（规划中）
    └── (HTML生成器等)
```

## 🔧 核心模块

### basic_analyzer.py

基础分析器，使用正则表达式进行代码分析：

- 函数定义识别
- 函数调用提取
- 回调函数映射
- 异步机制识别（工作队列、定时器、中断等）

```bash
python src/core/basic_analyzer.py driver.c -o result.json
```

### advanced_analyzer.py

高级分析器，增加了结构体分析能力：

- 结构体定义解析
- 字段类型推断
- 结构体嵌套关系
- 函数指针赋值追踪

```bash
python src/core/advanced_analyzer.py driver.c --structs -o result.json
```

### knowledge_base.json

Linux内核知识库，包含：

- 驱动框架定义（usb_driver, platform_driver 等）
- 回调函数时机说明
- 异步机制上下文信息

## 🗺️ 开发计划

- [ ] v0.2: 添加 tree-sitter 后端
- [ ] v0.3: 添加 libclang 后端
- [ ] v0.4: 跨文件分析支持

