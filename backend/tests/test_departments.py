"""部门管理测试 — 部门的树形 CRUD + 唯一性 / 循环检测。

覆盖 department_service 的核心业务逻辑：
  - 列表（扁平列表）
  - 创建（code 唯一、父部门校验）
  - 更新（循环检测：不能把自己或子孙设为父部门）
  - 删除（子部门变顶级）

运行：cd backend && pytest tests/test_departments.py
"""

from app.core.exceptions import ErrorCode


# ============ 列表 ============

async def test_list_departments_empty(client, admin_headers):
    resp = await client.get("/api/v1/system/departments", headers=admin_headers)
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 0
    assert body["data"]["items"] == []


# ============ 创建 ============

async def test_create_department(client, admin_headers):
    resp = await client.post(
        "/api/v1/system/departments",
        headers=admin_headers,
        json={"code": "tech", "name": "技术部", "parent_id": None, "sort_order": 1},
    )
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["code"] == "tech"
    assert body["data"]["name"] == "技术部"
    assert body["data"]["parent_id"] is None


async def test_create_department_duplicate_code(client, admin_headers):
    await client.post(
        "/api/v1/system/departments", headers=admin_headers,
        json={"code": "tech", "name": "技术部"},
    )
    resp = await client.post(
        "/api/v1/system/departments", headers=admin_headers,
        json={"code": "tech", "name": "技术部2"},
    )
    assert resp.json()["code"] == ErrorCode.DEPT_CODE_EXISTS.value


async def test_create_department_invalid_parent(client, admin_headers):
    resp = await client.post(
        "/api/v1/system/departments", headers=admin_headers,
        json={"code": "child", "name": "子部门", "parent_id": 9999},
    )
    assert resp.json()["code"] == ErrorCode.DEPT_NOT_FOUND.value


# ============ 更新 ============

async def test_update_department(client, admin_headers):
    created = await client.post(
        "/api/v1/system/departments", headers=admin_headers,
        json={"code": "tech", "name": "技术部"},
    )
    dept_id = created.json()["data"]["id"]

    resp = await client.put(
        f"/api/v1/system/departments/{dept_id}",
        headers=admin_headers,
        json={"name": "技术研发部", "parent_id": None, "sort_order": 2, "description": "改"},
    )
    assert resp.json()["code"] == 0
    assert resp.json()["data"]["name"] == "技术研发部"


async def test_update_department_self_parent_conflict(client, admin_headers):
    """把自己设为父部门 → 冲突。"""
    created = await client.post(
        "/api/v1/system/departments", headers=admin_headers,
        json={"code": "tech", "name": "技术部"},
    )
    dept_id = created.json()["data"]["id"]

    resp = await client.put(
        f"/api/v1/system/departments/{dept_id}",
        headers=admin_headers,
        json={"name": "技术部", "parent_id": dept_id, "sort_order": 0, "description": None},
    )
    assert resp.json()["code"] == ErrorCode.CONFLICT.value


async def test_update_department_cycle_conflict(client, admin_headers):
    """把父部门设为子部门的子 → 循环引用冲突。"""
    parent = await client.post(
        "/api/v1/system/departments", headers=admin_headers,
        json={"code": "parent", "name": "父部门"},
    )
    parent_id = parent.json()["data"]["id"]
    child = await client.post(
        "/api/v1/system/departments", headers=admin_headers,
        json={"code": "child", "name": "子部门", "parent_id": parent_id},
    )
    child_id = child.json()["data"]["id"]

    resp = await client.put(
        f"/api/v1/system/departments/{parent_id}",
        headers=admin_headers,
        json={"name": "父部门", "parent_id": child_id, "sort_order": 0, "description": None},
    )
    assert resp.json()["code"] == ErrorCode.CONFLICT.value


# ============ 删除 ============

async def test_delete_department(client, admin_headers):
    created = await client.post(
        "/api/v1/system/departments", headers=admin_headers,
        json={"code": "tmp", "name": "临时部门"},
    )
    dept_id = created.json()["data"]["id"]

    resp = await client.delete(f"/api/v1/system/departments/{dept_id}", headers=admin_headers)
    assert resp.json()["code"] == 0


