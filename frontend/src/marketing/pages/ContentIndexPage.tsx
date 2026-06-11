import { ArrowRight, Headphones, Newspaper, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Button } from "../../shared/components/Button";
import { contentEntries, type ContentEntry } from "../content/pages";

export function ContentIndexPage({ kind }: { kind: "podcasts" | "press" }) {
  const [query, setQuery] = useState("");
  const [tag, setTag] = useState("全部");
  const entries = contentEntries.filter(entry => entry.kind === kind);
  const tags = ["全部", ...new Set(entries.flatMap(entry => entry.tags))];
  const Icon = kind === "podcasts" ? Headphones : Newspaper;
  const filteredEntries = useMemo(
    () =>
      entries.filter(entry => {
        const matchesTag = tag === "全部" || entry.tags.includes(tag);
        const haystack = `${entry.title} ${entry.summary} ${entry.tags.join(" ")}`.toLowerCase();
        return matchesTag && haystack.includes(query.trim().toLowerCase());
      }),
    [entries, query, tag],
  );

  return (
    <section className="content-index-page">
      <div className="content-index-heading">
        <span><Icon className="h-4 w-4" />{kind === "podcasts" ? "播客" : "媒体中心"}</span>
        <h1>{kind === "podcasts" ? "财务与运营播客" : "媒体报道与公司动态"}</h1>
        <p>{kind === "podcasts" ? "按主题筛选节目，查看中文摘要并进入独立节目页面。" : "按类型筛选新闻稿、媒体报道与数据研究。"}</p>
        <label className="content-search">
          <Search className="h-5 w-5" />
          <input
            aria-label={kind === "podcasts" ? "搜索播客" : "搜索媒体内容"}
            onChange={event => setQuery(event.target.value)}
            placeholder={kind === "podcasts" ? "搜索播客" : "搜索媒体内容"}
            type="search"
            value={query}
          />
        </label>
        <div aria-label="内容分类" className="mt-5 flex flex-wrap justify-center gap-2">
          {tags.map(item => (
            <button
              aria-pressed={tag === item}
              className={`rounded-full border px-4 py-2 text-sm font-bold ${tag === item ? "border-[#20245f] bg-[#20245f] text-white" : "border-slate-200 bg-white text-slate-600"}`}
              key={item}
              onClick={() => setTag(item)}
              type="button"
            >
              {item}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-16 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {filteredEntries.map(entry => (
          <article className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm" key={entry.slug}>
            <img alt="" className="h-52 w-full object-cover" src={entry.image} />
            <div className="p-6">
              <small className="font-black text-[#1a9da5]">{entry.meta}</small>
              <h2 className="mt-3 text-2xl font-black leading-tight text-[#171b46]">{entry.title}</h2>
              <p className="mt-4 leading-7 text-slate-600">{entry.summary}</p>
              <div className="mt-5 flex flex-wrap gap-2">
                {entry.tags.map(item => <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600" key={item}>{item}</span>)}
              </div>
              <Link className="mt-6 inline-flex items-center gap-2 text-sm font-black text-[#20245f]" to={`/${kind}/${entry.slug}`}>
                {kind === "podcasts" ? "查看节目" : "阅读报道"} <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </article>
        ))}
        {filteredEntries.length === 0 && <div className="empty-search md:col-span-2 lg:col-span-3">没有找到匹配内容，请换一个关键词或分类。</div>}
      </div>
    </section>
  );
}

export function ContentDetailPage({ kind }: { kind: "podcasts" | "press" }) {
  const { contentSlug } = useParams();
  const entry = contentEntries.find(item => item.kind === kind && item.slug === contentSlug);

  if (!entry) {
    return (
      <section className="content-index-page text-center">
        <h1>没有找到这条内容</h1>
        <Button className="mt-8" href={`/${kind}`} variant="dark">返回内容列表</Button>
      </section>
    );
  }

  return <ContentArticle entry={entry} />;
}

function ContentArticle({ entry }: { entry: ContentEntry }) {
  return (
    <article className="report-page">
      <header className="report-header">
        <span className="report-category">{entry.meta}</span>
        <h1>{entry.title}</h1>
        <p>{entry.summary}</p>
      </header>
      <div className="report-image-wrap"><img alt="" src={entry.image} /></div>
      <section className="report-body">
        <div>
          <p className="eyebrow">内容摘要</p>
          <h2>从真实经验中提炼可以立即讨论的问题</h2>
          <p>这条内容围绕软件采购、财务运营和团队协作展开，帮助读者把观点转化为预算、流程和责任分工上的实际行动。</p>
          <Button href={entry.kind === "podcasts" ? "/podcasts" : "/press"} variant="dark">
            返回{entry.kind === "podcasts" ? "播客" : "媒体"}列表
          </Button>
        </div>
        <div className="report-facts">
          {entry.tags.map(tag => <div key={tag}><span>主题</span><strong>{tag}</strong></div>)}
        </div>
      </section>
    </article>
  );
}
