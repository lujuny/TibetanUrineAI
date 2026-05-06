import { FormEvent, useEffect, useMemo, useState } from "react";
import { Plus, RefreshCw } from "lucide-react";
import { Shell } from "../components/Shell";
import { createCase, listCases } from "../lib/api";
import type { CaseCreatePayload, CaseSummary } from "../types/domain";

const initialForm: CaseCreatePayload = {
  age_group: "",
  gender: "",
  notes: ""
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(new Date(value));
}

export function CasesPage() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [form, setForm] = useState<CaseCreatePayload>(initialForm);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasCases = useMemo(() => cases.length > 0, [cases]);

  async function loadCases() {
    setLoading(true);
    setError(null);
    try {
      const data = await listCases();
      setCases(data);
    } catch {
      setError("病例列表加载失败，请确认后端服务已启动。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCases();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const created = await createCase({
        age_group: form.age_group?.trim() || undefined,
        gender: form.gender?.trim() || undefined,
        notes: form.notes?.trim() || undefined
      });
      setCases((current) => [created, ...current]);
      setForm(initialForm);
      window.location.hash = `#cases/${created.id}`;
    } catch {
      setError("新建病例失败，请稍后重试。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Shell activeRoute="cases">
      <section className="page-header">
        <div>
          <p className="eyebrow">M01</p>
          <h1>病例管理</h1>
          <p className="lede">创建匿名病例，查看病例列表，并进入病例详情维护观察记录。</p>
        </div>
        <button className="icon-button" type="button" onClick={loadCases} aria-label="刷新病例列表">
          <RefreshCw size={18} />
        </button>
      </section>

      {error && <div className="alert">{error}</div>}

      <section className="workspace-grid">
        <form className="panel form-panel" onSubmit={handleSubmit}>
          <div className="panel-header">
            <div>
              <span>新建</span>
              <h2>匿名病例</h2>
            </div>
            <Plus size={20} />
          </div>

          <label className="field">
            <span>年龄段</span>
            <select
              value={form.age_group ?? ""}
              onChange={(event) => setForm((current) => ({ ...current, age_group: event.target.value }))}
            >
              <option value="">未填写</option>
              <option value="0-18">0-18</option>
              <option value="19-30">19-30</option>
              <option value="31-45">31-45</option>
              <option value="46-60">46-60</option>
              <option value="60+">60+</option>
            </select>
          </label>

          <label className="field">
            <span>性别</span>
            <select
              value={form.gender ?? ""}
              onChange={(event) => setForm((current) => ({ ...current, gender: event.target.value }))}
            >
              <option value="">未填写</option>
              <option value="female">女</option>
              <option value="male">男</option>
              <option value="unknown">未知</option>
            </select>
          </label>

          <label className="field">
            <span>备注</span>
            <textarea
              placeholder="只填写与辅助记录相关的非敏感信息"
              value={form.notes ?? ""}
              onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
            />
          </label>

          <button className="primary-button" disabled={submitting} type="submit">
            {submitting ? "创建中" : "创建病例"}
          </button>
        </form>

        <section className="panel cases-panel">
          <div className="panel-header">
            <div>
              <span>列表</span>
              <h2>匿名病例</h2>
            </div>
            <strong>{cases.length}</strong>
          </div>

          {loading && <p className="muted">正在加载病例列表...</p>}

          {!loading && !hasCases && (
            <div className="empty-state">
              <h3>还没有病例</h3>
              <p>先创建一个匿名病例，后续采集、分析和报告都会挂在病例下面。</p>
            </div>
          )}

          {!loading && hasCases && (
            <div className="case-list">
              {cases.map((item) => (
                <a className="case-row" href={`#cases/${item.id}`} key={item.id}>
                  <div>
                    <strong>{item.anonymous_code}</strong>
                    <span>{item.notes || "暂无备注"}</span>
                  </div>
                  <dl>
                    <div>
                      <dt>年龄段</dt>
                      <dd>{item.age_group || "未填"}</dd>
                    </div>
                    <div>
                      <dt>性别</dt>
                      <dd>{item.gender || "未填"}</dd>
                    </div>
                    <div>
                      <dt>创建时间</dt>
                      <dd>{formatDate(item.created_at)}</dd>
                    </div>
                  </dl>
                </a>
              ))}
            </div>
          )}
        </section>
      </section>
    </Shell>
  );
}

