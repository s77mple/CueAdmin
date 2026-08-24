"""动态路由测试 — 当前用户的路由 + 权限 + 角色。

覆盖 routes 端点 + menu_service 的路由树构建逻辑：
  - 需要认证（无 token 拒绝）
  - admin 拿到全部菜单
  - 普通用户只拿到角色绑定的菜单（含父级自动补全）

运行：cd backend && pytest tests/test_routes.py
"""


async def test_routes_requires_auth(client):
    """无 token 访问 /routes → 认证失败。"""
    resp = await client.get("/api/v1/routes")
    # HTTPBearer 缺 token 会返回 401（FastAPI 默认行为）
    assert resp.status_code == 401


async def test_routes_admin_empty(client, admin_headers):
    """admin 登录但数据库无菜单 → routes 为空列表。"""
    resp = await client.get("/api/v1/routes", headers=admin_headers)
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["routes"] == []
    assert body["data"]["permissions"] == []
    # roles 里含 admin
    assert [r["code"] for r in body["data"]["roles"]] == ["admin"]


async def test_routes_admin_gets_all_menus(client, admin_headers):
    """admin 拥有全部菜单（不按角色过滤）。"""
    await client.post(
        "/api/v1/system/menus", headers=admin_headers,
        json={"code": "system", "name": "系统管理", "path": "/system"},
    )
    await client.post(
        "/api/v1/system/menus", headers=admin_headers,
        json={"code": "users", "name": "用户管理", "path": "/users",
              "component": "system/users/index"},
    )

    resp = await client.get("/api/v1/routes", headers=admin_headers)
    routes = resp.json()["data"]["routes"]
    codes = {r["name"] for r in routes}
    assert "system" in codes
    assert "users" in codes


async def test_routes_normal_user_gets_role_menus(client, admin_headers):
    """普通用户只拿到角色绑定的菜单，父级自动补全。"""
    # 1. 建父菜单（目录）+ 子菜单（页面）
    parent = await client.post(
        "/api/v1/system/menus", headers=admin_headers,
        json={"code": "system", "name": "系统管理", "path": "/system"},
    )
    parent_id = parent.json()["data"]["id"]
    child = await client.post(
        "/api/v1/system/menus", headers=admin_headers,
        json={
            "code": "system-users", "name": "用户管理", "path": "/users",
            "component": "system/users/index", "parent_id": parent_id,
        },
    )
    child_id = child.json()["data"]["id"]

    # 2. 建角色只绑定子菜单（不绑定父菜单）
    role = await client.post(
        "/api/v1/system/roles", headers=admin_headers,
        json={"code": "viewer", "name": "访客", "menu_ids": [child_id]},
    )
    role_id = role.json()["data"]["id"]

    # 3. 建用户绑定该角色
    user = await client.post(
        "/api/v1/system/users", headers=admin_headers,
        json={"username": "alice", "password": "alice123", "display_name": "爱丽丝",
              "role_ids": [role_id]},
    )
    assert user.json()["code"] == 0

    # 4. 用 alice 登录
    login = await client.post(
        "/api/v1/auth/login", json={"username": "alice", "password": "alice123"}
    )
    assert login.json()["code"] == 0
    token = login.json()["data"]["access_token"]

    # 5. 访问 /routes → 只有角色绑定的子菜单 + 自动补全的父菜单
    resp = await client.get("/api/v1/routes", headers={"Authorization": f"Bearer {token}"})
    body = resp.json()
    assert body["code"] == 0
    routes = body["data"]["routes"]

    # 顶级节点是补全出来的父菜单
    assert len(routes) == 1
    top = routes[0]
    assert top["name"] == "system"
    assert top["path"] == "/system"

    # 子节点是角色绑定的子菜单，且带 component
    assert len(top["children"]) == 1
    child_route = top["children"][0]
    assert child_route["name"] == "system-users"
    assert child_route["path"] == "/users"
    assert child_route["component"] == "system/users/index"
