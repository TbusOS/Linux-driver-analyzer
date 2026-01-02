#!/bin/bash
# 激活 Linux Driver Analyzer 虚拟环境
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/.venv/bin/activate"
echo "✓ 虚拟环境已激活"
echo "  使用 'deactivate' 退出虚拟环境"
