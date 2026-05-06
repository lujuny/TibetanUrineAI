import { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  BrainCircuit,
  CheckCircle2,
  ClipboardList,
  Clock,
  Eye,
  FileText,
  Pencil,
  Plus,
  RefreshCw
} from "lucide-react";
import { Shell } from "../components/Shell";
import {
  assessObservationQuality,
  extractObservationFeatures,
  getCase,
  listCaseObservations,
  normalizeObservationSymptoms
} from "../lib/api";
import type {
  CaseSummary,
  ImageQualityResult,
  ObservationRecord,
  SymptomProfileResult,
  VisualFeaturesResult
} from "../types/domain";

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

function formatCollectionContext(item: ObservationRecord): string {
  const context = item.collection_context;
  const parts = [
    context.lighting_condition,
    context.container_type,
    context.background_type,
    context.resting_minutes === null || context.resting_minutes === undefined
      ? null
      : `静置 ${context.resting_minutes} 分钟`,
    context.is_morning_sample === null || context.is_morning_sample === undefined
      ? null
      : context.is_morning_sample
        ? "晨尿"
        : "非晨尿"
  ].filter(Boolean);

  return parts.length > 0 ? parts.join(" / ") : "未记录采集条件";
}

function qualityLabel(result?: ImageQualityResult | null): string {
  if (!result) {
    return "未检测";
  }

  return result.usable ? "图像可用" : "建议重拍";
}

function qualityTone(result?: ImageQualityResult | null): string {
  if (!result) {
    return "pending";
  }

  return result.usable ? "ready" : "warning";
}

function gemmaLabel(result?: ImageQualityResult | null): string {
  const review = result?.gemma_review;
  if (!review) {
    return "Gemma4 未复核";
  }

  if (review.status === "completed") {
    const qualityMap: Record<string, string> = {
      good: "良好",
      acceptable: "可接受",
      poor: "需重拍",
      unknown: "不确定"
    };
    return `Gemma4 复核：${qualityMap[review.collection_quality ?? "unknown"] ?? "不确定"}`;
  }

  if (review.status === "failed") {
    return "Gemma4 复核失败";
  }

  return "Gemma4 未配置";
}

const featureLabels: Record<string, string> = {
  color: "颜色",
  transparency: "透明度",
  foam: "泡沫",
  sediment: "沉淀",
  layering: "分层"
};

function featureGemmaLabel(result?: VisualFeaturesResult | null): string {
  const review = result?.gemma_review;
  if (!review) {
    return "Gemma4 未复核";
  }

  if (review.status === "completed") {
    return "Gemma4 已复核";
  }

  if (review.status === "failed") {
    return "Gemma4 复核失败";
  }

  return "Gemma4 未配置";
}

function symptomStatusLabel(result?: SymptomProfileResult | null): string {
  if (!result) {
    return "未整理";
  }

  if (result.status === "completed") {
    const confidenceMap: Record<string, string> = {
      high: "高置信",
      medium: "中置信",
      low: "低置信"
    };
    return confidenceMap[result.confidence] ?? "已整理";
  }

  return "待补充";
}

