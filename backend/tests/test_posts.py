"""岗位管理测试 — 岗位的增删改查 + 唯一性 / 删除保护。

覆盖 post_service 的核心业务逻辑：
  - 列表（按 sort_order 排序）
  - 创建（code 唯一）
  - 更新（PUT 全量）
  - 删除（级联解绑、返回消息含受影响用户数）
  - 单查

运行：cd backend && pytest tests/test_posts.py
"""

from app.core.exceptions import ErrorCode


# ============ 列表 ============

async def test_list_posts_empty(client, admin_headers):
    resp = await client.get("/api/v1/system/posts", headers=admin_headers)
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 0


async def test_list_posts_sorted_by_sort_order(client, admin_headers):
    """列表按 sort_order 升序（同序按 id），不分页时一次拉全量。"""
    await client.post(
        "/api/v1/system/posts", headers=admin_headers,
        json={"code": "b_post", "name": "后创建", "sort_order": 2},
    )
    await client.post(
        "/api/v1/system/posts", headers=admin_headers,
        json={"code": "a_post", "name": "先排位", "sort_order": 1},
    )
    resp = await client.get(
        "/api/v1/system/posts", params={"page_size": 100}, headers=admin_headers
    )
    body = resp.json()
    assert body["code"] == 0
    codes = [p["code"] for p in body["data"]["items"]]
    assert codes == ["a_post", "b_post"]


# ============ 创建 ============

async def test_create_post(client, admin_headers):
    resp = await client.post(
        "/api/v1/system/posts", headers=admin_headers,
        json={"code": "se", "name": "项目经理", "sort_order": 2, "description": "负责项目交付"},
    )
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["code"] == "se"
    assert data["name"] == "项目经理"
    assert data["id"] > 0


async def test_create_post_default_sort(client, admin_headers):
    """sort_order 不传默认 0；description 可空。"""
    resp = await client.post(
        "/api/v1/system/posts", headers=admin_headers,
        json={"code": "ceo", "name": "董事长"},
    )
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["code"] == "ceo"


async def test_create_post_duplicate_code(client, admin_headers):
    await client.post(
        "/api/v1/system/posts", headers=admin_headers,
        json={"code": "ceo", "name": "董事长"},
    )
    resp = await client.post(
        "/api/v1/system/posts", headers=admin_headers,
        json={"code": "ceo", "name": "重复"},
    )
    assert resp.json()["code"] == ErrorCode.POST_CODE_EXISTS.value


# ============ 更新 ============

async def test_update_post(client, admin_headers):
    created = await client.post(
        "/api/v1/system/posts", headers=admin_headers,
        json={"code": "hr", "name": "人力资源"},
    )
    post_id = created.json()["data"]["id"]

    resp = await client.put(
        f"/api/v1/system/posts/{post_id}",
        headers=admin_headers,
        json={"name": "人力资源部", "sort_order": 5, "description": None},
    )
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["name"] == "人力资源部"

    # 回查确认已持久化（code 不变）
    got = await client.get(f"/api/v1/system/posts/{post_id}", headers=admin_headers)
    detail = got.json()["data"]
    assert detail["code"] == "hr"
    assert detail["sort_order"] == 5
    assert detail["description"] is None


# ============ 删除 ============

async def test_delete_post(client, admin_headers):
    created = await client.post(
        "/api/v1/system/posts", headers=admin_headers,
        json={"code": "tmp_post", "name": "临时岗位"},
    )
    post_id = created.json()["data"]["id"]

    resp = await client.delete(f"/api/v1/system/posts/{post_id}", headers=admin_headers)
    assert resp.json()["code"] == 0

    # 删后单查 404
    got = await client.get(f"/api/v1/system/posts/{post_id}", headers=admin_headers)
    assert got.json()["code"] == ErrorCode.POST_NOT_FOUND.value


async def test_delete_post_unlinks_users(client, admin_headers):
    """删除被用户担任的岗位 → 用户保留，只是不再担任该岗位。"""
    post = await client.post(
        "/api/v1/system/posts", headers=admin_headers,
        json={"code": "staff", "name": "普通员工"},
    )
    post_id = post.json()["data"]["id"]

    created = await client.post(
        "/api/v1/system/users", headers=admin_headers,
        json={"username": "post_holder", "password": "hold1234",
              "display_name": "任职用户", "post_ids": [post_id]},
    )
    assert created.json()["code"] == 0
    uid = created.json()["data"]["id"]

    resp = await client.delete(f"/api/v1/system/posts/{post_id}", headers=admin_headers)
    assert resp.json()["code"] == 0
    assert "1 个用户" in resp.json()["message"]

    # 用户还在，岗位已清空
    detail = (await client.get(f"/api/v1/system/users/{uid}", headers=admin_headers)).json()["data"]
    assert detail["post_ids"] == []


async def test_delete_nonexistent_post(client, admin_headers):
    resp = await client.delete("/api/v1/system/posts/99999", headers=admin_headers)
    assert resp.json()["code"] == ErrorCode.POST_NOT_FOUND.value


# ============ 单查 ============

async def test_get_post(client, admin_headers):
    created = await client.post(
        "/api/v1/system/posts", headers=admin_headers,
        json={"code": "qa", "name": "测试工程师", "sort_order": 3, "description": "负责质量保障"},
    )
    post_id = created.json()["data"]["id"]

    resp = await client.get(f"/api/v1/system/posts/{post_id}", headers=admin_headers)
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["code"] == "qa"
    assert body["data"]["description"] == "负责质量保障"


async def test_get_post_nonexistent(client, admin_headers):
    resp = await client.get("/api/v1/system/posts/99999", headers=admin_headers)
    assert resp.json()["code"] == ErrorCode.POST_NOT_FOUND.value
