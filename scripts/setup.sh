#!/bin/bash
# ============================================
# Linux Driver Analyzer - 一键安装脚本
# ============================================
#
# 支持系统: Ubuntu, Debian, macOS, 其他 Linux
#
# 默认行为: 自动创建虚拟环境并安装（推荐）
#
# 使用方法:
#   ./scripts/setup.sh              # 推荐安装（自动创建虚拟环境）
#   ./scripts/setup.sh --minimal    # 最小安装（无 tree-sitter）
#   ./scripts/setup.sh --dev        # 开发环境
#   ./scripts/setup.sh --no-venv    # 不使用虚拟环境（不推荐）
#   ./scripts/setup.sh --help       # 显示帮助
#
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 获取项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 默认配置 - 默认使用虚拟环境
INSTALL_MODE="recommended"
USE_VENV=true
VENV_DIR="$PROJECT_DIR/.venv"

# 帮助信息
show_help() {
    echo ""
    echo -e "${CYAN}Linux Driver Analyzer - 一键安装脚本${NC}"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "安装模式:"
    echo "  --minimal     最小安装（仅正则后端，无额外依赖）"
    echo "  --recommended 推荐安装（包含 tree-sitter，默认）"
    echo "  --dev         开发环境（包含测试和代码检查工具）"
    echo ""
    echo "环境选项:"
    echo "  --no-venv     不使用虚拟环境（不推荐，可能遇到权限问题）"
    echo "  --venv-dir    指定虚拟环境目录（默认: .venv）"
    echo ""
    echo "其他:"
    echo "  --help        显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                    # 推荐安装（自动创建虚拟环境）"
    echo "  $0 --dev              # 开发环境安装"
    echo "  $0 --minimal          # 最小安装"
    echo ""
    echo -e "${YELLOW}注意: 默认会创建虚拟环境，这是跨平台最可靠的方式${NC}"
    echo ""
}

# 解析参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --minimal)
                INSTALL_MODE="minimal"
                shift
                ;;
            --recommended)
                INSTALL_MODE="recommended"
                shift
                ;;
            --dev)
                INSTALL_MODE="dev"
                shift
                ;;
            --no-venv)
                USE_VENV=false
                shift
                ;;
            --venv-dir)
                VENV_DIR="$2"
                shift 2
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                echo -e "${RED}未知参数: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done
}

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/debian_version ]; then
            OS="debian"
            OS_NAME="Ubuntu/Debian"
        elif [ -f /etc/redhat-release ]; then
            OS="redhat"
            OS_NAME="CentOS/RHEL"
        else
            OS="linux"
            OS_NAME="Linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        OS_NAME="macOS"
    else
        OS="unknown"
        OS_NAME="Unknown"
    fi
    echo -e "${BLUE}📍 操作系统: $OS_NAME${NC}"
}

# 检查 Python
check_python() {
    echo -e "${BLUE}🔍 检查 Python...${NC}"
    
    # 尝试不同的 Python 命令
    for cmd in python3 python; do
        if command -v $cmd &> /dev/null; then
            PY_VERSION=$($cmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
            PY_MAJOR=$($cmd -c 'import sys; print(sys.version_info.major)')
            PY_MINOR=$($cmd -c 'import sys; print(sys.version_info.minor)')
            
            if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 8 ]; then
                PYTHON_CMD="$cmd"
                echo -e "${GREEN}   ✓ Python $PY_VERSION${NC}"
                return 0
            fi
        fi
    done
    
    echo -e "${RED}❌ 未找到 Python 3.8+${NC}"
    echo ""
    echo "请先安装 Python:"
    case $OS in
        debian)
            echo -e "  ${YELLOW}sudo apt update && sudo apt install python3 python3-pip python3-venv${NC}"
            ;;
        redhat)
            echo -e "  ${YELLOW}sudo yum install python3 python3-pip${NC}"
            ;;
        macos)
            echo -e "  ${YELLOW}brew install python${NC}"
            ;;
        *)
            echo "  请从 https://python.org 下载安装"
            ;;
    esac
    exit 1
}