export function CaseDetailPage({ caseId }: { caseId: string }) {
  const [caseRecord, setCaseRecord] = useState<CaseSummary | null>(null);
  const [observations, setObservations] = useState<ObservationRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [qualityCheckingId, setQualityCheckingId] = useState<string | null>(null);
  const [featureCheckingId, setFeatureCheckingId] = useState<string | null>(null);
  const [symptomCheckingId, setSymptomCheckingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDetail() {
      setLoading(true);
      setError(null);
      try {
        const [caseData, observationData] = await Promise.all([
          getCase(caseId),
          listCaseObservations(caseId)
        ]);
        setCaseRecord(caseData);
        setObservations(observationData);
      } catch {
        setError("病例详情加载失败，请确认病例是否存在。");
      } finally {
        setLoading(false);
      }
    }

    loadDetail();
  }, [caseId]);

  async function handleQualityCheck(observationId: string) {
    setQualityCheckingId(observationId);
    setError(null);

    try {
      const updated = await assessObservationQuality(observationId);
      setObservations((current) =>
        current.map((item) => (item.id === observationId ? updated : item))
      );
    } catch {
      setError("图像质量检测失败，请确认后端服务和图像文件是否正常。");
    } finally {
      setQualityCheckingId(null);
    }
  }

  async function handleFeatureExtraction(observationId: string) {
    setFeatureCheckingId(observationId);
    setError(null);

    try {
      const updated = await extractObservationFeatures(observationId);
      setObservations((current) =>
        current.map((item) => (item.id === observationId ? updated : item))
      );
    } catch {
      setError("视觉特征提取失败，请确认后端服务和图像文件是否正常。");
    } finally {
      setFeatureCheckingId(null);
    }
  }

  async function handleSymptomNormalize(observationId: string) {
    setSymptomCheckingId(observationId);
    setError(null);

    try {
      const updated = await normalizeObservationSymptoms(observationId);
      setObservations((current) =>
        current.map((item) => (item.id === observationId ? updated : item))
      );
    } catch {
      setError("症状信息整理失败，请确认后端服务和症状文本是否正常。");
    } finally {
      setSymptomCheckingId(null);
    }
  }

  return (
    <Shell activeRoute="cases">
      <section className="page-header">
        <div>
          <p className="eyebrow">M01</p>
          <h1>{caseRecord?.anonymous_code ?? "病例详情"}</h1>
          <p className="lede">查看匿名病例基础信息和观察记录时间线。</p>
        </div>
        <div className="header-actions">
          <a className="secondary-button" href="#cases">
            <ArrowLeft size={18} />
            返回列表
          </a>
          {caseRecord && (
            <a className="primary-button" href={`#capture/${caseRecord.id}`}>
              <Plus size={18} />
              新增采集
            </a>
          )}
        </div>
      </section>

      {error && <div className="alert">{error}</div>}
      {loading && <p className="muted">正在加载病例详情...</p>}

      {!loading && caseRecord && (
        <section className="detail-grid">
          <article className="panel">
            <div className="panel-header">
              <div>
                <span>基础信息</span>
                <h2>病例档案</h2>
              </div>
              <FileText size={20} />
            </div>

            <dl className="detail-list">
              <div>
                <dt>匿名编号</dt>
                <dd>{caseRecord.anonymous_code}</dd>
              </div>
              <div>
                <dt>年龄段</dt>
                <dd>{caseRecord.age_group || "未填写"}</dd>
              </div>
              <div>
                <dt>性别</dt>
                <dd>{caseRecord.gender || "未填写"}</dd>
              </div>
              <div>
                <dt>备注</dt>
                <dd>{caseRecord.notes || "暂无备注"}</dd>
              </div>
              <div>
                <dt>创建时间</dt>
                <dd>{formatDate(caseRecord.created_at)}</dd>
              </div>
            </dl>
          </article>

          <article className="panel">
            <div className="panel-header">
              <div>
                <span>时间线</span>
                <h2>观察记录</h2>
              </div>
              <Clock size={20} />
            </div>

            {observations.length === 0 ? (
              <div className="empty-state">
                <h3>暂无观察记录</h3>
                <p>点击“新增采集”上传尿液图像，并记录采集条件。</p>
              </div>
            ) : (
              <div className="timeline">
                {observations.map((item) => (
                  <div className="observation-row" key={item.id}>
                    {item.image_path ? (
                      <img alt="尿液样本缩略图" src={item.image_path} />
                    ) : (
                      <div className="observation-thumb">无图像</div>
                    )}
                    <div className="observation-copy">
                      <strong>{formatDate(item.created_at)}</strong>
                      <span>{formatCollectionContext(item)}</span>
                      {item.symptom_text && <p>{item.symptom_text}</p>}
                      <div className={`quality-panel ${qualityTone(item.quality_result)}`}>
                        <div className="quality-title">
                          {item.quality_result?.usable ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
                          <strong>
                            {qualityLabel(item.quality_result)}
                            {item.quality_result ? ` · ${item.quality_result.quality_score} 分` : ""}
                          </strong>
                        </div>
                        {item.quality_result?.issues?.[0] && (
                          <div className="quality-list">
                            {item.quality_result.issues.slice(0, 3).map((issue) => (
                              <p key={`${issue.type}-${issue.message}`}>{issue.message}</p>
                            ))}
                          </div>
                        )}
                        {item.quality_result?.recommendations?.[0] && (
                          <p>建议：{item.quality_result.recommendations[0]}</p>
                        )}
                        {item.quality_result && (
                          <div className="quality-meta">
                            <span>规则/CV {item.quality_result.score_sources?.rule_cv_score ?? item.quality_result.quality_score} 分</span>
                            <span>Gemma 扣分 {item.quality_result.score_sources?.gemma_penalty ?? 0}</span>
                            <span>
                              <BrainCircuit size={14} />
                              {gemmaLabel(item.quality_result)}
                            </span>
                          </div>
                        )}
                      </div>
                      {item.visual_features && (
                        <div className="feature-panel">
                          <div className="feature-title">
                            <Eye size={16} />
                            <strong>视觉特征</strong>
                            <span>{featureGemmaLabel(item.visual_features)}</span>
                          </div>
                          {item.visual_features.summary && <p>{item.visual_features.summary}</p>}
                          <div className="feature-grid">
                            {Object.entries(item.visual_features.features ?? {}).map(([key, feature]) => (
                              <div className="feature-chip" key={key}>
                                <span>{featureLabels[key] ?? key}</span>
                                <strong>{feature.label}</strong>
                              </div>
                            ))}
                          </div>
                          {item.visual_features.recommendations?.[0] && (
                            <p>提示：{item.visual_features.recommendations[0]}</p>
                          )}
                        </div>
                      )}
                      {item.symptom_profile && (
                        <div className="symptom-panel">
                          <div className="symptom-title">
                            <ClipboardList size={16} />
                            <strong>症状整理</strong>
                            <span>{symptomStatusLabel(item.symptom_profile)}</span>
                          </div>
                          <p>{item.symptom_profile.summary ?? "症状信息已整理。"}</p>
                          {(item.symptom_profile.symptom_profile.symptom_tags?.length ?? 0) > 0 && (
                            <div className="symptom-tags">
                              {item.symptom_profile.symptom_profile.symptom_tags.map((tag) => (
                                <span key={tag}>{tag}</span>
                              ))}
                            </div>
                          )}
                          <div className="symptom-detail-grid">
                            <div>
                              <span>主诉</span>
                              <strong>{item.symptom_profile.symptom_profile.chief_complaint ?? "未提供"}</strong>
                            </div>
                            <div>
                              <span>持续时间</span>
                              <strong>{item.symptom_profile.symptom_profile.duration ?? "未提供"}</strong>
                            </div>
                            <div>
                              <span>睡眠</span>
                              <strong>{item.symptom_profile.symptom_profile.sleep ?? "未提供"}</strong>
                            </div>
                            <div>
                              <span>饮食</span>
                              <strong>{item.symptom_profile.symptom_profile.diet ?? "未提供"}</strong>
                            </div>
                            <div>
                              <span>饮水</span>
                              <strong>{item.symptom_profile.symptom_profile.water_intake ?? "未提供"}</strong>
                            </div>
                            <div>
                              <span>用药/干扰</span>
                              <strong>{item.symptom_profile.symptom_profile.medication ?? "未提供"}</strong>
                            </div>
                          </div>
                          {item.symptom_profile.missing_fields.length > 0 && (
                            <p>需补充：{item.symptom_profile.missing_fields.slice(0, 4).join("、")}</p>
                          )}
                          {item.symptom_profile.follow_up_questions[0] && (
                            <p>追问：{item.symptom_profile.follow_up_questions[0]}</p>
                          )}
                        </div>
                      )}
                    </div>
                    <div className="observation-actions">
                      <button
                        className="secondary-button small-button"
                        disabled={qualityCheckingId === item.id}
                        onClick={() => handleQualityCheck(item.id)}
                        type="button"
                      >
                        <RefreshCw size={16} />
                        {qualityCheckingId === item.id ? "检测中" : "检测"}
                      </button>
                      <button
                        className="secondary-button small-button"
                        disabled={featureCheckingId === item.id}
                        onClick={() => handleFeatureExtraction(item.id)}
                        type="button"
                      >
                        <Eye size={16} />
                        {featureCheckingId === item.id ? "提取中" : "特征"}
                      </button>
                      <button
                        className="secondary-button small-button"
                        disabled={symptomCheckingId === item.id}
                        onClick={() => handleSymptomNormalize(item.id)}
                        type="button"
                      >
                        <ClipboardList size={16} />
                        {symptomCheckingId === item.id ? "整理中" : "症状"}
                      </button>
                      <a className="secondary-button small-button" href={`#capture/${item.case_id}/${item.id}`}>
                        <Pencil size={16} />
                        修改
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </article>
        </section>
      )}
    </Shell>
  );
}
