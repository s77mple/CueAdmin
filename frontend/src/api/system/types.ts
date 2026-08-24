// system 模块实体类型 — 对应后端 app/system/schemas/

// ===== 简要类型（嵌套在其他实体里，字段少）=====

/** 角色简要信息 */
export interface RoleBrief {
  id: number;
  code: string;
  name: string;
}

/** 权限简要信息 */
export interface PermissionBrief {
  id: number;
  code: string;
  name: string;
  resource: string;
}

/** 菜单简要信息 */
export interface MenuBrief {
  id: number;
  code: string;
  name: string;
  parent_id: number | null;
}

/** 部门简要信息 */
export interface DepartmentBrief {
  id: number;
  code: string;
  name: string;
  parent_id: number | null;
}

// ===== 实体完整类型（列表接口返回）=====

/** 用户 */
export interface User {
  id: number;
  username: string;
  display_name: string;
  phone: string | null;
  is_active: boolean;
  department_id: number | null;
  roles: RoleBrief[];
  created_at: string;
  updated_at: string;
}

/** 角色 */
export interface Role {
  id: number;
  code: string;
  name: string;
  description: string | null;
  is_system: boolean;
  permissions: PermissionBrief[];
  menus: MenuBrief[];
}

/** 部门 */
export interface Department {
  id: number;
  code: string;
  name: string;
  parent_id: number | null;
  sort_order: number;
  description: string | null;
}

/** 菜单 */
export interface Menu {
  id: number;
  code: string;
  name: string;
  icon: string | null;
  path: string | null;
  component: string | null;
  parent_id: number | null;
  sort_order: number;
}

/** 权限 */
export interface Permission {
  id: number;
  code: string;
  name: string;
  resource: string;
  action: string;
  description: string | null;
}

// ===== 数据字典 =====

/** 错误码条目（GET /meta/error-codes 返回的一行） */
export interface ErrorCodeItem {
  code: number;
  name: string;
  description: string;
}
