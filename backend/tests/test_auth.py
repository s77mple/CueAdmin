"""认证测试 — 登录、刷新令牌轮换、复用检测、登出黑名单。

覆盖 auth_service 的核心安全逻辑（这是项目里最需要测试的部分）：
  - 登录成功 / 密码错误 / 用户不存在 / 禁用 / 无角色
  - refresh 正常轮换、复用检测（被盗检测 → 撤销整个会话）
  - 登出后 access token 进黑名单，无法再访问受保护接口

运行：cd backend && pytest
"""

from app.core.exceptions import ErrorCode
from app.core.security import hash_password
from app.system.models import Role, User


# ============ 登录 ============

async def test_login_success(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["username"] == "admin"
    assert data["roles"][0]["code"] == "admin"
    assert isinstance(data["permissions"], list)


async def test_login_wrong_password(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong-password"},
    )
    body = resp.json()
    assert body["code"] == ErrorCode.AUTH_INVALID_CREDENTIALS.value


async def test_login_nonexistent_user(client):
    """用户不存在和密码错误返回同一个码 — 防止用户名枚举。"""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": "whatever"},
    )
    assert resp.json()["code"] == ErrorCode.AUTH_INVALID_CREDENTIALS.value


async def test_login_disabled_user(client, db_session_factory):
    """禁用用户（is_active=False）不能登录，且与密码错误同码（不泄露「此账号被禁」）。"""
    async with db_session_factory() as session:
        role = Role(code="staff", name="普通员工")
        session.add(role)
        await session.flush()
        user = User(
            username="disabled_user",
            password_hash=await hash_password("pw123456"),
            display_name="禁用用户",
            is_active=False,
        )
        user.roles = [role]
        session.add(user)
        await session.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "disabled_user", "password": "pw123456"},
    )
    assert resp.json()["code"] == ErrorCode.AUTH_INVALID_CREDENTIALS.value


async def test_login_user_without_roles(client, db_session_factory):
    """没分配任何角色的用户不能登录。"""
    async with db_session_factory() as session:
        user = User(
            username="norole",
            password_hash=await hash_password("pw123456"),
            display_name="无角色",
            is_active=True,
        )
        session.add(user)
        await session.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "norole", "password": "pw123456"},
    )
    assert resp.json()["code"] == ErrorCode.AUTH_NO_ROLES.value


# ============ 刷新令牌 ============

async def test_refresh_rotates_token(client):
    """refresh 正常轮换：返回新 access + 新 refresh，旧 refresh 作废。"""
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    old_refresh = login.json()["data"]["refresh_token"]

    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["access_token"]
    assert body["data"]["refresh_token"]
    assert body["data"]["refresh_token"] != old_refresh  # 一次性轮换，新票 != 旧票


async def test_refresh_reuse_detection(client):
    """复用检测：拿已作废的旧 refresh 再换 → 判定被盗 → 撤销整个会话。"""
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    old_refresh = login.json()["data"]["refresh_token"]

    # 第一次换票成功，拿到新 refresh
    first = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert first.json()["code"] == 0
    new_refresh = first.json()["data"]["refresh_token"]

    # 拿旧 refresh 再换 → 复用检测 → 撤销会话
    reuse = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert reuse.json()["code"] == ErrorCode.AUTH_TOKEN_REVOKED.value

    # 会话已被撤销，连新 refresh 也失效（会话不存在）
    after_revoke = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": new_refresh},
    )
    assert after_revoke.json()["code"] == ErrorCode.AUTH_TOKEN_EXPIRED.value


async def test_refresh_rejects_access_token(client):
    """拿 access token 冒充 refresh token → 令牌类型错误。"""
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    access_token = login.json()["data"]["access_token"]

    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert resp.json()["code"] == ErrorCode.AUTH_TOKEN_INVALID.value


# ============ 登出黑名单 ============

async def test_logout_blacklists_access_token(client):
    """登出后 access token 进黑名单，不能再访问受保护接口。"""
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    access_token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 登出
    logout = await client.post("/api/v1/auth/logout", headers=headers)
    assert logout.json()["code"] == 0

    # 用同一个 access token 访问受保护接口 → 被黑名单拦截
    resp = await client.get("/api/v1/system/users", headers=headers)
    assert resp.json()["code"] == ErrorCode.AUTH_TOKEN_REVOKED.value
