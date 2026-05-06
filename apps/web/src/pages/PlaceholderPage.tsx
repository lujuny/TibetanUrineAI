import { Shell } from "../components/Shell";

interface PlaceholderPageProps {
  activeRoute: string;
  moduleId: string;
  title: string;
}

export function PlaceholderPage({ activeRoute, moduleId, title }: PlaceholderPageProps) {
  return (
    <Shell activeRoute={activeRoute}>
      <section className="page-header">
        <div>
          <p className="eyebrow">{moduleId}</p>
          <h1>{title}</h1>
          <p className="lede">该模块尚未进入正式开发，当前仅保留导航占位。</p>
        </div>
      </section>

      <div className="empty-state wide">
        <h2>等待模块开发</h2>
        <p>当前阶段正在完成 M01 工作台与病例管理。该页面会在对应模块启动时继续实现。</p>
      </div>
    </Shell>
  );
}
