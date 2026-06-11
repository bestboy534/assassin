# 组织、多租户与 RBAC 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现组织、成员、邀请、部门、成本中心、角色与权限，并用后端租户边界阻止任何跨组织访问。

**Architecture:** 用户可属于多个组织；每个请求从会话与路径解析当前组织。Repository 默认要求 `OrganizationContext`，权限服务基于角色、资源范围和操作判定。平台角色与组织角色分离。

**Tech Stack:** FastAPI、SQLAlchemy、PostgreSQL、React、TanStack Query、Pytest 参数化权限测试

---

## 权限命名

```text
organization.read
organization.manage
members.read
members.invite
members.manage
roles.manage
applications.read
applications.manage
procurement.request
procurement.approve
vendors.manage
contracts.manage
spend.read
spend.manage
payments.manage
reports.read
audit.read
integrations.manage
billing.manage
```

## Task 1: 组织与成员模型

- [ ] **Step 1: 写租户隔离失败测试**

```py
async def test_member_cannot_read_other_organization(auth_client, org_a, org_b):
    client = auth_client(user=org_a.member)
    response = await client.get(f"/api/v1/organizations/{org_b.id}")
    assert response.status_code == 404
```

- [ ] **Step 2: 创建迁移**

创建 `organizations`、`organization_members`、`departments`、`cost_centers`、`legal_entities`、`locations`。

成员唯一约束：

```py
sa.UniqueConstraint("organization_id", "user_id", name="uq_org_member")
```

- [ ] **Step 3: 实现组织上下文**

```py
@dataclass(frozen=True)
class OrganizationContext:
    organization_id: UUID
    user_id: UUID
    membership_id: UUID

async def require_organization_context(
    organization_id: UUID,
    user: AuthenticatedUser = Depends(require_user),
) -> OrganizationContext:
    ...
```

不存在或无权限统一返回 404。

- [ ] **Step 4: 创建 API**

```text
POST /api/v1/organizations
GET  /api/v1/organizations
GET  /api/v1/organizations/{id}
PATCH /api/v1/organizations/{id}
```

创建组织的用户自动成为唯一 owner。

- [ ] **Step 5: 运行并提交**

```powershell
python -m pytest app/domains/organizations/tests/test_organizations.py -q
git add backend/app/domains/organizations backend/migrations
git commit -m "feat: add tenant organizations"
```

## Task 2: 邀请与成员生命周期

- [ ] **Step 1: 写邀请测试**

```py
async def test_accept_invitation_creates_single_membership(client, invitation):
    first = await client.post("/api/v1/invitations/accept", json={"token": invitation.raw_token})
    second = await client.post("/api/v1/invitations/accept", json={"token": invitation.raw_token})
    assert first.status_code == 200
    assert second.status_code == 409
    assert await membership_count(invitation.organization_id, invitation.email) == 1
```

- [ ] **Step 2: 创建邀请端点**

```text
POST   /organizations/{id}/invitations
GET    /organizations/{id}/invitations
POST   /organizations/{id}/invitations/{invitation_id}/resend
DELETE /organizations/{id}/invitations/{invitation_id}
POST   /invitations/accept
```

Token 哈希存储，7 天过期。

- [ ] **Step 3: 成员状态操作**

```text
PATCH /organizations/{id}/members/{member_id}
POST  /organizations/{id}/members/{member_id}/suspend
POST  /organizations/{id}/members/{member_id}/restore
DELETE /organizations/{id}/members/{member_id}
```

暂停成员立即撤销其所有组织会话授权。

- [ ] **Step 4: 最后 owner 保护**

写测试证明最后一个 owner 不能降级、删除或离开组织。

- [ ] **Step 5: Commit**

```powershell
git add backend/app/domains/organizations
git commit -m "feat: add organization invitations and membership lifecycle"
```

## Task 3: 角色、权限与资源范围

- [ ] **Step 1: 写权限矩阵测试**

```py
@pytest.mark.parametrize("role,permission,allowed", [
    ("owner", "organization.manage", True),
    ("finance_admin", "spend.manage", True),
    ("finance_admin", "roles.manage", False),
    ("auditor", "audit.read", True),
    ("member", "procurement.request", True),
])
async def test_default_role_permissions(permission_service, role, permission, allowed):
    assert await permission_service.allowed(role, permission) is allowed
```

