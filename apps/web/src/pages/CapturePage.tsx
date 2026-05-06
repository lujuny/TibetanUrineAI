import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { ArrowLeft, ImagePlus, Save } from "lucide-react";
import { Shell } from "../components/Shell";
import {
  createObservation,
  getObservation,
  listCases,
  updateObservation,
  uploadImage
} from "../lib/api";
import type { CaseSummary, CollectionContext, SymptomContext } from "../types/domain";

const initialContext: CollectionContext = {
  lighting_condition: "",
  container_type: "",
  background_type: "",
  resting_minutes: null,
  is_morning_sample: null,
  interference_note: ""
};

const initialSymptomContext: SymptomContext = {
  chief_complaint: "",
  duration: "",
  sleep: "",
  diet: "",
  water_intake: "",
  urination: "",
  stool: "",
  medication: ""
};

interface CapturePageProps {
  caseId?: string;
  observationId?: string;
}

function normalizeContext(context?: CollectionContext | null): CollectionContext {
  return {
    lighting_condition: context?.lighting_condition ?? "",
    container_type: context?.container_type ?? "",
    background_type: context?.background_type ?? "",
    resting_minutes: context?.resting_minutes ?? null,
    is_morning_sample: context?.is_morning_sample ?? null,
    interference_note: context?.interference_note ?? ""
  };
}

function normalizeSymptomContext(context?: SymptomContext | null): SymptomContext {
  return {
    chief_complaint: context?.chief_complaint ?? "",
    duration: context?.duration ?? "",
    sleep: context?.sleep ?? "",
    diet: context?.diet ?? "",
    water_intake: context?.water_intake ?? "",
    urination: context?.urination ?? "",
    stool: context?.stool ?? "",
    medication: context?.medication ?? ""
  };
}

