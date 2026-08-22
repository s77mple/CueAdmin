/**
 * 前端使用的后端业务错误码 — 与 backend/app/core/exceptions.py 保持一致。
 *
 * 使用规范：
 *  - 判断错误类型只比对 code，永不比对 message 字符串（改文案不影响逻辑）
 *  - 中文含义写在注释里（IDE hover 可见）；后端还有一份完整字典
 *    见 GET /api/v1/system/meta/error-codes（登录后可查，比源码注释更全）
 */
export const ErrorCode = {
  // —— 认证：登录失效（http 拦截器跳登录页）——
  /** 令牌过期，请重新登录 */
  AUTH_TOKEN_EXPIRED: 11002,
  /** 令牌已作废（用户主动登出后） */
  AUTH_TOKEN_REVOKED: 11003,
  /** 令牌格式错误或签名无效 */
  AUTH_TOKEN_INVALID: 11005,

  // —— 访问控制 ——
  /** 当前用户没有该操作的权限 */
  ACCESS_DENIED: 16001,

  // —— 唯一性冲突（表单字段标红）——
  /** 用户名已被占用 */
  USERNAME_ALREADY_EXISTS: 12002,
  /** 角色编码已被占用 */
  ROLE_CODE_EXISTS: 13002,
  /** 菜单编码已被占用 */
  MENU_CODE_EXISTS: 14002,
  /** 权限编码已被占用 */
  PERM_CODE_EXISTS: 15002,
  /** 部门编码已被占用 */
  DEPT_CODE_EXISTS: 18002,

  // —— 通用业务 ——
  /** 参数校验失败（前端提交的数据不符合要求） */
  VALIDATION_ERROR: 17001,
  /** 数据冲突（并发操作、唯一约束冲突等） */
  CONFLICT: 17002
} as const;
