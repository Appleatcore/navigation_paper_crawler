#!/bin/bash
# Navigation Paper Crawler - 运行脚本
# 用法: ./run.sh [config_file]

set -e

CONFIG_FILE="${1:-config.local.json}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

# 加载环境变量
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# 激活虚拟环境（如果存在）
if [ -d .venv ]; then
    source .venv/bin/activate
elif [ -d venv ]; then
    source venv/bin/activate
fi

# 检查配置文件
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ 配置文件不存在: $CONFIG_FILE"
    echo "请先复制 config.template.json 为 config.local.json 并填写配置"
    exit 1
fi

# 运行爬虫
echo "=========================================="
echo "Navigation Paper Crawler - 开始运行"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "配置: $CONFIG_FILE"
echo "日志: $SCRIPT_DIR/paper_crawler.log"
echo "=========================================="

python3 paper_crawler.py "$CONFIG_FILE"

echo ""
echo "=========================================="
echo "✅ 运行完成"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""
echo "查看详细日志: tail -f paper_crawler.log"
