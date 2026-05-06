import { useEffect, useState } from "react";
import { Activity, ClipboardList, Database, FileText, Image, ShieldCheck, Stethoscope } from "lucide-react";
import { Shell } from "../components/Shell";
import { getHealth } from "../lib/api";
import type { HealthResponse, ProjectModule } from "../types/domain";

const modules: ProjectModule[] = [
  {
    id: "M01",
    name: "病例管理",
    status: "ready",
    description: "匿名病例、观察记录和病例时间线。"
  },
  {
    id: "M02",
    name: "标准化采集",
    status: "ready",
    description: "图像上传、采集条件记录和采集引导。"
  },
  {
    id: "M03",
    name: "图像质量检测",
    status: "ready",
    description: "规则/CV 初筛与 Gemma4 多模态复核。"
  },
  {
    id: "M04",
    name: "视觉特征提取",
    status: "ready",
    description: "规则/CV 特征提取与 Gemma4 多模态复核。"
  },
  {
    id: "M05",
    name: "症状信息整理",
    status: "ready",
    description: "自由文本症状结构化、缺失信息识别和追问建议。"
  },
  {
    id: "M07",
    name: "Agent 辅助判读",
    status: "planned",
    description: "Gemma 4 融合多模态信息生成辅助解释。"
  },
  {
    id: "M10",
    name: "安全合规",
    status: "planned",
    description: "专业复核、安全声明和高风险输出检查。"
  }
];

const icons = [Database, Image, Activity, Stethoscope, ClipboardList, FileText, ShieldCheck];

export function Dashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealthError("后端 API 暂未连接"));
  }, []);

  return (
    <Shell activeRoute="dashboard">
      <section className="page-header">
        <div>
          <p className="eyebrow">TibetanUrineAI</p>
          <h1>藏医尿诊智能辅助系统</h1>
          <p className="lede">
            面向标准化采集、视觉特征提取、知识辅助解释和结构化报告的多模态 AI 工程骨架。
          </p>
        </div>
        <div className={`status-pill ${health ? "ready" : "pending"}`}>
          {health ? `API ${health.status}` : healthError ?? "连接中"}
        </div>
      </section>

      <section className="summary-grid">
        <article>
          <span>当前阶段</span>
          <strong>M05</strong>
          <p>症状信息整理初版完成</p>
        </article>
        <article>
          <span>开发方式</span>
          <strong>模块化</strong>
          <p>每次围绕一个模块推进</p>
        </article>
        <article>
          <span>安全边界</span>
          <strong>辅助判读</strong>
          <p>不输出确诊或治疗处方</p>
        </article>
      </section>

      <section className="module-grid">
        {modules.map((module, index) => {
          const Icon = icons[index];
          return (
            <article className="module-card" key={module.id}>
              <div className="module-card-header">
                <Icon aria-hidden="true" size={20} />
                <span className={`module-status ${module.status}`}>{module.status}</span>
              </div>
              <h2>{module.id} {module.name}</h2>
              <p>{module.description}</p>
            </article>
          );
        })}
      </section>
    </Shell>
  );
}
