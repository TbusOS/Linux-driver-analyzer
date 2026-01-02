#!/bin/bash
#
# Linux Driver Analyzer - 快速分析脚本
#
# 用法:
#   ./scripts/analyze.sh <driver.c> [output.json]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# 检查参数
if [ $# -lt 1 ]; then
    echo "用法: $0 <driver.c> [output.json]"
    echo ""
    echo "示例:"
    echo "  $0 my_driver.c"
    echo "  $0 my_driver.c result.json"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="${2:-analysis_result.json}"

# 检查输入文件
if [ ! -f "$INPUT_FILE" ]; then
    echo "错误: 文件不存在: $INPUT_FILE"
    exit 1
fi

echo "🔬 Linux Driver Analyzer"
echo "========================"
echo ""
echo "📄 输入文件: $INPUT_FILE"
echo "📊 输出文件: $OUTPUT_FILE"
echo ""

# 运行分析
echo "⏳ 正在分析..."
python3 "$PROJECT_DIR/src/core/advanced_analyzer.py" "$INPUT_FILE" --structs -o "$OUTPUT_FILE"

echo ""
echo "✅ 分析完成！"
echo ""
echo "📖 查看结果:"
echo "   1. 直接查看 JSON: cat $OUTPUT_FILE"
echo "   2. 在浏览器中可视化: open $PROJECT_DIR/web/templates/call_flow_viewer.html"
echo "      然后导入 $OUTPUT_FILE"

