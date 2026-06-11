# 数据库、异步任务与对象存储实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 SQLite 原型升级为 PostgreSQL 生产数据层，并建立 Alembic、Redis 任务队列、Outbox、对象存储和可查询任务状态。

**Architecture:** SQLAlchemy 2 异步会话承载事务；Alembic 管理迁移。数据库 Outbox 与业务写入同事务，Worker 从 Redis 队列消费。文件先进入隔离 bucket，扫描通过后移动到正式 bucket。

**Tech Stack:** PostgreSQL、SQLAlchemy 2、Alembic、Pydantic、Redis、RQ/Dramatiq、MinIO/S3、Pytest、Testcontainers

---

## 文件结构

**Create**

- `backend/app/core/database.py`
- `backend/app/core/ids.py`
- `backend/app/core/transactions.py`
- `backend/app/infrastructure/queue/client.py`
- `backend/app/infrastructure/queue/worker.py`
- `backend/app/infrastructure/queue/jobs.py`
- `backend/app/infrastructure/storage/base.py`
- `backend/app/infrastructure/storage/s3.py`
- `backend/app/infrastructure/storage/scanner.py`
- `backend/app/domains/jobs/models.py`
- `backend/app/domains/jobs/router.py`
- `backend/app/domains/outbox/models.py`
- `backend/app/domains/outbox/repository.py`
- `backend/migrations/env.py`
- `backend/migrations/versions/*_initial_infrastructure.py`
- `backend/tests/integration/test_database.py`
- `backend/tests/integration/test_outbox.py`
- `backend/tests/integration/test_storage.py`

**Modify**

- `backend/app/config.py`
- `backend/app/main.py`
- `backend/requirements.txt`
- `docker-compose.yml`
- `backend/.env.example`

## Task 1: PostgreSQL 与 SQLAlchemy 会话

- [ ] **Step 1: 写失败的事务测试**

```py
async def test_transaction_rolls_back_all_changes(session, sample_model):
    async with transaction(session):
        session.add(sample_model(name="first"))
        raise RuntimeError("force rollback")

    assert await session.scalar(select(func.count(sample_model.id))) == 0
```

- [ ] **Step 2: 添加依赖**

在 `requirements.txt` 增加：

```text
sqlalchemy[asyncio]
asyncpg
alembic
redis
dramatiq[redis]
boto3
python-multipart
testcontainers[postgres]
```

- [ ] **Step 3: 实现数据库配置**

```py
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session
```

`Settings` 增加 `database_url`，生产环境禁止 SQLite。

- [ ] **Step 4: 运行集成测试**

```powershell
python -m pytest tests/integration/test_database.py -q
```

Expected: commit、rollback、连接失败恢复测试通过。

- [ ] **Step 5: Commit**

```powershell
git add backend/app/core backend/app/config.py backend/requirements.txt backend/tests/integration
git commit -m "feat: add PostgreSQL transaction foundation"
```

## Task 2: Alembic 迁移与旧数据过渡

- [ ] **Step 1: 初始化迁移环境**

`migrations/env.py` 从应用 Metadata 读取模型，使用同步迁移 URL。

- [ ] **Step 2: 创建基础迁移**

迁移创建：

```text
jobs
outbox_events
files
```

统一字段：

```py
sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True)
sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())
```

- [ ] **Step 3: 写迁移测试**

```py
def test_migrations_upgrade_empty_database(postgres_url):
    run_alembic(postgres_url, "upgrade", "head")
    assert {"jobs", "outbox_events", "files"} <= inspect_tables(postgres_url)
```

- [ ] **Step 4: 迁移现有 SQLite 分析记录**

创建一次性命令：

```powershell
python -m app.cli migrate-sqlite-analysis --source data/saas_assassin.db
```

命令只迁移结构化 `analysis_runs` 和 items，不迁移原始账单；重复执行按旧 run ID 幂等。

- [ ] **Step 5: Commit**

```powershell
git add backend/migrations backend/app/cli
git commit -m "feat: add managed PostgreSQL migrations"
```

## Task 3: Job 状态与 Redis Worker

- [ ] **Step 1: 写任务状态测试**

```py
async def test_job_transitions_are_valid(job_service):
    job = await job_service.create("audit.parse", organization_id=ORG_ID)
    await job_service.start(job.id)
    await job_service.succeed(job.id, result={"analysis_run_id": str(RUN_ID)})
    assert (await job_service.get(job.id)).status == "succeeded"
    with pytest.raises(InvalidJobTransition):
        await job_service.fail(job.id, code="late_failure")
```

- [ ] **Step 2: 创建 Job 模型**

状态：

```py
JobStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]
```

字段包含 `organization_id`、`job_type`、`progress`、`result_json`、`error_code`、`attempts`、`trace_id`。

- [ ] **Step 3: 实现队列封装**

```py
class JobQueue:
    def enqueue(self, job_id: UUID, task_name: str, payload: dict[str, Any]) -> None: ...
```

Worker 只接收 ID 和最小 payload，不序列化 ORM 对象。

