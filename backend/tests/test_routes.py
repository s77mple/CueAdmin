"""动态路由测试 — 当前用户的路由 + 权限 + 角色。

覆盖 routes 端点 + menu_service 的路由树构建逻辑：
  - 需要认证（无 token 拒绝）
  - admin 拿到全部菜单
  - 普通用户只拿到角色绑定的菜单
  - 历史数据（库里只存了子菜单）兜底补全父级

运行：cd backend && pytest tests/test_routes.py
"""

from app.core.security import hash_password
from app.models import Menu, Role, User


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
    parent = await client.post(
        "/api/v1/system/menus",
        headers=admin_headers,
        json={"code": "system", "name": "系统管理", "path": "/system"},
    )
    await client.post(
        "/api/v1/system/menus",
        headers=admin_headers,
        json={
            "code": "users",
            "name": "用户管理",
            "path": "/users",
            "component": "system/users/index",
            "parent_id": parent.json()["data"]["id"],
        },
    )

    resp = await client.get("/api/v1/routes", headers=admin_headers)
    routes = resp.json()["data"]["routes"]
    top = next(r for r in routes if r["name"] == "system")
    assert top["children"][0]["name"] == "users"


async def test_routes_skips_directory_without_children(client, admin_headers):
    """空目录（无 component 也无子菜单）不进路由 —— 否则前端取不到落地页。"""
    await client.post(
        "/api/v1/system/menus",
        headers=admin_headers,
        json={"code": "empty_dir", "name": "空目录", "path": "/empty"},
    )

    resp = await client.get("/api/v1/routes", headers=admin_headers)
    assert "empty_dir" not in {r["name"] for r in resp.json()["data"]["routes"]}


async def test_routes_normal_user_gets_role_menus(client, admin_headers):
    """普通用户只拿到角色绑定的菜单，父级自动补全。"""
    # 1. 建父菜单（目录）+ 子菜单（页面）
    parent = await client.post(
        "/api/v1/system/menus",
        headers=admin_headers,
        json={"code": "system", "name": "系统管理", "path": "/system"},
    )
    parent_id = parent.json()["data"]["id"]
    child = await client.post(
        "/api/v1/system/menus",
        headers=admin_headers,
        json={
            "code": "system-users",
            "name": "用户管理",
            "path": "/users",
            "component": "system/users/index",
            "parent_id": parent_id,
        },
    )
    child_id = child.json()["data"]["id"]

    # 2. 建角色绑定父菜单 + 子菜单（后端要求父级完整，只给子会被拒绝）
    role = await client.post(
        "/api/v1/system/roles",
        headers=admin_headers,
        json={"code": "viewer", "name": "访客", "menu_ids": [parent_id, child_id]},
    )
    role_id = role.json()["data"]["id"]

    # 3. 建用户绑定该角色
    user = await client.post(
        "/api/v1/system/users",
        headers=admin_headers,
        json={"username": "alice", "password": "alice123", "display_name": "爱丽丝", "role_ids": [role_id]},
    )
    assert user.json()["code"] == 0

    # 4. 用 alice 登录
    login = await client.post("/api/v1/auth/login", json={"username": "alice", "password": "alice123"})
    assert login.json()["code"] == 0
    token = login.json()["data"]["access_token"]

    # 5. 访问 /routes → 只有角色绑定的菜单
    resp = await client.get("/api/v1/routes", headers={"Authorization": f"Bearer {token}"})
    body = resp.json()
    assert body["code"] == 0
    routes = body["data"]["routes"]

    # 顶级节点是父菜单（目录）
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


async def test_routes_legacy_child_only_role_autocompletes_parent(client, admin_headers, db_session_factory):
    """历史数据兜底：库里只存了子菜单的老角色，/routes 仍自动补全父级。

    新写入已被 role_service 的父子校验拦住，这里绕过接口直接写关联，
    模拟校验上线前存下的数据。
    """
    parent = await client.post(
        "/api/v1/system/menus",
        headers=admin_headers,
        json={"code": "legacy", "name": "历史目录", "path": "/legacy"},
    )
    parent_id = parent.json()["data"]["id"]
    child = await client.post(
        "/api/v1/system/menus",
        headers=admin_headers,
        json={
            "code": "legacy-users",
            "name": "历史用户",
            "path": "/legacy/users",
            "component": "system/users/index",
            "parent_id": parent_id,
        },
    )
    child_id = child.json()["data"]["id"]

    async with db_session_factory() as session:
        menu = await session.get(Menu, child_id)
        role = Role(code="legacy_viewer", name="历史角色")
        role.menus = [menu]
        user = User(
            username="bob",
            password_hash=await hash_password("bob123"),
            display_name="鲍勃",
        )
        user.roles = [role]
        session.add(user)
        await session.commit()

    login = await client.post("/api/v1/auth/login", json={"username": "bob", "password": "bob123"})
    assert login.json()["code"] == 0
    token = login.json()["data"]["access_token"]

    routes = (await client.get("/api/v1/routes", headers={"Authorization": f"Bearer {token}"})).json()["data"]["routes"]

    assert len(routes) == 1
    assert routes[0]["name"] == "legacy"
    assert routes[0]["children"][0]["name"] == "legacy-users"
