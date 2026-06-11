import { useEffect } from "react";
import { ArrowRight, Sparkles } from "lucide-react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { MarketingFooter } from "./MarketingFooter";
import { MarketingHeader } from "./MarketingHeader";

function ScrollToTop() {
  const location = useLocation();

  useEffect(() => {
    if (location.hash) {
      window.requestAnimationFrame(() => {
        document.querySelector(location.hash)?.scrollIntoView();
      });
      return;
    }
    window.scrollTo({ top: 0 });
  }, [location.pathname, location.hash]);

  return null;
}

export function MarketingLayout() {
  return (
    <main className="min-h-screen bg-white text-slate-950">
      <ScrollToTop />
      <div className="bg-[#12163e] px-5 py-3 text-center text-sm font-semibold text-white">
        <Link className="inline-flex items-center justify-center gap-2 text-white/90 hover:text-white" to="/resources/ai-report">
          <Sparkles className="h-4 w-4 text-[#cafbff]" />
          新报告：为 AI 软件采购建立更聪明的预算和审批策略
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
      <MarketingHeader />
      <Outlet />
      <MarketingFooter />
    </main>
  );
}
