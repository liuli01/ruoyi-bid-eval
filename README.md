# 海外项目投标评审系统

基于 **RuoYi-Vue3-FastAPI** 构建的海外项目 AI 评审系统，面向中建海外事业部投标审批场景。

## 功能菜单

```
评审概览    Dashboard — 四门户入口卡片 + 项目统计 + 最近评审
项目管理    项目 CRUD + 文件上传/分类/预览 + 启动评审 + 评审历史
评审管理    全量评审列表 + 意见详情 + Word 导出 + SSE 实时进度
规则管理    110+ 条 P/R 类规则可视化筛选 + 展开原文详情
风险会商    5 步审批流（经办人→拟稿→领导→核稿→报送）+ 材料完整性核验
项目立项    触发条件 + 5 步审批流 + 结论同步
一事一议    受理条件核验（含 LLM 版本）+ 7 项硬阻断 + 按承接模式阈值判定 + 审批
审计追溯    操作日志 + 评审记录时间线
F3签报     子企业回复函 LLM 解析（R-T1~T6 分类）+ 签报 Word 生成
国别字典    31 国 CRUD（区域/风险等级/政治体制）
系统设置    LLM 配置 + 模型测试 + 评审参数
```

## 技术栈

| 层 | 技术 |
|---|------|
| 后端框架 | FastAPI + SQLAlchemy 2.0 (async) + MySQL 8.0 |
| 前端框架 | Vue 3 + Element Plus + Vite |
| LLM 调用 | litellm + DeepSeek API（内网可切集团 R1 671B） |
| 规则引擎 | YAML 配置 + LLM 逐条判断（110+ 条规则，13 批次并行/顺序执行） |
| 实时推送 | SSE（Server-Sent Events） |
| 文档解析 | pypdf / python-docx / openpyxl |
| Word 导出 | python-docx → 会商意见函 / 签报 |
| 包管理 | uv (Python) / npm (前端) |
| 容器化 | Docker + Docker Compose，GitHub Actions CI |

## 快速启动

### 前置条件

- MySQL 8.0（Docker 或本地）
- Redis 7+（Docker 或本地）
- Python 3.10+
- Node.js 18+

### 后端启动

```bash
cd ruoyi-fastapi-backend

# 安装依赖
uv sync

# 配置环境变量
cp .env.dev .env
# 编辑 .env，配置数据库密码和 DS_API_KEY

# 初始化数据库表
docker exec -i mysql-bid-eval mysql -uroot -pmysqlroot bid_eval < sql/ruoyi-fastapi.sql
docker exec -i mysql-bid-eval mysql -uroot -pmysqlroot bid_eval < sql/eval_init.sql
docker exec -i mysql-bid-eval mysql -uroot -pmysqlroot bid_eval < sql/portal_init.sql

# 启动（端口 9100）
uv run python app.py
```

### 前端启动

```bash
cd ruoyi-fastapi-frontend

npm install
node node_modules/vite/bin/vite.js --host 0.0.0.0 --port 80
```

### Docker Compose 一键启动

```bash
DS_API_KEY=sk-xxx docker compose up -d
```

访问 http://localhost:80 (前端) / http://localhost:9100/docs (API)

### 测试用户

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员（全部权限） |
| waishi | admin123 | 外事专员（会商+立项） |
| yiyi | admin123 | 一事一议专员 |
| reviewer | admin123 | 评审专员（评审模块） |
| leader | admin123 | 海外部领导（全部） |

## API 概览

### 评审核心（`/eval/*`）

