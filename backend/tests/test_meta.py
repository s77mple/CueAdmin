"""元数据接口测试 — 错误码数据字典。

覆盖 meta 端点：
  - 无需认证即可访问（登录前的联调场景）
  - 返回全量错误码对照表 { code, name, description }

运行：cd backend && pytest tests/test_meta.py
"""


async def test_error_codes_no_auth(client):
    """错误码字典无需登录即可访问。"""
    resp = await client.get("/api/v1/system/meta/error-codes")
    body = resp.json()
    assert body["code"] == 0
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0


async def test_error_codes_contains_known_code(client):
    """字典里含已知错误码，且名字/描述与枚举定义一致。"""
    resp = await client.get("/api/v1/system/meta/error-codes")
    items = resp.json()["data"]
    by_code = {it["code"]: it for it in items}

    assert 11001 in by_code  # AUTH_INVALID_CREDENTIALS
    assert by_code[11001]["name"] == "AUTH_INVALID_CREDENTIALS"
    assert by_code[11001]["description"] == "用户名或密码错误"
