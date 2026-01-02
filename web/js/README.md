# 📜 JavaScript 脚本

本目录用于存放公共 JavaScript 文件。

## 📋 规划中的文件

| 文件 | 说明 |
|------|------|
| `analyzer-loader.js` | JSON 数据加载和解析 |
| `graph-renderer.js` | 图形渲染引擎 |
| `tree-view.js` | 树形视图组件 |
| `search.js` | 搜索功能 |
| `export.js` | 导出功能（图片/PDF） |

## 🎯 设计目标

从 HTML 模板中抽取公共逻辑，实现：

- 代码复用
- 模块化设计
- 更好的可测试性

## 📝 当前状态

JavaScript 目前内联在各 HTML 文件中，待抽取。

## 🔮 未来规划

考虑引入轻量级框架或工具：

- **构建工具**: esbuild / vite
- **类型检查**: TypeScript
- **图形库**: D3.js / Cytoscape.js


