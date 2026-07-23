# CueAdmin — 后端管理框架剥离设计

## 一、目标

从「握力数据采集」项目中，提取通用的后端管理框架，形成可复用的 **CueAdmin**。

新项目只需添加自己的业务 Model/Service/API，开箱即用：权限系统、用户管理、JWT 认证、Redis 缓存、日志、异常处理。

---

## 二、框架包含什么

| 模块 | 内容 | 说明 |
|------|------|------|
| **认证系统** | JWT 签发/验证、密码登录、微信登录、登出黑名单、Token 刷新 | 支持多端（admin + miniapp） |
| **权限系统** | RBAC 细粒度权限码、Depends 链注入、Redis 缓存、角色管理 | `require_permission("xxx:yyy")` |
| **用户管理** | 用户 CRUD、角色分配、软删除、分页 | 管理员可管理所有用户 |
| **角色/权限/菜单管理** | 完整 CRUD | 后台可配置 |
| **基础设施** | 配置管理、数据库连接、日志、异常类、跨域 | 零配置启动 |

---

## 三、架构分层

```
cueadmin/
├── app/
│   ├── api/           # 路由层 — 挂 HTTP 端点 + 绑权限
│   │   ├── auth.py        # 登录、登出、/me、改资料
│   │   ├── users.py       # 用户 CRUD
│   │   ├── roles.py       # 角色 + 权限分配
│   │   ├── menus.py       # 菜单 CRUD
│   │   ├── permissions.py # 权限码 CRUD
│   │   └── router.py      # 聚合所有路由
│   │
│   ├── services/      # 业务层 — 纯逻辑，不依赖 HTTP
│   │   └── auth_service.py
│   │
│   ├── models/        # 数据层 — ORM 模型
│   │   ├── base.py         # TimestampMixin
│   │   ├── associations.py # M2M 中间表
│   │   ├── user.py
│   │   ├── role.py
│   │   ├── permission.py
│   │   └── menu.py
│   │
│   ├── schemas/       # Pydantic 模型 — 请求/响应格式
│   │   ├── auth.py
│   │   └── user.py
│   │
│   ├── core/          # 基础设施
│   │   ├── config.py       # 配置（读 .env）
│   │   ├── database.py     # 数据库连接
│   │   ├── dependencies.py # Depends 注入（认证 + 鉴权）
│   │   └── security.py     # JWT + 密码哈希
│   │
│   ├── utils/         # 工具
│   │   ├── exceptions.py   # 统一异常类
│   │   └── logger.py       # Loguru 配置
│   │
│   └── main.py        # FastAPI 入口
│
├── seed.py            # 种子数据（管理员 + 角色 + 权限）
├── requirements.txt   # 框架依赖：fastapi sqlalchemy redis loguru 等
├── .env.example       # 配置模板：数据库、JWT、Redis（不含业务配置）
├── alembic.ini        # 数据库迁移配置
└── alembic/           # 迁移脚本目录
```

---

## 四、不包含什么（业务项目自己写）

| 不在框架里 | 举例 |
|-----------|------|
| 业务 Model | Patient, GripRecord, GripDataPoint |
| 业务 Schema | PatientCreate, RecordFullUpload |
| 业务 Service | PatientService, GripService |
| 业务 API | patients.py, records.py |
| 业务配置 | 微信 appid/secret（属于项目配置，不属于框架） |

---

## 五、使用方式

新项目只需 3 步：

```bash
# 1. 复制框架
cp -r cueadmin/backend myproject/

# 2. 在 models/ schemas/ services/ api/ 下加自己的业务代码

# 3. 在 api/router.py 注册新路由
api_router.include_router(patients.router, prefix="/patients", tags=["患者"])
```

**不改框架文件，只加新的。** 升级框架时只替换核心文件即可。

---

## 六、剥离计划

按依赖顺序，分 5 步：

| 步骤 | 模块 | 文件 | 依赖 |
|------|------|------|------|
| 1. 基础设施 | 配置、数据库、日志、异常 | `core/config.py` `core/database.py` `utils/exceptions.py` `utils/logger.py` | 无 |
| 2. 数据层 | ORM 模型 | `models/base.py` `associations.py` `user.py` `role.py` `permission.py` `menu.py` | 步骤 1 |
| 3. 认证 | JWT、依赖注入、登录 | `core/security.py` `core/dependencies.py` `schemas/auth.py` `schemas/user.py` `services/auth_service.py` `api/auth.py` | 步骤 2 |
| 4. 权限管理 | 用户/角色/菜单/权限 CRUD | `api/roles.py` `api/permissions.py` `api/menus.py` `api/users.py` | 步骤 2、3 |
| 5. 入口 & 种子 | 路由聚合、启动、种子数据 | `api/router.py` `main.py` `seed.py` `requirements.txt` `.env.example` `alembic.ini` `alembic/` | 全部 |

---

## 七、待确认问题

1. **微信登录** → ❌ 不包含，项目自己加。提取时删掉 `wechat-login` 接口 + `wx_appid`/`wx_secret` 配置
2. **`linked_patient_id`** → ❌ 不包含，项目自己加。User 模型保持纯粹
3. **Redis** → ✅ 强制依赖（权限缓存 + Token 黑名单）
4. **懒加载** → `relationship` 不设 `lazy`，查询时显式选 `selectinload`/`joinedload`
5. **`response_model`** → 建议用，不强制
6. **Alembic** → ✅ 包含，但用通用配置，不硬编码数据库 URL

### 提取时需清理的内容

| 文件 | 删掉 |
|------|------|
| `core/config.py` | `wx_appid` `wx_secret` |
| `api/auth.py` | `POST /wechat-login` 整个接口 |
| `api/auth.py` | `import requests` `from app.core.config import settings` |
| `seed.py` | 微信相关注释或示例 |