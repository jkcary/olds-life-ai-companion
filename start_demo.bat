@echo off
chcp 65001 >nul
echo.
echo =================================================
echo   银龄AI伴伴 v1.1 MVP Demo (Windows)
echo =================================================
echo.

cd /d "%~dp0backend"

REM 检查 .env
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo [WARN] 已创建 .env 文件，请用记事本填入 ANTHROPIC_API_KEY：
    echo        路径: %~dp0backend\.env
    echo.
    notepad ".env"
    pause
    exit /b 1
)

REM 安装依赖
echo [..] 安装依赖...
python -m pip install -r requirements.txt -q --disable-pip-version-check
echo [OK] 依赖就绪

REM 运行测试
echo [..] 运行单元测试...
python -m pytest tests/ --ignore=tests/test_integration.py -q
echo [OK] 测试通过

REM 启动服务
echo.
echo [>>] 启动服务器...
echo      Demo 体验: http://localhost:8000/demo
echo      API 文档:  http://localhost:8000/docs
echo.
set PYTHONIOENCODING=utf-8
python -m uvicorn app.main:app --port 8000 --log-level info

pause
