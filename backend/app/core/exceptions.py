"""
业务异常 + 数字错误码。

设计思路：
  1. 所有业务异常都抛 BusinessException，不抛 HTTPException
  2. BusinessException 被全局 handler 捕获，转成 HTTP 200 + { code, message }
  3. 前端根据 code 判断成功/失败，不用管 HTTP 状态码

错误码分段规则：
  0        = 成功
  11001+   = 认证相关（登录、token、密码）
  12001+   = 用户相关
  13001+   = 角色相关
  14001+   = 菜单相关
  15001+   = 权限相关
  16001+   = 访问控制（权限不足）
  17001+   = 通用错误（参数校验、数据冲突）
  18001+   = 部门相关
  19001+   = 岗位相关

为什么用 IntEnum？
  前端 switch/case 可以直接用数字判断，不需要字符串比较。
  比如 if (res.code === 11001) { ... } // 密码错误
"""

from enum import IntEnum


class ErrorCode(IntEnum):
    """数字错误码 — 按模块分段，每个段留 99 个空位方便扩展。

    value 保持纯 int（int(ErrorCode.XXX) 正常参与运算），
    description 是给前端/联调用的中文含义，通过 GET /api/v1/system/meta/error-codes
    作为数据字典暴露出去，不需要翻源码找数字含义。
    """

    # ====== 成功 ======
    OK = (0, "成功")

    # ====== 认证 (AUTH)  11001-11099 ======
    AUTH_INVALID_CREDENTIALS = (11001, "用户名或密码错误")
    AUTH_TOKEN_EXPIRED       = (11002, "令牌过期，请重新登录")
    AUTH_TOKEN_REVOKED       = (11003, "令牌已作废（用户主动登出后）")
    AUTH_NO_ROLES            = (11004, "账号未分配任何角色")
    AUTH_TOKEN_INVALID       = (11005, "令牌格式错误或签名无效")
    AUTH_SERVICE_UNAVAILABLE = (11006, "认证服务暂不可用（一般不会触发）")

    # ====== 用户 (USER)  12001-12099 ======
    USER_NOT_FOUND                = (12001, "用户不存在")
    USERNAME_ALREADY_EXISTS       = (12002, "用户名已被占用")
    USER_CANNOT_DISABLE_SUPERADMIN = (12003, "不允许对超级管理员（admin）执行此操作")

    # ====== 角色 (ROLE)  13001-13099 ======
    ROLE_NOT_FOUND   = (13001, "角色不存在")
    ROLE_CODE_EXISTS = (13002, "角色编码已被占用")
    ROLE_IS_SYSTEM   = (13003, "系统内置角色不允许删除/修改")

    # ====== 菜单 (MENU)  14001-14099 ======
    MENU_NOT_FOUND   = (14001, "菜单不存在")
    MENU_CODE_EXISTS = (14002, "菜单编码已被占用")

    # ====== 权限 (PERM)  15001-15099 ======
    PERM_NOT_FOUND   = (15001, "权限不存在")
    PERM_CODE_EXISTS = (15002, "权限编码已被占用")

    # ====== 权限校验 (ACCESS)  16001-16099 ======
    ACCESS_DENIED = (16001, "当前用户没有该操作的权限")

    # ====== 通用业务  17001-17099 ======
    VALIDATION_ERROR = (17001, "参数校验失败（前端提交的数据不符合要求）")
    CONFLICT         = (17002, "数据冲突（并发操作、唯一约束冲突等）")

    # ====== 部门 (DEPT)  18001-18099 ======
    DEPT_NOT_FOUND   = (18001, "部门不存在")
    DEPT_CODE_EXISTS = (18002, "部门编码已被占用")

    # ====== 岗位 (POST)  19001-19099 ======
    POST_NOT_FOUND   = (19001, "岗位不存在")
    POST_CODE_EXISTS = (19002, "岗位编码已被占用")

    def __new__(cls, value: int, description: str):
        """构造 IntEnum 成员 — 保持 value 是纯 int，额外挂一个 description 属性。

        这是标准做法：int.__new__ 先按整数创建成员，_value_ 覆盖成纯 int，
        这样 int(ErrorCode.XXX) 和 .value 都正常工作，同时多了 .description。
        """
        obj = int.__new__(cls, value)
        obj._value_ = value
        obj.description = description
        return obj


class BusinessException(Exception):
    """业务异常 — 不继承 HTTPException。

    用法：
        raise BusinessException(ErrorCode.USER_NOT_FOUND, f"用户不存在: {user_id}")

    前端收到：
        { "code": 12001, "message": "用户不存在: 42", "data": null }
    """

    def __init__(self, code: ErrorCode, message: str):
        self.code = code          # 数字错误码
        self.message = message    # 人类可读的提示
