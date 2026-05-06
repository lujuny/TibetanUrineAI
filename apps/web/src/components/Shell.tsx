import type { ReactNode } from "react";

interface ShellProps {
  activeRoute: string;
  children: ReactNode;
}

const navItems = [
  { id: "dashboard", label: "工作台", href: "#dashboard" },
  { id: "cases", label: "病例", href: "#cases" },
  { id: "capture", label: "采集", href: "#capture" },
  { id: "reports", label: "报告", href: "#reports" },
  { id: "knowledge", label: "知识库", href: "#knowledge" }
];

export function Shell({ activeRoute, children }: ShellProps) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">藏</span>
          <div>
            <strong>藏医尿诊</strong>
            <span>智能辅助系统</span>
          </div>
        </div>
        <nav className="nav">
          {navItems.map((item) => (
            <a
              className={`nav-item ${activeRoute === item.id ? "active" : ""}`}
              href={item.href}
              key={item.id}
            >
              {item.label}
            </a>
          ))}
        </nav>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}
