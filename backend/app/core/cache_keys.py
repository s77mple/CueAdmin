"""Redis key 集中定义 — 所有缓存/会话 key 的唯一拼装入口。

为什么集中：key 原先散落在认证依赖、auth 路由、4 个 service 里手拼 f-string。
读写两端一旦格式或 TTL 对不上，就是「改了角色权限但用户还是老权限、刷新也没用、
等 5 分钟自己好」这类现象与原因隔了好几层的 bug —— 6 处要同步改、漏一处就中招。
这里只回答「key 长什么样、活多久」，不放任何读写逻辑。

只依赖标准库，不依赖任何业务模块 —— 所以放 core，core 与各应用共用同一份。
"""

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
