#!/bin/bash
# 一键启动脚本
set -e

echo "=== quark2torrent 一键启动 ==="
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3"
    exit 1
fi

# 检查依赖
echo "[1/3] 检查依赖..."
pip install -q -r requirements.txt

# 检查CDP连接
echo "[2/3] 检查Chrome调试端口..."
if ! curl -s http://127.0.0.1:9222/json > /dev/null 2>&1; then
    echo "错误: 无法连接Chrome调试端口9222"
    echo "请先用以下参数启动Chrome:"
    echo "  chrome --remote-debugging-port=9222"
    exit 1
fi

# 检查是否打开了夸克网盘
if ! curl -s http://127.0.0.1:9222/json | grep -q "pan.quark.cn"; then
    echo "错误: 浏览器中没有打开夸克网盘"
    echo "请在Chrome中打开 https://pan.quark.cn 并登录"
    exit 1
fi

echo "[3/3] 环境就绪!"
echo ""

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "用法: ./run.sh <文件夹fid> <输出目录名>"
    echo ""
    echo "获取fid方法: 在夸克网盘打开目标文件夹，复制地址栏中 #/list/all/ 后面的一串字符"
    exit 1
fi

python3 quark2torrent.py "$1" "$2"
