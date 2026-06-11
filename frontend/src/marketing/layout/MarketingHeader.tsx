import { useEffect, useRef, useState } from "react";
import { ChevronDown, Menu, X } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { BrandMark } from "../../shared/components/BrandMark";
import { navigationGroups, type NavigationItem } from "../navigation/navigation";

const CLOSE_DELAY_MS = 2000;

function MenuLink({ item, onNavigate }: { item: NavigationItem; onNavigate: () => void }) {
  const Icon = item.icon;

  return (
    <Link className="mega-link" onClick={onNavigate} to={item.to}>
      <span className="mega-icon">{Icon && <Icon className="h-5 w-5" />}</span>
      <span>
        <strong>{item.label}</strong>
        {item.description && <small>{item.description}</small>}
      </span>
    </Link>
  );
}

export function MarketingHeader() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [openGroup, setOpenGroup] = useState<string | null>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const location = useLocation();

  const cancelClose = () => {
    if (closeTimer.current) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  };

  const closeMenus = () => {
    cancelClose();
    setOpenGroup(null);
    setMobileOpen(false);
  };

  const scheduleClose = () => {
    cancelClose();
    closeTimer.current = setTimeout(() => {
      setOpenGroup(null);
      closeTimer.current = null;
    }, CLOSE_DELAY_MS);
  };

  useEffect(() => closeMenus(), [location.pathname]);
  useEffect(() => () => cancelClose(), []);

  return (
    <header
      className="sticky top-0 z-40 border-b border-white/10 bg-[#3f469e]/95 text-white backdrop-blur"
      onKeyDown={event => {
        if (event.key === "Escape") {
          closeMenus();
        }
      }}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-4 lg:px-8">
        <Link aria-label="返回首页" className="brand-button" onClick={closeMenus} to="/">
          <BrandMark inverse />
        </Link>

        <nav aria-label="主导航" className="hidden items-center gap-1 lg:flex">
          {navigationGroups.map((group, index) => {
            const isOpen = openGroup === group.label;
            const menuId = `desktop-menu-${index}`;

            return (
              <div
                className="relative"
                key={group.label}
                onBlur={event => {
                  if (!event.currentTarget.contains(event.relatedTarget)) {
                    scheduleClose();
                  }
                }}
                onMouseEnter={() => {
                  cancelClose();
                  setOpenGroup(group.label);
                }}
                onMouseLeave={scheduleClose}
              >
                <button
                  aria-controls={menuId}
                  aria-expanded={isOpen}
                  className="inline-flex items-center gap-1 rounded-md px-4 py-2 text-sm font-semibold text-white/88 transition hover:bg-white/10"
                  onClick={() => {
                    cancelClose();
                    setOpenGroup(value => (value === group.label ? null : group.label));
                  }}
                  onFocus={() => {
                    cancelClose();
                    setOpenGroup(group.label);
                  }}
                  type="button"
                >
                  {group.label}
                  <ChevronDown className="h-4 w-4" />
                </button>

                {isOpen && (
                  <div
                    className="mega-menu absolute left-1/2 top-full w-[704px] -translate-x-1/2 translate-y-2 rounded-xl border border-slate-200 bg-white p-0 text-slate-900 shadow-2xl"
                    id={menuId}
                    onMouseEnter={cancelClose}
                    onMouseLeave={scheduleClose}
                  >
                    <div className="border-b border-slate-100 px-8 py-5 text-sm font-black text-[#20245f]">
                      {group.menuTitle}
                    </div>
                    <div className="grid grid-cols-2 gap-x-12 gap-y-8 px-8 py-7">
                      {group.items.map(item => (
                        <MenuLink item={item} key={item.to} onNavigate={closeMenus} />
                      ))}
                    </div>
                    <Link className="mega-feature" onClick={closeMenus} to={group.feature.to}>
                      <span className="mega-icon active">
                        {group.feature.icon && <group.feature.icon className="h-5 w-5" />}
                      </span>
                      <span>
                        <strong>{group.feature.label}</strong>
                        <small>{group.feature.description}</small>
                      </span>
                    </Link>
                  </div>
                )}
              </div>
            );
          })}
          <Link className="rounded-md px-4 py-2 text-sm font-semibold text-white/88 transition hover:bg-white/10" to="/resources/buyers-guide">
            买家指南
          </Link>
          <Link className="rounded-md px-4 py-2 text-sm font-semibold text-white/88 transition hover:bg-white/10" to="/pricing">
            定价
          </Link>
        </nav>

        <div className="hidden items-center gap-3 lg:flex">
          <Link className="text-sm font-semibold text-white/78 transition hover:text-white" to="/login">
            登录
          </Link>
          <Link className="inline-flex min-h-10 items-center rounded-md border border-white/35 px-8 py-2 text-sm font-bold" to="/book-a-demo">
            预约演示
          </Link>
        </div>

        <button
          aria-controls="mobile-navigation"
          aria-expanded={mobileOpen}
          aria-label={mobileOpen ? "关闭菜单" : "打开菜单"}
          className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-white/25 lg:hidden"
          onClick={() => setMobileOpen(value => !value)}
          type="button"
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {mobileOpen && (
        <nav aria-label="移动端主导航" className="mobile-nav border-t border-white/10 px-5 pb-5 lg:hidden" id="mobile-navigation">
          <div className="grid gap-5 pt-4">
            {navigationGroups.map(group => (
              <section key={group.label}>
                <h2 className="px-3 text-xs font-black text-white/55">{group.label}</h2>
                <div className="mt-2 grid">
                  {[group.feature, ...group.items].map(item => (
                    <Link className="rounded-md px-3 py-2.5 text-sm font-semibold text-white/90 hover:bg-white/10" key={item.to} onClick={closeMenus} to={item.to}>
                      {item.label}
                    </Link>
                  ))}
                </div>
              </section>
            ))}
            <div className="grid grid-cols-2 gap-3">
              <Link className="inline-flex min-h-11 items-center justify-center rounded-md border border-white/35 px-3 text-sm font-bold" onClick={closeMenus} to="/book-a-demo">
                预约演示
              </Link>
              <Link className="inline-flex min-h-11 items-center justify-center rounded-md bg-[#cafbff] px-3 text-sm font-bold text-[#17204f]" onClick={closeMenus} to="/signup">
                开始使用
              </Link>
            </div>
          </div>
        </nav>
      )}
    </header>
  );
}
