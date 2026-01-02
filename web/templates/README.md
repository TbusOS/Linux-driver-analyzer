# 📄 HTML 模板

本目录包含可视化页面的 HTML 模板。

## 📋 文件列表

| 文件 | 说明 | 数据来源 |
|------|------|----------|
| `call_flow_viewer.html` | 函数调用流可视化 | `basic_analyzer.py` |
| `struct_viewer.html` | 结构体关系可视化 | `advanced_analyzer.py` |

## 🔗 使用的分析器

| 页面 | 推荐分析器 | JSON 字段 |
|------|------------|-----------|
| call_flow_viewer | basic_analyzer | `functions`, `async_handlers`, `call_tree` |
| struct_viewer | advanced_analyzer | `structs`, `functions`, `func_ptr_assignments` |

## 🎨 设计规范

### 配色方案

两个页面使用类似的深色主题：

```css
--bg-primary: #1e1e1e;      /* 主背景 */
--bg-secondary: #252526;    /* 次要背景 */
--accent-green: #3fb950;    /* 入口函数 */
--accent-blue: #58a6ff;     /* 内核API */
--accent-yellow: #d29922;   /* 用户函数 */
--accent-purple: #a371f7;   /* 引用关系 */
```

### 图例

| 颜色 | 含义 |
|------|------|
| 🟢 绿色 | 入口/回调函数 |
| 🔵 蓝色 | 内核 API（虚线边框） |
| 🟡 黄色 | 用户定义函数 |
| 🟣 紫色 | 引用/嵌套关系 |

## 📱 响应式设计

- 侧边栏：固定宽度 280px
- 主内容区：自适应
- 最小宽度：800px

