"""CueAdmin 后端应用包 — 全项目按「分层」组织，不按业务域分包。

  api/           路由层   — 对外 HTTP 接口，按 API 版本分子目录（v1/v2/...）
  services/      业务层   — 权限校验、数据组装、事务编排等业务逻辑
  repositories/  仓储层   — 只做查询和 session.add/delete，不管事务
  models/        数据层   — SQLAlchemy ORM 模型，对应数据库表
  schemas/       视图层   — Pydantic 模型，定义接口的入参 / 出参结构
  core/          框架公共件 — 配置、数据库、认证、异常、统一响应、缓存 key
  utils/         纯工具   — 不依赖任何业务（如树构建）

依赖方向单向：api → services → repositories → models。
新业务（如采购）不需要建目录，在每一层各加一个文件即可：

  api/v1/purchase.py  services/purchase_service.py  repositories/purchase.py
  models/purchase.py  schemas/purchase.py

再在 api/router.py 里 include 一次。

一处有意为之的例外：core/dependencies.py 为了鉴权直接 import 了 models。
单应用下不做模块隔离，这条依赖是刻意保留的，不是待修的坏味道。
"""
