"""Redis key 集中定义 — 所有缓存/会话 key 的唯一拼装入口。"""

# 权限码缓存 TTL（秒）— 角色/权限变更时由 service 主动 delete 失效，这里只是兜底过期
PERM_CACHE_TTL = 300


def perm_key(user_id: int) -> str:
    """用户权限码缓存 — value 是逗号分隔的权限 code（写入时已排序）。"""
    return f"perm:{user_id}"


def session_key(session_id: str) -> str:
    """refresh 会话 — value 是当前有效的 refresh jti（轮换后覆盖成新的）。"""
    return f"session:{session_id}"


def blacklist_key(jti: str) -> str:
    """登出后 access token 的黑名单 — TTL = token 剩余有效期，过期自动释放。"""
    return f"blacklist:{jti}"


def login_fail_key(username: str) -> str:
    """登录失败计数 — 达阈值后 TTL 从「失败窗口」延长为「锁定时长」。"""
    return f"login_fail:{username}"
