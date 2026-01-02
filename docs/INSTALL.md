# 📦 安装指南

本文档提供 Linux Driver Analyzer 在各平台的详细安装说明。

## 📋 系统要求

- **Python**: 3.8 或更高版本
- **操作系统**: Linux、macOS、Windows

## 🚀 快速安装（推荐）

使用一键脚本安装，自动创建虚拟环境，**跨平台通用**：

```bash
# 克隆项目
git clone https://github.com/yourusername/linux-driver-analyzer.git
cd linux-driver-analyzer

# 一键安装（自动创建虚拟环境）
./scripts/setup.sh

# 激活环境
source .venv/bin/activate

# 开始使用
python src/core/basic_analyzer.py your_driver.c -o result.json
```

> 💡 **为什么使用虚拟环境？**
> - 跨平台一致（Ubuntu、macOS、Windows 都能工作）
> - 避免权限问题（macOS 的 Homebrew Python 默认禁止直接 pip install）
> - 隔离依赖（不污染系统 Python）

### 其他安装方式

**使用 Makefile:**

```bash
# 需要先激活虚拟环境
python3 -m venv .venv && source .venv/bin/activate

make install        # 推荐安装
make install-min    # 最小安装
make install-dev    # 开发环境
```

## 📱 各平台详细说明

### Ubuntu / Debian

```bash
# 1. 安装 Python
sudo apt update
sudo apt install python3 python3-pip python3-venv

# 2. 克隆并安装
git clone https://github.com/yourusername/linux-driver-analyzer.git
cd linux-driver-analyzer
./scripts/setup.sh

# 3. 激活环境后使用
source .venv/bin/activate
```

### CentOS / RHEL / Fedora

```bash
# 1. 安装 Python
sudo yum install python3 python3-pip  # CentOS/RHEL
sudo dnf install python3 python3-pip  # Fedora

# 2. 克隆并安装
git clone https://github.com/yourusername/linux-driver-analyzer.git
cd linux-driver-analyzer
./scripts/setup.sh
source .venv/bin/activate
```

### macOS

```bash
# 1. 安装 Python（使用 Homebrew）
brew install python

# 2. 克隆并安装
git clone https://github.com/yourusername/linux-driver-analyzer.git
cd linux-driver-analyzer
./scripts/setup.sh

# 3. 激活环境后使用
source .venv/bin/activate
```

> ⚠️ **注意**: macOS Homebrew 的 Python 默认禁止直接 pip install（PEP 668），所以**必须使用虚拟环境**。安装脚本会自动创建虚拟环境，无需手动处理。

### Windows (PowerShell)

```powershell
# 1. 从 https://python.org 下载安装 Python 3.8+
#    安装时勾选 "Add Python to PATH"

# 2. 克隆项目
git clone https://github.com/yourusername/linux-driver-analyzer.git
cd linux-driver-analyzer

# 3. 创建虚拟环境并安装
python -m venv .venv
.venv\Scripts\Activate
pip install ".[recommended]"
```

## 📦 安装选项

| 命令 | 说明 |
|------|------|
| `pip install .` | 最小安装，仅正则后端 |
| `pip install ".[recommended]"` | 推荐安装，包含 tree-sitter |
| `pip install ".[dev]"` | 开发环境，包含测试工具 |
| `pip install ".[full]"` | 完整安装 |
| `pip install -e ".[dev]"` | 可编辑安装（开发用） |

## ✅ 验证安装

```bash
# 方法 1: 使用 make
make verify

# 方法 2: Python 命令
python -c "
import sys
sys.path.insert(0, 'src')
from backends import get_backend, list_backends
print(f'可用后端: {list_backends()}')
print(f'默认后端: {get_backend().name}')
"
```

预期输出：

```
可用后端: ['regex', 'tree-sitter']
默认后端: tree-sitter
```

## 🧪 运行测试

```bash
# 运行所有测试
make test

# 或直接使用 pytest
python -m pytest tests/ -v
```

## ❓ 常见问题

### Q: 遇到 `externally-managed-environment` 错误

这是 Python 3.11+ 的新安全机制。解决方案：

```bash
# 使用虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate
pip install ".[recommended]"

# 或添加 --user 标志
pip install --user ".[recommended]"
```

### Q: tree-sitter 安装失败

tree-sitter 需要编译 C 扩展，确保系统有编译工具：

```bash
# Ubuntu/Debian
sudo apt install build-essential

# macOS
xcode-select --install

# CentOS/RHEL
sudo yum groupinstall "Development Tools"
```

### Q: 如何更新到最新版本？

```bash
cd linux-driver-analyzer
git pull
pip install ".[recommended]" --upgrade
```

### Q: 如何卸载？

```bash
pip uninstall linux-driver-analyzer
```

## 🔗 相关链接

- [项目主页](../README.md)
- [开发路线图](ROADMAP.md)
- [贡献指南](CONTRIBUTING.md)

