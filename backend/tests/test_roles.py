"""角色管理测试 — 角色的增删改查 + 唯一性 / 系统角色保护。

覆盖 role_service 的核心业务逻辑：
  - 列表（含权限/菜单关联）
  - 创建（code 唯一、权限/菜单外键校验）
  - 更新（系统角色不可改）
  - 删除（系统角色不可删）

运行：cd backend && pytest tests/test_roles.py
"""

from app.core.exceptions import ErrorCode


async def _admin_role_id(client, headers):
    resp = await client.get("/api/v1/system/roles", headers=headers)
    assert resp.json()["code"] == 0
    for r in resp.json()["data"]["items"]:
        if r["code"] == "admin":
            return r["id"]
    raise AssertionError("未找到 admin 角色")


# ============ 列表 ============


async def test_list_roles(client, admin_headers):
    resp = await client.get("/api/v1/system/roles", headers=admin_headers)
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1  # 种子只有 admin 角色
    item = body["data"]["items"][0]
    assert item["code"] == "admin"
    assert item["is_system"] is True


# ============ 创建 ============


async def test_create_role(client, admin_headers):
    resp = await client.post(
        "/api/v1/system/roles",
        headers=admin_headers,
        json={
            "code": "editor",
            "name": "编辑",
            "description": "只能编辑内容",
            "permission_codes": [],
            "menu_ids": [],
        },
    )
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["code"] == "editor"
    assert body["data"]["name"] == "编辑"


async def test_create_role_duplicate_code(client, admin_headers):
    resp = await client.post(
        "/api/v1/system/roles",
        headers=admin_headers,
        json={"code": "admin", "name": "重复"},
    )
    assert resp.json()["code"] == ErrorCode.ROLE_CODE_EXISTS.value


async def test_create_role_invalid_permission(client, admin_headers):
    resp = await client.post(
        "/api/v1/system/roles",
        headers=admin_headers,
        json={"code": "editor2", "name": "编辑2", "permission_codes": ["no:such"]},
    )
    assert resp.json()["code"] == ErrorCode.VALIDATION_ERROR.value


async def test_create_role_invalid_menu(client, admin_headers):
    resp = await client.post(
        "/api/v1/system/roles",
        headers=admin_headers,
        json={"code": "editor3", "name": "编辑3", "menu_ids": [9999]},
    )
    assert resp.json()["code"] == ErrorCode.VALIDATION_ERROR.value


async def _create_parent_child_menus(client, headers):
    """建一对父子菜单，返回 (parent_id, child_id)。"""
    parent = await client.post(
        "/api/v1/system/menus",
        headers=headers,
        json={"code": "report", "name": "报表", "path": "/report"},
    )
    parent_id = parent.json()["data"]["id"]
    child = await client.post(
        "/api/v1/system/menus",
        headers=headers,
        json={
            "code": "report-list",
            "name": "报表列表",
            "path": "/report/list",
            "component": "system/users/index",
            "parent_id": parent_id,
        },
    )
    return parent_id, child.json()["data"]["id"]


async def test_create_role_child_without_parent(client, admin_headers):
    """只选子菜单不给父级 → 拒绝（侧边栏挂不上，登录后取不到落地页）。"""
    _, child_id = await _create_parent_child_menus(client, admin_headers)

    resp = await client.post(
        "/api/v1/system/roles",
        headers=admin_headers,
        json={"code": "report_viewer", "name": "报表访客", "menu_ids": [child_id]},
    )
    assert resp.json()["code"] == ErrorCode.VALIDATION_ERROR.value


async def test_create_role_directory_without_children(client, admin_headers):
    """只选目录不给任何子菜单 → 拒绝（会生成没有 component 的空路由）。"""
    parent_id, _ = await _create_parent_child_menus(client, admin_headers)

    resp = await client.post(
        "/api/v1/system/roles",
        headers=admin_headers,
        json={"code": "report_dir", "name": "报表目录", "menu_ids": [parent_id]},
    )
    assert resp.json()["code"] == ErrorCode.VALIDATION_ERROR.value


async def test_create_role_with_complete_menu_tree(client, admin_headers):
    """父子一起选 → 允许。"""
    parent_id, child_id = await _create_parent_child_menus(client, admin_headers)

    resp = await client.post(
        "/api/v1/system/roles",
        headers=admin_headers,
        json={"code": "report_editor", "name": "报表编辑", "menu_ids": [parent_id, child_id]},
    )
    assert resp.json()["code"] == 0

    detail = await client.get(f"/api/v1/system/roles/{resp.json()['data']['id']}", headers=admin_headers)
    assert {m["id"] for m in detail.json()["data"]["menus"]} == {parent_id, child_id}


# ============ 更新 ============


async def test_update_role(client, admin_headers):
    created = await client.post(
        "/api/v1/system/roles",
        headers=admin_headers,
        json={"code": "viewer", "name": "访客"},
    )
    role_id = created.json()["data"]["id"]

    resp = await client.put(
        f"/api/v1/system/roles/{role_id}",
        headers=admin_headers,
        json={
            "name": "访客改名",
            "description": "x",
            "permission_codes": [],
            "menu_ids": [],
        },
    )
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["name"] == "访客改名"


async def test_update_system_role_forbidden(client, admin_headers):
    """系统角色（admin）不可修改。"""
    admin_id = await _admin_role_id(client, admin_headers)

    resp = await client.put(
        f"/api/v1/system/roles/{admin_id}",
        headers=admin_headers,
        json={
            "name": "超级管理员",
            "description": None,
            "permission_codes": [],
            "menu_ids": [],
        },
    )
    assert resp.json()["code"] == ErrorCode.ROLE_IS_SYSTEM.value


# ============ 删除 ============


async def test_delete_role(client, admin_headers):
    created = await client.post(
        "/api/v1/system/roles",
        headers=admin_headers,
        json={"code": "tmp_role", "name": "临时"},
    )
    role_id = created.json()["data"]["id"]

    resp = await client.delete(f"/api/v1/system/roles/{role_id}", headers=admin_headers)
    assert resp.json()["code"] == 0


async def test_delete_system_role_forbidden(client, admin_headers):
    admin_id = await _admin_role_id(client, admin_headers)

    resp = await client.delete(f"/api/v1/system/roles/{admin_id}", headers=admin_headers)
    assert resp.json()["code"] == ErrorCode.ROLE_IS_SYSTEM.value


async def test_delete_nonexistent_role(client, admin_headers):
    resp = await client.delete("/api/v1/system/roles/99999", headers=admin_headers)
    assert resp.json()["code"] == ErrorCode.ROLE_NOT_FOUND.value


# ============ 单查 ============


async def test_get_role(client, admin_headers):
    created = await client.post(
        "/api/v1/system/roles",
        headers=admin_headers,
        json={"code": "viewer", "name": "访客"},
    )
    role_id = created.json()["data"]["id"]

    resp = await client.get(f"/api/v1/system/roles/{role_id}", headers=admin_headers)
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["code"] == "viewer"
    assert body["data"]["name"] == "访客"
    assert body["data"]["permissions"] == []
    assert body["data"]["menus"] == []


async def test_get_role_nonexistent(client, admin_headers):
    resp = await client.get("/api/v1/system/roles/99999", headers=admin_headers)
    assert resp.json()["code"] == ErrorCode.ROLE_NOT_FOUND.value
