#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# 银龄AI伴伴 — 一键启动 Demo
# 用法: bash start_demo.sh
# ─────────────────────────────────────────────────────────
set -e

BACKEND_DIR="$(cd "$(dirname "$0")/backend" && pwd)"

echo ""
echo "================================================="
echo "  银龄AI伴伴 v1.1 MVP Demo"
echo "================================================="
echo ""

# 1. 检查 Python
if ! command -v python &>/dev/null && ! command -v python3 &>/dev/null; then
  echo "[ERROR] 未找到 Python，请安装 Python 3.12+"
  exit 1
fi
PYTHON=$(command -v python3 || command -v python)
echo "[OK] Python: $($PYTHON --version)"

# 2. 检查 .env
if [ ! -f "$BACKEND_DIR/.env" ]; then
  cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
  echo "[WARN] 已创建 .env 文件，请填入 ANTHROPIC_API_KEY 后重新运行"
  echo "       文件位置: $BACKEND_DIR/.env"
  exit 1
fi

# 3. 检查 API Key
source "$BACKEND_DIR/.env" 2>/dev/null || true
if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "your_anthropic_api_key_here" ]; then
  echo "[ERROR] 请在 $BACKEND_DIR/.env 中填入真实的 ANTHROPIC_API_KEY"
  echo "        获取方式: https://console.anthropic.com/settings/keys"
  exit 1
fi
echo "[OK] ANTHROPIC_API_KEY 已配置"

# 4. 安装依赖
echo "[..] 检查 Python 依赖..."
cd "$BACKEND_DIR"
$PYTHON -m pip install -r requirements.txt -q --disable-pip-version-check
echo "[OK] 依赖已就绪"

# 5. 运行单元测试
echo "[..] 运行单元测试..."
$PYTHON -m pytest tests/ --ignore=tests/test_integration.py -q
echo "[OK] 所有单元测试通过"

# 6. 启动服务器
echo ""
echo "[>>] 启动服务器..."
echo "     API 文档: http://localhost:8000/docs"
echo "     Demo 体验: http://localhost:8000/demo"
echo ""
echo "     按 Ctrl+C 停止服务"
echo ""

PYTHONIOENCODING=utf-8 $PYTHON -m uvicorn app.main:app --port 8000 --log-level info
