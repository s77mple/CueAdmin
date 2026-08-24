"""用户管理测试 — 用户的增删改查 + 唯一性 / 外键 / 删除保护。

覆盖 user_service 的核心业务逻辑：
  - 列表查询（含启用状态筛选）
  - 创建（用户名唯一、角色/部门外键校验、首尾空格）
  - 全量更新（PUT）/ 部分更新（PATCH）
  - 软禁用（默认删除）/ 硬删除（?hard=true）
  - 保护：不能操作自己、不能硬删启用中的用户

运行：cd backend && pytest tests/test_users.py
"""

from app.core.exceptions import ErrorCode


async def _admin_role_id(client, headers):
    """从角色列表里拿到 admin 角色的 ID（不写死 ID，避免脆弱）。"""
    resp = await client.get("/api/v1/system/roles", headers=headers)
    assert resp.json()["code"] == 0
    for r in resp.json()["data"]["items"]:
        if r["code"] == "admin":
            return r["id"]
    raise AssertionError("未找到 admin 角色")


# ============ 列表 ============

async def test_list_users(client, admin_headers):
    resp = await client.get("/api/v1/system/users", headers=admin_headers)
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["total"] == 1  # 种子只有 admin 一个用户
    assert data["items"][0]["username"] == "admin"
    # 分页字段齐全
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["has_more"] is False


async def test_list_users_filter_active(client, admin_headers):
    # 默认 admin 是启用状态，所以禁用筛选查不到、启用筛选查得到
    resp = await client.get(
        "/api/v1/system/users", params={"is_active": "false"}, headers=admin_headers
    )
    assert resp.json()["data"]["total"] == 0

    resp = await client.get(
        "/api/v1/system/users", params={"is_active": "true"}, headers=admin_headers
    )
    assert resp.json()["data"]["total"] == 1


# ============ 创建 ============

async def test_create_user(client, admin_headers):
    role_id = await _admin_role_id(client, admin_headers)
    resp = await client.post(
        "/api/v1/system/users",
        headers=admin_headers,
        json={
            "username": "alice",
            "password": "alice123",
            "display_name": "爱丽丝",
            "phone": "13800138000",
            "role_ids": [role_id],
            "department_id": None,
        },
    )
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["username"] == "alice"
    assert data["display_name"] == "爱丽丝"
    assert data["is_active"] is True
    assert [r["code"] for r in data["roles"]] == ["admin"]


async def test_create_user_duplicate_username(client, admin_headers):
    resp = await client.post(
        "/api/v1/system/users",
        headers=admin_headers,
        json={"username": "admin", "password": "whatever123", "display_name": "x"},
    )
    assert resp.json()["code"] == ErrorCode.USERNAME_ALREADY_EXISTS.value


async def test_create_user_invalid_role(client, admin_headers):
    resp = await client.post(
        "/api/v1/system/users",
        headers=admin_headers,
        json={
            "username": "bob",
            "password": "bob12345",
            "display_name": "鲍勃",
            "role_ids": [9999],
        },
    )
    assert resp.json()["code"] == ErrorCode.VALIDATION_ERROR.value


async def test_create_user_invalid_department(client, admin_headers):
    resp = await client.post(
        "/api/v1/system/users",
        headers=admin_headers,
        json={
            "username": "carol",
            "password": "carol123",
            "display_name": "卡罗尔",
            "department_id": 9999,
        },
    )
    assert resp.json()["code"] == ErrorCode.VALIDATION_ERROR.value


async def test_create_user_username_whitespace(client, admin_headers):
    """用户名首尾空格 → 校验失败。"""
    resp = await client.post(
        "/api/v1/system/users",
        headers=admin_headers,
        json={"username": "  dave  ", "password": "dave1234", "display_name": "戴夫"},
    )
    assert resp.json()["code"] == ErrorCode.VALIDATION_ERROR.value


# ============ 更新 ============

async def test_update_user(client, admin_headers):
    created = await client.post(
        "/api/v1/system/users",
        headers=admin_headers,
        json={"username": "eve", "password": "eve12345", "display_name": "伊芙"},
    )
    user_id = created.json()["data"]["id"]

    resp = await client.put(
        f"/api/v1/system/users/{user_id}",
        headers=admin_headers,
        json={
            "username": "eve",
            "display_name": "伊芙改名",
            "phone": None,
            "is_active": True,
            "role_ids": [],
            "department_id": None,
        },
    )
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["display_name"] == "伊芙改名"