# 设置虚拟环境
setup_venv() {
    if [ "$USE_VENV" = true ]; then
        echo -e "${BLUE}📦 设置虚拟环境...${NC}"
        
        if [ -d "$VENV_DIR" ]; then
            echo -e "${YELLOW}   虚拟环境已存在: $VENV_DIR${NC}"
        else
            echo -e "   创建虚拟环境: $VENV_DIR"
            $PYTHON_CMD -m venv "$VENV_DIR"
            echo -e "${GREEN}   ✓ 虚拟环境创建成功${NC}"
        fi
        
        # 激活虚拟环境
        source "$VENV_DIR/bin/activate"
        PYTHON_CMD="python"
        PIP_CMD="pip"
        echo -e "${GREEN}   ✓ 虚拟环境已激活${NC}"
    else
        echo -e "${YELLOW}⚠️  不使用虚拟环境（可能遇到权限问题）${NC}"
        PIP_CMD="$PYTHON_CMD -m pip"
    fi
}

# 安装项目
install_project() {
    echo -e "${BLUE}📥 安装 Linux Driver Analyzer...${NC}"
    
    cd "$PROJECT_DIR"
    
    # 升级 pip
    $PIP_CMD install --upgrade pip -q 2>/dev/null || true
    
    case $INSTALL_MODE in
        minimal)
            echo -e "   模式: ${CYAN}最小安装${NC}（正则后端 + pytest）"
            $PIP_CMD install ".[test]" -q
            ;;
        recommended)
            echo -e "   模式: ${CYAN}推荐安装${NC}（tree-sitter + pytest）"
            $PIP_CMD install ".[recommended]" -q
            ;;
        dev)
            echo -e "   模式: ${CYAN}开发环境${NC}（全部工具）"
            $PIP_CMD install -e ".[dev]" -q
            ;;
    esac
    
    echo -e "${GREEN}   ✓ 安装完成${NC}"
}

# 验证安装
verify_install() {
    echo -e "${BLUE}🔬 验证安装...${NC}"
    
    cd "$PROJECT_DIR"
    
    RESULT=$($PYTHON_CMD -c "
import sys
sys.path.insert(0, 'src')
from backends import get_backend, list_backends

backends = list_backends()
backend = get_backend()
print(f'{backends}|{backend.name}|{backend.version}')
" 2>&1) || {
        echo -e "${RED}   ❌ 安装验证失败！${NC}"
        exit 1
    }
    
    IFS='|' read -r BACKENDS DEFAULT_NAME DEFAULT_VERSION <<< "$RESULT"
    echo -e "${GREEN}   ✓ 可用后端: $BACKENDS${NC}"
    echo -e "${GREEN}   ✓ 默认后端: $DEFAULT_NAME v$DEFAULT_VERSION${NC}"
}

# 创建激活脚本
create_activate_script() {
    if [ "$USE_VENV" = true ]; then
        ACTIVATE_SCRIPT="$PROJECT_DIR/activate.sh"
        cat > "$ACTIVATE_SCRIPT" << 'EOF'
#!/bin/bash
# 激活 Linux Driver Analyzer 虚拟环境
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/.venv/bin/activate"
echo "✓ 虚拟环境已激活"
echo "  使用 'deactivate' 退出虚拟环境"
EOF
        chmod +x "$ACTIVATE_SCRIPT"
    fi
}

# 打印使用说明
print_usage() {
    echo ""
    echo -e "${BLUE}============================================${NC}"
    echo -e "${GREEN}🎉 安装完成！${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo ""
    
    if [ "$USE_VENV" = true ]; then
        echo -e "${CYAN}【重要】使用前请先激活虚拟环境:${NC}"
        echo ""
        echo -e "  ${YELLOW}source $VENV_DIR/bin/activate${NC}"
        echo ""
        echo -e "  或使用快捷方式:"
        echo -e "  ${YELLOW}source ./activate.sh${NC}"
        echo ""
        echo -e "  退出虚拟环境:"
        echo -e "  ${YELLOW}deactivate${NC}"
        echo ""
        echo -e "${BLUE}--------------------------------------------${NC}"
    fi
    
    echo ""
    echo "快速使用:"
    echo ""
    echo "  1. 分析驱动代码:"
    echo -e "     ${YELLOW}python src/core/basic_analyzer.py your_driver.c -o result.json${NC}"
    echo ""
    echo "  2. 使用后端 API:"
    echo -e "     ${YELLOW}python -c \"from backends import get_backend; print(get_backend().name)\"${NC}"
    echo ""
    echo "  3. 运行测试:"
    echo -e "     ${YELLOW}make test${NC}"
    echo ""
    echo "  4. 查看更多命令:"
    echo -e "     ${YELLOW}make help${NC}"
    echo ""
}

# 主流程
main() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║   Linux Driver Analyzer - 一键安装         ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
    echo ""
    
    parse_args "$@"
    detect_os
    check_python
    setup_venv
    install_project
    verify_install
    create_activate_script
    print_usage
}

main "$@"
