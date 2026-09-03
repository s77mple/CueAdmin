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


async def test_list_users_filter_department_subtree(client, admin_headers):
    """dept_id 匹配「该部门 + 全部子孙」（学 RuoYi find_in_set）— 左树点父部门能带出子部门用户。"""
    top = (
        await client.post(
            "/api/v1/system/departments", headers=admin_headers,
            json={"code": "fixta", "name": "总公司"},
        )
    ).json()["data"]["id"]
    child = (
        await client.post(
            "/api/v1/system/departments", headers=admin_headers,
            json={"code": "fixta1", "name": "研发部", "parent_id": top},
        )
    ).json()["data"]["id"]
    other = (
        await client.post(
            "/api/v1/system/departments", headers=admin_headers,
            json={"code": "fixtb", "name": "分公司"},
        )
    ).json()["data"]["id"]

    # alice 直属顶级，bob 挂在子孙部门，carol 在另一个顶级，dave 无部门
    for username, dept in [("alice", top), ("bob", child), ("carol", other), ("dave", None)]:
        resp = await client.post(
            "/api/v1/system/users", headers=admin_headers,
            json={"username": username, "password": "test1234",
                  "display_name": username, "department_id": dept},
        )
        assert resp.json()["code"] == 0

    # 点顶级 → 直属 alice + 子孙部门的 bob 都出；他部门/无部门的不出
    resp = await client.get(
        "/api/v1/system/users", params={"dept_id": top}, headers=admin_headers
    )
    body = resp.json()
    assert body["code"] == 0
    names = [u["username"] for u in body["data"]["items"]]
    assert "alice" in names and "bob" in names
    assert "carol" not in names and "dave" not in names and "admin" not in names

    # 点叶子部门 → 只回直属的 bob
    resp = await client.get(
        "/api/v1/system/users", params={"dept_id": child}, headers=admin_headers
    )
    names = [u["username"] for u in resp.json()["data"]["items"]]
    assert "bob" in names and "alice" not in names

    # 未知部门 id → 收不到任何行（空页，与若依行为一致）
    resp = await client.get(
        "/api/v1/system/users", params={"dept_id": 99999}, headers=admin_headers
    )
    assert resp.json()["data"]["total"] == 0


async def test_list_items_are_slim_rows(client, admin_headers):
    """列表行契约：学 RuoYi 列表不下发角色 —— 无 roles/role_ids，只带嵌套 department + 行内 department_id。

    role_ids/roles（全量下拉）只在详情接口的 UserDetail 顶层。
    """
    role_id = await _admin_role_id(client, admin_headers)
    dept_id = (
        await client.post(
            "/api/v1/system/departments", headers=admin_headers,
            json={"code": "slimdpt", "name": "瘦身部"},
        )
    ).json()["data"]["id"]
    created = await client.post(
        "/api/v1/system/users", headers=admin_headers,
        json={"username": "slim_user", "password": "slim1234",
              "display_name": "瘦身用户", "department_id": dept_id,
              "role_ids": [role_id]},
    )
    assert created.json()["code"] == 0
    # 创建接口（UserRead）是纯列镜像 —— role_ids 不再回显（只有详情接口顶层带）
    assert "role_ids" not in created.json()["data"]

    listed = await client.get("/api/v1/system/users", headers=admin_headers)
    target = next(
        u for u in listed.json()["data"]["items"] if u["username"] == "slim_user"
    )
    assert "role_ids" not in target
    # 学 RuoYi：列表行不下发角色对象，角色只在详情（UserDetail）里回显
    assert "roles" not in target
    # 行内带 department_id（RuoYi 的 deptId 就在行里）
    assert target["department_id"] == dept_id
    # 表格渲染的名字对象还在
    assert target["department"]["id"] == dept_id


# ============ 详情 ============

