# ============================================
# Linux Driver Analyzer - Makefile
# ============================================
#
# 使用方法（无需手动激活虚拟环境）:
#   make setup    - 首次安装
#   make test     - 运行测试
#   make demo     - 运行示例
#   make help     - 显示帮助
#
# ============================================

.PHONY: help setup install install-min install-dev test lint format clean venv

# 虚拟环境目录
VENV_DIR := .venv
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip

# 自动使用虚拟环境中的 Python（如果存在）
ifneq ($(wildcard $(VENV_PYTHON)),)
    PYTHON := $(VENV_PYTHON)
    PIP := $(VENV_PIP)
else
    PYTHON := python3
    PIP := $(PYTHON) -m pip
endif

# 颜色
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
CYAN := \033[0;36m
NC := \033[0m

help:
	@echo ""
	@echo "$(BLUE)╔════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║   Linux Driver Analyzer - 命令帮助         ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)【首次使用】$(NC)"
	@echo "  $(GREEN)make setup$(NC)        一键安装环境"
	@echo ""
	@echo "$(YELLOW)【常用命令】无需手动激活虚拟环境$(NC)"
	@echo "  $(GREEN)make test$(NC)         运行所有测试"
	@echo "  $(GREEN)make demo$(NC)         运行示例分析"
	@echo "  $(GREEN)make analyze F=xxx.c$(NC)  分析文件（自动用最佳后端）"
	@echo "  $(GREEN)make backends$(NC)     查看可用后端"
	@echo ""
	@echo "$(YELLOW)【开发命令】$(NC)"
	@echo "  $(GREEN)make lint$(NC)         代码检查"
	@echo "  $(GREEN)make format$(NC)       代码格式化"
	@echo "  $(GREEN)make clean$(NC)        清理缓存"
	@echo ""
	@echo "$(YELLOW)【示例】$(NC)"
	@echo "  $(CYAN)make setup && make test$(NC)"
	@echo "  $(CYAN)make analyze F=examples/usb_serial/usb_serial_example.c$(NC)"
	@echo ""

# 一键安装
setup:
	@echo "$(BLUE)一键安装 Linux Driver Analyzer...$(NC)"
	@./scripts/setup.sh
	@echo ""
	@echo "$(GREEN)✓ 安装完成！现在可以直接使用:$(NC)"
	@echo "  $(YELLOW)make test$(NC)     - 运行测试"
	@echo "  $(YELLOW)make demo$(NC)     - 运行示例"
	@echo "  $(YELLOW)make help$(NC)     - 查看更多命令"

# 推荐安装（包含 tree-sitter）
install:
	@echo "$(BLUE)安装 Linux Driver Analyzer（推荐配置）...$(NC)"
	$(PIP) install ".[recommended]"
	@echo "$(GREEN)✓ 安装完成！$(NC)"
	@echo ""
	@$(PYTHON) -c "import sys; sys.path.insert(0, 'src'); from backends import list_backends; print(f'可用后端: {list_backends()}')"

# 最小安装
install-min:
	@echo "$(BLUE)安装 Linux Driver Analyzer（最小配置）...$(NC)"
	$(PIP) install .
	@echo "$(GREEN)✓ 安装完成！$(NC)"

# 开发环境安装
install-dev:
	@echo "$(BLUE)安装 Linux Driver Analyzer（开发配置）...$(NC)"
	$(PIP) install -e ".[dev]"
	@echo "$(GREEN)✓ 开发环境安装完成！$(NC)"

# 运行测试
test:
	@echo "$(BLUE)运行测试...$(NC)"
	$(PYTHON) -m pytest tests/ -v

# 运行特定测试
test-backends:
	@echo "$(BLUE)运行后端测试...$(NC)"
	$(PYTHON) -m pytest tests/test_backends.py -v

test-basic:
	@echo "$(BLUE)运行基础分析器测试...$(NC)"
	$(PYTHON) -m pytest tests/test_basic_analyzer.py -v

# 代码检查
lint:
	@echo "$(BLUE)代码检查...$(NC)"
	$(PYTHON) -m flake8 src/ --max-line-length=100 --ignore=E501,W503
	$(PYTHON) -m mypy src/ --ignore-missing-imports || true

# 代码格式化
format:
	@echo "$(BLUE)代码格式化...$(NC)"
	$(PYTHON) -m black src/ tests/
	$(PYTHON) -m isort src/ tests/

# 运行示例
demo:
	@echo "$(BLUE)运行示例分析...$(NC)"
	@if [ -f "examples/async_demo/async_demo_example.c" ]; then \
		$(PYTHON) src/core/basic_analyzer.py examples/async_demo/async_demo_example.c -o demo_result.json; \
		echo "$(GREEN)✓ 分析完成，结果保存在 demo_result.json$(NC)"; \
	else \
		echo "示例文件不存在，请检查 examples/ 目录"; \
	fi

# 分析指定文件（使用新后端）- make analyze F=your_driver.c
analyze:
ifndef F
	@echo "$(YELLOW)用法: make analyze F=<文件路径> [B=后端]$(NC)"
	@echo ""
	@echo "示例:"
	@echo "  make analyze F=driver.c              # 自动选择最佳后端"
	@echo "  make analyze F=driver.c B=tree-sitter"
	@echo "  make analyze F=driver.c B=regex"
else
	@echo "$(BLUE)分析文件: $(F)$(NC)"
ifdef B
	@$(PYTHON) src/core/analyzer.py $(F) -b $(B) -o analysis_result.json
else
	@$(PYTHON) src/core/analyzer.py $(F) -o analysis_result.json
endif
	@echo "$(GREEN)✓ 结果保存在 analysis_result.json$(NC)"
endif

# 列出可用后端
backends:
	@$(PYTHON) -c "import sys; sys.path.insert(0, 'src'); from backends import list_backends, get_backend; print('可用后端:', list_backends()); b = get_backend(); print(f'默认后端: {b.name} v{b.version}')"

# v0.1 vs v0.2 功能对比
demo-compare:
	@echo "$(BLUE)v0.1 vs v0.2 功能对比测试$(NC)"
	@$(PYTHON) -c "\
import sys; \
sys.path.insert(0, 'src'); \
from backends import get_backend; \
file = 'examples/advanced_features/advanced_driver.c'; \
regex = get_backend('regex'); \
r1 = regex.parse_file(file); \
ts = get_backend('tree-sitter'); \
r2 = ts.parse_file(file); \
print(); \
print('| 特性 | v0.1 (regex) | v0.2 (tree-sitter) | 提升 |'); \
print('|------|-------------|-------------------|------|'); \
print(f'| 函数 | {len(r1.functions)} 个 | {len(r2.functions)} 个 | +{len(r2.functions) - len(r1.functions)} |'); \
print(f'| 结构体 | {len(r1.structs)} 个 | {len(r2.structs)} 个 | +{len(r2.structs) - len(r1.structs)} |'); \
print(f'| 枚举 | {len(r1.enums)} 个 | {len(r2.enums)} 个 | +{len(r2.enums)} ✨ |'); \
print(f'| 联合体 | {len(r1.unions)} 个 | {len(r2.unions)} 个 | +{len(r2.unions)} ✨ |'); \
print(); \
print('枚举:', list(r2.enums.keys())); \
print('联合体:', list(r2.unions.keys())); \
"

# 验证安装
verify:
	@echo "$(BLUE)验证安装...$(NC)"
	@$(PYTHON) -c "\
import sys; \
sys.path.insert(0, 'src'); \
from backends import get_backend, list_backends; \
print(f'可用后端: {list_backends()}'); \
b = get_backend(); \
print(f'默认后端: {b.name} v{b.version}'); \
print('✓ 安装验证通过')"

# 清理
clean:
	@echo "$(BLUE)清理缓存文件...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ 2>/dev/null || true
	@echo "$(GREEN)✓ 清理完成$(NC)"

# 构建发布包
build:
	@echo "$(BLUE)构建发布包...$(NC)"
	$(PYTHON) -m build
	@echo "$(GREEN)✓ 构建完成，查看 dist/ 目录$(NC)"

