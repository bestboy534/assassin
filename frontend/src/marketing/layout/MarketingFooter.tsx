import { Link } from "react-router-dom";
import { BrandMark } from "../../shared/components/BrandMark";
import { footerColumns } from "../navigation/navigation";

export function MarketingFooter() {
  return (
    <footer className="bg-[#12163e] px-5 py-14 text-white lg:px-8">
      <div className="mx-auto grid max-w-7xl gap-10 md:grid-cols-[1.2fr_2fr]">
        <div>
          <BrandMark inverse />
          <p className="mt-5 max-w-sm text-sm leading-7 text-white/58">
            面向财务、采购与 IT 团队的企业软件采购、支出和治理平台。
          </p>
        </div>
        <nav aria-label="页脚导航" className="grid gap-8 sm:grid-cols-2 lg:grid-cols-5">
          {footerColumns.map(column => (
            <section key={column.title}>
              <h2 className="text-sm font-extrabold text-white">{column.title}</h2>
              <div className="mt-4 grid gap-3">
                {column.links.map(link => (
                  <Link className="text-sm font-medium text-white/58 hover:text-white" key={link.to} to={link.to}>
                    {link.label}
                  </Link>
                ))}
              </div>
            </section>
          ))}
        </nav>
      </div>
    </footer>
  );
}
