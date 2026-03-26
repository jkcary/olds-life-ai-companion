@echo off
cd /d "%~dp0backend"
set PYTHONIOENCODING=utf-8
python -m uvicorn app.main:app --port 8000
