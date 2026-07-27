import { http } from "@/utils/http";

// —————— 通用类型 ——————
export type ApiResult<T = any> = {
  code: number;
  message: string;
  data: T;
};

export type PageData<T> = {
  items: Array<T>;
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
};

// —————— 用户管理 ——————
export const getUserList = (params?: object) => {
  return http.request<ApiResult<PageData<any>>>("get", "/api/v1/users", { params });
};
export const getUserDetail = (id: number) => {
  return http.request<ApiResult<any>>("get", `/api/v1/users/${id}`);
};
export const createUser = (data?: object) => {
  return http.request<ApiResult<any>>("post", "/api/v1/users", { data });
};
export const updateUser = (id: number, data?: object) => {
  return http.request<ApiResult<any>>("put", `/api/v1/users/${id}`, { data });
};
export const deleteUser = (id: number) => {
  return http.request<ApiResult>("delete", `/api/v1/users/${id}`);
};

// —————— 角色管理 ——————
export const getRoleList = () => {
  return http.request<ApiResult<any>>("get", "/api/v1/roles");
};
export const createRole = (data?: object) => {
  return http.request<ApiResult<any>>("post", "/api/v1/roles", { data });
};
export const updateRole = (id: number, data?: object) => {
  return http.request<ApiResult<any>>("put", `/api/v1/roles/${id}`, { data });
};
export const deleteRole = (id: number) => {
  return http.request<ApiResult>("delete", `/api/v1/roles/${id}`);
};

// —————— 菜单管理 ——————
export const getMenuList = () => {
  return http.request<ApiResult<any>>("get", "/api/v1/menus");
};
export const createMenu = (data?: object) => {
  return http.request<ApiResult<any>>("post", "/api/v1/menus", { data });
};
export const updateMenu = (id: number, data?: object) => {
  return http.request<ApiResult<any>>("put", `/api/v1/menus/${id}`, { data });
};
export const deleteMenu = (id: number) => {
  return http.request<ApiResult>("delete", `/api/v1/menus/${id}`);
};

// —————— 权限管理 ——————
export const getPermissionList = () => {
  return http.request<ApiResult<any>>("get", "/api/v1/permissions");
};
export const createPermission = (data?: object) => {
  return http.request<ApiResult<any>>("post", "/api/v1/permissions", { data });
};
export const updatePermission = (id: number, data?: object) => {
  return http.request<ApiResult<any>>("put", `/api/v1/permissions/${id}`, { data });
};
export const deletePermission = (id: number) => {
  return http.request<ApiResult>("delete", `/api/v1/permissions/${id}`);
};
