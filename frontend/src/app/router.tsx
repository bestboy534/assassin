import type { ReactElement } from "react";
import {
  createBrowserRouter,
  type RouteObject,
} from "react-router-dom";
import { MarketingLayout } from "../marketing/layout/MarketingLayout";
import { ApplicationDirectoryPage } from "../marketing/pages/ApplicationDirectoryPage";
import { CareerDetailPage, CareersPage } from "../marketing/pages/CareersPage";
import { CompanyStoryPage, CambridgePage } from "../marketing/pages/CompanyStoryPage";
import { ContactPage } from "../marketing/pages/ContactPage";
import { ContentDetailPage, ContentIndexPage } from "../marketing/pages/ContentIndexPage";
import { GenericSolutionPage } from "../marketing/pages/GenericSolutionPage";
import { HomePage } from "../marketing/pages/HomePage";
import { LegalPage } from "../marketing/pages/LegalPage";
import { NotFoundPage } from "../marketing/pages/NotFoundPage";
import { ReportPage } from "../marketing/pages/ReportPage";
import { SecurityPage } from "../marketing/pages/SecurityPage";
import { SupportMetricsPage } from "../marketing/pages/SupportMetricsPage";
import {
  legacyHashPaths,
  publicPages,
  type PublicPage,
} from "../marketing/content/pages";

function pageElement(page: PublicPage): ReactElement {
  if (page.id === "contact") return <ContactPage />;
  if (page.id === "cambridge") return <CambridgePage />;

  switch (page.kind) {
    case "directory":
      return <ApplicationDirectoryPage />;
    case "story":
      return <CompanyStoryPage />;
    case "careers":
      return <CareersPage />;
    case "content-index":
      return <ContentIndexPage kind={page.id === "podcasts" ? "podcasts" : "press"} />;
    case "report":
      return <ReportPage page={page} />;
    case "legal":
      return <LegalPage page={page} />;
    case "security":
      return <SecurityPage />;
    case "support":
      return <SupportMetricsPage />;
    default:
      return <GenericSolutionPage page={page} />;
  }
}

const publicRouteObjects: RouteObject[] = publicPages.flatMap(page => {
  const canonical: RouteObject = {
    path: page.path,
    element: pageElement(page),
  };
  const aliases = page.aliases
    .filter(alias => alias !== page.path)
    .map(
      (alias): RouteObject => ({
        path: alias,
        element: pageElement(page),
      }),
    );
  return [canonical, ...aliases];
});

export const routes: RouteObject[] = [
  {
    element: <MarketingLayout />,
    children: [
      { index: true, element: <HomePage /> },
      ...publicRouteObjects,
      { path: "/podcasts/:contentSlug", element: <ContentDetailPage kind="podcasts" /> },
      { path: "/press/:contentSlug", element: <ContentDetailPage kind="press" /> },
      { path: "/careers/:roleSlug", element: <CareerDetailPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];

export function resolveLegacyHash(hash: string): string | null {
  const key = hash.replace(/^#\/?/, "").split(/[?#]/, 1)[0];
  return key ? legacyHashPaths[key] ?? null : null;
}

export function applyLegacyHashRedirect() {
  if (typeof window === "undefined") return;
  const target = resolveLegacyHash(window.location.hash);
  if (target) {
    window.history.replaceState(null, "", target);
  }
}

applyLegacyHashRedirect();

export const router = createBrowserRouter(routes);