| 端点 | 说明 |
|------|------|
| `GET /eval/dashboard` | 首页统计 |
| `GET /eval/project/list` | 项目分页列表 |
| `POST /eval/project` | 创建项目 |
| `GET /eval/project/{id}` | 项目详情 |
| `DELETE /eval/project/{id}` | 删除项目 |
| `POST /eval/project/{id}/upload` | 上传材料（支持 category 分类） |
| `GET /eval/project/{id}/materials` | 材料列表 |
| `GET /eval/material/{id}/download` | 文件下载/在线预览 |
| `GET /eval/project/{id}/reviews` | 评审历史 |
| `POST /eval/review/start` | 启动评审（异步 + SSE 推送） |
| `GET /eval/review/{id}` | 评审状态 |
| `GET /eval/review/{id}/progress` | SSE 实时进度 |
| `GET /eval/review/{id}/opinions` | 评审意见 |
| `GET /eval/review/{id}/export` | Word 导出 |
| `GET /eval/review/list` | 评审列表 |
| `GET /eval/audit/{project_id}` | 审计时间线 |
| `POST /eval/f3/generate` | F3 签报生成 |
| `GET /eval/rules` | 规则列表（支持 type/level/keyword 筛选） |
| `GET/POST/PUT/DELETE /eval/country` | 国别字典 CRUD |
| `GET/POST /eval/settings` | 系统设置读写 |
| `GET/POST /eval/llm/status` | LLM 配置状态 |
| `POST /eval/llm/test` | LLM 连通性测试 |

### 三门户（`/portal/*`）

| 端点 | 说明 |
|------|------|
| `GET/POST /portal/consultation` | 会商列表/创建 |
| `POST /portal/consultation/{id}/approve` | 会商审批推进 |
| `GET /portal/consultation/{id}/check-materials` | 材料完整性核验 |
| `GET/POST /portal/approval` | 立项列表/创建 |
| `POST /portal/approval/{id}/approve` | 立项审批推进 |
| `GET/POST /portal/yiyi` | 一事一议列表/创建 |
| `POST /portal/yiyi/{id}/check` | 受理条件核验（规则引擎） |
| `POST /portal/yiyi/{id}/llm-check` | 受理条件核验（LLM） |
| `POST /portal/yiyi/{id}/approve` | 一事一议审批 |
| `POST /portal/f3/parse-reply` | 回复函 LLM 解析 |

## 测试

### 后端测试（13 项，含真实 LLM 调用，约 2 分钟）

```bash
cd ruoyi-fastapi-backend
uv run pytest tests/test_eval_comprehensive.py -v
```

测试覆盖：项目 CRUD / 文件上传分类 / 评审流水线 / LLM 状态 / 权限校验

### E2E 测试（Playwright，7 项核心路径）

```bash
# 首次需安装浏览器
npx playwright install chromium

# 运行（需确保前端:80 + 后端:9100 已在运行）
node e2e-test.mjs
```

测试路径：首页 → 项目管理 → 会商 → 一事一议 → 规则 → 国别 → 设置

## 功能清单 V2 覆盖

全部 **53 项功能** 已完成，按板块：

| 板块 | P0 | 完成 |
|------|:--:|:----:|
| 系统门户与首页 | 4 | ✅ 4/4 |
| 重大项目风险会商 | 10 | ✅ 10/10 |
| 特定项目立项 | 9 | ✅ 9/9 |
| 一事一议 | 11 | ✅ 11/11 |
| 项目评审 | 13 | ✅ 13/13 |
| 系统管理 | 6 | ✅ 6/6 |

## Docker 构建（CI）

Tag 推送自动构建（GitHub Actions）：

```bash
git tag v1.0.0
git push origin v1.0.0
```

构建产物推送到 `ghcr.io/<repo>-backend` 和 `ghcr.io/<repo>-frontend`。

## 注意事项

### 环境变量

- `DS_API_KEY`：DeepSeek API Key（必填，否则 LLM 功能不可用）
- `DB_PASSWORD`：数据库密码（默认 `mysqlroot`）
- `REVIEW_MODE`：评审模式（`complete`/`standard`/`fast`，默认 `complete`）

### 已知限制

- 后端 POST 端点使用 `DBSessionDependency()` 在某些环境下存在 greenlet 兼容性问题，已通过`后台线程 + 同步引擎`方案绕过
- 文件预览仅支持 PDF 和纯文本格式，DOCX/XLSX 需下载查看
- 国别字典为静态数据，需通过管理界面增删改
- 系统设置中的 LLM API Key 修改后需重启后端生效（当前仅持久化到数据库，未热加载）

