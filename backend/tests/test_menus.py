"""菜单管理测试 — 菜单的树形 CRUD + 唯一性 / 循环检测。

覆盖 menu_service 的核心业务逻辑：
  - 列表（扁平列表）
  - 创建（code 唯一、父菜单校验）
  - 更新（循环检测：不能把自己或子孙设为父菜单）
  - 删除（子菜单变顶级）

运行：cd backend && pytest tests/test_menus.py
"""

from app.core.exceptions import ErrorCode


# ============ 列表 ============

async def test_list_menus_empty(client, admin_headers):
    resp = await client.get("/api/v1/system/menus", headers=admin_headers)
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 0


# ============ 创建 ============

async def test_create_menu(client, admin_headers):
    resp = await client.post(
        "/api/v1/system/menus",
        headers=admin_headers,
        json={
            "code": "system",
            "name": "系统管理",
            "icon": "fa-solid:gear",
            "path": "/system",
            "component": None,  # 目录菜单（component=null）
            "parent_id": None,
            "sort_order": 1,
        },
    )
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["code"] == "system"
    assert body["data"]["name"] == "系统管理"
    assert body["data"]["parent_id"] is None


async def test_create_menu_duplicate_code(client, admin_headers):
    await client.post(
        "/api/v1/system/menus", headers=admin_headers,
        json={"code": "system", "name": "系统"},
    )
    resp = await client.post(
        "/api/v1/system/menus", headers=admin_headers,
        json={"code": "system", "name": "系统2"},
    )
    assert resp.json()["code"] == ErrorCode.MENU_CODE_EXISTS.value


async def test_create_menu_invalid_parent(client, admin_headers):
    resp = await client.post(
        "/api/v1/system/menus", headers=admin_headers,
        json={"code": "child", "name": "子菜单", "parent_id": 9999},
    )
    assert resp.json()["code"] == ErrorCode.MENU_NOT_FOUND.value


# ============ 更新 ============

async def test_update_menu(client, admin_headers):
    created = await client.post(
        "/api/v1/system/menus", headers=admin_headers,
        json={"code": "system", "name": "系统"},
    )
    menu_id = created.json()["data"]["id"]

    resp = await client.put(
        f"/api/v1/system/menus/{menu_id}",
        headers=admin_headers,
        json={
            "name": "系统管理",
            "icon": None,
            "path": "/system",
            "component": None,
            "parent_id": None,
            "sort_order": 1,
        },
    )
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["name"] == "系统管理"


async def test_update_menu_cycle_conflict(client, admin_headers):
    """把父菜单设为子菜单的子 → 循环引用冲突。"""
    parent = await client.post(
        "/api/v1/system/menus", headers=admin_headers,
        json={"code": "parent", "name": "父菜单"},
    )
    parent_id = parent.json()["data"]["id"]
    child = await client.post(
        "/api/v1/system/menus", headers=admin_headers,
        json={"code": "child", "name": "子菜单", "parent_id": parent_id},
    )
    child_id = child.json()["data"]["id"]

    resp = await client.put(
        f"/api/v1/system/menus/{parent_id}",
        headers=admin_headers,
        json={
            "name": "父菜单", "icon": None, "path": None,
            "component": None, "parent_id": child_id, "sort_order": 0,
        },
    )
    assert resp.json()["code"] == ErrorCode.CONFLICT.value


# ============ 删除 ============

async def test_delete_menu(client, admin_headers):
    created = await client.post(
        "/api/v1/system/menus", headers=admin_headers,
        json={"code": "tmp", "name": "临时菜单"},
    )
    menu_id = created.json()["data"]["id"]

    resp = await client.delete(f"/api/v1/system/menus/{menu_id}", headers=admin_headers)
    assert resp.json()["code"] == 0


async def test_delete_menu_with_child(client, admin_headers):
    """删除父菜单 → 子菜单变顶级。"""
    parent = await client.post(
        "/api/v1/system/menus", headers=admin_headers,
        json={"code": "parent", "name": "父菜单"},
    )
    parent_id = parent.json()["data"]["id"]
    await client.post(
        "/api/v1/system/menus", headers=admin_headers,
        json={"code": "child", "name": "子菜单", "parent_id": parent_id},
    )

    resp = await client.delete(f"/api/v1/system/menus/{parent_id}", headers=admin_headers)
    assert resp.json()["code"] == 0

    resp = await client.get("/api/v1/system/menus", headers=admin_headers)
    child = next(m for m in resp.json()["data"]["items"] if m["code"] == "child")
    assert child["parent_id"] is None


async def test_delete_nonexistent_menu(client, admin_headers):
    resp = await client.delete("/api/v1/system/menus/99999", headers=admin_headers)
    assert resp.json()["code"] == ErrorCode.MENU_NOT_FOUND.value


# ============ 单查 ============

async def test_get_menu(client, admin_headers):
    created = await client.post(
        "/api/v1/system/menus", headers=admin_headers,
        json={"code": "system", "name": "系统管理"},
    )
    menu_id = created.json()["data"]["id"]

    resp = await client.get(f"/api/v1/system/menus/{menu_id}", headers=admin_headers)
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["code"] == "system"
    assert body["data"]["name"] == "系统管理"


async def test_get_menu_nonexistent(client, admin_headers):
    resp = await client.get("/api/v1/system/menus/99999", headers=admin_headers)
    assert resp.json()["code"] == ErrorCode.MENU_NOT_FOUND.value