- [ ] **Step 4: 创建 Job API**

```text
GET  /api/v1/jobs/{job_id}
POST /api/v1/jobs/{job_id}/retry
POST /api/v1/jobs/{job_id}/cancel
```

只能访问同组织 Job；retry 仅允许可重试失败。

- [ ] **Step 5: 运行**

```powershell
python -m pytest app/domains/jobs tests/integration/test_jobs.py -q
```

Expected: 状态机、组织隔离和重试测试通过。

- [ ] **Step 6: Commit**

```powershell
git add backend/app/domains/jobs backend/app/infrastructure/queue
git commit -m "feat: add reliable asynchronous jobs"
```

## Task 4: Transactional Outbox

- [ ] **Step 1: 写同事务测试**

```py
async def test_business_write_and_outbox_commit_together(session, outbox):
    async with transaction(session):
        entity = Example(name="created")
        session.add(entity)
        await outbox.add("example.created", entity.id, {"name": entity.name})
    assert await session.get(Example, entity.id)
    assert await find_outbox(session, aggregate_id=entity.id)
```

- [ ] **Step 2: 实现 Outbox**

状态 `pending -> processing -> processed/dead_letter`。消费者使用：

```sql
SELECT ... FOR UPDATE SKIP LOCKED
```

抢占批次，处理超时可回收。

- [ ] **Step 3: 添加幂等收件箱**

创建 `inbox_receipts(consumer, event_id)` 唯一键。消费者在副作用与 receipt 同事务提交。

- [ ] **Step 4: 运行**

```powershell
python -m pytest tests/integration/test_outbox.py -q
```

Expected: 崩溃重试不会重复副作用。

- [ ] **Step 5: Commit**

```powershell
git add backend/app/domains/outbox backend/migrations
git commit -m "feat: add transactional outbox delivery"
```

## Task 5: 对象存储与病毒扫描

- [ ] **Step 1: 写隔离上传测试**

```py
async def test_uploaded_file_is_not_downloadable_before_scan(file_service):
    file = await file_service.create_upload(ORG_ID, "invoice.pdf", "application/pdf")
    assert file.status == "quarantined"
    with pytest.raises(FileNotAvailable):
        await file_service.create_download_url(file.id)
```

- [ ] **Step 2: 定义 Storage Adapter**

```py
class ObjectStorage(Protocol):
    def presign_upload(self, key: str, content_type: str, expires: int) -> str: ...
    def presign_download(self, key: str, expires: int) -> str: ...
    def move(self, source: str, destination: str) -> None: ...
    def delete(self, key: str) -> None: ...
```

- [ ] **Step 3: 实现流程**

1. API 创建 `files` 记录和隔离区上传 URL。
2. 客户端上传后调用 complete。
3. Worker 校验大小、MIME、文件签名并调用扫描器。
4. 通过后移至组织正式前缀并设为 `available`。
5. 失败设为 `rejected` 并删除对象。

- [ ] **Step 4: 创建端点**

```text
POST /api/v1/files/uploads
POST /api/v1/files/{id}/complete
GET  /api/v1/files/{id}/download
DELETE /api/v1/files/{id}
```

- [ ] **Step 5: 运行**

```powershell
python -m pytest tests/integration/test_storage.py -q
```

Expected: 隔离、扫描、下载过期和组织隔离测试通过。

- [ ] **Step 6: Commit**

```powershell
git add backend/app/infrastructure/storage backend/app/domains/files backend/migrations
git commit -m "feat: add quarantined object storage"
```

## Task 6: Docker Compose 开发环境

- [ ] **Step 1: 扩展服务**

`docker-compose.yml` 增加：

```yaml
postgres:
  image: postgres:16
  environment:
    POSTGRES_DB: assassin
    POSTGRES_USER: assassin
    POSTGRES_PASSWORD: local_only
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U assassin"]

redis:
  image: redis:7-alpine

minio:
  image: minio/minio
  command: server /data --console-address ":9001"
```

增加 `worker` 服务，与 backend 使用同一镜像但不同启动命令。

- [ ] **Step 2: 更新环境模板**

`.env.example` 明确数据库、Redis、S3 endpoint、bucket、访问密钥和签名 URL 过期时间。

- [ ] **Step 3: 验证**

```powershell
docker compose config
docker compose up -d postgres redis minio
docker compose run --rm backend alembic upgrade head
docker compose ps
```

Expected: 三个基础服务 healthy，迁移成功。

- [ ] **Step 4: Commit**

```powershell
git add docker-compose.yml backend/.env.example backend/Dockerfile
git commit -m "dev: add local data and worker infrastructure"
```

## 完成验收

- [ ] 空数据库可升级到 head。
- [ ] 事务 rollback 不留下部分数据。
- [ ] Job、Outbox 和 Inbox 均有状态与幂等测试。
- [ ] 文件扫描前不可下载。
- [ ] 对象存储按组织隔离。
- [ ] 本地 Docker 环境一条命令可启动。

