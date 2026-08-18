/**
 * 前端使用的后端业务错误码 — 与 backend/app/core/exceptions.py 保持一致。
 *
 * 使用规范：
 *  - 判断错误类型只比对 code，永不比对 message 字符串（改文案不影响逻辑）
 *  - 完整字典见 GET /api/v1/meta/error-codes（登录后可查）
 */
export const ErrorCode = {
  // —— 认证：登录失效（http 拦截器跳登录页）——
  AUTH_TOKEN_EXPIRED: 11002,
  AUTH_TOKEN_REVOKED: 11003,
  AUTH_TOKEN_INVALID: 11005,

  // —— 访问控制 ——
  ACCESS_DENIED: 16001,

  // —— 唯一性冲突（表单字段标红）——
  USERNAME_ALREADY_EXISTS: 12002,
  ROLE_CODE_EXISTS: 13002,
  MENU_CODE_EXISTS: 14002,
  PERM_CODE_EXISTS: 15002,
  DEPT_CODE_EXISTS: 18002
} as const;