async def test_delete_department_with_child(client, admin_headers):
    """删除父部门 → 子部门变顶级。"""
    parent = await client.post(
        "/api/v1/system/departments", headers=admin_headers,
        json={"code": "parent", "name": "父部门"},
    )
    parent_id = parent.json()["data"]["id"]
    await client.post(
        "/api/v1/system/departments", headers=admin_headers,
        json={"code": "child", "name": "子部门", "parent_id": parent_id},
    )

    resp = await client.delete(
        f"/api/v1/system/departments/{parent_id}", headers=admin_headers
    )
    assert resp.json()["code"] == 0

    # 子部门还在，且变顶级（parent_id=None）
    resp = await client.get("/api/v1/system/departments", headers=admin_headers)
    child = next(d for d in resp.json()["data"]["items"] if d["code"] == "child")
    assert child["parent_id"] is None


async def test_delete_nonexistent_department(client, admin_headers):
    resp = await client.delete("/api/v1/system/departments/99999", headers=admin_headers)
    assert resp.json()["code"] == ErrorCode.DEPT_NOT_FOUND.value


# ============ 单查 ============

async def test_get_department(client, admin_headers):
    created = await client.post(
        "/api/v1/system/departments", headers=admin_headers,
        json={"code": "tech", "name": "技术部"},
    )
    dept_id = created.json()["data"]["id"]

    resp = await client.get(f"/api/v1/system/departments/{dept_id}", headers=admin_headers)
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["code"] == "tech"
    assert body["data"]["name"] == "技术部"


async def test_get_department_nonexistent(client, admin_headers):
    resp = await client.get("/api/v1/system/departments/99999", headers=admin_headers)
    assert resp.json()["code"] == ErrorCode.DEPT_NOT_FOUND.value


# ============ 部门树 ============

async def test_get_department_tree_nested(client, admin_headers):
    """GET /departments/tree：嵌套成树，顶层/子级均按 sort_order 排序，叶子空数组。"""
    root_a = await client.post(
        "/api/v1/system/departments", headers=admin_headers,
        json={"code": "root_a", "name": "总公司", "sort_order": 10},
    )
    root_a_id = root_a.json()["data"]["id"]
    root_b = await client.post(
        "/api/v1/system/departments", headers=admin_headers,
        json={"code": "root_b", "name": "分公司", "sort_order": 1},
    )
    root_b_id = root_b.json()["data"]["id"]
    child = await client.post(
        "/api/v1/system/departments", headers=admin_headers,
        json={"code": "dev_dept", "name": "研发部", "parent_id": root_a_id, "sort_order": 2},
    )
    child_id = child.json()["data"]["id"]

    resp = await client.get("/api/v1/system/departments/tree", headers=admin_headers)
    body = resp.json()
    assert body["code"] == 0

    # 顶层按 sort_order 升序：root_b(1) 在前，root_a(10) 在后
    roots = body["data"]
    assert [r["id"] for r in roots] == [root_b_id, root_a_id]

    # 子级嵌套在父节点 children 下，父节点保留完整字段
    root = roots[1]
    assert root["name"] == "总公司"
    assert root["parent_id"] is None
    assert root["sort_order"] == 10
    assert len(root["children"]) == 1
    child_node = root["children"][0]
    assert child_node["id"] == child_id
    assert child_node["parent_id"] == root_a_id
    assert child_node["children"] == []  # 叶子为空数组

    # 原扁平列表接口不带 children 键（无回归）
    flat = await client.get("/api/v1/system/departments", headers=admin_headers)
    for item in flat.json()["data"]["items"]:
        assert "children" not in item


async def test_get_department_tree_empty(client, admin_headers):
    resp = await client.get("/api/v1/system/departments/tree", headers=admin_headers)
    body = resp.json()
    assert body["code"] == 0
    assert body["data"] == []