- [ ] **Step 2: 创建模型**

```text
roles
permissions
role_permissions
member_roles
role_scopes
```

系统角色不可删除；自定义角色可配置权限和部门/成本中心范围。

- [ ] **Step 3: 实现授权依赖**

```py
def require_permission(permission: str):
    async def dependency(
        context: OrganizationContext = Depends(require_organization_context),
        service: PermissionService = Depends(),
    ) -> OrganizationContext:
        await service.require(context, permission)
        return context
    return dependency
```

- [ ] **Step 4: 创建角色 API**

```text
GET    /organizations/{id}/roles
POST   /organizations/{id}/roles
PATCH  /organizations/{id}/roles/{role_id}
DELETE /organizations/{id}/roles/{role_id}
PUT    /organizations/{id}/members/{member_id}/roles
```

- [ ] **Step 5: 运行并提交**

```powershell
python -m pytest app/domains/organizations/tests/test_permissions.py -q
git add backend/app/domains/organizations
git commit -m "feat: add organization role based access control"
```

## Task 4: 部门、成本中心与组织维度

- [ ] **Step 1: 写层级约束测试**

```py
async def test_department_cannot_parent_itself(department_service, department):
    with pytest.raises(ValidationError):
        await department_service.update(department.id, parent_id=department.id)
```

- [ ] **Step 2: 实现 CRUD**

对部门、成本中心、法人实体、地点提供列表、创建、更新和停用。已被业务数据引用的维度只能停用，不能硬删除。

- [ ] **Step 3: 导入维度**

CSV 导入先预览：

```json
{
  "valid_rows": 93,
  "invalid_rows": 2,
  "errors_file_id": "..."
}
```

确认后才写入。

- [ ] **Step 4: 运行并提交**

```powershell
python -m pytest app/domains/organizations/tests/test_dimensions.py -q
git add backend/app/domains/organizations
git commit -m "feat: add organization dimensions"
```

## Task 5: 前端组织设置

- [ ] **Step 1: 写组织切换测试**

```tsx
test("switching organization invalidates organization scoped queries", async () => {
  renderWorkspace();
  await user.selectOptions(screen.getByLabelText("当前组织"), ORG_B_ID);
  expect(queryClient.invalidateQueries).toHaveBeenCalledWith(
    expect.objectContaining({ queryKey: ["organization", ORG_A_ID] }),
  );
});
```

- [ ] **Step 2: 创建页面**

```text
/app/settings/organization
/app/settings/members
/app/settings/roles
/app/settings/departments
/app/settings/cost-centers
```

- [ ] **Step 3: 权限感知 UI**

无权限用户可查看允许的数据，但不渲染修改按钮；API 403 时显示权限错误，不重定向成 404 页面。

- [ ] **Step 4: E2E**

覆盖：

- 创建组织
- 邀请成员
- 接受邀请
- 分配角色
- 暂停成员
- 切换组织
- 跨租户 URL 返回 404

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/workspace/settings frontend/src/shared/auth
git commit -m "feat: add organization administration UI"
```

## Task 6: 全仓库租户边界扫描

- [ ] **Step 1: 编写 Repository 约束测试**

创建测试辅助函数，遍历所有组织级模型，断言存在非空 `organization_id`。

- [ ] **Step 2: 禁止裸查询**

组织级 Repository 构造函数必须接收 `OrganizationContext`；代码审查规则禁止 Router 直接使用 Session 查询组织级表。

- [ ] **Step 3: 运行安全测试**

```powershell
python -m pytest -m tenant_isolation -q
```

Expected: 每个资源类型至少有跨租户读、写、列表和 ID 猜测测试。

- [ ] **Step 4: Commit**

```powershell
git add backend/tests/security backend/app
git commit -m "test: enforce tenant isolation across repositories"
```

## 完成验收

- [ ] 所有业务表包含 `organization_id`。
- [ ] 跨租户访问返回 404。
- [ ] 最后一个 owner 受到保护。
- [ ] 成员暂停立即失效。
- [ ] 自定义角色由后端执行权限。
- [ ] 组织切换清理旧组织缓存。