export function CapturePage({ caseId, observationId }: CapturePageProps) {
  const isEditing = Boolean(observationId);
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState(caseId ?? "");
  const [context, setContext] = useState<CollectionContext>(initialContext);
  const [symptomContext, setSymptomContext] = useState<SymptomContext>(initialSymptomContext);
  const [symptomText, setSymptomText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [existingImagePath, setExistingImagePath] = useState<string | null>(null);
  const [loadingCases, setLoadingCases] = useState(true);
  const [loadingObservation, setLoadingObservation] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedCase = useMemo(
    () => cases.find((item) => item.id === selectedCaseId),
    [cases, selectedCaseId]
  );
  const displayImage = previewUrl ?? existingImagePath;

  useEffect(() => {
    if (caseId) {
      setSelectedCaseId(caseId);
    }
  }, [caseId]);

  useEffect(() => {
    async function loadCases() {
      setLoadingCases(true);
      setError(null);
      try {
        const data = await listCases();
        setCases(data);
        if (!caseId && data.length > 0) {
          setSelectedCaseId((current) => current || data[0].id);
        }
      } catch {
        setError("病例列表加载失败，请确认后端服务已启动。");
      } finally {
        setLoadingCases(false);
      }
    }

    loadCases();
  }, [caseId]);

  useEffect(() => {
    if (!observationId) {
      setExistingImagePath(null);
      return;
    }

    let cancelled = false;

    async function loadObservation() {
      setLoadingObservation(true);
      setError(null);
      try {
        const observation = await getObservation(observationId as string);
        if (cancelled) {
          return;
        }
        setSelectedCaseId(observation.case_id);
        setExistingImagePath(observation.image_path ?? null);
        setContext(normalizeContext(observation.collection_context));
        setSymptomContext(normalizeSymptomContext(observation.symptom_context));
        setSymptomText(observation.symptom_text ?? "");
      } catch {
        if (!cancelled) {
          setError("采集记录加载失败，请确认记录是否存在。");
        }
      } finally {
        if (!cancelled) {
          setLoadingObservation(false);
        }
      }
    }

    loadObservation();

    return () => {
      cancelled = true;
    };
  }, [observationId]);

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const selectedFile = event.target.files?.[0] ?? null;
    setFile(selectedFile);
    setError(null);

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }

    setPreviewUrl(selectedFile ? URL.createObjectURL(selectedFile) : null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedCaseId) {
      setError("请先选择一个病例。");
      return;
    }

    if (!file && !existingImagePath) {
      setError("请上传一张尿液样本图像。");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const uploaded = file ? await uploadImage(file) : null;
      const imagePath = uploaded?.image_path ?? existingImagePath;
      const payload = {
        case_id: selectedCaseId,
        image_path: imagePath,
        collection_context: {
          lighting_condition: context.lighting_condition || null,
          container_type: context.container_type || null,
          background_type: context.background_type || null,
          resting_minutes: context.resting_minutes,
          is_morning_sample: context.is_morning_sample,
          interference_note: context.interference_note || null
        },
        symptom_context: {
          chief_complaint: symptomContext.chief_complaint || null,
          duration: symptomContext.duration || null,
          sleep: symptomContext.sleep || null,
          diet: symptomContext.diet || null,
          water_intake: symptomContext.water_intake || null,
          urination: symptomContext.urination || null,
          stool: symptomContext.stool || null,
          medication: symptomContext.medication || null
        },
        symptom_text: symptomText.trim() || null
      };

      if (isEditing && observationId) {
        await updateObservation(observationId, payload);
      } else {
        await createObservation(payload);
      }

      window.location.hash = `#cases/${selectedCaseId}`;
    } catch {
      setError(isEditing ? "采集记录修改失败，请检查后端服务状态。" : "采集记录保存失败，请检查图片格式和后端服务状态。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Shell activeRoute="capture">
      <section className="page-header">
        <div>
          <p className="eyebrow">M02</p>
          <h1>{isEditing ? "编辑采集记录" : "标准化采集"}</h1>
          <p className="lede">
            {isEditing ? "修改已保存的尿液样本图像、采集条件和备注信息。" : "上传尿液样本图像，记录光照、容器、背景、静置时间等采集条件。"}
          </p>
        </div>
        <a className="secondary-button" href={selectedCaseId ? `#cases/${selectedCaseId}` : "#cases"}>
          <ArrowLeft size={18} />
          返回病例
        </a>
      </section>

      {error && <div className="alert">{error}</div>}
      {loadingObservation && <p className="muted">正在加载采集记录...</p>}

      <form className="capture-grid" onSubmit={handleSubmit}>
        <section className="panel">
          <div className="panel-header">
            <div>
              <span>图像</span>
              <h2>尿液样本</h2>
            </div>
            <ImagePlus size={20} />
          </div>

          <label className="upload-box">
            {displayImage ? (
              <img alt="尿液样本预览" src={displayImage} />
            ) : (
              <span>点击上传 JPG / PNG / WEBP 图像</span>
            )}
            <input accept="image/jpeg,image/png,image/webp" type="file" onChange={handleFileChange} />
          </label>

          {isEditing && existingImagePath && !file && (
            <p className="inline-note">当前保留原图，重新选择图片后会替换。</p>
          )}
        </section>

        <section className="panel form-panel">
          <div className="panel-header">
            <div>
              <span>{isEditing ? "编辑" : "记录"}</span>
              <h2>采集条件</h2>
            </div>
          </div>

          <label className="field">
            <span>所属病例</span>
            <select
              disabled={loadingCases || loadingObservation}
              value={selectedCaseId}
              onChange={(event) => setSelectedCaseId(event.target.value)}
            >
              <option value="">请选择病例</option>
              {cases.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.anonymous_code}
                </option>
              ))}
            </select>
          </label>

          {selectedCase && <p className="inline-note">当前病例：{selectedCase.notes || selectedCase.anonymous_code}</p>}

          <div className="form-row">
            <label className="field">
              <span>光照条件</span>
              <select
                value={context.lighting_condition ?? ""}
                onChange={(event) => setContext((current) => ({ ...current, lighting_condition: event.target.value }))}
              >
                <option value="">未记录</option>
                <option value="自然光">自然光</option>
                <option value="室内白光">室内白光</option>
                <option value="暖光">暖光</option>
                <option value="未知">未知</option>
              </select>
            </label>

            <label className="field">
              <span>容器类型</span>
              <select
                value={context.container_type ?? ""}
                onChange={(event) => setContext((current) => ({ ...current, container_type: event.target.value }))}
              >
                <option value="">未记录</option>
                <option value="透明杯">透明杯</option>
                <option value="试管">试管</option>
                <option value="其他">其他</option>
              </select>
            </label>
          </div>

          <div className="form-row">
            <label className="field">
              <span>背景类型</span>
              <select
                value={context.background_type ?? ""}
                onChange={(event) => setContext((current) => ({ ...current, background_type: event.target.value }))}
              >
                <option value="">未记录</option>
                <option value="白色背景">白色背景</option>
                <option value="浅色背景">浅色背景</option>
                <option value="复杂背景">复杂背景</option>
                <option value="未知">未知</option>
              </select>
            </label>

            <label className="field">
              <span>静置时间 分钟</span>
              <input
                min="0"
                type="number"
                value={context.resting_minutes ?? ""}
                onChange={(event) => {
                  const value = event.target.value;
                  setContext((current) => ({
                    ...current,
                    resting_minutes: value === "" ? null : Number(value)
                  }));
                }}
              />
            </label>
          </div>

          <label className="field">
            <span>是否晨尿</span>
            <select
              value={
                context.is_morning_sample === null || context.is_morning_sample === undefined
                  ? ""
                  : String(context.is_morning_sample)
              }
              onChange={(event) => {
                const value = event.target.value;
                setContext((current) => ({
                  ...current,
                  is_morning_sample: value === "" ? null : value === "true"
                }));
              }}
            >
              <option value="">未记录</option>
              <option value="true">是</option>
              <option value="false">否</option>
            </select>
          </label>

          <div className="form-section-title">
            <span>症状信息</span>
            <strong>结构化补充</strong>
          </div>

          <label className="field">
            <span>主诉/症状</span>
            <input
              placeholder="例如尿黄、口干、乏力"
              value={symptomContext.chief_complaint ?? ""}
              onChange={(event) => setSymptomContext((current) => ({ ...current, chief_complaint: event.target.value }))}
            />
          </label>

          <div className="form-row">
            <label className="field">
              <span>持续时间</span>
              <input
                placeholder="例如3天、1周"
                value={symptomContext.duration ?? ""}
                onChange={(event) => setSymptomContext((current) => ({ ...current, duration: event.target.value }))}
              />
            </label>

            <label className="field">
              <span>睡眠情况</span>
              <select
                value={symptomContext.sleep ?? ""}
                onChange={(event) => setSymptomContext((current) => ({ ...current, sleep: event.target.value }))}
              >
                <option value="">未记录</option>
                <option value="睡眠好">睡眠好</option>
                <option value="睡眠一般">睡眠一般</option>
                <option value="睡眠差">睡眠差</option>
                <option value="失眠">失眠</option>
                <option value="多梦">多梦</option>
                <option value="易醒">易醒</option>
              </select>
            </label>
          </div>

          <div className="form-row">
            <label className="field">
              <span>饮食情况</span>
              <select
                value={symptomContext.diet ?? ""}
                onChange={(event) => setSymptomContext((current) => ({ ...current, diet: event.target.value }))}
              >
                <option value="">未记录</option>
                <option value="饮食清淡">饮食清淡</option>
                <option value="偏油腻">偏油腻</option>
                <option value="偏辛辣">偏辛辣</option>
                <option value="食欲差">食欲差</option>
                <option value="近期饮食变化">近期饮食变化</option>
              </select>
            </label>

            <label className="field">
              <span>饮水情况</span>
              <select
                value={symptomContext.water_intake ?? ""}
                onChange={(event) => setSymptomContext((current) => ({ ...current, water_intake: event.target.value }))}
              >
                <option value="">未记录</option>
                <option value="饮水少">饮水少</option>
                <option value="饮水正常">饮水正常</option>
                <option value="饮水多">饮水多</option>
              </select>
            </label>
          </div>

          <div className="form-row">
            <label className="field">
              <span>小便情况</span>
              <input
                placeholder="例如尿黄、尿频、尿少"
                value={symptomContext.urination ?? ""}
                onChange={(event) => setSymptomContext((current) => ({ ...current, urination: event.target.value }))}
              />
            </label>

            <label className="field">
              <span>大便情况</span>
              <select
                value={symptomContext.stool ?? ""}
                onChange={(event) => setSymptomContext((current) => ({ ...current, stool: event.target.value }))}
              >
                <option value="">未记录</option>
                <option value="大便正常">大便正常</option>
                <option value="大便干">大便干</option>
                <option value="大便稀">大便稀</option>
                <option value="便秘">便秘</option>
              </select>
            </label>
          </div>

          <label className="field">
            <span>用药/干扰</span>
            <textarea
              placeholder="例如未服药、服用维生素、饮酒、特殊饮食等"
              value={symptomContext.medication ?? ""}
              onChange={(event) => setSymptomContext((current) => ({ ...current, medication: event.target.value }))}
            />
          </label>

          <label className="field">
            <span>其他症状或备注</span>
            <textarea
              placeholder="可记录无法归入上方字段的补充描述"
              value={symptomText}
              onChange={(event) => setSymptomText(event.target.value)}
            />
          </label>

          <label className="field">
            <span>干扰备注</span>
            <textarea
              placeholder="例如轻微反光、背景复杂、容器边缘遮挡等"
              value={context.interference_note ?? ""}
              onChange={(event) => setContext((current) => ({ ...current, interference_note: event.target.value }))}
            />
          </label>

          <button className="primary-button" disabled={submitting || loadingObservation} type="submit">
            <Save size={18} />
            {submitting ? "保存中" : isEditing ? "保存修改" : "保存采集记录"}
          </button>
        </section>
      </form>
    </Shell>
  );
}
