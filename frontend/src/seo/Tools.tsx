import { tools, type ToolKind } from "./tools";
export function ToolIcon() {
  return <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><rect x="5" y="2" width="14" height="20" rx="3" /><path d="M8 6h8M8 11h2m4 0h2M8 15h2m4 0h2M8 19h2m4 0h2" /></svg>;
}
export function ToolHeader({ kind }: { kind: ToolKind }) {
  const tool = tools.find(tool => tool.kind === kind)!;
  return <div className="tool-header"><p className="tool-eyebrow"><ToolIcon /> FITICIAN TOOL</p><h1>{tool.title}</h1><p className="tool-intro">یک تخمین شفاف برای شروع؛ بدون ثبت‌نام و بدون ارسال اطلاعات</p><span className="tool-privacy"><span aria-hidden="true">●</span> محاسبه روی دستگاه شما</span></div>;
}
export function ToolSwitcher({ kind }: { kind: ToolKind }) {
  return <nav className="tool-switcher" aria-label="ماشین‌حساب‌های فیتیشن">{tools.map(tool => <a key={tool.kind} href={tool.path} aria-current={kind === tool.kind ? "page" : undefined}>{tool.label}</a>)}</nav>;
}
export function ToolHub() {
  return <section className="tool-hub" aria-label="ابزارهای رایگان فیتیشن">{tools.map((tool, index) => <a className="tool-card" href={tool.path} key={tool.kind}><span className="tool-card-top"><span className="tool-symbol" dir="ltr">{tool.symbol}</span><span className="tool-card-index" aria-hidden="true">0{index + 1}</span></span><h2>{tool.label}</h2><p>{tool.description}</p><span className="tool-card-cta">محاسبه کن <span aria-hidden="true">←</span></span></a>)}</section>;
}
