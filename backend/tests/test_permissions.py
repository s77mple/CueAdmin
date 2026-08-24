"""权限码管理测试 — 权限的增删改查 + code 唯一性。

覆盖 permission_service 的核心业务逻辑：
  - 列表（扁平列表）
  - 创建（code 唯一）
  - 更新（code 变更时唯一性校验）
  - 删除

运行：cd backend && pytest tests/test_permissions.py
"""

from app.core.exceptions import ErrorCode


# ============ 列表 ============

async def test_list_permissions_empty(client, admin_headers):
    resp = await client.get("/api/v1/system/permissions", headers=admin_headers)
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 0


# ============ 创建 ============

async def test_create_permission(client, admin_headers):
    resp = await client.post(
        "/api/v1/system/permissions",
        headers=admin_headers,
        json={
            "code": "user:list",
            "name": "用户列表",
            "resource": "user",
            "action": "list",
            "description": "查看用户列表",
        },
    )
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["code"] == "user:list"


async def test_create_permission_duplicate_code(client, admin_headers):
    await client.post(
        "/api/v1/system/permissions", headers=admin_headers,
        json={"code": "user:list", "name": "用户列表", "resource": "user", "action": "list"},
    )
    resp = await client.post(
        "/api/v1/system/permissions", headers=admin_headers,
        json={"code": "user:list", "name": "重复", "resource": "user", "action": "list"},
    )
    assert resp.json()["code"] == ErrorCode.PERM_CODE_EXISTS.value


# ============ 更新 ============

async def test_update_permission(client, admin_headers):
    created = await client.post(
        "/api/v1/system/permissions", headers=admin_headers,
        json={"code": "user:list", "name": "用户列表", "resource": "user", "action": "list"},
    )
    perm_id = created.json()["data"]["id"]

    resp = await client.put(
        f"/api/v1/system/permissions/{perm_id}",
        headers=admin_headers,
        json={
            "code": "user:list",
            "name": "用户列表改名",
            "resource": "user",
            "action": "list",
            "description": None,
        },
    )
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["name"] == "用户列表改名"


async def test_update_permission_duplicate_code(client, admin_headers):
    await client.post(
        "/api/v1/system/permissions", headers=admin_headers,
        json={"code": "user:list", "name": "用户列表", "resource": "user", "action": "list"},
    )
    created = await client.post(
        "/api/v1/system/permissions", headers=admin_headers,
        json={"code": "user:create", "name": "创建用户", "resource": "user", "action": "create"},
    )
    perm_id = created.json()["data"]["id"]

    # 把 user:create 改成 user:list（已存在）→ 唯一性冲突
    resp = await client.put(
        f"/api/v1/system/permissions/{perm_id}",
        headers=admin_headers,
        json={
            "code": "user:list",
            "name": "创建用户",
            "resource": "user",
            "action": "create",
            "description": None,
        },
    )
    assert resp.json()["code"] == ErrorCode.PERM_CODE_EXISTS.value


# ============ 删除 ============

async def test_delete_permission(client, admin_headers):
    created = await client.post(
        "/api/v1/system/permissions", headers=admin_headers,
        json={"code": "tmp:act", "name": "临时", "resource": "tmp", "action": "act"},
    )
    perm_id = created.json()["data"]["id"]

    resp = await client.delete(
        f"/api/v1/system/permissions/{perm_id}", headers=admin_headers
    )
    assert resp.json()["code"] == 0


async def test_delete_nonexistent_permission(client, admin_headers):
    resp = await client.delete("/api/v1/system/permissions/99999", headers=admin_headers)
    assert resp.json()["code"] == ErrorCode.PERM_NOT_FOUND.value
