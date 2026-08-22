"""系统管理模块 — 后端唯一的业务域（对应若依的 module_admin）。

按「模块 → 分层」组织，本模块内的文件按职责分四层：

  api/      路由层 — 对外 HTTP 接口，按 API 版本分子目录（v1/v2/...）
  services/ 业务层 — 权限校验、数据组装、事务编排等业务逻辑
  models/   数据层 — SQLAlchemy ORM 模型，对应数据库表
  schemas/  视图层 — Pydantic 模型，定义接口的入参 / 出参结构

框架公共件（配置、数据库、认证、异常处理、统一响应等）都在 app/core/，
不放在本模块里；本模块只依赖 core，不反向被 core 依赖。

将来新增业务域（如 monitor 监控、task 定时任务）时，
在 app/ 下并列建一个 monitor/、task/ 包，内部结构与本包保持一致。
"""
