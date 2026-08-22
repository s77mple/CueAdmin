"""API 路由层 — 对外接口的入口，按 API 版本分子目录。

版本化规则：
  目录名 = API 版本（v1 / v2 / ...），只管"代码怎么组织"；
  URL 前缀（/api/v1 /api/v2 ...）在 main.py 挂载时统一设置，
  目录名和 URL 前缀两边保持一致。

  新增一个 API 版本时：
    1. 复制 v1/ 的结构建一个 v2/（router.py 汇总 + 各业务模块路由）
    2. 在 main.py 里再 app.include_router(v2_router, prefix="/api/v2")

  每个版本目录内部的固定布局：
    router.py      该版本的路由汇总（import 各模块并逐个 include_router）
    *_模块.py       按业务域拆分的路由文件（auth / users / roles / menus ...）
"""
