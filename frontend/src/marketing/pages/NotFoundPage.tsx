import { ArrowLeft } from "lucide-react";
import { Button } from "../../shared/components/Button";

export function NotFoundPage() {
  return (
    <section className="content-index-page text-center">
      <p className="eyebrow">404</p>
      <h1>没有找到这个页面</h1>
      <p className="mx-auto mt-6 max-w-xl text-lg leading-8 text-slate-600">链接可能已经更新。你可以返回首页，或通过主导航前往完整的中文页面。</p>
      <Button className="mt-8" href="/" variant="dark"><ArrowLeft className="h-4 w-4" />返回首页</Button>
    </section>
  );
}
