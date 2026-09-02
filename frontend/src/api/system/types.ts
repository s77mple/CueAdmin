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
  /** 部门对象（表格显示名字用），对应后端 User.department 关系 */
  department: DepartmentBrief | null;
  role_ids: number[];
  /** 角色对象列表（表格显示名字用），对应后端 User.roles 关系 */
  roles: RoleBrief[];
  created_at: string;
  updated_at: string;
}

/** 用户详情（单查接口 GET /users/{id} 返回，打包角色/部门下拉） */
export interface UserDetail {
  user: User;
  roles: RoleBrief[];
  departments: DepartmentBrief[];
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

// ===== 请求类型（POST/PUT/PATCH 的请求体，对应后端 XxxCreate/Update/Patch）=====

/** 创建用户请求体（POST）— 无 is_active，新建默认启用 */
export interface UserCreate {
  username: string;
  password: string;
  display_name: string;
  phone?: string | null;
  role_ids?: number[];
  department_id?: number | null;
}

/** 全量更新用户请求体（PUT）— 所有字段必填 */
export interface UserUpdate {
  username: string;
  display_name: string;
  phone: string | null;
  is_active: boolean;
  role_ids: number[];
  department_id: number | null;
}

/** 部分更新用户请求体（PATCH）— 所有字段可选，传了才改 */
export interface UserPatch {
  username?: string | null;
  display_name?: string | null;
  phone?: string | null;
  is_active?: boolean | null;
  role_ids?: number[] | null;
  department_id?: number | null;
}

/** 用户列表查询参数 */
export interface UserListQuery {
  page?: number;
  page_size?: number;
  role_id?: number;
  is_active?: boolean;
}

// ===== 数据字典 =====

/** 错误码条目（GET /meta/error-codes 返回的一行） */
export interface ErrorCodeItem {
  code: number;
  name: string;
  description: string;
}
