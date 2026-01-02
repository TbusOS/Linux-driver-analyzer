# 🌐 Web 可视化

本目录包含 LDA 的 Web 可视化界面。

## 📁 目录结构

```
web/
├── templates/        # HTML 页面模板
│   ├── call_flow_viewer.html    # 函数调用流可视化
│   └── struct_viewer.html       # 结构体关系可视化
│
├── css/              # 样式文件（规划中）
│   └── (抽取公共样式)
│
└── js/               # JavaScript 文件（规划中）
    └── (抽取公共逻辑)
```

## 🚀 使用方式

### 方式1：本地服务器

```bash
cd linux-driver-analyzer
python -m http.server 8080

# 浏览器访问
# http://localhost:8080/web/templates/call_flow_viewer.html
# http://localhost:8080/web/templates/struct_viewer.html
```

### 方式2：直接打开

```bash
open web/templates/call_flow_viewer.html
```

> 注意：直接打开时，"选择示例"功能可能因跨域限制无法使用

## 📊 页面说明

### call_flow_viewer.html

**函数调用流可视化**

功能：
- 📤 导入分析结果 JSON
- 💡 加载内置示例
- 🔍 搜索函数
- 📂 展开/折叠调用树
- 📊 显示分析摘要
- ⚡ 异步处理函数列表

### struct_viewer.html

**结构体关系可视化**

功能：
- 📊 概览 - 分析摘要
- 📦 结构体图 - 结构体关系
- 🔗 调用图 - 多层调用树
- ⚡ 回调映射 - 函数指针映射

## 🎨 技术栈

- **纯 HTML/CSS/JavaScript** - 无框架依赖
- **SVG** - 图形渲染
- **CSS Variables** - 主题支持
- **Fetch API** - JSON 加载

## 🗺️ 开发计划

- [ ] 抽取公共 CSS 到 `css/` 目录
- [ ] 抽取公共 JS 到 `js/` 目录
- [ ] 添加深色/浅色主题切换
- [ ] 支持导出为图片/PDF
- [ ] 添加更多交互功能

