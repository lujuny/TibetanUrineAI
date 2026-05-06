# TibetanUrineAI

藏医尿诊智能辅助系统代码工程。

本项目采用前后端分离结构：

- `apps/web`：前端 Web App，负责病例、采集、分析结果、报告和趋势展示。
- `apps/api`：后端 API，负责病例数据、图像分析、Gemma 4 Agent、知识库和报告生成。
- `packages/shared`：共享数据结构和接口约定。
- `docs`：工程文档。
- `scripts`：本地开发脚本。

## 当前状态

当前已完成基础工程骨架、M01 工作台与病例管理初版、M02 标准化采集初版、M03 图像质量检测初版、M04 视觉特征提取初版、M05 症状信息整理初版，病例与观察记录已持久化到 SQLite。

后续开发建议按照模块文档推进：

1. M00 基础工程与数据底座
2. M01 工作台与病例管理
3. M02 标准化采集
4. M03 图像质量检测
5. M04 视觉特征提取
6. M05 症状信息整理
7. M06 藏医知识库
8. M07 Gemma 4 Agent 辅助判读
9. M08 报告生成
10. M09 历史趋势对比
11. M10 专业复核与安全合规

## 已完成模块

- M00 基础工程与数据底座：前后端骨架、依赖环境、启动脚本、健康检查、基础数据模型、SQLite 仓储。
- M01 工作台与病例管理：前端路由、病例列表、新建匿名病例、病例详情、观察记录时间线占位、病例相关 API。
- M02 标准化采集：从病例详情进入采集页，上传尿液图像，记录采集条件，保存观察记录并在病例详情展示；支持回到已保存记录进行修改。
- M03 图像质量检测：基于规则/CV 读取上传图像并检测分辨率、亮度、曝光、反光、对比度、清晰度和尿液色彩区域占比；配置 Gemma4 后会进行多模态复核，并融合生成质量分、可用状态、问题列表和重拍建议。
- M04 视觉特征提取：基于规则/CV 提取颜色、透明度、泡沫、沉淀和分层特征；配置 Gemma4 后会进行多模态复核，并融合生成结构化视觉特征。
- M05 症状信息整理：支持单独填写主诉、持续时间、睡眠、饮食、饮水、二便、用药/干扰因素，并结合自由文本补充说明生成缺失信息和追问建议，结果可供后续 Agent 辅助判读使用。

## 数据存储

后端默认使用 SQLite，本地数据库路径由 `DATABASE_URL` 控制：

```text
sqlite:///./data/tibetan_urine_ai.db
```

从 `apps/api` 目录启动后端时，数据库会自动创建在 `apps/api/data/tibetan_urine_ai.db`。该目录属于本地运行数据，不提交到代码仓库。

上传图片会保存到 `apps/api/data/uploads`，并通过 `/uploads/...` 静态路径访问。

## Gemma4 图像质量复核

M03 默认先执行本地规则/CV 检测。如果配置了 OpenAI-compatible 的 Gemma4 多模态接口，会继续把图片和规则指标发送给 Gemma4 做采集质量复核：

后端运行时读取 `apps/api/.env`，可参考 `apps/api/.env.example` 创建或修改配置。

```text
GEMMA_API_BASE=http://127.0.0.1:18080/v1
GEMMA_API_KEY=your-api-key
GEMMA_MODEL=gemma4:e4b
GEMMA_QUALITY_REVIEW_ENABLED=true
GEMMA_FEATURE_REVIEW_ENABLED=true
```

如果 `GEMMA_API_BASE` 为空，系统会自动跳过 Gemma4 复核，仅使用规则/CV 结果。

## 当前核心接口

- `GET /api/health`：健康检查
- `GET /api/cases`：病例列表
- `POST /api/cases`：创建匿名病例
- `GET /api/cases/{case_id}`：病例详情
- `GET /api/cases/{case_id}/observations`：病例观察记录
- `POST /api/uploads`：上传尿液图像
- `POST /api/observations`：创建观察记录
- `GET /api/observations/{observation_id}`：观察记录详情
- `PATCH /api/observations/{observation_id}`：修改观察记录基础信息
- `POST /api/observations/{observation_id}/quality`：重新检测图像质量
- `POST /api/observations/{observation_id}/features`：提取视觉特征
- `POST /api/observations/{observation_id}/symptoms`：整理症状文本

## 本地开发

后端：

```bash
cd apps/api
conda activate zangai
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8021
```

前端：

```bash
cd apps/web
npm install
npm run dev
```

前端默认地址：`http://127.0.0.1:8022`

也可以在项目根目录使用脚本：

```bash
./scripts/dev_api.sh
./scripts/dev_web.sh
```

## 安全边界

本系统仅用于藏医尿诊相关的辅助观察、记录、教学和复核，不提供医学确诊或治疗建议。所有结果需由专业藏医师结合完整问诊和实际情况进行判断。