async def test_user_detail_echoes_assigned_role_ids(client, admin_headers):
    """详情 = getInfo 同款：user 纯列镜像（无 role_ids）+ 全量角色下拉 + 顶层 role_ids 回显已分配。"""
    role_id = await _admin_role_id(client, admin_headers)
    created = await client.post(
        "/api/v1/system/users", headers=admin_headers,
        json={"username": "detail_echo", "password": "detail123",
              "display_name": "回显用户", "role_ids": [role_id], "department_id": None},
    )
    assert created.json()["code"] == 0
    uid = created.json()["data"]["id"]

    resp = await client.get(f"/api/v1/system/users/{uid}", headers=admin_headers)
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    # user 是纯列镜像，不带 role_ids
    assert "role_ids" not in data["user"]
    # role_ids 放顶层（RuoYi getInfo.roleIds 同款），回显的是该用户已分配的角色
    assert data["role_ids"] == [role_id]
    # roles 是全量角色下拉（至少含 admin），user 回显详情字段
    assert "admin" in [r["code"] for r in data["roles"]]
    assert data["user"]["username"] == "detail_echo"


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
    # UserRead 纯列镜像：已分配角色回显在详情接口（UserDetail.role_ids），不在写返回
    assert "role_ids" not in data


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
            "post_ids": [],
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
            "post_ids": [],
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


# ============ 岗位关联（岗位与角色是正交的两条 M2M）============

async def _create_post(client, headers, code: str, name: str) -> dict:
    """岗位模块造数小助手。"""
    resp = await client.post(
        "/api/v1/system/posts", headers=headers,
        json={"code": code, "name": name},
    )
    assert resp.json()["code"] == 0
    return resp.json()["data"]


async def test_user_detail_echoes_assigned_posts(client, admin_headers):
    """详情 getInfo 同款第二维：user 纯列（无 post_ids）+ 全量岗位下拉 posts + 顶层 post_ids 回显。"""
    post = await _create_post(client, admin_headers, "pm", "项目经理")
    created = await client.post(
        "/api/v1/system/users", headers=admin_headers,
        json={"username": "post_echo", "password": "post1234",
              "display_name": "岗位回显用户", "post_ids": [post["id"]]},
    )
    assert created.json()["code"] == 0
    # UserRead 纯列镜像：岗位回显走详情，写返回不背 post_ids
    assert "post_ids" not in created.json()["data"]
    uid = created.json()["data"]["id"]

    resp = await client.get(f"/api/v1/system/users/{uid}", headers=admin_headers)
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert "post_ids" not in data["user"]
    assert data["post_ids"] == [post["id"]]
    # posts 是全量岗位下拉（含刚建的 pm）
    assert "pm" in [p["code"] for p in data["posts"]]
    assert data["user"]["username"] == "post_echo"


async def test_create_user_invalid_post(client, admin_headers):
    resp = await client.post(
        "/api/v1/system/users", headers=admin_headers,
        json={"username": "badpost", "password": "bad12345",
              "display_name": "坏岗位用户", "post_ids": [9999]},
    )
    assert resp.json()["code"] == ErrorCode.VALIDATION_ERROR.value


async def test_update_user_assign_posts(client, admin_headers):
    """PUT 带 post_ids → 全量覆盖岗位关联；PATCH 单独动岗位不动角色。"""
    post_a = await _create_post(client, admin_headers, "pa", "岗位甲")
    post_b = await _create_post(client, admin_headers, "pb", "岗位乙")

    created = await client.post(
        "/api/v1/system/users", headers=admin_headers,
        json={"username": "mgr", "password": "mgr12345", "display_name": "经理"},
    )
    uid = created.json()["data"]["id"]

    # PUT 全量：挂两个岗位
    resp = await client.put(
        f"/api/v1/system/users/{uid}",
        headers=admin_headers,
        json={
            "username": "mgr", "display_name": "经理", "phone": None,
            "is_active": True, "role_ids": [], "post_ids": [post_a["id"], post_b["id"]],
            "department_id": None,
        },
    )
    assert resp.json()["code"] == 0
    detail = (await client.get(f"/api/v1/system/users/{uid}", headers=admin_headers)).json()["data"]
    assert sorted(detail["post_ids"]) == sorted([post_a["id"], post_b["id"]])

    # PATCH 换成只留一个 → 岗位维度独立变更，不影响角色
    resp = await client.patch(
        f"/api/v1/system/users/{uid}", headers=admin_headers,
        json={"post_ids": [post_a["id"]]},
    )
    assert resp.json()["code"] == 0
    detail = (await client.get(f"/api/v1/system/users/{uid}", headers=admin_headers)).json()["data"]
    assert detail["post_ids"] == [post_a["id"]]