async def test_update_user_duplicate_username(client, admin_headers):
    await client.post(
        "/api/v1/system/users", headers=admin_headers,
        json={"username": "frank", "password": "frank123", "display_name": "弗兰克"},
    )
    created = await client.post(
        "/api/v1/system/users", headers=admin_headers,
        json={"username": "grace", "password": "grace123", "display_name": "格蕾丝"},
    )
    grace_id = created.json()["data"]["id"]

    # 把 grace 改成 frank（已存在）→ 唯一性冲突
    resp = await client.put(
        f"/api/v1/system/users/{grace_id}",
        headers=admin_headers,
        json={
            "username": "frank",
            "display_name": "格蕾丝",
            "phone": None,
            "is_active": True,
            "role_ids": [],
            "department_id": None,
        },
    )
    assert resp.json()["code"] == ErrorCode.USERNAME_ALREADY_EXISTS.value


async def test_patch_user(client, admin_headers):
    created = await client.post(
        "/api/v1/system/users", headers=admin_headers,
        json={"username": "henry", "password": "henry123", "display_name": "亨利"},
    )
    user_id = created.json()["data"]["id"]

    # 只改 display_name，其他字段不动
    resp = await client.patch(
        f"/api/v1/system/users/{user_id}",
        headers=admin_headers,
        json={"display_name": "亨利二世"},
    )
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["display_name"] == "亨利二世"
    assert body["data"]["username"] == "henry"  # 未传的字段保持原样


# ============ 删除 ============

async def test_delete_user_soft(client, admin_headers):
    created = await client.post(
        "/api/v1/system/users", headers=admin_headers,
        json={"username": "ivy", "password": "ivy12345", "display_name": "艾维"},
    )
    user_id = created.json()["data"]["id"]

    resp = await client.delete(f"/api/v1/system/users/{user_id}", headers=admin_headers)
    assert resp.json()["code"] == 0

    # 软禁用：用户还在列表里，只是 is_active 变 false
    resp = await client.get("/api/v1/system/users", headers=admin_headers)
    items = resp.json()["data"]["items"]
    target = next(u for u in items if u["id"] == user_id)
    assert target["is_active"] is False


async def test_delete_user_hard(client, admin_headers):
    created = await client.post(
        "/api/v1/system/users", headers=admin_headers,
        json={"username": "jack", "password": "jack1234", "display_name": "杰克"},
    )
    user_id = created.json()["data"]["id"]

    # 先软禁用，再硬删除
    await client.delete(f"/api/v1/system/users/{user_id}", headers=admin_headers)
    resp = await client.delete(
        f"/api/v1/system/users/{user_id}", params={"hard": "true"}, headers=admin_headers
    )
    assert resp.json()["code"] == 0

    # 彻底删除后列表里没有了
    resp = await client.get("/api/v1/system/users", headers=admin_headers)
    ids = [u["id"] for u in resp.json()["data"]["items"]]
    assert user_id not in ids


async def test_delete_user_hard_active_conflict(client, admin_headers):
    """硬删除启用中的用户 → 冲突（必须先禁用）。"""
    created = await client.post(
        "/api/v1/system/users", headers=admin_headers,
        json={"username": "kate", "password": "kate1234", "display_name": "凯特"},
    )
    user_id = created.json()["data"]["id"]

    resp = await client.delete(
        f"/api/v1/system/users/{user_id}", params={"hard": "true"}, headers=admin_headers
    )
    assert resp.json()["code"] == ErrorCode.CONFLICT.value


async def test_delete_self_conflict(client, admin_headers):
    """不能操作自己的账号。"""
    resp = await client.get("/api/v1/system/users", headers=admin_headers)
    admin_id = next(
        u["id"] for u in resp.json()["data"]["items"] if u["username"] == "admin"
    )

    resp = await client.delete(f"/api/v1/system/users/{admin_id}", headers=admin_headers)
    assert resp.json()["code"] == ErrorCode.CONFLICT.value


async def test_delete_nonexistent_user(client, admin_headers):
    resp = await client.delete("/api/v1/system/users/99999", headers=admin_headers)
    assert resp.json()["code"] == ErrorCode.USER_NOT_FOUND.value
