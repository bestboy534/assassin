import { useState } from "react";
import { ArrowRight, LockKeyhole } from "lucide-react";
import { Link } from "react-router-dom";
import { loginAccount, registerAccount, type AuthSession } from "../../app/api";
import { Button } from "../../shared/components/Button";

type AuthMode = "login" | "signup";

function workspaceUrl(session: AuthSession) {
  const firstOrganization = session.organizations[0];
  return `/app/${firstOrganization?.slug ?? "workspace"}/dashboard`;
}

export function AuthPage({ mode }: { mode: AuthMode }) {
  const isSignup = mode === "signup";
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  return (
    <section className="auth-page">
      <div className="auth-panel">
        <div>
          <span className="detail-badge">
            <LockKeyhole className="h-4 w-4" />
            {isSignup ? "创建工作区" : "安全登录"}
          </span>
          <h1>{isSignup ? "从导入第一批软件支出开始" : "登录你的软件管理工作区"}</h1>
          <p>
            {isSignup
              ? "创建账号后会自动生成第一个组织工作区，随后即可继续连接账单、应用目录和审批流程。"
              : "使用邮箱和密码进入工作区。企业单点登录、多因素认证和恢复码将在账号安全计划中继续增强。"}
          </p>
        </div>

        <form
          className="auth-form"
          onSubmit={async event => {
            event.preventDefault();
            setError(null);
            setLoading(true);
            const form = new FormData(event.currentTarget);
            try {
              const session = isSignup
                ? await registerAccount({
                    email: String(form.get("email") ?? ""),
                    password: String(form.get("password") ?? ""),
                    displayName: String(form.get("displayName") ?? ""),
                    organizationName: String(form.get("organizationName") ?? ""),
                  })
                : await loginAccount({
                    email: String(form.get("email") ?? ""),
                    password: String(form.get("password") ?? ""),
                  });
              window.location.assign(workspaceUrl(session));
            } catch (caught) {
              setError(caught instanceof Error ? caught.message : "请求失败，请稍后再试");
            } finally {
              setLoading(false);
            }
          }}
        >
          {isSignup && (
            <>
              <label>
                姓名
                <input autoComplete="name" name="displayName" required />
              </label>
              <label>
                组织名称
                <input autoComplete="organization" name="organizationName" required />
              </label>
            </>
          )}
          <label>
            工作邮箱
            <input autoComplete="email" name="email" required type="email" />
          </label>
          <label>
            密码
            <input
              autoComplete={isSignup ? "new-password" : "current-password"}
              minLength={12}
              name="password"
              required
              type="password"
            />
          </label>
          {error && <p className="auth-error" role="alert">{error}</p>}
          <Button type="submit" variant="dark">
            {loading ? "处理中..." : isSignup ? "创建工作区" : "登录"}
            <ArrowRight className="h-4 w-4" />
          </Button>
          <p className="auth-switch">
            {isSignup ? "已经有账号？" : "还没有账号？"}
            <Link to={isSignup ? "/login" : "/signup"}>
              {isSignup ? "前往登录" : "创建工作区"}
            </Link>
          </p>
        </form>
      </div>
    </section>
  );
}
