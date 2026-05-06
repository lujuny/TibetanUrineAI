# 工程架构

## 目录结构

```text
TibetanUrineAI/
  apps/
    api/                 # FastAPI 后端
    web/                 # React/Vite 前端
  packages/
    shared/              # 共享 schema 和接口约定
  docs/                  # 工程文档
  scripts/               # 本地开发脚本
```

## 后端分层

```text
app/
  core/                  # 配置、安全边界、通用能力
  db/                    # SQLite 数据访问层
  models/                # Pydantic schema
  routers/               # HTTP API
  services/              # 业务服务与模块逻辑
  data/                  # 初始知识库数据
```

## 数据存储

后端使用 Python 标准库 `sqlite3` 作为当前阶段的数据底座，不额外引入 ORM。默认数据库地址为：

```text
sqlite:///./data/tibetan_urine_ai.db
```

从 `apps/api` 目录启动服务时，运行数据位于：

```text
apps/api/data/tibetan_urine_ai.db
```

当前已持久化的数据：

- 病例 `cases`
- 观察记录 `observations`

`observations` 中的采集上下文、图像质量、视觉特征、症状结构化、辅助判读和报告字段以 JSON 文本存储，便于后续模块逐步扩展。

上传图像保存在：

```text
apps/api/data/uploads
```

后端通过 `/uploads/...` 暴露静态访问路径，前端开发服务器会将 `/uploads` 代理到后端。

观察记录支持修改采集基础信息。修改后会更新 `observations.updated_at`，重新生成图像质量结果，并清空视觉特征、症状结构化、辅助判读和报告等后续派生结果，避免后续页面展示基于旧数据生成的内容。

M03 图像质量检测采用“规则/CV 初筛 + Gemma4 多模态复核”的混合架构。规则/CV 层使用 Pillow 读取上传图像，当前检测项包括：

- 文件是否存在、是否可解析
- 图像分辨率
- 亮度和过暗/过曝
- 高亮反光比例
- 灰度对比度
- 边缘强度作为清晰度初步指标
- 尿液色彩区域占比作为样本区域是否明显的初步指标

Gemma4 复核层使用 OpenAI-compatible chat completions 接口发送图片和规则指标，让多模态模型判断尿液样本是否可见、样本区域是否完整、背景是否复杂、是否存在遮挡/反光/失焦等语义质量问题。

质量结果写入 `observations.quality_result`，包含 `quality_score`、`usable`、`issues`、`recommendations`、`metrics`、`gemma_review` 和 `score_sources`。最终分数以规则/CV 分数为基础，再根据 Gemma4 发现的语义问题扣分。如果未配置 `GEMMA_API_BASE`，系统会自动跳过 Gemma4 复核，仅保存规则/CV 结果。创建或修改观察记录时会自动刷新质量结果，也可以通过 `/api/observations/{observation_id}/quality` 手动重新检测。

M04 视觉特征提取同样采用“规则/CV 初筛 + Gemma4 多模态复核”的混合架构。规则/CV 层基于 Pillow 对尿液色彩区域进行粗分割，并提取：

- 颜色：基于尿液色彩区域平均 RGB/HSV 估算
- 透明度：基于灰度对比度、边缘强度和色彩区域占比估算
- 泡沫：基于高亮低饱和区域占比估算
- 沉淀：基于低亮度高饱和像素占比估算
- 分层：基于图像上中下水平带亮度差异估算

Gemma4 复核层会根据图片和规则结果复核上述五类特征。视觉特征结果写入 `observations.visual_features`，包含 `features`、`summary`、`recommendations`、`rule_cv_result` 和 `gemma_review`。可以通过 `/api/observations/{observation_id}/features` 手动提取，也会在 `/api/observations/{observation_id}/analyze` 中作为后续 Agent 判读输入。

## 前端分层

```text
src/
  components/            # 通用组件
  lib/                   # API 客户端与工具
  pages/                 # 页面级组件
  types/                 # 前端类型定义
```

## 模块映射

| 模块 | 后端位置 | 前端位置 |
|---|---|---|
| M00 基础工程与数据底座 | `core/`, `db/`, `models/` | `lib/`, `types/` |
| M01 工作台与病例管理 | `routers/cases.py` | `pages/Dashboard.tsx`, `pages/CasesPage.tsx`, `pages/CaseDetailPage.tsx` |
| M02 标准化采集 | `routers/uploads.py`, `routers/observations.py` | `pages/CapturePage.tsx` |
| M03 图像质量检测 | `services/image_quality.py` | `pages/CaseDetailPage.tsx` |
| M04 视觉特征提取 | `services/feature_extraction.py`, `services/gemma_features.py` | `pages/CaseDetailPage.tsx` |
| M05 症状信息整理 | `services/symptom_normalizer.py`, `routers/observations.py` | `pages/CapturePage.tsx`, `pages/CaseDetailPage.tsx` |
| M06 藏医知识库 | `data/knowledge_seed.json` | 后续知识库页面 |
| M07 Gemma 4 Agent 辅助判读 | `services/agent.py` | 后续辅助判读页面 |
| M08 报告生成 | `services/reporting.py` | 后续报告页面 |
| M09 历史趋势对比 | `services/history.py` | 后续趋势页面 |
| M10 专业复核与安全合规 | `core/safety.py` | 后续复核组件 |