### 生产部署

- `APP_RELOAD` 务必设为 `false`（默认已关闭）
- 前端需构建静态文件部署：`npm run build:docker`
- Nginx 需配置 `/docker-api` 代理到后端 `:9100`（参见 `nginx.conf`）
- 数据库连接池参数按服务器规格调整（`DB_POOL_SIZE`/`DB_MAX_OVERFLOW`）

### 数据库编码

- **创建数据库**时务必指定 `utf8mb4` 字符集：
  ```sql
  CREATE DATABASE bid_eval DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  ```
- **导入 SQL** 时使用 `--default-character-set=utf8mb4`：
  ```bash
  mysql --default-character-set=utf8mb4 bid_eval < init.sql
  ```
- **后端连接 URL** 需加 `?charset=utf8mb4`（已配置在 `config/database.py`）：
  ```
  mysql+asyncmy://user:pass@host:3306/bid_eval?charset=utf8mb4
  ```
- 否则中文会以 Latin-1 编码写入数据库，导致 **双编码乱码**（`ç®¡ç†å‘˜` 之类）

### 时区

- MySQL 容器默认时区为 UTC，需改为东八区：
  ```sql
  SET GLOBAL time_zone = '+08:00';
  ```
- 或在 `docker-compose.yml` 的 MySQL 服务中加入：
  ```yaml
  environment:
    - TZ=Asia/Shanghai
  ```
- 后端时区由 Python 运行时决定，Linux 服务器可用 `timedatectl set-timezone Asia/Shanghai`

### 重新部署复原指南

重新初始化数据库后按以下步骤复原：

**1. 数据库初始化（顺序不能错）**
```bash
# 创建数据库
CREATE DATABASE bid_eval_v2 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 导入 SQL
mysql --default-character-set=utf8mb4 bid_eval_v2 < sql/ruoyi-fastapi.sql     # ① 基础表
mysql --default-character-set=utf8mb4 bid_eval_v2 < sql/eval_init.sql         # ② 业务表+菜单+用户
mysql --default-character-set=utf8mb4 bid_eval_v2 < sql/seed_projects.sql     # ③ 国别+项目（可选）
mysql --default-character-set=utf8mb4 bid_eval_v2 < sql/seed_opinions.sql     # ④ 评审意见（可选）

# 关闭验证码 + 设置时区
mysql bid_eval_v2 -e "UPDATE sys_config SET config_value='false' WHERE config_key='sys.account.captchaEnabled'; SET GLOBAL time_zone='+08:00';"
```

**2. 后端配置**
```bash
# .env.dev 中的数据库名（后端加载的是 .env.dev 不是 .env）
DB_DATABASE = 'bid_eval_v2'

# 连接 URL 已加 charset（config/database.py）
# mysql+asyncmy://user:pass@host:3306/bid_eval_v2?charset=utf8mb4
```

**3. 前端已修改的文件**（重新部署时不要覆盖）

| 文件 | 改动 |
|------|------|
| `src/router/index.js` | `/index` → `@/views/dashboard/index` |
| `src/views/dashboard/index.vue` | 重写为 Element Plus 系统看板 |
| `src/store/modules/permission.js` | 路由路径自动补 `/`、子路由不加 `/` |
| `src/views/eval/review/progress.vue` | 修复 `startReview` 命名冲突 |
| `ruoyi-fastapi-frontend/.npmrc` | 配置国内镜像源 |

**4. Docker 构建注意事项**
```dockerfile
FROM node:22-slim                            # 固定版本，不要用 current-slim
ENV NODE_OPTIONS="--max-old-space-size=8192"  # 防 OOM
RUN npm install --registry=https://registry.npmjs.org/
```

**5. 菜单是如何复原的**
- 菜单数据在 `eval_init.sql` 中（已取消注释并修正）
- **父菜单** `component=NULL`（不能用 `'layout'`）
- **门户菜单**用 `type='M'` 目录 + 子菜单空路径（不能直接用 `type='C'`）
- `sys_role_menu` 分配给管理员（`role_id=1`）
