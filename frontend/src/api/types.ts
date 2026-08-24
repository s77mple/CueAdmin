// 公共类型 — 所有模块的 API 文件共用（框架层响应外壳，与具体业务无关）

/** 后端统一响应外壳 */
export type ApiResult<T = any> = {
  code: number;
  message: string;
  data: T;
};

/** 后端分页结构（用户/角色列表用） */
export type PageData<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
};

/** 后端非分页列表结构（部门/菜单/权限列表用） */
export type ListData<T> = {
  items: T[];
  total: number;
};
