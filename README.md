# 夕阳伴侣·银龄AI伴伴

**产品需求文档（PRD）v2.0**

面向中国老年人市场的 AI 驱动移动应用 | Android & iOS 双平台

---

## 项目简介

"夕阳伴侣·银龄AI伴伴"定位为中国老年人的"AI生活管家"，通过大型语言模型（LLM）技术驱动，以情感陪伴为核心，覆盖老年人社交、健康、娱乐、出行、购物五大生活场景。

## 文档信息

| 项目 | 内容 |
|------|------|
| 文档编号 | PRD-SILV-2026-001 |
| 版本号 | V2.0 |
| 文档状态 | 正式版（需求冻结） |
| 产品负责人 | 张伟（产品总监） |
| 最后更新 | 2026年3月24日 |
| 适用平台 | Android 8.0+ / iOS 14.0+ |

## 核心功能模块

| 功能模块 | 优先级 | 迭代版本 |
|----------|--------|----------|
| 情感陪伴（AI聊天、心情日记） | P0 | V1.0 |
| 社交交友（兴趣圈子、找老朋友） | P0 | V1.0 |
| 健康医疗（AI问诊、用药提醒、SOS急救） | P0 | V1.0 |
| 生活分享（Vlog一键录制） | P1 | V1.1 |
| 文娱兴趣（K歌、听书） | P1 | V1.1 |
| 出行出游（AI语音找路、老年旅游） | P1 | V1.1 |
| 生活购物（老年专属商城、防诈骗） | P2 | V2.0 |

## 商业目标

- **短期（18个月）**：注册用户破100万，MAU破30万
- **中期（3年）**：月活破500万，年营收超1亿元

## 迭代路线图

```
V1.0 MVP（6个月）→ V1.1（3个月）→ V2.0（4个月）→ V3.0（6个月）
```

---

## 🚀 MVP Demo 快速体验

### 前置条件

- Python 3.12+
- [Anthropic API Key](https://console.anthropic.com/settings/keys)

### 一键启动

**Windows：**
```bat
start_demo.bat
```

**macOS / Linux：**
```bash
bash start_demo.sh
```

首次运行会自动创建 `.env` 文件，填入 `ANTHROPIC_API_KEY` 后重新运行即可。

### 手动启动

```bash
cd backend
cp .env.example .env          # 编辑填入 ANTHROPIC_API_KEY
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

### 访问地址

| 地址 | 说明 |
|------|------|
| http://localhost:8000/demo | **MVP Demo 体验页面** |
| http://localhost:8000/docs | Swagger API 文档 |
| http://localhost:8000/health | 服务健康检查 |

### Demo 功能模块

| 模块 | 功能 | AI 特性 |
|------|------|---------|
| 情感陪伴 | 流式 AI 对话 + 记忆 | SSE 流式 / 工具调用 |
| 健康问诊 | 症状分析 + 用药建议 | Adaptive Thinking |
| 防诈骗检测 | 两阶段风险评估 | 结构化输出 / Haiku+Opus 级联 |
| 社交交友 | AI 兴趣匹配 + 开场白 | 结构化输出 |
| 内容创作 | Vlog 文案 + 每日问候 | 节气感知 / 个性化 |
| 出行导航 | 适老化路线规划 | 无障碍标注 |

### 测试

```bash
cd backend
# 单元测试（不需要 API Key）
python -m pytest tests/ --ignore=tests/test_integration.py -q

# 全栈集成测试（需先启动服务器）
python -m pytest tests/test_integration.py -v
```

当前测试覆盖：**56 个单元测试 + 17 个集成测试，全部通过**。

---

> 机密文件 · 仅限内部使用 · 未经授权禁止传阅
>
> 版权归属夕阳伴侣科技有限公司，保留所有权利。
