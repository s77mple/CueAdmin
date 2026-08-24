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
