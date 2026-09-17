# CueAdmin — 开箱即用的后台管理框架

基于 **FastAPI + Vue 3** 的通用后台管理系统，内置 RBAC 权限、JWT 认证、用户/角色/菜单管理。后端框架从业务项目中剥离而来，前端基于 [vue-pure-admin](https://github.com/pure-admin/vue-pure-admin) 进行定制开发，开箱即用，新项目只需添加业务代码。

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-%3E%3D22.18.0-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.136+-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/vue-3.5+-4FC08D.svg)](https://vuejs.org/)

---

## 功能一览

> 📸 **截图示例**：以下为实际运行截图（存放于 `docs/images/` 目录，Markdown 相对路径引用）。

| 登录页 | 仪表盘 |
|:---:|:---:|
| ![登录页](docs/images/login.png) | ![仪表盘](docs/images/dashboard.png) |

| 用户管理 | 角色管理 |
|:---:|:---:|
| ![用户管理](docs/images/users.png) | ![角色管理](docs/images/roles.png) |

| 菜单管理 | 权限管理 |
|:---:|:---:|
| ![菜单管理](docs/images/menus.png) | ![权限管理](docs/images/permissions.png) |

| 部门管理 |  |
|:---:|:---:|
| ![部门管理](docs/images/departments.png) |  |

| 模块 | 功能 |
|------|------|
| 🔐 **认证系统** | JWT 登录/登出、refresh token 一次性轮换 + 复用检测、Token 黑名单 |
| 🛡️ **权限系统** | RBAC 细粒度权限码，`Security(get_current_user, scopes=[...])` 声明式鉴权，权限码 Redis 缓存 5 分钟 |
| 👤 **用户管理** | 用户 CRUD、角色/岗位分配、软删除、分页、多条件筛选 |
| 🎭 **角色管理** | 角色 CRUD、权限分配、菜单分配、系统角色保护 |
| 📋 **菜单管理** | 无限级树形菜单、图标、排序、隐藏/显示、按角色下发动态路由 |
| 🔑 **权限码管理** | 权限码 CRUD、按 resource 分组 |
| 🏢 **部门管理** | 组织架构树、部门-用户关联、按部门子树筛选 |
| 💼 **岗位管理** | 岗位 CRUD、排序、用户关联 |
| 📖 **元数据** | 错误码数据字典（`GET /api/v1/system/meta/error-codes`） |
| 📦 **基础设施** | 配置管理、异步连接池、Redis 缓存、Loguru 日志、统一异常处理、GZip 压缩 |

---

## 技术栈

| 层 | 技术 |
|----|------|
| **前端框架** | Vue 3 + TypeScript + Vite |
| **UI 组件** | Element Plus + Tailwind CSS |
| **状态管理** | Pinia |
| **后端框架** | FastAPI (Python 3.12+) |
| **ORM** | SQLAlchemy 2.0 (async) + aiomysql |
| **数据库** | MySQL 8.0+ |
| **缓存** | Redis 6.0+ |
| **认证** | JWT (python-jose + bcrypt) |
| **迁移** | Alembic |
| **日志** | Loguru |

---

## 快速开始

### 环境要求

- Python >= 3.12
- Node.js >= 22.18.0
- pnpm >= 10.6
- MySQL 8.0+
- Redis 6.0+

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd CueAdmin
```

### 2. 启动后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入数据库地址和 JWT 密钥

# 创建数据库
mysql -u root -p -e "CREATE DATABASE cueadmin CHARACTER SET utf8mb4"

# 初始化表结构 + 种子数据（24 权限 / 14 菜单 / 4 部门 / 4 岗位 / admin 用户）
python seed.py

# 启动服务 (默认 http://localhost:8000)
uvicorn app.main:app --reload
```

### 3. 启动前端

```bash
cd frontend

# 安装依赖
pnpm install

# 启动开发服务器 (默认 http://localhost:8848)
pnpm dev
```

#### 前端怎么找到后端

前端**带完整域名直连后端**，地址写在 `.env` 里，dev 和 build 走同一套寻址方式：

| 文件 | 用途 | 值 |
|------|------|-----|
| `.env.development` | `pnpm dev` | `http://127.0.0.1:8000` |
| `.env.production` | `pnpm build` | **部署前必须替换成真实域名** |
| `.env.staging` | `pnpm build:staging` | **部署前必须替换** |

> - 后端不在 `127.0.0.1:8000`？改 `.env.development` 里的 `VITE_API_BASE_URL`
> - `.env.production` / `.env.staging` 里现在是占位符 `https://api.example.com`，**不替换的话打包产物所有接口都会失败**
> - 地址会被**写死进构建产物**，同一份 `dist` 不能指向不同后端 —— 要多环境就用 `build:staging` 单独构建

**这就要求后端允许跨域**（`app/main.py` 的 `CORSMiddleware`）。当前配置是 `allow_origins=["*"]` + `allow_credentials=False`，开箱可用；如果哪天把 token 改存 cookie，两项都必须改（`*` 不能和 `credentials=True` 共存）。

### 4. 安装提交钩子

提交前自动检查代码，不合格直接拒绝提交。**在仓库根目录执行**：

```bash
pip install -r backend/requirements-dev.txt
pre-commit install
```

| 检查项 | 工具 | 范围 |
|--------|------|------|
| 后端 lint + 排版 | ruff | `backend/`，规则见 `backend/ruff.toml` |
| 前端 lint + 排版 | lint-staged | `frontend/`，规则见 `frontend/.lintstagedrc` |

> - `.git/hooks/` 不随 `git clone` 分发，每个克隆都要装一次，否则你这台机器上没有钩子。
> - 前端那条要用 `node_modules` 里的工具，所以得排在第 3 步之后。
> - 手动全量跑 `pre-commit run --all-files`；应急绕过 `git commit --no-verify`。

### 5. 登录

| 账号 | 密码 |
|------|------|
| `admin` | `admin123` |

打开 http://localhost:8848 ，使用管理员账号登录即可进入后台。

---

## 改表结构（数据库迁移）

`python seed.py` 只负责**首次建库**（内部是 `Base.metadata.create_all`）。**已有表要改结构，必须走 Alembic**，不要重新跑 seed。

```bash
cd backend

# ① 对比「模型」与「数据库」，生成迁移脚本（只写文件，不动数据库）
alembic revision --autogenerate -m "描述这次改动"

# ② 把迁移应用到数据库
alembic upgrade head

# ③ 随时检查「模型和数据库是否一致」（不写文件、不改库，只报告）
alembic check
```

`alembic check` 输出 `No new upgrade operations detected.` 表示没有漏做的迁移；有差异时会列出待处理的操作。

> ⚠️ **绝不手写 `op.alter_column` 改列定义。**
> 历史事故：手写的 `MODIFY` 没带 `existing_autoincrement` / `existing_server_default`，导致全库主键丢失 `AUTO_INCREMENT`，只能 DROP 重建。
>
> **已知坑**：`alembic/env.py` 未开启 `compare_comment` / `compare_server_default` / `compare_type`，所以 autogenerate **检测不到**注释、默认值、类型的改动——改这三类需要手写迁移（只动对应参数，不要覆盖整列定义）。

### 常用 Alembic 命令

```bash
alembic current             # 当前数据库在哪个版本
alembic history             # 全部迁移脚本列表
alembic check               # 模型与数据库是否一致
alembic upgrade head        # 升到最新
alembic downgrade -1        # 回退一步
```

> `alembic stamp` 只改版本号、**不执行任何 SQL**，用错会让 alembic 误以为迁移已完成，慎用。

---

## 项目结构

```
CueAdmin/
├── backend/                        # 后端 — FastAPI
│   ├── app/
│   │   ├── core/                   # 框架级基础设施（不含业务）
│   │   │   ├── config.py           # .env 配置读取
│   │   │   ├── dependencies.py     # 依赖注入：认证 + 鉴权 + 会话/Redis
│   │   │   ├── security.py         # bcrypt 哈希 + JWT 签发/验证
│   │   │   ├── response.py         # 统一 ApiResponse + PageData
│   │   │   ├── exceptions.py       # BusinessException + 错误码枚举
│   │   │   ├── error_handler.py    # 全局异常处理器
│   │   │   ├── paginate.py         # 通用分页（page / page_size / has_more）
│   │   │   ├── logger.py           # Loguru 配置
│   │   │   └── storage/            # 连接资源
│   │   │       ├── db.py           # 异步引擎、Session 工厂、Base、TimestampMixin
│   │   │       └── redis.py        # Redis 客户端工厂（create_redis）
│   │   ├── system/                 # 业务模块
│   │   │   ├── api/v1/             # 路由层 — HTTP 端点 + 权限绑定
│   │   │   │   ├── auth.py             # 登录、登出、刷新令牌
│   │   │   │   ├── users.py            # 用户 CRUD
│   │   │   │   ├── roles.py            # 角色 + 权限/菜单分配
│   │   │   │   ├── menus.py            # 菜单树 CRUD
│   │   │   │   ├── permissions.py      # 权限码 CRUD
│   │   │   │   ├── departments.py      # 部门树 CRUD
│   │   │   │   ├── posts.py            # 岗位 CRUD
│   │   │   │   ├── routes.py           # 当前用户的动态路由
│   │   │   │   ├── meta.py             # 错误码数据字典
│   │   │   │   └── router.py           # 路由聚合 → /api/v1
│   │   │   ├── services/           # 业务层 — 编排 + 事务边界（commit/rollback 只在这里）
│   │   │   ├── repositories/       # 数据层 — SQL 查询（只查/存，不 commit，不抛业务异常）
│   │   │   ├── models/             # SQLAlchemy ORM 模型
│   │   │   │   ├── associations.py     # M2M 中间表
│   │   │   │   └── user / role / permission / menu / department / post
│   │   │   └── schemas/            # Pydantic — 请求/响应模型
│   │   ├── utils/                  # 纯函数工具（如 tree.py 树遍历）
│   │   └── main.py                 # FastAPI 入口：lifespan、中间件、异常处理
│   ├── alembic/                    # 数据库迁移脚本
│   ├── tests/                      # pytest 测试
│   ├── seed.py                     # 种子数据（权限/菜单/角色/部门/岗位/admin 用户）
│   ├── requirements.txt            # 生产依赖
│   ├── requirements-dev.txt        # 测试 + 钩子依赖
│   └── .env.example
│
├── frontend/                       # 前端 — Vue 3 + Element Plus
│   ├── src/
│   │   ├── views/                  # 页面组件
│   │   │   ├── login/              # 登录页
│   │   │   ├── welcome/            # 仪表盘
│   │   │   └── system/             # 系统管理（用户/角色/菜单/权限/部门/岗位/错误码）
│   │   ├── router/                 # 动态路由 + 权限守卫
│   │   ├── store/                  # Pinia 状态管理
│   │   ├── api/                    # 后端接口调用
│   │   └── layout/                 # 布局系统（侧边栏/顶栏/标签页）
│   ├── package.json
│   └── vite.config.ts
│
├── docs/
│   ├── images/                     # 📸 README 截图存放目录
│   ├── 通路1系统开发文档.md          # 开发文档
│   └── 通路1系统界面演示.html        # 界面演示
├── DESIGN.md                       # 框架设计文档
└── LICENSE
```

### 分层调用链

```
api/  →  services/  →  repositories/  →  models/
          （事务边界）    （只查/存）
```

- **`api/`**：只做 HTTP 入参出参、依赖注入（`SessionDep` / `CurrentUser` / `Security(scopes=...)`），不写业务逻辑
- **`services/`**：业务编排，**唯一持有 `commit` / `rollback` 的地方**（一个业务操作常含多个 repo 调用，要保证要么全成、要么全不成）
- **`repositories/`**：SQL 查询与 `session.add/delete` 的对象准备，查不到返回 `None`，**不抛业务异常、不提交事务**
- **`models/`**：SQLAlchemy ORM 表定义

---

## 开发命令

```bash
# ---------- 后端 ----------
cd backend

uvicorn app.main:app --reload      # 启动开发服务
pytest                             # 跑全部测试（SQLite 内存库 + fakeredis，不碰真实 MySQL/Redis）
pytest -q                          # 精简输出
pytest tests/test_auth.py          # 只跑某个文件

# ---------- 前端 ----------
cd frontend

pnpm dev                           # 启动开发服务器
pnpm typecheck                     # TypeScript 类型检查
pnpm build                         # 生产构建
pnpm lint                          # eslint + prettier + stylelint
```

> 后端测试用 `dependency_overrides` 把数据库换成 SQLite 内存库、Redis 换成 `fakeredis`，**不会读写你的 MySQL/Redis**。
> 例外：`/health` 直接使用全局 `async_engine`，绕过依赖注入——给它写测试时会连真实数据库。

---

## 在新项目中使用

只需 3 步，把 CueAdmin 作为新项目的起点：

```bash
# 1. 复制后端框架
cp -r CueAdmin/backend myproject/

# 2. 在 system/ 下添加你的业务模块（models → schemas → repositories → services → api）

# 3. 在 api/v1/router.py 注册新路由
v1_router.include_router(patient.router, prefix="/patients", tags=["患者"])
```

**核心原则：不改框架文件，只加新的。** 升级框架时只需替换核心文件，业务代码不受影响。

---

## API 文档

启动后端后访问：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **错误码字典**: http://localhost:8000/api/v1/system/meta/error-codes

所有接口统一返回 `{ code, message, data }`，业务错误也返回 HTTP 200，前端只需读 `code`。

---

## License

MIT © 2026 [s77mple](https://github.com/s77mple)
