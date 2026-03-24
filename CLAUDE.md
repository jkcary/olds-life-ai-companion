# 银龄AI伴伴 — 项目开发指南

## 项目概述

AI 原生移动应用后端，面向中国老年人市场。每个功能模块都由 Claude API 驱动，而非传统规则引擎。

## 技术栈

- **后端**: Python 3.12 + FastAPI + SQLAlchemy (async)
- **AI 核心**: Anthropic SDK (`anthropic`)，主力模型 `claude-opus-4-6`
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **通信**: SSE 流式输出

## 目录结构

```
backend/
├── app/
│   ├── core/           # AI 核心：Claude客户端、工具注册、流式响应、系统提示词
│   ├── modules/
│   │   ├── companion/  # 情感陪伴（流式聊天 + 记忆工具）
│   │   ├── health/     # 健康医疗（adaptive thinking + 药物工具）
│   │   └── safety/     # 安全防护（两阶段检测 + 结构化输出）
│   ├── api/            # FastAPI 路由
│   ├── db/             # 数据库 schema 和会话
│   ├── config.py       # 环境配置
│   └── main.py         # 应用入口
├── requirements.txt
└── .env.example
```

## 快速启动

```bash
cd backend
cp .env.example .env
# 编辑 .env 填入 ANTHROPIC_API_KEY

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档

## AI 原生设计原则

1. **Claude 是决策引擎**，不是文本生成器
   - 所有业务判断（症状分析、诈骗识别、情绪检测）由 Claude 完成
   - Python 代码只做工具调用和 IO 处理

2. **模型分层策略**
   - `claude-opus-4-6`: 情感对话、健康问诊（复杂推理）
   - `claude-haiku-4-5`: 内容审核初筛、快速分类（低延迟）

3. **Adaptive Thinking**
   - 健康问诊强制开启 `thinking: {type: "adaptive"}`
   - 高风险诈骗分析开启 adaptive thinking
   - 普通聊天不开启（降低延迟和成本）

4. **流式优先**
   - 所有面向用户的聊天接口使用 SSE 流式输出
   - 避免老人等待超过 3 秒

5. **结构化输出**
   - 防诈骗检测、内容审核使用 `output_config.format` 保证 JSON 格式

## 工具设计规范

在 `app/core/tool_registry.py` 中新增工具时：
- `description` 要详细，Claude 靠描述决定何时调用
- 参数尽量使用 `enum` 约束，减少 Claude 的猜测
- 工具名采用 `动词_名词` 格式

## 测试 API

```bash
# 情感陪伴（流式）
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test001", "message": "今天天气真好，我去公园散步了"}'

# 健康问诊（流式）
curl -X POST http://localhost:8000/api/v1/health/consult/stream \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test001", "message": "我最近膝盖有点疼，上楼梯很困难"}'

# 防诈骗检测
curl -X POST http://localhost:8000/api/v1/safety/fraud/check \
  -H "Content-Type: application/json" \
  -d '{"content": "您好，我是公安局的，您的银行账户涉嫌洗钱，需要配合调查，请立即转账到安全账户"}'
```
