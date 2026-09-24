"""API 路由层 — 对外接口的入口，按 API 版本分子目录。

  router.py   路由汇总 — 把各版本的模块路由收成一个总路由，main.py 只 import 它
  v1/         端点模块 — 按业务域拆分的路由文件（auth / users / roles / menus ...）

汇总放在版本目录之外：它管的是"有哪几个版本"，不属于任何单一版本。

版本化规则：
  目录名 = API 版本（v1 / v2 / ...），只管"代码怎么组织"；
  URL 前缀（/api/v1 /api/v2 ...）在 main.py 挂载时统一设置，
  目录名和 URL 前缀两边保持一致。

  新增一个 API 版本时：
    1. 复制 v1/ 整个目录为 v2/（只有端点模块，汇总不跟着走）
    2. 在 router.py 里加一个 v2_router，include v2 的各模块
    3. 在 main.py 里再 app.include_router(v2_router, prefix="/api/v2")
"""
