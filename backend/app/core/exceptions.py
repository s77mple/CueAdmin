"""业务异常 + 数字错误码枚举。"""

from enum import IntEnum


class ErrorCode(IntEnum):
    """数字错误码 — 按模块分段，段内留 99 个空位。"""

    # ====== 成功 ======
    OK = 0

    # ====== 认证 (AUTH)  11001-11099 ======
    AUTH_INVALID_CREDENTIALS = 11001   # 用户名或密码错误
    AUTH_TOKEN_EXPIRED       = 11002   # 令牌过期
    AUTH_TOKEN_REVOKED       = 11003   # 令牌已作废（登出后）
    AUTH_NO_ROLES            = 11004   # 未分配角色
    AUTH_TOKEN_INVALID       = 11005   # 令牌格式/签名无效
    AUTH_SERVICE_UNAVAILABLE = 11006   # 认证服务暂不可用（Redis 故障时拒绝请求）

    # ====== 用户 (USER)  12001-12099 ======
    USER_NOT_FOUND             = 12001  # 用户不存在
    USERNAME_ALREADY_EXISTS    = 12002  # 用户名已存在
    USER_CANNOT_DISABLE_SUPERADMIN = 12003  # 不允许禁用超级管理员

    # ====== 角色 (ROLE)  13001-13099 ======
    ROLE_NOT_FOUND   = 13001  # 角色不存在
    ROLE_CODE_EXISTS = 13002  # 角色编码已存在
    ROLE_IS_SYSTEM   = 13003  # 系统角色不可删除

    # ====== 菜单 (MENU)  14001-14099 ======
    MENU_NOT_FOUND   = 14001  # 菜单不存在
    MENU_CODE_EXISTS = 14002  # 菜单编码已存在

    # ====== 权限 (PERM)  15001-15099 ======
    PERM_NOT_FOUND   = 15001  # 权限不存在
    PERM_CODE_EXISTS = 15002  # 权限编码已存在

    # ====== 权限校验 (ACCESS)  16001-16099 ======
    ACCESS_DENIED = 16001      # 权限不足

    # ====== 部门 (DEPT)  18001-18099 ======
    DEPT_NOT_FOUND   = 18001  # 部门不存在
    DEPT_CODE_EXISTS = 18002  # 部门编码已存在

    # ====== 通用业务  17001-17099 ======
    VALIDATION_ERROR = 17001   # 参数校验失败
    CONFLICT         = 17002   # 数据冲突


class BusinessException(Exception):
    """纯业务异常 — 不继承 HTTPException，由全局 handler 捕获后转 HTTP 200。"""

    def __init__(self, code: ErrorCode, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
